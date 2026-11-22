import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
def ev(g, amp, settle, gp=None):
    e=MuJoCoTendonPhysics(actuation_amplitude=amp, fitness_mode='directed')
    e.load_robot(g, gait_params=gp)
    return float(e.get_fitness(simulation_time=2.5, settle_time=settle))
arc=pickle.load(open('results/stage1c_s1/archive.pkl','rb'))['archive']
top=sorted(arc.items(), key=lambda kv:-kv[1]['fitness'])[:3]
print("SAME MODE (directed) both columns - the valid comparison\n", flush=True)
print(f"{'cell':>9}{'d@0.5':>9}{'d@2.0':>9}{'retain':>8}{'vox':>5}{'musc%':>7}{'abs_m@2.0':>11}", flush=True)
for k,e in top:
    g=e['genome']; idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
    mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
    a=ev(g,0.16,0.5); b=ev(g,0.16,2.0)
    print(f"{str(k):>9}{a:>9.4f}{b:>9.4f}{100*b/max(a,1e-9):>7.0f}%{n:>5}{100*mu/n:>6.0f}%{b*bl*0.01:>11.3f}", flush=True)
# fair reference: pvp_long at the SAME amplitude
d=pickle.load(open('results/pvp_long/best_robot.pkl','rb'))
g=d['genome']; pc=getattr(d.get('cppn'),'phase_cppn',None)
idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
print("\npvp_long (old record, 100% muscle) evaluated the SAME way:", flush=True)
for amp in (0.08, 0.16):
    b=ev(g,amp,2.0,pc)
    print(f"  amp {amp}: d@2.0 = {b:.4f} BL   abs {b*bl*0.01:.3f} m", flush=True)
