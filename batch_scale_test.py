"""
Fast batch-scaling test to diagnose WHY MJX is slow on this (WSL2) setup.

Key question: as batch grows, does per-step latency stay ~constant?
  - constant latency  -> overhead/launch-bound (GPU underused; throughput scales
                         with batch but a fixed per-step cost dominates -> WSL2
                         kernel-launch latency is the likely culprit)
  - latency grows     -> compute-bound (GPU actually saturated)

STEPS kept tiny (latency is per-step); compile dominates wall time.
"""
import os
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
import time
import numpy as np
import mujoco
import mujoco.mjx as mjx
import jax

STEPS = 20
COMBOS = [(30, 256), (30, 4096), (300, 256), (300, 2048)]


def chain_xml(n, dt=0.002):
    lines = ['<mujoco>',
             f'<option timestep="{dt}" gravity="0 0 0" solver="CG" iterations="20" tolerance="1e-6"/>',
             '<worldbody>',
             '<body name="b0" pos="0 0 0.5"><freejoint/>'
             '<geom type="box" size="0.01 0.01 0.01" mass="0.001"/>']
    for i in range(1, n):
        lines.append(f'<body name="b{i}" pos="0.025 0 0">'
                     f'<joint name="j{i}" type="hinge" axis="0 1 0" range="-1.5 1.5" damping="0.05"/>'
                     f'<geom type="box" size="0.01 0.01 0.01" mass="0.001"/>')
    lines += ['</body>'] * (n - 1)
    lines += ['</body>', '</worldbody>', '</mujoco>']
    return '\n'.join(lines)


print("device", jax.devices(), "| autotune ON | allocator async")
print(f"{'N':>4} {'batch':>6} | {'compile':>8} | {'ms/step':>9} | {'steps/s':>12}")

models = {}
for N, B in COMBOS:
    if N not in models:
        m = mujoco.MjModel.from_xml_string(chain_xml(N))
        models[N] = (m, mjx.put_model(m))
    model, mx = models[N]

    @jax.jit
    def run(bd, mx=mx):
        def single(d):
            d, _ = jax.lax.scan(lambda d, _: (mjx.step(mx, d), None), d, None, length=STEPS)
            return d
        return jax.vmap(single)(bd)

    def mk(_):
        d = mjx.make_data(model)
        return d.replace(qvel=d.qvel.at[:].set(0.01))

    try:
        bd = jax.vmap(mk)(jax.numpy.arange(B))
        t0 = time.perf_counter(); jax.block_until_ready(run(bd)); comp = time.perf_counter() - t0
        ts = []
        for _ in range(3):
            bd2 = jax.vmap(mk)(jax.numpy.arange(B))
            t0 = time.perf_counter(); jax.block_until_ready(run(bd2)); ts.append(time.perf_counter() - t0)
        g = min(ts)
        print(f"{N:>4} {B:>6} | {comp:>7.0f}s | {g/STEPS*1000:>8.2f} | {STEPS*B/g:>12,.0f}")
    except Exception as e:
        msg = "OOM" if "RESOURCE_EXHAUSTED" in str(e) or "out of memory" in str(e).lower() else type(e).__name__
        print(f"{N:>4} {B:>6} | {msg}")

print("\nIf ms/step is ~flat across batch -> launch/overhead-bound (WSL2), not compute-bound.")
