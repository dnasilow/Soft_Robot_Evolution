"""Video for the floor test: the three champions of the transfer video once more, each in the
2013 simulator, in the MuJoCo engine on the preset's floor, and in the MuJoCo engine under the
2013 floor rule (floor_softness.py). The robots are those the transfer video's rule picked on
24 November, before this test existed.

usage, from the project folder:
    python paper/diagnostics_2026-11-25/render_floors.py

A champion that does not touch the bottom of the workspace is started at its height in all three
panels, as the 2013 simulator starts it. Checks, each of which stops the script: the 2013 side
repeats the robot's score; the engine on the preset's floor repeats the score of the transfer
report; all three hold the same body at the same height.

Written to paper/outcomes/videos/: floors_champions.gif, .webp, .png (five moments), .json.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))

import floor_softness as fs                                   # noqa: E402
import render_champions as rc                                 # noqa: E402
import render_transfer as rt                                  # noqa: E402
import transfer_scores as ts                                  # noqa: E402

COLUMNS = (('simulator_2013', 'the 2013 simulator'), ('hard', "MuJoCo engine, the preset's floor"),
           ('rule2013', 'MuJoCo engine, the 2013 floor rule'))


def describe(score, evolved, times, cms, frames):
    turn = rt.turned(frames)
    return {'score': float(score), 'share_of_its_2013_score': float(score / evolved),
            'gain_in_distance_per_cycle': rt.per_cycle(times, cms),
            'lowest_point_voxels': rt.lowest_point(frames),
            'body_turned_degrees': {'at_the_end': round(float(turn[-1]), 1), 'at_most': round(float(turn.max()), 1)},
            'heading_degrees': rt.heading(cms)}


def assemble(panels, captions, times, slowdown):
    from PIL import Image, ImageDraw
    w, h = rc.PANEL
    big, small = rc.font(15), rc.font(12)
    sheets = []
    for k in range(len(times)):
        sheet = Image.new('RGB', (len(COLUMNS) * (w + 6) - 6, len(panels) * (h + 6) - 6), (255, 255, 255))
        for i, (row, texts) in enumerate(zip(panels, captions)):
            for j, (images, (first, second)) in enumerate(zip(row, texts)):
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
    ap.add_argument('--every', type=float, default=0.0025)
    ap.add_argument('--frame-ms', type=int, default=60)
    a = ap.parse_args(argv)
    with open(rt.REPORT, encoding='utf-8') as f:
        report = json.load(f)
    params = ts.worker_parameters(ts.evaluator_arguments())

    shown, records = [], []
    for i, (row, how) in enumerate(rt.choose(report['champions'])):
        who = f"{ts.set_title(row['set'])}, {row['label']}"
        text = rt.robot_text(row)
        grid = ts.grid_of_text(text)
        reference, recorded, trace = rc.record({'vxa': text}, f'floors_{i}', a.every)
        m13, t13, cm13, f13 = rc.read_trace(trace)
        score_2013 = reference / rc.BODY
        if abs(score_2013 - row['evolved']) > 1e-5 * max(1.0, row['evolved']) or abs(recorded - reference) > 1e-5 * reference:
            raise SystemExit(f'{who}: the 2013 simulator does not repeat its score.')
        settings = params if how == 'floor' else dict(params, initial_height=row['lowest_layer'] * params['voxel_size'])
        record = {'robot': who, 'started': 'set on the floor' if how == 'floor' else 'at its height in the workspace',
                  'voxels': int(len(m13)), 'lowest_layer': row['lowest_layer'],
                  'simulator_2013': describe(score_2013, row['evolved'], t13, cm13, f13)}
        runs = [(m13, t13, *rc.for_display(cm13, f13))]
        for floor in ('hard', 'rule2013'):
            floor_params, prepare = fs.floor_settings(floor, settings)
            score, blew_up, mmj, tmj, cmmj, fmj = rt.mujoco_frames(grid, floor_params, a.every, prepare)
            if floor == 'hard':
                expected = row['score'] if how == 'floor' else row['placed']['score']
                if abs(score - expected) > 1e-9:
                    raise SystemExit(f"{who}: on the preset's floor the engine scores {score:.9f}, the transfer report says "
                                     f"{expected:.9f}.")
            if not rt.same_body(m13, f13[0], mmj, fmj[0]) or abs(fmj[0][:, 2].min() - f13[0][:, 2].min()) > 1e-9:
                raise SystemExit(f'{who}: the engine does not hold the body the 2013 simulator holds, or not at its height.')
            record[floor] = describe(score, row['evolved'], tmj, cmmj, fmj)
            record[floor]['blew_up'] = bool(blew_up)
            record[floor]['heading_relative_to_2013_degrees'] = float(
                (rt.heading(cmmj) - rt.heading(cm13) + 180.0) % 360.0 - 180.0)
            runs.append((mmj, tmj, *rc.for_display(cmmj, fmj)))
        records.append(record)
        shown.append(runs)
        print(f"{who} ({record['started']})")
        for key, label in COLUMNS:
            r = record[key]
            print(f"   {label:<36} score {r['score']:.3f} ({r['share_of_its_2013_score']:.2f}); lowest point "
                  f"{r['lowest_point_voxels']:+.2f} voxels; turned {r['body_turned_degrees']['at_most']:.0f} degrees at most; "
                  f"gain per cycle {r['gain_in_distance_per_cycle']}")

    n = min(len(run[1]) for runs in shown for run in runs)
    times = shown[0][0][1][:n]
    span = max(r[key]['score'] for r in records for key, _ in COLUMNS) * 10 + 28
    panels, captions = [], []
    for runs, r in zip(shown, records):
        panels.append([rc.render_robot(m, pos[:n], quat[:n], size[:n], span) for m, _, pos, quat, size, _ in runs])
        up = (f", starts {r['lowest_layer']} voxel{'s' if r['lowest_layer'] > 1 else ''} up" if r['lowest_layer'] else '')
        texts = [(f"{r['robot']}: the 2013 simulator",
                  f"{r['simulator_2013']['score']:.2f} body lengths in 10 cycles, {r['voxels']} voxels{up}")]
        for key, label in COLUMNS[1:]:
            texts.append((label, f"{r[key]['score']:.2f} body lengths, {r[key]['share_of_its_2013_score']:.2f} of its score; "
                                 f"turns over by {r[key]['body_turned_degrees']['at_most']:.0f}° at most"))
        captions.append(texts)
    slowdown = a.frame_ms / 1000 / a.every
    sheets = assemble(panels, captions, times, slowdown)

    os.makedirs(rc.OUT, exist_ok=True)
    stem = os.path.join(rc.OUT, 'floors_champions')
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
