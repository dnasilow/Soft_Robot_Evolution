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

## Arm A

Added on 23 November 2026, before any run of arm A existed. `--arm A` reads the run folders of `run_tendon_evolution.py`:

- **Scores** come from the numbered generation files (`gen_001.json` is the first population evaluated, as in the 2013 program). `history.json` is not used: it repeats a generation for every time a run was continued.
- **The champion** is the individual with the highest fitness in the stored final population (ties: the first), measured like every other champion.
- **Against arm R.** The report also sets arm A against arm R, the fifth primary comparison of the protocol, taking arm R's scores from its committed report in `../outcomes/`, and repeats arm R's own result: the floor measured for the original code.

Checked on made-up runs (the deposited cost curves standing in for arm A's scores): the report against the deposit, the comparison with arm R and the floor come out as they must, and an arm with one unfinished run is refused.

## Not yet here

- Arms D and E.
- The transfer scores: every champion scored in the other simulator. It needs the finished champions and some processor time.
- Figures.
