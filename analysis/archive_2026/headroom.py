"""Why did 313 generations return the identical robot - physics ceiling, or search limitation?

Diversity did not collapse (30/30 distinct genomes, distinct-fitness count steady), so the search was
still working. The remaining suspect is that the two gait parameters are FIXED GLOBALS evolution
cannot touch: actuation frequency (40 Hz) and amplitude (+-20%). If the champion body goes markedly
faster at some other frequency or amplitude, that is headroom the search was structurally unable to
reach - a setup limitation, not a physics ceiling.

Scored the way the run scored it: 10 cycles at whatever frequency is being tested, no settle.
"""
import os
import sys
import pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT)
os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
FREQS = (20.0, 30.0, 40.0, 50.0, 60.0, 80.0)
AMPS = (0.10, 0.14, 0.20, 0.28)


def job(a):
    kind, freq, amp = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open('results/cheney_fix600_s1/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, actuation_frequency=freq,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact='voxelyze')
    e.load_robot(g)
    nb, r = e.model.nbody, e.voxel_size / 2
    cycles = 10.0 / freq                                   # always 10 actuation cycles
    f = float(e.get_fitness(cycles, 0.0, early_term_threshold=-1e9))
    pen = 0.0
    e2 = MuJoCoBeamPhysics(actuation_amplitude=amp, actuation_frequency=freq,
                           fitness_mode='forward', friction=SS, materials='cheney2013',
                           floor_contact='voxelyze')
    e2.load_robot(g)
    for _ in range(int(cycles / e2.default_timestep)):
        e2.step()
        pen = max(pen, (r - float(e2.data.xpos[1:nb, 2].min())) / e2.voxel_size)
    return kind, freq, amp, f, pen, e2.diverged()


def main():
    jobs = [('freq', f, 0.20) for f in FREQS] + [('amp', 40.0, a) for a in AMPS]
    with Pool(10) as p:
        out = p.map(job, jobs)
    res = {(k, f, a): (fit, pen, dv) for k, f, a, fit, pen, dv in out}
    base = res[('freq', 40.0, 0.20)][0]
    print("champion of cheney_fix600_s1, 10 cycles, evolved at 40 Hz and +-20%\n")
    print(f"{'frequency':>11}{'BL / 10 cycles':>16}{'vs evolved':>12}{'penetration':>13}{'blew up':>9}")
    for f in FREQS:
        fit, pen, dv = res[('freq', f, 0.20)]
        mark = '  <- evolved here' if f == 40.0 else ''
        print(f"{f:>9.0f}Hz{fit:>16.4f}{fit/base:>11.2f}x{pen:>13.2f}{str(dv):>9}{mark}")
    print(f"\n{'amplitude':>11}{'BL / 10 cycles':>16}{'vs evolved':>12}{'penetration':>13}{'blew up':>9}")
    for a in AMPS:
        fit, pen, dv = res[('amp', 40.0, a)]
        mark = '  <- evolved here' if a == 0.20 else ''
        print(f"{a:>10.2f} {fit:>15.4f}{fit/base:>11.2f}x{pen:>13.2f}{str(dv):>9}{mark}")
    bf = max(FREQS, key=lambda f: res[('freq', f, 0.20)][0])
    ba = max(AMPS, key=lambda a: res[('amp', 40.0, a)][0])
    print(f"\n  best frequency {bf:.0f} Hz ({res[('freq', bf, 0.20)][0]:.4f} BL), "
          f"best amplitude {ba:.2f} ({res[('amp', 40.0, ba)][0]:.4f} BL)")
    print("  If either beats the evolved setting by a lot, the ceiling is a FIXED-PARAMETER")
    print("  limitation (evolution cannot tune the gait), not the physics.")


if __name__ == '__main__':
    main()
