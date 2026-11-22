"""Preview Cheney's score on robots we already have, before building it into evolution.

Cheney 2013 (paper §3.4 + HCUBE_SoftbotsExperiment.cpp): fitness = |COM_end - COM_start| (3D vector
length, Voxelyze's FinalCOM_Dist) / (BoundingBoxLength x VoxelSize) = a FIXED 10-voxel width.
For each robot, over 10 cycles: our +X BL, his 3D score, a horizontal-only variant, and how much
of his score is vertical (sag / toppling). Also tracks XY paths for 60 cycles and plots them.
"""
import os, sys, pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
W = 10                                              # workspace width in voxels


def track(a):
    name, g, net = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze',
                          phase_mode='offset')
    e.load_robot(g, gait_params=net)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    c0 = np.array(e.get_position(), float)
    n1 = int(0.025 / e.default_timestep)
    path = [c0.copy()]
    for cyc in range(60):
        for _ in range(n1):
            e.step()
        path.append(np.array(e.get_position(), float))
    return name, dict(path=np.array(path), bl=bl, vs=e.voxel_size, div=e.diverged())


def main():
    s2 = 'results/beamstage2_s1'
    best = pickle.load(open(f'{s2}/best_robot.pkl', 'rb'))
    r3 = pickle.load(open(f'{s2}/rank3.pkl', 'rb'))
    r5 = pickle.load(open(f'{s2}/rank5.pkl', 'rb'))
    fix = pickle.load(open('results/cheney_fix_s1/best_robot.pkl', 'rb'))
    jobs = [('stage-2 champion', best['genome'], best['cppn'].phase_cppn),
            ('stage-2 #3', r3['genome'], r3['cppn'].phase_cppn),
            ('stage-2 #5', r5['genome'], r5['cppn'].phase_cppn),
            ('plateau record', fix['genome'], None)]
    jobs = [(n, np.asarray(g), net) for n, g, net in jobs]
    with Pool(len(jobs)) as p:
        out = dict(p.map(track, jobs))

    print("10 cycles, each robot scored three ways")
    print(f"{'robot':<18}{'our +X BL':>10}{'Cheney 3D':>11}{'horiz only':>12}{'vertical part':>15}"
          f"{'60-cyc Cheney 3D':>18}")
    for n, d in out.items():
        p, ws = d['path'], W * d['vs']
        dx = (p[10] - p[0])
        bl_x = dx[0] / d['bl']
        ch3 = np.linalg.norm(dx) / ws
        chh = np.linalg.norm(dx[:2]) / ws
        print(f"{n:<18}{bl_x:>10.4f}{ch3:>11.4f}{chh:>12.4f}{abs(dx[2]) / ws:>15.4f}"
              f"{np.linalg.norm(p[60] - p[0]) / ws:>18.4f}{'  DIVERGED' if d['div'] else ''}")

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 6))
    for (n, d), col in zip(out.items(), ('#d62728', '#1f77b4', '#2ca02c', '#7f7f7f')):
        p = (d['path'] - d['path'][0]) / (W * d['vs'])
        ax.plot(p[:, 0], p[:, 1], '-', color=col, lw=2, label=n)
        ax.plot(p[10, 0], p[10, 1], 'o', color=col, ms=7)
        ax.plot(p[-1, 0], p[-1, 1], 's', color=col, ms=6)
    ax.plot([], [], 'ko', label='end of the 10 scored cycles')
    ax.plot([], [], 'ks', label='cycle 60')
    ax.set_xlabel('x (workspace widths = 10 voxels)')
    ax.set_ylabel('y (workspace widths)')
    ax.set_title('Top-down paths over 60 cycles (start at origin)')
    ax.axis('equal'); ax.grid(alpha=0.3); ax.legend(loc='best', fontsize=9)
    fig.tight_layout()
    fig.savefig(f'{s2}/paths_60cycles.png', dpi=110)
    print(f"\nsaved {s2}/paths_60cycles.png")


if __name__ == '__main__':
    main()
