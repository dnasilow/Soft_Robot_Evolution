import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
ck=pickle.load(open('results/cheney_repro_s1/checkpoint.pkl','rb'))
rows=sorted(ck['archive'].values(), key=lambda e:-e['fitness'])[:3]
print("cheney_repro_s1 top-3 — is 3.50 real, or transient/ballistic?", flush=True)
print("(run used --fitness forward = NO ground penalty, so airborne gaits are unpenalised)\n", flush=True)
print(f"{'arch':>8}{'fwd@0.5':>9}{'fwd@2.0':>9}{'dir@2.0':>9}{'ret':>6}{'vox':>5}{'abs_m':>8}", flush=True)
for e in rows:
    g=e['genome']; idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
    n=int((g!=0).sum())
    out={}
    for mode,st in (('forward',0.5),('forward',2.0),('directed',2.0)):
        eng=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode=mode)
        eng.load_robot(g)
        out[(mode,st)]=float(eng.get_fitness(simulation_time=2.5, settle_time=st))
    a=out[('forward',0.5)]; b=out[('forward',2.0)]; c=out[('directed',2.0)]
    print(f"{e['fitness']:>8.4f}{a:>9.4f}{b:>9.4f}{c:>9.4f}{100*b/max(a,1e-9):>5.0f}%{n:>5}{b*bl*0.01:>8.3f}", flush=True)
print("\n  dir@2.0 applies the ground penalty: if it collapses vs fwd, the gait is airborne.", flush=True)
print("  reference: stage2c best 2.9364 BL / 0.294 m ; pvp_long 1.1416 / 0.171 m", flush=True)
