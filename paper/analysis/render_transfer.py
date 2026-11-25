"""Videos for the transfer outcome: the same champion in the two simulators, side by side. Left,
the 2013 simulator it was evolved in; right, this project's MuJoCo engine with the settings of
--preset cheney2013. A check that a transfer score describes what the robot does, and that the
two simulators were given the same body.

usage, from the project folder (needs the report of transfer_scores.py in paper/outcomes/):
    python paper/analysis/render_transfer.py

Which robots, by a rule fixed here and not by eye: for every arm in the report, the champion with
the median transfer ratio among those that touch the bottom of the workspace; and, where at least
three champions of the arm do not touch it, the one with the median ratio among those, started at
its height in the workspace (PROTOCOL.md, section 9.4, point 9).

Checks made on every robot shown, each of which stops the script if it fails
  the 2013 side   the recording copy of the simulator reports the distance the campaign's
                  simulator reports, and the robot's recorded score
  the MuJoCo side the frames come from the evaluation that is scored: its score is the score in
                  the transfer report, to the last digit
  the body        the two simulators hold the same voxels of the same materials in the same places

Written to paper/outcomes/videos/: transfer_champions.gif, .webp, .png (five moments), .json.
"""
import argparse
import json
import math
import os
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import analyse_arm as aa                                      # noqa: E402
import render_champions as rc                                 # noqa: E402
import transfer_scores as ts                                  # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402

REPORT = os.path.join(aa.OUTCOMES, 'transfer.json')
MIN_OFF_THE_FLOOR = 3


# --------------------------------------------------------------------------------------------
# which robots
# --------------------------------------------------------------------------------------------
def median_by(rows, key):
    """The row with the median value of key (the lower of the two middle ones for an even number)."""
    ranked = sorted(rows, key=key)
    return ranked[(len(ranked) - 1) // 2]


def choose(champions):
    """[(row of the report, 'floor' or 'placed'), ...] by the rule in the module's description."""
    chosen = []
    for name in dict.fromkeys(r['set'] for r in champions if r['set'].startswith('arm_')):
        rows = [r for r in champions if r['set'] == name]
        on_floor = [r for r in rows if r['lowest_layer'] == 0]
        off_floor = [r for r in rows if r.get('placed')]
        if on_floor:
            chosen.append((median_by(on_floor, lambda r: r['ratio']), 'floor'))
        if len(off_floor) >= MIN_OFF_THE_FLOOR:
            chosen.append((median_by(off_floor, lambda r: r['placed']['ratio']), 'placed'))
    return chosen


def robot_text(row):
    """The robot file of a champion of an arm of re-runs, from its run's archive."""
    arm = row['set'][len('arm_'):]
    spec = aa.ARMS[arm]
    if spec['kind'] != 'rerun':
        raise SystemExit(f'Arm {arm} keeps no robot files; its champions have to be exported first.')
    seed = int(row['label'].split()[-1])
    archive = os.path.join(aa.RERUNS, f"{spec['prefix']}{seed}", f"Gen_{spec['generations']:04d}.tgz")
    with tarfile.open(archive, 'r:gz') as t:
        for m in t:
            if m.isfile() and os.path.basename(m.name) == row['file']:
                return t.extractfile(m).read().decode('iso-8859-1')
    raise SystemExit(f"{row['file']} is not in {archive}.")


# --------------------------------------------------------------------------------------------
# the MuJoCo engine, recorded
# --------------------------------------------------------------------------------------------
def mujoco_frames(grid, params, every, prepare=None):
    """The scored evaluation itself (as transfer_scores.score_one runs it), keeping the state of
    every voxel each `every` seconds. Lengths are returned in the 2013 simulator's units, where a
    voxel is 1 mm, so that both simulators can be drawn by the same code.
    prepare: called with the engine once the body is loaded (diagnostics that set up another
    floor use it); None leaves the engine as the search runs it.
    -> score, blew up, materials (2013 numbers), times, centre of mass, voxel states (f x n x 10)."""
    from src.evolution import mujoco_tendon_evaluator as evaluation
    engine = evaluation._make_engine(params)
    engine.load_robot(np.asarray(grid), voxel_size=params['voxel_size'], initial_height=params['initial_height'],
                      gait_params=None)
    if prepare is not None:
        prepare(engine)
    size = float(engine.voxel_size)
    scale = c13.VOXEL_SIZE_2013 / size
    times, cms, frames = [], [], []

    def keep():
        pos = np.array(engine.data.xpos[1:], float) * scale
        quat = np.array(engine.data.xquat[1:], float)
        side = size * (1.0 + engine.voxel_strain(engine.current_time)) * scale
        times.append(float(engine.current_time))
        cms.append(pos.mean(axis=0))
        frames.append(np.hstack([pos, quat, np.repeat(side[:, None], 3, axis=1)]))

    keep()
    step = engine.step

    def watched_step():
        step()
        if engine.current_time >= len(times) * every - 0.5 * engine.default_timestep:
            keep()

    engine.step = watched_step
    score = float(engine.get_fitness(simulation_time=params['simulation_time'], settle_time=params['settle_time'],
                                     return_descriptors=False, **evaluation._fitness_kw(params)))
    if len(times) < int(round(params['simulation_time'] / every)) + 1:
        keep()                                                # the state the score was read from
    materials = np.array([int(c13.OURS_TO_2013[int(m)]) for m in engine.mats])
    return score, bool(engine.diverged()), materials, np.array(times), np.array(cms), np.array(frames)


def same_body(materials_a, frame_a, materials_b, frame_b):
    """True if the two simulators start from the same voxels: the same cells along the same axes,
    holding the same materials. frame: the first recorded state, positions in metres of the 2013
    scale. Where a body stands is not compared (the MuJoCo engine centres it on the origin), only
    its cells, counted from the corner of its bounding box."""
    def cells(materials, frame):
        p = frame[:, 0:3]
        c = np.rint((p - p.min(axis=0)) / c13.VOXEL_SIZE_2013).astype(int)
        return sorted((int(x), int(y), int(z), int(m)) for (x, y, z), m in zip(c, materials))
    return len(materials_a) == len(materials_b) and cells(materials_a, frame_a) == cells(materials_b, frame_b)


def heading(cms):
    d = cms[-1] - cms[0]
    return math.degrees(math.atan2(d[1], d[0]))


def per_cycle(times, cms):
    """Distance from the start at the end of each cycle, in body lengths, and the gain per cycle."""
    d = np.linalg.norm(cms - cms[0], axis=1) / rc.BODY
    at = [float(np.interp(k * rc.CYCLE, times, d)) for k in range(11)]
    return [round(float(v), 3) for v in np.diff(at)]


def turned(frames):
    """How far the body as a whole has turned from its first recorded state, in degrees, at every
    frame: the angle of the rigid rotation that best maps the voxels' first positions (about
    their centre) onto their positions now."""
    first = frames[0][:, 0:3] - frames[0][:, 0:3].mean(axis=0)
    angles = []
    for f in frames:
        now = f[:, 0:3] - f[:, 0:3].mean(axis=0)
        u, _, vt = np.linalg.svd(first.T @ now)
        d = np.sign(np.linalg.det(vt.T @ u.T))
        r = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1.0) / 2.0)))))
    return np.array(angles)


def lowest_point(frames):
    """Voxels below the floor's surface reached by the lowest voxel face (negative = sunk)."""
    return float(((frames[..., 2] - frames[..., 9] / 2) / c13.VOXEL_SIZE_2013).min())


# --------------------------------------------------------------------------------------------
# pictures
# --------------------------------------------------------------------------------------------
def assemble(panels, captions, times, slowdown):
    """panels: [left images, right images] per robot. captions: [(line 1, line 2), (line 1, line 2)] per robot."""
    from PIL import Image, ImageDraw
    w, h = rc.PANEL
    big, small = rc.font(15), rc.font(12)
    sheets = []
    for k in range(len(times)):
        sheet = Image.new('RGB', (2 * w + 6, len(panels) * (h + 6) - 6), (255, 255, 255))
        for i, (pair, texts) in enumerate(zip(panels, captions)):
            for j, (images, (first, second)) in enumerate(zip(pair, texts)):
                im = Image.fromarray(images[k])
                d = ImageDraw.Draw(im)
                d.rectangle([0, 0, w, 40], fill=(255, 255, 255))
                d.text((8, 3), first, fill=(0, 0, 0), font=big)
                d.text((8, 22), second, fill=(60, 60, 60), font=small)
                d.text((8, h - 18), f"cycle {min(times[k] / rc.CYCLE, 10):4.1f} of 10    one square = one body length    "
                                    f"slowed {slowdown:.0f}x", fill=(40, 40, 40), font=small)
                sheet.paste(im, (j * (w + 6), i * (h + 6)))
        sheets.append(sheet)
    return sheets


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    ap.add_argument('--report', default=REPORT, help='the transfer report (default paper/outcomes/transfer.json)')
    ap.add_argument('--every', type=float, default=0.0025, help='simulated seconds between frames (default 0.0025)')
    ap.add_argument('--frame-ms', type=int, default=60, help='milliseconds each frame is shown (default 60)')
    a = ap.parse_args(argv)
    if not os.path.isfile(a.report):
        raise SystemExit(f'{a.report} does not exist. Run transfer_scores.py first and copy its report to paper/outcomes/.')
    with open(a.report, encoding='utf-8') as f:
        report = json.load(f)
    params = ts.worker_parameters(ts.evaluator_arguments())

    shown, records = [], []
    for i, (row, how) in enumerate(choose(report['champions'])):
        who = f"{ts.set_title(row['set'])}, {row['label']}"
        text = robot_text(row)
        grid = ts.grid_of_text(text)
        robot = {'vxa': text, 'row': ts.set_title(row['set']), 'who': row['label'], 'column': how, 'ours': True,
                 'recorded': row['evolved']}
        reference, recorded, trace = rc.record(robot, f'transfer_{i}', a.every)
        m13, t13, cm13, f13 = rc.read_trace(trace)
        for name, value in (('the recording copy', recorded / rc.BODY), ('the first and last frame',
                                                                         float(np.linalg.norm(cm13[-1] - cm13[0]) / rc.BODY))):
            if abs(value - reference / rc.BODY) > 1e-5 * max(1.0, reference / rc.BODY):
                raise SystemExit(f'{who}: {name} gives {value:.6f}, the campaign\'s simulator {reference / rc.BODY:.6f}.')
        if abs(reference / rc.BODY - row['evolved']) > 1e-5 * max(1.0, row['evolved']):
            raise SystemExit(f"{who}: scores {reference / rc.BODY:.6f} in the 2013 simulator now, recorded {row['evolved']:.6f}.")

        settings = params if how == 'floor' else dict(params, initial_height=row['lowest_layer'] * params['voxel_size'])
        expected = row['score'] if how == 'floor' else row['placed']['score']
        score, blew_up, mmj, tmj, cmmj, fmj = mujoco_frames(grid, settings, a.every)
        if abs(score - expected) > 1e-9:
            raise SystemExit(f'{who}: the recorded evaluation scores {score:.9f}, the transfer report says {expected:.9f}. '
                             f'The frames would not be the evaluation that was scored.')
        if not same_body(m13, f13[0], mmj, fmj[0]):
            raise SystemExit(f'{who}: the two simulators do not hold the same body.')
        if abs(fmj[0][:, 2].min() - f13[0][:, 2].min()) > 1e-9:
            raise SystemExit(f'{who}: the body does not start at the same height in the two simulators.')
        turn = (heading(cmmj) - heading(cm13) + 180.0) % 360.0 - 180.0
        turned_13, turned_mj = turned(f13), turned(fmj)
        record = {
            'robot': who, 'started': 'set on the floor' if how == 'floor' else 'at its height in the workspace',
            'voxels': int(len(m13)), 'lowest_layer': row['lowest_layer'],
            'same_voxels_and_materials_in_both_simulators': True,
            'simulator_2013': {'score': reference / rc.BODY, 'score_in_the_recording_copy': recorded / rc.BODY,
                               'heading_degrees': heading(cm13), 'body_lengths_per_cycle': per_cycle(t13, cm13),
                               'lowest_point_voxels': lowest_point(f13),
                               'body_turned_degrees': {'at_the_end': round(float(turned_13[-1]), 1),
                                                       'at_most': round(float(turned_13.max()), 1)},
                               'moved_vertically_body_lengths': float((cm13[-1][2] - cm13[0][2]) / rc.BODY),
                               'all_numbers_finite': bool(np.isfinite(f13).all())},
            'mujoco_engine': {'score': score, 'score_in_the_transfer_report': expected, 'blew_up': blew_up,
                              'ratio': score / row['evolved'], 'heading_degrees': heading(cmmj),
                              'body_lengths_per_cycle': per_cycle(tmj, cmmj), 'lowest_point_voxels': lowest_point(fmj),
                              'body_turned_degrees': {'at_the_end': round(float(turned_mj[-1]), 1),
                                                      'at_most': round(float(turned_mj.max()), 1)},
                              'moved_vertically_body_lengths': float((cmmj[-1][2] - cmmj[0][2]) / rc.BODY),
                              'all_numbers_finite': bool(np.isfinite(fmj).all())},
            'heading_in_mujoco_relative_to_2013_degrees': turn,
        }
        if how == 'placed':
            record['mujoco_engine']['score_when_set_on_the_floor'] = row['score']
        records.append(record)
        shown.append(((m13, t13, *rc.for_display(cm13, f13)), (mmj, tmj, *rc.for_display(cmmj, fmj)), record))
        print(f"{who} ({record['started']}): 2013 simulator {reference / rc.BODY:.4f}, MuJoCo engine {score:.4f} "
              f"({score / row['evolved']:.2f}), heading {turn:+.0f} degrees from the 2013 one, lowest point "
              f"{record['simulator_2013']['lowest_point_voxels']:+.2f} and {record['mujoco_engine']['lowest_point_voxels']:+.2f} voxels")
        for name, key in (('2013', 'simulator_2013'), ('MuJoCo', 'mujoco_engine')):
            print(f"   {name}: gain in distance per cycle {record[key]['body_lengths_per_cycle']}; the body turned "
                  f"{record[key]['body_turned_degrees']['at_the_end']:.0f} degrees by the end, "
                  f"{record[key]['body_turned_degrees']['at_most']:.0f} at most")
    if not shown:
        raise SystemExit('The report holds no champion of an arm of re-runs.')

    n = min(min(len(a13[1]), len(amj[1])) for a13, amj, _ in shown)
    times = shown[0][0][1][:n]
    span = max(max(r['simulator_2013']['score'], r['mujoco_engine']['score']) for r in records) * 10 + 28
    panels, captions = [], []
    for (m13, _, p13, q13, s13, _), (mmj, _, pmj, qmj, smj, _), r in shown:
        panels.append([rc.render_robot(m13, p13[:n], q13[:n], s13[:n], span),
                       rc.render_robot(mmj, pmj[:n], qmj[:n], smj[:n], span)])
        right = (f"{r['mujoco_engine']['score']:.2f} body lengths, {r['mujoco_engine']['ratio']:.2f} of its score; "
                 f"heading {r['heading_in_mujoco_relative_to_2013_degrees']:+.0f}°")
        if 'score_when_set_on_the_floor' in r['mujoco_engine']:
            right += f"; set on the floor {r['mujoco_engine']['score_when_set_on_the_floor']:.2f}"
        captions.append([(f"{r['robot']}: the 2013 simulator",
                          f"{r['simulator_2013']['score']:.2f} body lengths in 10 cycles, {r['voxels']} voxels"
                          + (f", starts {r['lowest_layer']} voxel{'s' if r['lowest_layer'] > 1 else ''} up"
                             if r['lowest_layer'] else '')),
                         ('the same robot in the MuJoCo engine'
                          + (', started at the same height' if r['started'] != 'set on the floor' else ''), right)])
    slowdown = a.frame_ms / 1000 / a.every
    sheets = assemble(panels, captions, times, slowdown)

    os.makedirs(rc.OUT, exist_ok=True)
    stem = os.path.join(rc.OUT, 'transfer_champions')
    from PIL import Image
    sheets[0].save(stem + '.webp', save_all=True, append_images=sheets[1:], duration=a.frame_ms, loop=0, quality=72, method=4)
    paletted = [s.quantize(colors=96, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) for s in sheets]
    paletted[0].save(stem + '.gif', save_all=True, append_images=paletted[1:], duration=a.frame_ms, loop=0, optimize=True)
    moments = [sheets[int(round(v * (len(sheets) - 1)))] for v in (0, 0.25, 0.5, 0.75, 1)]
    strip = Image.new('RGB', (moments[0].width, sum(m.height for m in moments) + 4 * 8), (255, 255, 255))
    y = 0
    for m in moments:
        strip.paste(m, (0, y))
        y += m.height + 8
    strip.save(stem + '.png', optimize=True)
    with open(stem + '.json', 'w', encoding='utf-8') as f:
        json.dump({'seconds_between_frames': a.every, 'slowed_down': slowdown, 'robots': records}, f, indent=1)
    for ext in ('.gif', '.webp', '.png', '.json'):
        print(f"{os.path.relpath(stem + ext, ROOT)}: {os.path.getsize(stem + ext) / 1e6:.2f} MB")
    return 0


if __name__ == '__main__':
    sys.exit(main())
