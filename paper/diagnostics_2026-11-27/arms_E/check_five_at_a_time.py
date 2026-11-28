"""Is a run of arm E2's command the same run with five robots at a time as with three?

Arm E2's robots take about twice as long to simulate as those of the other arms (with the
volumetric law the engine's time step is shorter), so the launcher starts its runs with five
robots at a time (--workers 5) where the others have three. The number of robots simulated at a
time is machine time and must change no score.

Two runs of the launcher's trial of 27 November 2026 are compared, both of seed 101 (the seed of
no arm), two generations, population 30, with arm E2's options:
    trialE2_s101   three robots at a time; made with
                   python paper/reference_2013/start_arm.py --arm E2 --tag trialE2 --seeds 101-103 --gens 2 --workers 3 --here
    trialW_s101    five robots at a time; made with
                   python paper/reference_2013/start_arm.py --arm E2 --tag trialW --seeds 101 --gens 2 --workers 5 --here
Compared: every score of both generations, and the bodies and scores of the final population.

usage, from the project folder (the two runs must be in results/):
    python paper/diagnostics_2026-11-27/arms_E/check_five_at_a_time.py
Written next to this file: five_at_a_time.json.
"""
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)                                          # the stored populations hold objects of src/
RESULTS = os.path.join(ROOT, 'results')
THREE, FIVE = 'trialE2_s101', 'trialW_s101'
GENERATIONS = 2


def run(name):
    folder = os.path.join(RESULTS, name)
    with open(os.path.join(folder, 'manifest.json'), encoding='utf-8') as f:
        starts = json.load(f)['invocations']
    scores = []
    for g in range(1, GENERATIONS + 1):
        with open(os.path.join(folder, f'gen_{g:03d}.json'), encoding='utf-8') as f:
            scores.append([float(v) for v in json.load(f)['fitnesses']])
    with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
        population = pickle.load(f)
    return starts, scores, population


def main():
    (starts3, scores3, final3), (starts5, scores5, final5) = run(THREE), run(FIVE)
    same_settings = {k: v for k, v in starts3[0]['settings'].items() if k not in ('name', 'workers')} == \
                    {k: v for k, v in starts5[0]['settings'].items() if k not in ('name', 'workers')}
    total = sum(len(g) for g in scores3)
    same = sum(a == b for g3, g5 in zip(scores3, scores5) for a, b in zip(g3, g5))
    bodies = int(sum(np.array_equal(np.asarray(a), np.asarray(b)) for a, b in zip(final3['genomes'], final5['genomes'])))
    fitnesses = int(sum(float(a) == float(b) for a, b in zip(final3['fitnesses'], final5['fitnesses'])))
    good = (same_settings and same == total and [len(g) for g in scores3] == [len(g) for g in scores5]
            and bodies == len(final3['genomes']) == len(final5['genomes']) and fitnesses == len(final3['fitnesses']))
    out = {'runs': {THREE: {'robots_at_a_time': [s['settings']['workers'] for s in starts3], 'command': starts3[0]['command']},
                    FIVE: {'robots_at_a_time': [s['settings']['workers'] for s in starts5], 'command': starts5[0]['command']}},
           'the_same_settings_but_for_the_number_at_a_time': bool(same_settings),
           'scores': {'compared': total, 'identical_to_the_last_digit': int(same)},
           'final_population': {'robots': len(final3['genomes']), 'the_same_bodies': bodies, 'the_same_scores': fitnesses},
           'the_same_run': bool(good)}
    print(f"{THREE}: {out['runs'][THREE]['robots_at_a_time']} robots at a time; {FIVE}: {out['runs'][FIVE]['robots_at_a_time']}")
    print(f"the same settings but for that number: {'yes' if same_settings else 'NO'}")
    print(f'scores of the two generations: {same} of {total} identical to the last digit')
    print(f"final population: {bodies} of {len(final3['genomes'])} bodies the same, {fitnesses} of "
          f"{len(final3['fitnesses'])} scores the same")
    with open(os.path.join(HERE, 'five_at_a_time.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
