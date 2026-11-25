"""After the 2013 floor rule and start were built into the engine (--preset cheney2013-floor):
do the engine's own evaluator and the new preset give the champions the scores the emulation
gave them in the floor test (floor_champions.json, 'rule2013_placed')? And does the old preset
still give the scores of the transfer outcome (paper/outcomes/transfer.json)?

usage, from the checkout that holds the new code:
    python paper/diagnostics_2026-11-25/check_built_in_floor.py [--data C:/SoftRobotEvolution] [--workers 6]

--data: the folder whose results/ and research_reference/ hold the champions (the campaign's own
folder; this script may run from another checkout of the code). Every evaluation goes through
the search's evaluation (mujoco_tendon_evaluator._eval_worker) with the arguments read from the
preset, with the early stop off, as in the transfer outcome. Finished evaluations are kept in <data>/results/transfer/, so a run that is
stopped can be started again without loss.
Written next to this file: built_in_floor_check.json.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))

import analyse_arm as aa                                      # noqa: E402
import transfer_scores as ts                                  # noqa: E402

OLD_SAMPLE = 3          # champions per set re-scored under the old preset


def one(job):
    """One body through the search's own worker function."""
    name, grid, params = job
    import gc
    from src.evolution import mujoco_tendon_evaluator as evaluation
    started = time.time()
    try:
        score = float(evaluation._eval_worker((np.asarray(grid), None, None, params)))
    finally:
        gc.collect()
    return name, score, round(time.time() - started, 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--data', default=ROOT)
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args(argv)
    data = os.path.abspath(a.data)
    reruns = os.path.join(data, 'results', 'rerun2013')
    deposit = os.path.join(data, 'research_reference', 'extracted', 'dryad_gen1000')
    outcomes = os.path.join(ROOT, 'paper', 'outcomes')
    robots = (ts.arm_champions('R', reruns, outcomes) + ts.deposited_champions('noCost', deposit)
              + ts.arm_champions('Rc', reruns, outcomes) + ts.deposited_champions('costNumActuated', deposit))
    with open(os.path.join(HERE, 'floor_champions.json'), encoding='utf-8') as f:
        emulated = {(r['set'], r['label']): r['rule2013_placed']['score'] for r in json.load(f)['robots']}
    with open(os.path.join(outcomes, 'transfer.json'), encoding='utf-8') as f:
        transfer = {(r['set'], r['label']): r['score'] for r in json.load(f)['champions']}

    new = ts.worker_parameters(ts.evaluator_arguments(preset='cheney2013-floor'))
    old = ts.worker_parameters(ts.evaluator_arguments())
    jobs = [(('new', r['set'], r['label']), r['grid'], new) for r in robots]
    for name in dict.fromkeys(r['set'] for r in robots):
        jobs += [(('old', r['set'], r['label']), r['grid'], old) for r in [x for x in robots if x['set'] == name][:OLD_SAMPLE]]
    kept_path = os.path.join(data, 'results', 'transfer', 'built_in_floor_check_progress.json')
    kept = ts.read_cache(kept_path)
    results = {name: kept['/'.join(name)] for name, _, _ in jobs if '/'.join(name) in kept}
    jobs = [j for j in jobs if j[0] not in results]
    print(f'{len(results)} evaluations already done, {len(jobs)} to do.', flush=True)
    if jobs:
        workers = ts.workers_that_fit(a.workers)
        print(f'{workers} worker processes.', flush=True)
        from multiprocessing import Pool
        started = time.time()
        with Pool(workers, maxtasksperchild=8) as pool:
            for i, (name, score, seconds) in enumerate(pool.imap_unordered(one, jobs, chunksize=1), 1):
                if score == 0.0:                          # the search's worker turns any failure into a zero
                    raise SystemExit(f'{name}: the evaluation failed (score 0). What was finished is kept.')
                results[name] = kept['/'.join(name)] = score
                ts.write_cache(kept_path, kept)
                if i % 10 == 0 or i == len(jobs):
                    print(f'  {i}/{len(jobs)}  ({(time.time() - started) / 60:.1f} min so far)', flush=True)

    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'code': aa.code_version(), 'rows': []}
    for which, reference, label in (('new', emulated, 'preset cheney2013-floor against the emulation of the floor test'),
                                    ('old', transfer, 'preset cheney2013 against the transfer outcome')):
        rows = [(k[1], k[2], v, reference[(k[1], k[2])]) for k, v in results.items() if k[0] == which]
        differences = [abs(v - ref) for _, _, v, ref in rows]
        same = sum(d == 0.0 for d in differences)
        print(f'{label}: {same} of {len(rows)} scores identical; largest difference {max(differences):.3e}')
        report[which] = {'what': label, 'compared': len(rows), 'identical': int(same), 'largest_difference': float(max(differences))}
        report['rows'] += [{'preset': which, 'set': s, 'label': lab, 'score': v, 'reference': ref} for s, lab, v, ref in rows]
    with open(os.path.join(HERE, 'built_in_floor_check.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return 0 if all(report[w]['identical'] == report[w]['compared'] for w in ('new', 'old')) else 1


if __name__ == '__main__':
    sys.exit(main())
