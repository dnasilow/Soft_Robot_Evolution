import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
def ev(g, amp, settle, gp):
    e=MuJoCoTendonPhysics(actuation_amplitude=amp, fitness_mode='directed')
    e.load_robot(g, gait_params=gp)
    return float(e.get_fitness(simulation_time=2.5, settle_time=settle))
d=pickle.load(open('results/stage2c_s1/best_robot.pkl','rb'))
g=d['genome']; pc=d['cppn'].phase_cppn
idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
print(f"champion 272vox blen{bl}  (archive fitness 2.6358)\n", flush=True)
for lab, gp in [("WITH phase net", pc), ("WITHOUT (stage-1 gait)", None)]:
    for st in (0.5, 2.0):
        f=ev(g,0.16,st,gp)
        print(f"  {lab:<24} settle {st}s -> {f:.4f} BL  ({f*bl*0.01:.3f} m)", flush=True)
print(f"\n  pvp_long old record @ amp 0.08 settle 2.0 = 1.1416 BL (0.171 m)", flush=True)
