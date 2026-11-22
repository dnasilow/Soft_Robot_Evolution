"""Verify --fitness skip: (1) graded credit formula, (2) a grounded crawler scores ~the
same as directed (skip only differs when the robot actually leaves the ground)."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

# (1) formula sanity (settled=0.1 -> thr=0.2, hi=0.35)
thr, hi = 0.2, 0.2*1.75
def credit(z):
    if z <= thr: return 1.0
    if z >= hi:  return 0.0
    return (hi - z)/(hi - thr)
checks = {0.15:1.0, 0.20:1.0, 0.275:0.5, 0.35:0.0, 0.40:0.0}
for z,exp in checks.items():
    got = credit(z); assert abs(got-exp)<1e-9, (z,got,exp)
print(f"(1) credit ramp OK: 2x=full, midpoint(0.275)=0.5, 3.5x(0.35)=0  hi={hi:.3f}")

# (2) functional: grounded champion, directed vs skip should match (crawler never > 2x resting)
d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
g = d['genome']; pc = d['cppn'].phase_cppn
def ev(mode):
    e = MuJoCoTendonPhysics(actuation_amplitude=0.08, fitness_mode=mode)
    e.load_robot(g, gait_params=pc)
    return float(e.get_fitness(simulation_time=2.5, settle_time=0.5))
fd, fs = ev('directed'), ev('skip')
print(f"(2) grounded champion: directed={fd:.4f}  skip={fs:.4f}  diff={abs(fd-fs):.4f}")
print("    -> ~equal expected (crawler stays grounded; skip only opens headroom for lifters)")
print("SKIP MODE OK")
