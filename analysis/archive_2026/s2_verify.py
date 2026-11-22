import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
def ev(g, amp, settle, gp=None):
    e=MuJoCoTendonPhysics(actuation_amplitude=amp, fitness_mode='directed')
    e.load_robot(g, gait_params=gp)
    return float(e.get_fitness(simulation_time=2.5, settle_time=settle))
d=pickle.load(open('results/stage2c_s1/best_robot.pkl','rb'))
g=d['genome']; pc=getattr(d.get('cppn'),'phase_cppn',None)
idx=np.argwhere(g!=0); bl=int((idx.max(0)-idx.min(0)+1).max())+1
mu=int(((g==1)|(g==2)).sum()); n=int((g!=0).sum())
print(f"stage2c champion: {n}vox {mu}musc({100*mu/n:.0f}%) blen{bl} phase_cppn={pc is not None}\n", flush=True)
a=ev(g,0.16,0.5); print(f"  directed @ settle 0.5 = {a:.4f} BL  ({a*bl*0.01:.3f} m)", flush=True)
b=ev(g,0.16,2.0); print(f"  directed @ settle 2.0 = {b:.4f} BL  ({b*bl*0.01:.3f} m)  retained {100*b/max(a,1e-9):.0f}%", flush=True)
# stage-1 body BEFORE control optimisation, same body, fixed material gait
s1=pickle.load(open('results/stage1c_s1/final_population.pkl','rb'))
match=[i for i,gg in enumerate(s1['genomes']) if np.array_equal(gg,g)]
if match:
    g1=s1['genomes'][match[0]]
    c=ev(g1,0.16,2.0)
    print(f"\n  SAME body, stage-1 fixed gait @ settle 2.0 = {c:.4f} BL  ({c*bl*0.01:.3f} m)", flush=True)
    print(f"  -> control optimisation gain = {b/max(c,1e-9):.2f}x", flush=True)
print(f"\n  reference pvp_long (old record) @ its own amp 0.08, settle 2.0 = 1.1416 BL (0.171 m)", flush=True)
