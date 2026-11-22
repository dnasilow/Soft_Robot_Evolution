"""Confirm the REAL pvp_s1 champion reproduces its 1.32, then render it."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
g = d['genome']; c = d['cppn']; pc = c.phase_cppn
print(f"stored archive fitness = {d['fitness']:.4f}", flush=True)
eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)
eng.load_robot(g, gait_params=pc)
f1 = float(eng.get_fitness(simulation_time=2.5, settle_time=0.5))   # eval settings
print(f"re-eval @ 2.5s (eval settings) = {f1:.4f}   reproduces={abs(f1-d['fitness'])<0.02}", flush=True)

# render it (sim-time 3 to match the other GIFs)
from render_champion import render
render('results/pvp_s1_champion_RUN1.pkl', out_gif='results/pvp_s1_champion_RUN1.gif', sim_time=3.0)
print("DONE", flush=True)
