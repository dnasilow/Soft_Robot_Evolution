# Analysis protocol for paper 1

**Status: draft for approval, not yet frozen.** It becomes binding when this line is replaced by "Frozen on <date>" and committed, before the first campaign run. Pilot runs made before that date are reported as pilots and are not part of any arm.

## 1. Question

Does independent re-evolution reproduce the scores and body types of Cheney et al. 2013, and what moves the outcome when it does not?

## 2. Arms

Population 30 in every arm, as in 2013. Seeds are the unit of analysis.

| Arm | Simulator | Search | Condition | Seeds | Generations |
|---|---|---|---|---|---|
| A | Original 2013 simulator (`--simulator voxelyze2013`) | This project's CPPN-NEAT as it is (`--no-age-pareto`) | No cost | 1–35 | 1000 |
| B | Original 2013 simulator | CPPN-NEAT set to the 2013 settings file | No cost | 1–35 | 1000 |
| C | Original 2013 simulator | Whichever of A and B has the higher median at generation 1000 | Actuated cost (`--penalty actuated`) | 1–35 | 1000 |
| D | MuJoCo engine with `--preset cheney2013` | Same search as arm C | No cost | 1–10 | 300 |
| E1 | MuJoCo engine, preset, global damping back to 0.01 | Same | No cost | 1–3 | 300 |
| E2 | MuJoCo engine, preset, amplitude ±20% with the volumetric law on | Same | No cost | 1–3 | 300 |
| E3 | MuJoCo engine, preset, the soft floor of September 2026 | Same | No cost | 1–3 | 300 |

Arm B needs the switch for the 2013 search settings, which is not built yet. Arms A and B differ only in the search; A, B and C differ from D only in the simulator; E1 to E3 each undo one setting.

## 3. Reference data

The deposited 2013 data: champion score by generation for 35 runs per condition (`softbots2013GenchampData.tgz`), and the generation-1000 robots (`softbots2013Gen1000.tgz`). The no-cost condition is the reference for arms A, B, D and E; the actuated-cost condition for arm C.

## 4. Outcomes

A run's champion at a generation is the individual with the best fitness (after any penalty) in that generation; its score is its original, unpenalised 2013 score. The best such score up to that generation is used, and the deposited curves are read the same way.

- **Primary.** Champion score at generation 1000 for arms A, B and C; at generation 300 for arm D. Each is compared with the deposited runs at the same generation.
- **Secondary, scores.** The same at generations 100 and 300.
- **Secondary, body.** For each run's final champion: voxels, footprint, fill of the bounding box, muscle fraction, and whether it has two or more separate feet, all from `morphology_scorecard.body_metrics`, the same code used on the deposited robots.
- **Secondary, transfer.** Every champion of arms A to C scored in the MuJoCo engine with the preset; every champion of arm D scored in the 2013 simulator.

## 5. Statistics

- Two-sided Mann-Whitney U, each arm against the deposited runs. Holm correction over the four primary comparisons (A, B, C, D), and separately within the body measures.
- Effect size: Vargha-Delaney A12 with a bootstrapped 95% interval.
- Bootstrapped 95% interval of the ratio of medians (arm over deposited), 10,000 resamples of runs.
- **Reproduction criterion, fixed in advance:** an arm reproduces its reference condition if that interval of the ratio of medians lies inside 0.90 to 1.10. Otherwise the gap is reported with its interval. The floor measured for the original code itself (same source, different compiler) is reported alongside.

## 6. Rules

- Every seed is reported, including failures.
- A run that dies is resumed from its checkpoint, never replaced by another seed.
- No arm is extended, shortened or re-seeded after its results have been looked at.
- If a defect is found in the code, the whole affected arm is rerun and the paper says so.
- Every champion gets the audit (reproduced score, and for MuJoCo champions a quarter time step and floor penetration). The audit is reported; it is not used to drop runs.
- Each run's `manifest.json` records its command, settings and code version; the campaign runs from one tagged commit.

## 7. Exploratory, and labelled as such in the paper

Everything not listed above: conditions that favour limbs, gravity, longer runs, other search methods.

## 8. Open points to settle before freezing

1. Arm B: which of the 2013 search details count as "the 2013 settings" (mutation rates, tournament size, elitism and species target for certain; the activation-function set and the starting networks need to be read from the 2013 source).
2. Arm C needs the original score of each generation's champion stored during the run. Today only the fitness after the penalty is stored.
3. Number of seeds for arm D and for E1 to E3, once the cost of a MuJoCo run under the preset has been measured.
4. Whether two or three 2013-simulator runs can share the machine without slowing each other.
