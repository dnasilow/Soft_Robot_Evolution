import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
for name in ('stage1c_s3',):
    arc=pickle.load(open(f'results/{name}/archive.pkl','rb'))['archive']
    rows=sorted(arc.values(), key=lambda e:-e['fitness'])[:3]
    print(f"{name} top-3 (directed, settle 2.0, amp 0.16)\n", flush=True)
    print(f"{'fit':>8}{'vox':>5}{'blen':>6}{'musc%':>7}{'d@2.0':>9}{'abs_m':>9}", flush=True)
    for e in rows:
        g=e['genome']; idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
        mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
        eng=MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='directed')
        eng.load_robot(g)
        f=float(eng.get_fitness(simulation_time=2.5, settle_time=2.0))
        print(f"{e['fitness']:>8.4f}{n:>5}{bl:>6}{100*mu/n:>6.0f}%{f:>9.4f}{f*bl*0.01:>9.3f}", flush=True)
print("\n  seed1 best body: 2.4038 BL / 0.240 m", flush=True)
print("  seed2 best body: 2.4231 BL / 0.170 m", flush=True)
print("  pvp_long record: 1.1416 BL / 0.171 m", flush=True)
