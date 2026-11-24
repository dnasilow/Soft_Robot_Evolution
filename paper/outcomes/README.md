# Outcomes of the campaign

Reports of `paper/analysis/analyse_arm.py`, computed as fixed in [PROTOCOL.md](../PROTOCOL.md) and copied here from `results/analysis/` (which is kept out of git) once an arm is complete.

## Arm R: the original 2013 experiment, re-executed

35 runs of the authors' search program and simulator, built here from their source: seeds 1 to 35, 1000 generations, no cost. Started 21 November 2026 at 23:27, complete on 22 November at 21:40. Analysed once, on 22 November at 22:23, with the code of commit 27e89df. The report says "dirty" because the tracked simulator log `MUJOCO_LOG.TXT` differed from the commit; nothing else did.

**Arm R reproduces the deposited 2013 runs, by the criterion fixed before the campaign.**

| Champion score, best so far | Arm R, median (quartiles) | Deposited 2013, median (quartiles) | Ratio of medians (95% interval) | A12 (95% interval) | p (Mann-Whitney) |
|---|---|---|---|---|---|
| Generation 1000, primary | 4.41 (4.27–4.71) | 4.39 (4.20–5.07) | 1.00 (0.94–1.05) | 0.48 (0.34–0.62) | 0.75 |
| Generation 300 | 3.91 (3.49–4.19) | 3.70 (3.52–4.11) | 1.06 (0.96–1.10) | 0.54 (0.40–0.67) | 0.60 |
| Generation 100 | 3.31 (2.81–3.78) | 3.26 (2.75–3.59) | 1.02 (0.90–1.17) | 0.52 (0.38–0.65) | 0.81 |

- **Primary outcome.** Ratio of medians 1.004, 95% interval 0.942 to 1.048, inside 0.90 to 1.10. A perfect reproduction would have met this criterion in 66% of cases (PROTOCOL.md, section 9.2).
- **Holm.** Over the five primary comparisons it is final only when all arms are in. For this comparison it will lie between 0.75 and 1.

The body of each run's final champion:

| Measure | Arm R, median (quartiles) | Deposited 2013, median (quartiles) | A12 (95% interval) | p | p (Holm, five measures) |
|---|---|---|---|---|---|
| Voxels | 675 (598–704) | 652 (594–698) | 0.52 (0.38–0.66) | 0.77 | 1.00 |
| Footprint, cells | 24 (16–30) | 26 (14–40) | 0.44 (0.30–0.58) | 0.39 | 1.00 |
| Fill of the bounding box | 0.68 (0.60–0.70) | 0.65 (0.59–0.70) | 0.52 (0.38–0.66) | 0.81 | 1.00 |
| Muscle fraction | 0.99 (0.95–1.00) | 1.00 (0.96–1.00) | 0.45 (0.32–0.58) | 0.46 | 1.00 |
| Two or more separate feet | 3 of 35 | 1 of 35 | | 0.61 (Fisher) | 1.00 |

Checks made on the result:

| Check | Result |
|---|---|
| The primary numbers recomputed from the raw curve files, without the analysis code | Medians 4.4103 and 4.3931, ratio 1.0039 |
| The launcher's closing summary, which resampled the runs in another order | The same interval, 0.942 to 1.048 |
| The first ten generations of seeds 1 to 12 against the pilot of 21 November | Identical in all 12 |
| Each champion's fitness in its file name against the last row of its run's curve | Agree in all 35 |
| Audit: each champion re-simulated in the 2013 simulator (`arm_R_champion_audit.csv`) | All 35 reproduce their recorded score, to the six digits the simulator prints |

The arm was launched once and no run was interrupted, so no seed was started more than once.

Not yet done for this arm: the transfer scores, each champion scored in the MuJoCo engine (a secondary outcome of the protocol).

## Arm Rc: the original 2013 experiment with the actuated-voxel cost, re-executed

35 runs of the same two programs with the cost condition of 2013 (the search program's `-P 2`): seeds 1 to 35, 1000 generations. Started 22 November 2026 at 23:19; cut short on 23 November at 08:46, when three runs had finished; its 32 unfinished seeds started again from the beginning at 09:00; complete at 23:20 (the slowest run took 14.3 hours). Analysed once, on 24 November at 10:08, with the code of commit aa83d02 (again "dirty" only for `MUJOCO_LOG.TXT`).

**Arm Rc is not distinguishable from the deposited 2013 cost runs. Reproduction within 10% is not shown, and could not have been:** in this condition a perfect reproduction meets the criterion in 0% of cases (PROTOCOL.md, section 9.2, recorded before any arm was analysed).

| Champion's original score, best so far | Arm Rc, median (quartiles) | Deposited 2013, median (quartiles) | Ratio of medians (95% interval) | A12 (95% interval) | p (Mann-Whitney) |
|---|---|---|---|---|---|
| Generation 1000, primary | 3.57 (3.30–4.13) | 3.41 (3.23–4.08) | 1.05 (0.88–1.12) | 0.54 (0.40–0.68) | 0.55 |
| Generation 300 | 3.06 (2.73–3.33) | 3.25 (2.77–3.60) | 0.94 (0.88–1.05) | 0.43 (0.30–0.57) | 0.32 |
| Generation 100 | 2.60 (2.23–2.85) | 2.65 (2.30–2.98) | 0.98 (0.85–1.10) | 0.47 (0.33–0.60) | 0.66 |

- **Primary outcome.** Ratio of medians 1.046, 95% interval 0.876 to 1.119. It contains 1 and is not inside 0.90 to 1.10.
- **Holm.** For this comparison it will lie between 0.55 and 1.

The body of each run's final champion:

| Measure | Arm Rc, median (quartiles) | Deposited 2013, median (quartiles) | A12 (95% interval) | p | p (Holm, five measures) |
|---|---|---|---|---|---|
| Voxels | 363 (296–452) | 362 (292–432) | 0.50 (0.37–0.64) | 0.97 | 1.00 |
| Footprint, cells | 7 (4–16) | 5 (3–14) | 0.56 (0.42–0.70) | 0.38 | 1.00 |
| Fill of the bounding box | 0.46 (0.41–0.50) | 0.44 (0.36–0.50) | 0.56 (0.42–0.70) | 0.38 | 1.00 |
| Muscle fraction | 0.62 (0.46–0.94) | 0.60 (0.51–0.86) | 0.51 (0.38–0.65) | 0.85 | 1.00 |
| Two or more separate feet | 1 of 35 | 0 of 35 | | 1.00 (Fisher) | 1.00 |

The cost changes the bodies the way it did in 2013: about half the voxels of the no-cost champions (363 against 675 in arm R) and less muscle (0.62 against 0.99).

Checks made on the result:

| Check | Result |
|---|---|
| The primary numbers recomputed from the raw curve files, without the analysis code | Medians 3.5692 and 3.4124, ratio 1.0459 |
| **Each of the 32 interrupted attempts against the run that replaced it** | Identical in every generation the attempt had reached (395 to 934 generations): the restart repeated the lost run, as the protocol assumes |
| The first ten generations of seeds 3 and 5 against the cost trial of 22 November | Identical |
| Each champion's fitness in its file name against the last row of its run's curve | Agree in all 35; the cost lowered the fitness of all 35 |
| Audit: each champion re-simulated in the 2013 simulator (`arm_Rc_champion_audit.csv`) | All 35 reproduce their recorded original score, to the six digits the simulator prints |

32 of this arm's 35 seeds were started twice (the three that had finished were kept). The unfinished attempts are kept on the WSL side in `runs/_interrupted/`.

Not yet done for this arm: the transfer scores.

## Files

| File | Content |
|---|---|
| `arm_R.txt`, `arm_Rc.txt` | The reports as printed, with every seed |
| `arm_R.json`, `arm_Rc.json` | The same as data: every number, every seed's scores and champion |
| `arm_R_champion_audit.csv`, `arm_Rc_champion_audit.csv` | The audits: recorded score and re-simulated distance of each champion |
