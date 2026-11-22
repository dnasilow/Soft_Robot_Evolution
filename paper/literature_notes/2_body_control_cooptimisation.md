# Literature survey 2 — Co-optimisation of morphology and control

Topic: why co-optimisation is hard, premature convergence of morphology, remedies, and whether
"body first, control later" / staged / decoupled protocols have been tested (2D vs 3D).
Survey date: 18 November 2026.

## 0. How to read these notes

Verification codes (what I actually opened for each paper):

- **[L]** local full text in `C:\SoftRobotEvolution\research_reference\extracted\` (read directly).
- **[P]** full paper PDF fetched from the web and converted to text; read directly.
- **[H]** arXiv HTML / ar5iv / publisher full text read through the fetch tool (a small model summarises
  the page; numbers are as extracted by that tool — re-check against the PDF before quoting in a paper).
- **[A]** abstract / metadata page only (arXiv abs page, Crossref, Semantic Scholar, Europe PMC, lab page).
- **[S]** search-engine snippet only -> treat every detail as UNVERIFIED.

Nothing below is from memory alone. Where I could not confirm something it says UNVERIFIED.
Dimensionality (2D/3D) is only stated when the source said so; otherwise "not stated on the page opened".

---

## 1. The Cheney line: premature convergence in 3D voxel soft robots (Voxelyze / VoxCad)

### 1.1 Cheney, MacCurdy, Clune, Lipson 2013 — "Unshackling evolution" [L]
- GECCO 2013, pp. 167-174, doi 10.1145/2463372.2463404. Local: `Unshackling_Evolution_Cheney_2013.txt`.
- Setting: 3D, VoxCad/Voxelyze, CPPN-NEAT bodies, 4 materials, fixed open-loop actuation (body-only evolution).
  "Treatments consist of 35 runs, each with a population size of 30, evolved for 1000 generations";
  fitness = centre-of-mass displacement after 10 actuation cycles. Plots: medians with 95% bootstrapped CIs;
  p-values reported (test name not found in my grep of the local text).
- Relevance: this is "stage 1 only" (body under a fixed gait). It is the system re-implemented in the project.

### 1.2 Cheney, Bongard, SunSpiral, Lipson 2016 — "On the difficulty of co-optimizing morphology and control in evolved virtual creatures" [P]
- Proc. Artificial Life Conference 2016 (ALIFE XV), MIT Press, pp. 226-233, doi 10.7551/978-0-262-33936-0-ch042.
  PDF: https://meclab.w3.uvm.edu/papers/2016_ALife_Cheney.pdf
- **"Lipson et al. 2016" is the same paper**: DBLP indexes it with the author order reversed
  (DBLP key `conf/alife/LipsonSBC16`, seen in the Semantic Scholar record for this DOI). There is no second paper.
- Setting: **3D**, VoxCad, **7x7x7** voxel space; dual-network CPPN (one network for morphology: presence + muscle/tissue;
  one for control: per-voxel **phase offset** + a global frequency 5-10 Hz); 20 actuation cycles per evaluation;
  (mu/rho + lambda) = (50/25 + 25); no crossover; each mutation hits only one of the two networks (50/50).
  Constraint: at least 10% of voxels filled and at least 5% muscle.
  **30 independent runs x 5000 generations**; Mann-Whitney rank-sum test; 95% CIs by bootstrap (10,000 samples).
- What they did (the staged "freezing" experiments):
  - Co-optimise both up to generation X, then **freeze the morphology** and continue with control mutations only (Fig. 2).
    Result: morphologies optimised for only **25 generations or more** give final fitness not significantly different from
    full 5000-generation co-optimisation (p >= 0.0604 for all freezing points >= 25).
    Control optimisation after the freeze still helps: 26.520 vs 21.157 at the freezing time (p < 0.001).
  - Converse: **freeze the controller**, continue with morphology only (Fig. 3). Significant loss for freezing points <= 100
    generations, not for >= 250 (p >= 0.0565).
  - Final (best-of-run) morphology appears on average at generation 558; best controller mutation at 2926 (p < 0.001).
  - With an energy term in the fitness (penalising actuated voxels) morphologies look more complex but the same pattern holds
    (final controller gen 2968 vs morphology gen 419, p < 0.001).
  - When control is reduced to **two discrete phase states** (the Cheney 2013 scheme) the asymmetry disappears
    (665 vs 795, p = 0.149) — and the authors note that with two muscle types the line between "morphology" and "control" blurs.
- Claim: morphology converges prematurely because a body mutation "scrambles" the controller-body interface (embodied cognition).
- Their future work: repeat the freezing approach with other encodings, neural / closed-loop control, diversity-preserving EAs,
  harder tasks, other scales; the morphology/control split is arbitrary and should be varied; "multi-timescale" re-adaptation (-> MIP).
- Relevance: first staged (co-optimise -> control-only) analysis **in 3D voxel robots**. It is not body-first-under-fixed-gait:
  stage 1 is co-optimisation. Note the two-phase-state result: the project's 4-material fixed gait IS the regime where
  Cheney 2016 saw no morphology/control asymmetry.

### 1.3 Cheney, Bongard, SunSpiral, Lipson 2018 — "Scalable co-optimization of morphology and control in embodied machines" [P]
- J. R. Soc. Interface 15(143):20170937, doi 10.1098/rsif.2017.0937 (Crossref checked). arXiv:1706.06133 (v2 read).
- Setting: **3D**, VoxCad; CPPN morphology + separate CPPN controller (per-voxel phase offset, global frequency);
  **5x5x5** default, **10x10x10** "high resolution"; (mu, lambda)-ES with mu = 25, lambda = 25 ("population size of 50");
  5000 generations; 20 actuation cycles; 50% chance a mutation hits body or controller (other ratios 1:99 ... 99:1 tried, no effect).
  **30 independent trials per treatment** with seeds shared across treatments; Wilcoxon rank-sum; means with 95% bootstrapped CIs.
- Method: **morphological innovation protection (MIP)** = age-fitness Pareto selection where "age" is reset when the body mutates,
  so a new body only competes with bodies that had equal or less controller re-adaptation.
- Results (voxels travelled): no protection 21.717 (CI 19.457-22.426); **MIP 31.953** (CI 28.157-36.511), p = 6.067e-6;
  "controller innovation protection" 22.049 (not better than none, p = 0.240). Without protection no significant improvement
  from generation 1000 to 5000 (p = 0.085); with MIP 25.925 -> 31.953 (p = 0.013).
  At 10^3 resolution the text reports 60.728 for MIP vs 32.575 without (p = 1.208e-4) and 35.375 for controller protection
  (p = 0.018), and 43.340 for the other MIP variant; the arXiv v2 sentence is ambiguous about which of the two MIP numbers is
  "with the 20% change threshold" (difference between them p = 0.063). Check the journal version before quoting.
- Their future work: rigid bodies / centralised controllers; test generality; developmental body-brain feedback; NAS analogy.
- Relevance: the canonical remedy, and it is **3D with per-voxel phase control** — i.e. the exact co-evolution setting in which the
  project saw collapse to single-material blobs. A MIP arm is the obvious matched baseline.

### 1.4 Context papers
- **Sims 1994**, "Evolving virtual creatures", SIGGRAPH '94 pp. 15-22; "Evolving 3D morphology and behavior by competition",
  Artificial Life IV pp. 28-39. [A: https://www.karlsims.com/evolved-virtual-creatures.html]. Body and control evolved together.
- **Bongard 2011**, "Morphological change in machines accelerates the evolution of robust behavior", PNAS 108(4):1234-1239,
  doi 10.1073/pnas.1015390108, PMID 21220304 [A: Europe PMC record]. Robots that start anguilliform and grow legs during life,
  early in evolution, evolve gaits for the legged form faster and more robustly; the anguilliform stage is later lost.
  (Run counts and simulator NOT extracted — abstract only.)
- **Joachimczak, Suzuki, Arita 2016**, "Artificial metamorphosis", Artificial Life 22(3):271-298, doi 10.1162/ARTL_a_00207
  [quoted at length inside Cheney 2016, P]. Source of the original observation that morphology locks in within the first few
  hundred generations while controllers keep improving. (2D per Mertan & Cheney 2024's description of that simulator family.)
- **Kriegman, Cheney, Bongard 2018**, "How morphological development can guide evolution", Sci. Rep. 8:13934,
  doi 10.1038/s41598-018-31868-7, arXiv:1711.07387 [H]. **3D** Voxelyze, 4x4x3 robots; morphology = per-voxel resting length,
  control = per-voxel phase offset; Evo vs Evo-Devo; **30 trials**, population 30, 10,000 generations, AFPO;
  Mann-Whitney U, bootstrapped 95% CIs. 25/30 Evo-Devo runs found the fast design vs 6/30 Evo runs.
  "Differential canalization": body development made bodies robust to control mutations; controllers stayed sensitive to body mutations.
- **Corucci, Cheney, Giorgio-Serchi, Bongard, Laschi 2018**, Soft Robotics 5(4):475-495 [L]. **3D**; two CPPNs (morphology; control =
  frequency + per-voxel phase); **15 repetitions per treatment**; Mann-Whitney U with Bonferroni; 95% bootstrap CIs.
  The authors themselves call 15 repetitions and the generation count a limitation and suggest AFPO.

---

## 2. Mertan & Cheney 2023-2026 (all in 2D Evolution Gym)

### 2.1 Mertan & Cheney 2023 — "Modular controllers facilitate the co-optimization of morphology and control in soft robots" [P]
- GECCO '23, pp. 174-183, doi 10.1145/3583131.3590416, arXiv:2306.09358. Code: github.com/mertan-a/gecco-23.
- Setting: EvoGym, **2D**, 5x5 bounding box, Walker-v0, max 500 time steps, controller queried every 4th step.
  Global MLP (7289 parameters) vs shared modular MLP per active voxel (6497 parameters, Moore neighbourhood 2); 1 hidden layer of 32.
  (mu + lambda)-ES, mu = lambda = 16, age-fitness Pareto with age reset after every mutation, one random individual per generation;
  10% per-voxel body mutation; controller noise N(0, 0.1); 50/50 body/brain mutation.
  **100 independent runs per controller type, 5000 generations**. Wilcoxon rank-sum; 95% bootstrapped CIs.
- Results: run champions 10.42 (modular) vs 9.67 (global), p = 0.0016; modular reaches 99% of final fitness at generation 2710 vs 3059.
  On four hand-made fixed bodies (10 seeds, 1500 generations) modular is NOT better (global better on Biped, p < 0.01).
  Transfer test: 20 mutated neighbours per distance; zero-shot and one-shot transfer never worse and often better for modular.
  Share of successful mutations that are body mutations is higher with modular control (p < 0.05).
- Claim: the gain comes from better transfer of the controller to mutated bodies, i.e. better search over morphologies.
- Their own caveats / future work: "the advantages presented in the paper are significant but small"; "relatively small 2D design
  space"; future work in "more complicated 3D design spaces", harder tasks, closed-loop sensing; combine with MIP;
  bodies that are robust to controller perturbation.

### 2.2 Mertan & Cheney 2024 — "Investigating premature convergence in co-optimization of morphology and control in evolved virtual soft robots" [L]
- EuroGP 2024 (EvoStar), LNCS 14631, pp. 38-55, Springer, doi 10.1007/978-3-031-56957-9_3 (gpbib record checked); arXiv:2402.09231.
- Setting: EvoGym v1.0.0, **2D** (they state it "works in 2D"); direct encoding; bounding boxes **5x5 and 7x7**;
  Walker-v0 and BridgeWalker-v0 -> 4 settings (W5, W7, B5, B7).
  Learnable controller: shared modular network (32 hidden), 3x3 observation window, proprioception + time signal (t mod 2).
  **Fixed controller**: zero parameters, no sensing; every active voxel alternates between maximal expansion and maximal contraction
  at each effective time step (controller queried every 5th step).
  AFPO with truncation selection, **population 16, 10,000 generations**, one random individual per generation, mutation only,
  10% per-voxel body mutation, 50/50 body/controller mutation (with the fixed controller a "controller mutation" just copies).
  **10 independent runs per setting**; Wilcoxon rank-sum; fitness curves with 95% bootstrapped CIs; every run champion plotted.
- Experiment 1 (evolution): fixed-controller populations (= morphology-only optimisation) find significantly better solutions in
  all 4 settings (all P < 0.005) and faster (all P < 0.05 for reaching 85% of final performance).
  Fixed-controller champions converge on the same body plan across runs (t-SNE, intra-cluster distance); learnable runs are diverse,
  which the authors read as poor search, not as a virtue.
- Experiment 2 (**the "fixed controller, then optimise" test**): take the body of each fixed-controller run champion, start a new run
  "from scratch, with 16 individuals having the same fixed body plan", and optimise **only the controller for 5000 generations**.
  - Learnable controller on fixed-champion bodies beats the co-optimised (learnable) champions in **3 of 4 settings (W5, W7, B5; all P < 0.05)**.
  - Control for "retraining alone helps": retrain a learnable controller from scratch on the co-optimised champions' own bodies ->
    statistically indistinguishable from the originals (all P > 0.44).
  - Fixed controller on learnable-champion bodies is very poor (means W5 4.88, W7 6.31, B5 2.64, B7 2.47).
  - **The learnable controller trained on fixed-champion bodies does not always reach what the fixed controller itself achieves on
    those bodies (P < 0.05 in W5, W7, B7).** I.e. stage 2 frequently ended BELOW stage 1.
  - Footnote: all experiments were repeated with a global controller with no qualitative difference (results not shown).
- Claims: high-performing body regions exist that co-optimisation does not find but body-only optimisation finds easily
  ("the most concrete example to date"); the bottleneck is sub-par morphologies, not sub-par controllers; proposed
  "morphology-centric" landscape view (a range of fitness per body; first-mover advantage for early bodies).
- What it is NOT: it is an analysis, not a proposed two-stage method. Budgets are not matched (the staged pipeline uses
  10,000 + 5,000 generations against 10,000); there is no QD in stage 1; n = 10; 2D only; two locomotion tasks.
- Their future work: tasks whose complexity matches the controller; scaling "no controller" body-centred solutions to tasks that
  seem to need closed-loop control; links to surrogate fitness, bandits, NAS supernets, transfer/meta-learning of controllers.

### 2.3 Mertan & Cheney 2024 — "Towards multi-morphology controllers with diversity and knowledge distillation" [P]
- GECCO '24, pp. 367-376, doi 10.1145/3638529.3654013, arXiv:2404.14625.
- Setting: EvoGym v1.0.0, **2D**, 5x5, Walker-v0 (BridgeWalker-v0 for fine-tuning); observation and action noise N(0, 0.01);
  each evaluation repeated 5 times. MAP-Elites (descriptors: number of voxels x number of active voxels), 16 offspring per generation,
  **20,000 generations -> an archive of 296 morphologies** (the text describes one map); teachers = top 10/40/75/100% (29/118/222/296);
  distillation by supervised learning; zero-shot test on 357 unseen bodies from 30 pairs; fine-tuning 300 generations of AFPO.
  Statistics: one-sample t-test on relative performance; Wilcoxon rank-sum for two samples; alpha = .05.
- Claims: a distilled controller matches its teachers on most bodies, generalises zero-shot to unseen bodies, and is a better
  starting point for fine-tuning (faster to 90/95/99% of final performance; final performance not significantly different).
- Their discussion: migrations between MAP-Elites cells were "very limited" — body mutations rarely survive even in QD;
  doubts about QD scaling to complex morphology spaces; future work in 3D and on real robots.

### 2.4 Mertan & Cheney 2024 — "No-brainer: morphological computation driven adaptive behavior in soft robots" [L]
- SAB 2024 (From Animals to Animats 17), pp. 81-92; arXiv:2407.16613. Code: github.com/mertan-a/no-brainer.
- Setting: EvoGym, **2D**; **MAP-Elites with a CPPN body genome**; no controller at all: two hand-designed muscle voxel types that
  follow a sinusoid with 180 degree phase offset ("similar to the designs in" Cheney 2013) plus four stimulus-reactive voxel types.
  7 archive dimensions (3 morphological, 4 behavioural); bounding boxes 5x5, 7x7, 10x10; **10 repetitions each**;
  3000 generations, 16 parents -> 16 offspring. Significance reported at P < 0.001.
- Claim: closed-loop adaptive behaviour (direction switching under two binary stimuli, logic-gate-like) from body alone.
- Relevance: methodologically the closest published analogue of the project's stage 1 (MAP-Elites + CPPN + fixed antiphase gait),
  but in 2D and for a different question.

### 2.5 Mertan & Cheney 2025 — "Controller distillation reduces fragile brain-body co-adaptation and enables migrations in MAP-Elites" [H]
- GECCO '25 (Complex Systems track, full paper), doi 10.1145/3712256.3726368, arXiv:2504.06523.
- Setting (as extracted): EvoGym, **2D**, **10x10** bounding box, Walker-v0; MAP-Elites with 10 x 10 bins (total voxels x active voxels);
  20 parents per generation; **10,000 generations**; 5 noisy evaluations per individual; **20 independent runs per condition**;
  Wilcoxon rank-sum, 95% CIs. "Pollination": every 500 generations distil a random archive solution and its 4 niche neighbours
  into one controller and give it back to the teachers if it performs comparably.
- Claims (key sentences re-checked as verbatim quotes through the fetch tool): in standard MAP-Elites migrations fall quickly to
  "over 4.7 migrations per 500 generations", occur "at a low fitness regime" and almost only at the very start of a champion's
  lineage; a "No Migration" control shows "no significant difference in the quality of the best robot found from the Standard
  treatment"; pollination raises total and maximal quality and makes descendants more robust to body mutations.
- Limitations stated: hyper-parameters from limited preliminary tests; generalist controllers are harder to optimise.

### 2.6 Mertan & Cheney 2025/2026 — "Evolutionary brain-body co-optimization consistently fails to select for morphological potential" [L]
- Conference: ALIFE 2025 proceedings, doi 10.1162/isal.a.891. Journal: **Artificial Life (MIT Press), doi 10.1162/artl.a.476,
  issued online 4 Sep 2026, pp. 1-20** (Crossref). arXiv:2508.17464 (v1 24 Aug 2025; **v2 12 Aug 2026 = accepted journal manuscript**,
  the local file). The journal version adds MIP and the goal-switching analysis to the conference paper.
- Setting: EvoGym, **2D**; **3x3** design space, at least 3 active voxels -> **1,305,840** viable morphologies; flat locomotion,
  max 500 steps; global MLP (32 hidden, 1417 parameters); single-voxel body mutation; controller noise N(0, 0.1).
- Landscape construction: for **every** morphology, 300 generations of AFPO (population 20) on the controller alone; the best
  fitness is the "estimated true fitness". Later updated for 94,201 morphologies with better controllers found during co-optimisation.
  Spearman rank correlation over controller-training time: ranking among the top 1-5% of bodies is uncorrelated with the final
  ranking early on -> early selection among good bodies is uninformed ("fast and slow learners").
  Ruggedness: mean distance to nearest local maximum 1.93 mutations, to the global maximum 7.08.
- Co-optimisation runs: AFPO, MAP-Elites (archive 28; active voxels x passive voxels), MIP (their variant: every body mutation gets
  protection); population 20; **10,000 generations; 100 independent repetitions per algorithm**; Mann-Whitney U test;
  curves with 95% bootstrapped CIs, smoothed with a 100-generation moving average.
- Results:
  - Near-optimal (top 30% of the fitness range, threshold 2.53; 308 such bodies) found in only **17/100 (AFPO), 22/100 (MAP-Elites),
    13/100 (MIP)** runs. AFPO vs MAP-Elites champions indistinguishable; MIP slightly worse (p < 0.05 / < 0.01) but found the best single robot.
  - Run champions that are local maxima in morphology space: 22 (AFPO), 62 (MAP-Elites), 43 (MIP) of 100 — the rest are stuck on
    bodies **one voxel mutation away from a better body**.
  - **Morphology-only evolution with oracle fitness** (AFPO, population 10, 1,000 generations, 100 repetitions — far less compute)
    is significantly better than all three and "consistently finds near-optimal morphologies".
  - Fitness drop after a body mutation during co-optimisation is much larger than the true-fitness difference (undervaluation);
    counterfactual "selection accuracy" by true potential stays low for all three algorithms.
  - **"To co-optimise or not"**: for the 5 best bodies, control-only optimisation from scratch (10,000 generations, population 10,
    10 seeds, t-distribution fitted) is unlikely (< 0.01) to reach the co-optimised controller's performance in **2 of 5** cases
    -> "goal switching" along a lineage of bodies helps the controller. The authors explicitly warn that **"fully decoupling
    optimization of morphology and control might result in suboptimal performance"** and question bi-level schemes, while admitting
    the comparison is not fair (3 algorithms x 100 runs x twice the compute to find these cases).
- Their future work: use the landscape to benchmark existing remedies; training schedules, hyper-parameters, encodings;
  "extend this analysis ... to more challenging design spaces, potentially utilizing different simulation engines";
  how common the goal-switching benefit is; whether control-only catches up with more compute.

### 2.7 Mertan & Cheney 2025 — "Morphological cognition: classifying MNIST digits through morphological computation alone" [A]
- ALIFE 2025 (talk), doi 10.1162/isal.a.892, arXiv:2508.17469. Controller-free voxel robots that move left/right depending on the digit shown.

### 2.8 Anything in 2026?
- arXiv author feed for Mertan (checked 18 Nov 2026): **no new 2026 submission**; only the v2 update of 2508.17464 (12 Aug 2026)
  and its Artificial Life publication (Sep 2026). The lab publication page stops at 2024.
- Cheney's arXiv author feed (27 entries, checked 18 Nov 2026): the 2026 entries are 2605.15435 and 2604.15414 (Lillo & Cheney,
  plasticity in continual learning / continual RL) and 2602.18467 (a health study). **No 2026 arXiv paper from this lab on soft robots or
  brain-body co-optimisation.** Papers published only in proceedings without an arXiv copy would not show up here.

---

## 3. Other evolutionary-robotics groups

### 3.1 Medvet, Pigozzi, Nadizar, Ferigo et al. (2D voxel soft robots; 2D-VSR-Sim / EvoGym)
- **Medvet, Pigozzi, Bartoli, Rochelli 2021**, "Biodiversity in evolved voxel-based soft robots", GECCO '21 pp. 129-137,
  doi 10.1145/3449639.3459315 [A: https://medvet.inginf.units.it/publications/2021-c-mpbr-biodiversity/]. Body+brain evolved for
  locomotion with 3 EAs x 2 representations; representation matters more than the EA; no clear diversity/effectiveness trade-off.
  2D (Mertan & Cheney 2024 list this simulator family as 2D). Run counts not extracted.
- **Pigozzi, Medvet, Bartoli, Rochelli 2023**, "Factors impacting diversity and effectiveness of evolved modular robots",
  ACM TELO, doi 10.1145/3587101 [A]. Adds environment as a factor; here EA and environment matter more than representation;
  proposes a species-based EA.
- **Pigozzi, Camerota Verdu, Medvet 2023**, "How the morphology encoding influences the learning ability in body-brain
  co-optimization", GECCO '23 pp. 1045-1054, doi 10.1145/3583131.3590429 [A]. Bodies evolved, controllers learned by RL;
  direct encoding gives better learning (mainly speed) than indirect; linked to the Baldwin effect.
- **Ferigo, Soros, Medvet, Iacca 2022**, "On the entanglement between evolvability and fitness", ALIFE 2022 [S + cited in L].
- **Medvet & Rusin 2022**, "Impact of morphology variations on evolved neural controllers for modular robots", WIVACE 2022,
  doi 10.1007/978-3-031-31183-3_22 [S]. Small body variations are generally detrimental to an evolved controller; quantifies the gain
  of re-optimising the controller.
- **Talamini, Medvet, Nichele 2021**, "Criticality-driven evolution of adaptable morphologies of voxel-based soft-robots",
  Frontiers in Robotics and AI 8:673156, doi 10.3389/frobt.2021.673156 [H]. **A true body-first protocol, in 2D**:
  stage 1 evolves 20-voxel bodies for a task-free criticality score (no task, no controller, no gravity);
  stage 2 optimises, with CMA-ES on the frozen bodies, a **per-voxel phase of a 1 Hz sinusoid** (and later a neural controller)
  for locomotion, jump and escape. 10 body runs; 10 CMA-ES runs x 10,000 evaluations per body and task; Mann-Whitney U + Bonferroni.
  Evidence is modest (overall rank difference vs hand-made bodies not significant; cheap "grown" random bodies do as well).
- **Medvet, Lippolis, Nadizar 2025**, "Quality-diversity in problems with composite solutions: a case study on body-brain robot
  optimization", GPEM 26:22, doi 10.1007/s10710-025-09520-x [A]. MAP-Elites works on body+brain only with two archives (one per part);
  proposes coevolutionary MAP-Elites (CoME).
- **Ferigo, Iacca, Medvet, Nadizar 2025**, "Totipotent neural controllers for modular soft robots ...", Neurocomputing 614:128811
  [cited in L; existence also in the Semantic Scholar citation list].
- **de Bruin, Glette, Ellefsen, Nadizar, Medvet 2026**, "Social learning strategies for evolved virtual soft robots",
  GECCO '26, doi 10.1145/3795095.3805149, arXiv:2604.12482 [H]. EvoGym **2D**, 5x5; outer GA (population 200, 50 generations),
  inner Bayesian optimisation (50 evaluations per body); **20 repetitions per condition**, Mann-Whitney U with Benjamini-Hochberg,
  box plots. Relevant finding: after a large-budget **re-learning of the controller on the frozen evolved bodies (500 evaluations)
  the differences between approaches largely vanish** -> gains during co-optimisation were better control, not better bodies.

### 3.2 Eiben, Miras, Luo, De Carlo et al. (modular rigid robots, Revolve; learning in the loop)
- **Miras, De Carlo, Akhatou, Eiben 2020**, "Evolving-controllers versus learning-controllers for morphologically evolvable robots",
  EvoApplications 2020, LNCS 12104 pp. 86-99, doi 10.1007/978-3-030-43722-0_6 [S]. Adding learning changes fitness and yields larger robots.
- **Eiben & Hart 2020**, "If it evolves it needs to learn", GECCO Companion pp. 1383-1384, doi 10.1145/3377929.3398151 [cited in L].
- **Luo, Stuurman, Tomczak, Ellers, Eiben 2022**, "The effects of learning in morphologically evolving robot systems",
  Frontiers in Robotics and AI 9:797393 [H]. 3D-printable modular robots (Revolve/Gazebo); body+brain evolved (CPPN), brain also learned
  (100 trials per newborn); **10 repetitions**, mu = 100, lambda = 50, 30 generations. Learning delta grows over generations
  (read as "morphological intelligence"); bodies evolve differently with learning.
- **Luo, Miras, Tomczak, Eiben 2023**, "Lamarck's revenge" arXiv:2309.13099 [A] = "Enhancing robot evolution through Lamarckian
  principles", Sci. Rep. 2023, doi 10.1038/s41598-023-48338-4. Lamarckian inheritance of learned brain features amplifies
  "morphological intelligence"; the benefit comes from better-matched newborns.
- **Luo, Miras, Longhi, Weissl, Eiben 2024/25**, "Lamarckian inheritance improves robot evolution in dynamic environments",
  arXiv:2403.19545 [A]; listed by Semantic Scholar as IEEE TEVC, doi 10.1109/TEVC.2025.3619278.
- **de Bruin, Glette, Ellefsen 2026**, "Lamarckian inheritance in dynamic environments: how key variables affect evolutionary dynamics",
  arXiv:2605.15769 [A] (virtual soft robots; Lamarckian loses only when changes are conflicting and unpredictable).
- **van Diggelen et al. 2023**, "Comparing robot controller optimization methods on evolvable morphologies", Evolutionary Computation,
  doi 10.1162/evco_a_00334 [existence only, Semantic Scholar list].

### 3.3 Hart / Le Goff; Glette / Nygaard / Arza; Nolfi; others
- **Le Goff & Hart 2021**, "On the challenges of jointly optimising robot morphology and control using a hierarchical optimisation
  scheme", GECCO Companion pp. 1498-1502, doi 10.1145/3449726.3463156 [cited in L (AdaControl) and listed among the papers citing
  Cheney 2016; my fetch of the PDF was blocked -> content UNVERIFIED beyond AdaControl's one-line description that simpler
  controllers gave higher morphological diversity, in rigid robots on flat terrain].
- **Thomson, Le Goff, Hart, Buchanan 2024**, "Understanding fitness landscapes in morpho-evolution via local optima networks",
  GECCO 2024, doi 10.1145/3638529.3654059, arXiv:2402.07822 [A]. Local-optima-network analysis of three encodings for a
  locomotion task; claimed as the first LON analysis in morpho-evolution. Relevant to any landscape-mapping contribution (gap 3).
- **de Bruin, Glette, Ellefsen 2024**, "More complex environments may be required to discover benefits of lifetime learning in
  evolving robots", arXiv:2412.16184 [A]. Learning helps much more on hilly than on flat terrain.
- **Hardman, Thuruthel, Iida 2020**, "Towards growing robots: a piecewise morphology-controller co-adaptation strategy for legged
  locomotion", TAROS 2020, doi 10.1007/978-3-030-63486-5_37 [title only — whether "piecewise" means alternating stages is UNVERIFIED].
- **Le Goff, Buchanan, Hart 2024**, "An investigation of the factors influencing evolutionary dynamics in the joint evolution of robot
  body and control", arXiv:2403.10303 [A]. Asynchronous evolution + goal-based selection + replace-worst was best.
- **Le Goff & Hart 2024**, "Improving efficiency of evolving robot designs via self-adaptive learning cycles and an asynchronous
  architecture", GECCO Companion pp. 1607-1615, doi 10.1145/3638530.3664116 [cited in L].
- **Nygaard, Samuelsen, Glette 2017**, "Overcoming initial convergence in multi-objective evolution of robot control and morphology using
  a two-phase approach", EvoApplications 2017, LNCS 10199 pp. 825-836, doi 10.1007/978-3-319-55849-3_53 [P:
  https://mn.uio.no/ifi/english/people/aca/kyrrehg/pubs/nygaard-evorobot2017.pdf]. Six-legged rigid robot (11 morphology parameters),
  physics simulation plus three real robots. Phase 1: free co-evolution of body and control (NSGA-II, 1024 generations x 256
  individuals, **20 runs**); phase 2: morphology locked, controllers reset to random and re-evolved with the same settings, for two
  selected evolved bodies and one hand design. Abstract: the two-phase solutions "outperform the single co-evolutionary run by
  over 10%". Phase 2 was run on hand-picked bodies; no rank test found in my grep. The authors suggest turning the idea into an
  operator that locks the morphology for some generations inside one run.
- **Arza, Veenstra, Nygaard, Glette 2024 (v2 Sep 2025)**, "An empirical study on the computation budget of co-optimization of robot
  design and control in simulation", arXiv:2409.08621 [H]. Four frameworks: EvoGym (2D soft 5x5), RoboGrammar (3D), gym-rem 2D, gym-rem
  (3D modular); budget 8e6 simulation steps; **60 runs per configuration**; mean with bootstrap 95% band.
  **Two-phase "retrain end"** (cheap controller training during design search, then lock the best design and retrain its controller)
  beat single-phase baselines in all four environments (not significant in gym-rem 2D). Lower per-design budgets give simpler designs.
- **Pagliuca & Nolfi 2020**, "The dynamic of body and brain co-evolution", arXiv:2011.11440 [A] (Semantic Scholar lists it in
  Adaptive Behavior, doi 10.1177/1059712321994685): gains come from continued mutual shaping; body changes did not necessarily
  hurt — a dissenting data point to the "body mutations scramble control" account, from rigid 2D-style locomotors. **Pagliuca 2026**, "Leveraging high morphology rates in body-brain
  co-evolution: a case study on 2D robot locomotion", doi 10.54364/cybersecurityjournal.2026.3227 [A].
- **Eguiarte-Morett & Aguilar 2023/24**, "Premature convergence in morphology and control co-evolution: a study", Adaptive Behavior
  32(2):137-165, doi 10.1177/10597123231198497 [A]. Benchmarks QD algorithms (MAP-Elites, NSLC, MNSLC, fitness-novelty MOEA);
  MAP-Elites balances exploration/exploitation but does not protect morphological diversity well.
- **Zardini, Zappetti, Zambrano, Iacca, Floreano 2021**, soft tensegrity modular robots, GECCO '21, arXiv:2104.12175 [A]
  (MAP-Elites vs ViE-NEAT vs double-map MAP-Elites).
- **Lehman & Stanley 2011** (novelty search with local competition) and **Nordmoen et al. 2021** (MAP-Elites for modular robots,
  doi 10.3389/frobt.2021.639173): cited in L as the diversity-based remedies.

---

## 4. Learning-based co-design (RL / differentiable); which are 2D and which 3D

| Paper | Venue / id | Simulator, dimension | Coupling of body and control | Seeds | Verif. |
|---|---|---|---|---|---|
| Gupta, Savarese, Ganguli, Fei-Fei 2021, "Embodied intelligence via learning and evolution" (DERL) | Nat. Commun. 12:5721, arXiv:2102.02202 | MuJoCo, **3D rigid** (UNIMAL) | bi-level: evolution outside, PPO from scratch inside (5M interactions per body), no weight inheritance; P = 576; ~4,000 bodies per run; 1,152 CPUs | **3 evolutionary runs per environment**; 95% bootstrapped CIs; Mann-Whitney U | H |
| Wang, Zhou, Fidler, Ba 2019, "Neural graph evolution" | ICLR 2019, arXiv:1906.05370 | MuJoCo; Fish **3D**, Walker **2D** | evolution over graphs, GNN controller weights inherited from parent (amortised fitness) | number of runs not given | H |
| Yuan, Song, Luo, Sun, Kitani 2022, "Transform2Act" | ICLR 2022 (oral), arXiv:2110.03659 | MuJoCo; 2D Locomotion, Swimmer, Gap Crosser **2D**; 3D Locomotion **3D** | one policy, three stages inside an episode (skeleton transform, attribute transform, execution) | 6 seeds | H |
| Bhatia, Jackson, Tian, Xu, Matusik 2021, "Evolution Gym" | NeurIPS 2021 pp. 2201-2214, arXiv:2201.09863 | own mass-spring, **2D** | bi-level: GA / BO / CPPN-NEAT outside, PPO inside (1000 iterations per robot); population 25; 250-750 robots; 5x5 (5x7) | **6 seeds** (10 main tasks), 3 seeds (all 32 tasks); mean with variance band | L |
| Wang et al. 2023, CuCo | ICLR 2023 | ModularEvoGym, "2D Voxel-based Soft Robots", compatible with Evolution Gym (README of github.com/Yuxing-Wang-THU/ModularEvoGym) -> **2D** | **curriculum over design-space size** (small -> target), design and control policies trained jointly with PPO per stage and inherited | not extracted | A |
| Wang et al. 2023, PreCo | CoRL 2023, PMLR 229:478-498 | "modular soft robot system" (dimension not stated on the page) | pre-train one co-design policy on many tasks, then fine-tune | not extracted | A |
| Song et al. 2024, MorphVAE | AAAI-24 pp. 10368-10376 | EvoGym **2D**, 5x5 | VAE over bodies outside, PPO inside; 1000 robot evaluations | **3 runs**; Wilcoxon rank-sum | L |
| Song et al. 2025, LASeR | ICLR 2025 | EvoGym (2D) | LLM proposes bodies, PPO inside | not extracted | cited in L |
| Harada & Iba 2024, "Lamarckian co-design of soft robots via transfer learning" | GECCO '24, doi 10.1145/3638529.3654180 | EvoGym (2D) | PPO weights inherited by offspring | not extracted | cited in L |
| Liu et al. 2024, "Rapidly evolving soft robots via action inheritance" | IEEE TEVC 28:1674-1688, doi 10.1109/TEVC.2023.3327459 | EvoGym (2D) | action inheritance | not extracted | cited in L |
| Tanaka & Aranha 2022, "Co-evolving morphology and control of soft robots using a single genome" | IEEE SSCI 2022, arXiv:2212.11517 | EvoGym (2D) | single HyperNEAT genome for body and controller; converged faster than separate genomes on 4 tasks | not extracted | A |
| Wang J. et al. 2026, "Evolving embodied intelligence: GNN-driven co-design" | arXiv:2603.19582 (20 Mar 2026) | EvoGym **2D** | GA outside; GAT-PPO inside with topology-consistent weight inheritance | **3 runs**, mean +/- std | L |
| Song J. et al. 2026, AdaControl | arXiv:2608.23100 (24 Aug 2026) | EvoGym **2D**, 5x5; Carrier, Pusher, BridgeWalker | GA outside, PPO inside; adaptive PPO length until survivors are not biased toward fast learners | **5 trials**; two-tailed t-tests; 1000 robot evaluations | L |
| Song J. et al. 2026, MISCO ("Generative evolutionary design of voxel-based soft robots with provable optimality") | arXiv:2609.29491 | voxel soft robots (simulated) | EDA + VAE | — | A |
| Shen et al. 2026, EvoGymCM | arXiv:2604.08258 (under review IROS 2026) | EvoGym-based; search snippet says 2D grid | adds continuous stiffness as a design variable | — | A |
| Zhang D. et al. 2026, "Phased genetic algorithm for simultaneous morphology and controller optimization in soft robots" | Discover Computing 29:579, doi 10.1007/s10791-026-10490-6 | EvoGym, 2D voxel matrices | bi-level: GA over bodies, fresh PPO per body (512,000 steps). **"Phased" = mutation-only for the first 5 generations, then block crossover — NOT a body-then-control staging** | seeds not reported; no tests | H |
| Xie, Chu, Wang, Iida 2025, "The morphology-control trade-off" | arXiv:2503.16127 (not peer-reviewed) | EvoGym | MAP-Elites generates 81 structures, PPO controllers trained; the text is inconsistent on whether controllers were trained during or after body search; no seeds or tests reported | none reported | H |
| Zhang S. 2026, "Beyond task reward: a controller-restriction protocol ..." | arXiv:2610.07629 (6 Oct 2026) | EvoGym, 5x5 (2D) | scores each co-designed body under a **restricted open-loop travelling-wave controller** (4 parameters, random search, 48 evaluations); as a second objective it missed its pre-registered bar (3 of 5 runs) | 2-3 runs per arm | H |
| Sato, Yuhn, Kobayashi, Kawamoto, Nomura 2024, "Computational co-design of structure and feedback controller for locomoting soft robots" | arXiv:2407.09270 | MLS-MPM; **2D and 3D** walkers | **simultaneous** topology optimisation + actuator layout + NN controller; no sequential baseline | single optimisation per setting | H |
| Wang T.-H. et al. 2023, SoftZoo | ICLR 2023, arXiv:2303.09555 | differentiable MPM, **3D** | reports control-only (fixed design), design-only (fixed controller) and joint co-design; swimmer: joint 0.332 vs design-only 0.152 vs control-only 0.107 | best of 8 initialisations (diff. physics); 5 seeds (RL) | H |
| Strgar, Matthews, Hummer, Kriegman 2024, "Evolution and learning in differentiable robots" | RSS 2024, arXiv:2405.14712 | differentiable mass-spring; **2D** (stated in the 2025 follow-up) | bi-level: GA over bodies, gradient-trained controllers inside; evolution yields "increasingly differentiable" bodies | not extracted | A |
| **Strgar & Kriegman 2025**, "Accelerated co-design of robots through morphological pretraining" | arXiv:2502.10862; Semantic Scholar lists ICLR; cited as ICLR 2026 in AdaControl | differentiable mass-spring, **3D voxel** (6x6x4 workspace) | **staged, controller first**: pre-train one universal controller on > 10 million bodies; "zero-shot evolution" of bodies with the controller frozen (population 8,192, 100 generations); "few-shot" fine-tuning per generation; baseline = simultaneous co-design from scratch, which shows "diversity collapse" | **3 trials**, min-max shading, **no statistical tests**; 8 H100 GPUs | H |
| Matthews, Spielberg, Rus, Kriegman, Bongard 2023, "Efficient automatic design of robots" | PNAS 120(41):e2305180120, arXiv:2306.03263 | gradient-based design; dimension not stated on the abstract page | joint | — | A |
| Li, Matthews, Kriegman 2023/24, "Reinforcement learning for freeform robot design" | ICRA 2024, arXiv:2310.05670 | **3D** freeform bodies | RL designs the body; **open-loop control only** | — | A |
| Li, Kong, Kriegman 2024/25, "Generating freeform endoskeletal robots" | ICLR 2025, arXiv:2412.01036 | **3D** soft-rigid | evolution in a learned latent design space; RL controller per design | — | A |
| Guo, Zhang, Li, Li, Kriegman 2026, "Evolving dexterous robots from scratch" | arXiv:2609.33101 | not stated on the abstract page | evolution of designs, then RL trains each evolved design | — | A |
| Jeon et al. 2025, "Convergent functions, divergent forms" (LOKI) | arXiv:2505.21665 | UNIMAL design space | shared policies per cluster of similar bodies; cited by Mertan & Cheney for "fast and slow learners" in rigid robots | — | A |
| Dai, Wang, Ashley, Schmidhuber 2026, "Efficient morphology-control co-design via Stackelberg PPO" | ICLR 2026, arXiv:2603.15388 | not stated on the abstract page | models control adaptation inside the morphology update (leader-follower) | — | A |
| Feng et al. 2026, "Bridging body and brain: gene-driven morphology-control co-design" | arXiv:2609.31329 | "2D and 3D co-design tasks" | shared latent "Morphogene" conditions both body and control | — | A |
| Hejna, Abbeel, Pinto 2021, "Task-agnostic morphology evolution" (TAME) | ICLR 2021, arXiv:2102.13100 | "2D, 3D, and manipulation environments" (rigid) | **body first without any task or reward** (random action primitives, information-theoretic objective), controllers trained afterwards | — | A |
| **Candiello, Mekkattu, Michelis, Katzschmann 2026**, "A unified low-dimensional design embedding for joint optimization of shape, material, and actuation in soft robots" | arXiv:2603.06497 (6 Mar 2026), no venue named | black-box variational FEM, **3D** (swimmer on a tetrahedral mesh; **jumper on a 7x7x7 hexahedral grid**) | **explicit sequential-vs-joint test, matched budget**: sequential = shape+material for 150 generations with actuation fixed, then actuation alone for 50; joint = 200 generations; CMA-ES, lambda = 50, 10,000 simulator calls each; open-loop actuation | **single run per condition, no seeds, no statistics** | H |
| Wang Y. et al. 2025, "Embodied co-design for rapidly evolving agents: taxonomy, frontiers, and challenges" (survey) | arXiv:2512.04770 | — | taxonomy: bi-level, single-level, generative, open-ended; names MIP as the remedy for premature convergence; challenge headings: efficiency/scalability, generalisation, sim-to-real, theories, benchmarks/datasets | — | H (partly) |

Not found: a co-design algorithm called **"MoMa"** on Evolution Gym (one targeted search; nothing came up) -> UNVERIFIED / possibly a mis-remembered name.

---

## 5. Has "body first, control later" (or any staged / decoupled protocol) been tested? Evidence by dimension

### 5.1 In 2D
| Study | Stage 1 | Stage 2 | Compared with | n | Outcome |
|---|---|---|---|---|---|
| Mertan & Cheney 2024 (EvoGym 5x5, 7x7) | bodies evolved under a **fixed open-loop controller** (AFPO, 10,000 generations) | learnable controller evolved on the frozen champion body, 5,000 generations | co-optimisation with the learnable controller (10,000 generations); budgets NOT matched | 10 runs | staged > co-optimised in 3 of 4 settings (P < 0.05); but stage 2 below stage 1's fixed controller in 3 of 4 |
| Mertan & Cheney 2025/26 (EvoGym 3x3) | morphology-only evolution on **oracle** true fitness | — | AFPO / MAP-Elites / MIP co-optimisation | 100 runs | morphology-only far better with less compute; yet control-only from scratch cannot match co-optimised controllers on 2 of 5 top bodies |
| Talamini, Medvet, Nichele 2021 (2D-VSR-Sim) | bodies evolved for task-free criticality | CMA-ES on per-voxel phase (and NN) on frozen bodies | hand-made and random bodies (no co-evolution baseline) | 10 | modest, mostly non-significant |
| de Bruin et al. 2026 (EvoGym 5x5) | bi-level co-optimisation | large-budget controller re-learning on frozen bodies | — | 20 | differences between methods vanish after re-learning |
| Arza et al. 2024/25 (EvoGym part) | co-optimisation with cheap controller training | retrain controller of the best design | single-phase | 60 | two-phase better |
| Zhang S. 2026 (EvoGym 5x5) | reward-only co-design | screen top designs by restricted open-loop competence | — | 8 eligible runs | picks a different body at <= 0.10 reward cost (exploratory) |
| Xie et al. 2025 (EvoGym) | MAP-Elites structures | PPO controllers | — | none reported | protocol unclear in the text |

### 5.2 In 3D
| Study | Robots | Protocol | Compared with | n | Outcome |
|---|---|---|---|---|---|
| Cheney et al. 2016 | **voxel soft, 7^3, CPPN** | co-optimise X generations -> freeze body -> control only (and the converse) | full co-optimisation | 30 | body frozen after >= 25 generations loses nothing; diagnosis, not a method |
| Cheney et al. 2018 | **voxel soft, 5^3 and 10^3, CPPN** | interleaved (MIP), not staged | no protection; controller protection | 30 | MIP 31.95 vs 21.72 voxels |
| Kriegman et al. 2018 | voxel soft, 4x4x3 | development of body and control during life | no development | 30 | body development helps (25/30 vs 6/30) |
| Strgar & Kriegman 2025 | **voxel mass-spring, 6x6x4** | **controller first** (universal, pre-trained) -> body evolution with frozen controller -> fine-tuning | simultaneous co-design from scratch | 3 | staged faster; simultaneous shows diversity collapse; no tests |
| **Candiello et al. 2026** | **soft FEM; jumper on 7^3 hex grid; swimmer** | **shape+material under FIXED open-loop actuation (150 gen) -> actuation only (50 gen)** | joint optimisation, matched 10,000 calls | **1** | **joint better**: swimming loss -70.74 vs -62.64; jumping -7.97 vs -7.34 |
| SoftZoo 2023 | soft MPM | design-only with fixed controller; control-only; joint | each other | best-of-8 | joint 0.332 > design-only 0.152 > control-only 0.107 (swimmer) |
| Arza et al. 2024/25 | rigid (RoboGrammar, gym-rem) | cheap co-optimisation -> retrain best design's controller | single-phase | 60 | two-phase better |
| TAME 2021 | rigid | task-free body evolution -> controllers | task-supervised co-design | — | "matches" multi-task performance (abstract) |
| Gupta et al. 2021 | rigid UNIMAL | bi-level, controller from scratch per body | — | 3 | — |
| Nygaard et al. 2017 | rigid six-legged (sim + 3 real robots) | co-evolve -> lock body, reset and re-evolve control | the single co-evolutionary run | 20 co-evolution runs; phase 2 on 3 chosen bodies | two-phase > single run "by over 10%" |

### 5.3 Answer
- **Body-first under a fixed open-loop gait, then control on frozen bodies, has been run in 2D** (Mertan & Cheney 2024, as an analysis,
  n = 10, unmatched budget) and, task-free, in 2D by Talamini et al. 2021.
- **In 3D soft robots the only explicit sequential-vs-joint test I found is Candiello et al. 2026** (FEM, CMA-ES over an RBF embedding,
  open-loop actuation, matched budget) — and it found **joint better than sequential**, but with **one run per condition and no statistics**.
- **I found no study that evaluates a body-first protocol (fixed gait, with or without QD) against matched-budget co-evolution and/or MIP
  in 3D CPPN voxel soft robots with multiple seeds and a significance test.** The 3D voxel work is either diagnosis by freezing
  (Cheney 2016), interleaved protection (Cheney 2018), or controller-first staging (Strgar & Kriegman 2025).
- Limits of this "no": six extended web searches on staged / sequential / fixed-controller protocols, three arXiv API queries
  (one author feed and two keyword feeds; the API was rate-limited for the rest), and Semantic Scholar citation lists of
  arXiv:2402.09231 (21 citing papers), arXiv:2508.17464 (5) and Cheney 2018 (143 listed; about 8 of the 2021-2022 entries were not
  printed by the tool). GECCO/ALIFE 2026 companion papers without arXiv copies, theses, and the mechanical-design / topology-
  optimisation literature (where "sequential vs concurrent" comparisons are common) may be missed.

---

## 6. How this literature measures and reports (the bar to match)

| Paper | Runs per condition | Test | Plots | Budget per run |
|---|---|---|---|---|
| Cheney 2013 | 35 | p-values (test name not checked) | median, 95% bootstrap CI | pop 30 x 1000 gen |
| Cheney 2016 | 30 | Mann-Whitney | mean, 95% bootstrap CI (10,000 samples); top-10 run morphology strips | (50/25+25) x 5000 gen |
| Cheney 2018 | 30, seeds paired across treatments | Wilcoxon rank-sum | mean of best-of-run, 95% bootstrap CI; per-run lineage plots | pop 50 x 5000 gen |
| Kriegman 2018 | 30 | Mann-Whitney U | 95% (and 99%) bootstrap CI | pop 30 x 10,000 gen |
| Corucci 2018 | 15 (called a limitation by the authors) | Mann-Whitney U + Bonferroni | 95% bootstrap CI | 5000-9000 gen |
| Mertan & Cheney 2023 | 100 (main), 10 (side experiments) | Wilcoxon rank-sum | mean, 95% bootstrap CI; box plots of champions | pop 16 x 5000 gen |
| Mertan & Cheney 2024 EuroGP | 10 | Wilcoxon rank-sum | mean, 95% bootstrap CI; every champion plotted; t-SNE of bodies | pop 16 x 10,000 gen (+ 5,000 control-only) |
| Mertan & Cheney 2024 GECCO | 1 archive; 10 noisy evaluations; 357 unseen bodies | one-sample t-test; Wilcoxon rank-sum | scatter/box | 16 x 20,000 gen |
| Mertan & Cheney 2025 GECCO | 20 | Wilcoxon rank-sum | 95% CI | 20 x 10,000 gen, 5 evals each |
| Mertan & Cheney 2025/26 | 100 (10 for control-only) | Mann-Whitney U; t-distribution fit | champion distributions; 95% bootstrap CI | pop 20 x 10,000 gen |
| de Bruin et al. 2026 | 20 | Mann-Whitney U + Benjamini-Hochberg | box plots; mean with inter-quartile band | 200 bodies x 50 gen x 50 BO evals |
| Arza et al. 2024/25 | 60 | bootstrap 95% band (no named test) | mean curves | 8e6 simulation steps |
| Talamini et al. 2021 | 10 | Mann-Whitney U + Bonferroni | rank tables | 10,000 evals per controller run |
| Luo et al. 2022 | 10 | — (std bands; bootstrap CI for body traits) | mean +/- std | 30 gen |
| Gupta et al. 2021 | 3 evolutionary runs | Mann-Whitney U | 95% bootstrap CI | ~4,000 bodies x 5M steps |
| EvoGym 2021 | 6 (3 for the full suite) | none | mean with variance band | 250-750 robots x 1000 PPO iterations |
| MorphVAE 2024 / GNN 2026 / Strgar & Kriegman 2025 | 3 | Wilcoxon (MorphVAE) / none / none | mean +/- std or min-max | 1000 robots / 500-700 robots / GPU hours |
| AdaControl 2026 | 5 | two-tailed t-test | mean curves | 1000 robots |
| Candiello et al. 2026 | 1 | none | single curves | 10,000 simulator calls |

Reading: the evolutionary-robotics venues the project would target (GECCO, ALIFE, EuroGP, Artificial Life) expect **10-30 independent
runs per condition (20-30 is the Cheney-line norm; 100 where the simulator is cheap), a rank test (Mann-Whitney U = Wilcoxon rank-sum),
multiple-comparison correction when there are several arms, best-of-run fitness curves with 95% bootstrapped CIs, every run champion
shown, and pictures of champion bodies for the top-10 runs.** Paired seeds across treatments (Cheney 2018) and a "retrain from scratch"
control (Mertan & Cheney 2024) are the two design details reviewers from this line will look for. Three seeds is accepted only in the
RL co-design venues, and with a reported run-to-run spread of about 1.7x it would not support any claim here.

---

## 7. Open problems / future work as stated by the authors themselves

- **Cheney 2016**: repeat the freezing analysis for other encodings, neural and closed-loop controllers, diversity-focused EAs, harder
  tasks and other scales; vary where the morphology/control line is drawn.
- **Cheney 2018**: MIP beyond soft voxel robots (rigid, centralised control); developmental body-brain feedback as the longer-term answer.
- **Mertan & Cheney 2023**: 3D design spaces, harder tasks, closed-loop; bodies robust to control perturbation; modular control + MIP.
- **Mertan & Cheney 2024 (EuroGP)**: tasks matched to controller complexity; can body-centred / controller-free solutions scale to tasks
  that seem to need closed-loop control; better early estimates of a body's potential (surrogates, bandits, weight sharing).
- **Mertan & Cheney 2024 (GECCO)**: how QD behaves in brain-body co-optimisation (migrations are rare); 3D; real robots; compute comparison.
- **Mertan & Cheney 2025/26**: benchmark existing remedies on the mapped landscape; schedules, hyper-parameters, encodings;
  "more challenging design spaces, potentially utilizing different simulation engines"; how prevalent the goal-switching benefit is;
  why AFPO's better selection accuracy does not give better champions ("warrants further exploration").
- **Bhatia et al. 2021**: concurrent co-optimisation instead of bi-level, neuroevolution, morphogenetic development, gradient-based
  design, decentralised control, other encodings, multi-task.
- **Song et al. 2026 (AdaControl)**: do the findings hold for other body representations, tasks and physical platforms; control
  complexity beyond training length (architecture, algorithm).
- **Strgar & Kriegman 2025**: one material, one percept, one actuator type, one task; no sim-to-real; only one diversity metric.
- **Candiello et al. 2026**: closed-loop control; differentiable simulators or surrogates; fabrication.
- **de Bruin et al. 2026**: QD and better teacher selection; only a 5x5 grid with a simple encoding.
- **Corucci et al. 2018**: more repetitions and generations; a stronger EA (AFPO).

---

## 8. Gaps a one-workstation solo project could fill, and scoop risks

### Gaps
1. **The missing 3D test, done to the Cheney-line standard.** Body-first (fixed gait; with and without MAP-Elites) -> phase control on
   frozen bodies, against (a) co-evolution of body and per-voxel phase at matched evaluations and (b) the same with MIP (Cheney 2018),
   plus (c) plain fixed-gait CPPN-NEAT with the stage-2 budget spent on more generations. 20-30 paired seeds, Mann-Whitney U with
   correction. Both directions are publishable: 2D says staged helps (Mertan & Cheney 2024), the one 3D data point says joint wins
   (Candiello 2026, n = 1), and Mertan & Cheney 2025/26 predict a cost of full decoupling. Mertan & Cheney ask for 3D / other
   simulators in three papers.
2. **Why stage 2 does not beat stage 1.** Mertan & Cheney 2024 already saw the learnable controller fall below the fixed controller on
   fixed-evolved bodies in 3 of 4 settings, and the project sees 2.27 < 2.61. Nobody has explained this. Testable: warm-start stage 2 at
   the fixed gait (so it cannot regress), measure mutational fragility of fixed-gait champions (the "needle peak"), and sweep actuation
   frequency to show resonance tuning. Cheney 2016 evolved a global frequency "to resonate with the natural frequency" but never
   measured it.
3. **A small exhaustive 3D morphology-fitness landscape** (e.g. 2x2x2 or 3x3x2 voxels, open-loop phase control), repeating the
   undervaluation and selection-accuracy analysis of Mertan & Cheney 2025/26 in 3D with a different engine. Cheap with open-loop
   control (no controller training per body beyond a small phase search). This is exactly their stated future work, so it is also
   the item with the highest scoop risk.
   (Smaller alternative: a replication of MIP in an open 3D simulator. I did not search specifically for replications of the 2018
   result and none surfaced in the citation lists I read; Mertan & Cheney's own 2D re-implementation — a variant, as their footnote
   says — found MIP slightly worse than AFPO.)

### Scoop risks
- **Mertan & Cheney (Vermont)**: own the question; journal paper out Sep 2026; announced extension to harder design spaces and other
  simulators. No 2026 preprint found on this, but they are the most likely to publish a 3D follow-up.
- **Strgar & Kriegman (Northwestern)**: already have a 3D voxel staged pipeline (controller first) with far more compute; adding a
  body-first arm would be trivial for them.
- **Candiello / Katzschmann (ETH)**: already report sequential < joint in 3D soft robots; a reviewer will know it. Must be cited and
  the difference explained (n = 1, CMA-ES on a 57-147 parameter embedding, FEM).
- **Song, Yang, Yao et al. (AdaControl, MISCO, RoboLDA; Aug 2026)**: three preprints in one month on evaluation fidelity and "true
  potential" in EvoGym; a staged or fidelity-aware scheme from them is plausible, in 2D.
- **Zhang S. (Oct 2026)**: restricted open-loop competence as a body score in EvoGym — the same idea as "judge bodies under a fixed
  gait", in 2D, with pre-registered thresholds.
- **Oslo / Trieste (de Bruin, Glette, Ellefsen, Nadizar, Medvet; Arza)**: re-learning on frozen bodies and two-phase budgets; 2D soft
  and 3D rigid.

---

## 9. What I could not verify

- "MoMa" as an EvoGym co-design algorithm: not found.
- Le Goff & Hart 2021: only via AdaControl's reference list and its one-sentence description; PDF blocked.
- PreCo: the benchmark name and 2D/3D were not on the page I opened ("a modular soft robot system"; the same group's ModularEvoGym is
  2D, but its README does not mention PreCo). CuCo's seed counts and baselines were not extracted.
- LASeR, Harada & Iba, Liu et al. (action inheritance), Ferigo et al. 2025, Eiben & Hart 2020, Lehman & Stanley 2011, Nordmoen et al.
  2021: existence taken from reference lists of local full texts and/or Semantic Scholar citation lists; not opened individually.
- Bongard 2011: abstract only (no run counts). Medvet et al. 2021/2023: abstracts only (no run counts).
- Strgar & Kriegman: "ICLR 2026" comes from AdaControl's reference list and a search hit on the ICLR 2026 proceedings; the arXiv page
  itself names no venue.
- [H] items: numbers were extracted by the fetch tool's summariser, not read line by line. For three of them I asked a second time for
  verbatim sentences and they matched: Candiello et al. 2026 (150 + 50 vs 200 generations, 10,000 simulator calls, losses -70.74 vs
  -62.64 and -7.97 vs -7.34, no mention of seeds or statistics), Strgar & Kriegman 2025 (3D, 6x6x4 workspace, three independent
  trials, frozen controller in "zero-shot evolution", no test), Mertan & Cheney 2025 GECCO (2D EvoGym, 10-by-10 box, 20 repetitions,
  10,000 generations, Wilcoxon rank-sum).
- Cheney 2018 high-resolution numbers: which MIP variant gave 60.728 vs 43.340 is ambiguous in arXiv v2.
- A February 2026 TechRxiv preprint on evolved soft robots for extraterrestrial terrain (403; authors and method unknown).
- The web-search allowance for this session ran out before a last sweep of ALIFE 2026 / GECCO 2026 programme pages; that sweep was
  not done.
- arXiv:2609.29491 and 2609.29490 are returned by the arXiv API with a "published" date of 24 Aug 2026 despite the 2609 identifiers.

## 10. Main URLs

- Cheney 2016: https://meclab.w3.uvm.edu/papers/2016_ALife_Cheney.pdf
- Cheney 2018: https://arxiv.org/abs/1706.06133 ; https://doi.org/10.1098/rsif.2017.0937
- Mertan & Cheney 2023: https://arxiv.org/abs/2306.09358
- Mertan & Cheney 2024 (EuroGP): https://arxiv.org/abs/2402.09231 ; https://doi.org/10.1007/978-3-031-56957-9_3
- Mertan & Cheney 2024 (GECCO): https://arxiv.org/abs/2404.14625
- Mertan & Cheney 2024 (SAB): https://arxiv.org/abs/2407.16613
- Mertan & Cheney 2025 (GECCO): https://arxiv.org/abs/2504.06523
- Mertan & Cheney 2025/26: https://arxiv.org/abs/2508.17464 ; https://doi.org/10.1162/artl.a.476 ; https://doi.org/10.1162/isal.a.891
- Mertan & Cheney 2025 (MNIST): https://arxiv.org/abs/2508.17469
- Bongard 2011: https://doi.org/10.1073/pnas.1015390108
- Sims 1994: https://www.karlsims.com/evolved-virtual-creatures.html
- Kriegman 2018: https://arxiv.org/abs/1711.07387
- Talamini 2021: https://www.frontiersin.org/articles/10.3389/frobt.2021.673156/full
- de Bruin 2026: https://arxiv.org/abs/2604.12482 ; https://arxiv.org/abs/2605.15769
- Luo 2022: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2022.797393/full
- Luo 2023: https://arxiv.org/abs/2309.13099 ; Luo 2024: https://arxiv.org/abs/2403.19545
- Arza 2024: https://arxiv.org/abs/2409.08621
- Le Goff 2024: https://arxiv.org/abs/2403.10303
- Eguiarte-Morett & Aguilar: https://doi.org/10.1177/10597123231198497
- Gupta 2021: https://arxiv.org/abs/2102.02202 ; https://doi.org/10.1038/s41467-021-25874-z
- NGE: https://arxiv.org/abs/1906.05370 ; Transform2Act: https://arxiv.org/abs/2110.03659 ; EvoGym: https://arxiv.org/abs/2201.09863
- CuCo: https://iclr.cc/virtual/2023/poster/10693 ; PreCo: https://proceedings.mlr.press/v229/wang23b.html
- AdaControl: https://arxiv.org/abs/2608.23100 ; GNN co-design: https://arxiv.org/abs/2603.19582 ; MISCO: https://arxiv.org/abs/2609.29491
- Controller-restriction protocol: https://arxiv.org/abs/2610.07629 ; Morphology-control trade-off: https://arxiv.org/abs/2503.16127
- Sato 2024: https://arxiv.org/abs/2407.09270 ; SoftZoo: https://arxiv.org/abs/2303.09555
- Strgar 2024: https://arxiv.org/abs/2405.14712 ; Strgar & Kriegman 2025: https://arxiv.org/abs/2502.10862
- Candiello 2026: https://arxiv.org/abs/2603.06497
- TAME: https://arxiv.org/abs/2102.13100 ; LOKI: https://arxiv.org/abs/2505.21665 ; Stackelberg PPO: https://arxiv.org/abs/2603.15388
- Survey: https://arxiv.org/abs/2512.04770
- Medvet lab pages: https://medvet.inginf.units.it/publications/2021-c-mpbr-biodiversity/ ;
  https://medvet.inginf.units.it/publications/2023-j-pmbr-factors/ ; https://medvet.inginf.units.it/publications/2023-c-pcm-morphology/ ;
  https://medvet.inginf.units.it/publications/2025-j-mln-quality/
