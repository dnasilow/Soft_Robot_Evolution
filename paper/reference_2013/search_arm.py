"""The arms of the campaign that are run with this project's own search (run_tendon_evolution.py).
Used through start_arm.py, which hands itself over as `core`:

    python paper/reference_2013/start_arm.py --arm A             start it, or continue it
    python paper/reference_2013/start_arm.py --arm A --status    where every run is; starts nothing
    python paper/reference_2013/start_arm.py --arm A --watch     follow its progress
    python paper/reference_2013/start_arm.py --arm A --stop      stop its runs

    A    this project's CPPN-NEAT as it is (--no-age-pareto) in the original 2013 simulator,
         no cost, seeds 1 to 35, 1000 generations, population 30 (paper/PROTOCOL.md)
    D    the same search in this project's MuJoCo engine with --preset cheney2013-floor,
         no cost, seeds 1 to 10, 300 generations, population 30 (PROTOCOL.md, sections 2 and 9.5)
    E1   arm D with one setting undone, seeds 1 to 3, 300 generations (PROTOCOL.md, section 9.8):
         global damping back to 0.01 (--damping-global 0.01)
    E2   the same with the actuation back to +-20% with the volumetric law (--amp 0.2 --poisson on)
    E3   the same with the engine's hard floor and bodies set on it (--preset cheney2013)

    python paper/reference_2013/start_arm.py --arm E1 --after D
         start arm E1 as soon as arm D is complete; if arm D ends unfinished, start nothing

How these arms differ from the re-runs of the original program (R, Rc)
  - A run is one `python run_tendon_evolution.py ... --seed <s> --name armA_s<s>` process. It
    saves a checkpoint after every generation and, started again with the same command, goes on
    from it with its random state restored. So stopping costs nothing: unfinished runs are
    CONTINUED, never started over.
  - That is why the launcher owns its runs: if it ends, however it ends, Windows ends them with
    it (a job object). Starting the arm again continues them. Closing the progress window still
    stops nothing.
  - A run that ends without finishing is continued automatically, a few times at most.
  - The code that computes a run (run_tendon_evolution.py and src/) must be the code of the
    arm's tag; the launcher refuses to start an arm otherwise. Arm A: campaign-v2, which is
    campaign-v1 with one correction (PROTOCOL.md section 9.3: a continued run now repeats the
    uninterrupted one exactly). Arms D and E1 to E3: campaign-v4 (sections 9.5 and 9.6).
  - Runs side by side: all of them by default. In arm A each simulates one robot at a time, the
    pattern of arm R, which keeps every core busy with 35 runs. Arm D has 10 runs, so each
    simulates three robots at a time (--workers); the scores do not depend on that number. Arms
    E1 to E3 have 3 runs each, with three robots at a time in arms E1 and E3 and five in arm E2,
    whose robots take about twice as long to simulate; the three arms can run side by side, each
    with its own launcher (9 runs, 33 simulations at a time).
  - Every run is started with one linear-algebra thread (PROTOCOL.md section 9.6).
  - The arms in the MuJoCo engine (D, E1 to E3), memory: a run is started only while the system
    can still promise the memory its processes may ask for. A launcher that finds too little
    for all its runs at its start refuses and says so; one that waited for another arm
    (--after), and may have nobody at the machine, starts its runs one at a time as room
    appears. A run that an error stopped is continued like any other; the launcher's log says
    what stopped it.
  - A run that records no new generation for two hours of the launcher's running time has its
    processes ended and is continued from its checkpoint, like any run that ends unfinished.
    (A worker process that dies outright leaves its run waiting for a result that never comes.)

Files: results/<run>/ as written by run_tendon_evolution.py; the launcher's own log, its launch
records and each run's console output are in results/campaign/.
"""
import datetime
import glob
import hashlib
import json
import os
import platform
import re
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
    'A': {'tag': 'armA', 'generations': 1000, 'condition': 'noCost', 'seeds': '1-35', 'code': 'campaign-v2',
          'workers': 1, 'runner': ['--simulator', 'voxelyze2013', '--no-age-pareto', '--pop', '30']},
    'D': {'tag': 'armD', 'generations': 300, 'condition': 'noCost', 'seeds': '1-10', 'code': 'campaign-v4',
          'workers': 3, 'runner': ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30']},
    # Arm D with one setting undone each (PROTOCOL.md, section 9.8). An option given next to a
    # preset replaces the preset's value; engine_options() reads it back for the audit.
    'E1': {'tag': 'armE1', 'generations': 300, 'condition': 'noCost', 'seeds': '1-3', 'code': 'campaign-v4',
           'workers': 3, 'runner': ['--preset', 'cheney2013-floor', '--damping-global', '0.01',
                                    '--no-age-pareto', '--pop', '30']},
    # Arm E2 simulates five robots at a time where the others simulate three: with the volumetric
    # law the engine's time step is shorter, and a generation takes about twice as long. That is
    # machine time; the scores do not depend on it (seed 101 with five at a time repeats the run
    # with three, 60 of 60 scores: the trial of 27 November 2026).
    'E2': {'tag': 'armE2', 'generations': 300, 'condition': 'noCost', 'seeds': '1-3', 'code': 'campaign-v4',
           'workers': 5, 'runner': ['--preset', 'cheney2013-floor', '--amp', '0.2', '--poisson', 'on',
                                    '--no-age-pareto', '--pop', '30']},
    'E3': {'tag': 'armE3', 'generations': 300, 'condition': 'noCost', 'seeds': '1-3', 'code': 'campaign-v4',
           'workers': 3, 'runner': ['--preset', 'cheney2013', '--no-age-pareto', '--pop', '30']},
}
# The options of an arm's command that set the search and not the engine, with the number of
# values each takes. Every other option of the command is an engine option.
SEARCH_OPTIONS = {'--no-age-pareto': 0, '--pop': 1}
CODE_TAG = 'campaign-v2'            # the code arm A ran from; every arm names its own under 'code'
# Every code tag of the campaign that this project's search has run or will run from, oldest
# first. campaign-v3 adds the 2013 simulator's floor and start to the engine as options
# (PROTOCOL.md, section 9.5). campaign-v4, from which arms D and E run, states how much memory
# MuJoCo sets aside for a body and stops a run when an evaluation fails for a reason that is not
# the robot's, instead of scoring it 0 (section 9.6). Under the same settings every one of them
# computes the same scores.
ENGINE_TAGS = ('campaign-v2', 'campaign-v3', 'campaign-v4')
RUN_DEFINING = ['run_tendon_evolution.py', 'src']
MAX_ATTEMPTS = 6            # times one run is started or continued by one launcher
# One linear-algebra thread in every run the launcher starts, and in the processes a run starts
# (PROTOCOL.md, section 9.6). Left to themselves numpy and scipy each set memory aside for one
# thread per logical processor when they are loaded: 1.5 GB per process on this machine, none of
# it used. The scores do not depend on the number of threads. A run's manifest records what it
# was started with.
ONE_THREAD = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
# Memory, for the arms that run in the MuJoCo engine. A process of such a run, started with one
# thread and with MuJoCo's memory stated, asks the system for 0.12 GB with the largest champion
# of the campaign loaded and 0.09 GB with a full workspace of 1000 voxels
# (paper/diagnostics_2026-11-27). Ten runs with three evaluations at a time are 40 processes:
# about 4 GB asked for, and 12 GB wanted here before they are started.
GB_PER_PROCESS = 0.2        # allowed for each process of a run
KEEP_FREE_GB = 4.0          # left for everything else on the machine
STALL_SECONDS = 2 * 3600    # a run without a new generation for this long is ended and continued
SPAWN_APART_SECONDS = 60    # between the starts of two runs by a launcher that found too little memory at its start


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


def run_environment(base=None):
    """The environment the launcher gives each run: its own, with output that is written at once
    and one linear-algebra thread per process."""
    return dict(os.environ if base is None else base, PYTHONUNBUFFERED='1',
                PYTHONIOENCODING='utf-8:backslashreplace', **ONE_THREAD)


def in_the_2013_simulator(arm):
    """Does this arm's search score its robots in the original 2013 simulator (arm A)? The other
    arms score them in this project's MuJoCo engine, in processes of their own."""
    return 'voxelyze2013' in arm['runner']


def engine_options(arm):
    """What an arm's command says about the MuJoCo engine: (the preset, {option: the value given
    next to the preset}). The options are named as the search names them inside ('--damping-global'
    is 'damping_global') and the values are the words of the command. An option given next to a
    preset replaces the preset's value: the search's own rule. The options that set the search
    (SEARCH_OPTIONS) are left out. (None, {}) for an arm in the 2013 simulator, whose command
    says nothing about the engine."""
    if in_the_2013_simulator(arm):
        return None, {}
    words, preset, given, i = list(arm['runner']), None, {}, 0
    while i < len(words):
        word = words[i]
        if word in SEARCH_OPTIONS:
            i += 1 + SEARCH_OPTIONS[word]
        elif word.startswith('--') and i + 1 < len(words) and not words[i + 1].startswith('--'):
            if word == '--preset':
                preset = words[i + 1]
            else:
                given[word[2:].replace('-', '_')] = words[i + 1]
            i += 2
        else:
            raise ValueError(f'cannot read the engine options of the command {words}: {word}')
    if preset is None:
        raise ValueError(f'the command {words} names no preset')
    return preset, given


def free_commit_gb():
    """How much memory Windows can still promise to programs, in GB (None where it cannot be asked).
    When this runs out, any program on the machine can fail, also a campaign run."""
    if not sys.platform.startswith('win'):
        return None
    import ctypes

    class Status(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile', 'ullAvailPageFile',
                                                    'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual')]
    status = Status()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.ullAvailPageFile / 2 ** 30


def processes_of_a_run(workers):
    """A run is one process; with more than one evaluation at a time it has one more for each."""
    return 1 + (workers if workers > 1 else 0)


def room_for(runs, workers, free=None):
    """Can `runs` more runs be started with what the system can still promise? -> (yes or no, GB
    free, GB wanted). Yes where the system cannot be asked."""
    free = free_commit_gb() if free is None else free
    wanted = KEEP_FREE_GB + runs * processes_of_a_run(workers) * GB_PER_PROCESS
    return free is None or free >= wanted, free, wanted


def when_short_of_memory(waited_for):
    """What a launcher does when, at its start, the system cannot promise the memory for all its
    runs: 'refuse' or 'one at a time'. A launcher that a person started refuses and says how to
    make room: the person is there to do it. One that waited for another arm (--after) may begin
    at night with nobody at the machine, and giving up would leave the machine idle until someone
    looks: it starts each run when there is room for that run, one at a time."""
    return 'one at a time' if waited_for else 'refuse'


def may_start_a_run(one_at_a_time, seconds_since_the_last_start, apart=None):
    """One at a time: no run is started before the run started last has had time to take the
    memory it takes, so that the look at free memory before the next start sees it."""
    return not one_at_a_time or seconds_since_the_last_start >= (SPAWN_APART_SECONDS if apart is None else apart)


def stopped_by(last_lines):
    """What the end of a run's output says about why the run ended, in a few words; '' if nothing
    is recognised. A run stops itself when an evaluation ends in an error that is not the robot's
    own (PROTOCOL.md section 9.6); the last line of its output then names the error."""
    marker = 'EvaluationStopped: '
    at = last_lines.rfind(marker)
    if at < 0:
        return ''
    reason = last_lines[at + len(marker):].split(' / ')[0].strip()
    cut = reason.find('not scored: ')
    reason = reason[cut + len('not scored: '):] if cut >= 0 else reason
    return "an evaluation failed for a reason that is not the robot's and was not scored (" + reason[:200] + ')'


SCORE_IN_OUTPUT = re.compile(r'((?:best|mean|worst|fitness)[^0-9\n/]{0,12})[-+]?\d+\.\d+(?:[eE][-+]?\d+)?')


def without_scores(text):
    """Lines of a run's output with the scores taken out. The launcher's log says where the runs
    are and why one ended, never how well a run is doing: an arm's results are read only once the
    arm is complete (PROTOCOL.md, section 9.1, point 8)."""
    return SCORE_IN_OUTPUT.sub(r'\1(not shown)', text)


def without_progress(progress, generations_now, now, limit=None):
    """progress: {seed: [generations, time of the last new one]}, brought up to date here.
    -> {seed: seconds} for the runs that have recorded no new generation for longer than limit."""
    limit = STALL_SECONDS if limit is None else limit
    out = {}
    for seed, done in generations_now.items():
        last = progress.get(seed)
        if last is None or done != last[0]:
            progress[seed] = [done, now]
        elif now - last[1] > limit:
            out[seed] = now - last[1]
    for seed in [s for s in progress if s not in generations_now]:
        del progress[seed]
    return out


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


def campaign_tag_of_code(creationflags=0, root=None, tags=None):
    """The newest code tag of the campaign that the files which compute a run are, as they stand
    on disk, equal to; None if they are those of no such tag."""
    for tag in reversed(tags or ENGINE_TAGS):
        if code_differs_from_tag(creationflags, tag, root) is None:
            return tag
    return None


def wait_until_free(held, stop_requested, say, what, poll=5.0, remind=1800.0, sleep=time.sleep, clock=time.time):
    """Wait for as long as held() is true. Returns 'free', or 'stopped' if a stop was asked for
    meanwhile. Says every half hour that it is still waiting."""
    last = clock()
    while held():
        if stop_requested():
            return 'stopped'
        if clock() - last >= remind:
            say(f'(still waiting for {what})')
            last = clock()
        sleep(poll)
    return 'free'


def wait_for_other_arm(core, name, stop_requested, poll=5.0):
    """Wait until the re-run arm `name` (R or Rc) has ended, then say how it ended:
    'complete' (every seed finished with all its generations), 'incomplete', or 'stopped' if a
    stop of THIS launcher was asked for while it waited.

    That arm's runs are looked at only once its launcher has ended (two programs must not copy
    its results out at the same time). If its launcher is gone but runs of it are still alive,
    the wait goes on until they have ended.

    An arm that is itself run with this project's search (arm D, for which arms E1 to E3 may
    wait) is waited for by wait_for_search_arm."""
    if name in ARMS:
        return wait_for_search_arm(core, name, stop_requested, poll)
    say = core.say
    other = core.ARMS[name]
    stem = f"{other['tag']}_P{other['penalty']}"
    lock = os.path.join(core.RERUN_OUT, f'{stem}_host.lock')
    seeds = core.parse_seeds(core.PROTOCOL_SEEDS)
    with open(core.SETTINGS, encoding='utf-8', errors='replace') as f:
        generations = core.settings_generations(f.read())
    if core.lock_held(lock):
        say(f'Arm {name} is running. Waiting for it to finish; nothing is started before that.')
    while True:
        if wait_until_free(lambda: core.lock_held(lock), stop_requested, say, f'arm {name}', poll) == 'stopped':
            return 'stopped'
        st = core.read_status(stem + '_s', seeds)
        alive = core.running_seeds(st)
        if not alive:
            break
        say(f'Arm {name} has no launcher, but {len(alive)} of its runs are alive. Waiting for them to end.')
        waited = 0.0
        while waited < 600 and not core.lock_held(lock):
            if stop_requested():
                return 'stopped'
            time.sleep(poll)
            waited += poll
    done = core.complete_seeds(st, generations)
    if len(done) == len(seeds):
        say(f'Arm {name} is complete: {len(done)} of {len(seeds)} runs with {generations} generations.')
        return 'complete'
    say(f'Arm {name} has ended without being complete. ' + core.progress_line(st, generations))
    return 'incomplete'


def wait_for_search_arm(core, name, stop_requested, poll=5.0, out=None, results=None):
    """Wait until the launcher of the search arm `name` (arm D) has ended, then say how the arm
    ended: 'complete', 'incomplete', or 'stopped' if a stop of THIS launcher was asked for while
    it waited. The runs of such an arm belong to its launcher and end with it, so once the
    launcher is gone the run folders say all there is to say. If that arm has no launcher when
    the wait begins, the answer is given at once, from the run folders as they are.

    Only the other arm's lock and the names of its files are looked at: how many generations each
    run has on record, never a score."""
    say = core.say
    other = ARMS[name]
    stem, generations = other['tag'], other['generations']
    seeds = core.parse_seeds(other['seeds'])
    lock = os.path.join(out or OUT, f'{stem}_host.lock')
    if core.lock_held(lock):
        say(f'Arm {name} is running. Waiting for it to finish; nothing is started before that.')
    if wait_until_free(lambda: core.lock_held(lock), stop_requested, say, f'arm {name}', poll) == 'stopped':
        return 'stopped'
    st = statuses(stem, seeds, generations, results=results)
    done = core.complete_seeds(st, generations)
    if len(done) == len(seeds):
        say(f'Arm {name} is complete: {len(done)} of {len(seeds)} runs with {generations} generations.')
        return 'complete'
    say(f'Arm {name} has ended without being complete. ' + core.progress_line(st, generations))
    return 'incomplete'


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
    waiting_for = read_state_file(stem).get('waiting_for') if alive else None
    print(f"  launcher: {'running' if alive else 'not running'}"
          + (f', waiting for arm {waiting_for} to finish before it starts anything' if waiting_for else ''))
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
        workers = a.workers or arm.get('workers', 1)
        with_2013 = in_the_2013_simulator(arm)
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
            problem = code_differs_from_tag(core.HIDDEN, arm['code'])
            if problem:
                say(f'{problem} An arm of the campaign runs from that code; nothing started.')
                return 2

        os.environ.update(ONE_THREAD)                # for this process too: keep_awake loads numpy with the runner
        stop_awake, awake = core.keep_awake()
        say(awake)
        record = {
            'time': datetime.datetime.now().isoformat(timespec='seconds'),
            'arm': a.arm, 'stem': stem, 'seeds': seeds, 'generations': generations, 'jobs': jobs,
            'workers': workers, 'after': a.after, 'runner_arguments': arm['runner'], 'command': sys.argv,
            'launcher_pid': os.getpid(), 'git': git, 'code_tag': arm['code'],
            'python': platform.python_version(), 'windows': platform.platform(), 'keep_awake': awake,
            'threads': ONE_THREAD,
        }
        if with_2013:                                # the 2013 simulator and its settings
            record.update(simulator_sha256=core.programs()['sha256']['voxelize'], template_sha256=sha256(TEMPLATE))
        launches = os.path.join(OUT, f'{stem}_launches.json')
        earlier = []
        if os.path.exists(launches):
            with open(launches, encoding='utf-8') as f:
                earlier = json.load(f)
        for key in ('simulator_sha256', 'template_sha256'):
            if with_2013 and earlier and earlier[0][key] != record[key]:
                say('The 2013 simulator or its settings template has changed since this arm was first launched. '
                    'All runs of an arm must come from one build; nothing started.')
                return 2
        with open(launches, 'w', encoding='utf-8') as f:
            json.dump(earlier + [record], f, indent=1)
        say(f"code {git.get('describe', '?')}"
            + (f", modified tracked files: {git['modified']}" if git.get('modified') else '')
            + (f"; simulator {record['simulator_sha256'][:12]}, settings template {record['template_sha256'][:12]}"
               if with_2013 else "; the MuJoCo engine, one linear-algebra thread in every process"))

        stop_request = os.path.join(OUT, f'{stem}_stop.request')
        if os.path.exists(stop_request):
            os.remove(stop_request)
        here = f'python paper\\reference_2013\\start_arm.py --arm {a.arm}{core.trial_args(a)}'
        if a.after:
            with open(os.path.join(OUT, f'{stem}_state.json'), 'w', encoding='utf-8') as f:
                json.dump({'time': time.time(), 'running': [], 'waiting': [], 'failed': {}, 'waiting_for': a.after}, f)
            outcome = wait_for_other_arm(core, a.after, lambda: os.path.exists(stop_request))
            if outcome == 'stopped':
                os.remove(stop_request)
                say(f'Stop requested while waiting. Nothing of arm {a.arm} was started.')
                return 130
            if outcome == 'incomplete':
                say(f'Arm {a.arm} is therefore not started. When you want it started:  {here}')
                return 3
            problem = None if a.tag else code_differs_from_tag(core.HIDDEN, arm['code'])     # hours may have passed
            if problem:
                say(f'{problem} An arm of the campaign runs from that code; nothing started.')
                return 2
            say(f'Starting arm {a.arm} now.')

        own_children()          # from here on, whatever this launcher starts ends with it
        logs = os.path.join(OUT, f'{stem}_logs')
        os.makedirs(logs, exist_ok=True)
        python = os.path.join(os.path.dirname(sys.executable), 'python.exe')
        python = python if os.path.exists(python) else sys.executable
        environment = run_environment()

        st = statuses(stem, seeds, generations)
        pending = [s for s in seeds if st[s][1] != 'finished']
        say(f"{len(seeds) - len(pending)} runs are complete already, "
            f"{sum(1 for s in pending if st[s][1] == 'interrupted')} are continued from their checkpoints, "
            f"{sum(1 for s in pending if st[s][1] == 'not started')} start from the beginning.")
        attempts = {s: 0 for s in seeds}
        failed = {}
        one_at_a_time = False                        # short of memory at the start, with nobody to tell (see below)
        last_start = [0.0]                           # when this launcher last started a run
        if not with_2013:
            fits, free, wanted = room_for(min(jobs, len(pending)), workers)
            if not fits:
                short = (f'The system can still promise {free:.1f} GB of memory to programs; {wanted:.1f} GB are wanted '
                         f'before {min(jobs, len(pending))} runs with {workers} simulation(s) at a time are started '
                         f'({GB_PER_PROCESS:g} GB for each process, {KEEP_FREE_GB:g} GB left free).')
                if when_short_of_memory(a.after) == 'refuse':
                    say(short + ' Nothing started. Close other programs, or start fewer runs side by side with --jobs.')
                    return 2
                one_at_a_time = True
                say(short + f' This launcher waited for arm {a.after} and may have nobody at the machine, so it does '
                            f'not give up: each run is started when there is room for it, one at a time.')
        progress = {}                                # {seed: [generations, when the last one came]}
        awake = [0.0, time.time()]                   # seconds this launcher has been running, and when last counted:
        #                                              time the machine slept through is no time a run stood still
        waiting_for_memory = [0.0]                   # when that was last said

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

        def last_lines(seed, n=3, width=160):
            try:
                with open(os.path.join(logs, run_name(stem, seed) + '.log'), 'rb') as f:
                    f.seek(max(0, os.path.getsize(f.name) - 6000))
                    lines = [l for l in f.read().decode('utf-8', errors='replace').splitlines() if l.strip()]
                return ' / '.join(l.strip()[:width] for l in lines[-n:])
            except OSError:
                return ''

        stopped = False
        next_report = time.time() + 90
        while pending or active:
            try:
                awake[0] += min(time.time() - awake[1], 30.0)
                awake[1] = time.time()
                while pending and len(active) < jobs:
                    if not may_start_a_run(one_at_a_time, time.time() - last_start[0]):
                        break                        # the run started last has not yet taken its memory
                    # a run continued while others are going: only if the system has the memory for it
                    if not with_2013 and not room_for(1, workers)[0]:
                        if time.time() - waiting_for_memory[0] > 600:
                            waiting_for_memory[0] = time.time()
                            say(f'{len(pending)} run(s) wait to be started: the system can promise too little memory '
                                f'just now ({free_commit_gb():.1f} GB). Looking again every few seconds.')
                        break
                    seed = pending.pop(0)
                    active[seed] = spawn(seed)
                    last_start[0] = time.time()
                for seed, process in list(active.items()):
                    code = process.poll()
                    if code is None:
                        continue
                    del active[seed]
                    done, state = run_state(os.path.join(RESULTS, run_name(stem, seed)), generations)
                    if state == 'finished':
                        say(f'{run_name(stem, seed)}: complete')
                    elif attempts[seed] < MAX_ATTEMPTS:
                        why = stopped_by(last_lines(seed, 30, 600))
                        say(f'{run_name(stem, seed)}: ended with code {code} at generation {done}'
                            + (f': {why}' if why else '') + f'; continuing it from '
                            f'its checkpoint (start {attempts[seed] + 1} of {MAX_ATTEMPTS}). Its last lines: '
                            f'{without_scores(last_lines(seed))}')
                        pending.append(seed)
                    else:
                        failed[str(seed)] = f'ended {attempts[seed]} times, last with code {code}'
                        say(f'{run_name(stem, seed)}: ended {attempts[seed]} times without finishing; left as it is. '
                            f'Its last lines: {without_scores(last_lines(seed))}')
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
                    st = statuses(stem, seeds, generations, set(active), failed)
                    say(core.progress_line(st, generations))
                    for seed, seconds in without_progress(progress, {s: st[s][0] for s in active}, awake[0]).items():
                        say(f'{run_name(stem, seed)} has recorded no new generation for {seconds / 3600:.1f} h: its '
                            f'processes are ended, and the run is then continued from its checkpoint.')
                        subprocess.run(['taskkill', '/PID', str(active[seed].pid), '/T', '/F'], stdin=subprocess.DEVNULL,
                                       capture_output=True, creationflags=core.HIDDEN)
                        progress.pop(seed, None)
                time.sleep(2)
            except KeyboardInterrupt:                        # only with --here
                say('Ctrl+C: ending the runs. They keep their checkpoints.')
                stopped = True
                break

        st = statuses(stem, seeds, generations, (), failed)
        done = core.complete_seeds(st, generations)
        say(core.progress_line(st, generations))
        say(f'{len(done)} of {len(seeds)} runs are complete with {generations} generations.')
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
