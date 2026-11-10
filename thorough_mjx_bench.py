"""
Thorough MJX-vs-CPU investigation.

The earlier fair_mjx_bench.py inherited XLA_FLAGS=--xla_gpu_autotune_level=0 from
mjx_prototype.py (set there to dodge a COMPILE-time OOM). That disables XLA kernel
autotuning and almost certainly crippled GPU throughput (715 steps/s on a 30-DOF
model is ~1000x below a sane MJX number). This re-runs cleanly:

  * autotuning ON (flag removed)
  * async allocator (less fragmentation / OOM)
  * sweep batch size 128 -> 1024 -> 8192  (MJX wants large batches to saturate)
  * model sizes 30 / 100 / 300 bodies
  * report total steps/s, per-step latency, GPU/CPU ratio, and COMPILE time
    (compile matters: evolution makes a new model per morphology).

Verdict guide: GPU/CPU must exceed ~30x to beat our 30-worker CPU setup.
"""
import os
# Deliberately NOT disabling autotune this time. Use the async allocator.
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
import time
import numpy as np
import mujoco
import mujoco.mjx as mjx
import jax

STEPS = 500
MODELS = [30, 100, 300]
BATCHES = [128, 1024, 8192]


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


print("jax", jax.__version__, "| device", jax.devices(), "| backend", jax.default_backend())
print("XLA_FLAGS:", os.environ.get('XLA_FLAGS', '(none -> autotune ON)'))
print("(earlier crippled result for reference: N=30 batch=120 -> 715 steps/s)\n")

# ── CPU baselines (single robot) ─────────────────────────────────────────────
cpu_sps = {}
for N in MODELS:
    model = mujoco.MjModel.from_xml_string(chain_xml(N))
    data = mujoco.MjData(model); data.qvel[:] = 0.01
    t0 = time.perf_counter()
    for _ in range(STEPS):
        mujoco.mj_step(model, data)
    cpu_sps[N] = STEPS / (time.perf_counter() - t0)
    print(f"CPU N={N:3d} (nv={model.nv}): {cpu_sps[N]:,.0f} steps/s (1 thread)")
print()
print(f"{'N':>4} {'nv':>4} {'batch':>6} | {'compile':>8} | {'GPU steps/s':>13} | {'ms/step':>8} | {'GPU/CPU':>8}")

# ── GPU sweep ────────────────────────────────────────────────────────────────
for N in MODELS:
    model = mujoco.MjModel.from_xml_string(chain_xml(N))
    mx = mjx.put_model(model)

    def make_run(mx):
        @jax.jit
        def run(bd):
            def single(d):
                d, _ = jax.lax.scan(lambda d, _: (mjx.step(mx, d), None),
                                    d, None, length=STEPS)
                return d
            return jax.vmap(single)(bd)
        return run

    run = make_run(mx)

    def mk(_):
        d = mjx.make_data(model)
        return d.replace(qvel=d.qvel.at[:].set(0.01))

    for B in BATCHES:
        try:
            bd = jax.vmap(mk)(jax.numpy.arange(B))
            t0 = time.perf_counter()
            out = run(bd)
            jax.block_until_ready(out)
            compile_t = time.perf_counter() - t0

            ts = []
            for _ in range(3):
                bd2 = jax.vmap(mk)(jax.numpy.arange(B))
                t0 = time.perf_counter()
                out = run(bd2)
                jax.block_until_ready(out)
                ts.append(time.perf_counter() - t0)
            gpu_t = min(ts)
            gpu_sps = STEPS * B / gpu_t
            ms_step = gpu_t / STEPS * 1000
            ratio = gpu_sps / cpu_sps[N]
            print(f"{N:>4} {model.nv:>4} {B:>6} | {compile_t:>7.0f}s | {gpu_sps:>13,.0f} | "
                  f"{ms_step:>7.2f} | {ratio:>6.1f}x")
        except Exception as e:
            msg = "OOM" if "RESOURCE_EXHAUSTED" in str(e) or "out of memory" in str(e).lower() else type(e).__name__
            print(f"{N:>4} {model.nv:>4} {B:>6} | {msg}")

print("\nGuide: GPU/CPU must exceed ~30x to beat the 30-worker CPU setup we run now.")
print("Also weigh compile time: evolution makes a NEW model per morphology.")
