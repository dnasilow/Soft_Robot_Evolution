# What has already been done: evolving voxel soft robots

Survey of 18–19 November 2026, for the paper plan in [PLAN.md](PLAN.md).

**How it was gathered.** Five parallel searches over arXiv, Semantic Scholar, OpenAlex, publisher and author pages, plus the papers already in `research_reference/`. Google Scholar itself blocked automated access. The detailed notes in [literature_notes/](literature_notes/) tag every entry by how it was checked: full text read, abstract only, or search listing only. Statements below that carry a number were checked against the paper's text; "not found" means not found in these searches, not proven absent. Downloaded papers and extracted text are in `research_reference/review_2026-11-18/` (kept out of git).

**Before citing anything in the paper, open the source again.** GECCO treats invented references as grounds for desk rejection.

---

## 1. The system this project re-implements

- **Cheney, MacCurdy, Clune, Lipson (GECCO 2013)**, "Unshackling evolution". CPPN-NEAT bodies of four materials in VoxCad/Voxelyze, fixed two-phase actuation, score = centre-of-mass displacement over 10 cycles. 35 runs per condition, 30 individuals, 1000 generations. DOI [10.1145/2463372.2463404](https://doi.org/10.1145/2463372.2463404). Data: Dryad [10.5061/dryad.m3s84](https://datadryad.org/dataset/doi:10.5061/dryad.m3s84). Full source: [softbots2013Code.tgz](http://jeffclune.com/codePublished/softbots2013Code.tgz) (a copy is in `research_reference/repositories/`).
  - The paper text does not state gravity, friction, damping, frequency or time step. It says "20% volumetric" actuation; the code gives ±14% linear, which is what the 2015 and 2018 papers state.
  - The paper itself describes the common no-cost body, the L-Walker, as "blocky", and reports that costs change the material mix and the body plans.
- **Hiller & Lipson (2014)**, the Voxelyze physics. [arXiv:1212.2845](https://arxiv.org/abs/1212.2845). The authors note that floor stiffness is tied to voxel stiffness and can allow significant floor penetration.
- **Later code in the same family**: evosoro (2017, Python 2, different defaults: 1 g, 4 Hz, stiffness ratio 100, damping 0.01), voxcraft-sim (GPU, last commit 2021). Neither is the 2013 configuration.

## 2. Has anyone reproduced it?

**No independent re-implementation with a comparison against the 2013 numbers was found, and no re-analysis of the deposited data.** What exists:

- Reuse of the authors' simulator for new questions: Methenitis et al. 2015, Mouret & Clune 2015, Gravina et al. 2017–2019 (below). None reports a side-by-side reproduction.
- Two unpublished student term papers (Swarthmore CS81, 2015) that reran the authors' code for a few runs.
- **Lehman et al. (Artificial Life 2020)**, "The surprising creativity of digital evolution", [arXiv:1803.03453](https://arxiv.org/abs/1803.03453): anecdotes, including these soft robots exploiting floor penetration and the time step. The only published record of contact artefacts in this system.

## 3. What bodies evolve, and when limbs appear

**Compact, filled, muscle-rich bodies are the default** under distance-only fitness on flat ground:

- Cheney et al. 2016 (ALIFE), "On the difficulty of co-optimizing morphology and control": bodies lock in within about 100 generations. DOI [10.7551/978-0-262-33936-0-ch042](https://doi.org/10.7551/978-0-262-33936-0-ch042).
- Cheney et al. 2018 (J. R. Soc. Interface), "Scalable co-optimization of morphology and control": without protection of new bodies the result is a filled cube. [arXiv:1706.06133](https://arxiv.org/abs/1706.06133).
- Li, Matthews, Kriegman 2023, "Reinforcement learning for freeform robot design": a learned designer also grows large compact bodies. [arXiv:2310.05670](https://arxiv.org/abs/2310.05670).
- Miras et al. 2018 (ALIFE), rigid modular robots: selecting for speed alone gives mostly single-limb bodies; a penalty on limb length gives multi-limb bodies at a cost in speed.
- Kriegman, Cheney, Bongard 2018 (Scientific Reports), "How morphological development can guide evolution": four-legged trotters were a slow local optimum; rolling bodies were several times faster. [arXiv:1711.07387](https://arxiv.org/abs/1711.07387).

**Conditions reported to produce limbs or appendages:**

| Condition | Source |
|---|---|
| Material or energy costs | Cheney 2013; Cheney 2016; Corucci 2018 |
| Gravity | **Methenitis, Hennes, Izzo, Visser (GECCO 2015)**, "Novelty search for soft robotic space exploration", DOI [10.1145/2739480.2754731](https://doi.org/10.1145/2739480.2754731): same simulator and encoding; hopping at lunar gravity, legged bodies from Mars gravity up, two- and four-legged walkers with footfall diagrams at Earth gravity |
| Stiffness relative to weight | **Corucci et al. (Soft Robotics 2018)**, [arXiv:1711.06605](https://arxiv.org/abs/1711.06605): legs need material stiff enough to carry the body |
| Environments other than open flat ground | Corucci 2018 (water); Cheney, Bongard, Lipson 2015, "Evolving soft robots in tight spaces", DOI [10.1145/2739480.2754662](https://doi.org/10.1145/2739480.2754662) |
| Per-voxel phase control, with protection of new bodies | Cheney 2018 |
| A reward that names posture, or uneven terrain | Li, Kong, Kriegman (ICLR 2025), "Generating freeform endoskeletal robots", [arXiv:2412.01036](https://arxiv.org/abs/2412.01036) |
| Gradient-based design | Matthews et al. (PNAS 2023), "Efficient automatic design of robots", [arXiv:2306.03263](https://arxiv.org/abs/2306.03263); Strgar et al. (RSS 2024), [arXiv:2405.14712](https://arxiv.org/abs/2405.14712) |

**What is missing.** Limb claims rest on pictures of selected individuals. Each study that gives numbers uses its own measure (branching index in Corucci 2018; limb descriptors for rigid robots in Miras 2018). No study reports the fraction of runs that end limbed, and none varies these factors together.

**2D analogues with explicit shape classes**: Medvet et al. (GECCO 2021), "Biodiversity in evolved voxel-based soft robots", DOI [10.1145/3449639.3459315](https://doi.org/10.1145/3449639.3459315), classify bodies as Blob / Legged / Other; with sensing controllers the legged ones were fastest. Pigozzi et al. (ACM TELO 2023), "Factors impacting diversity and effectiveness of evolved modular robots", DOI [10.1145/3587101](https://doi.org/10.1145/3587101): encoding and terrain, more than the search algorithm, shift the share of limbed bodies.

## 4. Search algorithms on this problem

| Study | System, budget | Runs | Result on the champion |
|---|---|---|---|
| Mouret & Clune 2015, [arXiv:1504.04909](https://arxiv.org/abs/1504.04909) | Cheney system | 5–8 | MAP-Elites: better map, champion not significantly different |
| Methenitis et al. 2015 | Cheney system, 30k evaluations | 10 | Novelty search equal or better than fitness search, no test |
| **Gravina, Liapis, Yannakakis (GECCO 2018)**, "Fusing novelty and surprise for evolving robot morphologies", DOI [10.1145/3205455.3205503](https://doi.org/10.1145/3205455.3205503) | Cheney system, 30k evaluations, 0.4 s per evaluation | **90** | At 10³: objective search 9.29 body lengths, novelty 11.32, surprise 11.18, both combined 12.05. Trajectory-based novelty beats plain CPPN-NEAT at every lattice size |
| Gravina et al. (GECCO Companion 2019), "Blending notions of diversity for MAP-Elites", DOI [10.1145/3319619.3321987](https://doi.org/10.1145/3319619.3321987) | Cheney system at 5³, 300k | 10 | Biased parent selection beats uniform MAP-Elites on best fitness |
| Nordmoen et al. 2021, [arXiv:2012.04375](https://arxiv.org/abs/2012.04375) | Rigid modular, direct encoding, 100k | 30 | MAP-Elites wins |
| Zardini et al. (GECCO 2021), [arXiv:2104.12175](https://arxiv.org/abs/2104.12175) | Tensegrity soft robots, 45k | 10 | A NEAT-based method beats plain MAP-Elites in one of two tasks |
| Pigozzi et al. 2023 | 2D voxel robots, 30k | 10 | MAP-Elites over size, elongation, compactness: slightly lower effectiveness |
| Mertan & Cheney 2025, [arXiv:2508.17464](https://arxiv.org/abs/2508.17464) | 2D, exhaustive landscape | 100 | Age-fitness Pareto and MAP-Elites indistinguishable |
| Le Goff, Smith, Hart 2026, [arXiv:2606.11037](https://arxiv.org/abs/2606.11037) | Rigid robots, 10k | 20 | MAP-Elites does not raise the best score |

Take-aways:

- "MAP-Elites gives the population, plain evolution the champion" is published several times over. It is not a new claim.
- In this very system, diversity-driven search with a **trajectory** descriptor beats objective search. An algorithm-comparison paper would need that arm.
- Not found: a head-to-head of speciated CPPN-NEAT, age-fitness Pareto and MAP-Elites on one 3D voxel system; a sample-efficiency study; the number of separate ground-contact patches used as an archive dimension.
- Newer quality-diversity methods (CMA-ME, CMA-MAE, Dominated Novelty Search [arXiv:2502.00593](https://arxiv.org/abs/2502.00593)): no morphology application found.

## 5. Body and control together, or one after the other

- **Mertan & Cheney (EuroGP 2024)**, "Investigating premature convergence in co-optimization of morphology and control", [arXiv:2402.09231](https://arxiv.org/abs/2402.09231). Evolution Gym (2D), 10 runs per setting. Bodies evolved under a fixed controller beat co-optimised ones in all four settings; freezing those bodies and then evolving a controller beat co-optimisation in three of four. The authors present it as an analysis, not a method: budgets are unmatched, and the learned controller ended below the fixed one on those bodies in three of four settings.
- **Mertan & Cheney 2025** (ALIFE, then Artificial Life), "Evolutionary brain-body co-optimization consistently fails to select for morphological potential", [arXiv:2508.17464](https://arxiv.org/abs/2508.17464). 100 runs per algorithm on an exhaustively mapped body space.
- Mertan & Cheney 2023 (GECCO), modular controllers, [arXiv:2306.09358](https://arxiv.org/abs/2306.09358); 2025 (GECCO), controller distillation in MAP-Elites, [arXiv:2504.06523](https://arxiv.org/abs/2504.06523).
- **In 3D**: Cheney 2016 froze bodies as a diagnosis; Cheney 2018 interleaves protection instead of staging; Strgar & Kriegman 2025, [arXiv:2502.10862](https://arxiv.org/abs/2502.10862), stage the controller first; Candiello et al. 2026, [arXiv:2603.06497](https://arxiv.org/abs/2603.06497), compared sequential with joint design of 3D soft robots on one run each and found joint better.
- **No multi-seed 3D test of body-first against matched co-evolution was found.** That is the open experiment, and the group most likely to run it is Mertan & Cheney, who name harder design spaces and other simulators as future work.

## 6. Simulators and validation

| Simulator | Dimension | State in November 2026 |
|---|---|---|
| Voxelyze / VoxCad | 3D | Last push 2015–2016 |
| 2013 code (authors' tarball) | 3D | Available; ships a Makefile for the headless simulator |
| evosoro | 3D | 2018, Python 2 |
| voxcraft-sim | 3D, GPU | Last commit 2021, old CUDA |
| RISE (Li, Kong, Kriegman 2025) | 3D, GPU | Closed binary, Linux, described by its authors as unfinished |
| Evolution Gym | 2D | Maintained; the de facto benchmark of the 2023–2026 literature |
| 2D-VSR-Sim / 2D-MR-Sim | 2D | Active |
| Genesis, MuJoCo flex | 3D | Very active general engines, no voxel-robot benchmark |

- No published MuJoCo engine with Voxelyze-style mechanics was found, and no 3D successor to Evolution Gym.
- Simulated and physical voxel robots disagree in telling ways: Kriegman et al. (RoboSoft 2020), [arXiv:1911.10290](https://arxiv.org/abs/1911.10290), found that the two best designs moved in opposite directions in simulation and reality. Kriegman et al. (PNAS 2020), DOI [10.1073/pnas.1910837117](https://doi.org/10.1073/pnas.1910837117), filtered designs for robustness before building them.
- So Voxelyze is a reference implementation, not ground truth. The defensible claim for a re-implementation is equivalence to the 2013 code, plus an honest sensitivity analysis.

## 7. Reproducibility as a paper type

- López-Ibáñez et al. (ACM TELO 2021), "Reproducibility in evolutionary computation", DOI [10.1145/3466624](https://doi.org/10.1145/3466624): new artefacts with the same experiment is a *replicability* study.
- GECCO's BBSR track (Benchmarking, Benchmarks, Software and Reproducibility) names reproduction studies in its call. Its one replication paper so far, Karns & Desell (GECCO 2025), DOI [10.1145/3712256.3726458](https://doi.org/10.1145/3712256.3726458), follows the pattern: reproduce, find an overlooked factor, add something new.

## 8. The frontier a pure-evolution paper sits beside

Gradient-based design builds a walker in seconds (Matthews 2023). Generative and language-model designers exist too: DiffuseBot (2023, diffusion with differentiable physics), and MorphVAE (2024) and LASeR (ICLR 2025) on 2D voxel robots. These methods rely on differentiable physics, a learning inner loop or small 2D grids, and the ones read in full report 3 to 6 seeds. A paper from this project should position itself as controlled, well-replicated evidence on a non-differentiable 3D system, not as the state of the art in design.

## 9. How results are reported in this literature

- Runs per condition: 10 is the floor (Zardini, Medvet, Pigozzi), 20 to 30 is common, the decisive papers use 90 to 100.
- Two-sided Mann-Whitney U on end-of-run values, Holm or Bonferroni correction, bootstrapped 95% intervals, best-of-run curves, pictures of the top bodies.
- Effect sizes are rare. Reporting one puts a paper above the usual bar.
- With 3 seeds per arm an exact Mann-Whitney test cannot go below p = 0.10.

## 10. Gaps this project could fill

1. **An independent reproduction and audit of the 2013 benchmark** (the plan's paper 1).
2. **Body-first against matched co-evolution in 3D**, with enough paired seeds.
3. **A quantitative account of when limbs appear**, with a stated limb measure and the fraction of runs ending limbed.
4. Smaller: parent selection in MAP-Elites at small budgets; contact-patch count as an archive dimension.

## 11. What the survey did not cover

- Google Scholar directly.
- A final sweep of the GECCO 2026 and ALIFE 2026 proceedings, and a dedicated search for seed-variance studies in evolutionary robotics (the search allowance ran out).
- Several publisher pages sit behind bot checks (MIT Press, ACM Digital Library, PNAS); those entries were read from author copies, arXiv or Europe PMC, as marked in the notes.
