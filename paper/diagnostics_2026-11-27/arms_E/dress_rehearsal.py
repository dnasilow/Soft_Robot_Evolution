"""Dress rehearsal of everything that follows an E arm, on runs that belong to no arm.

The tools of an E arm's analysis are tried in rehearsal mode on trial runs (the folder
rehearsal/). Their ARM mode, the one that will be used on the arms, needs an analysed arm D next
to an analysed E arm: the report with the comparison against arm D, the checks of that
comparison from the raw files of both arms, and the video that shows the arm below arm D. This
script tries that mode too, without an arm. In this process only, the trial runs of 27 November
2026 stand in for the arms:

    "arm D"   trialD_s101 .. trialD_s110   (arm D's command, 3 generations, seeds 101 to 110)
    "arm E"   trial<E>_s101 .. s103        (the E arm's command, 2 generations, seeds 101 to 103)

and the tools are run as they will be run on the arms:

    analyse_arm.py --arm D, then --arm <E>      (the E report needs the D report)
    check_arm_D.py --arm <E>                    (checks, the comparison with "arm D" by hand, audit)
    render_champions.py --arm <E>               (six robots: the 2013 originals, "arm D", "arm E")

Everything is written to results/diagnostics_2026-11-27/arms_E/dress_<E>/, which is kept out of
git: the files there carry the names of arms and are made of trial runs, so they must not be
mistaken for results. Nothing goes to paper/outcomes, and no file of the real arm D is opened:
only its name is borrowed.

usage, from the project folder (the trial runs must be in results/):
    python paper/diagnostics_2026-11-27/arms_E/dress_rehearsal.py E1 [--video]
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

if len(sys.argv) < 2 or sys.argv[1] not in ('E1', 'E2', 'E3'):
    raise SystemExit(__doc__)
arm = sys.argv[1]
video = '--video' in sys.argv
OUT = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'arms_E', 'dress_' + arm)
os.makedirs(OUT, exist_ok=True)

import check_arm_D as cd              # noqa: E402  (sets one thread before numpy is loaded)
import analyse_arm as aa              # noqa: E402
import render_champions as rc         # noqa: E402
import search_arm                     # noqa: E402

assert aa is cd.ts.aa and aa is rc.aa
# the stand-ins, in this process only
aa.ARMS['D'] = dict(aa.ARMS['D'], prefix='trialD_s', seeds=list(range(101, 111)), generations=3, score_generations=(3, 2))
aa.ARMS[arm] = dict(aa.ARMS[arm], prefix=f'trial{arm}_s', seeds=[101, 102, 103], generations=2, score_generations=(2,))
search_arm.ARMS['D'] = dict(search_arm.ARMS['D'], tag='trialD', seeds='101-110', generations=3)
search_arm.ARMS[arm] = dict(search_arm.ARMS[arm], tag=f'trial{arm}', seeds='101-103', generations=2)
cd.OUTCOMES = OUT
real_finished_arm = aa.finished_arm
aa.finished_arm = lambda name, outcomes=OUT: real_finished_arm(name, OUT)
rc.OUT = OUT

print('=' * 30, 'analysis of the stand-in for arm D')
code = aa.main(['--arm', 'D', '--out-dir', OUT, '--outcomes-dir', OUT])
assert code == 0, code
print()
print('=' * 30, f'analysis of the stand-in for arm {arm}')
code = aa.main(['--arm', arm, '--out-dir', OUT, '--outcomes-dir', OUT])
assert code == 0, code

# the audit's evaluations of these champions were made in the rehearsal before this one: keep them
earlier = os.path.join(ROOT, 'results', 'analysis', f'rehearsal_trial{arm}_s_audit_evaluations.json')
if os.path.isfile(earlier) and not os.path.isfile(os.path.join(OUT, f'arm_{arm}_audit_evaluations.json')):
    shutil.copy(earlier, os.path.join(OUT, f'arm_{arm}_audit_evaluations.json'))
print()
print('=' * 30, f'checks and audit of the stand-in for arm {arm}')
checks = cd.main(['--arm', arm, '--out-dir', OUT, '--workers', '3'])
print('exit code of the checks:', checks)

shown = 0
if video:
    print()
    print('=' * 30, f'video of the stand-in for arm {arm}')
    shown = rc.main(['--arm', arm])
    print('exit code of the video:', shown)
sys.exit(1 if checks or shown else 0)
