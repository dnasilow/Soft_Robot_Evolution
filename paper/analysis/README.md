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

The rehearsals are in `tests/test_protocol_analysis.py` (51 tests with those for arms A, D and E1 to E3). They need the deposited data, which is kept out of git.

The interval of the pilot is 0.86 to 1.48 here. The summary of 21 November gave 0.86 to 1.50: it took the runs in folder-name order, this analysis takes them in seed order, and with 12 runs the resampling differs that much. `summarise_reruns.py` now uses seed order too, so the launcher's closing summary and this analysis give the same interval.

## Files

| File | Purpose |
|---|---|
| `protocol_stats.py` | The statistics, as pure functions: comparison of two sets of runs, the criterion, Holm, Fisher's exact test, what the criterion can show, and how often a comparison of few runs is read as a difference |
| `analyse_arm.py` | Reads an arm's collected runs and the deposited data and writes the report |
| `check_arm_A.py` | Checks on arm A's report after its analysis: the scores recomputed with readers of its own, each run's record of itself, seed 1 against the pilot, and the audit of every champion (simulated again in the 2013 simulator). Written on 26 November 2026, after the arm's analysis; it changes nothing in the report |
| `render_champions.py` | Videos of an analysed arm's median and best champion next to their 2013 counterparts, each simulated again in the simulator it was evolved in, with checks that the frames are the simulation that was scored. Arms R, Rc and A: the recording copy of the 2013 simulator. Arm D: this project's MuJoCo engine, and the same two robots once more in the 2013 simulator (below). Arms E1 to E3: next to arm D, each in the engine of its own arm (below) |
| `transfer_scores.py` | The transfer outcome: every final champion scored in the MuJoCo engine with the preset's settings (below) |
| `render_transfer.py` | Videos of one champion in both simulators side by side, with checks that both hold the same body and that the frames are the evaluation that was scored |
| `compare_presets.py` | The two transfer reports side by side, champion by champion: how many keep more of their score under the second preset, with the paired test of the floor test. Reads the reports only; nothing is simulated |
| `check_arm_D.py` | Checks on arm D's report after its analysis, and the audit of its champions: the scores recomputed with readers of its own, each run's record of itself and of every start, and each champion evaluated again in the MuJoCo engine (below). Written on 27 November 2026, while the arm was running and before any score of it had been read. With `--arm E1` (`E2`, `E3`) the same for those arms, with their own settings |
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

40 tests for the scoring, 8 for its video tool, 25 for the champions' video tool, 15 for the memory changes of 27 November (`tests/test_memory.py`).

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

21 tests in `tests/test_arm_D_tools.py` (29 with those added for arms E1 to E3).

What the rehearsal showed about the audit's second line, on robots that belong to no arm: of the ten trial champions, robots of a third generation, seven changed their score by under 2% at a quarter of the time step and three lost 45% to 68% of it. That says nothing about arm D. It shows what the check is for, and that under this preset a single score can rest on the time step.

## The video of arm D's champions

Added on 27 November 2026, while arm D was running. `render_champions.py --arm D` shows six robots where the other arms have four:

| Row | Robots | Simulator | What must hold, or the script stops |
|---|---|---|---|
| Top | The deposited 2013 champions with the median and the best score | The 2013 simulator | The recording copy gives what the campaign's simulator gives |
| Middle | Arm D's champions with the median and the best score (of ten: the median is the fifth) | The MuJoCo engine, where they were evolved | The evaluation of the run, run again from the body the run stored, gives the recorded score to the last digit; the frames give that score |
| Bottom | The same two robots | The 2013 simulator, which they were not evolved in | The two simulators hold the same voxels of the same materials at the same height; once the arm's transfer has been computed, the score is the one in its report |

```
python paper/analysis/render_champions.py --arm D                                   after the arm's analysis
python paper/analysis/render_champions.py --rehearsal trialD_s --generation 3       runs that are not an arm
```

Tried on the ten trial runs with seeds 101 to 110 (three generations, not an arm): the two trial champions reproduce their recorded scores in the engine to the last digit, the same bodies are found in both simulators, and their scores in the 2013 simulator are the ones the transfer tool gave them. The still picture and the record of that rehearsal are in `../diagnostics_2026-11-27/rehearsal_arm_D_tools/`. The videos of arms R, Rc and A are made by the same code as before: arm R's video, made again with the changed tool, is the committed one in every pixel of every frame, with the same record of its checks.

## Arms E1 to E3

Added on 27 November 2026, while arm D was running and before any of the three was started. What is computed for them was fixed in PROTOCOL.md, section 9.8, and committed before any of this was built. Each is arm D with one setting undone, in three runs of 300 generations:

| Arm | The engine options of its runs | The setting it undoes |
|---|---|---|
| E1 | `--preset cheney2013-floor --damping-global 0.01` | Global damping 0.001, the value of the 2013 files, back to the engine's own 0.01 |
| E2 | `--preset cheney2013-floor --amp 0.2 --poisson on` | Amplitude ±14% without the volumetric law back to ±20% with it |
| E3 | `--preset cheney2013` | The 2013 simulator's floor and start back to the hard floor with bodies set on it |

```
python paper/analysis/analyse_arm.py --arm E1               after arm D's analysis; refuses before it
python paper/analysis/check_arm_D.py --arm E1               after the arm's analysis: checks and audit
python paper/analysis/render_champions.py --arm E1          after that: the video
python paper/analysis/analyse_arm.py --what-can-the-criterion-show     what three runs can show, from the deposit alone
```

**The report** is arm D's with three differences:

- **No primary comparison.** The champion score at generation 300 is the arm's outcome, against the deposited runs with the same statistics, but it is not one of the five primary comparisons of the protocol. The report has an `outcome` where the others have a `primary`, gives the p-value uncorrected and says so.
- **Against arm D.** The same statistics once more with arm D in the place of the deposit: the ratio of medians is the E arm over arm D. This is the comparison these arms are for. It is read by whether the 95% interval of the ratio contains 1. Arm D's scores are taken from its committed report, so an E arm is not analysed before arm D.
- **What three runs can show** is printed in the report, computed from the deposited runs alone: three runs drawn from them and multiplied by a factor, set against the deposit or against ten more drawn runs.

  | True ratio of the scores | Against the deposit: the interval excludes 1 | p < 0.05 | Against a 10-run arm: the interval excludes 1 | p < 0.05 |
  |---|---|---|---|---|
  | 1 (no difference) | 10% | 3% | 8% | 5% |
  | 0.9 | 43% | 25% | 26% | 18% |
  | 0.75 | 93% | 86% | 79% | 65% |
  | 0.5 | 100% | 100% | 100% | 100% |

  So such an arm can show a loss of a quarter of the score or more. It cannot show a difference of 10%, and "not distinguishable" is no evidence that a setting does not matter. With three runs the interval of the arm's own median is the range of its three scores, and the interval reading gives a false alarm in 8 to 10% of cases; the Mann-Whitney test is exact at these sizes and keeps its 5%.

**The settings are written in one place:** the launcher's command for the arm (`search_arm.ARMS`). `search_arm.engine_options` reads the preset and the options given next to it back from that command, and the audit and the video take the evaluation's settings from there (`transfer_scores.evaluator_arguments(..., given=...)`: an option given next to a preset replaces the preset's value, as in the search). An option the script does not know stops it.

**The checks and the audit** are arm D's (`check_arm_D.py --arm E1`). What is their own:

- **The record of each run** must show the arm's command, the preset applied without the entries the command replaces, and the replaced settings with the command's values.
- **By hand** the comparison with arm D as well, from the raw files of both arms.
- **The audit** evaluates each champion again with the arm's own settings. Arms E1 and E2 stand on the 2013 simulator's floor, whose rule depends on the time step; arm E3 stands on the hard floor, which has no such rule.

**The video** (`render_champions.py --arm E1`) shows six robots: the deposited 2013 champions with the median and the best score in the 2013 simulator, arm D's median and best champion in arm D's engine, and the arm's own median and best champion (of three: the second and the first) in the engine with its setting undone. Each robot in the MuJoCo engine must reproduce its recorded score to the last digit under the settings of its own arm, or the script stops. None is shown in the 2013 simulator: the protocol names no transfer outcome for these arms.

**The same seeds.** Seeds 1 to 3 are also seeds of arm D, and a run takes its first population from its seed alone, so a run of an E arm begins with the same thirty robots as arm D's run of that seed (`../diagnostics_2026-11-27/arms_E/check_first_population.py`). The report lists the two scores of each seed side by side, without a test; the checks compare that list with the raw files of both arms.

What they were checked against (`../diagnostics_2026-11-27/arms_E/`):

| Check | Result |
|---|---|
| The reports of arms R, Rc and A, written again by the changed analysis from their committed numbers | Identical to the committed text, character for character |
| Made-up arms: ten deposited runs standing in for arm D; three others at half their scores as an E arm; three of the ten, the ones around their median, as another | The first is read as different from arm D and from the deposit, the second as not distinguishable; an E arm without arm D's report is refused; arm D's own report is untouched (`tests/test_protocol_analysis.py`) |
| For each of the three settings a run of the search's own command line, small enough for a test; its record checked like an arm's run, its champion evaluated again with the settings read back from the launcher's command | The record passes; the recorded score to the last digit (`tests/test_arm_D_tools.py`) |
| The checks and the audit on the nine trial runs of 27 November (`trialE1_s101` to `trialE3_s103`: seeds that belong to no arm, two generations each), against their pilot reports | By hand the reports' numbers. The run that was ended on purpose and continued is reported as started twice, and nothing else is flagged. All nine champions get their recorded score to the last digit under the settings of their own arm |
| The video tool on the same runs | Each trial robot's evaluation, run again and recorded, gives its recorded score to the last digit |
| A dress rehearsal of the arm mode, with trial runs standing in for arm D and for the E arm in one process (`dress_rehearsal.py`): report, checks with the comparison by hand from both arms' raw files, audit, and the six-robot video | Ran through for all three arms; every check holds. Its files carry the names of arms and are made of trial runs, so they are kept out of git |
| Made-up runs: runs made with another arm's command, a record that says the volumetric law was off, a comparison with arm D that is off or missing, a seed left out of the list | Each is caught and named |

51 tests for the analysis, 29 for the checks, the audit and the transfer of arms D and E, 25 for the video tool, 54 for the launcher.

What the rehearsal showed, on robots of a second generation that belong to no arm: under arm E2's settings the trial robots tumble and their lowest voxels stand a full voxel deep in the 2013 floor's spring (0.5 to 1.1, against 0.6 for the trial robots of arm D's settings); on arm E3's hard floor they stand 0.14 of a voxel deep and their scores change by under 2% at a quarter of the time step, where three of ten trial robots under arm D's floor rule lost half their score. None of this is a result of an arm. It is what the audit and the videos are there to show.

## Not yet here

- Figures.
