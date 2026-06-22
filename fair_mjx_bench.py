"""
Fair MJX-vs-CPU throughput benchmark.

The existing mjx_prototype.py is misleading: a 31-body model (too small for GPU)
that also numerically diverges. This measures pure, STABLE articulated-body
dynamics throughput at realistic DOF scales, so we can decide if the GPU port is
worth it. Metric: total steps/s on GPU (120 robots batched) vs CPU (1 robot),
i.e. how many CPU-single-thread-equivalents the GPU delivers. We run evolution on
~30 CPU workers, so the GPU must beat ~30x to be worth porting to.
"""
import os
os.environ['XLA_FLAGS'] = '--xla_gpu_autotune_level=0'
import time
import numpy as np
import mujoco
import mujoco.mjx as mjx
import jax

POP = 120
STEPS = 1000


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


print("device:", jax.devices())
print(f"batch={POP}, steps={STEPS}\n")
print(f"{'bodies':>6} {'nv':>5} | {'CPU steps/s':>12} | {'GPU steps/s':>12} | {'GPU/CPU':>8} | compile")

for N in [30, 100, 300]:
    model = mujoco.MjModel.from_xml_string(chain_xml(N))

    # CPU: one robot, sequential
    data = mujoco.MjData(model)
    data.qvel[:] = 0.01
    t0 = time.perf_counter()
    for _ in range(STEPS):
        mujoco.mj_step(model, data)
    cpu_t = time.perf_counter() - t0
    cpu_sps = STEPS / cpu_t

    # GPU: POP robots, vmapped + scanned
    mx = mjx.put_model(model)

    @jax.jit
    def batch_run(mx, bd):
        def single(d):
            def step_fn(d, _):
                return mjx.step(mx, d), None
            d, _ = jax.lax.scan(step_fn, d, None, length=STEPS)
            return d
        return jax.vmap(single)(bd)

    def mk(_):
        d = mjx.make_data(model)
        return d.replace(qvel=d.qvel.at[:].set(0.01))

    bd = jax.vmap(mk)(jax.numpy.arange(POP))
    t0 = time.perf_counter()
    out = batch_run(mx, bd)
    out.qpos.block_until_ready()
    comp = time.perf_counter() - t0

    bd2 = jax.vmap(mk)(jax.numpy.arange(POP))
    t0 = time.perf_counter()
    out = batch_run(mx, bd2)
    out.qpos.block_until_ready()
    gpu_t = time.perf_counter() - t0
    gpu_sps = STEPS * POP / gpu_t

    print(f"{N:>6} {model.nv:>5} | {cpu_sps:>12.0f} | {gpu_sps:>12.0f} | "
          f"{gpu_sps/cpu_sps:>7.1f}x | {comp:.0f}s")

print("\nGuide: GPU/CPU must exceed ~30x to beat the 30-worker CPU setup we run now.")
