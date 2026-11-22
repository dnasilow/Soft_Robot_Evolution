import pickle, numpy as np, sys, os, time
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
d=None
for _ in range(8):
    try: d=pickle.load(open('results/stage1c_s1/checkpoint.pkl','rb')); break
    except Exception: time.sleep(1.2)
top=max(d['archive'].values(), key=lambda e:e['fitness'])
g=top['genome']; idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
print(f"stage1c top: {n}vox {mu}musc ({100*mu/n:.0f}%) blen{bl}", flush=True)
for st in (0.5, 2.0):
    e=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='directed')
    e.load_robot(g)
    f=float(e.get_fitness(simulation_time=2.5, settle_time=st))
    print(f"  settle {st}s -> {f:.4f} BL   (abs {f*bl*0.01:.3f} m)", flush=True)
