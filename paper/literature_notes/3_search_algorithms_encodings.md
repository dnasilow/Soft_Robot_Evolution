# Literature survey 3 — Search algorithms and encodings for evolving soft-robot (and robot) morphology, 2013-2026

Compiled 18 November 2026. Scope: search algorithms (quality-diversity, AFPO, plain EAs), encodings, 2023-2026 frontier (differentiable, generative, LLM), statistical practice, gaps.

## How to read these notes

- **Verification tags.** Every entry carries one of:
  - `[FULL TEXT]` — I read the paper text (local extracted text in `C:\SoftRobotEvolution\research_reference\extracted\`, or the author-hosted PDF/arXiv HTML fetched during this survey). Numbers quoted (runs, tests, descriptors) come from that text.
  - `[ABSTRACT]` — I opened the arXiv abs page / publisher or author publication page and confirmed title, authors, venue and abstract only. Details beyond the abstract are not checked.
  - `[SEARCH ONLY]` — confirmed to exist via search-result metadata (title/authors/venue/DOI) but no page with the abstract was read. Treat details as provisional.
  - `UNVERIFIED` — a specific field (venue, number, claim) that I could not confirm; stated explicitly.
- Abstract summaries are paraphrases, not quotations.
- "Runs" = independent evolutionary runs (seeds) per condition.

---

## A. Quality-diversity and diversity-driven search applied to morphology

### A1. Mouret & Clune 2015 — MAP-Elites (includes the Cheney-2013 soft-robot domain) `[FULL TEXT, local]`
- **Citation.** Mouret, J.-B., Clune, J. "Illuminating search spaces by mapping elites." arXiv:1504.04909 (preprint, 20 Apr 2015).
- **URL.** https://arxiv.org/abs/1504.04909 ; local text `MAP-Elites_Mouret_Clune_2015.txt`.
- **What it did.** Introduces MAP-Elites. Three domains: modular neural networks, **simulated soft-robot morphologies (the same domain as Cheney et al. 2013: VoxCad, 10x10x10, four materials, CPPN encoding, fitness = distance)**, and a real soft arm. In the soft-robot domain the CPPNs are evolved in Sferes (NEAT-style mutation, *no crossover and no speciation*).
- **Morphology descriptors.** (1) percentage of voxels that are bone (stiff material), (2) percentage of voxels filled. Map resolution 128 x 128.
- **Controls.** "EA" (single-objective, implemented in NSGA-II) and "EA+D" (fitness + diversity in the same feature space, NSGA-II); same number of evaluations as MAP-Elites.
- **Runs / statistics.** 10 runs launched per treatment, but only 7 (EA), 5 (EA+D) and 8 (MAP-Elites) had finished and are reported; the paper itself calls the data preliminary. p-values are reported (test not re-checked by me).
- **Findings in the soft-robot domain.** MAP-Elites has significantly higher *global reliability* and *coverage* (p < 0.002). **For *global performance* (single best solution) MAP-Elites has a higher median but "no significant difference" from EA and EA+D (p > 0.05).** MAP-Elites is significantly *worse* in *precision* (p < 0.01). The authors note a "long, skinny island" of one-voxel-wide sheet organisms that exploit a simulator quirk.
- **Relevance.** This is the direct precedent for the project: same domain, same encoding family, MAP-Elites vs. objective-based EA. The founding paper already reports "better map, champion statistically indistinguishable" — but with unequal, small run counts, without speciation in either arm, and without AFPO. The project's finding ("CPPN-NEAT with speciation gives the better champion and is ~3x more sample-efficient; MAP-Elites gives the better population") refines rather than contradicts it. Also note the abstract's stronger general claim that MAP-Elites "tends to find a better overall solution" is *not* supported by the soft-robot experiment in the same paper.

### A2. Lehman & Stanley 2011 — Novelty search with local competition (NSLC) `[FULL TEXT]`
- **Citation.** Lehman, J., Stanley, K.O. "Evolving a diversity of virtual creatures through novelty search and local competition." GECCO 2011, pp. 211-218. DOI 10.1145/2001576.2001606.
- **URL.** https://groups.csail.mit.edu/EVO-DesignOpt/gecco2011Proceedings/proceedings/p211.pdf
- **What it did.** Sims-style rigid virtual creatures (ERO system); NSGA-II-based multi-objective search with four setups: fitness only; novelty only; novelty + global competition; novelty + local competition (NSLC).
- **Morphology descriptors (niche space).** Three dimensions: **height, mass, number of active joints** (rescaled; height 0-1.5 m, mass 0-3 kg, 1-4 active joints). Novelty = squared Euclidean distance in this space; k = 15 nearest neighbours.
- **Runs / statistics.** Population 1,000; 500 generations; **15 runs** per setup. Kruskal-Wallis across the four setups, then pairwise Mann-Whitney U.
- **Findings.** *Maximum fitness:* novelty + **global** competition is significantly best (p < 0.001); **fitness-only and local competition are not significantly different**; novelty-only is worst. *Niche coverage:* local competition and novelty-only best. *Niche exploitation:* local competition significantly best. The paper states the trade-off explicitly: local competition maintains and exploits diversity "albeit at a cost in absolute performance" relative to global competition.
- **Relevance.** Earliest published evidence, in morphology search, that local competition (the core QD mechanism) buys diversity but not a better champion. Directly supports the project's headline.

### A3. Methenitis, Hennes, Izzo, Visser 2015 — Novelty search in the Cheney-2013 soft-robot system `[FULL TEXT]`
- **Citation.** Methenitis, G., Hennes, D., Izzo, D., Visser, A. "Novelty Search for Soft Robotic Space Exploration." GECCO 2015, pp. 193-200. DOI 10.1145/2739480.2754731.
- **URL.** https://ir.cwi.nl/pub/23805 (PDF https://ir.cwi.nl/pub/23805/23805D.pdf)
- **What it did.** Same substrate as the project: VoxCad, CPPN-NEAT (HyperNEAT package, parameters as Cheney 2013), four materials. Replaces fitness by novelty; compares novelty search, fitness search, random search (all CPPN-NEAT) and a direct-encoded simple GA (GAlib); adds "fitness elitism" to novelty search; repeats at Moon/Mars/Earth/Jupiter gravity.
- **Behaviour descriptors tried for novelty (10 types).** 3D trajectory, 2D trajectory, pace, **voxels touching the ground (VTG)**, pressure, kinetic energy, and the DFT of the 1-D signals. Trajectory descriptors gave the best champion fitness; **VTG and DFT-VTG performed worst** ("does not hold any information as to how fast the robot is moving").
- **Runs / statistics.** **10 runs** per experiment; population 30; up to 1,000 generations; lattices 5^3, 7^3 and 10^3 (not all experiments at 10^3 because of cost). Results are shown as means with deviation bands and box plots; **I found no formal significance test in the text.**
- **Findings.** Novelty search equal or better than fitness search in champion displacement in all experiments; on the 10^3 lattice the advantage is smaller (> 1 body length on average) and both methods reached the same best individual (~14 body lengths). Novelty + fitness elitism improved further. Gravity shaped the outcome: at low gravity hopping dominates; "legged locomotion starts to become favourable" at higher gravity. They also remark that defining behaviour by *morphology* has "failed" in earlier work and argue that only observed behaviour should drive novelty.
- **Relevance.** The closest prior study of a diversity-driven search on exactly the Cheney system. It reports the opposite sign from the project (diversity search >= fitness search on the champion) — but with 10 runs, population 30 and no test. Must be cited and discussed. Also evidence that a ground-contact descriptor is a poor *novelty* signal, and that environment (gravity) changes whether legs appear.

### A4. Nordmoen, Veenstra, Ellefsen, Glette 2021 — MAP-Elites for modular robots `[FULL TEXT via ar5iv]`
- **Citation.** Nordmoen, J., Veenstra, F., Ellefsen, K.O., Glette, K. "MAP-Elites Enables Powerful Stepping Stones and Diversity for Modular Robotics." Frontiers in Robotics and AI 8:639173 (2021). DOI 10.3389/frobt.2021.639173. arXiv:2012.04375.
- **URL.** https://arxiv.org/abs/2012.04375 ; https://www.frontiersin.org/article/10.3389/frobt.2021.639173
- **What it did.** Rigid modular robots (REM framework on PyBullet, up to 20 modules, tree-based *direct* encoding, decentralised sine-wave controllers). Compares a single-objective EA, NSGA-II with a diversity objective, and MAP-Elites; then transfers populations to harder environments; genealogical "stepping stone" analysis.
- **Morphology descriptors.** Number of non-movable modules x number of movable (joint) modules.
- **Runs / statistics.** **30 repetitions** per algorithm, 100,000 evaluations; Mann-Whitney U with Holm correction; 95 % confidence intervals.
- **Findings.** MAP-Elites reached the **highest best fitness** (significant against both others) *and* the most morphological diversity, and recovered best after environment change.
- **Relevance.** The main published counter-example to "plain EA beats MAP-Elites on the champion". Differences from the project that may explain the sign: direct encoding, 100k evaluations (11x the project's budget), rigid modules, a size-type descriptor. Also the model for the statistical bar (30 runs, MWU + Holm).
- **Precursor.** Nordmoen et al., "Quality and Diversity in Evolutionary Modular Robotics", arXiv:2008.02116 (2020) `[ABSTRACT]` — same three algorithm classes; "all three algorithms evolved high-performing individuals", MAP-Elites best at filling niches. (IEEE SSCI 2020 venue is UNVERIFIED — the arXiv page lists no venue.)

### A5. Zardini, Zappetti, Zambrano, Iacca, Floreano 2021 — QD for soft tensegrity modular robots `[FULL TEXT via ar5iv]`
- **Citation.** "Seeking Quality Diversity in Evolutionary Co-design of Morphology and Control of Soft Tensegrity Modular Robots." GECCO 2021. DOI 10.1145/3449639.3459311. arXiv:2104.12175.
- **URL.** https://arxiv.org/abs/2104.12175
- **What it did.** Chains of up to 10 tensegrity modules with NN controllers; goal-reaching and squeezing tasks. Compares MAP-Elites, ViE-NEAT (viability evolution) and Double-Map MAP-Elites (DM-ME: separate maps for morphology and controller).
- **Descriptors.** Morphology: number of modules, module stiffness. Controller: PCA of head-module trajectory. Plain MAP-Elites uses the 4-D concatenation (8,100 cells); DM-ME two 90-cell maps.
- **Runs / statistics.** **10 runs**, 45,000 evaluations; Wilcoxon rank-sum, alpha = 0.05.
- **Findings.** Goal reaching: ViE-NEAT (mean 26.21) and DM-ME (25.76) beat MAP-Elites (22.16) on best fitness; ViE-NEAT vs MAP-Elites significant (p = 0.034). Squeezing: best fitness statistically equivalent. DM-ME best on QD-score in both tasks.
- **Relevance.** Published case where a non-QD (NEAT-based) method significantly beats plain MAP-Elites on the champion for soft-robot co-design; and evidence that a high-dimensional single archive hurts.

### A6. Medvet, Bartoli, Pigozzi, Rochelli 2021 — Biodiversity in evolved VSRs `[FULL TEXT, author PDF]`
- **Citation.** "Biodiversity in Evolved Voxel-based Soft Robots." GECCO 2021 (best paper, complex systems track per author page). DOI 10.1145/3449639.3459315.
- **URL.** https://medvet.inginf.units.it/publications/2021-c-mpbr-biodiversity/
- **Correction to the task brief:** this paper does **not** use MAP-Elites. The three EAs are CMA-ES, a GA, and a new NEAT-inspired "speciated evolver" (SE) that clusters the population with k-means (k = 10) on genotype (SE-g), **shape features (SE-s)** or **behaviour features (SE-b)**.
- **System.** 2D VSRs (2D-VSR-Sim), 5x5 body grid, direct morphology encoding, distributed neural controller (heterogeneous vs homogeneous weights).
- **Shape/behaviour characterisation.** Shape = 16x16 "dynamic pose" (long-exposure occupancy) -> classes **Blob / Legged / Other** via a random forest trained on 5,200 hand-labelled robots; behaviour = centre-of-mass FFT + **ground-contact "footprint" n-grams** -> Idle / Galloping / Crawling / Vibrating. Diversity = inverse Simpson index over species.
- **Runs / statistics.** **10 runs** per EA x representation, 30,000 evaluations; Mann-Whitney U.
- **Findings.** SE variants gave both the highest velocity and the highest diversity; plain GA and CMA-ES collapsed to one species; no trade-off between diversity and effectiveness. The fastest robots were Legged/Crawling, then Blob/Vibrating. (Abstract says representation matters more than the EA; the conclusion section says the EA matters more — the journal version below settles on "EA and environment matter more".)
- **Relevance.** Closest published analogue of the project's "blob vs limbed" question, including an explicit Blob/Legged classifier and a ground-contact behaviour descriptor. In 2D with a closed-loop controller, legged shapes *did* appear and were the fastest.

### A7. Pigozzi, Medvet, Bartoli, Rochelli 2023 — Factors impacting diversity and effectiveness `[FULL TEXT, author PDF]`
- **Citation.** "Factors Impacting Diversity and Effectiveness of Evolved Modular Robots." ACM Transactions on Evolutionary Learning and Optimization 3(1), 2023, pp. 1-33. DOI 10.1145/3587101.
- **URL.** https://medvet.inginf.units.it/publications/2023-j-pmbr-factors/ ; code https://github.com/pigozzif/FactorsImpactingModularRobots
- **What it did.** Journal extension of A6: 10x10 body grid; two morphology encodings (direct vs Gaussian-mixture "GMM"); six EAs (**ES, GA, SE-g, SE-s, SE-b and MAP-Elites**); three terrains (flat, downhill 30 deg, uphill 20 deg).
- **MAP-Elites descriptors.** **[number of voxels, elongation, compactness]**, 10 bins each (10^3 cells), 20 parents per iteration, 30,000 evaluations. Elongation = focal distance / major axis of the smallest enclosing ellipse; compactness = voxels / convex-hull area.
- **Shape classes.** Blob, **Limbed**, Elongated, Other; behaviour classes Jumping, Walking, Rolling, Other (16 species).
- **Runs / statistics.** **10 runs** per condition; two-sided Mann-Whitney U at 0.05.
- **Findings.** All EAs evolve effective robots; SE variants and MAP-Elites give the most diversity; MAP-Elites has "slightly lower effectiveness", which the authors attribute to its incentive to fill cells; "the EA impacts diversity a lot, while the same is not true for effectiveness". Direct encoding yields more knotty shapes with protrusions usable as limbs and more Walking; GMM yields rounder, more compact bodies. Selection pushes toward more compact, more elongated and smaller bodies under both encodings. **Terrain changes the dominant shape: downhill favours Blob/Rolling, uphill favours Elongated.**
- **Relevance.** The single most relevant precedent for the project's shape-descriptor MAP-Elites (elongation/compactness archive on voxel robots) and for the claim that the encoding and the environment, more than the search algorithm, decide whether limbed bodies appear. The project's 3D, open-loop, CPPN setting is still not covered.

### A8. Ferigo, Soros, Medvet, Iacca 2022 — MAP-Elites vs ES on VSR body+brain `[FULL TEXT, author PDF]`
- **Citation.** "On the Entanglement between Evolvability and Fitness: an Experimental Study on Voxel-based Soft Robots." ALIFE 2022. DOI 10.1162/isal_a_00493.
- **URL.** https://medvet.inginf.units.it/publications/2022-c-fsmi-entanglement/
- **What it did.** 2D VSRs with an **open-loop sinusoidal controller** (per-voxel frequency/phase), hilly terrain; ES vs MAP-Elites; four representations (direct/indirect x brain-only/body+brain; indirect = Gaussian mixture).
- **Descriptors.** Body: width and height of the enclosing grid. Behaviour: **ground-contact spectra** — ratio of 0-2 Hz to 0-5 Hz energy of the contact signals of the back and front halves.
- **Runs / statistics.** **10 runs**, 25,000 evaluations; Mann-Whitney U with Bonferroni correction.
- **Findings.** For body+brain, the direct representation reached 2-2.5x the velocity of the indirect one; with the indirect representation the EA made no difference. Fitness maps depend mostly on representation, evolvability maps on the EA. The abstract adds that MAP-Elites is "particularly effective" for simultaneous body-brain evolution.
- **Relevance.** Open-loop VSR control + body descriptors + ground-contact descriptors — the nearest 2D analogue of the project's descriptor pair (COM height x bounce / contact).

### A9. Mertan & Cheney 2023-2026 — MAP-Elites and AFPO on Evolution Gym voxel robots
All by Alican Mertan and Nick Cheney (University of Vermont).
- **(a) "Modular Controllers Facilitate the Co-Optimization of Morphology and Control in Soft Robots."** GECCO 2023. arXiv:2306.09358, DOI 10.1145/3583131.3590416. `[ABSTRACT]` — modular controllers are more robust to body mutations than global ones, giving more successful morphological mutations and better evolved robots. https://arxiv.org/abs/2306.09358
- **(b) "Investigating Premature Convergence in Co-optimization of Morphology and Control in Evolved Virtual Soft Robots."** EuroGP 2024. arXiv:2402.09231. `[FULL TEXT, local: Mertan_Cheney_2024.txt]` — uses **AFPO**, population 16, 10,000 generations, **10 runs**, Wilcoxon rank-sum, 95 % bootstrapped CIs. Finds high-performing morphologies that co-optimisation misses but morphology-only optimisation with a fixed controller finds. https://arxiv.org/abs/2402.09231
- **(c) "Towards Multi-Morphology Controllers with Diversity and Knowledge Distillation."** GECCO 2024 (EML track). arXiv:2404.14625. `[ABSTRACT]` — MAP-Elites produces many single-morphology teacher controllers which are distilled into one multi-morphology controller. https://arxiv.org/abs/2404.14625
- **(d) "No-brainer: Morphological Computation driven Adaptive Behavior in Soft Robots."** SAB 2024. arXiv:2407.16613. `[FULL TEXT, local: No_brainer.txt]` — MAP-Elites with a **7-D archive**: three morphology dimensions (number of active voxels, sensory voxels, total voxels; 4 bins each) plus four behaviour dimensions; 3,000 generations, 16 parents per generation chosen uniformly; 10 runs. https://arxiv.org/abs/2407.16613
- **(e) "Controller Distillation Reduces Fragile Brain-Body Co-Adaptation and Enables Migrations in MAP-Elites."** GECCO 2025 (Complex Systems track). arXiv:2504.06523. `[FULL TEXT via arXiv HTML]` — EvoGym Walker-v0, 10x10 bounding box; MAP-Elites archive = **total voxels x active (muscle) voxels**, 10x10 = 100 niches; **20 runs**, 10,000 generations; Wilcoxon rank-sum (p = 0.05). Fragile co-adaptation blocks migration between morphological niches; periodically replacing controllers with a distilled generalist ("Pollination") increases migrations and improves total and maximal quality. No comparison with a non-QD algorithm. https://arxiv.org/abs/2504.06523
- **(f) "Evolutionary Brain-Body Co-Optimization Consistently Fails to Select for Morphological Potential."** Accepted in *Artificial Life* (journal); extension of an ALIFE 2025 conference paper. arXiv:2508.17464 (v2 dated 12 Aug 2026). `[FULL TEXT, local: Morphological_potential_2025.txt]` https://arxiv.org/abs/2508.17464
  - Exhaustively maps a morphology-fitness landscape of **1,305,840** EvoGym voxel morphologies (controller trained for each), then runs **AFPO, MAP-Elites and MIP (morphological innovation protection, Cheney 2018)** on it.
  - Settings: 10,000 generations; AFPO/MIP population 20 with one random injection per generation; MAP-Elites archive of 28 cells over (number of active voxels, number of passive voxels); 50 % brain / 50 % body mutations; no crossover.
  - **100 independent runs per algorithm; Mann-Whitney U.**
  - **Result: run-champion fitness of AFPO and MAP-Elites is statistically indistinguishable (p >> 0.05); the paper concludes that explicit morphological niching "does not lead to good stepping stones for a better run champion". Near-optimal morphology found in 17/100 (AFPO), 22/100 (MAP-Elites), 13/100 (MIP) runs.** MAP-Elites more often ends on a local maximum of the morphology landscape (62 vs 22 for AFPO), but all three frequently stop one voxel-mutation away from a better body because new bodies are under-valued.
- **Relevance.** (f) is the strongest and most recent head-to-head of AFPO vs MAP-Elites on voxel-robot morphology and the **main scoop risk** for a "which algorithm gives the better champion" paper: 100 runs, exhaustive ground truth. What it does *not* contain: 3D bodies, CPPN-NEAT with speciation, open-loop actuation, shape descriptors (elongation/fill), parent-selection variants, sample-efficiency curves, or any analysis of limbed vs compact shapes.

### A10. Medvet, Lippolis, Nadizar 2025 — QD for composite (body+brain) solutions `[FULL TEXT, author PDF]`
- **Citation.** "Quality-Diversity in Problems with Composite Solutions: a Case Study on Body-Brain Robot Optimization." Genetic Programming and Evolvable Machines, 2025. DOI 10.1007/s10710-025-09520-x.
- **URL.** https://medvet.inginf.units.it/publications/2025-j-mln-quality/
- **What it did.** Formalises "QD composite problems"; compares 11 EAs (GA; MAP-Elites with body, brain, behaviour or body+brain descriptors; multi-archive MAP-Elites; five variants of a new co-evolutionary MAP-Elites, CoME) on two-wheeled differential-drive robot navigation (body = 9 real parameters; **not** voxel morphology).
- **Runs / statistics.** **30 runs** per EA per problem (8 problems), ~50,000 evaluations; Wilcoxon test, alpha = 0.01.
- **Findings.** Differences in best-fitness between EAs are "negligible"; the only consistently worse method is MAP-Elites with the 4-D body+brain archive. Two-archive variants (MAME, CoME) are best on the QD indexes.
- **Relevance.** Again: QD does not buy a better champion; one large joint archive is harmful; diversity must be enforced per part.

### A11. Le Goff, Smith, Hart 2026 — Superquadrics vs CPPN x EA vs MAP-Elites `[FULL TEXT via arXiv HTML]`
- **Citation.** "Generation of Diverse and Functional Robot Designs using Superquadrics Parametrisation and Quality-Diversity." arXiv:2606.11037 (9 June 2026); arXiv comment: accepted at PPSN 2026.
- **URL.** https://arxiv.org/abs/2606.11037
- **What it did.** ARE-style robots (free-form chassis in an 11^3 voxel grid plus wheels, joints, sensors), homeokinetic controller. 2x2 design: chassis encoding (superquadrics + CPPN vs dual CPPN) x algorithm (steady-state EA vs MAP-Elites with uniform parent selection).
- **Descriptors.** 6-D archive: number of wheels, joints, sensors; chassis height, depth, width.
- **Runs / statistics.** **20 runs** per variant and environment, 10,000 designs per run; Mann-Whitney U (p < 0.001) with **Cliff's delta** effect sizes.
- **Findings.** Superquadrics + MAP-Elites highest coverage and QD-score. **Maximum fitness similar across variants; MAP-Elites did not raise the best score** (slightly lower with superquadrics). The authors note that CPPN searches converge quickly to one robot type.
- **Relevance.** A 2026 "encoding x algorithm" factorial in morphology search with nearly the project's evaluation budget (10k) — methodologically the closest recent template, and a partial scoop of the "QD gives population, not champion" message for rigid robots.

### A12. Other QD / diversity work on morphology (shorter entries)
- **Nadizar, Medvet, Wilson 2025.** "Enhancing Adaptability in Embodied Agents: a Multi-Quality-Diversity Approach." IEEE TEVC. DOI 10.1109/TEVC.2025.3596746. `[ABSTRACT]` — co-optimises body and brain with diversity kept on several axes (body, brain, behaviour) at once; reports better performance and zero-shot transfer to 18 new tasks. https://medvet.inginf.units.it/publications/2025-j-nmw-enhancing/
- **Nadizar, Rusin, Medvet, Ochoa 2025.** "The Role of Stepping Stones in MAP-Elites: Insights from Search Trajectory Networks." EuroGP 2025. DOI 10.1007/978-3-031-89991-1_14. `[ABSTRACT]` — MAP-Elites vs GA on robot navigation with three controller representations; clearer stepping stones in MAP-Elites, especially with direct/local representations. (Controllers, not morphology.) https://medvet.inginf.units.it/publications/2025-c-nrmo-role/
- **Ludwig, Espeseth, Medvet 2025.** "Trace-Elites: better Quality-Diversity with Multi-Point Descriptors." EvoApplications 2025. DOI 10.1007/978-3-031-90062-4_21. `[ABSTRACT]` — a solution occupies a trail of cells instead of one. https://medvet.inginf.units.it/publications/2025-c-lem-trace/
- **Veenstra, Olsen, Glette 2022.** "Effects of encodings and quality-diversity on evolving 2D virtual creatures." GECCO Companion 2022, pp. 164-167. DOI 10.1145/3520304.3529053. `[SEARCH ONLY — citation page read, abstract not available]` https://www.mn.uio.no/ifi/english/people/aca/kyrrehg/publications/veenstra-gecco2022-abstract.html
- **Medina, Richey, Mueller, Schrum 2023.** "Evolving Flying Machines in Minecraft Using Quality Diversity." GECCO 2023. arXiv:2302.00782. `[ABSTRACT]` — MAP-Elites finds working voxel machines much more reliably than fitness-only evolution *if the behaviour characterisation is appropriate*. https://arxiv.org/abs/2302.00782
- **Xie, Pinskier, Liow, Howard, Iida 2024.** "A 'MAP' to find high-performing soft robot designs: Traversing complex design spaces using MAP-elites and Topology Optimization." arXiv:2407.07591. `[FULL TEXT header, local: MAP_topology_optimization.txt]` — MAP-Elites evolves void regions of the design domain, topology optimisation refines each design; soft grippers; Kruskal-Wallis + Bonferroni. Publication venue UNVERIFIED. https://arxiv.org/abs/2407.07591
- **Daly et al. 2023.** "Robustness for Free: Quality-Diversity Driven Discovery of Agile Soft Robotic Gaits." arXiv:2311.01245 (submitted to IEEE RoboSoft). `[ABSTRACT]` — QD gait repertoires for a soft tensegrity robot are more robust than single-objective gaits (gaits, not morphology). https://arxiv.org/abs/2311.01245
- **Gaier, Asteroth, Mouret 2019.** "Are quality diversity algorithms better at generating stepping stones than objective-based search?" GECCO Companion 2019, pp. 115-116. `[SEARCH ONLY]` — image-recreation domain; QD far better. https://pub.h-brs.de/frontdoor/index/index/year/2019/docId/4545
- **Thomson, Le Goff, Hart, Buchanan 2024.** "Understanding fitness landscapes in morpho-evolution via local optima networks." arXiv:2402.07822 (arXiv comment: submitted to GECCO 2024). `[ABSTRACT]` — local-optima-network analysis of three morphology encodings. https://arxiv.org/abs/2402.07822

### A13. Morphological descriptor sets used in the literature (summary table)

| Source | System | Descriptors |
|---|---|---|
| Lehman & Stanley 2011 | rigid virtual creatures | height, mass, number of active joints |
| Mouret & Clune 2015 | 3D voxel soft robots (Cheney domain) | % bone voxels, % voxels filled |
| Methenitis et al. 2015 | 3D voxel soft robots | behaviour only: 2D/3D trajectory, pace, voxels touching ground, pressure, kinetic energy (+DFTs) |
| Miras et al. 2018 (EvoApplications) | modular robots | Branching, **Limbs**, Length of Limbs, Coverage, Joints, Proportion, **Symmetry**, Size |
| Nordmoen et al. 2021 | modular robots | number of non-movable modules, number of joint modules |
| Zardini et al. 2021 | tensegrity soft modules | number of modules, stiffness (+ PCA of trajectory for controller) |
| Medvet et al. 2021 | 2D VSR | 16x16 dynamic-pose occupancy; classes Blob/Legged/Other; ground-contact footprints |
| Ferigo et al. 2022 | 2D VSR | bounding-box width, height; ground-contact spectra front/back |
| Pigozzi et al. 2023 | 2D VSR | number of voxels, **elongation**, **compactness**; classes Blob/Limbed/Elongated/Other |
| Mertan & Cheney 2024-2026 | EvoGym 2D VSR | number of active / passive / sensory / total voxels |
| Le Goff et al. 2026 | ARE rigid robots | number of wheels, joints, sensors; chassis height, depth, width |
| Gravina et al. 2018, 2019 | 3D voxel soft robots (Cheney domain) | structure: % filled, % bone; behaviour: sampled trajectory (used for novelty / surprise) |
| Corucci et al. 2018 (analysis only, not search) | 3D voxel soft robots | global symmetry index; branching index 1 - V/V_hull; curvature-entropy complexity |

Observations: (i) composition/size descriptors dominate; (ii) explicit "number of limbs" and "symmetry" descriptors exist as search dimensions only in the modular-robot line (Miras et al.); for 3D voxel robots Corucci et al. 2018 define a symmetry index and a branching index but use them only to analyse evolved bodies — as far as I could find, neither has been used as a MAP-Elites dimension for voxel soft robots; (iii) ground contact has been used as a *behaviour* descriptor (Methenitis: poor for novelty; Medvet/Ferigo: footprints/spectra) but **I found no study that uses the number of separate ground-contact patches as an archive dimension**.

### A14. Gravina, Liapis, Yannakakis 2017-2019 — divergent search and MAP-Elites selection in the Cheney soft-robot domain (important; not in the task brief)
All three use VoxCad + CPPN-NEAT, four materials, the Cheney 2013 / Methenitis 2015 parameters.
- **(a) "Exploring Divergence in Soft Robot Evolution."** GECCO 2017 Companion (2 pages). DOI 10.1145/3067695.3076072. `[FULL TEXT, author PDF]` https://antoniosliapis.com/papers/exploring_divergence_in_soft_robot_evolution.pdf — 5^3 lattice, **30 runs**. Champion distance (median body lengths): surprise search 10.77, novelty search 10.61, **objective search 6.26**; both divergent methods significantly better.
- **(b) "Fusing Novelty and Surprise for Evolving Robot Morphologies."** GECCO 2018, pp. 93-100. DOI 10.1145/3205455.3205503. `[FULL TEXT, author PDF]` https://antoniosliapis.com/papers/fusing_novelty_and_surprise_for_evolving_robot_morphologies.pdf
  - Objective search (OS) vs novelty search (NS) vs surprise search (SS) vs novelty-surprise search (NSS); behaviour characterisation = the robot's sampled **trajectory**; eight lattice resolutions 3^3 ... 10^3; population 30, 1,000 generations (30,000 evaluations per run).
  - **90 independent runs** per algorithm per resolution; two-tailed Mann-Whitney U at 5 %, Bonferroni correction; 95 % confidence intervals; ANCOVA on regression intercepts.
  - Table 1 (mean champion distance in body lengths, 10x10x10): **OS 9.29, NS 11.32, SS 11.18, NSS 12.05**; the same ordering holds at all eight resolutions. The authors conclude that the problem "is deceptive" because objective search never matches the divergent methods, and that objective-search robots are structurally more similar to each other.
  - Structural diversity was analysed post hoc in the Mouret-Clune feature space (% filled, % bone).
- **(c) "Blending Notions of Diversity for MAP-Elites."** GECCO 2019 Companion (2 pages). DOI 10.1145/3319619.3321987. `[FULL TEXT, author PDF]` https://www.antoniosliapis.com/papers/blending_notions_of_diversity_for_map_elites.pdf
  - 5^3 lattice; MAP-Elites with a 32x32 grid over the structural descriptors (% filled, % bone voxels among filled), batch of 1,024 offspring per iteration with NEAT crossover/mutation.
  - Baseline MAP-Elites selects parents **uniformly**; four variants bias **parent selection** by novelty and/or surprise computed on the *trajectory* descriptor ("multi-behaviour characterisation").
  - **10 runs**; two-tailed Mann-Whitney U, p < 0.05. All four selection-biased variants reached significantly higher *global performance* (best fitness) than uniform MAP-Elites within 300,000 evaluations (best variant 12.80 +/- 2.70 vs 8.38 +/- 0.70 body lengths); QD-score differences were not significant; coverage was the same.
- **Relevance.** This line is the strongest published evidence *against* a naive reading of the project's result. With 90 runs, plain objective CPPN-NEAT is beaten on the champion by trajectory-based novelty search at 30k evaluations, including at 10^3. And (c) is the only prior study of **parent selection in MAP-Elites for soft-robot morphology** — it reports that plain uniform MAP-Elites with structural descriptors is weak on the champion (8.38 after 300k evaluations, i.e. no better than objective search after 30k in (b)) and that biasing selection fixes this. The project's pilot ("fitness-biased selection helped MAP-Elites") agrees in direction; the novelty would be the selection signal (fitness / curiosity rather than trajectory novelty), the 10^3 scale, the small budget, and a proper number of seeds. Any GECCO reviewer from this community will expect these three papers to be cited.

### A15. Joachimczak, Suzuki, Arita 2015 — novelty search for developmental soft-bodied robots `[SEARCH ONLY]`
- "Improving Evolvability of Morphologies and Controllers of Developmental Soft-Bodied Robots with Novelty Search." Frontiers in Robotics and AI 2:33 (2015). DOI 10.3389/frobt.2015.00033. https://www.frontiersin.org/articles/10.3389/frobt.2015.00033/full
- Search-result summary: novelty search gave significantly better solutions than fitness-driven search for co-evolved developmental soft bodies. Details not read.
- Companion: "Artificial Metamorphosis: Evolutionary Design of Transforming, Soft-Bodied Robots", Artificial Life 22(3), 2016 `[SEARCH ONLY]`.

### A16. Miras et al. — morphological descriptors, selection preferences and encoding bias in modular robots
- **Miras, Haasdijk, Glette, Eiben 2018a.** "Search Space Analysis of Evolvable Robot Morphologies." EvoApplications 2018, LNCS 10784, pp. 703-718. DOI 10.1007/978-3-319-77538-8_47. `[FULL TEXT, author PDF]` https://research.vu.nl/en/publications/search-space-analysis-of-evolvable-robot-morphologies/ — defines **eight descriptors: Branching, Limbs, Length of Limbs, Coverage, Joints, Proportion, Symmetry, Size**; novelty search in this 8-D space (population 500, 100 generations); direct vs generative (L-system) encoding showed no significant difference in diversity; strong bias toward bodies with few, long limbs.
- **Miras, Haasdijk, Glette, Eiben 2018b.** "Effects of Selection Preferences on Evolved Robot Morphologies and Behaviors." ALIFE 2018, pp. 224-231. `[FULL TEXT, author PDF]` https://mn.uio.no/ifi/english/people/aca/kyrrehg/pubs/miras-alife2018-abstract.html — four fitness functions: novelty (N), speed (S1), speed with morphological penalties (S2, S3; S3 penalises long limbs). **Speed-only selection produced mostly single-limb robots; the penalty on limb length produced multi-limb, branching, symmetric bodies — at a significant cost in speed** (Wilcoxon p < 0.05; the more penalised the fitness, the lower the speed).
- **Miras 2021.** "Constrained by Design: Influence of Genetic Encodings on Evolved Traits of Robots." Frontiers in Robotics and AI 8:672379. `[FULL TEXT, publisher HTML]` https://www.frontiersin.org/articles/10.3389/frobt.2021.672379/full — CPPN vs L-system; **20 runs**, population 100, 150 generations; Wilcoxon. CPPN tends to "spider" bodies (slower, stable gaits; some runs give dysfunctional blobs), L-system to faster rolling "snakes". Encoding bias persists despite an initial novelty-search phase.
- **Relevance.** Direct published support for two statements the project needs: (i) under pure speed selection, limb-poor bodies are the norm, and explicit morphological pressure produces limbs only by paying in speed; (ii) the encoding, not the search algorithm, sets the morphological "style".

### A17. Synthesis — what is known about QD vs plain EA vs AFPO on the champion in morphology search

| Study | Substrate / budget | Runs | Result on best fitness |
|---|---|---|---|
| Lehman & Stanley 2011 | rigid creatures, 500k evals | 15 | NS + global competition best; fitness-only = NSLC (n.s.) |
| Mouret & Clune 2015 | Cheney 3D VSR, CPPN | 5-8 | MAP-Elites vs EA: n.s. |
| Methenitis et al. 2015 | Cheney 3D VSR, 30k evals | 10 | novelty search >= objective CPPN-NEAT (no test) |
| Gravina et al. 2018 | Cheney 3D VSR, 30k evals | 90 | novelty / surprise / NSS > objective CPPN-NEAT at all sizes (sig.) |
| Gravina et al. 2019 | Cheney 3D VSR 5^3, 300k | 10 | selection-biased MAP-Elites > uniform MAP-Elites (sig.) |
| Nordmoen et al. 2021 | rigid modular, direct enc., 100k | 30 | MAP-Elites > EA and > NSGA-II+diversity (sig.) |
| Zardini et al. 2021 | tensegrity, 45k | 10 | ViE-NEAT > MAP-Elites in one task (sig.), n.s. in the other |
| Medvet et al. 2021 | 2D VSR, 30k | 10 | speciated EA (shape/behaviour) > GA, CMA-ES |
| Ferigo et al. 2022 | 2D VSR open-loop, 25k | 10 | EA makes no difference with indirect encoding; encoding dominates |
| Pigozzi et al. 2023 | 2D VSR, 30k | 10 | MAP-Elites (size, elongation, compactness) slightly lower; EA does not affect effectiveness |
| Medvet et al. 2025 | wheeled robot body+brain, 50k | 30 | negligible differences; 4-D-archive MAP-Elites worst |
| Mertan & Cheney 2025/26 | EvoGym 2D VSR, exhaustive landscape | 100 | AFPO = MAP-Elites (n.s.); MIP slightly worse |
| Le Goff et al. 2026 | ARE rigid, CPPN / superquadrics, 10k | 20 | MAP-Elites does not raise the best score |

Reading: (1) No published study shows MAP-Elites with *structural* descriptors and uniform selection beating a well-configured objective-based EA on the champion at small budgets in voxel soft robots; several show parity or a deficit. (2) The clear wins for diversity-driven search come either from **behaviour (trajectory) descriptors with novelty pressure** (Methenitis, Gravina, Joachimczak) or from a **direct encoding with a large budget** (Nordmoen). (3) AFPO vs MAP-Elites has been compared head-to-head once (Mertan & Cheney), in 2D, with the answer "no difference in champions". (4) I found **no** published comparison of speciated CPPN-NEAT, AFPO and MAP-Elites on the same 3D voxel substrate, and **no** study of sample efficiency (anytime curves / evaluations-to-target) across these methods. (5) Seed-to-seed variance is rarely quantified; the studies with the firmest conclusions use 30-100 runs.

**Does descriptor choice determine whether limbed morphologies appear?** I found no paper that tests this directly as a MAP-Elites question in voxel soft robots. The nearest evidence: Miras 2018b (explicit limb-related selection pressure produces limbs, at a speed cost); Pigozzi 2023 (encoding and terrain, not the EA, shift the share of limbed/blob/elongated bodies; elongation/compactness archive does not by itself produce a limbed champion); Methenitis 2015 (gravity level changes whether legs are favourable); Medvet 2021 (in 2D with sensing controllers, Legged/Crawling were the fastest); Matthews et al. 2023 (gradient-based design starting from a legless body "consistently discovers legged locomotion" — see E2). Mouret & Clune 2015 show legged bipeds inside a MAP-Elites map of the Cheney domain and also a high-fitness "island" of one-voxel-wide sheets caused by a simulator quirk — a reminder that the champion's shape is simulator-dependent.

---

## B. Newer QD algorithms and tooling

### B1. Core algorithm papers
- **Cully & Demiris 2018.** "Quality and Diversity Optimization: A Unifying Modular Framework." IEEE Trans. Evolutionary Computation 22(2):245-259 (journal reference taken from citing papers; the arXiv page lists none). arXiv:1708.09251. `[FULL TEXT via ar5iv]` https://arxiv.org/abs/1708.09251 — unifies MAP-Elites and NSLC as container + selection operator; introduces the **curiosity score** ("the propensity of an individual to generate offspring that are added to the collection"; raised when an offspring enters the archive, lowered otherwise) and compares selection operators (none, uniform, fitness-, novelty-, curiosity-proportionate, Pareto, population-based). Curiosity-based selection over the whole collection was generally best on the QD metrics; exception: in straight-line walking the population-based *fitness* selection found the highest maximum quality. 20 / 10 / 10 replicates per variant; Wilcoxon rank-sum with Holm-Bonferroni correction. **Relevance:** the origin of the project's "curiosity" selection, and a precedent that fitness-oriented selection can win on the champion.
- **Fontaine, Togelius, Nikolaidis, Hoover 2020 — CMA-ME.** "Covariance Matrix Adaptation for the Rapid Illumination of Behavior Space." GECCO 2020. DOI 10.1145/3377930.3390232. arXiv:1912.02400. `[FULL TEXT header, local: CMA_ME.txt]` — CMA-ES emitters ranked by archive improvement; continuous benchmarks and Hearthstone (5 trials there). Needs a fixed-length real-valued genome.
- **Fontaine & Nikolaidis 2023 — CMA-MAE.** "Covariance Matrix Adaptation MAP-Annealing." GECCO 2023. DOI 10.1145/3583131.3590389. arXiv:2205.10752. `[FULL TEXT header, local: CMA_MAE_NSF.txt]` — archive learning rate blends CMA-ES and CMA-ME; addresses premature abandonment of the objective, flat objectives and **poor performance with low-resolution archives**. 20 trials (5 for latent-space domains); ANOVA-style analysis with Bonferroni-corrected simple main effects.
- **Cully 2021 — Multi-Emitter MAP-Elites.** GECCO 2021, pp. 84-92. DOI 10.1145/3449639.3459326. arXiv:2007.05352. `[FULL TEXT header, local]` — heterogeneous emitter pool chosen by a UCB bandit; 20 replicates, Wilcoxon rank-sum + Holm-Bonferroni.
- **Nilsson & Cully 2021 — PGA-MAP-Elites.** "Policy Gradient Assisted MAP-Elites." GECCO 2021. DOI 10.1145/3449639.3459304. `[SEARCH ONLY; HAL preprint hal-03135723]` — critic-gradient variation for neural controllers. Not applicable to a CPPN body genome with open-loop actuation (no policy, no differentiable objective).
- **Bahlous-Boldi, Faldor, Grillotti, Janmohamed, Coiffard, Spector, Cully 2025 — Dominated Novelty Search (DNS).** arXiv:2502.00593 (1 Feb 2025). `[FULL TEXT, local]` https://arxiv.org/abs/2502.00593 — recasts QD as a GA with a fitness transformation: each individual's competition fitness is its mean descriptor distance to its k nearest **fitter** individuals; no grid, bounds or threshold. Brax Walker/Ant/Ant-Blocks and Kheperax; **10 seeds**, Mann-Whitney U + Holm-Bonferroni; beats MAP-Elites where the reachable descriptor space is constrained, high-dimensional or learned. All tasks are controller search. **Venue UNVERIFIED** (the arXiv page lists none; I believe GECCO 2025 but could not confirm).
- **Sfikas, Liapis, Yannakakis 2021 — Monte Carlo Elites.** GECCO 2021. DOI 10.1145/3449639.3459321. arXiv:2104.08781. `[ABSTRACT]` — parent selection in MAP-Elites as a multi-armed bandit (UCB on offspring survival).
- **Wang, Xue, Shang, Qian, Fu, Fu 2023 — NSS.** "Multi-objective Optimization-based Selection for Quality-Diversity by Non-surrounded-dominated Sorting." IJCAI 2023, pp. 4335-4343. `[SEARCH ONLY]` https://ijcai.org/proceedings/2023/482 — argues that uniform parent selection lacks selection pressure.
- **Calamita, Mendicini, Ferrari, Bertamini 2026.** "From Admission to Retention: Predicting Durable Offspring in Quality-Diversity Search." arXiv:2611.06522 (4 Nov 2026; NeurIPS 2026 workshop "EvoRobust"). `[ABSTRACT]` — planar arm and two locomotion tasks, unstructured archive; **biasing parent selection toward survival-predicting signals did not help: moderate bias matched uniform sampling, strong bias lowered QD-score.** A two-week-old negative result on selection bias (controllers, not morphology) that a selection-bias paper should acknowledge.
- **Gaier, Asteroth, Mouret 2017 — SAIL.** Local text is the preprint "Feature Space Modeling Through Surrogate Illumination", arXiv:1702.03713 `[FULL TEXT header, local: SAIL_v1.txt]` — Gaussian-process surrogate + acquisition-function MAP-Elites; airfoil design; "several orders of magnitude fewer evaluations" than MAP-Elites; 20 replicates. (Published versions at GECCO 2017 / Evolutionary Computation journal: UNVERIFIED by me.)

### B2. Tooling
- **QDax.** Chalumeau, Lim, Boige, Allard, Grillotti, Flageat, Macé, Flajolet, Pierrot, Cully. "QDax: A Library for Quality-Diversity and Population-based Algorithms with Hardware Acceleration." arXiv:2308.03665 (2023). `[ABSTRACT]` https://arxiv.org/abs/2308.03665 — JAX; assumes vectorisable evaluation. (JMLR publication UNVERIFIED.)
- **pyribs.** Tjanaka, Fontaine, Lee, Zhang, Balam, Dennler, Garlanka, Klapsis, Nikolaidis. "pyribs: A Bare-Bones Python Library for Quality Diversity Optimization." GECCO 2023. arXiv:2303.00191. `[ABSTRACT]` https://arxiv.org/abs/2303.00191 — archive / emitter / scheduler components; CPU-friendly ask-tell interface; emitters assume real-vector genomes.
- **Flageat, Lim, Grillotti, Allard, Smith, Cully 2022.** "Benchmarking Quality-Diversity Algorithms on Neuroevolution for Reinforcement Learning." arXiv:2211.02193 (GECCO QD-benchmarks workshop). `[ABSTRACT]` — standard metrics: coverage, QD-score, max fitness, archive profile; "corrected" metrics under stochasticity.

### B3. Have the newer QD methods been applied to robot morphology or soft robots?
Two extended searches (CMA-ME / CMA-MAE / PGA-MAP-Elites / pyribs / QDax + morphology / soft robot; Dominated Novelty Search + morphology / co-design) returned **no paper** applying CMA-ME, CMA-MAE, PGA-MAP-Elites, multi-emitter MAP-Elites or DNS to robot or soft-robot *morphology* search. All morphology-QD papers I found use plain grid MAP-Elites (uniform selection), NSLC-style novelty, multi-archive MAP-Elites, or k-means speciation. Absence in my searches is not proof of absence. There is a structural reason: CMA-based and gradient-based emitters need fixed-length continuous genomes or policies, whereas CPPN-NEAT genomes are variable-topology graphs. What *does* transfer directly to a CPPN genome: selection operators (curiosity, bandit, fitness-biased), unstructured/bounds-free competition (DNS), multi-archive schemes, multi-point descriptors (Trace-Elites), and surrogate pre-screening (SAIL-style).

---

## C. AFPO and its use in soft-robot evolution

- **Schmidt & Lipson 2010.** "Age-Fitness Pareto Optimization." GECCO 2010 (the local copy is the short proceedings version; an extended chapter exists in Genetic Programming Theory and Practice VIII — not checked). `[FULL TEXT, local]` — age (how long the genotype's lineage has been in the population) as a second objective with fitness; random individuals injected every generation; symbolic regression; claims roughly three-fold improvement over comparable methods and better scaling than ALPS.
- **Kriegman, Cheney, Corucci, Bongard 2017.** "A Minimal Developmental Model Can Increase Evolvability in Soft Robots." GECCO 2017. DOI 10.1145/3071178.3071296. arXiv:1706.07296. `[FULL TEXT via ar5iv]` — **AFPO**, population 30, 2,000 generations, **30 runs**, Mann-Whitney U; *direct* encoding (4x4x3 voxels, bilateral symmetry), explicitly not CPPN-NEAT.
- **Kriegman, Cheney, Bongard 2018.** "How morphological development can guide evolution." Scientific Reports 8 (2018) (article number 13934 from memory, not re-checked). DOI 10.1038/s41598-018-31868-7. arXiv:1711.07387. `[FULL TEXT via ar5iv]` — **AFPO**, population 30 (doubled + 1 random per generation), 10,000 generations, **30 runs** per treatment, Mann-Whitney U, 95 % bootstrapped CIs.
- **Cheney, Bongard, SunSpiral, Lipson 2018.** "Scalable Co-Optimization of Morphology and Control in Embodied Machines." J. R. Soc. Interface 15:20170937 (journal reference from memory — the arXiv page lists none; UNVERIFIED). arXiv:1706.06133. `[FULL TEXT via ar5iv]` — "morphological innovation protection": Pareto selection on fitness and **morphological age** (reset when the body mutates) on top of a (mu, lambda) evolution strategy with mu = lambda = 25; CPPN-encoded body and CPPN-encoded phase offsets in VoxCad; **30 runs**, 5,000 generations; Wilcoxon rank-sum; 95 % bootstrapped CIs. With protection 31.95 vs 21.72 voxel-lengths (p ~ 6e-6). An AFPO *derivative*, not AFPO proper.
- **Cheney, Bongard, SunSpiral, Lipson 2016.** "On the Difficulty of Co-Optimizing Morphology and Control in Evolved Virtual Creatures." ALIFE XV, pp. 226-233. `[SEARCH ONLY]` — premature convergence of morphology.
- **Corucci, Cheney, Giorgio-Serchi, Bongard, Laschi 2018.** "Evolving soft locomotion in aquatic and terrestrial environments: effects of material properties and environmental transitions." (Soft Robotics journal — venue not shown in the local text; UNVERIFIED by page.) `[FULL TEXT, local]` — CPPN encoding, evosoro; **multi-objective Pareto EA, mutation only, three objectives: distance, % actuated voxels (energy), number of voxels**. The text does not name age as an objective, so I do not count it as AFPO. **15 repetitions**; 95 % bootstrapped CIs; Mann-Whitney U with Bonferroni. **Defines 3D voxel shape descriptors: a global symmetry index, a "branching index" BI = 1 - V_robot / V_convex-hull (meant to capture appendages such as legs and hollow structures), and curvature-entropy morphological complexity** — used for analysis, not as search dimensions.
- **Kriegman, Blackiston, Levin, Bongard 2020.** "A scalable pipeline for designing reconfigurable organisms." PNAS 117(4):1853-1859. DOI 10.1073/pnas.1910837117. `[FULL TEXT main article via PMC]` https://pmc.ncbi.nlm.nih.gov/articles/PMC6994979 — **100 independent evolutionary runs**; the main text cites AFPO (its ref. 19) for diversity maintenance; details of the EA are in the SI (not read).
- **Mertan & Cheney 2024 / 2025-26** (A9 b, f) — AFPO as the default co-optimisation algorithm on EvoGym; the only head-to-head AFPO vs MAP-Elites comparison I found.
- **Relevance.** AFPO is the house algorithm of the Bongard / Kriegman / Cheney line; typical settings are population 16-30 and thousands of generations, i.e. tens to hundreds of thousands of evaluations and 30+ runs. I found **no** published comparison of AFPO against speciated CPPN-NEAT on voxel soft robots, and none at a budget below 10k evaluations. The project's "AFPO beat MAP-Elites at short horizons on 3 seeds" is therefore new in setting but, with 3 seeds, below every published evidential standard (see F).

---

## D. Encodings for (soft-)robot bodies and studies that compare them

### D1. Indirect vs direct on voxel soft robots
- **Cheney, MacCurdy, Clune, Lipson 2013.** "Unshackling Evolution: Evolving Soft Robots with Multiple Materials and a Powerful Generative Encoding." GECCO 2013, pp. 167-174. DOI 10.1145/2463372.2463404. `[FULL TEXT, local]` — CPPN-NEAT vs a direct encoding (GAlib, 5 values per voxel = 5,000 genes at 10^3). **35 runs** per treatment, population 30, 1,000 generations (30,000 evaluations); p-values reported (test not named in the passages I read). CPPN "far outperforms" the direct encoding; direct-encoded robots barely improve. Penalty functions (number of voxels, actuated voxels, connections) change the evolved body plans. The project's baseline; the 35-run design is the bar the original set.
- **Hiller & Lipson 2012.** "Automatic Design and Manufacture of Soft Robots." IEEE Transactions on Robotics 28(2):457-466. `[SEARCH ONLY]` — earlier voxel soft-robot evolution with fabricated results (encodings used there not re-checked).
- **Methenitis et al. 2015** (A3) — repeats CPPN vs direct GA: direct is competitive only on the 5^3 lattice; CPPN clearly better at 10^3.
- **Ferigo et al. 2022** (A8) — 2D VSR, open-loop control: **direct beats the indirect Gaussian-mixture encoding by 2-2.5x** for body+brain.
- **Pigozzi et al. 2023** (A7) — 2D VSR: direct vs Gaussian-mixture encoding comparable in velocity; they differ in *shape bias* (direct: protrusions/limbs/Walking; GMM: compact, round).
- **Pigozzi, Camerota Verdù, Medvet 2023.** "How the Morphology Encoding Influences the Learning Ability in Body-Brain Co-Optimization." GECCO 2023. DOI on the author page is given as 10.1145/3583131.3590429 (the page's publisher link uses ...3590431 — one of the two is a typo; UNVERIFIED which). `[ABSTRACT]` https://medvet.inginf.units.it/publications/2023-c-pcm-morphology/ — evolution of VSR bodies with RL-trained controllers; direct vs indirect encoding on three tasks; the direct encoding more consistently improves (speeds up) learning — interpreted as a Baldwin effect.
- **Tanaka & Aranha 2022.** "Co-evolving morphology and control of soft robots using a single genome." IEEE SSCI 2022. arXiv:2212.11517. `[ABSTRACT]` https://arxiv.org/abs/2212.11517 — one HyperNEAT genome generates body and controller (Evolution Gym); **speciation modified to include body similarity**; converges faster than separate genomes on four tasks.
- **Bhatia, Jackson, Tian, Xu, Matusik 2021 — Evolution Gym.** NeurIPS 2021. arXiv:2201.09863. `[FULL TEXT, local]` — 2D voxel benchmark; design optimisers GA (direct), Bayesian optimisation, CPPN-NEAT, each wrapped around PPO control learning. "Overall, GA outperforms the other two"; CPPN-NEAT does well on locomotion. Curves averaged over **6 seeds** (3 for some), no tests.

### D2. Encoding comparisons on rigid / modular robots
- **Veenstra & Glette 2020.** "How Different Encodings Affect Performance and Diversification when Evolving the Morphology and Control of 2D Virtual Creatures." ALIFE 2020, pp. 592-601. `[FULL TEXT, author PDF]` https://mn.uio.no/ifi/english/people/aca/kyrrehg/pubs/veenstra-alife2020-abstract.html — direct vs L-system vs CPPN vs cellular encoding; **20 runs** of 100,000 evaluations after a 256-run mutation-rate sweep; six two-sided Mann-Whitney U tests. **Direct and L-system significantly fitter than CPPN and cellular encoding** (p < 0.001); the network encodings make large jumps and find fewer distinct morphologies.
- **Miras et al. 2018a; Miras 2021** (A16) — direct vs L-system: no difference in diversity; CPPN vs L-system: different body "styles".
- **Le Goff et al. 2026** (A11) — superquadrics vs CPPN: the compact geometric encoding improves quality and diversity under both EA and MAP-Elites.
- **Thomson et al. 2024** (A12) — local-optima-network view of three encodings.
- **Saad Saoud 2026.** "The Cost of Becoming: Developmental Encoding Increases Phenotypic Diversity but Reduces Locality and Recombination Robustness in Evolved Robots." arXiv:2609.17606 (14 Sep 2026). `[ABSTRACT]` https://arxiv.org/abs/2609.17606 — direct vs static generative vs developmental encoding with matched parameter counts and budgets; **30 paired runs**; developmental encoding gives more phenotypic diversity but no reliable fitness gain, lower mutation viability and locality. (Search snippet adds: paired bootstrap interval, Wilcoxon signed-rank, rank-biserial effect size — not confirmed on the abstract page.)
- **Le Goff, Buchanan, Hart 2024.** "An Investigation of the Factors Influencing Evolutionary Dynamics in the Joint Evolution of Robot Body and Control." arXiv:2403.10303. `[ABSTRACT]` — asynchronous evolution + goal-based selection + replace-worst gave the best robots; novelty-driven selection did not.
- **Take-away.** "CPPN is better than direct" is solid only for large 3D voxel grids with open-loop actuation (Cheney 2013, Methenitis 2015). In 2D VSRs and tree-structured modular robots, direct encodings are equal or better (Ferigo 2022, Pigozzi 2023, Veenstra 2020, Evolution Gym). Several studies agree that the encoding fixes the *shape bias* (compact/regular for smooth generative encodings such as GMM and CPPN; knotty/limbed for direct ones). That is a plausible, citable explanation of the project's "blob" attractor that does not depend on the search algorithm.

### D3. Developmental / growth encodings
- **Kriegman et al. 2017, 2018** (C) — ballistic morphological development (voxel volumes change over the lifetime) increases evolvability; direct encoding + AFPO.
- **Joachimczak et al. 2015, 2016** (A15) — gene-regulatory-network-controlled cell division growing soft bodies; novelty search helps.
- **Corucci et al. 2018** (C) — CPPN bodies with evolved material stiffness; water/land transitions.
- **Talamini, Medvet, Nichele 2021.** "Criticality-Driven Evolution of Adaptable Morphologies of Voxel-Based Soft-Robots." Frontiers in Robotics and AI 8:673156. `[SEARCH ONLY]` — evolves bodies toward criticality rather than a task; cited by Ferigo 2022 for "irregular shapes are faster and more robust".
- **Mégane, Medvet, Lourenço, Machado 2026.** "Exploring Grammar-Guided Design and Evolution of Polyominoes with Modular Soft Robots." Genetic Programming and Evolvable Machines. DOI 10.1007/s10710-026-09534-z. `[ABSTRACT]` — grammar-constrained VSR bodies.

### D4. Neural cellular automata
- **Sudhakaran, Grbic, Li, Katona, Najarro, Glanois, Risi 2021.** "Growing 3D Artefacts and Functional Machines with Neural Cellular Automata." ALIFE 2021. arXiv:2103.08737. `[ABSTRACT]` — 3D NCA trained by gradient descent to grow *given target* structures in Minecraft (castles, trees, simple machines) and to regenerate them. It is supervised reconstruction of targets, **not** a search for novel functional morphologies.
- **Horibe, Walker, Risi 2021.** "Regenerating Soft Robots through Neural Cellular Automata." EuroGP 2021 (venue from the ITU repository / search; the arXiv page lists none). arXiv:2102.02579. `[ABSTRACT]` — NCA grow voxel soft robots; a second NCA regrows damaged bodies, partially restoring shape and locomotion.
- **Horibe, Walker, Berg Palm, Sudhakaran, Risi 2022.** "Severe damage recovery in evolving soft robots through differentiable programming." Genetic Programming and Evolvable Machines. `[SEARCH ONLY — title seen only; authors from memory, UNVERIFIED]`.
- **Relevance.** NCA are an encoding alternative to CPPNs with a regeneration story; I found no study comparing NCA and CPPN encodings for locomotion fitness under a fixed evaluation budget.

### D5. Learned / latent / probabilistic encodings (see also E)
- **Song, Yang, Peng, Zhou, Wang, Yao 2024 — MorphVAE.** AAAI-24, pp. 10368 ff. `[FULL TEXT, local]` https://ojs.aaai.org/index.php/AAAI/article/view/28904 — task-conditioned VAE trained by bootstrapping on evaluated designs ("continuous natural selection"), Evolution Gym; baselines CPPN-NEAT, BO, GA and others; **1,000 design evaluations, 3 runs**; Wilcoxon rank-sum in an appendix.
- **Song et al. 2026 — MISCO.** "Generative Evolutionary Design of Voxel-Based Soft Robots with Provable Optimality." arXiv:2609.29491. `[ABSTRACT]` — estimation-of-distribution algorithm with a VAE; claims asymptotic convergence guarantees.
- **Song et al. 2026 — RoboLDA.** arXiv:2609.29490. `[ABSTRACT]` — hierarchical Bayesian (task / robot / organ / voxel) generative model; zero-shot designs reported at ~106 % of EA performance.
- **Liu, Yao, Wang, Peng, Yang 2023 — AIEA.** "Rapidly Evolving Soft Robots via Action Inheritance." IEEE Trans. Evolutionary Computation. DOI 10.1109/TEVC.2023.3327459. `[SEARCH ONLY]` — inherited control actions act as a surrogate so that not every design needs full controller training; about half the compute.
- **Han et al. 2026.** "Benchmarking Tabular Foundation Models as Surrogates in Expensive Evolutionary Optimization." arXiv:2609.18130. `[ABSTRACT; the VSR case study is reported only in a search snippet]` — TabPFN as surrogate; mixed results.

---

## E. The 2023-2026 frontier: differentiable, generative, RL- and LLM-based design

### E1. Differentiable design
- **Matthews, Spielberg, Rus, Kriegman, Bongard 2023.** "Efficient automatic design of robots." PNAS (DOI 10.1073/pnas.2305180120). arXiv:2306.03263. `[ABSTRACT]` — gradient-based optimisation of body structure through a differentiable simulator; designs a walking robot "within seconds on a single consumer-grade computer", versus days of supercomputing for earlier evolutionary methods; **starts from a legless body and "consistently discovers legged locomotion"**; a manufactured robot retains the behaviour.
- **Strgar, Matthews, Hummer, Kriegman 2024.** "Evolution and learning in differentiable robots." Robotics: Science and Systems 2024 (paper 100). arXiv:2405.14712. `[ABSTRACT + RSS listing]` https://roboticsproceedings.org/rss20/p100.html — outer genetic algorithm over bodies, inner gradient descent on neural controllers in massively parallel differentiable simulation; evolution yields "increasingly differentiable" bodies; one built physically. (A search snippet says 10 evolutionary runs; not checked.)
- **Strgar & Kriegman 2025/2026.** "Accelerated co-design of robots through morphological pretraining." arXiv:2502.10862; listed as an ICLR 2026 paper (ICLR virtual site / mlanthology via search). `[ABSTRACT]` — one morphology-agnostic controller pretrained by gradients; "zero-shot evolution"; identifies **"diversity collapse"** when a shared controller is co-trained with an evolving population.
- **Wang, Ma, Spielberg, Xian, Zhang, Tenenbaum, Rus, Gan 2023 — SoftZoo.** ICLR 2023. arXiv:2303.09555. `[ABSTRACT]` — differentiable soft-robot co-design benchmark across terrains.
- **Cochevelou et al. 2023** — cited by Strgar et al. as a differentiable soft-robot design study; exact title and venue **UNVERIFIED** (my search did not find the paper itself).

### E2. Generative models
- **Wang, Zheng, Ma, Du, Kim, Spielberg, Tenenbaum, Gan, Rus 2023 — DiffuseBot.** NeurIPS 2023. arXiv:2311.17053. `[ABSTRACT]` — diffusion model over soft-robot shapes augmented with differentiable physics; co-optimises design and control with simulator gradients; simulated and fabricated robots.
- MorphVAE, MISCO, RoboLDA (D5).
- **Feng, Shi, Xie, Wang, Geng 2026.** "Bridging Body and Brain: Gene-Driven Morphology-Control Co-Design." arXiv:2609.31329. `[ABSTRACT]` — latent "Morphogene" generating limb-level body and policy together.

### E3. Reinforcement-learning design policies, GNN / transformer controllers
- **Gupta, Savarese, Ganguli, Fei-Fei 2021 — DERL.** "Embodied Intelligence via Learning and Evolution." Nature Communications (DOI 10.1038/s41467-021-25874-z). arXiv:2102.02202. `[ABSTRACT]` — tournament evolution of rigid morphologies with lifetime RL.
- **Yuan, Song, Luo, Sun, Kitani 2022 — Transform2Act.** ICLR 2022 (oral). arXiv:2110.03659. `[ABSTRACT]` — one graph policy first edits the skeleton, then controls it.
- **Wang, Wu, Fu, Fu, Zhang, Chang, Wang 2023 — CuCo.** "Curriculum-based Co-design of Morphology and Control of Voxel-based Soft Robots." ICLR 2023. `[SEARCH ONLY]` https://iclr.cc/virtual/2023/poster/10693 — RL design policy grown from small to large voxel grids.
- **Li, Matthews, Kriegman 2024.** "Reinforcement learning for freeform robot design." arXiv:2310.05670 (venue UNVERIFIED). `[ABSTRACT]` — policy-gradient design of free-form bodies, open-loop control.
- **Li, Kong, Kriegman 2025.** "Generating Freeform Endoskeletal Robots." arXiv:2412.01036 (venue UNVERIFIED). `[ABSTRACT]` — latent design space for soft bodies with rigid skeletons, RL control, evolution strategies in latent space.
- **Wang, Li, Guo, Kriegman 2026 — ECo-MoE.** arXiv:2605.24225. `[ABSTRACT]` — embodiment-conditioned mixture of expert controllers to raise evolvability.
- **Wang, Pan, Serra-Gomez, Wei, Xie, ... 2026.** "Evolving Embodied Intelligence: Graph Neural Network-Driven Co-Design of Morphology and Control in Soft Robotics." arXiv:2603.19582. `[FULL TEXT header, local]` — GA over EvoGym bodies with graph-attention PPO controllers inherited across generations; **3 runs**.
- **Song et al. 2026 — "AdaControl".** "Shaping the Evolutionary Dynamics of Robot Morphology via Adaptive Control Learning." arXiv:2608.23100. `[FULL TEXT header, local]` — adaptive controller-training budget inside a GA on EvoGym; **5 trials, two-tailed t-tests**.
- **Wang et al. 2025.** "Embodied Co-Design for Rapidly Evolving Agents: Taxonomy, Frontiers, and Challenges." arXiv:2512.04770. `[ABSTRACT]` — survey of 100+ co-design papers (bi-level, single-level, generative, open-ended).

### E4. LLM-driven design — what each paper actually does
- **LASeR** — Song, Yang, Xiao, Peng, Yao, Wang. "LASeR: Towards Diversified and Generalizable Robot Design with Large Language Models." **ICLR 2025.** `[ABSTRACT]` https://proceedings.iclr.cc/paper_files/paper/2025/hash/934eb45b99eff8f16b5cb8e4d3cb5641-Abstract-Conference.html — the LLM is the *variation operator* of an evolutionary search over **voxel soft robots** (Evolution Gym per search snippets); a reflection mechanism ("DiRect") steers exploration; claims better efficiency and diversity than baselines and zero-shot proposals for new tasks. Exists; soft robots: yes.
- **RoboMorph** — Qiu, Pałucki, Ciebiera, Fijałkowski, Cygan, Kuciński. arXiv:2407.08626 (v1 July 2024, v3 March 2026; no venue listed). `[ABSTRACT]` — LLM + evolutionary loop over **robot-grammar designs of modular (rigid, RoboGrammar-style) robots**, RL control evaluation; matches or beats RoboGrammar's graph search on four terrains. Exists; **not soft robots**.
- **Text2Robot** — Ringel, Charlick, Liu, Xia, Chen. arXiv:2406.19963 (no venue listed). `[ABSTRACT]` — text-to-3D generative models produce initial bodies for **quadrupedal** robots, then geometric processing and evolutionary body-control co-optimisation aware of electronics and manufacturability; about a day per robot. Exists; **rigid legged robots, not soft**.
- **RoboMoRe** — Fang, Sun, Ma, Lu, Yao. arXiv:2506.00276 (2025). `[ABSTRACT]` — LLM co-optimises morphology *and reward function* in two stages; eight tasks.
- **Chen, Xu, Wang, Huang 2025.** "Natural Selection via Foundation Models for Soft Robot Evolution" (RoboCrafter-QA). arXiv:2503.02249. `[ABSTRACT]` — benchmark of whether (multimodal) LLMs can pick the better of two EvoGym soft-robot designs; they struggle with small performance differences; a fine-tuned open model does best.
- **Ma, Zhao, She, Jiang, Sun, Zhu, Balkcom, Vosoughi 2024.** "On the Exploration of LM-Based Soft Modular Robot Design." arXiv:2411.00345. `[ABSTRACT]` — LLM generates construction sequences for soft modular robots from instructions, refined with simulator feedback.
- **Zhang 2024.** "CUDA-Accelerated Soft Robot Neural Evolution with Large Language Model Supervision." arXiv:2405.00698 (3 pages). `[ABSTRACT]` — LLM as "control centre" of an evolutionary co-design run; short note.

### E5. Implications for a pure-evolution paper
- The frontier has moved the *efficiency* goalposts: gradients design a walker in seconds (Matthews 2023); generative / LLM methods report gains with ~1,000 design evaluations (MorphVAE, LASeR). A paper whose selling point is "our evolutionary variant reaches a faster robot" will be compared — at least rhetorically — against these.
- Those methods need what the Cheney-style setting does not offer: a differentiable simulator (E1, DiffuseBot), a controller-learning inner loop (E3), or small 2D voxel grids that fit an LLM prompt or a VAE (LASeR, MorphVAE: Evolution Gym; a search snippet on the 2026 TabPFN study mentions 5x5 morphologies — grid sizes not re-checked per paper). None of the frontier papers I verified works on 10x10x10 multi-material bodies with open-loop actuation, and their statistics are thin (3-6 seeds).
- The defensible positioning is therefore: (i) black-box search remains the only option when the simulator is non-differentiable and contact-rich, and it is the outer loop in most "frontier" pipelines (Strgar 2024, Li 2025, AdaControl 2026 all keep a GA / ES outside); (ii) the contribution is *methodological evidence* — a controlled, well-replicated comparison of selection schemes (speciation, age, archive) on an open, reproducible substrate, with seed variance quantified — rather than a new state of the art; (iii) the recurring frontier observations of "diversity collapse" (Strgar & Kriegman), "premature convergence" (Le Goff 2026) and "fragile co-adaptation" (Mertan & Cheney) show that the selection question is still open even in gradient-based pipelines.

---

## F. Statistical practice and reporting

### F1. What comparable papers actually do (numbers as recorded in sections A-E; see H for which were read line by line and which came from text summaries)

| Paper | Venue | Runs per condition | Tests / intervals |
|---|---|---|---|
| Cheney et al. 2013 | GECCO | 35 | p-values (test not named in passages read) |
| Mouret & Clune 2015 | arXiv | 5-8 completed of 10 | p-values |
| Lehman & Stanley 2011 | GECCO | 15 | Kruskal-Wallis, then Mann-Whitney U |
| Methenitis et al. 2015 | GECCO | 10 | none found (box plots, mean +/- deviation) |
| Gravina et al. 2017 / 2018 / 2019 | GECCO comp. / GECCO / GECCO comp. | 30 / 90 / 10 | Mann-Whitney U (2018, 2019; test of the 2017 paper not seen); Bonferroni and 95 % CIs (2018) |
| Kriegman et al. 2017, 2018 | GECCO, Sci. Rep. | 30 | Mann-Whitney U; 95 % bootstrapped CIs |
| Cheney et al. 2018 | J. R. Soc. Interface | 30 | Wilcoxon rank-sum; 95 % bootstrapped CIs |
| Corucci et al. 2018 | Soft Robotics | 15 | Mann-Whitney U + Bonferroni; 95 % bootstrapped CIs |
| Cully & Demiris 2018 | IEEE TEVC | 10-20 | Wilcoxon rank-sum + Holm-Bonferroni |
| Veenstra & Glette 2020 | ALIFE | 20 | Mann-Whitney U (six pairwise) |
| Kriegman et al. 2020 | PNAS | 100 | (not checked) |
| Nordmoen et al. 2021 | Frontiers Robot. AI | 30 | Mann-Whitney U + Holm; 95 % CIs |
| Zardini et al. 2021 | GECCO | 10 | Wilcoxon rank-sum, alpha 0.05 |
| Medvet et al. 2021 | GECCO (best paper, CS track) | 10 | Mann-Whitney U |
| Miras 2021 | Frontiers Robot. AI | 20 | Wilcoxon |
| Cully 2021 (ME-MAP-Elites) | GECCO | 20 | Wilcoxon rank-sum + Holm-Bonferroni |
| Ferigo et al. 2022 | ALIFE | 10 | Mann-Whitney U + Bonferroni |
| Pigozzi et al. 2023 | ACM TELO | 10 | two-sided Mann-Whitney U, 0.05 |
| Fontaine & Nikolaidis 2023 (CMA-MAE) | GECCO | 20 (5 for expensive domains) | ANOVA-style + Bonferroni; 95 % CIs |
| Mertan & Cheney 2024 | EuroGP | 10 | Wilcoxon rank-sum; 95 % bootstrapped CIs |
| Mertan & Cheney 2025 | GECCO | 20 | Wilcoxon rank-sum, 0.05 |
| Medvet et al. 2025 | GPEM | 30 | Wilcoxon, alpha 0.01 |
| Bahlous-Boldi et al. 2025 (DNS) | arXiv | 10 | Mann-Whitney U + Holm-Bonferroni; 95 % CIs |
| Mertan & Cheney 2025/26 | Artificial Life | 100 | Mann-Whitney U; 95 % bootstrapped CIs |
| Le Goff et al. 2026 | PPSN | 20 | Mann-Whitney U (p < 0.001) + Cliff's delta |
| Saad Saoud 2026 | arXiv | 30 paired | (snippet: paired bootstrap, Wilcoxon signed-rank, rank-biserial) |
| ML-venue design papers: Evolution Gym 2021; MorphVAE 2024; GNN co-design 2026; AdaControl 2026 | NeurIPS; AAAI; arXiv; arXiv | 6 (3); 3; 3; 5 | none; Wilcoxon rank-sum (appendix); none; t-tests |

Patterns:
- In GECCO / ALIFE / EuroGP / TELO evolutionary-robotics papers the **floor is 10 runs per condition; 20-30 is common; the papers whose conclusions people rely on use 30-100.** Three to six seeds appear only in ML-venue papers with expensive RL inner loops.
- The **Mann-Whitney U / Wilcoxon rank-sum test on end-of-run values** is nearly universal; corrections are Holm (Nordmoen, Cully, DNS) or Bonferroni (Corucci, Ferigo, Gravina). Kruskal-Wallis is sometimes used as an omnibus test first.
- **Bootstrapped 95 % confidence bands** on learning curves are standard in the Vermont line.
- **Effect sizes are rare** — I found Cliff's delta in Le Goff et al. 2026 and rank-biserial in Saad Saoud 2026; I found **no** soft-robot evolution paper reporting Vargha-Delaney A12. Reporting an effect size is therefore an easy way to be above the bar.
- Nobody in this literature reports *sample-efficiency* statistics (evaluations to reach a target, area under the best-so-far curve) with intervals; anytime curves are shown but compared only at the end point.

### F2. Guidance papers
- **Arcuri & Briand 2014.** "A Hitchhiker's guide to statistical tests for assessing randomized algorithms in software engineering." Software Testing, Verification and Reliability 24(3):219-250. DOI 10.1002/stvr.1486 (extends an ICSE 2011 paper). `[SEARCH ONLY]` — the usual citation for "run randomized algorithms many times (commonly quoted as 30), use non-parametric tests, report effect sizes"; indexed keywords include effect size, confidence interval, Bonferroni adjustment. That it specifically recommends the Mann-Whitney U + Vargha-Delaney A12 pairing is my recollection, **not verified** here.
- **Vargha & Delaney 2000.** "A Critique and Improvement of the CL Common Language Effect Size Statistics of McGraw and Wong." J. Educational and Behavioral Statistics 25(2):101-132. `[SEARCH ONLY]` — defines the A measure of stochastic superiority (probability that a run of method X beats a run of method Y).
- **Derrac, García, Molina, Herrera 2011.** "A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms." Swarm and Evolutionary Computation 1(1):3-18. `[SEARCH ONLY]` — pairwise and multiple-comparison non-parametric procedures (multi-problem analysis).
- **Bartz-Beielstein et al. 2020.** "Benchmarking in Optimization: Best Practice and Open Issues." arXiv:2007.03488 (17 authors). `[ABSTRACT]` — goals, problem and algorithm selection, performance measures, analysis, design, presentation, reproducibility.
- **López-Ibáñez, Branke, Paquete 2021.** "Reproducibility in Evolutionary Computation." ACM TELO. DOI 10.1145/3466624. arXiv:2102.03380. `[ABSTRACT]` — reproducibility taxonomy and guidelines for EC.
- **Agarwal, Schwarzer, Castro, Courville, Bellemare 2021.** "Deep Reinforcement Learning at the Edge of the Statistical Precipice." NeurIPS 2021 (outstanding paper). arXiv:2108.13264. `[ABSTRACT]` — with few runs, report **interval estimates** rather than point estimates; **interquartile mean (IQM)**, **performance profiles**; the `rliable` library. (Stratified-bootstrap CIs and "probability of improvement" are also in that paper as I recall, but the abstract page does not say so — not verified.)
- **Colas, Sigaud, Oudeyer 2018.** "How Many Random Seeds? Statistical Power Analysis in Deep Reinforcement Learning Experiments." arXiv:1806.08295. `[ABSTRACT]` — relates number of seeds to error probabilities; t-test and bootstrap CI test; guidelines for the number of seeds.
- **Colas, Sigaud, Oudeyer 2019.** "A Hitchhiker's Guide to Statistical Comparisons of Reinforcement Learning Algorithms." arXiv:1904.06979. `[ABSTRACT]` — compares tests by false-positive rate and power across sample and effect sizes and under assumption violations.
- **Flageat et al. 2022** (B2) — QD metrics to report: coverage, QD-score, max fitness, archive profile.
- I searched for guidance specific to evolutionary robotics (seed variance, number of runs) and **found none**; the field relies on the general EC guidance above.

### F3. Consequences for this project (my arithmetic, not from a source)
- With **3 runs per method**, the exact two-sided Mann-Whitney U test cannot give p < 0.10 (complete separation of 3 vs 3 gives p = 2/20 = 0.10). Complete separation needs **4 vs 4** for p = 0.029 and **5 vs 5** for p = 0.008; with Holm/Bonferroni over three pairwise comparisons (three methods) 5 per method is the minimum at which *any* comparison can be significant, and only if the runs separate completely.
- Rule of thumb (Lehr's approximation, n per group ~ 16 / d^2 for 80 % power at alpha = 0.05): a "large" standardised effect d = 0.8 needs ~25 runs per method; d = 1.2 needs ~11; d = 1.5 needs ~7. If seed-to-seed spread really exceeds most between-method effects, 10 runs will resolve only the largest effects — which is itself worth reporting.
- A credible GECCO full paper in this niche therefore needs **>= 10 runs per condition as an absolute floor, 20-30 for the headline comparison**, Mann-Whitney U with Holm correction, an effect size (A12 or Cliff's delta) with a bootstrap interval, bootstrapped bands on best-so-far curves, and QD metrics (coverage, QD-score, max fitness) reported on a *common* evaluation grid for all methods (the "projected" archive idea used by the DNS paper). At 8-10 h per run, 3 methods x 20 runs is roughly 500-600 workstation-hours.
- If runs are paired by seed across methods (the task brief mentions "identical physics and seed") *and* the seed effect is shared — e.g. the same initial population — paired tests (Wilcoxon signed-rank) and a paired bootstrap are justified and more powerful; this is what Saad Saoud 2026 reportedly does. If the seed only fixes the random stream, runs are effectively independent and unpaired tests are the honest choice.

---

## G. Gaps a one-workstation project could fill, and scoop risks

### G1. Selection pressure *inside* the archive for morphology search at small budgets
- **Idea.** Systematic study of parent selection in MAP-Elites on 3D CPPN voxel robots: uniform vs fitness-biased vs curiosity vs trajectory-novelty, at <= 10k evaluations, with anytime statistics.
- **Why plausibly new.** The only morphology precedent is Gravina et al. 2019 — a two-page companion paper on a 5^3 lattice with 10 runs and 300k evaluations, using novelty/surprise of trajectories as the signal. Curiosity (Cully & Demiris 2018) and bandit selection (Sfikas et al. 2021) were evaluated on controllers and games. I found no study of fitness-proportionate or curiosity selection for morphology archives, none at a 10^3 lattice, none in a low-budget regime.
- **Risk.** May be judged incremental; the November 2026 workshop paper (Calamita et al.) reports that selection bias does not help in arm/locomotion controller tasks, so a positive result must be statistically solid and explained (e.g. by the low coverage-to-budget ratio of morphology archives).

### G2. Where should local competition live? A budget-resolved comparison of speciation, age and archives
- **Idea.** On one open substrate: speciated CPPN-NEAT (competition among genotype-similar individuals), AFPO (among same-age lineages), grid MAP-Elites (among descriptor neighbours), a bounds-free variant (Dominated Novelty Search, 2025), optionally phenotype-clustered speciation (Medvet's SE-s / SE-b) and a trajectory-novelty baseline (Gravina) — reported as evaluations-to-target and best-so-far curves with intervals, not just end points.
- **Why plausibly new.** No published head-to-head of speciated CPPN-NEAT, AFPO and MAP-Elites on 3D voxel robots exists (A17). Published results conflict by budget and encoding: MAP-Elites wins at 100k evaluations with a direct encoding (Nordmoen 2021); novelty search wins at 30k (Gravina 2018); parity in 2D (Mertan & Cheney 2025/26; Pigozzi 2023); CPPN-NEAT ahead at ~9k (this project). A crossover analysis over budget would reconcile them. DNS has, as far as I could find, never been applied to morphology; its premise (unknown descriptor bounds, sparse reachable region) matches a 16x16 morphology archive after 9k evaluations.
- **Risk — highest of the three.** Mertan & Cheney (Vermont) published AFPO vs MAP-Elites vs MIP with 100 runs and an exhaustive ground-truth landscape (ALIFE 2025 -> *Artificial Life* 2026) and a GECCO 2025 MAP-Elites paper; a 3D / CPPN follow-up from them would overlap directly. Le Goff, Smith & Hart (PPSN 2026) already report "MAP-Elites does not raise the best score" for CPPN-encoded rigid robots at 10k evaluations. Gravina et al. 2018 (90 runs) will be used by reviewers to argue that objective CPPN-NEAT is a weak baseline unless a trajectory-novelty arm is included.

### G3. Surrogate pre-screening for open-loop voxel robots
- **Idea.** Train a predictor of fitness (and descriptors) from the 10^3 material grid on the evaluations already produced, and use it to pre-screen CPPN offspring before simulation (SAIL-style acquisition inside MAP-Elites, or simple pre-selection inside NEAT/AFPO); report evaluations saved at equal champion quality.
- **Why plausibly new.** With fixed open-loop actuation, fitness is a deterministic function of the body — there is no controller-training noise, unlike all the Evolution Gym surrogate / generative work (AIEA 2023, MorphVAE 2024, MISCO / RoboLDA / TabPFN 2026), which is 2D with RL controllers and direct or latent encodings. Surrogate-assisted illumination (Gaier et al. 2017) has been shown on airfoils; I found no application to voxel soft robots or to CPPN-generated bodies. The project's cost profile (~9k evaluations per 8-10 h run) is exactly where a 30-50 % saving matters.
- **Risk.** The Song / Yao group (MorphVAE -> LASeR -> MISCO, RoboLDA, AdaControl) and Handing Wang's group (AIEA, TabPFN) publish several sample-efficiency papers per year on voxel robots; they are 2D / RL-based but are the likely reviewers and the likely source of a competing 3D result. A surrogate that only works on one simulator will be seen as engineering unless tied to a search-dynamics insight.

### G4. Descriptor-side opportunity (smaller, but cheap)
- Limb-oriented archive dimensions — the **branching index** (Corucci 2018), **number of limbs / symmetry** (Miras 2018a), or the **number of separate ground-contact patches** — have not been used as MAP-Elites dimensions for voxel soft robots as far as I could find. Even if limbed bodies stay slow, the archive then *quantifies* the fitness cost of limbs under this physics (the "illumination" use of MAP-Elites that Mouret & Clune advocate) and turns the project's negative result into a measured landscape property. Pigozzi et al. 2023 (2D; elongation / compactness; encoding and terrain decide limbs) and Miras et al. 2018b (limbs appear under explicit pressure, at a speed cost) are the comparison points; Matthews et al. 2023 (gradient design finds legs from a legless start) is the counter-example reviewers will raise, so the actuation model and the 10-cycle horizon need to be discussed as causes.

### G5. General scoop / positioning risks
- The project's headline, as currently phrased, has partial precedents on both sides: Mouret & Clune 2015 (same domain: map better, champion n.s.), Lehman & Stanley 2011 (local competition costs absolute performance), Pigozzi 2023, Medvet 2025, Le Goff 2026 and Mertan & Cheney 2025/26 (no champion gain from MAP-Elites). "QD gives the population, the EA gives the champion" is therefore **not new as a qualitative statement**; what is new must be the substrate (3D, open, MuJoCo), the inclusion of speciated NEAT and AFPO, the sample-efficiency quantification, and the seed-variance analysis.
- Conversely Gravina 2017/2018 and Methenitis 2015 report that diversity-driven search *beats* objective CPPN-NEAT on the champion in the original VoxCad system. The project must either reproduce or explain that (descriptor type: trajectory vs structure; physics engine; fitness horizon; budget).
- A February 2026 TechRxiv preprint ("Evolutionary AI for Morphological and Locomotor Design of ...", DOI 10.36227/techrxiv.176116522.21490062) appears from search snippets to revisit CPPN-NEAT + novelty search under different gravity levels; **I could not open it (HTTP 403) — title incomplete, authors unknown, content UNVERIFIED.**
- I found no MuJoCo-based re-implementation of the Cheney 2013 system in the literature (one extended search; simulators were outside my brief).

---

## H. What I could not verify (consolidated)

- **Venue not confirmed by a page I opened:** Dominated Novelty Search (arXiv only; GECCO 2025 is my belief); Nordmoen et al. 2020 precursor (IEEE SSCI); Cheney et al. 2018 journal reference (J. R. Soc. Interface); Corucci et al. 2018 (Soft Robotics); QDax (JMLR); SAIL published versions; Xie et al. 2024 (MAP + topology optimisation); Li et al. 2024 and Li, Kong, Kriegman 2025 (venues); Horibe et al. 2021 (EuroGP — from repository/search, not the arXiv page); Strgar & Kriegman (ICLR 2026 — from search listing).
- **Existence confirmed only through search metadata (no abstract read):** Veenstra, Olsen, Glette 2022; Gaier et al. 2019; Nilsson & Cully 2021; Wang et al. 2023 (NSS, IJCAI); Hiller & Lipson 2012; Joachimczak et al. 2015 / 2016; Talamini et al. 2021; Cheney et al. 2016; Liu et al. 2023 (AIEA); CuCo (ICLR 2023); Arcuri & Briand 2014; Vargha & Delaney 2000; Derrac et al. 2011; Horibe et al. 2022.
- **Not found / not openable:** Cochevelou et al. 2023 (title, venue); the February 2026 TechRxiv preprint; the ESA "memetic xenobots" project page (HTTP 404); the ACM DL pages (HTTP 403 — I used author-hosted PDFs instead).
- **Details taken from an automated summary of the full text rather than read line by line:** Nordmoen 2021, Zardini 2021, Cully & Demiris 2018, Cheney 2018, Kriegman 2017/2018, Miras 2021, Le Goff 2026, Mertan & Cheney 2025 (GECCO) — numbers such as run counts and tests should be re-checked against the PDFs before being quoted in a paper. (For Nordmoen 2021 and Le Goff 2026 the run counts, budgets, tests and the best-fitness statements were additionally confirmed by a second pass that returned the quoted sentences.)
- **Pigozzi, Camerota Verdù, Medvet 2023 DOI** is ambiguous on the author page (…3590429 vs …3590431).
- **Medvet et al. 2021** — the abstract ("representation matters more than the EA") and the conclusion ("the EA plays a more important role than representation") of the author PDF disagree; cite with care.
- **Mouret & Clune 2015** — the arXiv preprint states its data are preliminary; I did not check whether a later version changes the soft-robot statistics.
- **Semantic Scholar API** returned HTTP 429, so no systematic forward-citation chaining was done; coverage of 2025-2026 follow-ups relies on web search and arXiv listings. Absence claims ("no paper applies X to morphology") are based on a handful of targeted searches and should be read as "not found", not "does not exist".
- The task brief described Medvet et al. 2021 as a MAP-Elites work; the paper uses CMA-ES, a GA and a k-means speciated EA (MAP-Elites appears only in the 2023 journal extension).

---

## I. The twelve most important papers for this project

1. **Mouret & Clune 2015**, MAP-Elites — same VoxCad/CPPN domain; map far better, champion not significantly different (5-8 runs). https://arxiv.org/abs/1504.04909
2. **Gravina, Liapis, Yannakakis 2018**, GECCO — 90 runs, 3^3-10^3: trajectory novelty/surprise search beats objective CPPN-NEAT on the champion at every size. https://doi.org/10.1145/3205455.3205503
3. **Gravina, Liapis, Yannakakis 2019**, GECCO Companion — only prior study of parent selection in MAP-Elites for soft-robot morphology; biased selection > uniform on best fitness. https://doi.org/10.1145/3319619.3321987
4. **Mertan & Cheney 2025/26**, Artificial Life (arXiv:2508.17464) — AFPO vs MAP-Elites vs MIP on an exhaustively mapped voxel-robot landscape, 100 runs: champions indistinguishable. https://arxiv.org/abs/2508.17464
5. **Pigozzi, Medvet, Bartoli, Rochelli 2023**, ACM TELO — MAP-Elites over (size, elongation, compactness) on VSRs; Blob/Limbed/Elongated classes; encoding and terrain decide shape, EA does not decide effectiveness. https://doi.org/10.1145/3587101
6. **Nordmoen, Veenstra, Ellefsen, Glette 2021**, Frontiers Robot. AI — the counter-example: MAP-Elites beats EAs on best fitness (direct encoding, 100k evaluations, 30 runs, MWU + Holm). https://arxiv.org/abs/2012.04375
7. **Lehman & Stanley 2011**, GECCO — NSLC; descriptors height/mass/active joints; local competition trades absolute performance for diversity. https://doi.org/10.1145/2001576.2001606
8. **Methenitis, Hennes, Izzo, Visser 2015**, GECCO — novelty search in the Cheney system; ten behaviour descriptors incl. voxels-touching-ground; gravity decides whether legs appear. https://doi.org/10.1145/2739480.2754731
9. **Le Goff, Smith, Hart 2026**, PPSN (arXiv:2606.11037) — encoding x {EA, MAP-Elites} factorial at 10k evaluations, 20 runs, MWU + Cliff's delta; MAP-Elites does not raise the best score. https://arxiv.org/abs/2606.11037
10. **Cully & Demiris 2018**, IEEE TEVC — unified QD framework; curiosity score; comparison of selection operators. https://arxiv.org/abs/1708.09251
11. **Bahlous-Boldi et al. 2025**, Dominated Novelty Search — grid-free, bounds-free local competition as a fitness transformation; not yet applied to morphology (as far as found). https://arxiv.org/abs/2502.00593
12. **Matthews, Spielberg, Rus, Kriegman, Bongard 2023**, PNAS — differentiable design in seconds; legs emerge from a legless start; the efficiency benchmark any pure-evolution paper is implicitly measured against. https://arxiv.org/abs/2306.03263

Close runners-up: Cheney et al. 2018 (morphological innovation protection); Miras et al. 2018b (limbs under explicit pressure, at a speed cost); Zardini et al. 2021 (NEAT-based method > MAP-Elites); Medvet et al. 2021 (speciation on shape/behaviour gives both speed and diversity); Schmidt & Lipson 2010 (AFPO); Song et al. 2025 (LASeR).

## J. Process note

- Tools: web search, page fetches (arXiv abs / HTML, ar5iv, author-hosted PDFs converted to text locally), and the local extracted texts. The shared web-search budget was exhausted near the end, so one last check (the publication venue of Dominated Novelty Search) could not be run.
- The Semantic Scholar API rate-limited the first request (HTTP 429) and was not used further; no systematic citation chaining was performed.
- ACM Digital Library, PMC and university repository pages frequently returned HTTP 403 or a CAPTCHA; in those cases author-hosted copies were used.
- Text extracted from the author-hosted PDFs that were read in full (Medvet 2021, Pigozzi 2023, Lehman & Stanley 2011, Methenitis 2015, Miras 2018a/b, Veenstra 2020, Ferigo 2022, Medvet 2025, Nadizar 2025, Gravina 2017/2018/2019) is in the session scratchpad folder `lit3_txt` next to this file; it is temporary and can be deleted.
