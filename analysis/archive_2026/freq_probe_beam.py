"""Beam champion (evolved at 10 Hz) evaluated at several actuation frequencies, 10 cycles each,
settle scaled to 5 cycles, early termination off. Measurement only."""
import os, sys, pickle
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def job(f):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open('results/cheney_beam_s1/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS, actuation_frequency=f)
    e.load_robot(g)
    return f, float(e.get_fitness(simulation_time=10.0 / f, settle_time=5.0 / f, early_term_threshold=-1e9))


if __name__ == '__main__':
    with Pool(6) as p:
        res = sorted(p.map(job, [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]))
    print("beam champion (evolved at 10 Hz), 10 cycles at each frequency:")
    for f, bl in res:
        print(f"   {f:>4.0f} Hz: {bl:.4f} BL in 10 cycles = {bl/10:.3f} BL/cycle   ({bl*f/10:.3f} BL/s)")
    print("   Cheney 2013: 3.5-4.0 BL in 10 cycles = 0.35-0.40 BL/cycle")
