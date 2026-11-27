"""Videos of champions moving in the simulator they were evolved in: a look at what the numbers
describe.

For an arm that has been analysed, the champion with the median score and the champion with the
best score are shown below their counterparts among the deposited 2013 runs (the same rule for
every row, nothing picked by eye). Every robot is simulated again for the 0.25 s and 10
actuation cycles of an evaluation, with every voxel's motion recorded.

usage, from the project folder:
    python paper/analysis/render_champions.py --arm R
    python paper/analysis/render_champions.py --rehearsal trialD_s --generation 3
        runs of this project's search in its MuJoCo engine that are NOT an arm (trials); written
        to results/analysis/videos_work/, not to the outcomes

Arms R and Rc are re-runs of the original program; their champions are robot files in the runs'
archives. Arm A is this project's own search in the 2013 simulator; its champions are bodies in
the runs' final populations and are written to a robot file here exactly as the search wrote
them for the simulator (the 2013 settings template with the body filled in). These three are
simulated by the copy of the 2013 simulator that records (build_2013_trace.sh).

Arm D is this project's search in its own MuJoCo engine (added on 27 November 2026, before the
arm was complete). Its two champions are shown in that engine: the evaluation of their run is
run again from the body the run stored, and recorded. A third row shows the same two robots in
the 2013 simulator, which they were not evolved in. Six robots instead of four.

Arms E1 to E3 are arm D with one setting undone each (PROTOCOL.md, section 9.8; added on 27
November 2026, before any of them was started). Their video sets the arm next to arm D: the 2013
originals, arm D's median and best champion in arm D's engine, and the arm's own median and best
champion in the engine with its setting undone. Six robots. They are not shown in the 2013
simulator: the protocol names no transfer outcome for these arms.

    python paper/analysis/render_champions.py --arm E1
    python paper/analysis/render_champions.py --rehearsal trialE1_s --generation 2 --settings-of E1
        trial runs made with arm E1's command: the 2013 originals and the trial's two robots

It writes into paper/outcomes/videos/:
    arm_<X>_champions.gif       the animation (a robot is 1 cm long; the motion is slowed down)
    arm_<X>_champions.webp      the same, smaller and in full colour
    arm_<X>_champions.png       five moments of it, as a still picture
    arm_<X>_champions.json      what was checked on each robot

Checks made on every robot, and written down:
  - in the 2013 simulator: the recording copy gives the score the campaign's simulator gives,
    and, for a robot that one of this project's runs scored there, the score its run recorded
    (so the frames are the simulation that was scored, and recording changes nothing);
  - in the MuJoCo engine: the recorded evaluation gives the score the run recorded, to the last
    digit (so the frames are the evaluation that was scored);
  - the same score follows from the first and last recorded frame;
  - the lowest point of the body over the whole run, the height of its centre, and how far it
    gets in each of the 10 cycles.

The view: the floor's squares are one body length (10 voxels, the unit of the score) wide, every
robot is turned so that it travels to the right, and all share one scale. Colours are those of
the robot files: red and green are the two muscle types (opposite phase), light blue is soft
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
ENGINE_ARM = 'D'                               # the arm whose engine settings a robot has unless it names another
TRANSFER_REPORT = 'transfer_arm_{arm}.json'    # in paper/outcomes/: the arm's champions in the 2013 simulator

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
    """From a list of (score, ...) tuples: the one with the median score (the lower of the two
    middle ones for an even number) and the one with the best."""
    ranked = sorted(champions, key=lambda c: c[0])
    return ranked[(len(ranked) - 1) // 2], ranked[-1]


def population_of(folder):
    with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
        return pickle.load(f)


def search_robot_text(folder, name):
    """A champion of this project's search, as the robot file the 2013 simulator is given: the
    2013 settings template with the body of that individual of the final population. For arm A
    this is the file its run gave the simulator."""
    from src.evolution import cheney2013 as c13
    from src.evolution.voxelyze2013_evaluator import TEMPLATE
    index = int(re.search(r'individual (\d+)$', name).group(1))
    with open(TEMPLATE, encoding='iso-8859-1') as f:
        template = f.read()
    return c13.fill_template(template, c13.workspace_grid(np.asarray(population_of(folder)['genomes'][index])))


def stored_body(folder, name):
    """A champion of this project's search as its run stored it: the array the search evaluated."""
    index = int(re.search(r'individual (\d+)$', name).group(1))
    return np.asarray(population_of(folder)['genomes'][index])


def archived_robot_text(folder, name):
    """A champion of a re-run of the original program, from the archive of its last generation."""
    with tarfile.open(os.path.join(folder, 'Gen_1000.tgz')) as t:
        return t.extractfile(t.getmember('Gen_1000/' + name)).read().decode('iso-8859-1')


def deposited_robot_text(folder, name):
    with open(os.path.join(folder, name), encoding='iso-8859-1') as f:
        return f.read()


def evolved_in_the_engine(arm):
    """Is this an arm whose runs scored their robots in this project's MuJoCo engine (arm D)?"""
    sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
    import search_arm
    spec = search_arm.ARMS.get(arm)
    return bool(spec) and not search_arm.in_the_2013_simulator(spec)


def deposited(condition):
    """[(recorded score, who, folder, file name), ...] of the deposited champions of a condition."""
    out = []
    for c in aa.reference_champions(condition):
        folder = os.path.join(aa.DEPOSITED_ROBOTS, f'2013-01-16-10^3-{condition}', c['run'], 'Gen_1000')
        out.append((c['original'], c['run'].replace('_', ' '), folder, c['file']))
    return out


def transfer_scores_of(arm, outcomes=None):
    """{'seed N': the champion's score in the 2013 simulator} from the arm's committed transfer
    report, or {} while there is none."""
    path = os.path.join(outcomes or aa.OUTCOMES, TRANSFER_REPORT.format(arm=arm))
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return {r['label']: float(r['score']) for r in json.load(f)['champions']}


def originals(condition):
    """The top row of every video: the deposited champions with the median and the best score,
    in the 2013 simulator."""
    theirs = deposited(condition)
    return [{'row': '2013 original', 'column': column, 'who': who, 'recorded': float(score), 'simulator': '2013',
             'vxa': deposited_robot_text(folder, name), 'ours': False}
            for column, (score, who, folder, name) in zip((f'median of {len(theirs)}', f'best of {len(theirs)}'),
                                                          median_and_best(theirs))]


def in_the_engine(champions, label, engine):
    """A row of two: the median and the best of these champions in the MuJoCo engine with the
    settings of the arm `engine`, from the bodies their runs stored. -> (the panels, the two chosen)."""
    chosen = list(zip((f'median of {len(champions)}', f'best of {len(champions)}'), median_and_best(champions)))
    return [{'row': label, 'column': column, 'who': who, 'recorded': float(score), 'simulator': 'mujoco',
             'genome': stored_body(folder, name), 'ours': True, 'engine': engine}
            for column, (score, who, folder, name) in chosen], chosen


def engine_robots(ours, ours_label, condition, transfer=None, engine=ENGINE_ARM, in_2013_too=True):
    """The six panels for runs in the MuJoCo engine. ours: [(recorded score, who, folder, name)].
    Top row: the 2013 originals in the 2013 simulator. Middle row: the runs' median and best
    champion in the MuJoCo engine, where they were evolved. Bottom row: the same two robots in the
    2013 simulator; their score there is on record only once the transfer has been computed.
    in_2013_too=False leaves the bottom row out (runs with the settings of arms E1 to E3)."""
    transfer = transfer or {}
    out = originals(condition)
    row, chosen = in_the_engine(ours, ours_label, engine)
    out += row
    for column, (score, who, folder, name) in chosen if in_2013_too else ():
        out.append({'row': 'the same robot in the 2013 simulator', 'column': column, 'who': who,
                    'recorded': transfer.get(who), 'simulator': '2013', 'vxa': search_robot_text(folder, name),
                    'ours': who in transfer, 'evolved_score': float(score)})
    return out


def sensitivity_robots(ours, arm, undone, baseline, baseline_arm, condition):
    """The six panels of an arm that is another arm with one setting undone (E1 to E3 and arm D).
    Top row: the 2013 originals in the 2013 simulator. Middle row: the other arm's median and best
    champion in its engine. Bottom row: this arm's median and best champion in its own engine,
    the one with the setting undone. Nothing is shown in a simulator it was not evolved in."""
    return (originals(condition) + in_the_engine(baseline, f'arm {baseline_arm}', baseline_arm)[0]
            + in_the_engine(ours, f'arm {arm}: {undone}', arm)[0])


def champions_of(arm):
    """[(recorded score, 'seed N', run folder, which individual)] from an arm's committed report."""
    spec = aa.ARMS[arm]
    report = aa.finished_arm(arm)
    if report is None:
        raise SystemExit(f'Arm {arm} has no report in paper/outcomes yet. Videos are made of analysed arms.')
    folder = aa.SEARCH_RUNS if spec['kind'] == 'search' else aa.RERUNS
    return [(row['champion']['original'], f"seed {row['seed']}", os.path.join(folder, f"{spec['prefix']}{row['seed']}"),
             row['champion']['file']) for row in report['per_seed']]


def robots_of(arm):
    """The panels of an analysed arm, in the order they are shown (two to a row)."""
    spec = aa.ARMS[arm]
    search = spec['kind'] == 'search'
    ours = champions_of(arm)
    if evolved_in_the_engine(arm) and spec.get('sensitivity'):
        # arms E1 to E3: next to arm D, whose report their own analysis has already needed
        return sensitivity_robots(ours, arm, spec['undone'], champions_of(spec['against']), spec['against'],
                                  spec['condition'])
    if evolved_in_the_engine(arm):
        return engine_robots(ours, f'own search, arm {arm}, MuJoCo engine', spec['condition'], transfer_scores_of(arm),
                             engine=arm)
    theirs = deposited(spec['condition'])
    ours_label = f'own search 2026, arm {arm}' if search else f're-run 2026, arm {arm}'
    ours_text = search_robot_text if search else archived_robot_text
    out = []
    for row_label, group, text_of, is_ours in (('2013 original', theirs, deposited_robot_text, False),
                                               (ours_label, ours, ours_text, True)):
        for column, (score, who, folder, name) in zip((f'median of {len(group)}', f'best of {len(group)}'),
                                                      median_and_best(group)):
            out.append({'row': row_label, 'column': column, 'who': who, 'recorded': float(score), 'simulator': '2013',
                        'vxa': text_of(folder, name), 'ours': is_ours})
    return out


def rehearsal_robots(prefix, generation, results=None, settings_of=ENGINE_ARM):
    """The same six panels for runs of the search in the MuJoCo engine that are not an arm: every
    complete run <prefix><seed> with that many generations. settings_of: the arm whose command
    the runs were made with. With the settings of arms E1 to E3 the bottom row, the 2013
    simulator, is left out, as it is for those arms."""
    results = results or aa.SEARCH_RUNS
    ours = []
    for d in sorted(os.listdir(results)):
        tail = d[len(prefix):]
        if not (d.startswith(prefix) and tail.isdigit() and os.path.isdir(os.path.join(results, d))):
            continue
        run = aa.load_search_run(os.path.join(results, d), int(tail))
        if aa.is_complete(run, generation):
            aa.load_search_champion(run)
            ours.append((run['champion']['original'], f'seed {int(tail)}', run['folder'], run['champion']['file']))
    if len(ours) < 3:
        raise SystemExit(f'Fewer than 3 complete runs named {prefix}<seed> have {generation} generations.')
    return engine_robots(sorted(ours, key=lambda c: int(c[1].split()[1])),
                         f'trial runs {prefix} (not an arm), MuJoCo engine', 'noCost', engine=settings_of,
                         in_2013_too=not aa.ARMS[settings_of].get('sensitivity'))


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


def engine_parameters(arm=ENGINE_ARM):
    """What a run of that arm hands its evaluation, the search's early stop included: the preset
    of the arm's command with the options the command gives next to it (arm D: --preset
    cheney2013-floor and nothing else)."""
    import transfer_scores as ts
    import search_arm                       # on the path once transfer_scores is loaded
    preset, given = search_arm.engine_options(search_arm.ARMS[arm])
    return ts.worker_parameters(ts.evaluator_arguments(early_stop=True, preset=preset, given=given))


def record_in_the_engine(robot, every, params=None):
    """The evaluation of the robot's run, run again from the body the run stored, with the state
    of every voxel kept (render_transfer.mujoco_frames; lengths come back in the 2013 simulator's
    units so that both simulators are drawn by the same code).
    -> score, blew up, materials, times, centre of mass, voxel states."""
    import render_transfer as rt
    return rt.mujoco_frames(robot['genome'], params or engine_parameters(robot.get('engine', ENGINE_ARM)), every)


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


def motion(materials, times, cms, frames):
    """What the recorded frames say, in the units of the score (body lengths) and of the body (voxels)."""
    pos, _, size, cm = for_display(cms, frames)
    bottoms = pos[..., 2] - size[..., 2] / 2
    at_cycle = [float(np.interp(k * CYCLE, times, cm[:, 0])) / (BODY * 1000) for k in range(11)]
    return {
        'voxels': int(len(materials)),
        'materials': {str(k): int((materials == k).sum()) for k in sorted(set(materials.tolist()))},
        'score_from_first_and_last_frame': float(np.linalg.norm(cms[-1] - cms[0]) / BODY),
        'frames': int(len(times)),
        'lowest_point_voxels': float(bottoms.min()),
        'centre_height_voxels': [float(cm[:, 2].min()), float(cm[:, 2].max())],
        'highest_point_voxels': float((pos[..., 2] + size[..., 2] / 2).max()),
        'body_lengths_per_cycle': [round(float(v), 3) for v in np.diff(at_cycle)],
        'all_numbers_finite': bool(np.isfinite(frames).all()),
    }


def describe(robot, materials, times, cms, frames, reference, recorded):
    """The checks on a robot simulated in the 2013 simulator. reference, recorded: the distance
    the campaign's simulator and the recording copy report, in metres."""
    m = motion(materials, times, cms, frames)
    return {
        'robot': f"{robot['row']}, {robot['who']} ({robot['column']})",
        'from_a_run_of_this_project': robot['ours'],
        'voxels': m['voxels'], 'materials': m['materials'],
        'recorded_score': robot['recorded'],
        'score_in_the_campaign_simulator': reference / BODY,
        'score_in_the_recording_simulator': recorded / BODY,
        'score_from_first_and_last_frame': m['score_from_first_and_last_frame'],
        'frames': m['frames'],
        'lowest_point_voxels': m['lowest_point_voxels'],
        'centre_height_voxels': m['centre_height_voxels'],
        'highest_point_voxels': m['highest_point_voxels'],
        'body_lengths_per_cycle': m['body_lengths_per_cycle'],
        'all_numbers_finite': m['all_numbers_finite'],
    }


def describe_in_the_engine(robot, materials, times, cms, frames, score, blew_up):
    """The checks on a robot whose evaluation in the MuJoCo engine was run again and recorded."""
    out = {'robot': f"{robot['row']}, {robot['who']} ({robot['column']})", 'simulator': 'the MuJoCo engine',
           'from_a_run_of_this_project': True, 'recorded_score': robot['recorded'],
           'score_of_the_recorded_evaluation': float(score),
           'identical_to_the_last_digit': bool(score == robot['recorded']), 'blew_up': bool(blew_up)}
    out.update(motion(materials, times, cms, frames))
    return out


def captions(robot, check):
    """The two lines above a robot's view."""
    if robot.get('simulator') == 'mujoco':
        return (f"{robot['row']}, {robot['who']} ({robot['column']})",
                f"{check['score_of_the_recorded_evaluation']:.2f} body lengths in 10 cycles (its recorded score), "
                f"{check['voxels']} voxels")
    now = check['score_in_the_campaign_simulator']
    if 'evolved_score' in robot:
        return (f"{robot['row']}, {robot['who']}",
                f"{now:.2f} body lengths in 10 cycles, {now / robot['evolved_score']:.2f} of its score in the engine")
    note = 'its recorded score' if check['from_a_run_of_this_project'] else f"recorded as {check['recorded_score']:.2f} by the 2013 build"
    return check['robot'], f"{now:.2f} body lengths in 10 cycles ({note}), {check['voxels']} voxels"


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


def fitting(text, width, sizes=(15, 14, 13, 12, 11)):
    """The largest of the sizes at which the text is no wider than width pixels."""
    for size in sizes:
        f = font(size)
        if f.getlength(text) <= width:
            return f
    return f


def assemble(panels, lines, times, slowdown):
    """panels: one list of images per robot, in the order they are shown, two to a row.
    lines: the two lines above each robot's view. -> list of PIL frames."""
    from PIL import Image, ImageDraw
    w, h = PANEL
    small = font(12)
    titles = [fitting(first, w - 16) for first, _ in lines]
    seconds = [fitting(second, w - 16, (12, 11, 10)) for _, second in lines]
    rows = (len(panels) + 1) // 2
    frames = []
    for k in range(len(times)):
        sheet = Image.new('RGB', (2 * w + 6, rows * (h + 6) - 6), (255, 255, 255))
        for i, (images, (first, second)) in enumerate(zip(panels, lines)):
            im = Image.fromarray(images[k])
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, w, 40], fill=(255, 255, 255))
            d.text((8, 3), first, fill=(0, 0, 0), font=titles[i])
            d.text((8, 22), second, fill=(60, 60, 60), font=seconds[i])
            d.text((8, h - 18), f"cycle {min(times[k] / CYCLE, 10):4.1f} of 10    one square = one body length    "
                                f"slowed {slowdown:.0f}x", fill=(40, 40, 40), font=small)
            sheet.paste(im, ((i % 2) * (w + 6), (i // 2) * (h + 6)))
        frames.append(sheet)
    return frames


def simulate(robot, tag, every, params=None):
    """One robot simulated again and recorded, with its checks. A check that fails stops the script:
    the frames would not show what was scored. -> (check, materials, times, centre of mass, frames)."""
    if robot.get('simulator') == 'mujoco':
        score, blew_up, materials, times, cms, frames = record_in_the_engine(robot, every, params)
        check = describe_in_the_engine(robot, materials, times, cms, frames, score, blew_up)
        if not check['identical_to_the_last_digit']:
            raise SystemExit(f"{check['robot']}: the recorded evaluation scores {score!r}, its run recorded "
                             f"{robot['recorded']!r}. The frames would not be the evaluation that was scored.")
        if abs(check['score_from_first_and_last_frame'] - score) > 1e-6 * max(1.0, score):
            raise SystemExit(f"{check['robot']}: the frames give {check['score_from_first_and_last_frame']:.6f}, the "
                             f"evaluation {score:.6f}.")
        return check, materials, times, cms, frames
    reference, recorded, trace = record(robot, tag, every)
    materials, times, cms, frames = read_trace(trace)
    check = describe(robot, materials, times, cms, frames, reference, recorded)
    shown_score = check['score_in_the_campaign_simulator']
    # Recording must change nothing: the copy that records and the campaign's simulator agree,
    # and the frames themselves give that score.
    for key in ('score_in_the_recording_simulator', 'score_from_first_and_last_frame'):
        if abs(check[key] - shown_score) > 1e-5 * max(1.0, shown_score):
            raise SystemExit(f"{check['robot']}: {key} is {check[key]:.6f} but the campaign's simulator gives "
                             f"{shown_score:.6f}. The frames would not be the simulation that is scored.")
    # A robot that one of this project's runs scored in this simulator must repeat that score. A
    # deposited robot was scored in 2013 by the authors' build; today's build of the same source
    # gives some robots another score (reference README, section 1), so both are kept. A robot
    # evolved in the MuJoCo engine has a score here only once its transfer has been computed.
    if robot['ours'] and abs(shown_score - robot['recorded']) > 1e-5 * max(1.0, robot['recorded']):
        raise SystemExit(f"{check['robot']}: scores {shown_score:.6f} now, but {robot['recorded']:.6f} is on record.")
    if 'evolved_score' in robot:
        check['simulator'] = 'the 2013 simulator, which it was not evolved in'
        check['score_in_the_engine_it_was_evolved_in'] = robot['evolved_score']
        check['share_of_that_score'] = shown_score / robot['evolved_score']
        check['score_is_that_of_the_transfer_report'] = bool(robot['ours'])
    return check, materials, times, cms, frames


def shown_score_of(check):
    return check.get('score_of_the_recorded_evaluation', check.get('score_in_the_campaign_simulator'))


def same_robot_in_both(robots, checks, recorded):
    """A robot shown in the engine and once more in the 2013 simulator must be one body: the same
    voxels of the same materials in the same places, started at the same height. Stops the script
    otherwise; marks the check of the 2013 view. recorded: (materials, voxel states) per robot."""
    import render_transfer as rt
    for i, robot in enumerate(robots):
        if 'evolved_score' not in robot:
            continue
        twin = [k for k, other in enumerate(robots) if other.get('simulator') == 'mujoco' and other['who'] == robot['who']]
        if len(twin) != 1:
            raise SystemExit(f"{checks[i]['robot']}: its view in the MuJoCo engine is not among the robots shown.")
        (m13, f13), (mmj, fmj) = recorded[i], recorded[twin[0]]
        if not rt.same_body(m13, f13[0], mmj, fmj[0]):
            raise SystemExit(f"{checks[i]['robot']}: the two simulators do not hold the same body.")
        if abs(fmj[0][:, 2].min() - f13[0][:, 2].min()) > 1e-9:
            raise SystemExit(f"{checks[i]['robot']}: the body does not start at the same height in the two simulators.")
        checks[i]['same_voxels_materials_and_height_as_in_the_engine'] = True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--arm', choices=sorted(aa.ARMS))
    what.add_argument('--rehearsal', metavar='PREFIX',
                      help='runs in the MuJoCo engine that are not an arm: the start of their folder names')
    ap.add_argument('--generation', type=int, help='rehearsal only: the generations each run has')
    ap.add_argument('--settings-of', default=ENGINE_ARM, choices=[n for n in sorted(aa.ARMS) if evolved_in_the_engine(n)],
                    help='rehearsal only: the arm whose command the runs were made with (default D)')
    ap.add_argument('--every', type=float, default=0.0025, help='simulated seconds between frames (default 0.0025)')
    ap.add_argument('--frame-ms', type=int, default=60, help='milliseconds each frame is shown (default 60)')
    a = ap.parse_args(argv)

    if a.arm:
        robots, name, out_dir = robots_of(a.arm), f'arm_{a.arm}', OUT
    else:
        if not a.generation:
            ap.error('--rehearsal needs --generation')
        robots = rehearsal_robots(a.rehearsal, a.generation, settings_of=a.settings_of)
        name, out_dir = f'rehearsal_{a.rehearsal}', WORK
    # the settings of each arm whose engine a robot is shown in: an arm E next to arm D has two
    params = {arm: engine_parameters(arm) for arm in sorted({r['engine'] for r in robots if r.get('simulator') == 'mujoco'})}
    checks, shown, recorded = [], [], []
    for i, robot in enumerate(robots):
        check, materials, times, cms, frames = simulate(robot, f'{name}_{i}', a.every, params.get(robot.get('engine')))
        checks.append(check)
        shown.append((materials, times, *for_display(cms, frames)))
        recorded.append((materials, frames))
        print(f"{check['robot']}: recorded "
              + ('nowhere yet' if check['recorded_score'] is None else f"{check['recorded_score']:.4f}")
              + f", simulated now {shown_score_of(check):.4f}, {check['voxels']} voxels, lowest point "
              f"{check['lowest_point_voxels']:+.2f} voxels, per cycle {check['body_lengths_per_cycle']}")

    same_robot_in_both(robots, checks, recorded)

    n = min(len(s[1]) for s in shown)
    times = shown[0][1][:n]
    span = max(shown_score_of(c) for c in checks) * 10 + 28      # voxels: the longest travel, the body, a margin
    panels = [render_robot(m, pos[:n], quat[:n], size[:n], span) for m, _, pos, quat, size, _ in shown]
    slowdown = a.frame_ms / 1000 / a.every
    frames = assemble(panels, [captions(r, c) for r, c in zip(robots, checks)], times, slowdown)

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, f'{name}_champions')
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
        json.dump({'arm': a.arm, 'rehearsal': a.rehearsal, 'seconds_between_frames': a.every, 'slowed_down': slowdown,
                   'robots': checks}, f, indent=1)
    for ext in ('.gif', '.webp', '.png', '.json'):
        print(f"{os.path.relpath(stem + ext, ROOT)}: {os.path.getsize(stem + ext) / 1e6:.2f} MB")
    return 0


if __name__ == '__main__':
    sys.exit(main())
