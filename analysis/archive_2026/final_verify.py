import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
def ev(g, amp, settle, gp):
    e=MuJoCoTendonPhysics(actuation_amplitude=amp, fitness_mode='directed')
    e.load_robot(g, gait_params=gp); return float(e.get_fitness(simulation_time=2.5, settle_time=settle))
print("Stage-2 champions, transient-free (directed, settle 2.0, amp 0.16)\n", flush=True)
print(f"{'run':<13}{'arch':>8}{'d@0.5':>8}{'d@2.0':>8}{'ret':>6}{'vox':>5}{'musc%':>7}{'abs_m':>8}", flush=True)
abs_m=[]
for r in ('stage2c_s1','stage2c_s2','stage2c_s3'):
    d=pickle.load(open(f'results/{r}/best_robot.pkl','rb'))
    g=d['genome']; pc=getattr(d.get('cppn'),'phase_cppn',None)
    idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
    mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
    a=ev(g,0.16,0.5,pc); b=ev(g,0.16,2.0,pc); abs_m.append(b*bl*0.01)
    print(f"{r:<13}{d['fitness']:>8.4f}{a:>8.4f}{b:>8.4f}{100*b/max(a,1e-9):>5.0f}%"
          f"{n:>5}{100*mu/n:>6.0f}%{b*bl*0.01:>8.3f}", flush=True)
am=np.array(abs_m)
print(f"\nabsolute: {np.round(am,3).tolist()} m  mean {am.mean():.3f}  spread {am.max()/am.min():.2f}x", flush=True)
print(f"pvp_long old record: 1.1416 BL / 0.171 m (same settings, amp 0.08)", flush=True)
