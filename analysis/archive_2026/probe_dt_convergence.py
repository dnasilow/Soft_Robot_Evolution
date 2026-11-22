"""Is the volumetric blow-up numerical or structural? Run the same body with progressively
smaller time steps and report when the strains run away. Also runs a free (no gravity, no
actuation) block given a small initial stretch: with no energy source, growing strain can only
be the integrator."""
import os, sys, pickle
import numpy as np
import mujoco
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)


def champ_job(div):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open('results/cheney_floor_s1/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', poisson=True, dt_rule='ours')
    e.load_robot(g)
    e.default_timestep /= div
    e.model.opt.timestep = e.default_timestep
    worst, blew = 0.0, None
    n = int(0.3 / e.default_timestep)
    for k in range(n):
        e.step()
        if k % 10 == 0:
            i, j = e.bi, e.bj
            d = np.linalg.norm(e.data.xpos[1:][j] - e.data.xpos[1:][i], axis=1) / e.voxel_size
            worst = max(worst, float(np.abs(d - 1).max()))
            if blew is None and worst > 1.0:
                blew = e.current_time
    w = int(e.data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number)
    return div, e.default_timestep, worst, blew, w


def free_job(args):
    pois, div = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    cells = [(x, y, z) for x in range(4) for y in range(4) for z in range(4)]
    g = np.zeros((20, 20, 20), np.int8)
    for c in cells:
        g[c] = 3
    e = MuJoCoBeamPhysics(actuation_amplitude=0.0, fitness_mode='forward', poisson=pois, dt_rule='ours')
    e.load_robot(g, initial_height=0.5)
    e.model.opt.gravity[:] = 0
    e.default_timestep /= div
    e.model.opt.timestep = e.default_timestep
    q = e.data.qpos.reshape(len(e.cells), 7)
    q[:, 0] *= 1.02                                  # 2% stretch along x, then let it ring
    mujoco.mj_forward(e.model, e.data)
    i, j = e.bi, e.bj
    hist = []
    for k in range(int(0.5 / e.default_timestep)):
        e.step()
        if k % 20 == 0:
            d = np.linalg.norm(e.data.xpos[1:][j] - e.data.xpos[1:][i], axis=1) / e.voxel_size
            hist.append(float(np.abs(d - 1).max()))
    return pois, div, hist[:3], max(hist), hist[-1]


if __name__ == '__main__':
    with Pool(6) as p:
        print("cheney_floor_s1 champion, amp 0.2, volumetric law ON, 0.3 s:")
        print(f"  {'dt/':>5}{'dt (us)':>10}{'worst |strain|':>16}{'runaway at':>13}{'BADQACC':>9}")
        for div, dt, worst, blew, w in p.map(champ_job, [1, 2, 4, 8, 16]):
            print(f"  {div:>5}{dt*1e6:10.2f}{worst:16.3f}"
                  f"{('%.3f s' % blew) if blew else '        -':>13}{w:9d}")
        print("\nfree 4x4x4 block, no gravity, no muscles, 2% initial stretch, 0.5 s "
              "(strain must decay):")
        print(f"  {'poisson':>8}{'dt/':>5}{'first 3 samples':>34}{'max':>10}{'final':>10}")
        for pois, div, first, mx, fin in p.map(free_job, [(a, b) for a in (False, True) for b in (1, 4)]):
            print(f"  {str(pois):>8}{div:>5}   {['%.4f' % x for x in first]}{mx:>10.4f}{fin:>10.4f}")
