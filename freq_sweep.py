import pickle, numpy as np
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
d = pickle.load(open('results/tendon_eg/best_robot.pkl','rb'))
g = d['genome']; gp = d['cppn'].to_gait_params()
# champion evolved at freq=10 Hz, amp=0.08 (DEFAULT_AMP), sim 2.5 / settle 0.5
print('validation @ evolved settings (freq10 amp0.08 sim2.5): ', end='', flush=True)
e = MuJoCoTendonPhysics(actuation_frequency=10, actuation_amplitude=0.08)
e.load_robot(g, gait_params=gp)
print(f'{e.get_fitness(simulation_time=2.5, settle_time=0.5):.4f} BL (saved=1.1195)', flush=True)
print('frequency sweep (amp=0.08, sim 2.0):', flush=True)
for freq in [5, 7, 8, 10, 12, 14]:
    e = MuJoCoTendonPhysics(actuation_frequency=freq, actuation_amplitude=0.08)
    e.load_robot(g, gait_params=gp)
    print(f'  freq={freq:>3} Hz -> {e.get_fitness(simulation_time=2.0, settle_time=0.5):.4f} BL', flush=True)
