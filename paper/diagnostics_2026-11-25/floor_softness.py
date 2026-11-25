"""Exploratory (PROTOCOL.md, section 7): does the floor explain why champions evolved in the 2013
simulator lose their gait in the MuJoCo engine? What is compared, and what was fixed before any
champion was scored, is in README.md next to this file.

usage, from the project folder:
    python paper/diagnostics_2026-11-25/floor_softness.py --checks
        simple bodies (at rest, dropped, shaking) in the 2013 simulator and on every floor
    python paper/diagnostics_2026-11-25/floor_softness.py --pilot
        the 12 pilot robots of generation 10, which belong to no arm
    python paper/diagnostics_2026-11-25/floor_softness.py --champions
        the 140 champions of the transfer outcome

The engine's code is not changed: every floor is set up here, on the loaded engine, inside this
script's own processes. Finished evaluations are kept in results/transfer/.
"""
import argparse
import concurrent.futures
import hashlib
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
import render_champions as rc                                 # noqa: E402
import render_transfer as rt                                  # noqa: E402
import transfer_scores as ts                                  # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402

FLOORS = ('hard', 'matched', 'default', 'rule2013')
MATCHED_TIME_CONSTANT, MATCHED_IMPEDANCE = 0.0045, 0.99       # MuJoCo's contact as soft under load as the 2013 spring
# What a kept evaluation was computed with: change the name here whenever a floor's code or constants change.
FLOOR_ID = {'hard': 'hard', 'matched': f'matched-{MATCHED_TIME_CONSTANT}-{MATCHED_IMPEDANCE}', 'default': 'default',
            'rule2013': 'rule2013-1', 'rule2013_placed': 'rule2013-1-placed'}
# README, point 7: the 2013 rule with a body started where it is in the workspace. Only a body that
# does not touch the bottom differs from 'rule2013'; for the others that evaluation serves.
PLACED = 'rule2013_placed'
COL_DAMP, MU_STATIC, MU_DYNAMIC = 0.8, 1.0, 0.5               # ColDampingZ, uStatic, uDynamic of the 2013 robot files
EVERY = 0.0025                                                # seconds between recorded states
TIPPED = 90.0                                                 # degrees: a body that has turned further has tipped over
TEMPLATE = os.path.join(ROOT, 'src', 'evolution', 'voxelyze2013_template.vxa')
CACHE = os.path.join(ROOT, 'results', 'transfer', 'floor_evaluations.json')
VOXEL = c13.VOXEL_SIZE_2013


# --------------------------------------------------------------------------------------------
# the floors
# --------------------------------------------------------------------------------------------
def soften_contact(engine):
    """MuJoCo's own floor contact with a longer time constant and a constant impedance."""
    engine.model.pair_solref[:, 0] = MATCHED_TIME_CONSTANT
    engine.model.pair_solref[:, 1] = 1.0
    engine.model.pair_solimp[:, 0] = MATCHED_IMPEDANCE
    engine.model.pair_solimp[:, 1] = MATCHED_IMPEDANCE


def install_2013_floor(engine):
    """Replace the engine's floor by the rule of the 2013 simulator (CVXS_Voxel::CalcFloorEffect).

    MuJoCo's contact is switched off. At every step, after the engine has computed its own forces
    on each voxel (bonds, damping, self-collision), a voxel whose centre is lower than half its
    current size gets
      up:      E * size/2 * (size/2 - z)  -  ColDampingZ * 2 * m * sqrt(E * size / m) * vz
      along the floor, by the 2013 rule:
        not moving, and pulled with less than uStatic * N   -> held: horizontal force cancelled
        moving, and uDynamic * N * dt < m * speed           -> braked with uDynamic * N against its motion
        moving, but slower than that                        -> stopped dead: horizontal velocity set to
                                                               zero, horizontal force cancelled
    E, m and size are the engine's own (its 2013 materials, rescaled for its 10 mm voxels)."""
    import mujoco
    import src.physics.mujoco_beam_physics as beam
    n, length, mass = len(engine.cells), float(engine.voxel_size), float(engine._m)
    modulus = np.array([beam.e_scaled(int(v), engine.materials, length) for v in engine.mats])
    engine.model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
    dof = np.asarray(engine.model.jnt_dofadr[:n])
    engine_forces = engine.forces

    def forces(strain):
        force, torque = engine_forces(strain)
        data = engine.data
        z = data.xpos[1:, 2]
        size = length * (1.0 + strain)
        k = np.where(z < size / 2)[0]
        if not len(k):
            return force, torque
        vx, vy, vz = data.qvel[dof[k]], data.qvel[dof[k] + 1], data.qvel[dof[k] + 2]
        normal = modulus[k] * size[k] / 2 * (size[k] / 2 - z[k])
        pull = np.hypot(force[k, 0], force[k, 1])             # along the floor, before the floor acts
        force[k, 2] += normal - COL_DAMP * 2 * mass * np.sqrt(modulus[k] * size[k] / mass) * vz
        speed = np.hypot(vx, vy)
        still = (vx == 0.0) & (vy == 0.0)
        held = still & (pull < MU_STATIC * normal)
        brake = MU_DYNAMIC * normal
        sliding = ~still & (brake * engine.default_timestep < mass * speed)
        stopped = ~still & ~sliding
        s = np.where(sliding)[0]
        force[k[s], 0] -= brake[s] * vx[s] / speed[s]
        force[k[s], 1] -= brake[s] * vy[s] / speed[s]
        fixed = k[held | stopped]
        force[fixed, 0] = 0.0
        force[fixed, 1] = 0.0
        halt = dof[k[stopped]]
        data.qvel[halt] = 0.0
        data.qvel[halt + 1] = 0.0
        return force, torque

    engine.forces = forces


def floor_settings(name, params, grid=None):
    """-> (the engine's settings, what to do to the loaded engine or None)."""
    if name == 'hard':
        return params, None
    if name == 'default':
        return dict(params, floor_contact='mujoco'), None
    if name == 'matched':
        return params, soften_contact
    if name == 'rule2013':
        return params, install_2013_floor
    if name == PLACED:
        return dict(params, initial_height=ts.lowest_layer(grid) * params['voxel_size']), install_2013_floor
    raise ValueError(f'unknown floor {name!r}')


# --------------------------------------------------------------------------------------------
# what is measured on a recorded motion (lengths in the 2013 simulator's units)
# --------------------------------------------------------------------------------------------
def motion_measures(times, cms, frames):
    distance = np.linalg.norm(cms - cms[0], axis=1) / rc.BODY
    at = [float(np.interp(k * rc.CYCLE, times, distance)) for k in range(11)]
    early, late = at[5] - at[0], at[10] - at[5]
    turn = rt.turned(frames)
    return {'distance_at_cycle': [round(v, 4) for v in at],
            'late_over_early': float(late / early) if early > 1e-6 else None,
            'sunk': float(-rt.lowest_point(frames)),          # voxels below the floor's surface, at most
            'turned_at_most': float(turn.max()), 'turned_at_the_end': float(turn[-1]),
            'frames': int(len(times))}


def evaluate(job):
    """One robot on one floor in the MuJoCo engine: the scored evaluation, recorded."""
    key, grid, params, floor = job
    started = time.time()
    out = {'key': key, 'floor': floor, 'score': 0.0, 'blew_up': False, 'error': None}
    try:
        settings, prepare = floor_settings(floor, params, grid)
        score, blew_up, _, times, cms, frames = rt.mujoco_frames(np.asarray(grid), settings, EVERY, prepare)
        out.update(score=float(score), blew_up=bool(blew_up))
        if np.isfinite(frames).all():
            out.update(motion_measures(times, cms, frames))
    except Exception as exc:                                  # noqa: BLE001
        if ts.out_of_memory(exc):                             # not a result of the robot: stop the run
            raise RuntimeError(f'out of memory while scoring ({type(exc).__name__}: {exc})') from exc
        out['error'] = f'{type(exc).__name__}: {exc}'
    out['seconds'] = round(time.time() - started, 1)
    return out


def robot_text(grid):
    """A body as a robot file of the 2013 simulator, with the settings of the 2013 experiment."""
    with open(TEMPLATE, encoding='iso-8859-1') as f:
        return c13.fill_template(f.read(), np.asarray(grid))


def simulate_2013(job):
    """One robot in the 2013 simulator (the campaign's build, and its recording copy)."""
    key, grid, every = job
    started = time.time()
    reference, recorded, trace = rc.record({'vxa': robot_text(grid)}, f'floor_{key}', every)
    _, times, cms, frames = rc.read_trace(trace)
    for path in (trace, trace.replace('.trace.txt', '.vxa')):
        if os.path.exists(path):
            os.remove(path)
    out = {'key': key, 'score': float(reference / rc.BODY),
           'recording_agrees': bool(abs(recorded - reference) <= 1e-5 * max(reference, rc.BODY))}
    out.update(motion_measures(times, cms, frames))
    out['seconds'] = round(time.time() - started, 1)
    return out


# --------------------------------------------------------------------------------------------
# running, with what was already done kept
# --------------------------------------------------------------------------------------------
def body_key(grid):
    g = np.ascontiguousarray(grid, np.int8)
    return hashlib.sha256(repr(g.shape).encode() + g.tobytes()).hexdigest()[:20]


def kept_name(key, floor, grid):
    """Under which name an evaluation is kept. A body that touches the bottom of the workspace has
    no separate evaluation 'started where it is': the one set on the floor is that evaluation."""
    if floor == PLACED and ts.lowest_layer(grid) == 0:
        floor = 'rule2013'
    return f'{key}/{FLOOR_ID[floor]}'


def run_all(robots, floors, workers, cache_path=CACHE, say=ts.tell):
    """robots: dicts with 'grid'. Adds nothing to them; returns {(body key, floor or '2013'): result}."""
    params = ts.worker_parameters(ts.evaluator_arguments())
    cache = {k: v for k, v in ts.read_cache(cache_path).items() if not v.get('error')}     # a failure is not a result
    bodies = {body_key(r['grid']): r['grid'] for r in robots}
    todo_2013 = [(k, g, EVERY) for k, g in bodies.items() if f'{k}/2013' not in cache]

    def kept_as(k, floor):
        return kept_name(k, floor, bodies[k])

    todo, queued = [], set()
    for floor in floors:
        for k, g in bodies.items():
            name = kept_as(k, floor)
            if name not in cache and name not in queued:
                queued.add(name)
                todo.append((name, g, params, floor if name.endswith(FLOOR_ID[floor]) else 'rule2013'))
    say(f'{len(bodies)} bodies: {len(todo_2013)} runs of the 2013 simulator and {len(todo)} evaluations in the '
        f'MuJoCo engine to do.')
    started = time.time()
    if todo_2013:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for i, result in enumerate(pool.map(simulate_2013, todo_2013), 1):
                cache[f"{result['key']}/2013"] = result
                if i % 10 == 0 or i == len(todo_2013):
                    ts.write_cache(cache_path, cache)
                    say(f'  2013 simulator: {i}/{len(todo_2013)}  ({(time.time() - started) / 60:.1f} min so far)')
    if todo:
        from multiprocessing import Pool
        with Pool(ts.workers_that_fit(workers, say=say), maxtasksperchild=8) as pool:
            for i, result in enumerate(pool.imap_unordered(evaluate, todo, chunksize=1), 1):
                if result['error']:
                    raise SystemExit(f"An evaluation failed ({result['floor']}: {result['error']}). Nothing is "
                                     f"summarised from an incomplete run; what was finished is kept.")
                cache[result['key']] = result
                ts.write_cache(cache_path, cache)
                if i % 10 == 0 or i == len(todo) or result['error'] or result['blew_up']:
                    say(f"  MuJoCo engine: {i}/{len(todo)}  last: {result['floor']} score {result['score']:.3f}"
                        f"{'  BLEW UP' if result['blew_up'] else ''}{'  ERROR ' + result['error'] if result['error'] else ''}"
                        f"  ({(time.time() - started) / 60:.1f} min so far)")
    out = {(k, '2013'): cache[f'{k}/2013'] for k in bodies}
    out.update({(k, floor): cache[kept_as(k, floor)] for k in bodies for floor in floors})
    return out


# --------------------------------------------------------------------------------------------
# the report
# --------------------------------------------------------------------------------------------
def summarise(robots, results, floors, n_boot=None):
    """Per set of robots and floor: what README.md, point 3, names."""
    from scipy.stats import wilcoxon
    out = {}
    for name in dict.fromkeys(r['set'] for r in robots):
        rows = [r for r in robots if r['set'] == name]
        keys = [body_key(r['grid']) for r in rows]
        evolved = np.array([r['evolved'] for r in rows])
        in_2013 = [results[(k, '2013')] for k in keys]
        block = {'n': len(rows), 'simulator_2013': {
            'score': list(ps.quartiles([x['score'] for x in in_2013])),
            'repeats_its_score': int(sum(abs(x['score'] - e) <= 1e-4 * max(1.0, e) for x, e in zip(in_2013, evolved))),
            'sunk': list(ps.quartiles([x['sunk'] for x in in_2013])),
            'turned_at_most': list(ps.quartiles([x['turned_at_most'] for x in in_2013])),
            'tipped': int(sum(x['turned_at_most'] > TIPPED for x in in_2013)),
            'late_over_early': list(ps.quartiles([x['late_over_early'] for x in in_2013 if x['late_over_early'] is not None]))},
            'floors': {}}
        base = None
        for floor in floors:
            res = [results[(k, floor)] for k in keys]
            scores = np.array([x['score'] for x in res])
            ratio = scores / evolved
            moved = [x for x in res if 'sunk' in x]
            _, lo, hi = ps.median_interval(ratio, n_boot)
            rho, rho_lo, rho_hi = ps.rank_correlation(evolved, scores, n_boot)
            f = {'blew_up': int(sum(x['blew_up'] for x in res)), 'failed': int(sum(bool(x['error']) for x in res)),
                 'score': list(ps.quartiles(scores)), 'ratio': list(ps.quartiles(ratio)), 'ratio_median_interval': [lo, hi],
                 'rank_agreement': rho, 'rank_agreement_interval': [rho_lo, rho_hi],
                 'kept_all_or_more': int((ratio >= 1.0).sum()),
                 'within_20_percent': int((np.abs(ratio - 1.0) <= 0.20).sum()),
                 'error': list(ps.quartiles(np.abs(ratio - 1.0))),
                 'sunk': list(ps.quartiles([x['sunk'] for x in moved])) if moved else None,
                 'turned_at_most': list(ps.quartiles([x['turned_at_most'] for x in moved])) if moved else None,
                 'tipped': int(sum(x['turned_at_most'] > TIPPED for x in moved)), 'recorded': len(moved),
                 'late_over_early': list(ps.quartiles([x['late_over_early'] for x in moved
                                                       if x['late_over_early'] is not None])) if moved else None}
            if floor == 'hard':
                base = ratio
            elif base is not None:
                gain = ratio - base
                _, glo, ghi = ps.median_interval(gain, n_boot)
                f['gain_over_hard'] = {'median': float(np.median(gain)), 'interval': [glo, ghi],
                                       'better': int((gain > 0).sum()),
                                       'p': float(wilcoxon(gain).pvalue) if np.any(gain != 0) else 1.0}
            block['floors'][floor] = f
        out[name] = block
    return out


def render(summary, title):
    L = [title, '']
    for name, block in summary.items():
        s = block['simulator_2013']
        L.append(f"{ts.set_title(name)}: {block['n']} robots")
        L.append(f"  in the 2013 simulator: score {med_q(s['score'])}; repeats its known score {s['repeats_its_score']} of "
                 f"{block['n']}; lowest point {med_q(s['sunk'])} voxels below the surface; turns over by at most "
                 f"{med_q(s['turned_at_most'], '.0f')} degrees, {s['tipped']} tip beyond {TIPPED:.0f}; late over early "
                 f"distance {med_q(s['late_over_early'])}")
        L.append(f"  {'floor':<9}  {'blew up':>7}  {'score':>18}  {'share kept':>18}  {'95% of median':>13}  {'rank agreement (95%)':>22}  "
                 f"{'>= 1':>5}  {'within 20%':>10}  {'off by':>18}  {'sunk':>18}  {'turned at most':>16}  {'tipped':>6}  {'late/early':>18}  "
                 f"gain over hard (95%), better, p")
        for floor, f in block['floors'].items():
            gain = f.get('gain_over_hard')
            L.append(f"  {floor:<9}  {f['blew_up']:>7}  {med_q(f['score']):>18}  {med_q(f['ratio']):>18}  "
                     f"{f['ratio_median_interval'][0]:>6.2f}-{f['ratio_median_interval'][1]:<6.2f}  "
                     f"{f['rank_agreement']:>+6.2f} ({f['rank_agreement_interval'][0]:+.2f} to {f['rank_agreement_interval'][1]:+.2f})  "
                     f"{f['kept_all_or_more']:>5}  {f['within_20_percent']:>10}  {med_q(f['error']):>18}  "
                     f"{med_q(f['sunk']):>18}  {med_q(f['turned_at_most'], '.0f'):>16}  "
                     f"{f['tipped']:>6}  {med_q(f['late_over_early']):>18}  "
                     + (f"{gain['median']:+.2f} ({gain['interval'][0]:+.2f} to {gain['interval'][1]:+.2f}), {gain['better']} of "
                        f"{block['n']}, p = {gain['p']:.4f}" if gain else ''))
        L.append('')
    return '\n'.join(L)


def med_q(q, fmt='.2f'):
    return '-' if not q else f'{q[0]:{fmt}} ({q[1]:{fmt}}-{q[2]:{fmt}})'


# --------------------------------------------------------------------------------------------
# checks on simple bodies
# --------------------------------------------------------------------------------------------
def check_bodies():
    """name -> (body, layers above the bottom of the workspace it starts at)."""
    def block(shape, material, at=(3, 3, 0)):
        g = np.zeros((10, 10, 10), np.int8)
        g[at[0]:at[0] + shape[0], at[1]:at[1] + shape[1], at[2]:at[2] + shape[2]] = material
        return g
    shaker = block((4, 4, 4), 1)
    shaker[5:7, 3:7, 0:4] = 2                                 # the two muscle phases side by side
    return {'block at rest (3x3x3, soft)': block((3, 3, 3), 3),
            'tower at rest (2x2x10, soft)': block((2, 2, 10), 3),
            'block dropped from 3 voxels (3x3x3, soft)': block((3, 3, 3), 3, at=(3, 3, 3)),
            'shaker (4x4x4, two muscle phases)': shaker}


def run_engine(grid, params, floor, seconds, every, height):
    """A body stepped in the engine without scoring it (a body without muscles has no score)."""
    from src.evolution import mujoco_tendon_evaluator as evaluation
    settings, prepare = floor_settings(floor, params)
    engine = evaluation._make_engine(settings)
    engine.load_robot(np.asarray(grid), voxel_size=settings['voxel_size'], initial_height=height, gait_params=None)
    if prepare is not None:
        prepare(engine)
    size = float(engine.voxel_size)
    scale = VOXEL / size
    times, cms, frames = [], [], []

    def keep():
        pos = np.array(engine.data.xpos[1:], float) * scale
        side = size * (1.0 + engine.voxel_strain(engine.current_time)) * scale
        times.append(float(engine.current_time))
        cms.append(pos.mean(axis=0))
        frames.append(np.hstack([pos, np.array(engine.data.xquat[1:], float), np.repeat(side[:, None], 3, axis=1)]))

    keep()
    for _ in range(int(seconds / engine.default_timestep)):
        engine.step()
        if engine.current_time >= len(times) * every - 0.5 * engine.default_timestep:
            keep()
    return np.array(times), np.array(cms), np.array(frames), bool(engine.diverged())


def checks():
    """Simple bodies in the 2013 simulator and on every floor: where the lowest voxels are."""
    params = ts.worker_parameters(ts.evaluator_arguments())
    every, report = 0.0005, {}
    print('Lowest voxel centre in voxels (0.5 = resting on the surface without sinking), and the centre of mass.')
    for name, grid in check_bodies().items():
        layer = ts.lowest_layer(grid)
        reference, recorded, trace = rc.record({'vxa': robot_text(grid)}, 'floor_check', every)
        _, t, cm, fr = rc.read_trace(trace)
        runs = {'2013 simulator': (t, cm, fr, False)}
        for floor in FLOORS:
            runs[floor] = run_engine(grid, params, floor, 0.25, every, layer * params['voxel_size'])
        print(f'\n{name}: {int((grid != 0).sum())} voxels, {int((grid[:, :, layer] != 0).sum())} on its lowest layer, starts '
              f'{layer} voxels up')
        print(f"  {'':<15}  {'lowest centre: at the end':>26}  {'at its lowest':>14}  {'mean of last 50 ms':>19}  "
              f"{'centre of mass moved (x, y, z), voxels':>40}  {'distance / 10 voxels':>21}")
        report[name] = {}
        for where, (t, cm, fr, blew) in runs.items():
            low = fr[..., 2].min(axis=1) / VOXEL
            last = t >= t[-1] - 0.05
            moved = (cm[-1] - cm[0]) / VOXEL
            report[name][where] = {'lowest_centre_at_the_end': float(low[-1]), 'lowest_centre_at_its_lowest': float(low.min()),
                                   'lowest_centre_mean_of_last_50_ms': float(low[last].mean()),
                                   'moved_voxels': [float(v) for v in moved], 'blew_up': blew,
                                   'score': float(np.linalg.norm(cm[-1] - cm[0]) / rc.BODY)}
            print(f"  {where:<15}  {low[-1]:>26.4f}  {low.min():>14.4f}  {low[last].mean():>19.4f}  "
                  f"{moved[0]:>+12.3f} {moved[1]:>+12.3f} {moved[2]:>+12.3f}  {np.linalg.norm(cm[-1] - cm[0]) / rc.BODY:>21.4f}"
                  f"{'  BLEW UP' if blew else ''}")
    with open(os.path.join(HERE, 'floor_checks.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--checks', action='store_true')
    what.add_argument('--pilot', action='store_true')
    what.add_argument('--champions', action='store_true')
    ap.add_argument('--floors', nargs='+', default=list(FLOORS), choices=FLOORS + (PLACED,))
    ap.add_argument('--workers', type=int, default=10)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    if a.checks:
        return checks()
    if a.pilot:
        robots = ts.rehearsal_champions('pilot10_P0_s', 10)
        title = 'PILOT ROBOTS (generation 10 of the 12-seed pilot; not an arm) on four floors of the MuJoCo engine'
        name = 'floor_pilot'
    else:
        robots = (ts.arm_champions('R') + ts.deposited_champions('noCost')
                  + ts.arm_champions('Rc') + ts.deposited_champions('costNumActuated'))
        title = 'THE 140 CHAMPIONS OF THE TRANSFER OUTCOME on four floors of the MuJoCo engine'
        name = 'floor_champions'
    from run_tendon_evolution import _prevent_sleep
    awake = _prevent_sleep()
    try:
        results = run_all(robots, a.floors, max(1, a.workers))
    finally:
        awake()
    summary = summarise(robots, results, a.floors)
    text = render(summary, title)
    print('\n' + text)
    rows = []
    for r in robots:
        k = body_key(r['grid'])
        rows.append({'set': r['set'], 'label': r['label'], 'evolved': r['evolved'],
                     'simulator_2013': results[(k, '2013')], **{floor: results[(k, floor)] for floor in a.floors}})
    with open(os.path.join(HERE, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump({'title': title, 'made': time.strftime('%Y-%m-%dT%H:%M'), 'floors': list(a.floors), 'summary': summary,
                   'robots': rows}, f, indent=1, default=float)
    with open(os.path.join(HERE, name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    print(f'Written to {os.path.join(HERE, name)}.txt and .json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
