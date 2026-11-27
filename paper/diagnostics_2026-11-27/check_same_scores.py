"""Does the code in this folder give every champion the score that is on record?

After the changes of 27 November 2026 (one linear-algebra thread per process; MuJoCo's working
memory stated; an evaluation that fails stops the run) every evaluation behind the two transfer
reports is computed again, from nothing, and compared with the report as it is committed in
paper/outcomes/ (transfer.json: --preset cheney2013; transfer_floor2013.json: --preset
cheney2013-floor). That is every champion of arms R, Rc and A and of the deposit under each
preset, the champions that do not touch the bottom once more from their height, and the
time-step check (25 champions under each preset at a quarter of the time step).

The recorded scores were computed with the code tagged campaign-v2 and campaign-v3, with the
libraries' default number of threads and with the memory MuJoCo sets aside by itself.

Recorded with each evaluation: how much of the stated memory it used at most.

usage, from the project folder:
    python paper/diagnostics_2026-11-27/check_same_scores.py [--workers 16]
Finished evaluations are kept in results/diagnostics_2026-11-27/evaluations.json (never in the
store of the transfer outcome), so a run that is stopped loses nothing.
Written next to this file: same_scores.json.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))

import transfer_scores as ts                                  # noqa: E402  (sets one thread before numpy is loaded)
import analyse_arm as aa                                      # noqa: E402

CACHE = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'evaluations.json')
ARMS = ('R', 'Rc', 'A')
REPORTS = ((ts.PRESET, 'transfer.json'), (ts.FLOOR_PRESET, 'transfer_floor2013.json'))


def score_and_memory(job):
    """ts.score_one, with what the evaluation used of the memory stated to MuJoCo."""
    from src.evolution import mujoco_tendon_evaluator as evaluation
    made, real = [], evaluation._make_engine

    def make(params):
        made.append(real(params))
        return made[-1]

    evaluation._make_engine = make
    try:
        out = ts.score_one(job)
    finally:
        evaluation._make_engine = real
    engine = made[-1]
    out['memory_stated'] = int(engine.model.narena)
    out['memory_used'] = int(engine.data.maxuse_arena)        # MuJoCo forgets it when a simulation blows up
    out['contacts_most'] = int(engine.data.maxuse_con)
    out['voxels'] = len(engine.cells)
    return out


def recorded_scores(report):
    """{(set, label, which): score} of a committed transfer report."""
    out = {}
    for row in report['champions']:
        out[(row['set'], row['label'], 'floor')] = (row['score'], row['blew_up'])
        if 'quarter' in row:
            out[(row['set'], row['label'], 'short')] = (row['quarter']['score'], row['quarter']['blew_up'])
        if 'placed' in row:
            out[(row['set'], row['label'], 'placed')] = (row['placed']['score'], row['placed']['blew_up'])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--workers', type=int, default=16)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    sets = {}
    for arm in ARMS:
        sets[f'arm_{arm}'] = ts.arm_champions(arm)
        reference = f"deposit_{aa.ARMS[arm]['condition']}"
        if reference not in sets:
            sets[reference] = ts.deposited_champions(aa.ARMS[arm]['condition'])
    summary = {'made': None, 'code': aa.code_version(), 'threads': {k: os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS',
               'OMP_NUM_THREADS', 'MKL_NUM_THREADS')}, 'presets': {}, 'different': []}

    from run_tendon_evolution import _prevent_sleep
    awake = _prevent_sleep()
    try:
        for preset, file_name in REPORTS:
            with open(os.path.join(aa.OUTCOMES, file_name), encoding='utf-8') as f:
                committed = json.load(f)
            record = recorded_scores(committed)
            params = ts.worker_parameters(ts.evaluator_arguments(preset=preset))
            jobs, keys = ts.plan(sets, params, 'the code of 27 November 2026, before its tag')
            if set(keys) != set(record):
                raise SystemExit(f'{file_name} does not hold the evaluations this script plans: '
                                 f'{len(set(keys) ^ set(record))} differ.')
            print(f'\n--preset {preset}: {len(jobs)} evaluations, against {file_name} (code {committed["code"]})', flush=True)
            results = ts.evaluate_all(jobs, max(1, a.workers), CACHE, evaluate=score_and_memory)
            rows = []
            for which_key, key in keys.items():
                r, (score, blew_up) = results[key], record[which_key]
                same = r['score'] == score and bool(r['blew_up']) == bool(blew_up)
                rows.append({'set': which_key[0], 'label': which_key[1], 'which': which_key[2], 'recorded': score,
                             'now': r['score'], 'same': same, 'blew_up': bool(r['blew_up']), 'error': r['error'],
                             'voxels': r['voxels'], 'memory_stated': r['memory_stated'],
                             'memory_used': r['memory_used'], 'contacts_most': r['contacts_most'],
                             'seconds': r['seconds']})
                if not same:
                    summary['different'].append(rows[-1])
            kinds = {}
            for row in rows:
                k = kinds.setdefault(row['which'], [0, 0])
                k[0] += row['same']
                k[1] += 1
            steady = [r for r in rows if not r['blew_up']]
            most = max(steady, key=lambda r: r['memory_used'] / r['memory_stated'])
            summary['presets'][preset] = {
                'report': file_name, 'report_code': committed['code'], 'evaluations': len(rows),
                'same': int(sum(r['same'] for r in rows)), 'by_kind': kinds,
                'blew_up': int(sum(r['blew_up'] for r in rows)), 'errors': int(sum(r['error'] is not None for r in rows)),
                'memory_stated_mb': [round(min(r['memory_stated'] for r in rows) / 2 ** 20, 1),
                                     round(max(r['memory_stated'] for r in rows) / 2 ** 20, 1)],
                'memory_used_most_mb': round(max(r['memory_used'] for r in steady) / 2 ** 20, 3),
                'largest_share_used': round(most['memory_used'] / most['memory_stated'], 4),
                'largest_share_used_by': [most['set'], most['label'], most['which'], most['voxels'], most['contacts_most']],
                'used_bytes_per_voxel_most': round(max(r['memory_used'] / r['voxels'] for r in steady)),
                'contacts_most': int(max(r['contacts_most'] for r in rows)),
                'rows': rows}
            p = summary['presets'][preset]
            print(f"  the recorded score to the last digit: {p['same']} of {p['evaluations']}  "
                  + ', '.join(f"{k}: {v[0]} of {v[1]}" for k, v in kinds.items()))
            print(f"  memory stated {p['memory_stated_mb'][0]} to {p['memory_stated_mb'][1]} MB; most used "
                  f"{p['memory_used_most_mb']} MB; largest share used {100 * p['largest_share_used']:.1f}%; "
                  f"most contacts at once {p['contacts_most']}")
    finally:
        awake()

    summary['made'] = time.strftime('%Y-%m-%dT%H:%M')
    with open(os.path.join(HERE, 'same_scores.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1)
    total = sum(p['evaluations'] for p in summary['presets'].values())
    same = sum(p['same'] for p in summary['presets'].values())
    print(f"\n{same} OF {total} EVALUATIONS GIVE THE RECORDED SCORE TO THE LAST DIGIT."
          + ('' if same == total else f" DIFFERENT: {len(summary['different'])}"))
    return 0 if same == total else 1


if __name__ == '__main__':
    sys.exit(main())
