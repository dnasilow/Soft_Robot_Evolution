"""Trial of a launcher that finds too little memory when it starts its runs.

At its start a launcher looks whether all its runs fit into the memory the system can still
promise to programs. What it does when they do not depends on who is there:
    refuse          a launcher started by a person refuses and says how to make room
    one at a time   a launcher that waited for another arm (--after) may begin at night with
                    nobody at the machine; it does not give up, and starts each run when there
                    is room for that run, one at a time
(search_arm.when_short_of_memory; added on 28 November 2026, before the launchers of arms E1 to
E3 were started waiting for arm D.)

Too little memory is made up here: in this process only, the launcher is told to keep 1000 GB
free, which no machine has. In the log of the trial "1000 GB left free" is that made-up figure.

usage, from the project folder:
    python paper/diagnostics_2026-11-27/arms_E/trial_short_of_memory.py refuse
        a launcher started by hand (no --after): it must say "Nothing started" and end with code 2
    python paper/diagnostics_2026-11-27/arms_E/trial_short_of_memory.py wait
        a launcher started with --after. The arm it waits for is pointed at the trial of arm E3
        of 27 November, which is complete, so the wait ends at once. It must say that it does not
        give up, start nothing while memory is short, and start its two runs (trialM_s101 and
        trialM_s102, arm E1's command, one generation, seeds of no arm) some seconds apart once
        the made-up shortage ends, 90 seconds in.
"""
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCHER = os.path.abspath(os.path.join(HERE, '..', '..', 'reference_2013'))
sys.path.insert(0, LAUNCHER)
import search_arm                     # noqa: E402
import start_arm                      # noqa: E402

if len(sys.argv) != 2 or sys.argv[1] not in ('refuse', 'wait'):
    raise SystemExit(__doc__)
sys.modules['start_arm'] = start_arm
enough = search_arm.KEEP_FREE_GB
search_arm.KEEP_FREE_GB = 1000.0                                  # nothing fits
if sys.argv[1] == 'refuse':
    sys.argv = ['start_arm.py', '--arm', 'E1', '--tag', 'trialN', '--seeds', '101', '--gens', '1', '--here']
else:
    search_arm.ARMS['D'] = dict(search_arm.ARMS['D'], tag='trialE3', seeds='101-103', generations=2)
    search_arm.SPAWN_APART_SECONDS = 20
    timer = threading.Timer(90.0, lambda: setattr(search_arm, 'KEEP_FREE_GB', enough))    # the shortage ends
    timer.daemon = True
    timer.start()
    sys.argv = ['start_arm.py', '--arm', 'E1', '--tag', 'trialM', '--seeds', '101-102', '--gens', '1', '--after', 'D',
                '--interval', '1', '--here']
sys.exit(start_arm.main())
