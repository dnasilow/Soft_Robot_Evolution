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

- **Reading.** With the physics now identical to 2013, the run starts ahead of most deposited runs and then stalls, the same pattern as in your own engine. The champion's network did not grow after generation 10. One seed proves nothing, but it points at the search, which is what arm B of the protocol tests.
- **Shape.** The pilot champion is squat: 482 voxels, the whole 100-cell footprint on the floor, 98% muscle. Deposited champions perch on a median of 26 cells. So that difference survives the change of simulator.
- **Transfer.** The pilot champion scores 2.73 in the MuJoCo engine with the 2013 preset, a third more than in the simulator it evolved in. The deposited champions lose a third going the same way. The two simulators differ in both directions depending on the body.

### 3.9 21 November: the original experiment itself, re-run

Details in [reference_2013/README.md](reference_2013/README.md), section 5.

- **The original search program builds and runs.** HyperNEAT v2.5 with the Softbots experiment, from the same archive, built in WSL with CMake 4.2 and Boost 1.90 (installed for this). It needed compiler switches, a force-included compatibility header and a six-line patch to `main.cpp`; none changes what the program computes. The decisive switch restores the 2013 text-string layout, without which the program corrupts its own settings table.
- **It behaves like the deposited runs so far.** Twelve seeds for ten generations: the champion score has a median of 1.71 at generation 10 against 1.50 for the 35 deposited runs (ratio 1.14, bootstrapped 95% interval 0.86 to 1.50, p = 0.36). Generations 1, 2 and 5 agree as closely.
- **It is slow per run, cheap in total.** Each run uses one core: about 90 seconds per generation at the start, so 1000 generations is more than a day per run, but all 35 runs of an arm can run side by side.
- **What this gives the paper.** A ladder of three steps, each with its own arm in [PROTOCOL.md](PROTOCOL.md): the original code re-run with new seeds (does the experiment repeat?), an independent search in the original simulator (arm A), and an independent search in an independent simulator (arm D). The single-seed pilot of section 3.8 suggests the second step is where the gap opens.

### 3.10 21 November: protocol frozen, launcher for the re-execution arms

- **The protocol is frozen** (your approval of 21 November) and the campaign code is tagged `campaign-v1`. How its open points were settled is in its section 8. One rule changed in wording against the draft you approved: a run of the original program that dies is started again from the beginning with the same seed, instead of "resumed from its checkpoint". No seed is ever replaced.
- **That is safe because the original program is deterministic.** Seeds 1 to 3 over ten generations gave the pilot's scores to the last digit, whether three or twelve runs shared the machine, and so did seeds that were cut short and started again.
- **The build recipe is confirmed.** Both programs rebuilt from the scripts in the repository are byte for byte the ones the pilot ran with.
- **`paper/reference_2013/start_arm.py`** starts an arm in a console window of its own, keeps Windows awake, refuses a second launcher, reports progress without showing scores, and checks at the end that every seed has its 1000 generations. Details in [reference_2013/README.md](reference_2013/README.md), section 6.
- **A hazard removed.** The simulator build script cleared the whole reference folder, which also holds the run folders. It no longer does, and neither build script runs while runs are in progress.

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

**Decided on 21 November 2026:** 1 yes. 2 yes, as new options with defaults unchanged, together with the 2013 cost penalty, a switch for the 2013 CPPN-NEAT settings and a run manifest. 3 yes. 4 yes. 6 yes: branch `paper/reproduction`, small commits, pushed. 7: scipy, pandas and pytest. 10 yes. The 2013 search is realised by re-running the original search code (yes; built and piloted, section 3.9). The protocol is approved and frozen, and arm R (35 re-runs of the original code) has your go-ahead (section 3.10). Still open: 5, 8, 9, and the go-ahead for each later arm (Rc, A, D, E), which each cost days of machine time.

**Done on 21 November 2026:** scripts rescued into `analysis/archive_2026/`; packages installed and pinned in `requirements.txt`; the 2013 simulator built and checked (section 3.7); `--damping-global`, `--preset cheney2013` and the run manifest; `--simulator voxelyze2013` and `--penalty` (section 3.8); a 100-generation pilot; the protocol drafted; the original search program built and piloted on 12 seeds (section 3.9); the protocol frozen and the launcher for arms R and Rc built and tried (section 3.10). Not yet done: storing the original score per generation for cost runs with this project's search; the render and verify tools reading the manifest; a queue for the arms that use this project's own search (A, D, E).
