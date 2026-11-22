import os, sys, pickle, time
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
def job(kw):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open('results/cheney_fix_s1/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze', **kw)
    e.load_robot(g)
    t = time.time()
    f = float(e.get_fitness(0.25, 0.0, early_term_threshold=0.02, early_term_fraction=0.5))
    return kw, f, time.time() - t
if __name__ == '__main__':
    with Pool(2) as p:
        for kw, f, t in p.map(job, [{}, dict(direction='any', divide_by='workspace', workspace_voxels=10)]):
            print(kw, repr(f), f"{f:.4f}", f"{t:.0f}s")
