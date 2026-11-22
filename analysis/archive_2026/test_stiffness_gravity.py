"""The cheapest test of the squat-vs-perched hypothesis.

Claim: our robots lie flat (footprint 94) while Cheney's perch (footprint 26) because our voxels
are 200x too soft, so a body collapses under its own weight. If that is right, then simply letting
the SAME bodies settle under Cheney's real stiffness and gravity should make them stand taller and
touch the floor on fewer voxels -- no evolution needed.

Settles each body (no actuation) and measures how it sits, then runs 10 cycles for the cost and
divergence numbers.
"""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def job(a):
    tag, mat, amp, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, fitness_mode='forward', friction=SS,
                          materials=mat)
    e.load_robot(g)
    nb = e.model.nbody
    p0 = np.array(e.data.xpos[1:nb])
    h0 = float(p0[:, 2].max() - p0[:, 2].min())          # undeformed height
    # settle with the muscles switched off, so this measures gravity alone
    amp_save = e.v_amp.copy(); e.v_amp[:] = 0.0
    for _ in range(int(0.5 / e.default_timestep)):
        e.step()
    p = np.array(e.data.xpos[1:nb])
    h1 = float(p[:, 2].max() - p[:, 2].min())
    r = e.voxel_size / 2
    touching = int((p[:, 2] < r * 1.25).sum())           # voxels resting on the floor
    e.v_amp[:] = amp_save
    t0 = time.time()
    f = float(e.get_fitness(1.0, 0.5, early_term_threshold=0.02, early_term_fraction=0.5))
    return tag, mat, h0, h1, touching, e.diverged(), e.default_timestep, f, time.time() - t0


if __name__ == '__main__':
    arc = pickle.load(open('results/cheney_vox_s1/archive.pkl', 'rb'))['archive']
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:4]
    bodies = {f'vox_s1 #{i+1}': e['genome'] for i, e in enumerate(top)}
    bodies['beam_s1 champ'] = pickle.load(open('results/cheney_beam_s1/best_robot.pkl', 'rb'))['genome']
    jobs = [(t, m, 0.2, g) for t, g in bodies.items() for m in ('evosoro', 'cheney2013')]
    with Pool(8) as p:
        out = p.map(job, jobs)
    res = {(t, m): r for t, m, *r in out}
    print(f"{'body':<15}{'materials':<12}{'height':>9}{'squash':>9}{'on floor':>10}"
          f"{'dt (us)':>9}{'10-cyc BL':>11}{'sim s':>8}{'blew up':>9}")
    for t in bodies:
        for m in ('evosoro', 'cheney2013'):
            h0, h1, touch, div, dt, f, secs = res[(t, m)]
            print(f"{t:<15}{m:<12}{h1*1e3:>8.1f}m{100*(1-h1/h0):>8.1f}%{touch:>10}"
                  f"{dt*1e6:>9.2f}{f:>11.4f}{secs:>8.0f}{str(div):>9}")
    print("\n  squash = how much of its own height the body loses just standing there.")
    print("  Cheney's bodies compress ~2.8% of their height under their own weight.")
    ev = np.mean([res[(t, 'evosoro')][6] for t in bodies])
    ch = np.mean([res[(t, 'cheney2013')][6] for t in bodies])
    print(f"  mean simulation cost per evaluation: evosoro {ev:.0f}s  ->  cheney2013 {ch:.0f}s "
          f"({ch/ev:.2f}x)")
