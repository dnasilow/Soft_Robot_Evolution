import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
arc=pickle.load(open('results/stage1c_s1/archive.pkl','rb'))['archive']
rows=sorted(arc.items(), key=lambda kv:-kv[1]['fitness'])[:8]
print("Re-rank at settle 2.0s (transient-free) — which body to carry into Stage 2\n", flush=True)
print(f"{'cell':>10}{'orig':>8}{'settle2.0':>11}{'retain':>8}{'vox':>5}{'musc%':>7}{'abs_m':>8}", flush=True)
out=[]
for k,e in rows:
    g=e['genome']; idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
    mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
    eng=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='directed')
    eng.load_robot(g)
    f2=float(eng.get_fitness(simulation_time=2.5, settle_time=2.0))
    out.append((k,e['fitness'],f2,n,mu/n,f2*bl*0.01))
    print(f"{str(k):>10}{e['fitness']:>8.4f}{f2:>11.4f}{100*f2/max(e['fitness'],1e-9):>7.0f}%"
          f"{n:>5}{100*mu/n:>6.0f}%{f2*bl*0.01:>8.3f}", flush=True)
best=max(out,key=lambda x:x[2])
print(f"\nBEST at settle 2.0: cell {best[0]}  {best[2]:.4f} BL  ({best[3]} vox, {100*best[4]:.0f}% muscle, {best[5]:.3f} m)", flush=True)
