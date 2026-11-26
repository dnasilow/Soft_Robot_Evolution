"""Videos of champions moving in the ORIGINAL 2013 simulator: a look at what the numbers describe.

For an arm that has been analysed, the champion with the median score and the champion with the
best score are shown below their counterparts among the deposited 2013 runs (four robots, the
same rule for both rows, nothing picked by eye). Each robot is simulated again by the copy of
the 2013 simulator that records every voxel's motion (build_2013_trace.sh), for the 0.25 s and
10 actuation cycles of a 2013 evaluation.

usage, from the project folder:
    python paper/analysis/render_champions.py --arm R

Arms R and Rc are re-runs of the original program; their champions are robot files in the runs'
archives. Arm A is this project's own search; its champions are bodies in the runs' final
populations and are written to a robot file here exactly as the search wrote them for the
simulator (the 2013 settings template with the body filled in).

It writes into paper/outcomes/videos/:
    arm_<X>_champions.gif       the animation (a robot is 1 cm long; the motion is slowed down)
    arm_<X>_champions.webp      the same, smaller and in full colour
    arm_<X>_champions.png       five moments of it, as a still picture
    arm_<X>_champions.json      what was checked on each robot

Checks made on every robot, and written down:
  - the recording simulator gives the score recorded for the robot in its run (so the frames
    are the simulation that was scored, and recording changes nothing);
  - the same score follows from the first and last recorded frame;
  - the lowest point of the body over the whole run (it must not sink through the floor), the
    height of its centre, and how far it gets in each of the 10 cycles.

The view: the floor's squares are one body length (10 voxels, the unit of the score) wide, every
robot is turned so that it travels to the right, and all four share one scale. Colours are those
of the robot files: red and green are the two muscle types (opposite phase), light blue is soft
passive tissue, dark blue stiff.
"""
import argparse
import json
import math
import os
import pickle
import re
import subprocess
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import analyse_arm as aa                       # noqa: E402

WORK = os.path.join(ROOT, 'results', 'analysis', 'videos_work')
OUT = os.path.join(ROOT, 'paper', 'outcomes', 'videos')
TRACE_BINARY = '~/softbots2013_trace/softbots/Voxel_Sim_NoGui/voxelize_trace'
DISTRO = os.environ.get('VOXELYZE2013_WSL_DISTRO', 'Ubuntu')
BODY = 0.01                                    # m: the workspace width, the unit of the 2013 score
CYCLE = 0.025                                  # s: one actuation cycle (40 Hz)
COLOURS = {1: (0.90, 0.12, 0.12, 1), 2: (0.25, 0.85, 0.90, 1), 3: (0.15, 0.75, 0.20, 1), 4: (0.10, 0.20, 0.80, 1)}
PANEL = (460, 250)                             # pixels, width x height of one robot's view

REFERENCE_BINARY = '~/softbots2013_ref/softbots/Voxel_Sim_NoGui/voxelize'     # the campaign's simulator

# Simulates one robot twice: with the campaign's simulator, and with the recording copy. Prints
# the distance each reports (the text of <FinalCOM_Dist>), reference first.
TRACE_SH = r'''
set -u
VXA="$1"; OUT="$2"; EVERY="$3"; BIN="$4"; REF="$5"
BIN="${BIN/#\~/$HOME}"; REF="${REF/#\~/$HOME}"
if [ ! -x "$BIN" ] || [ ! -x "$REF" ]; then echo "NOBINARY"; exit 3; fi
W=$(mktemp -d)
mkdir "$W/ref" "$W/rec"
cp "$VXA" "$W/ref/r.vxa"; cp "$VXA" "$W/rec/r.vxa"
( cd "$W/ref" && "$REF" -f r.vxa > /dev/null 2>&1 )
( cd "$W/rec" && VX_TRACE="$W/trace.txt" VX_TRACE_EVERY="$EVERY" "$BIN" -f r.vxa > /dev/null 2>&1 )
cp "$W/trace.txt" "$OUT"
for d in ref rec; do
  echo "$d $(grep -h -o '<FinalCOM_Dist>[^<]*' "$W/$d"/*fitness.xml | sed 's/<FinalCOM_Dist>//' | head -1)"
done
rm -rf "$W"
'''


def wsl_path(path):
    p = os.path.abspath(path)
    return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')


# --------------------------------------------------------------------------------------------
# which robots
# --------------------------------------------------------------------------------------------
def median_and_best(champions):
    """From a list of (score, ...) tuples: the one with the median score and the one with the best."""
    ranked = sorted(champions, key=lambda c: c[0])
    return ranked[(len(ranked) - 1) // 2], ranked[-1]


def search_robot_text(folder, name):
    """A champion of this project's search (arm A), as the robot file its run gave the simulator:
    the 2013 settings template with the body of that individual of the final population."""
    from src.evolution import cheney2013 as c13
    from src.evolution.voxelyze2013_evaluator import TEMPLATE
    index = int(re.search(r'individual (\d+)$', name).group(1))
    with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
        population = pickle.load(f)
    with open(TEMPLATE, encoding='iso-8859-1') as f:
        template = f.read()
    return c13.fill_template(template, c13.workspace_grid(np.asarray(population['genomes'][index])))


def archived_robot_text(folder, name):
    """A champion of a re-run of the original program, from the archive of its last generation."""
    with tarfile.open(os.path.join(folder, 'Gen_1000.tgz')) as t:
        return t.extractfile(t.getmember('Gen_1000/' + name)).read().decode('iso-8859-1')


def deposited_robot_text(folder, name):
    with open(os.path.join(folder, name), encoding='iso-8859-1') as f:
        return f.read()


def robots_of(arm):
    """[(row label, column label, recorded original score, robot file text), ...] for the four panels."""
    spec = aa.ARMS[arm]
    report = aa.finished_arm(arm)
    if report is None:
        raise SystemExit(f'Arm {arm} has no report in paper/outcomes yet. Videos are made of analysed arms.')
    search = spec['kind'] == 'search'
    ours = []
    for row in report['per_seed']:
        c = row['champion']
        folder = os.path.join(aa.SEARCH_RUNS if search else aa.RERUNS, f"{spec['prefix']}{row['seed']}")
        ours.append((c['original'], f"seed {row['seed']}", folder, c['file']))
    theirs = []
    for c in aa.reference_champions(spec['condition']):
        folder = os.path.join(aa.DEPOSITED_ROBOTS, f"2013-01-16-10^3-{spec['condition']}", c['run'], 'Gen_1000')
        theirs.append((c['original'], c['run'].replace('_', ' '), folder, c['file']))
    ours_label = f'own search 2026, arm {arm}' if search else f're-run 2026, arm {arm}'
    ours_text = search_robot_text if search else archived_robot_text
    out = []
    for row_label, group, text_of, is_ours in (('2013 original', theirs, deposited_robot_text, False),
                                               (ours_label, ours, ours_text, True)):
        for column, (score, who, folder, name) in zip(('median of 35', 'best of 35'), median_and_best(group)):
            out.append({'row': row_label, 'column': column, 'who': who, 'recorded': float(score),
                        'vxa': text_of(folder, name), 'ours': is_ours})
    return out


# --------------------------------------------------------------------------------------------
# simulate with recording, read the recording
# --------------------------------------------------------------------------------------------
def record(robot, tag, every):
    os.makedirs(WORK, exist_ok=True)
    vxa = os.path.join(WORK, tag + '.vxa')
    trace = os.path.join(WORK, tag + '.trace.txt')
    with open(vxa, 'w', encoding='iso-8859-1', newline='\n') as f:
        f.write(robot['vxa'])
    r = subprocess.run(['wsl', '-d', DISTRO, '--', 'bash', '-s', '--', wsl_path(vxa), wsl_path(trace), str(every),
                        TRACE_BINARY, REFERENCE_BINARY], input=TRACE_SH.encode(), capture_output=True, timeout=1800)
    out = dict(line.split(None, 1) for line in r.stdout.decode('utf-8', 'replace').splitlines() if ' ' in line.strip())
    if r.returncode != 0 or 'ref' not in out or 'rec' not in out:
        raise SystemExit(f'The simulators did not run ({r.stdout.decode()[-200:]} {r.stderr.decode()[-300:]}). '
                         f'Build the recording copy with paper/reference_2013/build_2013_trace.sh.')
    return abs(float(out['ref'])), abs(float(out['rec'])), trace


def read_trace(path):
    """-> materials (n), times (f), centre of mass (f x 3), voxel states (f x n x 10), all in metres."""
    with open(path) as f:
        n = int(f.readline().split()[1])
        materials = np.array([int(f.readline()) for _ in range(n)])
        times, cms, frames = [], [], []
        while True:
            head = f.readline().split()
            if len(head) != 5 or head[0] != 't':
                break
            times.append(float(head[1]))
            cms.append([float(v) for v in head[2:]])
            frames.append(np.array([f.readline().split() for _ in range(n)], dtype=float))
    return materials, np.array(times), np.array(cms), np.array(frames)


def quat_mul(a, b):
    w1, x1, y1, z1 = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    w2, x2, y2, z2 = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], axis=-1)


def for_display(cms, frames):
    """Turn the run about the vertical so that the robot ends up to the right of where it began,
    put its starting point at the origin, and measure in voxels (millimetres)."""
    d = cms[-1] - cms[0]
    a = -math.atan2(d[1], d[0])
    c, s = math.cos(a), math.sin(a)
    rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    origin = np.array([cms[0][0], cms[0][1], 0.0])
    pos = ((frames[..., 0:3] - origin) @ rot.T) * 1000
    quat = quat_mul(np.array([math.cos(a / 2), 0, 0, math.sin(a / 2)]), frames[..., 3:7])
    size = frames[..., 7:10] * 1000
    return pos, quat, size, ((cms - origin) @ rot.T) * 1000


def describe(robot, materials, times, cms, frames, reference, recorded):
    """The checks, in the units of the score (body lengths) and of the body (voxels)."""
    pos, _, size, cm = for_display(cms, frames)
    bottoms = pos[..., 2] - size[..., 2] / 2
    at_cycle = [float(np.interp(k * CYCLE, times, cm[:, 0])) / (BODY * 1000) for k in range(11)]
    steps = np.diff(at_cycle)
    return {
        'robot': f"{robot['row']}, {robot['who']} ({robot['column']})",
        'from_a_run_of_this_project': robot['ours'],
        'voxels': int(len(materials)),
        'materials': {str(k): int((materials == k).sum()) for k in sorted(set(materials.tolist()))},
        'recorded_score': robot['recorded'],
        'score_in_the_campaign_simulator': reference / BODY,
        'score_in_the_recording_simulator': recorded / BODY,
        'score_from_first_and_last_frame': float(np.linalg.norm(cms[-1] - cms[0]) / BODY),
        'frames': int(len(times)),
        'lowest_point_voxels': float(bottoms.min()),
        'centre_height_voxels': [float(cm[:, 2].min()), float(cm[:, 2].max())],
        'highest_point_voxels': float((pos[..., 2] + size[..., 2] / 2).max()),
        'body_lengths_per_cycle': [round(float(v), 3) for v in steps],
        'all_numbers_finite': bool(np.isfinite(frames).all()),
    }


# --------------------------------------------------------------------------------------------
# pictures
# --------------------------------------------------------------------------------------------
def scene(n, materials, span):
    import mujoco
    w, h = PANEL
    bodies = ''.join(
        f'<body name="v{i}" mocap="true"><geom type="box" size="0.5 0.5 0.5" '
        f'rgba="{" ".join(str(v) for v in COLOURS.get(int(m), (0.6, 0.6, 0.6, 1)))}"/></body>'
        for i, m in enumerate(materials))
    xml = f'''<mujoco>
  <visual><global offwidth="{w}" offheight="{h}"/><quality shadowsize="4096"/>
    <headlight ambient="0.50 0.50 0.50" diffuse="0.45 0.45 0.45" specular="0 0 0"/></visual>
  <statistic extent="{span}" center="{span / 2} 0 5"/>
  <asset>
    <texture type="skybox" builtin="flat" rgb1="1 1 1" rgb2="1 1 1" width="32" height="32"/>
    <texture name="squares" type="2d" builtin="checker" rgb1="0.94 0.94 0.94" rgb2="0.82 0.82 0.82" width="256" height="256"/>
    <material name="floor" texture="squares" texrepeat="0.05 0.05" texuniform="true"/>
  </asset>
  <worldbody>
    <light pos="{span / 2} -40 80" dir="0.1 0.45 -1" directional="true" castshadow="true" diffuse="0.55 0.55 0.55" specular="0 0 0"/>
    <geom type="plane" size="{span * 4} {span * 4} 1" material="floor"/>
    <geom type="box" pos="0 0 0.02" size="0.12 {span} 0.02" rgba="0.1 0.1 0.1 1"/>
    {bodies}
  </worldbody>
</mujoco>'''
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    first = model.ngeom - n                        # the voxel boxes are the last n geoms
    return mujoco, model, data, first


def camera(mujoco, span):
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [span / 2 - 6, 0, 4]
    half = math.atan(math.tan(math.radians(22.5)) * PANEL[0] / PANEL[1])
    cam.distance = (span / 2) / math.tan(half) * 1.06
    cam.azimuth = 90
    cam.elevation = -16
    return cam


def render_robot(materials, pos, quat, size, span):
    mujoco, model, data, first = scene(len(materials), materials, span)
    cam = camera(mujoco, span)
    images = []
    with mujoco.Renderer(model, height=PANEL[1], width=PANEL[0]) as renderer:
        for k in range(len(pos)):
            data.mocap_pos[:] = pos[k]
            data.mocap_quat[:] = quat[k]
            model.geom_size[first:] = size[k] / 2
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, cam)
            images.append(renderer.render().copy())
    return images


def font(size):
    from PIL import ImageFont
    for name in ('arial.ttf', 'segoeui.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def assemble(panels, checks, times, slowdown):
    """panels: one list of images per robot, in the order of robots_of(). -> list of PIL frames."""
    from PIL import Image, ImageDraw
    w, h = PANEL
    big, small = font(15), font(12)
    frames = []
    for k in range(len(times)):
        sheet = Image.new('RGB', (2 * w + 6, 2 * h + 6), (255, 255, 255))
        for i, (images, check) in enumerate(zip(panels, checks)):
            im = Image.fromarray(images[k])
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, w, 40], fill=(255, 255, 255))
            d.text((8, 3), check['robot'], fill=(0, 0, 0), font=big)
            now = check['score_in_the_campaign_simulator']
            note = ('its recorded score' if check['from_a_run_of_this_project']
                    else f"recorded as {check['recorded_score']:.2f} by the 2013 build")
            d.text((8, 22), f"{now:.2f} body lengths in 10 cycles ({note}), {check['voxels']} voxels",
                   fill=(60, 60, 60), font=small)
            d.text((8, h - 18), f"cycle {min(times[k] / CYCLE, 10):4.1f} of 10    one square = one body length    "
                                f"slowed {slowdown:.0f}x", fill=(40, 40, 40), font=small)
            sheet.paste(im, ((i % 2) * (w + 6), (i // 2) * (h + 6)))
        frames.append(sheet)
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    ap.add_argument('--arm', required=True, choices=sorted(aa.ARMS))
    ap.add_argument('--every', type=float, default=0.0025, help='simulated seconds between frames (default 0.0025)')
    ap.add_argument('--frame-ms', type=int, default=60, help='milliseconds each frame is shown (default 60)')
    a = ap.parse_args(argv)

    robots = robots_of(a.arm)
    checks, shown = [], []
    for i, robot in enumerate(robots):
        reference, recorded, trace = record(robot, f'arm_{a.arm}_{i}', a.every)
        materials, times, cms, frames = read_trace(trace)
        check = describe(robot, materials, times, cms, frames, reference, recorded)
        shown_score = check['score_in_the_campaign_simulator']
        # Recording must change nothing: the copy that records and the campaign's simulator agree,
        # and the frames themselves give that score.
        for key in ('score_in_the_recording_simulator', 'score_from_first_and_last_frame'):
            if abs(check[key] - shown_score) > 1e-5 * max(1.0, shown_score):
                raise SystemExit(f"{check['robot']}: {key} is {check[key]:.6f} but the campaign's simulator gives "
                                 f"{shown_score:.6f}. The frames would not be the simulation that is scored.")
        # A robot of one of this project's runs was scored by that same simulator: it must repeat.
        # A deposited robot was scored in 2013 by the authors' build; today's build of the same
        # source gives some robots another score (reference README, section 1), so both are kept.
        if robot['ours'] and abs(shown_score - robot['recorded']) > 1e-5 * max(1.0, robot['recorded']):
            raise SystemExit(f"{check['robot']}: scores {shown_score:.6f} now, but its run recorded {robot['recorded']:.6f}.")
        checks.append(check)
        shown.append((materials, times, *for_display(cms, frames)))
        print(f"{check['robot']}: recorded {check['recorded_score']:.4f}, simulated now {shown_score:.4f} "
              f"(recording copy {check['score_in_the_recording_simulator']:.4f}), {check['voxels']} voxels, lowest point "
              f"{check['lowest_point_voxels']:+.2f} voxels, per cycle {check['body_lengths_per_cycle']}")

    n = min(len(s[1]) for s in shown)
    times = shown[0][1][:n]
    span = max(c['score_in_the_campaign_simulator'] for c in checks) * 10 + 28     # voxels: the longest travel, the body, a margin
    panels = [render_robot(m, pos[:n], quat[:n], size[:n], span) for m, _, pos, quat, size, _ in shown]
    slowdown = a.frame_ms / 1000 / a.every
    frames = assemble(panels, checks, times, slowdown)

    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, f'arm_{a.arm}_champions')
    from PIL import Image
    frames[0].save(stem + '.webp', save_all=True, append_images=frames[1:], duration=a.frame_ms, loop=0, quality=72, method=4)
    paletted = [f.quantize(colors=96, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) for f in frames]
    paletted[0].save(stem + '.gif', save_all=True, append_images=paletted[1:], duration=a.frame_ms, loop=0, optimize=True)
    moments = [frames[int(round(q * (len(frames) - 1)))] for q in (0, 0.25, 0.5, 0.75, 1)]
    strip = Image.new('RGB', (moments[0].width, sum(m.height for m in moments) + 4 * 8), (255, 255, 255))
    y = 0
    for m in moments:
        strip.paste(m, (0, y))
        y += m.height + 8
    strip.save(stem + '.png', optimize=True)
    with open(stem + '.json', 'w', encoding='utf-8') as f:
        json.dump({'arm': a.arm, 'seconds_between_frames': a.every, 'slowed_down': slowdown, 'robots': checks}, f, indent=1)
    for ext in ('.gif', '.webp', '.png', '.json'):
        print(f"{os.path.relpath(stem + ext, ROOT)}: {os.path.getsize(stem + ext) / 1e6:.2f} MB")
    return 0


if __name__ == '__main__':
    sys.exit(main())
