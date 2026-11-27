# The analysis of the protocol

22 November 2026. Developed and tested on the pilot runs and on the deposited 2013 data, and committed before it was first run on an arm. Arm R had finished earlier that evening; its results were not consulted while this was written. What it computes is fixed in [PROTOCOL.md](../PROTOCOL.md), sections 4, 5 and 9.

```
python paper/analysis/analyse_arm.py --arm R                              the arm's report
python paper/analysis/analyse_arm.py --pilot pilot10_P0_s --generation 10   runs that are not an arm
python paper/analysis/analyse_arm.py --what-can-the-criterion-show         from the deposited runs alone
```

## What an arm's report contains

- **Scores.** The champion's original score, best so far, at generations 1000 (primary), 300 and 100, against the 35 deposited runs: medians, the ratio of medians with its bootstrapped 95% interval, A12 with its interval, and the two-sided Mann-Whitney test.
- **The criterion.** For the primary outcome: *reproduces* (the interval of the ratio lies inside 0.90 to 1.10), *not distinguishable* (not inside, but it contains 1) or *differs* (it excludes 1). With it, how often a perfect reproduction would meet the criterion.
- **Body.** Each run's final champion measured with the code used on the deposited robots: voxels, footprint, fill, muscle fraction, and two or more separate feet, corrected by Holm within the arm.
- **Every seed**, with its generations, scores and champion.

The report is printed and written to `results/analysis/` as text and as JSON. The reports of finished arms are kept in [`../outcomes/`](../outcomes/README.md).

An arm is analysed only as a whole: while one of its seeds is unfinished the script computes nothing and says which seeds are missing. A seed that fails for good has to be named with `--failed-seeds`; it is then reported and left out.

## What it was checked against

| Check | Result |
|---|---|
| The 12-seed pilot at generation 10 | Medians 1.71 and 1.50, ratio 1.14, p = 0.36, as in the pilot summary of 21 November |
| The deposited no-cost runs dressed up as an arm, against themselves | Ratio 1.00, A12 0.50, "reproduces", every body test p = 1 |
| The deposited champions | 652 voxels, footprint 26, muscle fraction 1.00, one of 35 with two feet: the figures of 18 November |
| The deposited cost runs dressed up as an arm, against the no-cost runs | Ratio 0.78 (0.72 to 0.90), "differs"; smaller bodies with less muscle |
| An arm with a seed short of its generations, unfinished, failed, or missing | Refused, nothing computed |

The rehearsals are in `tests/test_protocol_analysis.py` (36 tests with those for arms A and D). They need the deposited data, which is kept out of git.

The interval of the pilot is 0.86 to 1.48 here. The summary of 21 November gave 0.86 to 1.50: it took the runs in folder-name order, this analysis takes them in seed order, and with 12 runs the resampling differs that much. `summarise_reruns.py` now uses seed order too, so the launcher's closing summary and this analysis give the same interval.

## Files

| File | Purpose |
|---|---|
| `protocol_stats.py` | The statistics, as pure functions: comparison of two sets of runs, the criterion, Holm, Fisher's exact test, and what the criterion can show |
| `analyse_arm.py` | Reads an arm's collected runs and the deposited data and writes the report |
| `check_arm_A.py` | Checks on arm A's report after its analysis: the scores recomputed with readers of its own, each run's record of itself, seed 1 against the pilot, and the audit of every champion (simulated again in the 2013 simulator). Written on 26 November 2026, after the arm's analysis; it changes nothing in the report |
| `render_champions.py` | Videos of an analysed arm's median and best champion next to their 2013 counterparts, simulated in the recording copy of the 2013 simulator, with checks that the frames are the simulation that was scored |
| `transfer_scores.py` | The transfer outcome: every final champion scored in the MuJoCo engine with the preset's settings (below) |
| `render_transfer.py` | Videos of one champion in both simulators side by side, with checks that both hold the same body and that the frames are the evaluation that was scored |
| `compare_presets.py` | The two transfer reports side by side, champion by champion: how many keep more of their score under the second preset, with the paired test of the floor test. Reads the reports only; nothing is simulated |
| `check_arm_D.py` | Checks on arm D's report after its analysis, and the audit of its champions: the scores recomputed with readers of its own, each run's record of itself and of every start, and each champion evaluated again in the MuJoCo engine (below). Written on 27 November 2026, while the arm was running and before any score of it had been read |
| `transfer_to_2013.py` | Arm D's transfer outcome: its champions scored in the original 2013 simulator (below). Written the same day |

## Arm A

Added on 23 November 2026, before any run of arm A existed. `--arm A` reads the run folders of `run_tendon_evolution.py`:

- **Scores** come from the numbered generation files (`gen_001.json` is the first population evaluated, as in the 2013 program). `history.json` is not used: it repeats a generation for every time a run was continued.
- **The champion** is the individual with the highest fitness in the stored final population (ties: the first), measured like every other champion.
- **Against arm R.** The report also sets arm A against arm R, the fifth primary comparison of the protocol, taking arm R's scores from its committed report in `../outcomes/`, and repeats arm R's own result: the floor measured for the original code.

Checked on made-up runs (the deposited cost curves standing in for arm A's scores): the report against the deposit, the comparison with arm R and the floor come out as they must, and an arm with one unfinished run is refused.

## Arm D

Added on 27 November 2026, before any run of arm D existed. `--arm D` reads its run folders the way arm A's are read. What is its own:

- **Ten seeds and 300 generations** (PROTOCOL.md, section 2). The primary outcome is the champion score at generation 300, the secondary one at generation 100, each against the deposited runs at the same generation (section 4). Its scores are the ones this project's MuJoCo engine gave under `--preset cheney2013-floor`.
- **The body table** sets the arm's champions of generation 300 against the deposited champions of generation 1000, the only robots the deposit holds, and the report says so in a note.
- **No second comparison.** The fifth primary comparison of the protocol is arm A against arm R; arm D is set against the deposit only.

Checked on made-up runs (the first 300 generations of ten deposited no-cost runs standing in for its scores): the primary outcome is read at generation 300, the deposit's median at that generation is the one the report gives, the note about the body table is there, every seed is listed, and an arm with one run a generation short is refused.

## The transfer outcome

Added on 24 November 2026. What it computes was fixed in PROTOCOL.md, section 9.4, before any champion of an arm was scored in the MuJoCo engine.

```
python paper/analysis/transfer_scores.py --arms R Rc A                         analysed arms and the deposited champions
python paper/analysis/transfer_scores.py --arms R Rc A --preset cheney2013-floor   the same under the settings of arm D
python paper/analysis/transfer_scores.py --rehearsal pilot10_P0_s --generation 10   runs that are not an arm
python paper/analysis/render_transfer.py                                       the video, from the report in ../outcomes/
```

- **What is scored.** The final champion of every run of the named arms, taken from the arm's committed report, and the champions of the 35 deposited runs of the same condition. An arm without a report is refused.
- **How.** With the search's own evaluation under `--preset cheney2013`. The settings are read from the preset in `run_tendon_evolution.py`; the script stops if the preset holds a setting it does not know. One evaluation of 0.25 s per champion, with the search's early stop switched off.
- **Two starts.** The 2013 simulator starts a body where it is in the workspace, in the air if it does not touch the bottom; the MuJoCo engine sets every body on the floor. A champion that does not touch the bottom is scored both ways, and the statistics are given both ways. On the floor is the preset as it is.
- **The ratio.** Score in the MuJoCo engine over the score in this campaign's build of the 2013 simulator. For deposited champions that score comes from the replay of all deposited robots; the 2013 figure is reported next to it.
- **Time-step check.** The first five champions of each set once more with a quarter of the time step.
- **Nothing is scored twice.** Finished evaluations are kept in `results/transfer/`, keyed by body, settings and code tag. An evaluation takes one to two minutes, six with the short time step. Every code tag of the campaign computes the same scores under a preset it has, so an evaluation is kept under the first tag that has the preset (`campaign-v2` for `cheney2013`, `campaign-v3` for `cheney2013-floor`) and is found again under a later one.
- **Refused** unless `run_tendon_evolution.py` and `src/` are those of the campaign's code tag.
- **Memory, and an evaluation that fails** (27 November 2026; PROTOCOL.md, section 9.6). The script sets one linear-algebra thread for itself and its worker processes before it loads numpy, as the launcher does for a run. A worker then asks the system for about 0.1 GB instead of up to 3.2, so the number of workers is no longer held down by memory (0.5 GB is allowed for each, 6 GB are left free). And it follows the search's rule for an evaluation that ends in an error: a body gets 0 only for an error that is its own (`ValueError` or `ArithmeticError`, not about memory), with the error recorded; any other error stops the scoring. All 431 evaluations behind the two reports were computed again that day and gave the recorded scores (`../diagnostics_2026-11-27/check_same_scores.py`).
- **The second preset** (added on 26 November 2026, committed before its first run). PROTOCOL.md, section 9.5, asks for the outcome under both presets of the campaign. `--preset cheney2013-floor` scores the same champions with the settings of arm D: the 2013 simulator's floor rule, and every body started where it is in the workspace. Under it no body needs a second evaluation "as placed". The report is written as `transfer_floor2013.*` and compares the champions that were scored under this preset on 25 November (`../diagnostics_2026-11-25/check_built_in_floor.py`) with the scores they got then. The default is untouched: from the kept evaluations the script gives the report under `--preset cheney2013` again, identical but for its date line.

What it was checked against:

| Check | Result |
|---|---|
| The search's own command line under the preset, then every robot of its final population scored by this script with the early stop left on (`tests/test_transfer_scores.py`) | The same score for every robot |
| One body through this script and through the search's evaluator object | The same score |
| A body started two voxels up | Its centre of mass ends two voxels lower than when set on the floor, and the score is the distance moved |
| Rehearsal on the 12 pilot runs at generation 10 | Ran through; seed 1 gives 1.7753, the value measured by hand before the script existed |
| Reading: made-up arm folders, a made-up deposit, a made-up replay table | The champions of the reports, their bodies, their scores; a body that is not the reported one stops the script |

39 tests for the scoring, 8 for its video tool, 8 for the champions' video tool, 15 for the memory changes of 27 November (`tests/test_memory.py`).

## Arm D's champions: the audit and the transfer

Added on 27 November 2026, while arm D was running and before any score of it had been read. What they compute was fixed in PROTOCOL.md, section 9.7, and committed before either was built. Both refuse to run on the arm while it has no report in `../outcomes/`.

```
python paper/analysis/check_arm_D.py                      after the arm's analysis: checks and audit
python paper/analysis/transfer_to_2013.py --arm D          after the arm's analysis: its champions in the 2013 simulator
python paper/analysis/check_arm_D.py --rehearsal trialD_s --seeds 101-110 --generations 3     runs that are not an arm
python paper/analysis/transfer_to_2013.py --rehearsal trialD_s --generation 3                  runs that are not an arm
```

**The checks** follow those of arm A: the scores again from the raw files; each run's own record; the champions against their runs. What is new for this arm:

- **Every start of every run** is read from the run's manifest: the command, the settings, one linear-algebra thread, and code that is the tag `campaign-v4` in every file that computes a run. A run started more than once is reported with what the launcher's log says about why. That is not a failure: a continued run is the run it would have been (protocol, section 9.3).
- **Bodies the engine refused** (they score 0) and **runs that stopped themselves** (section 9.6) are counted from the runs' own output.

**The audit** (section 9.7, point 2) evaluates each champion again in the MuJoCo engine, from the body its run stored and with the evaluation of its run:

- **Reproduced score.** Identical to the recorded score to the last digit, or not.
- **A quarter of the time step.** The change of the score, per champion, with its median and largest value. Under arm D's preset the floor rule depends on the time step, so this is not numerical error alone.
- **Floor penetration.** How deep the lowest voxel sank below the floor's surface.

The body is evaluated as the run stored it, inside the larger array the search works with, not cut out to the workspace: only then is the recorded score reproduced to the last digit.

**The transfer** scores each champion once in this campaign's build of the 2013 simulator, by the evaluation arm A's search used, and checks by its checksum that the program is the one arms R, Rc and A ran with. The ratio is the 2013 score over the recorded MuJoCo score. The statistics are those of the transfer outcome above; the comparison is made against the deposited no-cost champions' ratios under `--preset cheney2013-floor`.

What they were checked against:

| Check | Result |
|---|---|
| Arm A's 35 champions through the transfer tool. They were evolved in the 2013 simulator, so their scores there are on record | All 35 get exactly their recorded score |
| A run of the search's own command line under arm D's preset, small enough for a test; its champion evaluated again by the audit | The recorded score to the last digit (`tests/test_arm_D_tools.py`) |
| The checks and the audit on the ten trial runs of 27 November (`trialD_s101` to `trialD_s110`: seeds that belong to no arm, three generations each), against their pilot report | By hand the report's numbers. The run that was ended on purpose and continued is reported as started twice, and nothing else is flagged. All ten champions get their recorded score to the last digit when evaluated again |
| The transfer on the same ten champions | Ten simulations; the simulator is by its checksum the program of arms R, Rc and A |
| Made-up runs: a wrong number in the report, a start with another setting, without the one thread, with changed code, a checkpoint left over, a score off in the thirteenth digit | Each is caught and named |

21 tests in `tests/test_arm_D_tools.py`.

What the rehearsal showed about the audit's second line, on robots that belong to no arm: of the ten trial champions, robots of a third generation, seven changed their score by under 2% at a quarter of the time step and three lost 45% to 68% of it. That says nothing about arm D. It shows what the check is for, and that under this preset a single score can rest on the time step.

## Not yet here

- Arms E1 to E3, in the launcher, the analysis and the audit.
- A video of arm D's champions in the engine they were evolved in.
- Figures.
