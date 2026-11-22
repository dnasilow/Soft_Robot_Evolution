import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
d=pickle.load(open('results/cheney_repro_s1/best_robot.pkl','rb'))
g=d['genome']; idx=np.argwhere(g!=0); ext=idx.max(0)-idx.min(0)+1
bl=int(ext.max())+1; n=len(idx); m={k:int((g==k).sum()) for k in (1,2,3,4)}
mu=m[1]+m[2]
print(f"CHAMPION  fitness={d['fitness']:.4f}  voxels={n}", flush=True)
print(f"  materials: mat1={m[1]} mat2={m[2]} soft={m[3]} stiff={m[4]}  -> muscle {100*mu/n:.0f}%", flush=True)
print(f"  bbox={tuple(int(x) for x in ext)} body_len={bl} elong={ext.max()/max(ext.min(),1):.2f} fill={n/np.prod(ext):.2f}", flush=True)
zs=sorted(set(idx[:,2].tolist())); print(f"  z-layer areas (bottom->top): {[int((g[:,:,z]!=0).sum()) for z in zs]}", flush=True)
print("\nVERIFY (is it grounded, transient-free?)", flush=True)
for mode,st in (('forward',0.5),('forward',2.0),('directed',2.0)):
    e=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode=mode); e.load_robot(g)
    f=float(e.get_fitness(simulation_time=2.5, settle_time=st))
    print(f"  {mode:<9} settle {st}: {f:.4f} BL   abs {f*bl*0.01:.3f} m", flush=True)
