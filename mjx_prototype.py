"""
MJX prototype: benchmark batched joint-based simulation vs CPU MuJoCo.

Model: 301-body chain with 300 hinge joints + 300 motor actuators.
This approximates a dense 5x5x5 voxel soft robot (~300 active connections).

Measures:
 - CPU: single mj_step calls, sequential
 - GPU: vmapped mjx.step over full population, batched
"""
import os
os.environ['XLA_FLAGS'] = '--xla_gpu_autotune_level=0'   # skip triton autotuning — avoids OOM during compilation
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'     # reduces memory fragmentation

import time
import numpy as np
import mujoco
import mujoco.mjx as mjx
import jax
import jax.numpy as jnp

POP_SIZE = 120    # full population
N_BODIES = 31     # 30 joints/actuators — a minimal soft robot; tests MJX at scale
N_STEPS  = 5000   # 2.5s sim at dt=0.0005

print(f"JAX device: {jax.devices()}")
print(f"Model: {N_BODIES} bodies, {N_BODIES-1} joints, {N_BODIES-1} actuators")
print(f"Population: {POP_SIZE}  |  Steps per eval: {N_STEPS}")
print()


def build_chain_xml(n_bodies: int, dt: float = 0.0005) -> str:
    lines = [
        '<mujoco model="voxel_chain">',
        # No floor, no gravity — isolates pure joint-dynamics cost from contact constraint cost.
        # Contact Jacobians (floor × 300 bodies × batch) are what OOM'd previously.
        f'  <option timestep="{dt}" gravity="0 0 0" solver="CG" iterations="30" tolerance="1e-6"/>',
        '  <worldbody>',
        '    <body name="b0" pos="0 0 0.5">',
        '      <freejoint/>',
        '      <geom type="box" size="0.01 0.01 0.01" mass="0.001" rgba="0.2 0.6 0.9 1"/>',
    ]
    for i in range(1, n_bodies):
        lines.append(f'      <body name="b{i}" pos="0.025 0 0">')
        lines.append(f'        <joint name="j{i}" type="hinge" axis="0 1 0" range="-1.57 1.57" damping="0.01"/>')
        lines.append(f'        <geom type="box" size="0.01 0.01 0.01" mass="0.001" rgba="0.2 0.6 0.9 1"/>')
    lines.extend(['      </body>'] * (n_bodies - 1))
    lines.extend([
        '    </body>',
        '  </worldbody>',
        '  <actuator>',
    ])
    for i in range(1, n_bodies):
        lines.append(f'    <motor name="act{i}" joint="j{i}" gear="0.05" ctrllimited="true" ctrlrange="-1 1"/>')
    lines.extend(['  </actuator>', '</mujoco>'])
    return '\n'.join(lines)


xml   = build_chain_xml(N_BODIES)
model = mujoco.MjModel.from_xml_string(xml)
print(f"Model loaded: nq={model.nq}, nv={model.nv}, nu={model.nu}, nbody={model.nbody}")

# ── CPU baseline: sequential single-robot evals ────────────────────────────────
print("\n--- CPU baseline (sequential, 10 robots) ---")
data     = mujoco.MjData(model)
ctrl_cpu = np.random.uniform(-0.5, 0.5, (10, model.nu)).astype(np.float32)

t0 = time.perf_counter()
for i in range(10):
    mujoco.mj_resetData(model, data)
    data.ctrl[:] = ctrl_cpu[i]
    for _ in range(N_STEPS):
        mujoco.mj_step(model, data)
cpu_time_10  = time.perf_counter() - t0
cpu_per_robot = cpu_time_10 / 10
cpu_sps       = N_STEPS / cpu_per_robot
print(f"10 robots: {cpu_time_10:.2f}s  |  {cpu_per_robot:.2f}s/robot  |  {cpu_sps:.0f} steps/s single-threaded")
est_30workers = cpu_per_robot * (POP_SIZE + 12) / 30
print(f"Estimated gen time @ pop={POP_SIZE}+12 elites, 30 workers: {est_30workers:.0f}s")

# ── GPU: vmapped mjx simulation ─────────────────────────────────────────────────
print("\n--- GPU (MJX vmapped) ---")
mx = mjx.put_model(model)


def make_data(rng_key):
    d    = mjx.make_data(model)
    ctrl = jax.random.uniform(rng_key, (model.nu,), minval=-0.5, maxval=0.5)
    return d.replace(ctrl=ctrl)


CHUNK = 100  # steps per JIT call — avoids materialising the full 5000-step history
             # in GPU memory at once; 50 Python-level calls of 100 steps each.

@jax.jit
def batch_step_chunk(mx, batch_data):
    """Advance all POP_SIZE robots by CHUNK steps in one batched GPU kernel."""
    def single_chunk(d):
        def step_fn(d, _):
            d = mjx.step(mx, d)
            return d, None
        d, _ = jax.lax.scan(step_fn, d, None, length=CHUNK)
        return d
    return jax.vmap(single_chunk)(batch_data)


print(f"Compiling JIT (chunk={CHUNK} steps, first call includes XLA compile)...")
keys    = jax.random.split(jax.random.PRNGKey(0), POP_SIZE)
batch_d = jax.vmap(make_data)(keys)

t0          = time.perf_counter()
batch_d_out = batch_step_chunk(mx, batch_d)
batch_d_out.qpos.block_until_ready()
compile_time = time.perf_counter() - t0
print(f"First call (compile + {CHUNK} steps): {compile_time:.2f}s")

print(f"Timing {N_STEPS // CHUNK} JIT-warmed chunks ({N_STEPS} total steps)...")
keys2    = jax.random.split(jax.random.PRNGKey(42), POP_SIZE)
batch_d2 = jax.vmap(make_data)(keys2)

t0 = time.perf_counter()
for _ in range(N_STEPS // CHUNK):
    batch_d2 = batch_step_chunk(mx, batch_d2)
batch_d2.qpos.block_until_ready()
gpu_time = time.perf_counter() - t0

gpu_sps_total = N_STEPS * POP_SIZE / gpu_time
speedup       = est_30workers / gpu_time

print(f"{POP_SIZE} robots × {N_STEPS} steps: {gpu_time:.3f}s  |  {gpu_sps_total/1e6:.2f}M total steps/s")
print(f"vs CPU 30-worker estimate: {speedup:.1f}x speedup")
print()
print("=== SUMMARY ===")
print(f"CPU 30-worker estimate:  {est_30workers:.0f}s/gen")
print(f"GPU MJX batched:         {gpu_time:.3f}s/gen")
print(f"Speedup:                 {speedup:.1f}x")
print(f"(compile-once overhead:  {compile_time:.1f}s, paid once at startup)")
