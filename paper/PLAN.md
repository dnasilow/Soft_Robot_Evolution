# Research and paper plan: evolving voxel soft robots

Written 18–19 November 2026. Companion files: [LITERATURE.md](LITERATURE.md) (what has already been done), [literature_notes/](literature_notes/) (detailed notes per topic), [diagnostics_2026-11-18/](diagnostics_2026-11-18/) (the checks behind section 3).

Everything here is a proposal until you approve it. Section 13 lists the decisions that are yours.

---

## 1. Decisions you have made

| Topic | Decision |
|---|---|
| Venue | GECCO 2027 first, ALIFE 2027 as fallback |
| Compute | This workstation only |
| Author | Solo. Affiliation: see section 11 (recommendation: "Independent Researcher") |
| Paper focus | Decided 21 November 2026: paper 1 is the reproduction and audit of the 2013 benchmark (section 5). Body-first moves to paper 2. |

**GECCO 2027** (read from the official site): Kraków, 12–16 July 2027, in person only. Abstract (200 words) due **18 January 2027**, full paper due **25 January 2027**, both stated as non-extensible; the site gives no time zone, so plan to submit a day early. Decision 19 March, camera-ready 9 April. Eight pages excluding references, ACM `acmart` sigconf, double-blind.

**ALIFE 2027**: Prague, 19–23 July 2027. No call yet. In 2026 the deadline was 30 March, extended to 12 April.

---

## 2. Where the project stands

**What exists**

- A voxel soft-robot engine on MuJoCo (`--body beam`): Voxelyze-style beam bonds applied as explicit forces, stick-slip floor friction, per-robot time step, a divergence guard. 105 unit and pipeline tests; on a clean copy of commit `ebf3a28`, 94 pass and 11 are skipped because they need run outputs that are not in the repository.
- Three search methods in `run_tendon_evolution.py`: your own CPPN-NEAT with speciation, age-fitness Pareto, MAP-Elites.
- Analysis tools: `morphology_scorecard.py`, `verify_corr_s1.py`, `render_champion.py`, the research notebook.
- About 100 run folders (17,000 files, 544 MB) that exist only on this machine.
- About 100 one-off analysis scripts that exist only in a Windows temp folder (see section 7).

**How far each result can be trusted today**

| Result | Evidence | Status |
|---|---|---|
| Evolved bodies are compact, nearly all muscle, single contact patch | Every run; also true of the original study's own data (section 3.1) | Solid |
| Seed-to-seed spread of about 1.7× | Several three-seed sets | Solid, and the reason every claim needs 10 or more seeds |
| Body-first two-stage protocol, +123% | 3 seeds, old springs physics, different amplitudes, no matched co-evolution baseline | Real within the old physics. On beam physics the one two-stage run (2.27) is below the plain fixed-gait run (2.61) |
| Per-voxel phase, +13.9% | 3 seeds, old springs physics | Real within the old physics |
| CPPN-NEAT gives the better champion, MAP-Elites the better population | 1 seed against 2 | One seed. The pattern itself is already published (section 4) |
| Record 2.72 on Cheney's score | 1 seed, passes the verification battery | Genuine for the configuration it ran in. That configuration differs from the 2013 one in three settings (section 3.4) |
| "62% of Cheney's median" | 2.72 against 4.39 | Not a valid comparison (sections 3.2, 3.3) |
| Stiff-bias, forward fitness, flex engine, mass-spring engine, GPU port | Documented | Dead ends, correctly recorded as such |

---

## 3. What the checks on 18 November found

All read-only. Scripts and raw outputs are in [diagnostics_2026-11-18/](diagnostics_2026-11-18/). The engine was driven exactly as in `cheney_score_s1`, and the script reproduces your record champion to four decimals (2.7170) before measuring anything else.

### 3.1 The original study did not evolve multi-legged robots either

Shape statistics of Cheney's deposited generation-1000 robots, measured with your own scorecard (run champions, 35 per condition):

| | No-cost condition | Actuated-cost condition |
|---|---|---|
| Recorded score, median (range) | 4.39 (3.39–5.95) | 3.41 (2.59–4.49) |
| Voxels, median | 652 | 377 |
| Footprint (cells in the bottom layer), median | 26 | 4 |
| Fill of bounding box, median | 0.65 | 0.44 |
| Muscle fraction, median | 1.00 | 0.61 |
| Champions with two or more separate feet | 1 of 35 | 0 of 35 |

The cost condition gives thinner bodies perched on a small patch, which look more like creatures, but not bodies with several feet. Your pre-registered limb test (two feet in the top 10, or champion footprint of 50 or less) is passed by 94% of his no-cost champions on the footprint clause alone.

### 3.2 At equal generations your one seed is inside his range

Median run-champion score across his 35 no-cost runs, from the deposited learning curves:

| Generation | 1 | 10 | 30 | 100 | 200 | 300 | 600 | 1000 |
|---|---|---|---|---|---|---|---|---|
| His median | 0.85 | 1.50 | 2.15 | 3.26 | 3.61 | 3.70 | 4.26 | 4.39 |
| His minimum | 0.51 | 0.93 | 1.27 | 1.83 | 1.97 | 2.27 | 3.35 | 3.39 |
| `cheney_score_s1` (1 seed) | 1.34 | 1.76 | 2.05 | 2.27 | 2.52 | 2.72 | – | – |

Your run tracks his median to about generation 30, then levels off while his keep climbing. At generation 300 it sits at 73% of his median and above his minimum. "62%" compared your 300 generations with his 1000. His runs gained another 19% between generations 300 and 1000.

### 3.3 His robots in your engine: the transplant test

His 35 no-cost run champions, muscles on, 10 cycles, his score:

| Engine configuration | Median score | Ratio to his recorded score (95% interval) | Rank agreement |
|---|---|---|---|
| A. As you ran it: ±20%, volumetric law on, damping 0.01 | 1.43 | 0.34 (0.28–0.47) | +0.55 |
| B. Amplitude ±14% only | 1.94 | 0.45 (0.41–0.49) | +0.78 |
| C. ±14%, volumetric law off | 1.98 | 0.43 (0.40–0.47) | +0.73 |
| D. ±14%, volumetric law off, damping 0.001 | **3.23** | **0.68 (0.55–0.83)** | +0.40 |
| E. ±14%, damping 0.001, volumetric law on | 2.83 | 0.53 (0.44–0.67) | +0.09 |
| F. ±20%, volumetric law off, damping 0.001 | 1.73 | 0.38 (0.30–0.56) | +0.09 |

His 35 actuated-cost champions under configuration D: recorded median 3.41, yours 2.58, ratio 0.77.

Reading:

- As configured for your runs, the engine gives his own robots a third of their recorded distance. With the three settings below set to the 2013 values, it gives them about two thirds to three quarters. Eleven of the 35 no-cost champions land within 20% of their recorded score, and five exceed it.
- Global damping is the largest single factor (C to D), then amplitude.
- A gap of roughly a quarter to a third remains, and with low damping the per-robot agreement gets noisier (six bodies stay under 30%, one reaches 141%). Some loss is normal when a body tuned in one simulator is moved to another; how much of the remainder is a real model difference is the first question of the plan (experiment E1).
- In configuration A your evolved champion (2.72) beats 28 of his 35 transplanted champions, so your search does real work. But his best transplanted body reaches 3.62 in that same configuration, so better bodies existed there and your search did not find them.

### 3.4 Three settings that differ from the 2013 simulation

All three are in the full 2013 source archive you already have (`research_reference/repositories/softbots2013Code.tgz`) and in every one of 300 deposited robot files I sampled.

| Setting | 2013 paper text | 2013 files and source | evosoro defaults | Your `cheney_score_s1` |
|---|---|---|---|---|
| Actuation amplitude | "20% volumetric" | ±14% linear: `TempBase + (TempAmp − TempBase)·sin(…)` with TempAmp 39, TempBase 25, CTE 0.01 (`VX_Environment.cpp` line 300) | TempAmp 39 | ±20% linear |
| Poisson coupling | not stated | Off: `PoissonKickBackEnabled 0`, and the code inside that switch is commented out (`VXS_Bond.cpp` line 360) | – | Volumetric law on |
| Global damping | not stated | `SlowDampingZ 0.001` | 0.01 | 0.01 |
| Frequency | not stated | 40 Hz | 4 Hz | 40 Hz, matches |
| Gravity | not stated | 27.468 (2.8 g) | 1 g | Rescaled 2.8 g, matches |
| Stiffness, hard to soft | "more stiff" | 5× | 100× | 5×, matches |
| Time-step fraction | not stated | 0.9 | 0.7 | 0.7 (numerical only) |

The earlier notes said the temperature code was "not in the files we have". It is: only one file had been extracted from the archive. The same archive settles two other open points: the start position is recorded (`main.cpp` line 52), so his scores are true displacements, and the amplitude matches the "14% linear" stated in the 2015 and 2018 papers.

Your engine was modelled on the newer Voxelyze library and on evosoro's defaults. The 2013 experiment ran on the older Voxelyze code with its own settings.

### 3.5 Your CPPN-NEAT is not his CPPN-NEAT

| | 2013 settings file (`softbotTest.dat`) | Your code |
|---|---|---|
| Add node / add link | 3% / 5% | 8% / 15% |
| Remove or toggle a link | 3% remove | 5% toggle |
| Weight mutation | 80% of offspring, each link with probability 0.5, power 1.5 | each link with probability 0.3, step 0.5 |
| Activation-function mutation | no such setting in the file | 8% |
| Tournament size | 2 | 3 |
| Elitism | copy the generation champion | 2 elites |
| Species | target of 5, adaptive threshold | fixed threshold 1.5 |
| Generations / runs | 1000 / 35 | 300 / 1 |

The comparison is with the `--no-age-pareto` path your Cheney runs used. The 2013 activation-function set and its initial networks still need to be read from the HyperNEAT source in the same archive.

### 3.6 So: is the simulator wrong, or the algorithm?

- **The simulator is not wrong, it was set differently.** It passes its mechanical tests, and with three documented settings changed it reproduces most of his robots' recorded performance. What it has never done is evolve under those settings.
- **The algorithm is a plausible second factor.** Its settings differ from his, its curve flattens early, and one seed cannot say more.
- **Do not start from scratch.** Nothing maintained could replace the engine (section 4), and the evidence says it is close. The original 2013 simulator ships with a Makefile and this machine has a WSL Ubuntu installation, so it can probably be built as a reference to close the remaining gap.

### 3.7 21 November: the original 2013 simulator, rebuilt as the reference

Details and scripts in [reference_2013/](reference_2013/README.md).

- **It builds and it reproduces its own numbers.** Compiled unmodified from the authors' archive in WSL (g++ 15). Over the 2,037 deposited robots with a recorded score, the median ratio of reproduced to recorded score is 0.998; 81% are within 5% and 95% within 20%. The no-cost run champions give a median of 4.32 against the recorded 4.39. So the recorded scores are real and reproducible, and the simulator can serve as the measuring stick.
- **Same code, different compiler, is not bit-identical.** About one robot in five differs by more than 5%. That is the floor for any reproduction of these numbers.
- **It is fast.** About 3 s per robot on one core, against 40 to 50 s in the MuJoCo engine.
- **Your robots in it.** The `cheney_score_s1` champion scores 1.86 there (2.72 in your engine as configured), the best of its final population 2.10, and the two simulators rank that population alike (+0.89). Measured in one simulator, your best body is at about 45% of a typical 2013 champion. Those bodies were evolved under the other settings, so this says nothing yet about the search.
- **Engine options are in.** `--damping-global` and `--preset cheney2013` exist with tests, defaults unchanged, and every run now writes a `manifest.json`.

**Decided on 21 November (decision 10): the re-evolution experiments run in the 2013 simulator itself**, driven by your search code. The physics is then the 2013 physics by construction. The MuJoCo engine stays in the paper as the independent second implementation: transplants in both directions, the settings audit, the sensitivity study, and a smaller matched set of runs. The design is in [PROTOCOL.md](PROTOCOL.md), frozen on 21 November.

### 3.8 21 November: evolving in the 2013 simulator, and a first pilot

- **Built.** `--simulator voxelyze2013` evaluates every body in the original simulator, with the 2013 settings template (identical in 300 deposited files of both conditions). It returns exactly the scores of the reference replay. `--penalty actuated` (also `voxels`, `connections`) is the 2013 cost condition and works with either simulator. 19 new tests.
- **Cost.** 5 to 7 seconds per generation at population 30, so about two hours for a 1000-generation run.
- **Pilot, one seed, 100 generations, your CPPN-NEAT unchanged** (`pilot_vx2013_s1`; not part of any arm):

| Generation | This run | Deposited median (25th–75th percentile) | Deposited runs below this one |
|---|---|---|---|
| 1 | 0.91 | 0.85 (0.81–0.99) | 22 of 35 |
| 10 | 1.80 | 1.50 (1.32–1.81) | 25 of 35 |
| 30 | 1.95 | 2.15 (1.90–2.50) | 10 of 35 |
| 100 | 2.05 | 3.26 (2.75–3.59) | 2 of 35 |

- **Reading.** With the physics now identical to 2013, the run starts ahead of most deposited runs and then stalls, the same pattern as in your own engine. The champion's network did not grow after generation 10. One seed proves nothing, but it points at the search, which is what arm B of the protocol tests. *(26 November: arm A, 35 seeds of this search in the 2013 simulator, does not bear this out at generation 1000. The search starts more slowly and has caught up within the uncertainty by the end; this pilot is its seed 1, one of the slowest. Section 3.21.)*
- **Shape.** The pilot champion is squat: 482 voxels, the whole 100-cell footprint on the floor, 98% muscle. Deposited champions perch on a median of 26 cells. So that difference survives the change of simulator.
- **Transfer.** The pilot champion scores 2.73 in the MuJoCo engine with the 2013 preset, a third more than in the simulator it evolved in. The deposited champions lose a third going the same way. The two simulators differ in both directions depending on the body.

### 3.9 21 November: the original experiment itself, re-run

Details in [reference_2013/README.md](reference_2013/README.md), section 5.

- **The original search program builds and runs.** HyperNEAT v2.5 with the Softbots experiment, from the same archive, built in WSL with CMake 4.2 and Boost 1.90 (installed for this). It needed compiler switches, a force-included compatibility header and a six-line patch to `main.cpp`; none changes what the program computes. The decisive switch restores the 2013 text-string layout, without which the program corrupts its own settings table.
- **It behaves like the deposited runs so far.** Twelve seeds for ten generations: the champion score has a median of 1.71 at generation 10 against 1.50 for the 35 deposited runs (ratio 1.14, bootstrapped 95% interval 0.86 to 1.50, p = 0.36). Generations 1, 2 and 5 agree as closely.
- **It is slow per run, cheap in total.** Each run uses one core: about 90 seconds per generation at the start, so 1000 generations is more than a day per run, but all 35 runs of an arm can run side by side.
- **What this gives the paper.** A ladder of three steps, each with its own arm in [PROTOCOL.md](PROTOCOL.md): the original code re-run with new seeds (does the experiment repeat?), an independent search in the original simulator (arm A), and an independent search in an independent simulator (arm D). The single-seed pilot of section 3.8 suggests the second step is where the gap opens.

### 3.10 21 November: protocol frozen, launcher for the re-execution arms

- **The protocol is frozen** (your approval of 21 November) and the campaign code is tagged `campaign-v1`. How its open points were settled is in its section 8. One rule changed in wording against the draft you approved: a run of the original program that dies is started again from the beginning with the same seed, instead of "resumed from its checkpoint". No seed is ever replaced. You confirmed this wording on 22 November.
- **That is safe because the original program is deterministic.** Seeds 1 to 3 over ten generations gave the pilot's scores to the last digit, whether three or twelve runs shared the machine, and so did seeds that were cut short and started again.
- **The build recipe is confirmed.** Both programs rebuilt from the scripts in the repository are byte for byte the ones the pilot ran with.
- **`paper/reference_2013/start_arm.py`** starts an arm in a console window of its own, keeps Windows awake, refuses a second launcher, reports progress without showing scores, and checks at the end that every seed has its 1000 generations. Details in [reference_2013/README.md](reference_2013/README.md), section 6.
- **A hazard removed.** The simulator build script cleared the whole reference folder, which also holds the run folders. It no longer does, and neither build script runs while runs are in progress.
- **Arm R is running.** Started on 21 November at 23:27: seeds 1 to 35, 1000 generations each, no cost, all 35 side by side, in a console window titled "Soft robot campaign, arm R". That window must stay open, and Windows must not be restarted or logged off, until it reports the runs complete. `python paper\reference_2013\start_arm.py --arm R --status` shows where every run is. If the runs are interrupted, `--restart-incomplete` starts the unfinished seeds again from the beginning. The first generations are the slow ones: about 215 seconds each with every core busy, which pointed to 57 hours. That forecast was too long. After 15 hours (22 November, 14:40) the median run was at generation 684, an average of 80 seconds per generation, the fastest at 990 and the slowest at 527. **Arm R finished on 22 November at 21:40**: all 35 runs complete with 1000 generations, the slowest after 22.2 hours (median 20.1, fastest 15.4). Runs speed up as others finish, so even the 15-hour forecast of 30 hours was too long.

### 3.11 22 November: the analysis, written before the results

Details in [analysis/README.md](analysis/README.md) and in [PROTOCOL.md](PROTOCOL.md), section 9.

- **The analysis of an arm exists and is tested** (`paper/analysis/analyse_arm.py`, 24 tests). It was developed on the pilot and on the 2013 data only, and committed before its first run on an arm. Arm R had finished at 21:40 that evening; its results were not consulted while the analysis was written. It refuses to compute anything for an arm that is not complete.
- **It gives the right answers where the answers are known.** The deposited runs dressed up as an arm and set against themselves "reproduce" (ratio 1.00); the deposited cost runs set against the no-cost runs "differ" (ratio 0.78); the deposited champions measure as they did on 18 November; the pilot gives its numbers of 21 November.
- **Eight details the protocol had left open are now fixed** (its section 9.1). Two are real choices: the yes/no measure "two or more feet" is tested with Fisher's exact test, and the body measures are Holm-corrected within each arm.
- **What the 0.90 to 1.10 criterion can show**, computed from the 2013 runs alone (its section 9.2). A perfect reproduction would meet it in 66% of cases for arms R and A, in 17% for arm D with its 10 runs, and never for arm Rc: in the cost condition the median of 35 runs is too unsteady for a 10% window. The criterion is unchanged; a result that misses it while its interval contains 1 is reported as "not distinguishable", not as a failed reproduction.
- **Not yet written**: the reader for the arms run with your own search (A, D, E), the transfer scores, the figures.

### 3.12 22 November: arm R, the first result of the campaign

Details in [outcomes/README.md](outcomes/README.md). Analysed once, after your go-ahead, with the analysis as committed.

- **The original experiment repeats.** 35 re-runs of the authors' code with new seeds reach a median champion score of 4.41 at generation 1000, against 4.39 for the 35 deposited runs. Ratio of medians 1.00, 95% interval 0.94 to 1.05, inside the 0.90 to 1.10 fixed in advance. A12 0.48, p = 0.75. Generations 100 and 300 agree as well (ratios 1.02 and 1.06).
- **The bodies repeat too.** Voxels 675 against 652, footprint 24 against 26, fill 0.68 against 0.65, muscle fraction 0.99 against 1.00. Three of 35 champions have two or more feet, against one of 35 in 2013: still no limbs.
- **The result holds up to checking.** Recomputed by hand from the raw files it is the same; the arm's first ten generations are identical to the pilot's; every champion re-simulated in the 2013 simulator reproduces its recorded score.
- **What it gives the paper.** The first step of the ladder is solid: a different compiler, different libraries and thirteen years do not move the outcome of the 2013 experiment. That is also the floor against which the other arms are read. The one-seed pilot of your own search in the same simulator stood at 2.05 at generation 100, where arm R's median is 3.31; arm A will say whether that gap is real.
- **Next.** Arm Rc (the cost condition, about 22 hours), arm A (needs a queue for the runs and a reader in the analysis), and the transfer scores of arm R's champions.

### 3.13 22 November: arm Rc started

- **The cost switch was tried first.** The rebuilt program had never been run with its `-P 2` switch. Two seeds for ten generations (`dryRc_P2_s3`, `s5`): on all 50 simulated robots of the recorded generation the adjusted fitness is the original one times one minus actuated voxels over 1000, to seven digits, which is the rule read from the 2013 source and checked on the deposited cost robots. Under this switch the count in a robot's file name is its actuated voxels, not all its voxels.
- **Arm Rc is running.** Started on 22 November at 23:19 with your go-ahead: seeds 1 to 35, 1000 generations, actuated-voxel cost, all 35 side by side, in a window titled "Soft robot campaign, arm Rc". It runs on the same programs, libraries and settings file as arm R (identical checksums). `python paper\reference_2013\start_arm.py --arm Rc --status` shows where every run is. Arm R took 22 hours.
- **What to expect of its criterion.** As section 9.2 of the protocol records, a perfect reproduction cannot meet the 0.90 to 1.10 window in this condition. The arm will read as "not distinguishable" or as "differs".

### 3.14 23 November: arm Rc cut short, a safer launcher, arm Rc started again

- **What happened.** At 08:46 both campaign windows were closed: the finished one of arm R and the running one of arm Rc. The launcher ran inside its window, so arm Rc stopped. Three runs had finished; 32 were at generations 396 to 935 of 1000. Windows had not restarted and WSL had not shut down. Console windows are hosted by Windows Terminal on this machine, where one click can close several, and I had written that the old arm R window could be closed.
- **What changed (your choice of 23 November).** The launcher is now a process without a window; the window that opens only shows progress and can be closed. `--watch` opens the view again and `--stop` stops the runs. Runs that are alive without a launcher are adopted when the arm is started again. All of this was tried before use (reference README, section 6).
- **Arm Rc is running again.** The 32 unfinished seeds were started from the beginning at 09:00, as the protocol prescribes; the three finished runs are kept. The paper has to report that 32 of this arm's seeds were started twice. The unfinished attempts are kept in `runs/_interrupted/` on the WSL side.
- **Cost.** Nine hours of machine time.

### 3.15 23 November: arm A prepared, and a flaw in the search's checkpoints corrected

- **Arm A can be started with one command**, `python paper\reference_2013\start_arm.py --arm A`. It uses the same launcher without a window and runs all 35 searches side by side, each simulating one robot at a time, the way arm R ran. A run that ends without finishing is continued from its checkpoint. The launcher owns its runs: if it ends, they end, and starting the arm again continues them.
- **Your search repeats exactly for a seed.** Seed 1 gives the fitness of all 30 robots of the pilot of 21 November in each generation compared, although the number of workers, the generation limit and the load on the machine were different.
- **A flaw found and corrected (your choice of 23 November).** A run that was stopped and continued did not compute what it would have computed without the stop. The search loop and the genomes share one random generator, and the checkpoint split it in two. With arm A's selection scheme this went wrong only when a run was stopped within its first two generations. Two statements in `run_tendon_evolution.py` correct it. A test that failed before now passes, and real runs stopped and continued are identical to uninterrupted ones. Uninterrupted runs compute what they did before. The code of arms A, D and E is tagged `campaign-v2`; the protocol records this in section 9.3.
- **The analysis reads arm A's runs.** `analyse_arm.py --arm A` gives the report arm R got, also sets arm A against arm R (the fifth primary comparison) and repeats arm R's result as the floor. It was tested on made-up runs; no run of arm A exists yet.
- **Chained to arm Rc (your go-ahead of 23 November).** Arm A's launcher was started with `--after Rc`: it waits for arm Rc to finish and starts arm A only if arm Rc is complete. Seed 1 of arm A will repeat the pilot, so its first 100 generations are already known (2.05 at generation 100).

### 3.16 24 November: arm Rc, the second result; arm A running

Details in [outcomes/README.md](outcomes/README.md).

- **The cost condition repeats as well.** 35 re-runs of the original code with the actuated-voxel cost reach a median champion score of 3.57 at generation 1000, against 3.41 for the 35 deposited cost runs: ratio 1.05, 95% interval 0.88 to 1.12, A12 0.54, p = 0.55. By the fixed reading this is "not distinguishable"; the 10% window could not have been met in this condition, as recorded beforehand.
- **The bodies repeat.** 363 voxels against 362, footprint 7 against 5, fill 0.46 against 0.44, muscle fraction 0.62 against 0.60. The cost halves the bodies and removes muscle, as in 2013.
- **The restart rule held on real data.** Each of the 32 runs that had to be started again is identical to its interrupted attempt in every generation that attempt had reached (395 to 934 generations). All 35 champions re-simulated reproduce their scores.
- **The hand-over worked.** Arm Rc was complete on 23 November at 23:20; arm A started by itself at 23:21 and is running (median generation 246 of 1000 on 24 November at 10:07).
- **What the two re-execution arms give the paper.** Both conditions of the 2013 experiment repeat on a 2026 system, in scores and in bodies. That is the first step of the ladder; arm A is the second.
- **Videos as a check (your request of 24 November).** The median and best champion of each arm, next to the 2013 champions chosen by the same rule, simulated again in a copy of the 2013 simulator that records every voxel's motion: [outcomes/README.md](outcomes/README.md). The frames are the scored simulations (same distances), the robots advance by a steady 0.3 to 0.7 body lengths per cycle, stay intact and stay on the ground. Two things to carry into the paper: contact voxels sink 0.6 to 0.8 of a voxel into the 2013 simulator's floor, and single deposited robots do not all score today what they scored in 2013 (the best no-cost champion: 5.95 then, 4.90 now), which is why whole runs are compared and not single robots. From now on every arm or run that succeeds gets its video.
- **Standing instructions of 24 November.** Push every significant change and every tag to GitHub without asking (both tags are there now). Windows updates are paused until 24 December.

### 3.17 24 November: the champions of arms R and Rc in the MuJoCo engine; the literature checked again

Details in [outcomes/README.md](outcomes/README.md), section "Transfer". This is the protocol's secondary outcome "transfer": every champion scored in the simulator it was not evolved in.

- **Fixed first, then computed.** How the outcome is computed went into the protocol (section 9.4) before any champion of an arm was scored. The scoring reads its settings from the preset in the search's own code, and a test runs the search under the preset and checks that every robot gets the same score here.
- **The champions lose a large part of their score.** Median share kept: 0.43 for arm R (95% interval 0.37 to 0.64), 0.75 for the deposited no-cost champions, 0.67 for arm Rc, 0.85 for the deposited cost champions. Single robots range from 0.07 to 1.62. Nothing blew up. The deposited champions give exactly the scores of the diagnostic of 18 November.
- **The two simulators do not agree on which champions are good.** Rank agreement +0.26 and +0.33 without the cost, none with it. Two builds of the 2013 simulator agree at +0.88 and +0.91 on the same robots.
- **Arm R's champions tend to keep less than the 2013 ones** (0.43 against 0.75, p = 0.057, not corrected); not so in the cost condition (p = 0.25). Descriptive, and not settled.
- **A single robot's score in the MuJoCo engine is fragile.** With a quarter of the time step, 5 of the 20 champions checked change by more than 10%, one by 51%. Started one to three voxels higher, 15 of 29 change by more than half a body length. Medians of 35 are steadier than that, but single transfer scores should not be quoted alone.
- **A difference between the preset and 2013 that was not known: where a body starts.** The 2013 simulator starts a body where it is in the workspace, in the air if it does not touch the bottom, and counts the drop in its three-dimensional distance. The engine sets every body on the floor. 12 of the 35 deposited cost champions and 16 of arm Rc's are off the bottom; none of the deposited no-cost champions. For the sets it changes the transfer little; for arm D it is a setting to decide (decision 11).
- **What the video shows.** Three champions picked as the middle of their sets, in both simulators side by side, on the same body voxel for voxel. In the MuJoCo engine they start in the same direction and as fast or faster, then tip over (up to 118°, against 50° to 65° in the 2013 simulator) and lose the gait. In the 2013 simulator they stand 0.8 of a voxel deep in the floor; in the engine 0.1. A reading that fits, not yet a finding: the 2013 gaits lean on that soft floor. It can be tested cheaply by scoring the same champions on softer floors in the engine (exploratory, section 7 of the protocol).
- **What it means for the paper.** The engine with the preset is not interchangeable with the 2013 simulator robot by robot. That does not decide arm D, which asks whether evolution *in* the engine reaches the 2013 scores and bodies, but it says how to read it, and it gives the audit two concrete differences in the physics: the starting height and the floor.
- **The literature, checked again with OpenAlex and Scite** (your connectors of 24 November): 477 works cite the paper or its 2014 reprint; none presents itself as a reproduction, and no citation statement speaks of reproducing it. The one title that suggested a re-run (Gu et al. 2019) is, by its abstract, a use of the tools. [LITERATURE.md](LITERATURE.md), section 2, and [note 6](literature_notes/6_citing_works_sweep.md), which also lists what a person with library access should still read.

### 3.18 25 November: the transfer loss is the floor

Your "Yes, test it". Exploratory, in [diagnostics_2026-11-25/README.md](diagnostics_2026-11-25/README.md); what would count for and against was written down and committed before any champion was scored.

- **The 2013 floor, from its source.** A spring on the centre of each contact voxel, `E × size / 2` = 5000 N/m, and a friction rule that stops a slow voxel dead and holds it until the pull exceeds its full normal force. Under a champion's weight (25 to 50 voxel weights on each contact voxel) the spring gives 0.14 to 0.29 of a voxel at rest. The engine's floor of September was modelled on the later Voxelyze library and on the weight of a single voxel; under these bodies it barely gives at all.
- **The rule emulated on the engine, without changing its code.** Checked first on bodies that are not champions: a block rests and lands where the 2013 simulator puts it, and on the 12 pilot robots the typical error against the 2013 score falls from 51% to 18% and the rank agreement rises from +0.22 to +0.76.
- **Result on the 140 champions: under the 2013 floor rule they keep their score.** Median share kept, on the preset's floor and under the rule: arm R 0.43 and 1.02, deposited no-cost 0.75 and 1.16, arm Rc 0.67 and 1.07, deposited cost 0.85 and 1.15. 111 of 140 do better under the rule; p between 0.000002 and 0.004 by set. Rank agreement with the 2013 scores rises to between +0.36 and +0.61.
- **It is the rule, not softness.** MuJoCo's own contact made as soft at rest, and its default contact, do not help and mostly hurt.
- **Not a perfect match.** Under the rule the typical champion is still off by a quarter, the engine gives 2% to 16% more than the 2013 simulator in the median, and 52 of 140 champions still tip over where 5 do in the 2013 simulator. The rule depends on the time step, and the engine's step is 0.78 of the 2013 one.
- **For the paper.** This is the audit's most concrete finding so far: the 2013 champions lean on a floor that lets a body sink most of a voxel and pins its slow contact voxels. On a floor that does not, about half of the same bodies tip over, and the median champion loses a third of its score (15% to 57% by set). It also names what arm D has to decide (decision 11).
- **A lesson about this machine.** A champion-sized body reserves 1.2 GB in MuJoCo. Fourteen workers next to arm A used up the memory the system could promise; 86 evaluations failed and showed as zeros, which were caught and run again. Arm A was not harmed. The scoring scripts now size themselves to the free memory and stop instead of recording a failure. The launcher for arm D will need the same care.

### 3.19 25 November: the 2013 floor and start built into the engine

Your "Yes, build it" (decision 11). Recorded in the protocol as section 9.5.

- **Two new options, nothing else changed.** `--floor-contact rule2013` is the floor of the 2013 simulator itself, in place of MuJoCo's contact. `--start workspace` starts a body where it is in the workspace, as the 2013 simulator does. The preset `cheney2013-floor` is `cheney2013` with both. `cheney2013` itself is untouched, so everything scored with it stays repeatable, and it remains available as the hard-floor condition.
- **Held to what was tested.** The rule in the engine is the emulation of the floor test moved into the engine line for line. Tests require the same score to the last digit from both, and all 140 champions were scored again through the search's own evaluation under the new preset (result in section 9.5 of the protocol).
- **Built in a separate checkout.** Arm A's launcher refuses to continue a run if the engine code in the campaign's folder differs from its tag, so the work was done on the branch `engine/floor2013` in its own folder. It joined the campaign branch and got the tag `campaign-v3` late on 25 November, once arm A was complete (section 3.20).
- **Arm D** is to run with `--preset cheney2013-floor`. The two points that were still yours, decisions 12 and 13, you settled the same day: arm E3 is the hard floor, and the time step stays at 0.7 (section 13).

### 3.20 25 November, late evening: arm A complete; the engine change joins the campaign

- **Arm A is complete.** All 35 runs have their 1000 generations. The arm started on 23 November at 23:21 and its last run ended on 25 November at 23:36: 48 hours, against 22 for arm R. The first run was done after 22 hours, the median one after 44.5. No run was interrupted or had to be continued. **It is not analysed**: that is one command and waits for your go-ahead. *(Analysed on 26 November: section 3.21.)*
- **The engine change joined the campaign branch.** With arm A complete, the branch `engine/floor2013` was merged into `paper/reproduction` unchanged. The full test suite passed in the campaign's folder: 284 tests, none failed, none skipped. The code is tagged `campaign-v3` (commit 173a510); branch and tag are on GitHub. The separate checkout is removed.
- **The old paths compute what they computed.** Three champions scored in the campaign's folder after the merge get the scores recorded for them before it, to the last digit, under the old preset and under the new one. The test run's simulator warnings are those of the run of 23 November: the same test bodies blow up at the same instant.
- **Where a worker's memory goes, measured** ([diagnostics_2026-11-25/README.md](diagnostics_2026-11-25/README.md), "A lesson about memory"). A worker process asks the system for 1.5 GB before it has loaded a body: numpy and scipy each bring a linear-algebra library that sets aside working memory for every one of the machine's 32 logical processors. Told to use one thread, the process asks for 0.04 GB. On top of that MuJoCo reserves memory for each body, growing with the square of its size: 0.3 GB for 363 voxels, 1.0 GB for 764, 1.7 GB for a full 10×10×10 block. One evaluation uses about a thousandth of it. So a worker asks for 2.6 GB with a large champion and 3.2 GB with a full block, and needs a small fraction of either.
- **Why it matters for speed.** With no run of this project going, the machine can promise about 30 GB more, because other programs hold 51 GB. That is 7 to 9 workers as things are, on a machine with 32 logical processors. With one linear-algebra thread per worker, six evaluations of champions gave the same scores to the last digit and took no longer.
- **Why it matters for the results.** When an evaluation fails in the MuJoCo engine, for whatever reason, the search gives the body a score of 0 and goes on. That is right for a simulation that blows up, which is what the rule is for. It is wrong for a body that could not be loaded because the machine was short of memory: the run would continue with a false score, would no longer be the run its seed defines, and nothing would show it afterwards. On 25 November this happened to 86 evaluations of the scoring script, where it was caught. No arm of the campaign has run a search in the MuJoCo engine yet, so no result is affected; arm D would be the first. What to do is decision 14. *(Decided and done on 27 November: section 3.22.)*
- **Arm A lost no evaluation in that incident** (`diagnostics_2026-11-25/check_lost_evaluations.py`). In arm A an evaluation is a run of the 2013 simulator, and one that left no result would have been scored 0.001 by the 2013 rule. Arm A records every score of every generation. Of its 1,050,000 scores none is 0.001, and none is 0.0001, the 2013 score for anything unusable; that holds for the 23,850 scores written in the 85 minutes around the incident as for the rest. The count reads no other score, so it could be made before the analysis. And no run crashed: the launcher would have continued it and said so.
- **Next.** Arm A's analysis, then its video and its transfer scores under both presets (protocol, section 9.5). Then arm D: decision 14, a timing pilot under the new preset, and its launcher.

### 3.21 26 November: arm A, the third result

Analysed once, on 26 November at 17:35, after your "Yes, analyse it". The full report is in [outcomes/README.md](outcomes/README.md).

- **The result.** Your own search, with every body scored by the 2013 simulator, ends at a median champion score of 4.21 (quartiles 3.54 to 4.86). The deposited 2013 runs stand at 4.39, arm R at 4.41. Ratio of medians against the deposit 0.958, 95% interval 0.834 to 1.068: not distinguishable from the 2013 runs, and reproduction within 10% is not shown. A perfect reproduction would have met the criterion in 66% of cases. Against arm R: 0.954, interval 0.843 to 1.065, p = 0.28.
- **Slower at first, further apart at the end.** At generation 100 the arm stands at 0.80 of the deposited runs (0.71 to 0.94, p = 0.0024); by generation 300 the medians have met. At generation 1000 the middle half of the runs spans 1.32, against 0.87 in the deposit and 0.45 in arm R, and seven of the 35 runs end below the lowest deposited run.
- **The bodies** are the kind the 2013 runs produced: about 680 voxels, a footprint of 26 cells against 26, nearly all muscle, mostly one foot. One measure differs after the correction: a little passive tissue (muscle fraction 0.97 against 1.00, corrected p = 0.036).
- **Checks** (`analysis/check_arm_A.py`). The scores recomputed from the raw files with readers of their own; each run started once, from the same code and settings; the simulator is by its checksum the program arms R and Rc ran with; seed 1 is the pilot of 21 November score for score; all 35 champions reproduce their recorded score when simulated again; no evaluation was lost in the memory shortage of 25 November.
- **What it changes.** Section 3.8 read the one-seed pilot as pointing at the search. That pilot is seed 1 of this arm and is the fourth-lowest of the 35 at generation 100. With 35 seeds the search is slower at first and reaches the 2013 scores, within what 35 runs can resolve, by generation 1000. The squat body of the pilot was a body of generation 100: at generation 1000 arm A's champions stand on a median of 26 cells, as the deposited ones do.
- **Transfer, under both presets.** In the MuJoCo engine arm A's champions keep a median of 0.56 of their score on the hard floor (`--preset cheney2013`), like arm R's (0.43) and the deposited ones (0.75), and not distinguishable from either. Under the preset of arm D (`--preset cheney2013-floor`) they keep 1.10 (quartiles 0.83 to 1.23); 27 of the 35 keep more than on the hard floor, and the rank agreement between the simulators rises from +0.29 to +0.62. Arm A's champions had no part in finding the floor rule, so this repeats the finding of section 3.18 on new robots. The 140 earlier champions got the scores of 25 November again, to the last digit.
- **A caution for arm D's audit.** With a quarter of the time step, 7 of 25 checked champions change their score by more than 10% under the new preset, one by 151%. Under that preset the step is part of the floor rule, so this is not only numerical error. The protocol asks for this check on every MuJoCo champion and reports it without dropping runs; it will need this sentence next to it.
- **Videos.** `outcomes/videos/arm_A_champions.gif`: the arm's median and best champion below the 2013 ones, in the 2013 simulator. The transfer video now also shows arm A's median champion in both simulators.
- **For the paper.** Two steps of the ladder are in. Step one, arms R and Rc: the 2013 experiment repeats. Step two, arm A: an independent implementation of the search, in the same simulator, reaches scores that cannot be told from the 2013 ones at generation 1000 and bodies of the same kind, more slowly and less reliably. Before the campaign, one run of this search in the MuJoCo engine stood at 62% of the 2013 median (section 2; not a valid comparison, as noted there). In the 2013 simulator the same search reaches 96%, with an interval from 83% to 107%. That points away from the search and at the simulator. Arm D, with the 2013 floor and start in the engine, is the test.
- **Next.** Decision 14, the memory for arms D and E. Then arm D: a timing pilot under the new preset, its launcher, the reader for its runs in the analysis, and its transfer in the other direction.

### 3.22 27 November: memory for arms D and E

Decision 14, taken on 27 November ("Yes, make them"): the three changes of section 3.20, made before any run of arms D or E. The record is in the protocol, section 9.6, and in [diagnostics_2026-11-27/README.md](diagnostics_2026-11-27/README.md).

- **One linear-algebra thread per process.** The launcher starts every run that way, and the scoring script does the same for itself. A run's manifest records it.
- **An evaluation that fails is not scored.** After an error a body gets 0 only if the error is the body's own (the engine refuses it, or its arithmetic fails) and does not speak of memory; the run's output says so each time. Any other error stops the run. Nothing of the unfinished generation is recorded, and the same command continues the run from its last generation, as it would have gone.
- **MuJoCo's working memory is stated**: 8 MB plus 16 kB per voxel. A body can use 2.9 kB per voxel at most, which is every voxel on the floor at once. If the stated memory ran out all the same, MuJoCo would drop floor contacts and go on with a warning; the engine now stops instead.
- **No score changes.** All 431 evaluations behind the two transfer reports were computed again with the new code and gave the recorded score to the last digit. Short runs of the search under both presets of the campaign, with a seed that belongs to no arm, are the same runs with the old code and the new, score for score and body for body. A run stopped twice from outside while it ran, and continued each time, is the uninterrupted run.
- **A process of a run now asks the system for 0.12 GB with the largest champion loaded, against 2.57 GB.** The ten runs of arm D, each with three evaluations at a time, ask for about 4 GB together. Step (d) of the decision, a larger page file, is not needed.
- **A second read of the change** by a separate AI agent, given the diff and not the reasoning, found no defect in what is computed. Four of its six points were taken up before the checks were made; the other two are listed as known limits.
- **What a run does not do by itself**: go on when a worker process dies outright. The launcher sees a run that has recorded no generation for two hours, ends it and continues it.
- **The code is tagged `campaign-v4`.** Arms D and E run from it. The project's 318 tests pass on it.
- **Arm D is prepared, not started** (it was started that afternoon: section 3.23). The launcher knows it (`start_arm.py --arm D`: seeds 1 to 10, 300 generations, three evaluations at a time in each run, one thread per process). It looks at free memory before it starts a run, says what stopped a run, and ends and continues a run that stands still. The analysis reads it (`analyse_arm.py --arm D`: primary outcome at generation 300), written and tested on made-up runs before any run of the arm exists.
- **The launcher was tried** with ten runs side by side on seeds 101 to 110, which belong to no arm, three generations each. All ten finished; one was ended from outside on purpose and the launcher continued it; the run of seed 101 repeats the check run of that seed score for score.
- **How long arm D will take: about two days.** In the trial a generation took 8.8 minutes with all ten runs going, which makes 44 hours for 300. Later generations may cost somewhat more or less than the first three, so expect between one and a half and two and a half days.
- **Next.** Your go-ahead for arm D. While it runs: the audit of its champions and their transfer into the 2013 simulator, and arms E1 to E3 in the launcher.

### 3.23 27 November, afternoon: arm D started

- **Started at 15:03**, on your "Yes, start arm D": seeds 1 to 10, 300 generations each, all ten runs side by side with three evaluations at a time in each, from the code tagged `campaign-v4`.
- **One change to the launcher before the start.** When a run ends early the launcher quotes the last lines of the run's output, to show why, and those lines hold scores. They are now left out, so that reading the log shows no result of the arm. Tried on two runs with seeds 101 and 102, which belong to no arm.
- **Checked after the first generation**, at 15:14, without reading a score: all ten runs have a generation on record; each was started once, from that code, with one thread and with the settings of the protocol; no body was refused and no run stopped itself. The arm's 40 processes ask the system for 2.5 GB together.
- **Pace.** The first generation took 8.6 minutes in the median (6.5 to 9.6). At that pace the arm ends on Sunday 29 November in the morning; with the range of the estimate, between late on Saturday and Monday morning.
- **Not read until the arm is complete:** its scores. `start_arm.py --arm D --status` gives generations only.
- **Next, while it runs.** The audit of its champions and their transfer into the 2013 simulator; arms E1 to E3 in the launcher. Its analysis is one command once it is complete, and waits for your go-ahead.

### 3.24 27 November: the tools for arm D's champions, built while it runs

On your "Yes, build them". Nothing of arm D was read for this: all that was known of it was how many generations each run had on record.

- **First the protocol, then the code.** Section 9.7 fixes how the audit and the transfer of arm D's champions are computed. It was committed before either tool was built.
- **The audit** (`analysis/check_arm_D.py`). After the arm's analysis it checks the report from the raw files, reads every start of every run from the run's own record, and evaluates each champion again in the MuJoCo engine from the body its run stored: is the recorded score reproduced to the last digit, what a quarter of the time step does to it, and how deep the body stood in the floor.
- **The transfer** (`analysis/transfer_to_2013.py`). Each champion once in this campaign's build of the 2013 simulator, by the evaluation arm A's search used. The ratio is the 2013 score over the recorded MuJoCo score.
- **One choice in section 9.7 that is mine**, for you to overrule before the arm is analysed: the transfer ratios of arm D's champions are set against those of the 35 deposited no-cost champions under `--preset cheney2013-floor`, not under the hard floor. Both sets then cross between the same two simulators, in opposite directions.
- **Tried on what is on record and on runs that belong to no arm.** Arm A's 35 champions get exactly their recorded scores from the transfer tool. On the ten trial runs with seeds 101 to 110 the checks find the report's numbers, report the run that was ended on purpose as started twice, and all ten champions reproduce their recorded score to the last digit. 21 tests.
- **A caution the rehearsal gave.** Three of the ten trial champions, robots of a third generation, lost 45% to 68% of their score at a quarter of the time step; the other seven changed by under 2%. That is not arm D. But it is the second time this preset shows that a single score can rest on the time step (section 3.21), and the audit will show how arm D's champions stand.
- **Still missing.** A video of arm D's champions in the engine they were evolved in; arms E1 to E3 in the launcher, the analysis and the audit.

---

## 4. What the literature says

Details and links are in [LITERATURE.md](LITERATURE.md).

1. **Nobody has published an independent reproduction of Cheney et al. 2013, or a re-analysis of its deposited data.** Other groups reused the authors' simulator (Methenitis 2015, Mouret & Clune 2015, Gravina 2017–2019) but none reports a side-by-side reproduction.
2. **Compact, filled, muscle-rich bodies are the known default** under distance-only fitness on flat ground (Cheney 2013, 2016, 2018; Corucci 2016; Li, Matthews & Kriegman 2023; Miras 2018 for rigid modules). A legged body can simply be the slower solution (Kriegman, Cheney & Bongard 2018).
3. **Limbs appear under specific conditions**: material or energy costs, gravity (Methenitis 2015 report two- and four-legged walkers in this very system, hopping at lunar gravity), stiffness relative to weight (Corucci 2018), environments other than open flat ground, per-voxel phase control with protection of new bodies (Cheney 2018), gradient-based design (Matthews 2023). These claims rest on pictures of selected individuals; no study reports what fraction of runs ends limbed.
4. **"MAP-Elites gives the population, plain evolution the champion" is already published.** In this very system, trajectory-based novelty search beat plain CPPN-NEAT on the champion with 90 runs (Gravina 2018), and biased parent selection in MAP-Elites has a two-page precedent (Gravina 2019).
5. **Body-first has only been tested in 2D** (Mertan & Cheney 2024). In 3D there is no multi-seed test against matched co-evolution; the one single-run comparison found joint optimisation better (Candiello 2026). Mertan & Cheney also saw the second stage fail to beat the first.
6. **Scores are protocol-specific.** Gravina 2018 report 9.29 body lengths for plain objective search at 10³, with 0.4 s of simulation instead of 0.25 s.
7. **Contact artefacts in this system are documented only as an anecdote** (Lehman et al. 2020 describe these robots exploiting floor penetration). There is no controlled sensitivity study.
8. **The statistical floor is 10 runs per condition**; 20 to 30 is common, the decisive papers use 90 to 100. Mann-Whitney U with a correction for several comparisons, bootstrapped 95% intervals.
9. **No maintained 3D voxel simulator exists to switch to** (Voxelyze 2016, evosoro 2018 on Python 2, voxcraft-sim 2021, Evolution Gym is 2D). No published MuJoCo engine of this kind was found.

---

## 5. Recommendation: what to contribute

### Paper 1, for GECCO 2027: an independent reproduction and audit of the 2013 benchmark

Working title: *Unshackling Evolution, revisited: an independent reproduction and audit of evolved soft robots*.

Claims the paper would make, each already supported or testable within the budget:

- **C1. What the original data show.** A numerical census of the deposited robots: single-footed, filled, all-muscle bodies in the no-cost condition; thinner perched bodies under cost; learning curves that are still rising at generation 300.
- **C2. An independent engine, and how close it gets.** Mechanical validation, then the transplant test: deposited champions keep a third of their score under the settings a careful reader would infer from the paper and later code, and two thirds to three quarters under the settings in the deposited files. A provenance table of every setting.
- **C3. Re-evolution.** With physics and search set as in 2013, do scores and body types fall inside the original 35-run distribution at matched generations? This is the main new experiment.
- **C4. What changes the outcome.** Damping, amplitude, floor stiffness and the search settings, each varied on its own, with the effect on score and on body shape. Includes the floor-contact episode that produced a spurious record and a spurious morphology.

Why this one:

- It is the gap the literature most clearly leaves open, and GECCO has a track that asks for it (BBSR: "Reproducibility studies that rigorously replicate published experiments"). The one replication paper accepted there so far paired the replication with a new finding; C2 and C4 are that finding.
- Most of the material exists. The remaining runs fit one workstation.
- Every outcome is reportable. If re-evolution matches the original, that is a successful replication with a provenance lesson. If it does not, the gap is quantified and localised.
- It answers your own question, and it gives paper 2 a benchmark that reviewers can trust.

### Paper 2, for ALIFE 2027 or a journal: body-first in 3D, or when limbs appear

On the audited benchmark, with 20 to 30 paired seeds per arm:

- **Body-first against matched co-evolution, protection of new bodies, and plain fixed gait.** The 3D test that is missing from the literature. Every beam-physics result so far ran on the mis-set configuration, so these runs have to be redone anyway.
- **Or a quantitative map of when limbs appear**: fraction of runs ending limbed, by a stated measure, across two or three of the factors in section 4, point 3.

### About limbs

The honest position: on flat ground with distance as the only objective, limbs are not what the objective asks for, in the original study or in yours. A paper that shows this with numbers, and shows under which measured conditions bodies become limb-like, is better supported than one that promises limbed robots. The plan still gets you limb-like robots: experiment E4 reproduces the cost condition where the original's creature-like bodies came from, and paper 2 can vary gravity as Methenitis did.

---

## 6. Study design for paper 1

### Research questions

- RQ1. What do the deposited 2013 robots look like by objective measures, and how did the runs progress?
- RQ2. How closely does an independent engine reproduce the recorded performance of the deposited robots, and which settings matter?
- RQ3. Under the 2013 physics and search settings, does independent re-evolution reproduce the original distribution of scores and body types at matched generations?
- RQ4. How sensitive are evolved score and body shape to damping, amplitude, floor contact and search settings?

### Experiments

**Superseded on 21 November by [PROTOCOL.md](PROTOCOL.md).** Evolution now runs in the original 2013 simulator (arms R, Rc and A, 35 seeds of 1000 generations each), with the MuJoCo engine as the independent second implementation (arms D and E). The table below is the earlier design, kept for the record; E0 and E1 are done (sections 3.3 and 3.7).

| | What | Runs | Purpose |
|---|---|---|---|
| E0 | Transplant test (done, section 3.3) | – | RQ2 |
| E1 | Close the residual. Build the 2013 simulator in WSL as a reference; replay the deposited robots in it; compare simple scenes (one actuated voxel, cantilever, drop on floor, friction threshold) against your engine; switch remaining settings one at a time on the 70 deposited champions. Time-boxed to one week | minutes each | RQ2 |
| E2 | Re-evolution, 2013 physics, your current CPPN-NEAT | 10 seeds × 300 generations | RQ3 |
| E3 | Re-evolution, 2013 physics, CPPN-NEAT set to the 2013 settings file | 10 seeds × 300 generations | RQ3, RQ4 |
| E4 | Actuated-cost condition as in the 2013 source, with whichever search arm did better | 10 seeds × 300 generations | RQ3, and limb-like bodies |
| E5 | Sensitivity: damping 0.01, amplitude ±20% with the volumetric law (the old configuration), soft floor | 3 seeds each, 9 runs | RQ4 |
| E6 | Three seeds of the better arm continued to 1000 generations | about 7 run-equivalents | RQ3: does late improvement appear, as in the original? |
| E7 | Audit of every run champion: reproduce, quarter time step, 60-cycle path, floor penetration, bond strain | minutes each | RQ4 |

Comparison with the original uses his 35 runs at the same generation, from the deposited curves. No need to match his 1000 generations in every run.

### Compute budget

One 300-generation run should take 6 to 9 hours under the 2013 settings (the volumetric law off allows a larger time step). About 46 run-equivalents, roughly 370 hours, about 15 days of continuous running. The window from 30 November to 3 January is 35 days, which leaves room to raise the two key arms to 20 seeds (about 7 more days).

### Statistics, fixed before the runs start

- Seeds are the unit. Ten per arm as the floor, the same seeds across arms, every completed and failed seed reported.
- Primary outcomes: run-champion score on Cheney's score at generations 100 and 300; and for the run champion: voxels, footprint, fill, muscle fraction, number of feet (static and during the gait).
- Tests: two-sided Mann-Whitney U against the original 35 runs and between arms, Holm correction, bootstrapped 95% intervals for medians, and an effect size (Vargha-Delaney A12), which almost nobody in this literature reports.
- Write these into `paper/PROTOCOL.md` and commit it before the first run, so the git date shows the analysis was fixed in advance.

---

## 7. Engineering before the runs (week 0)

Needs your approval where it touches physics (your standing rule).

1. **Physics options**: a global-damping setting (today a module constant, `ZETA_GLOBAL`), and a named preset for the 2013 configuration (±14%, volumetric law off, damping 0.001). Defaults unchanged, resume guard extended, tests added.
2. **Cost penalty** exactly as in the 2013 source (multiply the score by one minus actuated voxels over the maximum).
3. **Search settings switch**: one flag that sets the CPPN-NEAT parameters to the 2013 file's values.
4. **Run manifest**: every run saves its command, git commit, package versions, seed and full physics settings; replays and renders read it.
5. **Run queue**: a script that runs a list of seeds back to back, keeps the machine awake, and runs the champion audit after each run.
6. **Rescue the analysis scripts.** About 100 scripts from earlier sessions, including the ones behind the verified records and the loader for Cheney's files, sit only in `%TEMP%\claude\c--SoftRobotEvolution\5cc73d86-…\scratchpad`. A cleanup or reboot can delete them. Copy them into the repository and make the keepers read the deposited archives directly.
7. **Back up the results.** 544 MB of run outputs exist only on this disk.
8. **Environment**: a pinned environment file; add scipy, pandas and pytest; small fixture files so the 11 skipped tests run for everyone.
9. **Repository hygiene** (it is public): add a licence; rewrite the README, which still describes the early spring-mass state; remove the five third-party paper PDFs in `Documentation/` (copyright); move the 150 loose root scripts into folders.

---

## 8. Timeline

| When | Work | Gate |
|---|---|---|
| 19–29 Nov | Your decisions (section 13). Rescue scripts, backup. Items 1 to 5 of section 7 with tests. E1. Write and commit `PROTOCOL.md` | **G1, 29 Nov**: 2013 configuration frozen and tagged |
| 30 Nov–13 Dec | E2 and E3 running (about 7 days of compute). Meanwhile: data census figures for RQ1, the provenance table, Methods draft | **G2, 13 Dec**: first look. Does re-evolution fall inside the original distribution? Choose the framing and the track |
| 14–27 Dec | E4, E5, E6. Figures pipeline. Related work written from LITERATURE.md | |
| 28 Dec–3 Jan | Buffer over the holidays. Top-up seeds. E7 on all champions | |
| 4–10 Jan | Full draft | |
| 11–17 Jan | Review pass with fresh eyes, fixes. Abstract submitted by 16 Jan. Anonymised code package, supplementary video | Abstract deadline 18 Jan |
| 18–24 Jan | Polish. Submit by 23 Jan | Paper deadline 25 Jan |
| After | arXiv preprint. If rejected on 19 March, revise with the reviews and send to ALIFE | |

**Fallback rule.** If G1 slips past 6 December, or the first arm is not finished by 20 December, switch the target: either a 4-page GECCO poster paper on C1 and C2 (same deadline), or the full paper for ALIFE.

---

## 9. Paper outline (8 pages plus references)

1. Introduction: a landmark result, never independently reproduced; what the reader will learn.
2. Background: the 2013 system; later work in the same simulator; what is known about body types.
3. The original data, re-analysed (RQ1). Figure: body census, both conditions. Figure: learning curves with quantiles.
4. An independent engine (RQ2). Table: validation tests. Table: provenance of every setting. Figure: transplant test, recorded against reproduced score per robot, by configuration.
5. Re-evolution (RQ3). Figure: score distributions at generations 100 and 300 against the original. Figure: body census of new champions against the original. Champion pictures.
6. Sensitivity (RQ4). Figure: effect of each setting on score and on shape. The floor episode as a worked example.
7. Discussion: what reproduced, what did not, a checklist for future studies, limits (one engine, seeds, flat ground only).
8. Reproducibility statement: code, data, seeds, environment.

---

## 10. Tools and accounts

| Need | Why | Who |
|---|---|---|
| GitHub CLI (`gh`) or the official GitHub plugin | Releases, issues, repository settings, Actions. Plain git push already works | You install and sign in |
| scipy, pandas, pytest in the project environment | Statistics, tables, tests | Approved 21 November |
| A compiler in WSL Ubuntu | Build the 2013 simulator as the reference (E1) | Nothing to install: g++ 15.2 and make are already in the Ubuntu 26.04 distribution. Build approved 21 November |
| LaTeX: Overleaf with the ACM template, or MiKTeX locally | Write and build the paper. Local lets me compile and check the PDF | Your choice |
| ffmpeg | Supplementary video | I can install on your word |
| alphaXiv connector (optional) | Full-text search over arXiv from inside Claude | You connect it if you want it |
| ORCID iD | Required by ACM | You |
| arXiv account and an endorser | See section 11 | You, with my help finding endorsers |
| Zenodo account | DOI for code and data at camera-ready | You, later |

Google Scholar blocks automated access from this network with a "not a robot" check, which I cannot complete. The survey used Semantic Scholar, OpenAlex, arXiv and publisher pages. If you want Scholar itself, complete the check in the browser pane and I will carry on from there.

---

## 11. Submission logistics

- **Affiliation.** Publisher guidance is consistent: the affiliation is where the research was conducted, supported or approved (Cambridge University Press author guidance; ACM defines primary affiliation as the institution where most of the research was conducted). An alma mater does not qualify for work done independently, and listing a university that subscribes to ACM Open would also wrongly trigger a fee waiver. Use "Independent Researcher" with city and country. You can still use your alumni email as contact address and name your degree in a biography. This would change if a Columbia faculty member joined the work.
- **Double-blind.** No names, affiliations, acknowledgements or links that identify you. arXiv preprints are allowed. The public repository under your name is not forbidden, but the submission must not point to it: provide an anonymised copy (anonymous.4open.science or a zip). GECCO 2027 also announces that runnable code is expected for review; details are not yet published.
- **AI use.** GECCO requires AI use for code or experiments to be described in the Methods and writing help to be named in the Acknowledgements. This project was built with heavy use of Claude, so the paper has to say so. Invented references can mean desk rejection: every citation gets checked against its source.
- **Costs to expect.** ACM publication charge of $500 for ACM or SIG members, $750 otherwise; ACM says waivers for independent authors are unlikely. One author must register by 10 May and present in person in Kraków. Registration fees for 2027 are not yet published.
- **arXiv.** Since January 2026 an institutional email no longer gives automatic endorsement. As a first-time submitter you need a personal endorsement from an established arXiv author in computer science. Ask early (December). Category cs.NE, cross-listed to cs.RO.
- **Track.** BBSR if the paper is framed as a reproduction; Complex Systems otherwise (it accepted 5 to 8 full papers a year recently). Decide at G2.

---

## 12. Risks

| Risk | What I would do |
|---|---|
| The residual gap in the transplant test stays near 30% | Report it as the measured simulator-to-simulator gap, with the reference-simulator comparison showing where it arises |
| The 2013 simulator does not build | Time-boxed. Fall back to scene comparisons against the newer Voxelyze and to the transplant test alone |
| Re-evolution lands far below the original | That is a result: quantify it, and separate physics from search with E3 and the transplant ceiling |
| Ten seeds are too few to separate arms | Top up the two key arms to 20; report intervals and effect sizes, not just p-values |
| A run dies overnight (sleep, crash) | Keep-awake, per-generation checkpoints, the run queue restarts |
| Time: holidays, day job | The fallback rule in section 8 |
| Someone publishes a reproduction first | Low: none found, and the deposit is 13 years old. A preprint in January fixes the date |
| Reviewers ask for a novelty-search arm (Gravina 2018) | State it as out of scope for a reproduction; plan it for paper 2 |

---

## 13. Decisions that are yours

| # | Decision | My default |
|---|---|---|
| 1 | Paper 1 is the reproduction and audit; body-first moves to paper 2 | Yes |
| 2 | Add the 2013 physics settings as new options and a preset (defaults unchanged) | Yes |
| 3 | Install a compiler in WSL and build the 2013 simulator as reference | Yes, time-boxed |
| 4 | Copy the earlier analysis scripts out of the temp folder into the repository | Yes, soon |
| 5 | Repository cleanup: licence (MIT for code), README, remove third-party PDFs. Whether to also purge them from git history is a separate, destructive step | Yes to cleanup; leave history alone unless you want it |
| 6 | Commit this `paper/` folder to GitHub, on a new branch | Your call; nothing is committed yet |
| 7 | Which tools from section 10 to install | scipy, pandas, pytest now; LaTeX and gh when writing starts |
| 8 | Budget for GECCO (publication charge, registration, travel to Kraków) | Check before committing to the full-paper route |
| 9 | Affiliation line | Independent Researcher |

| 10 | Use the rebuilt 2013 simulator as the evaluation back end for the re-evolution experiments (section 3.7), keeping the MuJoCo engine as the independent second implementation | Yes |
| 11 | Arms D and E, before they start: the engine differs from the 2013 simulator in where a body starts (on the floor, against where it is in the workspace) and in its floor (hard, against a spring with a stop-dead friction rule). The test of 25 November shows that the floor is what costs the 2013 champions their score in the engine (section 3.18). Keep the preset as frozen and report both differences, or build both into the engine first | Build both into the engine as options (the 2013 floor rule and the 2013 start), with tests against the 2013 simulator, and make them arm D's setting; keep the present hard floor as one of the E arms, so that the paper measures what the floor does to evolution, not only to finished champions. It is a change to arms that have not started: a new code tag and an entry in section 9 of the protocol |
| 12 | Which sensitivity arm carries the hard floor (`--preset cheney2013` as it was). The protocol's E3, "the soft floor of September 2026", is MuJoCo's default contact, on which bodies sink 3 to 4 voxels (section 3.18) | Make the hard floor E3 and drop the September floor from the campaign: it is far from the 2013 floor and the floor test already shows what it does to finished champions. Adding the hard floor as a fourth E arm instead costs three more runs, about a day |
| 13 | The time step. The 2013 files say `DtFrac` 0.9 (the step is 0.9 of the largest stable one); the engine uses 0.7. The 2013 floor rule stops a sliding voxel when the brake would stop it within one step, so the step is part of the rule | Keep 0.7. Measured on 25 November: the 12 pilot robots agree a little better with the 2013 simulator at 0.9 (off by 14% against 18%), but the 140 champions do not (75 closer at 0.9, 65 further; typical error better in two sets, worse in two). Keeping 0.7 also keeps arm D on the step of every check made so far and of arm E3, so that E3 differs from D in the floor and the start only. What 0.9 would buy is a fifth less machine time |
| 14 | Memory for arms D and E, before arm D starts (section 3.20). Two things are wrong as the code stands. A worker asks the system for 2.6 to 3.2 GB and uses a small fraction of it, so only 7 to 9 workers fit on 32 logical processors. And if memory does run short during a run, the search scores the body 0 and goes on, which would falsify the run without a trace. Four possible steps: (a) one linear-algebra thread per worker, a setting the launcher and the scoring scripts hand to their processes, with no change to the engine or the search; (b) the search stops a run when an evaluation fails for lack of memory, instead of scoring it 0, so that the run is continued from its last generation, exactly as it would have gone (protocol, section 9.3), once memory is there; (c) state in the engine how much memory MuJoCo reserves for a body; (d) give Windows a larger, fixed page file, a system setting that is yours to change. (b) and (c) change the code that computes a run and so need a new code tag, `campaign-v4`, and an entry in section 9 of the protocol | (a), (b) and (c) together, before arm D. (b) is the one that protects the result; (a) and (c) make the shortage itself unlikely: a worker then asks for well under half a GB instead of up to 3.2. Each is held to the recorded scores before it is used: all 140 champions under both presets to the last digit, and a short search run repeated generation for generation. Then (d) is not needed. My estimate is half a day of work |

**Decided on 27 November 2026:** 14 yes ("Yes, make them"): steps (a), (b) and (c), made that day and tagged `campaign-v4` (section 3.22; protocol, section 9.6). Step (d), a larger page file, is not needed: a process of a run now asks the system for about 0.1 GB.

**Decided on 25 November 2026:** 11 yes ("Yes, build it"): the 2013 floor rule and the 2013 start are built into the engine as options, and arm D is to run with them (section 3.19). 12 ("Yes, replace E3"): arm E3 is the hard floor, `--preset cheney2013` as it was; the September soft floor leaves the campaign (protocol, section 9.5). 13 ("Yes, keep 0.7"): arms D and E keep the engine's time step.

**Decided on 21 November 2026:** 1 yes. 2 yes, as new options with defaults unchanged, together with the 2013 cost penalty, a switch for the 2013 CPPN-NEAT settings and a run manifest. 3 yes. 4 yes. 6 yes: branch `paper/reproduction`, small commits, pushed. 7: scipy, pandas and pytest. 10 yes. The 2013 search is realised by re-running the original search code (yes; built and piloted, section 3.9). The protocol is approved and frozen, and arm R (35 re-runs of the original code) has your go-ahead (section 3.10). Still open: 5, 8, 9, and the go-ahead for each later arm (Rc, A, D, E), which each cost days of machine time.

**Done on 21 November 2026:** scripts rescued into `analysis/archive_2026/`; packages installed and pinned in `requirements.txt`; the 2013 simulator built and checked (section 3.7); `--damping-global`, `--preset cheney2013` and the run manifest; `--simulator voxelyze2013` and `--penalty` (section 3.8); a 100-generation pilot; the protocol drafted; the original search program built and piloted on 12 seeds (section 3.9); the protocol frozen and the launcher for arms R and Rc built and tried (section 3.10). Not yet done: storing the original score per generation for cost runs with this project's search; the render and verify tools reading the manifest; a queue for the arms that use this project's own search (A, D, E).
