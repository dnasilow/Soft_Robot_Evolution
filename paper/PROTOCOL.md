# Analysis protocol for paper 1

**Frozen on 21 November 2026.** This protocol is binding from the commit that carries this line, made before the first campaign run. Pilot and trial runs made before it are reported as such and are not part of any arm. Anything changed afterwards is listed in section 9 with its date and reason.

## 1. Question

Does independent re-evolution reproduce the scores and body types of Cheney et al. 2013, and what moves the outcome when it does not?

## 2. Arms

Population 30 in every arm, as in 2013. Seeds are the unit of analysis.

| Arm | Simulator | Search | Condition | Seeds | Generations |
|---|---|---|---|---|---|
| R | Original 2013 simulator | **Original 2013 search program**, both built from the authors' source (`run_2013_search.sh`) | No cost | 1–35 | 1000 |
| Rc | Original 2013 simulator | Original 2013 search program | Actuated cost (its `-P 2`) | 1–35 | 1000 |
| A | Original 2013 simulator (`--simulator voxelyze2013`) | This project's CPPN-NEAT as it is (`--no-age-pareto`) | No cost | 1–35 | 1000 |
| D | MuJoCo engine with `--preset cheney2013` | This project's CPPN-NEAT as it is | No cost | 1–10 | 300 |
| E1 | MuJoCo engine, preset, global damping back to 0.01 | Same | No cost | 1–3 | 300 |
| E2 | MuJoCo engine, preset, amplitude ±20% with the volumetric law on | Same | No cost | 1–3 | 300 |
| E3 | MuJoCo engine, preset, the soft floor of September 2026 | Same | No cost | 1–3 | 300 |

The arms form a ladder. R and Rc re-execute the original code with new seeds: does the experiment repeat? A replaces the search with an independent one in the same simulator. D replaces the simulator as well. E1 to E3 each undo one physics setting.

Arms R and Rc are started with `paper/reference_2013/start_arm.py`. Their runs are named `armR_P0_s<seed>` and `armRc_P2_s<seed>`.

## 3. Reference data

The deposited 2013 data: champion score by generation for 35 runs per condition (`softbots2013GenchampData.tgz`), and the generation-1000 robots (`softbots2013Gen1000.tgz`). The no-cost condition is the reference for arms R, A, D and E; the actuated-cost condition for arm Rc.

## 4. Outcomes

A run's champion at a generation is the individual with the best fitness (after any penalty) in that generation; its score is its original, unpenalised 2013 score. The best such score up to that generation is used, and the deposited curves are read the same way.

- **Primary.** Champion score at generation 1000 for arms R, Rc and A; at generation 300 for arm D. Each is compared with the deposited runs at the same generation, and A also with R.
- **Secondary, scores.** The same at generations 100 and 300.
- **Secondary, body.** For each run's final champion: voxels, footprint, fill of the bounding box, muscle fraction, and whether it has two or more separate feet, all from `morphology_scorecard.body_metrics`, the same code used on the deposited robots.
- **Secondary, transfer.** Every champion of arms R, Rc and A scored in the MuJoCo engine with the preset; every champion of arm D scored in the 2013 simulator.

## 5. Statistics

- Two-sided Mann-Whitney U, each arm against the deposited runs. Holm correction over the five primary comparisons (R, Rc, A and D against the deposit, A against R), and separately within the body measures.
- Effect size: Vargha-Delaney A12 with a bootstrapped 95% interval.
- Bootstrapped 95% interval of the ratio of medians (arm over deposited), 10,000 resamples of runs.
- **Reproduction criterion, fixed in advance:** an arm reproduces its reference condition if that interval of the ratio of medians lies inside 0.90 to 1.10. Otherwise the gap is reported with its interval. The floor measured for the original code itself (same source, different compiler) is reported alongside.

## 6. Rules

- Every seed is reported, including failures.
- A run that dies is never replaced by another seed. A run of this project's search is resumed from its checkpoint. A run of the original program (arms R and Rc) is started again from the beginning with the same seed: that program gives the same run for the same seed (section 8, point 2), so this repeats the lost run. Its own restart switch (`-X`) is not used, because it has not been validated here. The unfinished attempt is kept, and the paper reports how many seeds were started more than once.
- No arm is extended, shortened or re-seeded after its results have been looked at.
- If a defect is found in the code, the whole affected arm is rerun and the paper says so.
- Every champion gets the audit (reproduced score, and for MuJoCo champions a quarter time step and floor penetration). The audit is reported; it is not used to drop runs.
- Each run's `manifest.json` records its command, settings and code version. Arms R and Rc are not started by this project's evolution script, so their launcher records the same in `results/rerun2013/<arm>_launches.json`, together with the checksums of the two programs, their libraries and the settings file, and refuses to continue an arm on a different build.
- The campaign runs from the code tagged `campaign-v1`. Later commits may add documentation and analysis; they do not change what a run computes.

## 7. Exploratory, and labelled as such in the paper

Everything not listed above: porting single 2013 search settings into this project's CPPN-NEAT to find which one matters, this project's search under the cost condition, conditions that favour limbs, gravity, longer runs, other search methods.

## 8. Points settled at the freeze

The draft of this protocol left three points open and one rule imprecise. They were settled as follows when it was frozen.

1. **Seeds for arm D and for E1 to E3** are as in the table: 10 and 3. The cost of a MuJoCo run under the preset has not been measured yet; a timing pilot will measure it. If it shows that an arm cannot finish in time, the arm's seeds or generations may be reduced only before its first run is started, and the change is recorded in section 9.
2. **How many runs share the machine.** All 35 runs of arm R, and later of arm Rc, run side by side, one core each. This is a matter of machine time, not of design: for a given seed the original program gives the same scores however many runs share the machine, and when it is started again. Checked before the freeze: seeds 1 to 3 over ten generations, three side by side against twelve side by side, every score identical; seeds 1 and 2 cut short and started again, identical over the two generations run. The two programs were also rebuilt from the scripts in this repository and came out byte for byte the ones the pilot ran with.
3. **This project's search under the cost condition** stays exploratory (section 7). It is not an arm.
4. **Runs that die.** The draft said such a run "is resumed from its checkpoint". For the original program that is replaced by starting the same seed again from the beginning (section 6), which point 2 shows to be the same run. No seed is ever replaced by another.

## 9. Changes after the freeze

No change to the arms, the outcomes, the tests or the criterion.

### 9.1 Details of the analysis, fixed on 22 November 2026

Fixed on the evening of 22 November 2026. Arm R had finished at 21:40 and its launcher had printed its closing summary in the campaign window; these details were written without consulting that summary or any other result of the arm. Up to then the analysis had read only the runs' generation counts and file counts. The analysis is `paper/analysis/analyse_arm.py`. It was developed and tested on the pilot runs and on arms made up from the deposited runs themselves, and committed before it was first run on an arm.

1. **Scores.** A run's score at generation g is the largest champion original fitness (column 2 of the program's learning-curve file) in generations 1 to g. The deposited curves are read the same way.
2. **Final champion.** The robot with the highest adjusted fitness in the population of the last generation, by the fitness in its file name. Ties go to the first file name. The same rule picks the champion of each deposited run.
3. **Body measures.** From `morphology_scorecard.body_metrics`: voxels, footprint, fill, muscle fraction (the two muscle materials over all voxels), and "two or more separate feet" as its `feet` count being 2 or more, where feet are the separate face-connected patches of the body's lowest layer.
4. **Bootstrap.** 10,000 resamples. The arm's runs and the reference runs are each resampled with replacement, independently. The interval runs from the 2.5th to the 97.5th percentile. The random seed is fixed at 0 and the runs are taken in seed order, so a report can be reproduced to the last digit.
5. **Tests.** Mann-Whitney U, two-sided, as SciPy computes it by default. The one yes/no measure, two or more feet, is tested with Fisher's exact test, two-sided.
6. **Holm.** The five primary comparisons are one family. Its correction can be computed only when all five exist; until then a report gives the uncorrected p and the range the corrected one can still take. The body measures are corrected within each arm: its five measures against the deposit are one family.
7. **Reading the criterion.** Three outcomes, by the 95% interval of the ratio of medians. Inside 0.90 to 1.10: the arm *reproduces* its reference. Not inside, but containing 1: the arm is *not distinguishable* from its reference, and reproduction within 10% is not shown. Excluding 1: the arm *differs*.
8. **Whole arms only.** The analysis computes nothing for an arm while one of its seeds is unfinished. A seed that fails again when it is started again is reported and left out of the statistics, which then say how many runs they use.

### 9.2 What the criterion can show, computed on 22 November 2026 from the deposited runs alone

How often would a perfect reproduction meet the criterion? New runs were drawn from the deposited runs themselves, so that they come from the same distribution by construction, and analysed like an arm (`analyse_arm.py --what-can-the-criterion-show`).

| Design | A perfect reproduction meets the criterion in | The deposit against itself gives the interval |
|---|---|---|
| Arms R and A: 35 runs, generation 1000, no cost | 66% of cases | 0.94 to 1.06 |
| Arm Rc: 35 runs, generation 1000, actuated cost | 0% of cases | 0.85 to 1.17 |
| Arm D: 10 runs, generation 300, no cost | 17% of cases | 0.93 to 1.08 |

The criterion is unchanged, and these figures are reported with each result. In the cost condition the median of 35 runs is too unsteady for a 10% window, so arm Rc can only come out as "not distinguishable" or "differs". With 10 runs the same holds for arm D in five cases out of six.
