# Memory for arms D and E: three changes, and the checks that they change no score

27 November 2026. Decision 14 of the plan, taken that day ("Yes, make them"), before any run of arms D or E had started and with no arm running. The protocol records it in section 9.6. The code that computes a run changed, so it has a new tag, `campaign-v4`.

## What was wrong

Found on 25 November ([diagnostics_2026-11-25](../diagnostics_2026-11-25/README.md), "A lesson about memory"; `check_memory.py`):

1. **A process asked the system for up to 3.2 GB and used almost none of it.** 1.5 GB went to numpy and scipy, whose linear-algebra libraries each set memory aside for one thread per logical processor (32 here) when they are loaded. Up to 1.7 GB more went to MuJoCo, which reserves working memory for a body in proportion to the square of its size and uses about a thousandth of it. Windows counts memory a program has asked for against what it can promise to all programs, whether the program touches it or not. So 7 to 9 processes fitted on a machine with 32 logical processors, and on 25 November fourteen were too many: 86 evaluations of the scoring script failed.
2. **A failed evaluation became a score of 0.** The search's evaluation in the MuJoCo engine turned any error into a score of 0 and went on. That is right for a body the engine cannot build. It is wrong for a body that could not be evaluated because the machine was short of memory: the run goes on with a false score, is no longer the run its seed defines, and nothing shows it afterwards. No arm had run a search in the MuJoCo engine, so no result was touched. Arm D would have been the first.

## What was changed

| | Change | Where |
|---|---|---|
| (a) | **One linear-algebra thread per process.** The launcher starts every run with `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and a run's worker processes inherit them. The scoring script sets the same for itself and its workers. A run's manifest now records what it was started with | `reference_2013/search_arm.py`, `analysis/transfer_scores.py`; the manifest line in `run_tendon_evolution.py` |
| (b) | **An evaluation that fails is not scored.** A body is given 0 after an error only if the error is the body's own: Python's `ValueError` (the engine refuses the body; an empty grid is the known case) or `ArithmeticError`, and only if its message does not speak of memory. The run's output says so each time. Every other error stops the run: nothing of the unfinished generation is recorded, and the same command continues the run from its last recorded generation. A simulation that blows up is not an error and scores 0 as before | `src/evolution/mujoco_tendon_evaluator.py` |
| (c) | **MuJoCo's working memory is stated**: 8 MB plus 16 kB per voxel, in place of MuJoCo's own estimate. If the stated memory ever ran out, MuJoCo would drop floor contacts and go on with a warning; the engine now checks for that in every step and raises an error, which by (b) stops the run | `src/physics/mujoco_beam_physics.py` |

None of the three is meant to change a number that an evaluation computes. The rest of this page is the evidence for that.

Every check below was made on the code as it then stood in the campaign's folder, after the last change to it (03:52) and before it was committed. The three files that changed are the ones the tag `campaign-v4` holds: `run_tendon_evolution.py` (git blob `451b23ee`), `src/evolution/mujoco_tendon_evaluator.py` (`a456c04d`) and `src/physics/mujoco_beam_physics.py` (`96099b1a`).

## Why 8 MB plus 16 kB per voxel is enough

A beam body's only MuJoCo constraints are its floor pairs: one sphere per voxel against the floor, so at most one contact per voxel, with four constraint rows each. Voxels collide with each other through the engine's own forces, not through MuJoCo. The worst case is therefore every voxel in contact with the floor at once, and it can be built (`measure_memory.py`, part 1; `tests/test_memory.py`):

| Voxels in the body | Floor | Contacts at once | MuJoCo's own estimate | Used at most | Stated | Stated over used |
|---|---|---|---|---|---|---|
| 1 | hard | 1 | 13 MB | 0.03 MB | 8.0 MB | 292 |
| 10 | hard | 10 | 16 MB | 0.03 MB | 8.2 MB | 250 |
| 100 | hard | 100 | 57 MB | 0.28 MB | 9.6 MB | 34 |
| 125 | hard | 125 | 72 MB | 0.35 MB | 10.0 MB | 29 |
| 500 | hard | 500 | 506 MB | 1.39 MB | 15.8 MB | 11 |
| 1000, the full workspace | hard | 1000 | 1687 MB | 2.77 MB | 23.6 MB | 8.5 |
| 1000, the full workspace | the 2013 rule | none (the rule is the engine's own) | 1687 MB | 0.34 MB | 23.6 MB | 69 |

- **2.9 kB per voxel is the most a body can use** (2909 to 2920 bytes from 100 voxels up), with every voxel pressed into the hard floor and moving, so that friction is at work in every contact. Under the 2013 floor rule, which has no MuJoCo contact, it is 0.36 kB per voxel.
- **The statement is at least 8.5 times that**, for a body that fills the workspace. The per-voxel part alone is 5.5 times it, so the margin does not shrink below that for any size.
- **A real evaluation is far from the worst case.** A champion stands on a few dozen voxels, not on all of them; what the champions used is in the table of the checks below.

What MuJoCo does when the stated memory is too small was tried, not assumed (`measure_memory.py`, part 2):

| Stated | Body | What MuJoCo does | What the engine does | What the search does |
|---|---|---|---|---|
| 1 kB | 1 voxel | Drops the floor contact, counts a warning and goes on: the voxel sinks through the floor | Raises an error in the step in which the warning is counted | Stops the run |
| 1 kB | 200 voxels | Fails while it builds the model, with an error that Python sees as a `ValueError` whose message speaks of memory | Passes the error on | Stops the run |
| 300 kB | 200 voxels | Fails in the first step with its own fatal error | Passes the error on | Stops the run |

The first row is why the engine has its own check: left alone, that simulation would have gone on and been scored. The second is why the rule in (b) reads the message of a `ValueError` and does not trust its kind alone.

## The checks

Two kinds of evidence: single evaluations that are on record, and whole runs of the search.

### Every evaluation on record, computed again

`check_same_scores.py`. Every evaluation behind the two transfer reports in [`../outcomes/`](../outcomes/README.md) was computed again from nothing, with the new code, one thread and the stated memory, and compared with the committed report. Those reports were computed on 24 to 26 November with the code tagged `campaign-v2` and `campaign-v3`, with the libraries' default threads and the memory MuJoCo sets aside by itself.

| Preset | Evaluations | The recorded score, to the last digit | Memory stated | Used at most | Most contacts at once |
|---|---|---|---|---|---|
| `cheney2013` (hard floor, arm E3) | 231: 175 champions, 31 of them once more from their height, 25 at a quarter of the time step | **231 of 231** | 9.2 to 20.8 MB | 1.33 MB, 6.4% of what was stated for that body | 81 |
| `cheney2013-floor` (2013 floor, arm D) | 200: 175 champions, 25 at a quarter of the time step | **200 of 200** | 9.2 to 20.8 MB | 0.28 MB, 1.4% | none: the rule has no MuJoCo contact |

- **431 of 431.** No evaluation ended in an error and none blew up, as in the reports.
- **The champions are arms R, Rc and A and the deposit of both conditions**: 175 bodies of 76 to 819 voxels.
- **The largest share of the stated memory** was used by the largest body, arm A's champion of seed 16 (819 voxels, 42 contacts at once): 1.7 kB per voxel, against the 2.9 kB of the worst case and the 16 kB stated.

### Runs of the search, old code against new

`check_same_search.py`. The search's own command line with population 30 and tournament selection, as in arms D and E, run twice: with the code tagged `campaign-v3` as that code would have run it (a checkout of its own, default threads), and with the new code as the launcher starts a run (one thread). Compared score for score in every generation, and body for body in the final population.

The seed is 101, which is the seed of no arm. *A first attempt used seed 1. It was stopped and its files were removed unread once it was noticed that seed 1 is a seed of arms D and E3: no run of an arm's seed is made before the arm is started.*

| Run | Compared with | Result |
|---|---|---|
| `--preset cheney2013-floor`, 5 generations, 3 evaluations at a time, new code | The same with `campaign-v3` | **150 of 150 scores identical, 30 of 30 final bodies identical** |
| `--preset cheney2013` (hard floor), 3 generations, 3 at a time, new code | The same with `campaign-v3` | **90 of 90 scores identical, 30 of 30 final bodies identical** |
| `--preset cheney2013-floor`, 2 generations, one evaluation at a time (the search simulates in its own process, without worker processes), new code | The first 2 generations of the first run, new code | **60 of 60 scores identical** |
| The first run once more, **stopped twice while it ran** (its processes ended from outside while it evaluated generations 3 and 4) and started again each time, new code | The first run, new code | **150 of 150 scores identical, 30 of 30 final bodies identical**; started 3 times, continued from generations 2 and 3 |

- **In no run was a body refused, and no run stopped itself**: the new code's runs printed no "failed and scores 0" and raised no error.
- **Scores of exactly 0 are in these runs** (2, 1 and 1 in the first three generations of the first run, 2 in the first generation of the second): bodies that blow up or have no muscle. They are the same bodies with the same score under both codes.
- **The bodies are of the size the arms will have**: the final populations hold bodies of 336 to 890 voxels.
- **The run stopped from outside** is the case the change relies on: a run that an error stops is continued by the same command and then computes what the uninterrupted run computed. `tests/test_memory.py` holds the same for a run that stops itself because the engine fails, in the second generation and in the very first population.

### Tests

`tests/test_memory.py`, 15 tests: the stated memory is what the engine says it is; a body cannot use a fifth of it with every voxel on the floor (100, 500 and 1000 voxels on the hard floor, 1000 on each of the other two); the score of a small body is the same to the last digit with MuJoCo's own estimate in place of the statement; too little memory is never scored, whichever way MuJoCo reports it; which errors are a body's own; a failure reaches the run from a real worker process; a run of the search's command line that the engine fails in is stopped, records nothing of the unfinished generation, and continued gives the uninterrupted run; the launcher's environment; what a process asks the system for.

**The project's 318 tests pass on the new code**: none failed and none was skipped (`results/analysis/campaign_v4_tests.log` on this machine; 284 passed for `campaign-v3`). The simulator's warnings in that run are those of the run for `campaign-v3`: the same two test bodies blow up at the same instant. The only new ones are the two warnings that the tests of too little memory ask for.

## What a process asks the system for now

The measurement of 25 November, repeated with the new code (`measure_memory.py`, part 3): a process loads the libraries and the engine, then scores a champion; what it has asked the system for by then is read from Windows.

| Champion | Voxels | Preset | 25 November | New code, default threads | New code, one thread | MuJoCo's memory: stated | used |
|---|---|---|---|---|---|---|---|
| Arm R, seed 33 (the largest body) | 764 | `cheney2013` | 2.57 GB | 1.56 GB | 0.12 GB | 19.9 MB | 1.17 MB |
| Arm R, seed 30 (the median body) | 675 | `cheney2013` | 2.37 GB | 1.56 GB | 0.12 GB | 18.5 MB | 0.94 MB |
| Arm Rc, seed 15 (the median body) | 363 | `cheney2013` | 1.84 GB | 1.56 GB | 0.10 GB | 13.7 MB | 0.43 MB |
| Arm R, seed 33 | 764 | `cheney2013-floor` | 2.57 GB | 1.57 GB | 0.12 GB | 19.9 MB | 0.26 MB |
| Arm R, seed 30 | 675 | `cheney2013-floor` | 2.37 GB | 1.57 GB | 0.12 GB | 18.5 MB | 0.23 MB |
| Arm Rc, seed 15 | 363 | `cheney2013-floor` | 1.84 GB | 1.56 GB | 0.11 GB | 13.7 MB | 0.12 MB |

- **A process of a run now asks for 0.12 GB with the largest champion, against 2.57 GB**: about a twentieth. The stated memory takes away the part that grew with the body (1.0 GB for this one); the single thread takes away the 1.5 GB that was there before any body was loaded.
- **All six get the score of 25 November to the last digit**, with either number of threads, and each used exactly as much of MuJoCo's memory as it did then.
- **With a full workspace of 1000 voxels loaded** a process asks for 0.09 GB (`tests/test_memory.py` holds it below 0.25).
- **Seen on running searches**, while the checks above were being made: the worker processes of the new code held 0.07 to 0.12 GB each and the process of a run 0.04 GB; those of `campaign-v3` held 1.5 to 1.95 GB each and 0.76 GB.
- **What this means for arm D.** Ten runs with three evaluations at a time are 40 processes. Together they ask for about 4 GB. As the code stood, the 30 evaluating processes alone would have asked for 80 to 95 GB with champion-sized bodies, more than this machine can promise. A larger Windows page file, step (d) of the decision, is not needed.

## Known and left alone

- **A worker process that dies outright** (not an error raised in it: the process gone) leaves its run waiting for a result that never comes. The run does not go on with a false score, but it does not go on at all. This is handled outside the code that computes a run: the launcher ends a run that has recorded no generation for two hours of its own running time and continues it from its checkpoint.
- **The rule in (b) goes by the kind of error.** A fault in the code or in the settings that raises a `ValueError` or an `ArithmeticError` is not told apart from a body's own error: the body scores 0, as it did before. What is new is the line in the run's output, so that such bodies can be counted afterwards.
- **A start that fails in its very first evaluation**, the check a run makes before its first population, is not in the run's manifest, which is written after that check. It is in the launcher's log and in the run's output.
- **The other body types** (`--body springs`, `--flex`) get change (b) and not (c): their models are built elsewhere and no arm uses them.
- **A body the engine refuses still scores 0**, as it did. What is new is that the run's output says so.

## A second read of the change

Before the tag was set, the change to the three files that compute a run was read once more by a separate AI agent that was given the diff and the requirement, and not the reasoning above. It found no defect in what an evaluation computes: with its own runs it got the same state of a body after 400 steps from the old and the new engine, byte for byte, and confirmed that a model has no constraint other than the floor pairs. Four of its points were taken up before the checks on this page were made: the memory check now reads MuJoCo's counters afresh each time instead of keeping a view of them; its error message says that the engine's statement, not the machine, is what ran out; and two descriptions in the code that claimed more than the rule does were corrected (the rule cannot tell a fault in the code from a body's own error if both raise the same kind of error). Its other two points are the first and the third item of the list above.

## Later the same day: the tools for arm D's champions, rehearsed

Arm D was started at 15:03. While it ran, the audit and the transfer of its champions were fixed in the protocol (section 9.7) and built (`../analysis/check_arm_D.py`, `../analysis/transfer_to_2013.py`; described in [`../analysis/README.md`](../analysis/README.md)). They were tried on the ten trial runs of the launcher, `trialD_s101` to `trialD_s110`: seeds that belong to no arm, three generations each. What the rehearsal wrote is kept in `rehearsal_arm_D_tools/`: the pilot report of the trial runs, the checks with the audit, the transfer, and five moments of the video that `../analysis/render_champions.py` makes of such runs, with its record of what was checked. Nothing in that folder is a result of an arm.

## In the evening: arms E1 to E3 prepared

Arm D was still running, and nothing of it was read. The three sensitivity arms were fixed in the protocol (section 9.8) and then put into the launcher, the analysis, the audit and the video tool; none of them was started. What is kept in `arms_E/` is the record of how that was checked. Every run here has seed 101, 102 or 103: seeds of no arm.

**The settings** (`check_settings.py`, `settings.json`). Small runs of the search's own command line with the engine options of arm D and of each of the three arms, as the launcher has them. Each arm's run recorded settings that differ from arm D's in its one setting and in no other:

| Arm | Options next to the search's | What its run recorded differently from arm D's |
|---|---|---|
| E1 | `--preset cheney2013-floor --damping-global 0.01` | global damping 0.01 in place of 0.001 |
| E2 | `--preset cheney2013-floor --amp 0.2 --poisson on` | amplitude 0.2 in place of 0.14; volumetric law on in place of off |
| E3 | `--preset cheney2013` | the preset; floor `voxelyze` in place of `rule2013`; start `floor` in place of `workspace` |

**The first population** (`check_first_population.py`, `first_population.json`). Seeds 1 to 3 are seeds of arm D and of each E arm. Runs of one generation under the options of all four arms begin with the same bodies in the same order and share no score. So a run of an E arm begins with the robots of arm D's run of that seed, and the two differ by what the changed setting does from the first evaluation on.

**The launcher's trial.** Three runs with each arm's command, two generations each, next to arm D's ten runs; logs in `arms_E/rehearsal/`.

| Tried | Result |
|---|---|
| E2 and E3 started together, each by its own launcher | All six ended; each run's record shows its arm's command and settings |
| E1 started waiting (`trial_waiting_start.py`: in that process the name of arm D was pointed at the trial of arm E3, because the real arm D runs for days; in its log "Arm D" is that trial) | It waited 26 minutes and started nothing; when the trial it waited for had ended with its three runs complete, it started its own three within the minute |
| `trialE3_s102` ended from outside during its second generation | The launcher continued it from its checkpoint; its log shows no score |
| Seed 101 with arm E2's command and five robots at a time, against the trial run with three (`check_five_at_a_time.py`, `five_at_a_time.json`) | The same run: 60 of 60 scores, all 30 bodies of the final population |
| 28 November: too little memory at a launcher's start, made up by telling it to keep 1000 GB free (`trial_short_of_memory.py`) | Started by hand it refuses, as before. Started with `--after` it does not give up: it started nothing for the 90 seconds the shortage lasted, then its two runs one after the other, and both ended |

The volumetric law shortens the engine's time step by a factor of 1.57 for every body: a body of muscle only has 3.5e-5 s under the other settings and 2.2e-5 s under arm E2's, and the three trial champions of arm E2's settings have 1.0e-5 s where the others have 1.6e-5 s or 3.5e-5 s. A generation of arm E2's command took about twice as long. That is why arm E2's runs simulate five robots at a time.

**The tools rehearsed** on those nine trial runs (`arms_E/rehearsal/`): their pilot reports, the checks with the audit, and five moments of the video of each trial.

| Trial | Champions that get their recorded score when evaluated again with the arm's own settings | Change of the score at a quarter of the time step | How deep the lowest voxel stood in the floor (median) |
|---|---|---|---|
| E1 settings | 3 of 3, to the last digit | 0.3% to 0.4% | 0.55 of a voxel |
| E2 settings | 3 of 3, to the last digit | 0.6% to 10.9% | 1.09 voxels |
| E3 settings (hard floor) | 3 of 3, to the last digit | 0.6% to 1.6% | 0.14 of a voxel |

These are robots of a second generation. The table shows that the audit measures what it should under each arm's settings; it says nothing about the arms.

**The arm mode, with stand-ins** (`dress_rehearsal.py`). The tools of an E arm's analysis need an analysed arm D next to an analysed E arm: the report with the comparison against arm D, the checks of that comparison from the raw files of both arms, and the video with the arm below arm D. To try that mode before any arm is analysed, the trial runs stand in for the arms in one process: `trialD_s101` to `s110` for arm D, `trial<E>_s101` to `s103` for the E arm. It ran through for all three arms: every check holds, and in the video each of the four robots in the MuJoCo engine reproduces its recorded score to the last digit under the settings of its own arm. Its files carry the names of arms and are made of trial runs, so they stay in `results/`, out of git.

## Files

| File | What it is |
|---|---|
| `check_same_search.py`, `same_search.json` | Short runs of the search with the code tagged `campaign-v3` and with the new code, compared score for score; one run stopped twice and continued |
| `check_same_scores.py`, `same_scores.json` | Every evaluation behind the two transfer reports computed again with the new code and compared with the committed report; the memory each evaluation used |
| `measure_memory.py`, `memory_after.json` | The worst case for MuJoCo's memory, what MuJoCo does with too little, and what a process asks the system for |
| `rehearsal_arm_D_tools/` | The tools for arm D's champions tried on the trial runs with seeds 101 to 110: their pilot report, the checks with the audit, the transfer into the 2013 simulator |
| `arms_E/check_settings.py`, `settings.json` | Small runs with each E arm's options: what each recorded differently from arm D's |
| `arms_E/check_first_population.py`, `first_population.json` | One-generation runs under the options of all four arms: the same first population |
| `arms_E/check_five_at_a_time.py`, `five_at_a_time.json` | Arm E2's command with five robots at a time against three: the same run |
| `arms_E/trial_waiting_start.py` | The trial of a launcher that waits for another arm of this project's search |
| `arms_E/trial_short_of_memory.py` | The trial of a launcher that finds too little memory at its start: started by hand, and started waiting |
| `arms_E/dress_rehearsal.py` | The arm mode of the E arms' tools, tried with trial runs standing in for the arms |
| `arms_E/rehearsal/` | The nine trial runs' launcher logs, pilot reports, checks with the audit, and stills of their videos |
