import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
d=pickle.load(open('results/stage1b_s1/archive.pkl','rb'))
rows=sorted(d['archive'].values(), key=lambda e:-e['fitness'])
print("Real locomotion vs one-off topple (a topple vanishes with a longer settle)\n", flush=True)
for rank in (0,1):
    g=rows[rank]['genome']
    idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
    mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
    res={}
    for st in (0.5, 2.0):
        e=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='directed')
        e.load_robot(g)
        res[st]=float(e.get_fitness(simulation_time=2.5, settle_time=st))
        print(f"  #{rank+1} settle {st}s -> {res[st]:.4f} BL", flush=True)
    print(f"  #{rank+1}: {n}vox {mu}musc/{n-mu}passive blen{bl} | retained "
          f"{100*res[2.0]/max(res[0.5],1e-9):.0f}% | abs@2.0s = {res[2.0]*bl*0.01:.3f} m\n", flush=True)
