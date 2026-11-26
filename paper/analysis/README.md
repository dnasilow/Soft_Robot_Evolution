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

The rehearsals are in `tests/test_protocol_analysis.py` (31 tests with those for arm A). They need the deposited data, which is kept out of git.

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

## Arm A

Added on 23 November 2026, before any run of arm A existed. `--arm A` reads the run folders of `run_tendon_evolution.py`:

- **Scores** come from the numbered generation files (`gen_001.json` is the first population evaluated, as in the 2013 program). `history.json` is not used: it repeats a generation for every time a run was continued.
- **The champion** is the individual with the highest fitness in the stored final population (ties: the first), measured like every other champion.
- **Against arm R.** The report also sets arm A against arm R, the fifth primary comparison of the protocol, taking arm R's scores from its committed report in `../outcomes/`, and repeats arm R's own result: the floor measured for the original code.

Checked on made-up runs (the deposited cost curves standing in for arm A's scores): the report against the deposit, the comparison with arm R and the floor come out as they must, and an arm with one unfinished run is refused.

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
- **Nothing is scored twice.** Finished evaluations are kept in `results/transfer/`, keyed by body, settings and code tag. An evaluation takes one to two minutes, six with the short time step.
- **Refused** unless `run_tendon_evolution.py` and `src/` are those of the campaign's code tag.
- **The second preset** (added on 26 November 2026, committed before its first run). PROTOCOL.md, section 9.5, asks for the outcome under both presets of the campaign. `--preset cheney2013-floor` scores the same champions with the settings of arm D: the 2013 simulator's floor rule, and every body started where it is in the workspace. Under it no body needs a second evaluation "as placed". The report is written as `transfer_floor2013.*` and compares the champions that were scored under this preset on 25 November (`../diagnostics_2026-11-25/check_built_in_floor.py`) with the scores they got then. The default is untouched: from the kept evaluations the script gives the report under `--preset cheney2013` again, identical but for its date line.

What it was checked against:

| Check | Result |
|---|---|
| The search's own command line under the preset, then every robot of its final population scored by this script with the early stop left on (`tests/test_transfer_scores.py`) | The same score for every robot |
| One body through this script and through the search's evaluator object | The same score |
| A body started two voxels up | Its centre of mass ends two voxels lower than when set on the floor, and the score is the distance moved |
| Rehearsal on the 12 pilot runs at generation 10 | Ran through; seed 1 gives 1.7753, the value measured by hand before the script existed |
| Reading: made-up arm folders, a made-up deposit, a made-up replay table | The champions of the reports, their bodies, their scores; a body that is not the reported one stops the script |

38 tests for the scoring, 8 for its video tool, 8 for the champions' video tool.

## Not yet here

- Arms D and E, and arm D's transfer in the other direction (its champions in the 2013 simulator).
- Figures.
