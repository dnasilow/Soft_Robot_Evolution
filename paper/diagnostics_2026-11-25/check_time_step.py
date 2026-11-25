"""Exploratory: how much do scores under the 2013 floor rule depend on the time step?

The rule stops a sliding voxel when the brake would stop it within one time step, so the time
step is part of the rule. The 2013 robot files say DtFrac 0.9 (the step is 0.9 of the largest
stable one); this project's engine uses 0.7. The 12 pilot robots of generation 10, which belong
to no arm, are scored under --preset cheney2013-floor with the engine's step (0.7), with the 2013
simulator's (0.9) and with half the engine's (0.35), and set against their scores in the 2013
simulator (floor_pilot.json).

usage, from the checkout that holds the new code:
    python paper/diagnostics_2026-11-25/check_time_step.py [--data C:/SoftRobotEvolution] [--workers 4]
        the 12 pilot robots at 0.9, 0.7 and 0.35; written next to this file: time_step_check.json
    python paper/diagnostics_2026-11-25/check_time_step.py --champions [--data ...] [--workers 4]
        the 140 champions of the transfer outcome at 0.9, set against their scores at 0.7 (the
        floor test's, floor_champions.json) and in the 2013 simulator; written next to this
        file: time_step_champions.json. Finished evaluations are kept in <data>/results/transfer/.
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

import protocol_stats as ps                                   # noqa: E402
import transfer_scores as ts                                  # noqa: E402

FRACTIONS = (0.9, 0.7, 0.35)


def one(job):
    name, grid, params, fraction = job
    import gc
    from src.evolution import mujoco_tendon_evaluator as evaluation
    started = time.time()
    engine = evaluation._make_engine(params)
    engine.dt_frac = fraction                                 # the share of the largest stable step
    try:
        engine.load_robot(np.asarray(grid), voxel_size=params['voxel_size'],
                          initial_height=evaluation._start_height(np.asarray(grid), params), gait_params=None)
        score = float(engine.get_fitness(simulation_time=params['simulation_time'], settle_time=params['settle_time'],
                                         return_descriptors=False, **evaluation._fitness_kw(params)))
        return name, fraction, score, bool(engine.diverged()), float(engine.default_timestep), round(time.time() - started, 1)
    finally:
        del engine
        gc.collect()


def champions(a):
    """The 140 champions at DtFrac 0.9 against 0.7 (the floor test) and the 2013 simulator."""
    data = os.path.abspath(a.data)
    reruns = os.path.join(data, 'results', 'rerun2013')
    deposit = os.path.join(data, 'research_reference', 'extracted', 'dryad_gen1000')
    outcomes = os.path.join(ROOT, 'paper', 'outcomes')
    robots = (ts.arm_champions('R', reruns, outcomes) + ts.deposited_champions('noCost', deposit)
              + ts.arm_champions('Rc', reruns, outcomes) + ts.deposited_champions('costNumActuated', deposit))
    with open(os.path.join(HERE, 'floor_champions.json'), encoding='utf-8') as f:
        at_07 = {(r['set'], r['label']): r['rule2013_placed'] for r in json.load(f)['robots']}
    params = ts.worker_parameters(ts.evaluator_arguments(preset='cheney2013-floor'))
    kept_path = os.path.join(data, 'results', 'transfer', 'time_step_champions_progress.json')
    kept = ts.read_cache(kept_path)
    jobs = [(f"{r['set']}/{r['label']}", r['grid'], params, 0.9) for r in robots if f"{r['set']}/{r['label']}" not in kept]
    print(f'{len(robots) - len(jobs)} evaluations already done, {len(jobs)} to do.', flush=True)
    if jobs:
        workers = ts.workers_that_fit(a.workers)
        print(f'{workers} worker processes.', flush=True)
        from multiprocessing import Pool
        started = time.time()
        with Pool(workers, maxtasksperchild=8) as pool:
            for i, (name, fraction, score, blew_up, step, seconds) in enumerate(pool.imap_unordered(one, jobs, chunksize=1), 1):
                kept[name] = {'score': score, 'blew_up': blew_up, 'time_step': step, 'seconds': seconds}
                ts.write_cache(kept_path, kept)
                if i % 10 == 0 or i == len(jobs):
                    print(f'  {i}/{len(jobs)}  ({(time.time() - started) / 60:.1f} min so far)', flush=True)
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'sets': {}, 'robots': []}
    print(f"{'set':<30} {'DtFrac':>6}  {'blew up':>7}  {'share of the 2013 score':>24}  {'off by':>18}  {'within 20%':>10}  "
          f"{'rank agreement (95%)':>22}")
    for name in dict.fromkeys(r['set'] for r in robots):
        rows = [r for r in robots if r['set'] == name]
        evolved = np.array([r['evolved'] for r in rows])
        at_09 = [kept[f"{r['set']}/{r['label']}"] for r in rows]
        before = [at_07[(r['set'], r['label'])] for r in rows]
        block = {}
        for fraction, results in ((0.9, at_09), (0.7, before)):
            scores = np.array([x['score'] for x in results])
            ratio = scores / evolved
            rho, lo, hi = ps.rank_correlation(evolved, scores)
            q, e = ps.quartiles(ratio), ps.quartiles(np.abs(ratio - 1))
            blew = int(sum(bool(x['blew_up']) for x in results))
            block[str(fraction)] = {'blew_up': blew, 'ratio': list(q), 'error': list(e),
                                    'within_20_percent': int((np.abs(ratio - 1) <= 0.2).sum()),
                                    'rank_agreement': rho, 'rank_agreement_interval': [lo, hi]}
            print(f"{ts.set_title(name):<30} {fraction:>6}  {blew:>7}  {q[0]:>8.2f} ({q[1]:.2f}-{q[2]:.2f})  "
                  f"{e[0]:>6.2f} ({e[1]:.2f}-{e[2]:.2f})  {int((np.abs(ratio - 1) <= 0.2).sum()):>7} of {len(rows)}  "
                  f"{rho:>+6.2f} ({lo:+.2f} to {hi:+.2f})")
        error_09 = np.abs(np.array([x['score'] for x in at_09]) / evolved - 1)
        error_07 = np.abs(np.array([x['score'] for x in before]) / evolved - 1)
        block['closer_at_0.9'] = int((error_09 < error_07).sum())
        print(f"{'':<30} closer to its 2013 score at 0.9 than at 0.7: {block['closer_at_0.9']} of {len(rows)}")
        report['sets'][name] = block
    for r in robots:
        report['robots'].append({'set': r['set'], 'label': r['label'], 'evolved': r['evolved'],
                                 '0.9': kept[f"{r['set']}/{r['label']}"], '0.7': at_07[(r['set'], r['label'])]['score']})
    with open(os.path.join(HERE, 'time_step_champions.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--data', default=ROOT)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--champions', action='store_true')
    a = ap.parse_args(argv)
    if a.champions:
        return champions(a)
    robots = ts.rehearsal_champions('pilot10_P0_s', 10, os.path.join(os.path.abspath(a.data), 'results', 'rerun2013'))
    with open(os.path.join(HERE, 'floor_pilot.json'), encoding='utf-8') as f:
        pilot = {r['label']: r for r in json.load(f)['robots']}
    params = ts.worker_parameters(ts.evaluator_arguments(preset='cheney2013-floor'))
    jobs = [(r['label'], r['grid'], params, fraction) for fraction in FRACTIONS for r in robots]
    workers = ts.workers_that_fit(a.workers)
    print(f'{len(jobs)} evaluations with {workers} worker processes.', flush=True)
    from multiprocessing import Pool
    results = {}
    with Pool(workers, maxtasksperchild=8) as pool:
        for name, fraction, score, blew_up, step, seconds in pool.imap_unordered(one, jobs, chunksize=1):
            results[(name, fraction)] = {'score': score, 'blew_up': blew_up, 'time_step': step, 'seconds': seconds}
    in_2013 = np.array([pilot[r['label']]['simulator_2013']['score'] for r in robots])
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'fractions': {}, 'robots': []}
    print(f"{'DtFrac':>7}  {'blew up':>7}  {'share of the 2013 score':>24}  {'off by':>18}  {'within 20%':>10}  {'rank agreement (95%)':>22}")
    for fraction in FRACTIONS:
        scores = np.array([results[(r['label'], fraction)]['score'] for r in robots])
        ratio = scores / in_2013
        rho, lo, hi = ps.rank_correlation(in_2013, scores)
        q, e = ps.quartiles(ratio), ps.quartiles(np.abs(ratio - 1))
        report['fractions'][str(fraction)] = {
            'blew_up': int(sum(results[(r['label'], fraction)]['blew_up'] for r in robots)), 'ratio': list(q), 'error': list(e),
            'within_20_percent': int((np.abs(ratio - 1) <= 0.2).sum()), 'rank_agreement': rho, 'rank_agreement_interval': [lo, hi]}
        print(f"{fraction:>7}  {report['fractions'][str(fraction)]['blew_up']:>7}  {q[0]:>8.2f} ({q[1]:.2f}-{q[2]:.2f})  "
              f"{e[0]:>6.2f} ({e[1]:.2f}-{e[2]:.2f})  {int((np.abs(ratio - 1) <= 0.2).sum()):>7} of {len(robots)}  "
              f"{rho:>+6.2f} ({lo:+.2f} to {hi:+.2f})")
    same = [abs(results[(r['label'], 0.7)]['score'] - pilot[r['label']]['rule2013']['score']) for r in robots]
    print(f"With the engine's own step the built-in rule repeats the emulation's pilot scores: {sum(d == 0.0 for d in same)} of "
          f"{len(same)} identical, largest difference {max(same):.2e}")
    report['engine_step_repeats_the_emulation'] = {'identical': int(sum(d == 0.0 for d in same)), 'compared': len(same),
                                                  'largest_difference': float(max(same))}
    for r in robots:
        report['robots'].append({'label': r['label'], 'simulator_2013': float(pilot[r['label']]['simulator_2013']['score']),
                                 **{str(f): results[(r['label'], f)] for f in FRACTIONS}})
    with open(os.path.join(HERE, 'time_step_check.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
