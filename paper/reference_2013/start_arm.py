"""Start, or check, one arm of the campaign that re-executes the ORIGINAL 2013 experiment.

The arms are those of paper/PROTOCOL.md: the authors' search program driving the authors'
simulator (both built here from their source), seeds 1 to 35, 1000 generations each.
    R    no cost
    Rc   actuated-voxel cost (the program's -P 2)

usage, from the project folder:
    python paper/reference_2013/start_arm.py --arm R                        start it, in a window of its own
    python paper/reference_2013/start_arm.py --arm R --status               where every run is; starts nothing
    python paper/reference_2013/start_arm.py --arm R --restart-incomplete   after an interruption

What it does
  - Opens a console window of its own, through the Windows shell, so that it does not depend on
    the program the command was typed in, and runs there (--here runs in the current console
    instead). That window IS the campaign: the runs live in a WSL session that this program
    holds open, and closing the window stops them.
  - Keeps Windows awake for as long as it runs (the keep-awake of run_tendon_evolution.py).
  - Starts the runs through run_2013_search.sh. Finished runs are skipped, runs in progress are
    left alone, and a second launcher for the same arm is refused.
  - Every few minutes copies the learning curves to results/rerun2013/ and prints one line of
    progress: generations and time, not scores.
  - At the end checks that every seed finished with the expected number of generations and
    prints the comparison with the deposited runs (summarise_reruns.py).

After an interruption (a restart of Windows, a power cut, a closed window) the unfinished runs
cannot be continued. --restart-incomplete moves their folders to runs/_interrupted/ on the WSL
side and starts those seeds again from the beginning. The program is deterministic for a given
seed, so the repeat is the same run.

--seeds, --gens and --tag are for trials of the launcher itself. They need a --tag of their own,
so a trial can never be written into, or mistaken for, an arm of the campaign.
"""
import argparse
import contextlib
import datetime
import io
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'results', 'rerun2013')
PROTOCOL = os.path.join(ROOT, 'paper', 'PROTOCOL.md')
SETTINGS = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad', 'softbots2013Config',
                        'config', 'softbotTest.dat')
DISTRO = os.environ.get('VOXELYZE2013_WSL_DISTRO', 'Ubuntu')

ARMS = {
    'R':  {'tag': 'armR',  'penalty': 0, 'condition': 'noCost'},
    'Rc': {'tag': 'armRc', 'penalty': 2, 'condition': 'costNumActuated'},
}
PROTOCOL_SEEDS = '1-35'
STARTED_LINE = 'launcher started'
# The WSL child gets its own process group, so a Ctrl+C typed in the console reaches this
# program only and the runs are not stopped by a stray key press.
NEW_GROUP = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)

LOG = None          # the launcher's own log file, set once the arm is known


# --------------------------------------------------------------------------------------------
# small pure helpers (tested in tests/test_start_arm.py)
# --------------------------------------------------------------------------------------------
def parse_seeds(text):
    """'1-35' or '1-3,7,10-12' -> list of seeds."""
    seeds = []
    for part in text.replace(' ', '').split(','):
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', part)
        if not m:
            raise ValueError(f"cannot read seeds from '{text}'")
        first, last = int(m.group(1)), int(m.group(2) or m.group(1))
        if last < first:
            raise ValueError(f"cannot read seeds from '{text}'")
        seeds.extend(range(first, last + 1))
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"a seed is listed twice in '{text}'")
    return seeds


def shell_script(name, **settings):
    """Text of one of the bash scripts of this folder, with its settings exported in front."""
    with open(os.path.join(HERE, name), 'rb') as f:
        body = f.read().replace(b'\r', b'').decode('utf-8')
    head = ''
    for key, value in settings.items():
        if value is None or value == '':
            continue
        if not re.fullmatch(r'[A-Za-z0-9_ ]+', str(value)):
            raise ValueError(f'{key}: unexpected characters in {value!r}')
        head += f"export {key}='{value}'\n"
    return head + body


STATUS_LINE = re.compile(r'^(\S+): (\d+) generations, (finished|running|interrupted|FAILED.*)$')


def parse_status(text, prefix, seeds):
    """Output of collect_2013_runs.sh -> {seed: (generations, state)} for the seeds asked for."""
    found = {}
    for line in text.splitlines():
        m = STATUS_LINE.match(line.strip())
        if m and m.group(1).startswith(prefix) and m.group(1)[len(prefix):].isdigit():
            found[int(m.group(1)[len(prefix):])] = (int(m.group(2)), m.group(3))
    return {s: found.get(s, (0, 'not started')) for s in seeds}


def complete_seeds(st, generations):
    return [s for s, (g, state) in st.items() if state == 'finished' and g == generations]


def hours(seconds):
    return f'{seconds / 3600:.1f} h' if seconds >= 5400 else f'{max(1, round(seconds / 60))} min'


def progress_line(st, generations, started=None, now=None):
    """One line on where the runs are. started: {seed: epoch seconds}."""
    kinds = {}
    for s, (g, state) in st.items():
        kinds.setdefault(state.split()[0], []).append(s)
    order = ['running', 'finished', 'interrupted', 'FAILED', 'not']
    names = {'not': 'not started'}
    parts = [f"{len(kinds[k])} {names.get(k, k)}" for k in order if k in kinds]
    line = f"{len(st)} runs: {', '.join(parts)}."
    going = [g for g, state in st.values() if state == 'running']
    if going:
        line += (f" Generation of {generations}: slowest {min(going)}, median "
                 f"{int(statistics.median(going))}, fastest {max(going)}.")
        if started and now and min(going) >= 5:              # earlier than that the pace says nothing
            left = [(generations - g) * (now - started[s]) / g
                    for s, (g, state) in st.items() if state == 'running' and s in started]
            if left:
                line += f" At its pace so far the slowest run needs about {hours(max(left))} more."
    short = [s for s, (g, state) in st.items() if state == 'finished' and g != generations]
    if short:
        line += f" FINISHED WITH THE WRONG NUMBER OF GENERATIONS: seeds {short}."
    for k in ('interrupted', 'FAILED'):
        if k in kinds:
            line += f" {k}: seeds {sorted(kinds[k])}."
    return line


def protocol_is_frozen(text):
    """True if the status line of PROTOCOL.md (the first bold line) says it is frozen."""
    for line in text.splitlines():
        if line.startswith('**'):
            return line.startswith('**Frozen on ')
    return False


def settings_generations(text):
    m = re.search(r'^MaxGenerations\s+([0-9.]+)', text, re.M)
    return int(float(m.group(1))) if m else None


def trial_args(a):
    """The extra arguments that name a trial, for the commands this program suggests."""
    if not a.tag:
        return ''
    return f' --tag {a.tag} --seeds {a.seeds or PROTOCOL_SEEDS}' + (f' --gens {a.gens}' if a.gens else '')


def window_command_text(arm_name, child_args, python=None, script=None):
    """Text of the .cmd file that runs this launcher in a console window of its own."""
    command = subprocess.list2cmdline([python or sys.executable, script or os.path.abspath(__file__)] + child_args)
    return '\n'.join([
        '@echo off',
        f'title Soft robot campaign, arm {arm_name} - keep this window open',
        f'cd /d "{ROOT}"',
        command.replace('%', '%%'),
        'echo.',
        'echo The launcher has ended. Press a key to close this window.',
        'pause > nul',
    ]) + '\n'


# --------------------------------------------------------------------------------------------
# talking to WSL, logging
# --------------------------------------------------------------------------------------------
def say(text=''):
    stamp = datetime.datetime.now().strftime('%d %b %H:%M')
    for line in (str(text).splitlines() or ['']):
        out = f'[{stamp}] {line}'
        print(out, flush=True)
        if LOG:
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write(out + '\n')


def run_bash(script, timeout=900):
    """Run a bash script inside WSL (fed on standard input); returns (exit code, output)."""
    p = subprocess.run(['wsl', '-d', DISTRO, '--', 'bash', '-s'], input=script.encode('utf-8'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                       creationflags=NEW_GROUP)
    return p.returncode, p.stdout.decode('utf-8', errors='replace')


def read_status(prefix, seeds):
    code, text = run_bash(shell_script('collect_2013_runs.sh', PREFIX=prefix))
    if code != 0:
        raise RuntimeError(f'collect_2013_runs.sh ended with code {code}: {text.strip()[-300:]}')
    return parse_status(text, prefix, seeds)


def start_times(prefix, seeds):
    out = {}
    for s in seeds:
        try:
            with open(os.path.join(OUT, f'{prefix}{s}', 'started')) as f:
                out[s] = int(f.read().strip())
        except (OSError, ValueError):
            pass
    return out


def git_state():
    def git(*a):
        return subprocess.run(['git', '-C', ROOT] + list(a), capture_output=True, text=True,
                              timeout=60, creationflags=NEW_GROUP).stdout.rstrip('\n')
    try:
        return {'commit': git('rev-parse', 'HEAD'),
                'describe': git('describe', '--tags', '--always'),
                'modified': [l for l in git('status', '--porcelain', '--untracked-files=no').splitlines() if l]}
    except Exception as e:                                   # noqa: BLE001
        return {'unavailable': str(e)}


PROGRAMS_SCRIPT = r'''
H=~/softbots2013_ref/softbots/hyperneat/HyperNEAT_v2_5
for f in ~/softbots2013_ref/softbots/Voxel_Sim_NoGui/voxelize "$H/HyperNEAT/out/Hypercube_NEAT" \
         "$H/HyperNEAT/out/libNEAT.so" "$H/tinyxmldll/out/libtinyxmldll.so" "$H/zlib/out/libzlib.so" \
         /mnt/c/SoftRobotEvolution/research_reference/extracted/dryad/softbots2013Config/config/softbotTest.dat; do
  if [ -e "$f" ]; then echo "sha256 $(basename "$f") $(sha256sum "$f" | cut -d' ' -f1)"; else echo "missing $f"; fi
done
echo "compiler $(g++ --version | head -1)"
echo "kernel $(uname -r)"
echo "cpu $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')"
echo "logical_cpus $(nproc)"
command -v flock > /dev/null || echo "missing flock"
'''


def programs():
    """Hashes of the two programs, their libraries and the settings file, and the build host."""
    code, text = run_bash(PROGRAMS_SCRIPT, timeout=300)
    info = {'sha256': {}}
    missing = []
    for line in text.splitlines():
        p = line.split(None, 2 if line.startswith('sha256') else 1)
        if line.startswith('sha256 ') and len(p) == 3:
            info['sha256'][p[1]] = p[2]
        elif line.startswith('missing '):
            missing.append(p[1])
        elif len(p) == 2 and p[0] in ('compiler', 'kernel', 'cpu', 'logical_cpus'):
            info[p[0]] = p[1]
    if code != 0 or missing or len(info['sha256']) != 6:
        raise SystemExit('The 2013 programs are not all in place inside WSL'
                         + (f" (missing: {', '.join(missing)})" if missing else f': {text.strip()[-300:]}')
                         + '. Build them with build_2013_simulator.sh and build_2013_search.sh.')
    return info


def keep_awake():
    """The project's own keep-awake. Returns (stop function, the status line it printed)."""
    sys.path.insert(0, ROOT)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            from run_tendon_evolution import _prevent_sleep
            stop = _prevent_sleep()
    except Exception as e:                                   # noqa: BLE001
        raise SystemExit(f'Could not switch on the keep-awake of run_tendon_evolution.py ({e}). '
                         f'Start this with the Python that runs the project.')
    return stop, ' '.join(buffer.getvalue().replace('—', '-').split())


# --------------------------------------------------------------------------------------------
# the three modes
# --------------------------------------------------------------------------------------------
def show_status(prefix, seeds, generations):
    st = read_status(prefix, seeds)
    print(progress_line(st, generations, start_times(prefix, seeds), time.time()))
    groups = {}
    for s, (g, state) in sorted(st.items()):
        groups.setdefault(state, []).append(f'{s} ({g})' if state != 'not started' else str(s))
    for state, members in groups.items():
        print(f"  {state}, seed (generations): {', '.join(members)}")
    done = complete_seeds(st, generations)
    print(f'  complete: {len(done)} of {len(seeds)}')
    return 0 if len(done) == len(seeds) else 1


def open_own_window(a, prefix, seeds, generations):
    st = read_status(prefix, seeds)
    going = [s for s, (g, state) in st.items() if state == 'running']
    if going:
        print(f'Runs of this arm are in progress already ({len(going)} running); not opening another '
              f'window. --status shows them.')
        return 3
    child = ['--arm', a.arm, '--here', '--interval', str(a.interval)]
    for flag, value in (('--seeds', a.seeds), ('--gens', a.gens), ('--tag', a.tag), ('--jobs', a.jobs)):
        if value is not None:
            child += [flag, str(value)]
    if a.restart_incomplete:
        child.append('--restart-incomplete')
    os.makedirs(OUT, exist_ok=True)
    cmd_file = os.path.join(OUT, f'{prefix[:-2]}_window.cmd')
    with open(cmd_file, 'w', encoding='mbcs', newline='\r\n') as f:
        f.write(window_command_text(a.arm, child))
    before = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    # explorer.exe hands the file to the Windows shell, which opens it as a double click would:
    # the new window belongs to the shell, not to the program this command was typed in.
    subprocess.Popen(['explorer.exe', cmd_file])
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        if os.path.exists(LOG) and os.path.getsize(LOG) > before:
            with open(LOG, encoding='utf-8', errors='replace') as f:
                f.seek(before)
                new = f.read()
            if STARTED_LINE in new:
                print(f'Arm {a.arm} is starting in a window of its own.')
                print('  That window is the campaign: keep it open, and do not log off or restart Windows.')
                print(f'  Progress:  python paper\\reference_2013\\start_arm.py --arm {a.arm}{trial_args(a)} --status')
                print(f'  Log:       {os.path.relpath(LOG, ROOT)}')
                return 0
    print(f'No sign of the launcher after 3 minutes. Start it by double-clicking\n  {cmd_file}')
    return 1


def run_here(a, arm, prefix, seeds, generations):
    tag = a.tag or arm['tag']       # the run folders are <tag>_P<penalty>_s<seed>
    stem = prefix[:-2]              # <tag>_P<penalty>, the start of this arm's file names
    say(f"{STARTED_LINE} (process {os.getpid()}): arm {a.arm}, runs {prefix}{seeds[0]} to {prefix}{seeds[-1]} "
        f"({len(seeds)} seeds), {generations} generations each")
    if 'CLAUDECODE' in os.environ:
        say('NOTE: this console belongs to the Claude app. Runs started here stop when the app closes. '
            'Without --here the launcher opens a window of its own.')
    if not a.tag:
        with open(PROTOCOL, encoding='utf-8') as f:
            if not protocol_is_frozen(f.read()):
                say('paper/PROTOCOL.md is not frozen. An arm of the campaign starts only after the freeze.')
                return 2

    stop_awake, awake = keep_awake()
    say(awake)
    try:
        info = programs()
        record = {
            'time': datetime.datetime.now().isoformat(timespec='seconds'),
            'arm': a.arm, 'tag': tag, 'penalty': arm['penalty'], 'seeds': seeds, 'generations': generations,
            'jobs': a.jobs or len(seeds), 'restart_incomplete': bool(a.restart_incomplete),
            'command': sys.argv, 'launcher_pid': os.getpid(), 'git': git_state(), 'programs': info,
            'python': platform.python_version(), 'windows': platform.platform(), 'keep_awake': awake,
        }
        launches = os.path.join(OUT, f'{stem}_launches.json')
        earlier = []
        if os.path.exists(launches):
            with open(launches, encoding='utf-8') as f:
                earlier = json.load(f)
        if earlier and earlier[0]['programs']['sha256'] != info['sha256']:
            say('The 2013 programs or the settings file have changed since this arm was first launched. '
                'All runs of an arm must come from one build; nothing started.')
            return 2
        with open(launches, 'w', encoding='utf-8') as f:
            json.dump(earlier + [record], f, indent=1)
        say(f"code {record['git'].get('describe', '?')}"
            + (f", modified tracked files: {record['git']['modified']}" if record['git'].get('modified') else '')
            + f"; search program {info['sha256']['Hypercube_NEAT'][:12]}, simulator {info['sha256']['voxelize'][:12]}")

        script = shell_script('run_2013_search.sh', SEEDS=' '.join(map(str, seeds)), GENS=a.gens,
                              PENALTY=arm['penalty'], TAG=tag, JOBS=a.jobs or len(seeds),
                              RESTART_INCOMPLETE=1 if a.restart_incomplete else None)
        wsl_log = os.path.join(OUT, f"{stem}_launcher_wsl_{datetime.datetime.now():%Y%m%d-%H%M%S}.log")
        seen = 0
        with open(wsl_log, 'wb') as sink:
            # Output goes to a file, not to a pipe into this program: the runs must not depend on
            # this program reading them. One file per launch; its lines are repeated in the log.
            proc = subprocess.Popen(['wsl', '-d', DISTRO, '--', 'bash', '-s'], stdin=subprocess.PIPE,
                                    stdout=sink, stderr=subprocess.STDOUT, creationflags=NEW_GROUP)
        proc.stdin.write(script.encode('utf-8'))
        proc.stdin.close()

        def echo_script_output():
            nonlocal seen
            with open(wsl_log, 'rb') as f:
                f.seek(seen)
                data = f.read()
            cut = data.rfind(b'\n') + 1
            if cut:
                seen += cut
                say('\n'.join('  | ' + l for l in data[:cut].decode('utf-8', errors='replace').splitlines()))

        stopped = False
        last_ctrl_c = 0.0
        next_report = time.time() + 90
        while True:
            try:
                echo_script_output()
                if proc.poll() is not None:
                    break
                if time.time() >= next_report:
                    next_report = time.time() + a.interval * 60
                    try:
                        st = read_status(prefix, seeds)
                        say(progress_line(st, generations, start_times(prefix, seeds), time.time()))
                    except Exception as e:                   # noqa: BLE001  the monitor must never stop the runs
                        say(f'(could not read the progress this time: {e})')
                time.sleep(2)
            except KeyboardInterrupt:
                if time.time() - last_ctrl_c <= 5:
                    say('Stopping all runs of this arm ...')
                    proc.terminate()
                    try:
                        proc.wait(30)
                    except subprocess.TimeoutExpired:
                        pass
                    try:
                        say(run_bash(shell_script('stop_2013_runs.sh', PREFIX=prefix))[1].strip())
                    except Exception as e:                   # noqa: BLE001
                        say(f'(stop script: {e})')
                    stopped = True
                    break
                last_ctrl_c = time.time()
                say('Ctrl+C: the runs keep going. To stop them all, press Ctrl+C again within 5 seconds. '
                    'Stopped runs lose their work; finished runs are kept.')
        echo_script_output()

        code = proc.returncode
        if code == 4:
            say('Another launcher is handling this arm. Nothing was started here.')
            return 4
        try:
            st = read_status(prefix, seeds)
        except Exception as e:                               # noqa: BLE001
            say(f'Could not read the final state: {e}')
            return 1
        done = complete_seeds(st, generations)
        say(progress_line(st, generations))
        say(f'{len(done)} of {len(seeds)} runs are complete with {generations} generations.')
        if len(done) < len(seeds):
            say('To run the unfinished seeds again from the beginning:')
            say(f'  python paper\\reference_2013\\start_arm.py --arm {a.arm}{trial_args(a)} --restart-incomplete')
            return 1 if not stopped else 130
        summary = subprocess.run([sys.executable, os.path.join(HERE, 'summarise_reruns.py'), prefix,
                                  '--condition', arm['condition']], capture_output=True, creationflags=NEW_GROUP)
        say((summary.stdout + summary.stderr).decode('utf-8', errors='replace').rstrip())
        return 0
    finally:
        stop_awake()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    ap.add_argument('--arm', required=True, choices=sorted(ARMS))
    ap.add_argument('--status', action='store_true', help='report where every run is and start nothing')
    ap.add_argument('--here', action='store_true', help='run in this console instead of a window of its own')
    ap.add_argument('--restart-incomplete', action='store_true',
                    help='start unfinished seeds again from the beginning (their folders are moved aside)')
    ap.add_argument('--jobs', type=int, help='runs side by side (default: all seeds at once; each uses one core)')
    ap.add_argument('--interval', type=float, default=10.0, help='minutes between progress lines (default 10)')
    ap.add_argument('--seeds', help=f'trial only: seeds, e.g. 1-2 (the arm uses {PROTOCOL_SEEDS})')
    ap.add_argument('--gens', type=int, help='trial only: generations (the arm uses the settings file, 1000)')
    ap.add_argument('--tag', help='trial only: name of the trial; required with --seeds or --gens')
    a = ap.parse_args(argv)

    if (a.seeds or a.gens) and not a.tag:
        ap.error('--seeds and --gens change the arm; such a trial needs a --tag of its own')
    if a.tag and (a.tag in {v['tag'] for v in ARMS.values()} or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', a.tag)):
        ap.error('--tag must be letters and digits, and not the name of a campaign arm')
    if a.jobs is not None and a.jobs < 1:
        ap.error('--jobs must be at least 1')
    try:
        seeds = parse_seeds(a.seeds or PROTOCOL_SEEDS)
    except ValueError as e:
        ap.error(str(e))
    arm = ARMS[a.arm]
    with open(SETTINGS, encoding='utf-8', errors='replace') as f:
        generations = a.gens or settings_generations(f.read())
    if not generations:
        raise SystemExit(f'cannot read MaxGenerations from {SETTINGS}')
    prefix = f"{a.tag or arm['tag']}_P{arm['penalty']}_s"

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    if a.status:
        return show_status(prefix, seeds, generations)
    global LOG
    os.makedirs(OUT, exist_ok=True)
    LOG = os.path.join(OUT, f'{prefix[:-2]}_launcher.log')
    if a.here:
        return run_here(a, arm, prefix, seeds, generations)
    return open_own_window(a, prefix, seeds, generations)


if __name__ == '__main__':
    sys.exit(main())
