"""Isolate the volumetric-law divergence: which bodies, which amplitude, and does it need
gravity / the floor / self-collision?"""
import os, sys, pickle
import numpy as np
import mujoco
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
BODIES = {'floor_s1': 'results/cheney_floor_s1/best_robot.pkl',
          'beam_s1': 'results/cheney_beam_s1/best_robot.pkl'}


def job(a):
    name, amp, gravity, collide, pois = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open(BODIES[name], 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, fitness_mode='forward', poisson=pois,
                          dt_rule='ours')
    e.load_robot(g, initial_height=0.0 if gravity else 0.5)
    if not gravity:
        e.model.opt.gravity[:] = 0
    if not collide:
        e._collision_forces = lambda p, v, s: np.zeros((len(e.cells), 3))
    worst, blew = 0.0, None
    i, j = e.bi, e.bj
    for k in range(int(0.4 / e.default_timestep)):
        e.step()
        if k % 10 == 0:
            d = np.linalg.norm(e.data.xpos[1:][j] - e.data.xpos[1:][i], axis=1) / e.voxel_size
            worst = max(worst, float(np.abs(d - 1).max()))
            if blew is None and worst > 1.0:
                blew = e.current_time
    return a, worst, blew, int(e.data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number)


if __name__ == '__main__':
    jobs = [(n, amp, grav, col, pois)
            for n in BODIES for amp in (0.05, 0.1, 0.2) for grav, col in
            ((True, True), (False, True), (False, False)) for pois in (True, False)]
    with Pool(10) as p:
        res = p.map(job, jobs)
    print(f"{'body':>9}{'amp':>6}{'gravity':>9}{'collide':>9}{'poisson':>9}"
          f"{'worst |strain|':>16}{'runaway':>10}{'BADQACC':>9}")
    for (n, amp, grav, col, pois), worst, blew, w in res:
        print(f"{n:>9}{amp:>6.2f}{str(grav):>9}{str(col):>9}{str(pois):>9}{worst:>16.3f}"
              f"{('%.3f s' % blew) if blew else '      -':>10}{w:>9d}")
