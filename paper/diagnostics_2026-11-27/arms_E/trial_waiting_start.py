"""Trial of the waiting start for an arm that waits for arm D (start_arm.py --arm E1 --after D).

The real thing waits for the real arm D, which runs for days. For the trial the name of arm D
is pointed, in this process only, at the TRIAL of arm E3 (trialE3_s101 to trialE3_s103, two
generations), which must be running when this is started. Everything else is the launcher as it
is: it takes the trial's own lock, waits for the lock of the arm it waits for, reads that arm's
run folders once the lock is free, and starts the trial of arm E1 (trialE1_s101 to trialE1_s103,
two generations) only if every one of those runs is complete.

In the trial's log (rehearsal/trialE1_launcher_log.txt) "Arm D" therefore means the trial of arm E3.

usage, from the project folder, while the trial of arm E3 is running:
    python paper/reference_2013/start_arm.py --arm E3 --tag trialE3 --seeds 101-103 --gens 2 --here      (in another console)
    python paper/diagnostics_2026-11-27/arms_E/trial_waiting_start.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCHER = os.path.abspath(os.path.join(HERE, '..', '..', 'reference_2013'))
sys.path.insert(0, LAUNCHER)
import search_arm                     # noqa: E402
import start_arm                      # noqa: E402

sys.modules['start_arm'] = start_arm
search_arm.ARMS['D'] = dict(search_arm.ARMS['D'], tag='trialE3', seeds='101-103', generations=2)
sys.argv = ['start_arm.py', '--arm', 'E1', '--tag', 'trialE1', '--seeds', '101-103', '--gens', '2', '--after', 'D',
            '--interval', '3', '--here']
sys.exit(start_arm.main())
