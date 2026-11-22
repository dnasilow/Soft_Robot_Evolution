"""Measure eval-time cost of raising the voxel cap (tendon + per-voxel phase),
since tendon self-collision scales super-linearly. Decisive for a 9-day run budget."""
import time, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
import src.evolution.cppn_genome as cg
import src.evolution.genome_config as gc
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

def make_body(cap, rng, innov, target_lo):
    cg.MAX_VOXELS_PER_ROBOT = cap; gc.MAX_VOXELS_PER_ROBOT = cap
    for _ in range(400):
        c = CPPNGenome(innov, rng); g = c.to_voxel_grid()
        if g is not None and int((g!=0).sum()) >= target_lo:
            c.init_phase_cppn(rng); return c, g
    return None, None

def time_eval(g, pc, n=3):
    ts = []
    for _ in range(n):
        eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)
        eng.load_robot(g, gait_params=pc)
        na = len(eng._base_phases)
        t0 = time.perf_counter()
        eng.get_fitness(simulation_time=2.5, settle_time=0.5)
        ts.append(time.perf_counter()-t0)
    return np.median(ts), na

rng = np.random.default_rng(3); innov = InnovationCounter()
print(f"{'cap':>5}{'voxels':>8}{'act_tendons':>13}{'sec/eval':>10}{'rel':>7}")
base = None
for cap, lo in [(300,290),(400,380),(500,480),(700,650)]:
    c, g = make_body(cap, rng, innov, lo)
    if g is None: print(f"{cap:>5}   (no body reached {lo})"); continue
    vox = int((g!=0).sum())
    sec, na = time_eval(g, c.phase_cppn)
    if base is None: base = sec
    print(f"{cap:>5}{vox:>8}{na:>13}{sec:>10.2f}{sec/base:>7.2f}x")
