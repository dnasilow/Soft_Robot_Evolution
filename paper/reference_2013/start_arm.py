"""Start, watch, stop or check one arm of the campaign that re-executes the ORIGINAL 2013 experiment.

The arms are those of paper/PROTOCOL.md: the authors' search program driving the authors'
simulator (both built here from their source), seeds 1 to 35, 1000 generations each.
    R    no cost
    Rc   actuated-voxel cost (the program's -P 2)

usage, from the project folder:
    python paper/reference_2013/start_arm.py --arm R                        start it
    python paper/reference_2013/start_arm.py --arm R --status               where every run is; starts nothing
    python paper/reference_2013/start_arm.py --arm R --watch                follow its progress in this window
    python paper/reference_2013/start_arm.py --arm R --stop                 stop its runs
    python paper/reference_2013/start_arm.py --arm R --restart-incomplete   start it again after an interruption

How it runs
  - The runs are looked after by a launcher WITHOUT a window, started through the Windows shell,
    so it depends neither on the program the command was typed in nor on any console window.
    The window that opens only shows the progress. Closing it stops nothing; --watch opens the
    view again and --stop is the way to stop the runs. (Until 23 November 2026 the window WAS
    the campaign, and a closed window cost arm Rc nine hours.)
  - Logging off, restarting Windows or shutting WSL down still ends the runs.
  - The launcher keeps Windows awake for as long as it runs (the keep-awake of
    run_tendon_evolution.py).
  - It starts the runs through run_2013_search.sh. Finished runs are skipped, runs in progress
    are left alone, and a second launcher for the same arm is refused. If runs are in progress
    without a launcher (it was ended, the runs were not), starting again adopts them.
  - Every few minutes it copies the learning curves to results/rerun2013/ and writes one line of
    progress: generations and time, not scores.
  - At the end it checks that every seed finished with the expected number of generations and
    writes the comparison with the deposited runs (summarise_reruns.py).

After an interruption the unfinished runs cannot be continued. --restart-incomplete moves their
folders to runs/_interrupted/ on the WSL side and starts those seeds again from the beginning.
The program is deterministic for a given seed, so the repeat is the same run.

--here runs the launcher in the current console instead (for trials). --seeds, --gens and --tag
are for trials of the launcher itself. They need a --tag of their own, so a trial can never be
written into, or mistaken for, an arm of the campaign.
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
import traceback

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
ENDED_LINE = 'launcher ended'
# Every child process is started without a console window and in a process group of its own:
# nothing typed or closed in any window reaches the runs.
HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)

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


def running_seeds(st):
    return [s for s, (g, state) in st.items() if state == 'running']


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


def window_command_text(arm_name, host_args, watch_args, python=None, pythonw=None, script=None):
    """Text of the .cmd file the Windows shell opens: it starts the launcher without a window
    (pythonw has none, and `start` does not tie it to this console) and then shows its progress.
    Only the progress view lives in the window."""
    script = script or os.path.abspath(__file__)
    python = python or sys.executable
    pythonw = pythonw or os.path.join(os.path.dirname(python), 'pythonw.exe')
    line = lambda exe, args: subprocess.list2cmdline([exe, script] + args).replace('%', '%%')   # noqa: E731
    return '\n'.join([
        '@echo off',
        f'title Soft robot campaign, arm {arm_name} - progress only, closing this window does NOT stop the runs',
        f'cd /d "{ROOT}"',
        'start "" ' + line(pythonw, host_args),
        line(python, watch_args),
        'echo.',
        'echo This window only showed the progress. It can be closed.',
        'pause > nul',
    ]) + '\n'


def latest_launch_offset(log_bytes):
    """Where the latest launch begins in the launcher's log (byte offset of its first line)."""
    at = log_bytes.rfind(STARTED_LINE.encode())
    return log_bytes.rfind(b'\n', 0, at) + 1 if at >= 0 else 0


# --------------------------------------------------------------------------------------------
# the launcher's lock: who is looking after this arm
# --------------------------------------------------------------------------------------------
def take_lock(path):
    """Take the launcher's lock for an arm. Returns the open file to keep for as long as the
    lock is wanted, or None if another process holds it. Windows releases it when the holder
    ends, however it ends."""
    import msvcrt
    f = open(path, 'a+b')
    try:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        f.close()
        return None
    return f


def launcher_alive(stem):
    """Is a launcher looking after this arm right now?"""
    import msvcrt
    f = take_lock(os.path.join(OUT, f'{stem}_host.lock'))
    if f is None:
        return True
    f.seek(0)
    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    f.close()
    return False


# --------------------------------------------------------------------------------------------
# talking to WSL, logging
# --------------------------------------------------------------------------------------------
def say(text=''):
    stamp = datetime.datetime.now().strftime('%d %b %H:%M')
    for line in (str(text).splitlines() or ['']):
        out = f'[{stamp}] {line}'
        print(out, flush=True)                  # goes nowhere when there is no console
        if LOG:
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write(out + '\n')


def run_bash(script, timeout=900):
    """Run a bash script inside WSL (fed on standard input); returns (exit code, output)."""
    p = subprocess.run(['wsl', '-d', DISTRO, '--', 'bash', '-s'], input=script.encode('utf-8'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                       creationflags=HIDDEN)
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
        return subprocess.run(['git', '-C', ROOT] + list(a), stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=60, creationflags=HIDDEN).stdout.rstrip('\n')
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


def has_console_window():
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:                                        # noqa: BLE001
        return True


# --------------------------------------------------------------------------------------------
# the modes
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
    alive = launcher_alive(prefix[:-2])
    print(f"  launcher: {'running' if alive else 'not running'}")
    if running_seeds(st) and not alive:
        print('  NOTE: runs are in progress but nothing looks after them, so Windows may go to sleep.')
        print('        Starting the arm again adopts them.')
    return 0 if len(done) == len(seeds) else 1


def passthrough(a, for_launcher):
    """The arguments a second copy of this program needs to mean the same arm or trial."""
    args = []
    for flag, value in (('--seeds', a.seeds), ('--gens', a.gens), ('--tag', a.tag)):
        if value is not None:
            args += [flag, str(value)]
    if for_launcher:
        args += ['--interval', str(a.interval)]
        if a.jobs is not None:
            args += ['--jobs', str(a.jobs)]
        if a.restart_incomplete:
            args.append('--restart-incomplete')
    return args


def start(a, prefix, seeds, generations):
    """Start the windowless launcher through the Windows shell, with a window that shows its progress."""
    stem = prefix[:-2]
    if launcher_alive(stem):
        print(f"This arm's launcher is running already. Its progress:\n"
              f"  python paper\\reference_2013\\start_arm.py --arm {a.arm}{trial_args(a)} --watch")
        return 3
    going = running_seeds(read_status(prefix, seeds))
    if going:
        print(f'{len(going)} runs of this arm are in progress without a launcher. Starting one to look after them.')
    os.makedirs(OUT, exist_ok=True)
    before = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    cmd_file = os.path.join(OUT, f'{stem}_window.cmd')
    with open(cmd_file, 'w', encoding='mbcs', newline='\r\n') as f:
        f.write(window_command_text(a.arm, ['--arm', a.arm, '--host'] + passthrough(a, True),
                                    ['--arm', a.arm, '--watch', '--from-byte', str(before)] + passthrough(a, False)))
    # explorer.exe hands the file to the Windows shell, which opens it as a double click would:
    # what it starts belongs to the shell, not to the program this command was typed in.
    subprocess.Popen(['explorer.exe', cmd_file])
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        if os.path.exists(LOG) and os.path.getsize(LOG) > before:
            with open(LOG, encoding='utf-8', errors='replace') as f:
                f.seek(before)
                new = f.read()
            if STARTED_LINE in new:
                here = f'python paper\\reference_2013\\start_arm.py --arm {a.arm}{trial_args(a)}'
                print(f'Arm {a.arm} is starting. Its launcher has no window; the window that opened only shows progress.')
                print('  Closing that window stops nothing. Logging off or restarting Windows does.')
                print(f'  Where every run is:  {here} --status')
                print(f'  Progress view:       {here} --watch')
                print(f'  Stop the runs:       {here} --stop')
                print(f'  Log:                 {os.path.relpath(LOG, ROOT)}')
                return 0
    print(f'No sign of the launcher after 3 minutes. Start it by double-clicking\n  {cmd_file}')
    return 1


def watch(a, prefix, from_byte=None):
    """Follow the launcher's log in this console until the launcher has ended. Stops nothing."""
    stem = prefix[:-2]
    data = b''
    if os.path.exists(LOG):
        with open(LOG, 'rb') as f:
            data = f.read()
    pos = min(from_byte, len(data)) if from_byte is not None else latest_launch_offset(data)
    started = from_byte is None and bool(data)
    waited = quiet = 0
    try:
        while True:
            chunk = b''
            if os.path.exists(LOG):
                with open(LOG, 'rb') as f:
                    f.seek(pos)
                    chunk = f.read()
            cut = chunk.rfind(b'\n') + 1
            if cut:
                text = chunk[:cut].decode('utf-8', errors='replace')
                sys.stdout.write(text)
                sys.stdout.flush()
                pos += cut
                started = started or STARTED_LINE in text or ENDED_LINE in text
                quiet = 0
            elif started and not launcher_alive(stem):
                quiet += 1
                if quiet >= 3:
                    print('\nThe launcher is not running (any more). Where every run is:')
                    print(f'  python paper\\reference_2013\\start_arm.py --arm {a.arm}{trial_args(a)} --status')
                    return 0
            elif not started:
                waited += 1
                if waited > 90:
                    print('The launcher did not start within 3 minutes.')
                    return 1
            time.sleep(2)
    except KeyboardInterrupt:
        print('\n(view closed; the runs are not affected)')
        return 0


def stop(a, prefix, seeds, generations):
    """Stop the runs of this arm. Their launcher then ends by itself."""
    stem = prefix[:-2]
    code, text = run_bash(shell_script('stop_2013_runs.sh', PREFIX=prefix))
    print(text.strip())
    for _ in range(45):
        if not launcher_alive(stem):
            break
        time.sleep(2)
    else:
        print('The launcher is still running; look at its log.')
    show_status(prefix, seeds, generations)
    return 0 if code == 0 else 1


def run_launcher(a, arm, prefix, seeds, generations):
    """The launcher itself: starts the runs, keeps Windows awake, reports, checks the end.
    Runs without a window (--host) or in the current console (--here)."""
    tag = a.tag or arm['tag']       # the run folders are <tag>_P<penalty>_s<seed>
    stem = prefix[:-2]              # <tag>_P<penalty>, the start of this arm's file names
    lock = None
    for _ in range(10):             # a --status or --watch may hold the lock for an instant while it looks
        lock = take_lock(os.path.join(OUT, f'{stem}_host.lock'))
        if lock is not None:
            break
        time.sleep(0.3)
    if lock is None:
        say(f'A launcher is looking after arm {a.arm} already. Nothing started here.')
        say(ENDED_LINE)
        return 4
    stop_awake = None
    try:
        say(f"{STARTED_LINE} (process {os.getpid()}, {'in a console' if has_console_window() else 'no window'}): "
            f"arm {a.arm}, runs {prefix}{seeds[0]} to {prefix}{seeds[-1]} ({len(seeds)} seeds), {generations} generations each")
        if a.here and 'CLAUDECODE' in os.environ:
            say('NOTE: this console belongs to the Claude app. A launcher started here ends when the app closes. '
                'Without --here it is started through the Windows shell.')
        if not a.tag:
            with open(PROTOCOL, encoding='utf-8') as f:
                if not protocol_is_frozen(f.read()):
                    say('paper/PROTOCOL.md is not frozen. An arm of the campaign starts only after the freeze.')
                    return 2

        stop_awake, awake = keep_awake()
        say(awake)
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
                                    stdout=sink, stderr=subprocess.STDOUT, creationflags=HIDDEN)
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

        def report():
            try:
                st = read_status(prefix, seeds)
                say(progress_line(st, generations, start_times(prefix, seeds), time.time()))
                return st
            except Exception as e:                           # noqa: BLE001  the monitor must never stop the runs
                say(f'(could not read the progress this time: {e})')
                return None

        stopped = False
        adopted = False
        last_ctrl_c = 0.0
        next_report = time.time() + 90
        while True:
            try:
                echo_script_output()
                if not adopted and proc.poll() is not None:
                    if proc.returncode != 4:
                        break
                    # Another launch script holds the arm inside WSL. No launcher is alive (this
                    # one holds the lock), so those runs lost theirs: look after them from here.
                    st = report()
                    if st is None or not running_seeds(st):
                        say('A launch of this arm is still open inside WSL but none of its runs is alive. '
                            'Nothing started here.')
                        return 4
                    say('These runs are in progress without a launcher. Looking after them from here: '
                        'keeping Windows awake and reporting until they end.')
                    adopted = True
                    next_report = time.time() + a.interval * 60
                if time.time() >= next_report:
                    next_report = time.time() + a.interval * 60
                    st = report()
                    if adopted and st is not None and not running_seeds(st):
                        break
                time.sleep(2)
            except KeyboardInterrupt:                        # only with --here: a launcher without a window has no keys
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
        python = os.path.join(os.path.dirname(sys.executable), 'python.exe')      # not pythonw: this one prints
        summary = subprocess.run([python if os.path.exists(python) else sys.executable,
                                  os.path.join(HERE, 'summarise_reruns.py'), prefix,
                                  '--condition', arm['condition']], stdin=subprocess.DEVNULL,
                                 capture_output=True, creationflags=HIDDEN)
        say((summary.stdout + summary.stderr).decode('utf-8', errors='replace').rstrip())
        return 0
    except SystemExit as e:
        if isinstance(e.code, str):
            say(e.code)
            return 2
        raise
    except BaseException:                                    # noqa: BLE001  a launcher without a window must leave a trace
        say(traceback.format_exc())
        raise
    finally:
        if stop_awake:
            stop_awake()
        say(ENDED_LINE)
        lock.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    ap.add_argument('--arm', required=True, choices=sorted(ARMS))
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--status', action='store_true', help='report where every run is and start nothing')
    mode.add_argument('--watch', action='store_true', help='follow the progress in this console; stops nothing')
    mode.add_argument('--stop', action='store_true', help='stop the runs of this arm')
    mode.add_argument('--here', action='store_true', help='run the launcher in this console (for trials)')
    mode.add_argument('--host', action='store_true', help=argparse.SUPPRESS)      # the launcher without a window
    ap.add_argument('--restart-incomplete', action='store_true',
                    help='start unfinished seeds again from the beginning (their folders are moved aside)')
    ap.add_argument('--jobs', type=int, help='runs side by side (default: all seeds at once; each uses one core)')
    ap.add_argument('--interval', type=float, default=10.0, help='minutes between progress lines (default 10)')
    ap.add_argument('--seeds', help=f'trial only: seeds, e.g. 1-2 (the arm uses {PROTOCOL_SEEDS})')
    ap.add_argument('--gens', type=int, help='trial only: generations (the arm uses the settings file, 1000)')
    ap.add_argument('--tag', help='trial only: name of the trial; required with --seeds or --gens')
    ap.add_argument('--from-byte', type=int, help=argparse.SUPPRESS)              # --watch: where to begin in the log
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
    global LOG
    os.makedirs(OUT, exist_ok=True)
    LOG = os.path.join(OUT, f'{prefix[:-2]}_launcher.log')
    if a.status:
        return show_status(prefix, seeds, generations)
    if a.watch:
        return watch(a, prefix, a.from_byte)
    if a.stop:
        return stop(a, prefix, seeds, generations)
    if a.here or a.host:
        return run_launcher(a, arm, prefix, seeds, generations)
    return start(a, prefix, seeds, generations)


if __name__ == '__main__':
    sys.exit(main())
