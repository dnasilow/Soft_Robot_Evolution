"""The arms of the campaign that are run with this project's own search (run_tendon_evolution.py).
Used through start_arm.py, which hands itself over as `core`:

    python paper/reference_2013/start_arm.py --arm A             start it, or continue it
    python paper/reference_2013/start_arm.py --arm A --status    where every run is; starts nothing
    python paper/reference_2013/start_arm.py --arm A --watch     follow its progress
    python paper/reference_2013/start_arm.py --arm A --stop      stop its runs

    A    this project's CPPN-NEAT as it is (--no-age-pareto) in the original 2013 simulator,
         no cost, seeds 1 to 35, 1000 generations, population 30 (paper/PROTOCOL.md)

How these arms differ from the re-runs of the original program (R, Rc)
  - A run is one `python run_tendon_evolution.py ... --seed <s> --name armA_s<s>` process. It
    saves a checkpoint after every generation and, started again with the same command, goes on
    from it with its random state restored. So stopping costs nothing: unfinished runs are
    CONTINUED, never started over.
  - That is why the launcher owns its runs: if it ends, however it ends, Windows ends them with
    it (a job object). Starting the arm again continues them. Closing the progress window still
    stops nothing.
  - A run that ends without finishing is continued automatically, a few times at most.
  - The code that computes a run (run_tendon_evolution.py and src/) must be the code tagged
    campaign-v2; the launcher refuses to start an arm otherwise. (campaign-v2 is campaign-v1
    with one correction, PROTOCOL.md section 9.3: a continued run now repeats the
    uninterrupted one exactly.)
  - Runs side by side: all of them by default, each simulating one robot at a time (--workers),
    the pattern of arm R, which keeps every core busy.

Files: results/<run>/ as written by run_tendon_evolution.py; the launcher's own log, its launch
records and each run's console output are in results/campaign/.
"""
import datetime
import glob
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'results', 'campaign')
RESULTS = os.path.join(ROOT, 'results')
RUNNER = os.path.join(ROOT, 'run_tendon_evolution.py')
TEMPLATE = os.path.join(ROOT, 'src', 'evolution', 'voxelyze2013_template.vxa')

ARMS = {
    'A': {'tag': 'armA', 'generations': 1000, 'condition': 'noCost',
          'runner': ['--simulator', 'voxelyze2013', '--no-age-pareto', '--pop', '30']},
}
CODE_TAG = 'campaign-v2'
RUN_DEFINING = ['run_tendon_evolution.py', 'src']
MAX_ATTEMPTS = 6            # times one run is started or continued by one launcher


# --------------------------------------------------------------------------------------------
# pure helpers (tested in tests/test_search_arm.py)
# --------------------------------------------------------------------------------------------
def run_name(stem, seed):
    return f'{stem}_s{seed}'


def runner_command(arm, python, stem, seed, generations, workers):
    """The command of one run. The same command continues the run from its checkpoint."""
    return ([python, RUNNER] + list(arm['runner'])
            + ['--gen', str(generations), '--workers', str(workers), '--seed', str(seed),
               '--name', run_name(stem, seed)])


def run_state(folder, generations):
    """(generations recorded, state) of one run folder, from its files alone.
    finished      the run wrote its final files and has all its generations
    interrupted   it has begun and can be continued from its checkpoint
    not started   nothing there yet"""
    done = 0
    while os.path.isfile(os.path.join(folder, f'gen_{done + 1:03d}.json')):
        done += 1
    finished = (done >= generations and os.path.isfile(os.path.join(folder, 'final_population.pkl'))
                and os.path.isfile(os.path.join(folder, 'best_robot.pkl'))
                and not os.path.isfile(os.path.join(folder, 'checkpoint.pkl')))
    if finished:
        return done, 'finished'
    if done or os.path.isdir(folder) and os.listdir(folder):
        return done, 'interrupted'
    return 0, 'not started'


def statuses(stem, seeds, generations, running=(), failed=None, results=None):
    """{seed: (generations, state)} in the words start_arm.progress_line understands."""
    out = {}
    for s in seeds:
        done, state = run_state(os.path.join(results or RESULTS, run_name(stem, s)), generations)
        if state != 'finished' and s in running:
            state = 'running'
        elif state != 'finished' and failed and str(s) in failed:
            state = f"FAILED ({failed[str(s)]})"
        out[s] = (done, state)
    return out


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def code_differs_from_tag(creationflags=0, tag=None, root=None):
    """None if the files that compute a run are, as they stand on disk, those of the campaign's
    code tag; otherwise a sentence saying what is wrong."""
    tag, root = tag or CODE_TAG, root or ROOT

    def git(*a):
        return subprocess.run(['git', '-C', root] + list(a), stdin=subprocess.DEVNULL, capture_output=True,
                              creationflags=creationflags).returncode
    if git('rev-parse', '--verify', '--quiet', tag + '^{commit}') != 0:
        return f'The tag {tag} does not exist in this repository.'
    if git('diff', '--quiet', tag, '--', *RUN_DEFINING) != 0:
        return f'run_tendon_evolution.py or src/ differ from the code tagged {tag}.'
    return None


# --------------------------------------------------------------------------------------------
# Windows: every process this launcher starts ends when the launcher ends
# --------------------------------------------------------------------------------------------
def own_children():
    """Put this process into a job object that ends all its processes when the last handle to
    it closes, which is when this process ends, however it ends. Children join the job by
    themselves. Returns the handle, to be kept."""
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                    ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ('ReadOperationCount', 'WriteOperationCount',
                                                   'OtherOperationCount', 'ReadTransferCount',
                                                   'WriteTransferCount', 'OtherTransferCount')]

    class Extended(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', Basic), ('IoInfo', IoCounters),
                    ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]

    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.GetCurrentProcess.restype = wintypes.HANDLE
    job = k.CreateJobObjectW(None, None)
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not k.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)) \
            or not k.AssignProcessToJobObject(job, k.GetCurrentProcess()):
        raise OSError(f'could not set up the job object (Windows error {ctypes.get_last_error()})')
    return job


# --------------------------------------------------------------------------------------------
# the modes
# --------------------------------------------------------------------------------------------
def read_state_file(stem):
    try:
        with open(os.path.join(OUT, f'{stem}_state.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def current_statuses(core, stem, seeds, generations):
    """Statuses as anyone can see them: from the run folders, plus what a live launcher reports."""
    alive = core.launcher_alive(stem)
    state = read_state_file(stem) if alive else {}
    return alive, statuses(stem, seeds, generations, set(state.get('running', ())), state.get('failed'))


def show_status(core, a, stem, seeds, generations):
    alive, st = current_statuses(core, stem, seeds, generations)
    print(core.progress_line(st, generations))
    groups = {}
    for s, (g, state) in sorted(st.items()):
        groups.setdefault(state, []).append(f'{s} ({g})' if state != 'not started' else str(s))
    for state, members in groups.items():
        print(f"  {state}, seed (generations): {', '.join(members)}")
    done = core.complete_seeds(st, generations)
    print(f'  complete: {len(done)} of {len(seeds)}')
    print(f"  launcher: {'running' if alive else 'not running'}")
    if not alive and len(done) < len(seeds):
        print('  Unfinished runs are continued from their checkpoints when the arm is started again.')
    return 0 if len(done) == len(seeds) else 1


def stop(core, a, stem, seeds, generations):
    if not core.launcher_alive(stem):
        print('No launcher is running for this arm, so none of its runs is running.')
        return show_status(core, a, stem, seeds, generations)
    with open(os.path.join(OUT, f'{stem}_stop.request'), 'w') as f:
        f.write(datetime.datetime.now().isoformat())
    print('Asked the launcher to stop its runs ...')
    for _ in range(60):
        if not core.launcher_alive(stem):
            break
        time.sleep(2)
    else:
        print('The launcher is still running; look at its log.')
    show_status(core, a, stem, seeds, generations)
    return 0


def start(core, a, stem):
    if core.launcher_alive(stem):
        print(f"This arm's launcher is running already. Its progress:\n"
              f"  python paper\\reference_2013\\start_arm.py --arm {a.arm}{core.trial_args(a)} --watch")
        return 3
    return core.launch_through_shell(a, stem)


def run_launcher(core, a, arm, stem, seeds, generations):
    """The launcher of a search arm: starts or continues the runs, keeps Windows awake, reports,
    checks the end. Without a window (--host) or in the current console (--here)."""
    say = core.say
    lock = None
    for _ in range(10):
        lock = core.take_lock(os.path.join(OUT, f'{stem}_host.lock'))
        if lock is not None:
            break
        time.sleep(0.3)
    if lock is None:
        say(f'A launcher is looking after arm {a.arm} already. Nothing started here.')
        say(core.ENDED_LINE)
        return 4
    stop_awake = None
    active = {}
    try:
        jobs = a.jobs or len(seeds)
        workers = a.workers or 1
        say(f"{core.STARTED_LINE} (process {os.getpid()}, {'in a console' if core.has_console_window() else 'no window'}): "
            f"arm {a.arm}, runs {run_name(stem, seeds[0])} to {run_name(stem, seeds[-1])} ({len(seeds)} seeds), "
            f"{generations} generations each; {jobs} side by side, {workers} simulation(s) at a time in each")
        if a.here and 'CLAUDECODE' in os.environ:
            say('NOTE: this console belongs to the Claude app. A launcher started here ends when the app closes. '
                'Without --here it is started through the Windows shell.')
        git = core.git_state()
        if not a.tag:
            with open(core.PROTOCOL, encoding='utf-8') as f:
                if not core.protocol_is_frozen(f.read()):
                    say('paper/PROTOCOL.md is not frozen. An arm of the campaign starts only after the freeze.')
                    return 2
            problem = code_differs_from_tag(core.HIDDEN)
            if problem:
                say(f'{problem} An arm of the campaign runs from that code; nothing started.')
                return 2

        stop_awake, awake = core.keep_awake()
        say(awake)
        info = core.programs()                       # the 2013 simulator and its settings
        record = {
            'time': datetime.datetime.now().isoformat(timespec='seconds'),
            'arm': a.arm, 'stem': stem, 'seeds': seeds, 'generations': generations, 'jobs': jobs,
            'workers': workers, 'runner_arguments': arm['runner'], 'command': sys.argv,
            'launcher_pid': os.getpid(), 'git': git,
            'simulator_sha256': info['sha256']['voxelize'], 'template_sha256': sha256(TEMPLATE),
            'python': platform.python_version(), 'windows': platform.platform(), 'keep_awake': awake,
        }
        launches = os.path.join(OUT, f'{stem}_launches.json')
        earlier = []
        if os.path.exists(launches):
            with open(launches, encoding='utf-8') as f:
                earlier = json.load(f)
        for key in ('simulator_sha256', 'template_sha256'):
            if earlier and earlier[0][key] != record[key]:
                say('The 2013 simulator or its settings template has changed since this arm was first launched. '
                    'All runs of an arm must come from one build; nothing started.')
                return 2
        with open(launches, 'w', encoding='utf-8') as f:
            json.dump(earlier + [record], f, indent=1)
        say(f"code {git.get('describe', '?')}"
            + (f", modified tracked files: {git['modified']}" if git.get('modified') else '')
            + f"; simulator {record['simulator_sha256'][:12]}, settings template {record['template_sha256'][:12]}")

        own_children()          # from here on, whatever this launcher starts ends with it
        stop_request = os.path.join(OUT, f'{stem}_stop.request')
        if os.path.exists(stop_request):
            os.remove(stop_request)
        logs = os.path.join(OUT, f'{stem}_logs')
        os.makedirs(logs, exist_ok=True)
        python = os.path.join(os.path.dirname(sys.executable), 'python.exe')
        python = python if os.path.exists(python) else sys.executable
        environment = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8:backslashreplace')

        st = statuses(stem, seeds, generations)
        pending = [s for s in seeds if st[s][1] != 'finished']
        say(f"{len(seeds) - len(pending)} runs are complete already, "
            f"{sum(1 for s in pending if st[s][1] == 'interrupted')} are continued from their checkpoints, "
            f"{sum(1 for s in pending if st[s][1] == 'not started')} start from the beginning.")
        attempts = {s: 0 for s in seeds}
        failed = {}

        written = [None, 0.0]

        def write_state():
            """What --status cannot see in the run folders: which runs this launcher has going."""
            snapshot = (tuple(sorted(active)), tuple(pending), tuple(sorted(failed.items())))
            if snapshot == written[0] and time.time() - written[1] < 30:
                return
            try:
                tmp = os.path.join(OUT, f'{stem}_state.json.tmp')
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump({'time': time.time(), 'running': sorted(active), 'waiting': pending, 'failed': failed}, f)
                os.replace(tmp, os.path.join(OUT, f'{stem}_state.json'))
                written[0], written[1] = snapshot, time.time()
            except OSError:                                  # someone is reading it this instant; next time
                pass

        def spawn(seed):
            attempts[seed] += 1
            command = runner_command(arm, python, stem, seed, generations, workers)
            with open(os.path.join(logs, run_name(stem, seed) + '.log'), 'ab') as log:
                log.write(f"\n=== {datetime.datetime.now().isoformat(timespec='seconds')} attempt {attempts[seed]}: "
                          f"{subprocess.list2cmdline(command[1:])}\n".encode('utf-8'))
                log.flush()
                return subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, creationflags=core.HIDDEN)

        def last_lines(seed, n=3):
            try:
                with open(os.path.join(logs, run_name(stem, seed) + '.log'), 'rb') as f:
                    f.seek(max(0, os.path.getsize(f.name) - 2000))
                    lines = [l for l in f.read().decode('utf-8', errors='replace').splitlines() if l.strip()]
                return ' / '.join(l.strip()[:160] for l in lines[-n:])
            except OSError:
                return ''

        stopped = False
        next_report = time.time() + 90
        while pending or active:
            try:
                while pending and len(active) < jobs:
                    seed = pending.pop(0)
                    active[seed] = spawn(seed)
                for seed, process in list(active.items()):
                    code = process.poll()
                    if code is None:
                        continue
                    del active[seed]
                    done, state = run_state(os.path.join(RESULTS, run_name(stem, seed)), generations)
                    if state == 'finished':
                        say(f'{run_name(stem, seed)}: complete')
                    elif attempts[seed] < MAX_ATTEMPTS:
                        say(f'{run_name(stem, seed)}: ended with code {code} at generation {done}; continuing it from '
                            f'its checkpoint (start {attempts[seed] + 1} of {MAX_ATTEMPTS}). Its last lines: {last_lines(seed)}')
                        pending.append(seed)
                    else:
                        failed[str(seed)] = f'ended {attempts[seed]} times, last with code {code}'
                        say(f'{run_name(stem, seed)}: ended {attempts[seed]} times without finishing; left as it is. '
                            f'Its last lines: {last_lines(seed)}')
                if os.path.exists(stop_request):
                    say(f'Stop requested: ending {len(active)} runs. They keep their checkpoints.')
                    for process in active.values():
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdin=subprocess.DEVNULL,
                                       capture_output=True, creationflags=core.HIDDEN)
                    for process in active.values():
                        try:
                            process.wait(30)
                        except subprocess.TimeoutExpired:
                            pass
                    active.clear()
                    os.remove(stop_request)
                    stopped = True
                    break
                write_state()
                if time.time() >= next_report:
                    next_report = time.time() + a.interval * 60
                    say(core.progress_line(statuses(stem, seeds, generations, set(active), failed), generations))
                time.sleep(2)
            except KeyboardInterrupt:                        # only with --here
                say('Ctrl+C: ending the runs. They keep their checkpoints.')
                stopped = True
                break

        st = statuses(stem, seeds, generations, (), failed)
        done = core.complete_seeds(st, generations)
        say(core.progress_line(st, generations))
        say(f'{len(done)} of {len(seeds)} runs are complete with {generations} generations.')
        here = f'python paper\\reference_2013\\start_arm.py --arm {a.arm}{core.trial_args(a)}'
        if len(done) < len(seeds):
            say(f'To continue the unfinished runs from their checkpoints:  {here}')
            return 130 if stopped else 1
        say('The arm is complete. Its analysis is a separate step:  python paper\\analysis\\analyse_arm.py '
            f'--arm {a.arm}' if not a.tag else 'The trial is complete.')
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
        for process in active.values():                      # the job object would do it too
            try:
                process.kill()
            except OSError:
                pass
        if stop_awake:
            stop_awake()
        say(core.ENDED_LINE)
        lock.close()


def main(core, a, ap, seeds):
    """Called by start_arm.main for the arms listed in ARMS."""
    arm = ARMS[a.arm]
    if a.restart_incomplete:
        ap.error(f'runs of arm {a.arm} are continued from their checkpoints, never started over: '
                 f'start the arm again without --restart-incomplete')
    if a.workers is not None and a.workers < 1:
        ap.error('--workers must be at least 1')
    generations = a.gens or arm['generations']
    stem = a.tag or arm['tag']
    core.OUT = OUT                                           # this kind of arm keeps its launcher files here
    os.makedirs(OUT, exist_ok=True)
    core.LOG = os.path.join(OUT, f'{stem}_launcher.log')
    prefix = stem + '_s'                                     # core.watch and core.launch_through_shell derive the stem from it
    if a.status:
        return show_status(core, a, stem, seeds, generations)
    if a.watch:
        return core.watch(a, prefix, a.from_byte)
    if a.stop:
        return stop(core, a, stem, seeds, generations)
    if a.here or a.host:
        return run_launcher(core, a, arm, stem, seeds, generations)
    return start(core, a, stem)
