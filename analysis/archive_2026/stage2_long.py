"""Why does the stage-2 champion score 0 after 40 cycles of walking when its first 30 cycles are
steady (2.27 / 4.45 / 6.21 BL)? Tracks it cycle by cycle for 60 cycles: forward position, COM
height, uprightness, divergence. Same for the same body on its material gait, and for the other
top-5 stage-2 bodies, so 'the gait dies' vs 'the body tips' vs 'numerics' can be told apart.
"""
import os, sys, pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
NCYC = 60


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
    z = x0[:, 2]
    lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
    ix = float(e.get_position()[0])
    n1 = int(0.025 / e.default_timestep)              # steps per actuation cycle
    rows = []
    for cyc in range(1, NCYC + 1):
        up = 1.0
        for _ in range(n1):
            e.step()
        p = e.data.xpos[1:nb]
        v = p[hi].mean(0) - p[lo].mean(0)
        up = float(v[2] / (np.linalg.norm(v) + 1e-12))
        pos = e.get_position()
        rows.append((cyc, (float(pos[0]) - ix) / bl, float(pos[1] - x0[:, 1].mean()) / bl,
                     float(pos[2]) * 1e3, up, bool(e.diverged())))
        if e.diverged():
            break
    return name, rows


def main():
    best = pickle.load(open('results/beamstage2_s1/best_robot.pkl', 'rb'))
    arc = pickle.load(open('results/beamstage2_s1/archive.pkl', 'rb'))['archive']
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:5]
    jobs = [('champ evolved', np.asarray(best['genome']), best['cppn'].phase_cppn),
            ('champ material', np.asarray(best['genome']), None)]
    jobs += [(f'#{i + 1} evolved', np.asarray(e['genome']), e['cppn'].phase_cppn)
             for i, e in enumerate(top[1:], 1)]
    fix = pickle.load(open('results/cheney_fix_s1/best_robot.pkl', 'rb'))
    jobs.append(('plateau 2.6118', np.asarray(fix['genome']), None))
    with Pool(len(jobs)) as p:
        out = dict(p.map(track, jobs))

    c = out['champ evolved']
    print("stage-2 champion, evolved gait - every 5th cycle (x, y in BL; z in mm)")
    print(f"{'cyc':>4}{'x BL':>8}{'y BL':>8}{'z mm':>7}{'upright':>9}{'div':>6}")
    for r in c:
        if r[0] % 5 == 0 or r[0] <= 2 or r[5]:
            print(f"{r[0]:>4}{r[1]:>8.3f}{r[2]:>8.3f}{r[3]:>7.1f}{r[4]:>9.2f}{str(r[5]):>6}")

    print("\nforward BL gained per 10-cycle window (window 1 = what fitness scores)")
    print(f"{'robot':<16}" + "".join(f"{f'w{w}':>8}" for w in range(1, 7)) + f"{'final up':>10}{'div':>6}")
    for name, rows in out.items():
        x = {r[0]: r[1] for r in rows}
        ws = []
        for w in range(1, 7):
            a, b = x.get(10 * (w - 1), 0.0), x.get(10 * w)
            ws.append('    -   ' if b is None else f"{b - a:>8.3f}")
        print(f"{name:<16}" + "".join(ws) + f"{rows[-1][4]:>10.2f}{str(rows[-1][5]):>6}")


if __name__ == '__main__':
    main()
