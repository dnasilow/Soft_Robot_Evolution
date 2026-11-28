"""Does a run of an E arm begin with the same robots as arm D's run of the same seed?
(PROTOCOL.md, section 9.8, point 9.)

Seeds 1 to 3 are seeds of arm D and of each of the arms E1 to E3. A run of the search takes its
first population from its seed; if the engine's options have no part in that, the run of an E arm
and arm D's run of that seed begin with the same thirty bodies and differ by what the changed
setting does from the first evaluation on.

Checked here on seed 101, the seed of no arm, with runs of ONE generation (the first population,
evaluated and stored) under the engine options of all four arms as the launcher has them: small
runs, workspace 5 and population 6, one robot at a time. The stored bodies are compared with
those of the run under arm D's options, and the scores too.

usage, from the project folder:
    python paper/diagnostics_2026-11-27/arms_E/check_first_population.py
Runs that are complete already are not made again; they are kept in
results/diagnostics_2026-11-27/arms_E/. Written next to this file: first_population.json.
"""
import json
import os
import pickle
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)                                          # the stored populations hold objects of src/
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
import search_arm                                                 # noqa: E402

WORK = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'arms_E')
SEED = 101
SMALL = ['--pop', '6', '--grid-size', '5']


def first_population(arm):
    run = f'first{arm}_s{SEED}'
    stored = os.path.join(WORK, 'results', run, 'final_population.pkl')
    if not os.path.isfile(stored):
        os.makedirs(WORK, exist_ok=True)
        words = list(search_arm.ARMS[arm]['runner'])
        command = ([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py')] + words[:words.index('--pop')] + SMALL
                   + ['--gen', '1', '--workers', '1', '--seed', str(SEED), '--name', run])
        r = subprocess.run(command, cwd=WORK, env=search_arm.run_environment(), capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            raise SystemExit(f'The run with the options of arm {arm} ended with code {r.returncode}:\n'
                             + r.stdout[-1500:] + r.stderr[-1500:])
    with open(stored, 'rb') as f:
        return pickle.load(f)


def main():
    base = first_population('D')
    voxels = [int((np.asarray(g) != 0).sum()) for g in base['genomes']]
    out = {'seed': SEED, 'small': SMALL, 'robots': len(voxels), 'voxels_of_each': voxels, 'arms': {}}
    print(f"first population under arm D's options, seed {SEED}: {len(voxels)} robots of {voxels} voxels")
    good = True
    for arm in ('E1', 'E2', 'E3'):
        mine = first_population(arm)
        same_bodies = len(mine['genomes']) == len(base['genomes']) and all(
            np.array_equal(np.asarray(a), np.asarray(b)) for a, b in zip(mine['genomes'], base['genomes']))
        same_scores = int(sum(float(a) == float(b) for a, b in zip(mine['fitnesses'], base['fitnesses'])))
        good = good and same_bodies
        out['arms'][arm] = {'the_same_bodies_in_the_same_order': bool(same_bodies), 'robots_with_the_same_score': same_scores}
        print(f"arm {arm}'s options: the same bodies in the same order: {'yes' if same_bodies else 'NO'}; robots with the "
              f"same score as under arm D's options: {same_scores} of {len(voxels)}")
    out['every_arm_begins_with_the_population_of_arm_D'] = bool(good)
    with open(os.path.join(HERE, 'first_population.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
