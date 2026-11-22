# Literature and tooling survey 4: simulators, benchmarks, validation, reproducibility

Survey date: 18 November 2026. Scope: evolved voxel-based soft robots.

How to read this file
- **[V]** = I opened a page for the item in this session (URL given) and the stated facts come from it.
- **[V-local]** = checked in the local reference folder `C:\SoftRobotEvolution\research_reference\extracted`.
- **[S]** = seen only in a search-result summary; the page itself was not opened. Treat as probably right, not confirmed.
- **UNVERIFIED** = from memory or inference; do not cite without checking.
- Repository dates come from the GitHub API (`pushed_at`) or the repository's commit list.
- Limits of this survey: the shared web-search budget ran out before I had finished the replication-study and cross-simulator searches. Pages that refused access (HTTP 403): ACM badging policy, ACM TELO author guidelines, MDPI Biomimetics review, one University of Trieste PDF, PubMed Central.
- Text from papers is paraphrased, not quoted.

---

## 1. The Voxelyze family

### 1.1 Voxelyze (Hiller and Lipson) [V]
- Paper: J. Hiller, H. Lipson, "Dynamic Simulation of Soft Multimaterial 3D-Printed Objects", Soft Robotics 1(1):88-101, 2014. DOI 10.1089/soro.2013.0010 (Crossref: 156 citing works). Preprint: "Dynamic Simulation of Soft Heterogeneous Objects", arXiv:1212.2845 (2012). https://arxiv.org/abs/1212.2845
- Repository: https://github.com/jonhiller/Voxelyze . Created 7 Nov 2014, last push 26 Jan 2016, 33 commits, 85 stars, no licence field, not archived. README: general-purpose multi-material voxel simulation library, compiles on Windows and Linux, OpenMP via `USE_OMP`. Issue tracker: 5 items in total, the last one (Apr 2024) about a NaN assert under high density or gravity.
- Status in 2026: unmaintained for ten years. Still the reference that everything else descends from.
- What the paper itself validates [V-local, 2012 preprint text]:
  - Static cantilever: thin beam 0.822 mm simulated against 0.823 mm analytical (0.1%); thick beam 0.538 mm against 0.546 mm from a direct-stiffness FEA (1.5%).
  - Dynamic: modal frequencies of a 20x1x1 beam, simulated against analytical: 404 vs 389 Hz (mode 1, +3.9%) up to 34,290 vs 31,180 Hz (mode 6, +10%). Note: the table shows the simulation HIGHER than theory while the surrounding text says "slightly lower". This inconsistency is in the preprint; check the journal version before citing either direction.
  - No physical experiment in this paper. Validation is against beam theory and FEA only.
  - Floor model: the authors state that the floor contact stiffness is tied to the voxel stiffness (so that it does not shorten the stable time step) and that this allows significant floor penetration in some cases, with qualitatively appropriate behaviour. So floor penetration is a documented property of the reference model, not only of a re-implementation.
- Relevance: gives the exact acceptance tests a re-implementation should reproduce (Tables 1 and 2), and documents that the original floor is soft by design.

### 1.2 VoxCAD (GUI) [V]
- https://github.com/jonhiller/VoxCAD . Last commit 14 Aug 2015. Unmaintained.

### 1.3 Cheney et al. 2013 code and data [V] [V-local]
- Paper: N. Cheney, R. MacCurdy, J. Clune, H. Lipson, "Unshackling evolution: evolving soft robots with multiple materials and a powerful generative encoding", GECCO 2013, pp. 167-174, DOI 10.1145/2463372.2463404. Reprinted in ACM SIGEVOlution 7(1):11-23, DOI 10.1145/2661735.2661737 [S].
- Data: Dryad, DOI 10.5061/dryad.m3s84, published 7 Oct 2014, 19.96 MB. https://datadryad.org/dataset/doi:10.5061/dryad.m3s84 . Files: `softbots2013Config.tgz` (1.5 kB: HyperNEAT parameter file), `softbots2013Gen1000.tgz` (11.3 MB: generation-1000 robots as .vxa), `softbots2013GenchampData.tgz` (8.6 MB: per-run best and average fitness per generation), and a code README.
- Source code is NOT in Dryad. The Dryad README points to http://jeffclune.com/codePublished/softbots2013Code.tgz . I checked the link with a header-only request on 18 Nov 2026: HTTP 200, 15.9 MB, Last-Modified 25 Apr 2026. It is a personal web host, not an archive with a DOI, so it can disappear.
- GitHub copy: https://github.com/CreativeMachinesLab/softbotEvolution . Created 30 Aug 2014, last push 21 Sep 2016, 35 commits, 18 stars, no licence. README says the "base" version is the closest to the original but differs from the paper: the bounding box around the robot was removed. One open issue (a suggestion about parallel processing). No discussion of parameters.
- Parameters in the generating source `HCUBE_SoftbotsExperiment.cpp` [V-local]: GravAcc -27.468 (2.8 g), TempAmp 39, TempBase 25, TempPeriod 0.025 s (40 Hz), CTE +0.01 / -0.01 / 0, Elastic_Mod 1e7 (one material with an evolved-range stiffness written as N e+006), Density 1e6, Poisson 0.35, uStatic 1, uDynamic 0.5, DtFrac 0.9, BondDampingZ 1, ColDampingZ 0.8, SlowDampingZ 0.001, ColSystem 3, SelfColEnabled 1, Integrator 0, **PoissonKickBackEnabled 0**.
- Paper text [V-local]: says "20% volumetric" actuation and that all organisms, data, source code and parameter settings are archived at Dryad. It does not state gravity or frequency.
- Flag for the replication: every deposited .vxa I sampled has `PoissonKickBackEnabled` 0, and the 2013 simulator defaults it to false. Before claiming that the new engine follows "Voxelyze's volumetric (Poisson) law", check in the 2013 `VX_Bond`/`VX_Voxel` code what this flag switches off. The Poisson coupling in the later rewritten Voxelyze (2014-2016, `VX_Link.cpp`/`VX_Voxel.cpp`) may not be what ran in 2013. I could not check this: only `VX_Sim.cpp` of the 2013 code is in the extracted folder.

### 1.4 Later papers that document the 2013-style parameters [V]
- N. Cheney, J. Bongard, H. Lipson, "Evolving Soft Robots in Tight Spaces", GECCO 2015. PDF: https://www.uvm.edu/neurobotics/pubs/pdf/2015_CheneyBongardLipson_EvolvingSoftRobotsInTightSpaces_GECCO.pdf . Code with config file: https://github.com/CreativeMachinesLab/softbotEscape (the paper's short link git.io/vfSLV redirects there).
  - States the actuation amplitude explicitly: 14% linear contraction/expansion, about 48% volumetric change. Evaluation lasts 20 actuation cycles. Young's modulus 10 MPa (stiff treatment) and 1 MPa (soft treatment).
  - Says that contraction size, contraction rate, stiffness, evaluation length and other parameters were set arbitrarily or taken from the 2013 paper's values.
  - Reports a time-step artefact itself: fitness was measured at the last time step, chosen to fall at the end of an actuation cycle; because of the finite time step the muscles were not exactly at rest size at that instant, which the authors offer as one possible cause of the single-material bodies that evolved.
  - Does not mention gravity.
- N. Cheney, J. Bongard, V. SunSpiral, H. Lipson, "Scalable Co-Optimization of Morphology and Control in Embodied Machines", arXiv:1706.06133 (J. R. Soc. Interface 2018: journal reference UNVERIFIED). States muscle actuation of plus/minus 14% of length, i.e. plus/minus 48% of volume; 20 actuation cycles. No gravity, stiffness, friction or time-step values.
- F. Corucci, N. Cheney, F. Giorgio-Serchi, J. Bongard, C. Laschi, "Evolving Soft Locomotion in Aquatic and Terrestrial Environments: Effects of Material Properties and Environmental Transitions", Soft Robotics 5(4):475-495, 2018, DOI 10.1089/soro.2017.0055, arXiv:1711.06605. Uses evosoro. Says gravity is analogous to Earth's. Does not document Cheney 2013's settings.
- Conclusion: the amplitude is documented in later papers as 14% linear / 48% volumetric. The 2.8 g gravity and the 40 Hz frequency of the 2013 runs are documented nowhere that I found except the deposited code.

### 1.5 Where the TempAmp to strain mapping is written down [V]
- Not in any issue or README. It is in the code. evosoro's Voxelyze fork, `VX_Environment.cpp`: https://raw.githubusercontent.com/skriegman/evosoro/master/evosoro/_voxcad/Voxelyze/VX_Environment.cpp
  - On reading a .vxa: if `TempAmplitude` is absent and `TempAmp` is present, then `TempAmplitude = TempAmp - TempBase`.
  - Temperature: `TempBase + TempAmplitude * sin(2*pi*t/TempPeriod + phase)`.
  - Size factor [V-local, 2013 `VX_Sim.cpp` line 918]: `1 + (MatTemp - TempBase) * CTE`.
  - So TempAmp 39, TempBase 25, CTE 0.01 gives a linear strain amplitude of 0.14: +14% length is +48% volume (1.14 cubed), -14% length is -36% volume. This matches the 14% / 48% wording of the 2015 and 2018 papers and does not match "20% volumetric" in the 2013 text.
  - Caveat: I verified the `TempAmp - TempBase` line in evosoro's fork only. Confirm that the 2013 tarball's `VX_Environment.cpp` has the same line.
- Gravity: evosoro's `VX_Environment.cpp` defaults GravAcc to -9.81 and evosoro's `read_write_voxelyze.py` writes -9.81. https://raw.githubusercontent.com/skriegman/evosoro/master/evosoro/tools/read_write_voxelyze.py . No comment or issue anywhere discusses the 2013 value of -27.468.

### 1.6 evosoro [V]
- S. Kriegman, C. Cappelle, F. Corucci, A. Bernatskiy, N. Cheney, J. Bongard, "Simulating the evolution of soft and rigid-body robots", GECCO 2017 Companion, pp. 1117-1120, DOI 10.1145/3067695.3082051.
- https://github.com/skriegman/evosoro . Created Nov 2016, last push 12 Dec 2018, 65 commits, 125 stars, MIT. Python 2.7, networkx below 2.0, Linux build scripts. README says its Voxelyze copy diverged from the main VoxCad/Voxelyze branch some time ago.
- 14 issues in total, none about TempAmp, strain, gravity, frequency or stiffness. Recent ones are install failures: libqwt-dev missing on Ubuntu 20.04 (Dec 2020), a request for a working install guide (Mar 2025).
- Defaults [V]: `Env(frequency=4.0, ..., lattice_dimension=0.01, fat_stiffness=5e6, bone_stiffness=5e8, muscle_stiffness=5e6, temp_amp=39)`, `Sim(dt_frac=0.7, simulation_time=10, ...)`, TempBase 25, CTE 0.01, GravAcc -9.81, SlowDampingZ 0.01, uStatic 1, uDynamic 0.5, Density 1e6, Poisson 0.35. https://raw.githubusercontent.com/skriegman/evosoro/master/evosoro/base.py
- Differences from the 2013 deposit: gravity 1 g instead of 2.8 g; 4 Hz instead of 40 Hz; bone/fat stiffness ratio 100 instead of the 2013 setting; SlowDampingZ 0.01 instead of 0.001; DtFrac 0.7 instead of 0.9. Same TempAmp 39.
- Status in 2026: dead (Python 2). Related: https://github.com/skriegman/reconfigurable_organisms (766 stars, Python 2.7, Voxelyze plus VoxCad; code for the 2020 PNAS paper).

### 1.7 voxcraft-sim [V]
- S. Liu, D. Matthews, S. Kriegman, J. Bongard, "Voxcraft-sim, a GPU-accelerated voxel-based physics engine", 2020, Zenodo DOI 10.5281/zenodo.3835152. No peer-reviewed paper.
- https://github.com/voxcraft/voxcraft-sim . Created 20 May 2020; last commit on master 18 Nov 2021; API `pushed_at` 9 Aug 2022; 33 commits; 55 stars; CC0. Needs CUDA 10.1, CMake 3.12+, Boost; Docker or Google Colab recommended; Linux. 6 open issues; a Windows install question from Oct 2022 has no reply.
- Evidence from its issue tracker:
  - #41 (Feb 2021): same .vxa behaves differently in voxcraft and in the reconfigurable_organisms simulator. The maintainer's answer, paraphrased: two simulators are not expected to match out of the box; amplitude and phase offsets may be read differently. The cause turned out to be the viewer (no phase offset in VoxCAD/voxcraft-viz). The maintainer also says the team is stretched thin. https://github.com/voxcraft/voxcraft-sim/issues/41
  - #39 (Jan 2021): explosions and detaching voxels during a MAP-Elites run; attributed to soft material (low modulus to density ratio) and to neighbours with opposite-sign CTE; stiffer material reduced but did not remove the problem. https://github.com/voxcraft/voxcraft-sim/issues/39
  - #45 (Mar 2021): materials with a stiffness to density ratio near 1e6 cannot be handled natively; the time step becomes tiny. https://github.com/voxcraft/voxcraft-sim/issues/45
  - #31, #32 (Dec 2020): robots that jump suddenly as the time-step fraction is varied; closed without a technical answer.
- Used in: F. Pigozzi, S. Woodman, E. Medvet, R. Kramer-Bottiglio, J. Bongard, "Morphology Choice Affects the Evolution of Affordance Detection in Robots", GECCO 2023, pp. 211-219, DOI 10.1145/3583131.3590505 [S]. Kinematic self-replication (PNAS 2021) and the fractal-robots paper (arXiv:2103.04876): UNVERIFIED in this session.
- I found no 2024-2026 paper confirmed to use voxcraft-sim. The 2024-2026 soft-robot co-design papers in the local reference folder all use Evolution Gym [V-local].
- Status in 2026: dormant for four to five years; hard to build (CUDA 10.1).

### 1.8 RISE, the Kriegman lab's 2024-2025 voxel simulator [V]
- M. Li, L. Kong, S. Kriegman, "Generating Freeform Endoskeletal Robots", ICLR 2025 (spotlight), arXiv:2412.01036. https://arxiv.org/abs/2412.01036 , https://endoskeletal.github.io
- Code: https://github.com/phenoweave/endoskeletal (linked from the project page as iffiX/endoskeletal). 6 commits, 12 stars. The simulator ("RISE") ships as precompiled Python-importable CUDA libraries (CUDA 11.8 or 12.1, GPU compute capability 6.0 or higher, Linux, Ubuntu 22.04 preferred). README says the simulator is unfinished and that future versions will look very different.
- Physics: soft voxels are point masses with rotational inertia joined by massless Euler-Bernoulli beams, following Hiller and Lipson 2014; rigid "bones" are compound rigid bodies with joint constraints solved by projected Gauss-Seidel; static friction 1, dynamic 0.8. 3D. Massively parallel.
- Validation: the paper reports none against Voxelyze, beam theory or hardware.
- Relevance: this is the nearest thing to a current 3D voxel soft-robot platform, and the paper presents it as a benchmark platform. It is a closed binary, Linux and NVIDIA only, and not based on MuJoCo. It shows that re-implementing Hiller-Lipson mechanics on a new substrate is an accepted thing to do at a top venue, even without published validation.

### 1.9 Other Voxelyze-style or mass-spring GPU engines [V]
- J. Clay, S. Wyetzner, A. Gaudio, B. Xia, A. Moshova, J. Austin, M. Segan, H. Lipson, "A Massively-Parallel 3D Simulator for Soft and Hybrid Robots" (Cronos), arXiv:2207.09334, 2022. CUDA mass-spring; validated against Euler-Bernoulli beam theory, natural frequencies and data from a physical soft structure. Preprint only.
- J. Austin, R. Corrales-Fatou, S. Wyetzner, H. Lipson, "Titan: A Parallel Asynchronous Library for Multi-Agent and Soft-Body Robotics using NVIDIA CUDA", arXiv:1911.10274 (ICRA 2020 per a secondary listing [S]).
- Maintenance status of both: not checked.

---

## 2. Benchmarks and other simulators

### 2.1 Evolution Gym [V] [V-local]
- J. Bhatia, H. Jackson, Y. Tian, J. Xu, W. Matusik, "Evolution Gym: A Large-Scale Benchmark for Evolving Soft Robots", NeurIPS 2021 (Advances in NeurIPS 34, pp. 2201-2214), arXiv:2201.09863.
- https://github.com/EvolutionGym/evogym . 263 stars, MIT. Last commit on main 5 Jun 2025 (dataset release: 90k+ robot structures, 2.5k+ policies). July 2024 update: Gymnasium support, pip install. Python 3.7 to 3.10. No releases page.
- 2D mass-spring system (stated in the paper). CPU, C++ core. The paper says its closest comparison is other 2D voxel simulators.
- Status in 2026: lightly maintained, and the de facto standard. Every 2024-2026 co-design paper in the local folder uses it (Mertan and Cheney 2024 and 2025, MorphVAE 2024, adaptive-control 2026, GNN co-design 2026), as do arXiv:2609.29491 and arXiv:2609.29490 (both Aug 2026) [V].
- Derivatives, all 2D:
  - EvoGymCM: L. Shen, K. Huang, W. Zhao, H. Liu, arXiv:2604.08258 (Apr 2026, under review at IROS 2026). Continuous stiffness as a design variable. No code link on the arXiv page.
  - ModularEvoGym: https://github.com/Yuxing-Wang-THU/ModularEvoGym (described as 2D; last push Nov 2023).
  - jax-evogym: https://github.com/btgaskin/jax-evogym . JAX re-implementation, public alpha, 0 stars, no paper. Notable for its method: "reference-parity tests" against checked-in EvoGym traces with documented tolerances, with an explicit statement that parity is shown for the documented task set only.
- **3D successor: none found.** I searched for "EvoGym 3D" and variants and looked at the GitHub organisation listing in search results; nothing. Not exhaustive (search budget ran out).

### 2.2 2D-VSR-Sim and 2D-MR-Sim [V]
- E. Medvet, A. Bartoli, A. De Lorenzo, S. Seriani, "2D-VSR-Sim: A simulation tool for the optimization of 2-D voxel-based soft robots", SoftwareX 12:100573, 2020 (citation as given in a 2026 paper's reference list). Long version: "Design, Validation, and Case Studies of 2D-VSR-Sim, an Optimization-friendly Simulator of 2-D Voxel-based Soft Robots", arXiv:2001.08617.
- https://github.com/ericmedvet/2dhmsr : last commit 22 Dec 2022. Superseded by https://github.com/ericmedvet/2dmrsim (2D-MR-Sim; Java, dyn4j engine, Apache-2.0, 650 commits, last commits 8 Sep 2026, dyn4j 6.0.0). Active.
- How that simulator paper validated itself: (i) mechanical characterisation with cantilever tests under constant and impulse loads; (ii) qualitative repetition of three earlier studies (Hiller and Lipson 2012 body optimisation, Kriegman et al. 2018 development, Talamini et al. 2019 sensing controllers), stating openly that exact reproduction was not the aim because the originals were 3D. No hardware validation.
- Relevance: a published precedent for "new simulator, validated by beam tests plus qualitative repetition of known results".

### 2.3 Differentiable and MPM platforms [V]
- SoftZoo: T.-H. Wang, P. Ma, A. Spielberg, Z. Xian, H. Zhang, J. Tenenbaum, D. Rus, C. Gan, ICLR 2023, arXiv:2303.09555. https://github.com/zswang666/softzoo . 3D differentiable MPM on Taichi 1.4.1; terrains from ice to ocean. Last commit 17 Jul 2023. 69 stars. Unmaintained.
- DiffTaichi: Y. Hu et al., ICLR 2020, arXiv:1910.00935.
- ChainQueen: Y. Hu et al., arXiv:1810.01054 (ICRA 2019; arXiv page says "submitted to").
- PlasticineLab: Z. Huang et al., ICLR 2021 (spotlight), arXiv:2104.03311.
- D. Matthews, A. Spielberg, D. Rus, S. Kriegman, J. Bongard, "Efficient automatic design of robots", PNAS 120(41) e2305180120, 2023, arXiv:2306.03263. https://github.com/robodiff/robodiff . Gradient-based design; one robot built. Simulator details (2D? MPM?): UNVERIFIED.
- L. Strgar, D. Matthews, T. Hummer, S. Kriegman, "Evolution and learning in differentiable robots", arXiv:2405.14712 (2024). Massively parallel differentiable simulation; one physical robot retained its behaviour.
- H. Kobayashi et al., "Automated design of soft-rigid hybrid robots for dynamic locomotion", arXiv:2605.29389 (May 2026). Differentiable MPM plus XPBD; fabricated and tested.
- Relevance: different physics (continuum MPM), not Voxelyze-compatible; useful only as contrast.

### 2.4 Rod, continuum and FEM tools [V]
- SoMoGym: M. Graule, T. McCarthy, C. Teeple, J. Werfel, R. Wood, IEEE RA-L 7(2):4071-4078, 2022 [S]. PyBullet rigid-link approximation. https://github.com/GrauleM/somogym
- Elastica: N. Naughton, J. Sun, A. Tekinalp, G. Chowdhary, M. Gazzola, arXiv:2009.08422. Cosserat rods. (RA-L 2021 venue: UNVERIFIED.)
- SoRoMoX: M. Stoelzle et al., arXiv:2608.06650 (Aug 2026). JAX/Warp rod models on GPU.
- DisMech-RL: A. Choi, D. Tong, X. Huang, arXiv:2511.06667, accepted at IROS 2026. Includes a "sim-to-sim gap" test: train in one simulator, test in another. https://github.com/QuantuMope/dismech-rl
- SOFA: SofaGym, https://github.com/SofaDefrost/SofaGym (targets SOFA v23.06; Schegg et al., Soft Robotics). C. Schaff, A. Sedal, M. Walter, "Soft Robots Learn to Crawl", arXiv:2202.04575: FEM with model order reduction, zero-shot hardware transfer (the abstract does not name SOFA). SORS: M. Mekkattu, M. Michelis, R. Katzschmann, arXiv:2512.15994 (Dec 2025), FEM simulator validated against cantilever, pneumatic arm and contact data. M. Dubied et al., "Sim-to-real for soft robots using differentiable FEM", IEEE RA-L 7:5015-5022, 2022 (citation from a reference list).
- I found no paper that evolves voxel morphologies in SOFA.

### 2.5 General-purpose engines with soft bodies [V]
- **Genesis** (now "Genesis World"): https://github.com/Genesis-Embodied-AI/Genesis . Apache-2.0, 30.3k stars, Linux/Windows/macOS. Rigid, FEM, MPM, PBD/SPH, IPC and SAP couplers. Latest release v1.4.7, published 17 Nov 2026. That release alone fixes: FEM bodies sinking through the floor, an explicit stable Neo-Hookean material that was too soft, FEM damping errors, early-terminating implicit solves, wrong FEM-FEM contact stiffness. v1.4.6 fixed FEM muscle actuation being ignored by the implicit solver. Very active; soft-body correctness is still moving.
- **Newton**: https://github.com/newton-physics/newton . Linux Foundation project started by Disney Research, Google DeepMind and NVIDIA; built on Warp; MuJoCo Warp as primary rigid backend; VBD, MPM and Style3D examples for soft bodies and cloth; Apache-2.0; 6.0k stars; NVIDIA GPU (macOS CPU only). Version 1.0 in March 2026 [S].
- **MuJoCo**: latest 4.0.1 (11 Nov 2026); 4.0.0 on 6 Nov 2026; 3.17.0 on 22 Oct; 3.16.0 on 14 Oct; 3.15.0, 3.14.0, 3.13.0, 3.12.0 between 20 Aug and 5 Oct 2026. https://mujoco.readthedocs.io/en/latest/changelog.html
  - 3.16.0: corrected the shear contribution to stiffness of interpolated flexes; material parameters now give standard isotropic linear elasticity; existing models can change behaviour.
  - 3.17.0: fixed interpolated flexcomp elasticity being dropped when the first cell is empty; other flex elasticity fixes; self-collision for interpolated flexes.
  - 4.0.0: fixed the elastic constants of non-interpolated flexes. The 3D Saint Venant-Kirchhoff term had used twice the first Lame parameter; 2D stretching and bending constants were also wrong. Models become stiffer except 3D models with zero Poisson ratio. Also: `composite` element and `cable` plugin removed; elasto-plasticity added; RK4 now fourth-order accurate for free-joint orientations (changes results for free bodies under RK4); Python 3.10 dropped; packaging split.
  - Consequence: flex results obtained on MuJoCo 3.4 were computed with elastic constants that the developers have since corrected, and will not reproduce numerically on 4.x. An engine that uses MuJoCo only for rigid free bodies plus its own explicit beam forces does not depend on any of this. Pin the MuJoCo version in the paper.
- **MJX / Brax**: a Brax maintainer wrote in Dec 2023 that soft bodies were not expected in MJX/Brax soon. https://github.com/google/brax/discussions/432 . **MuJoCo Warp**: flex marked experimental, not all features implemented; differentiability not yet available. https://github.com/google-deepmind/mujoco_warp
- Soft-robot papers on MuJoCo: C. Shentu et al., "Do Rigid-Body Simulators Dream of Soft Robots?", arXiv:2606.22397 (Jun 2026): a tendon-driven continuum robot as a continuum-mechanics-informed discretisation into rigid bodies inside MuJoCo, validated against a Cosserat-rod reference and hardware (a search summary gives 7.7 mm mean tip error, 4.1% of length [S]). This is the closest published precedent for "soft robot = rigid bodies plus elastic coupling in MuJoCo". I found no peer-reviewed soft-robot paper built on MuJoCo flex.
- Isaac Sim / Isaac Lab deformables: not checked.

### 2.6 Is "Voxelyze mechanics on MuJoCo" new? [V]
- GitHub repository search (API): "mujoco voxel soft robot" 0 results; "soft robot evolution mujoco" 0 results; "mujoco voxel" 1 unrelated result; "voxel soft robot" 9 results, none on MuJoCo; "voxelyze" 48 results, none of the 18 I could read mentions MuJoCo.
- Web searches for a MuJoCo voxel soft-robot framework returned the researcher's own public repository as the nearest match, and otherwise only EvoGym work.
- One existing MuJoCo voxel project: **MorphVSR**, https://github.com/Hadi-Khan-Projects/VoxelSoftRobots . A final-year MEng project (University College London), 30 commits, Jan to May 2025, 0 stars, no paper. 3D voxel robots as a MuJoCo `flexcomp` of tetrahedra (Young 250, Poisson 0.3, implicitfast, 1 ms) actuated by spatial-tendon motors; controller optimisation and co-evolution. It is FEM flex plus tendons. It does not implement Voxelyze beams, its friction, its collision scheme or its time-step rule.
- arXiv:2609.29490 (RoboLDA, Aug 2026) ships scripts that turn voxel matrices into URDF/MuJoCo XML for rigid robots only.
- **Answer: no published MuJoCo-based Voxelyze-style engine found.** Safe wording: "to our knowledge the first". Cite MorphVSR and RISE as the nearest neighbours.
- Related MuJoCo evolutionary-robotics framework (rigid modular robots): Revolve2, https://github.com/ci-group/revolve2 (LGPL-3.0, 267 commits).

---

## 3. Evidence on fidelity

### 3.1 Sim-to-real with Voxelyze-type models [V]
- J. Hiller, H. Lipson, "Automatic Design and Manufacture of Soft Robots", IEEE Trans. Robotics 28(2):457-466, 2012, DOI 10.1109/TRO.2011.2172702. Abstract: cantilever beams confirmed physically within 0.5 to 7.6%; one evolved locomotion robot built and confirmed with 15% error. https://blogs.cornell.edu/maepubs/2012/04/01/new-article-automatic-design-and-manufacture-of-soft-robots
- S. Kriegman, A. Mohammadi Nasab, D. Shah, H. Steele, G. Branin, M. Levin, J. Bongard, R. Kramer-Bottiglio, "Scalable sim-to-real transfer of soft robot designs", RoboSoft 2020, DOI 10.1109/RoboSoft48309.2020.9116004, arXiv:1911.10290. Read via https://ar5iv.labs.arxiv.org/html/1911.10290
  - Simulator: Voxelyze on CPU; exhaustive search over 6,561 designs.
  - 108 designs fabricated; 9 actuated and measured, three trials each.
  - By net displacement the gap looked small and the two best designs ranked best in both worlds. But those two moved in OPPOSITE directions in simulation and reality (pushing versus pulling), headings disagreed across the nine, and the velocity gap was wider.
  - A grid search over friction and a finer 3x3x3 sub-voxel resolution found no friction pair that gave the right heading for all nine designs. The authors conclude that the Coulomb friction model may be insufficient for this kind of movement.
- S. Kriegman, D. Blackiston, M. Levin, J. Bongard, "A scalable pipeline for designing reconfigurable organisms", PNAS 117(4):1853-1859, 2020, DOI 10.1073/pnas.1910837117. Read from https://meclab.w3.uvm.edu/papers/2020_PNAS_Kriegman.pdf
  - First pass, evolved "on land" with finely tuned actuation: high-performing but non-transferable designs with bounding gaits that had no ground contact for about 47% of the gait cycle.
  - Second pass: lower gravity (buoyancy) and a drag force. Ground contact rose from 52.7% to 93.3% of the evaluation and behaviour matched the organisms better.
  - A robustness filter (random perturbation of actuation phase) selected which designs to build, citing earlier work that noise resistance in simulation predicts transfer. Built organisms moved in the predicted direction (p < 0.01).
  - This is direct published evidence, from the Voxelyze lineage itself, that the gravity setting and the environment model decide which gaits evolve.
- J. Legrand, S. Terryn, E. Roels, B. Vanderborght, "Reconfigurable, Multi-Material, Voxel-Based Soft Robots", IEEE RA-L 8(3):1255-1262, 2023, DOI 10.1109/LRA.2023.3236883. Abstract [S]: a physical voxel gripper and walker behave like their simulations with RMS errors down to 10.4%. Simulator name: UNVERIFIED.
- S. Kriegman et al., "Automated shapeshifting for function recovery in damaged robots", RSS 2019, DOI 10.15607/RSS.2019.XV.028, arXiv:1905.09264. Simulator and hardware details: not checked.
- Physical "designed in simulation" robots 2023-2026: Matthews et al. PNAS 2023; Strgar et al. 2024; Kobayashi et al. 2026 (all above); C. Yu, D. Matthews, J. Wang, J. Gu, D. Blackiston, M. Rubenstein, S. Kriegman, "Agile legged locomotion in reconfigurable modular robots", arXiv:2505.00784 (PNAS 123(10), 2026, DOI 10.1073/pnas.2519129123 [S]): metre-scale rigid modular legs ("metamachines"), not voxels. Simulator: not found in the abstract.
- T. Howison, S. Hauser, J. Hughes, F. Iida, "Reality-assisted evolution of soft robots through large-scale physical experimentation: a review", arXiv:2009.13960, Artificial Life 26(4):484 (2020). Argues for grounding evolved soft-robot design in physical experiments.
- Summary: quantitative agreement of Voxelyze-type models with hardware is roughly 10 to 15% in the best reported cases, and qualitative failures (direction reversal) occur. Nobody has shown that Voxelyze locomotion results are physically predictive in general. "Faithful to Voxelyze" and "physically right" are different claims.

### 3.2 Evolution exploiting simulator artefacts [V]
- J. Lehman, J. Clune, D. Misevic, et al. (about 50 authors, including N. Cheney, R. MacCurdy, H. Lipson, K. Sims, P. Krcah), "The Surprising Creativity of Digital Evolution: A Collection of Anecdotes from the Evolutionary Computation and Artificial Life Research Communities", Artificial Life 26(2):274-306, 2020, DOI 10.1162/artl_a_00319 [S for volume and pages], arXiv:1803.03453. Read via https://ar5iv.labs.arxiv.org/html/1803.03453
  - Section "Evolving Virtual Creatures Reveal Imperfectly Simulated Physics" has an anecdote about Cheney et al.'s soft robots, i.e. the very system being replicated. The simulator chose its time step from the creature (finer for more cells). Evolution shrank creatures to a few cells to obtain a large time step; bottom cells then penetrated the ground between updates, and the corrective collision force acted as free energy, so the creatures vibrated and drifted quickly. Fixes: more damping on ground contact, a larger minimum creature size, and a changed time-step calculation.
  - This is the same failure class as the researcher's "record robot pushing against the inside of the floor". It is the strongest citation for that part of the paper.
  - Same section: Sims's creatures exploiting integration error by twitching and a collision bug that launched them. Section on misspecified fitness: Sims's tall falling creatures; Krcah's somersault.
  - General advice in the paper: inspect evolved solutions visually; assume an adversary looking for loopholes.
- Cheney, Bongard, Lipson 2015 (section 1.4): single-material bodies possibly caused by a finite time-step effect at the fitness-measurement instant.
- F. Corucci et al. 2018 (section 1.4) [V-local]: with one material of stiffness from 0.001 to 10 MPa, evolved morphology and gait change with stiffness. The softest robots cannot locomote at all and collapse; soft ones vibrate or bounce at high actuation frequency; stiff ones evolve limbs and slower coordinated gaits. The authors note that fitness differences between land and water come from arbitrary friction and drag parameters. This supports the observation that a stiffness error changes what evolves.
- E. Medvet, A. Bartoli, F. Pigozzi, M. Rochelli, "Biodiversity in evolved voxel-based soft robots", GECCO 2021, pp. 129-137, DOI 10.1145/3449639.3459315. Vibrating gaits evolve frequently and would probably not survive in reality (paper text seen only through a search summary [S]).
- G. Nadizar, E. Medvet, S. Nichele, S. Pontes-Filho, "Collective control of modular soft robots via embodied Spiking Neural Cellular Automata", arXiv:2204.02099 (ICLR 2022 workshop). States that vibrating behaviour is a strong attractor in evolution and amounts to a reality gap. 2D-VSR-Sim at 60 Hz.
- E. Medvet, G. Nadizar, F. Pigozzi, "On the Impact of Body Material Properties on Neuroevolution for Embodied Agents: the Case of Voxel-based Soft Robots", NeuroEvolution@Work workshop at GECCO 2022. https://github.com/giorgia-nadizar/BodyParamsInfluenceOnNE . Varies body material properties and finds that neuroevolution exploits them. Paper not opened.
- Mertan and Cheney 2024 [V-local]: in EvoGym the controller is queried every fifth step to limit high-frequency dynamics that could be unstable.
- Reality-gap classics: N. Jakobi, P. Husbands, I. Harvey, "Noise and the reality gap: the use of simulation in evolutionary robotics", ECAL 1995, LNCS 929:704-720, DOI 10.1007/3-540-59496-5_337. S. Koos, J.-B. Mouret, S. Doncieux, "The Transferability Approach: Crossing the Reality Gap in Evolutionary Robotics", IEEE TEVC 17(1):122-145, 2013, DOI 10.1109/TEVC.2012.2185849 (the best simulated solutions tend to exploit badly modelled physics [S]). J.-B. Mouret, K. Chatzilygeroudis, "20 Years of Reality Gap: a few Thoughts about Simulators in Evolutionary Robotics", GECCO 2017 Companion (SimER workshop), DOI 10.1145/3067695.3082052 [S].

### 3.3 Cross-simulator comparisons
- For evolved voxel soft robots: **none found** (search incomplete).
- Nearest items: voxcraft-sim issue #41; jax-evogym parity tests; DisMech-RL sim-to-sim test; C. Pretorius, M. du Plessis, J. Gonsalves, "Evolutionary Robotics Applied to Hexapod Locomotion: a Comparative Study of Simulation Techniques", J. Intelligent and Robotic Systems 96(3-4):363-385, 2019, DOI 10.1007/s10846-019-00989-0 [S] (rigid hexapod).
- A systematic comparison of the same evolved voxel robots in two engines would therefore be a contribution in its own right.

---

## 4. Reproducibility and replication culture

### 4.1 Framework papers [V]
- M. Lopez-Ibanez, J. Branke, L. Paquete, "Reproducibility in Evolutionary Computation", ACM TELO 1(4), Article 14, 2021, DOI 10.1145/3466624, arXiv:2102.03380.
  - Four study types: repeatability (everything original), reproducibility (original artifacts, new random seeds), replicability (new artifacts, same fixed factors), generalisability (new fixed factors).
  - ACM swapped its definitions of reproducibility and replicability in August 2020.
  - ACM TELO has a reproducibility board and offers Artifacts Available, Artifacts Evaluated and Results Reproduced badges. It does not offer Results Replicated, judging the re-coding effort excessive.
  - Obstacles named: reproductions are hard to publish; confirmations look marginal and failures cause disputes; code is checked harder when results are bad than when they are good; 8 errata among 2,484 papers in three EC journals; in 2021 no EC journal or conference required artifacts.
  - Recommendations: permanent artifacts with DOI, raw data and actual solutions, seeds, software versions and hardware, sensitivity analyses, effect sizes.
  - An independent re-implementation of Cheney 2013 is a **replicability** study in this taxonomy.
- F. Da Ros, T. Zaciragic, A. Plaat, T. Baeck, N. van Stein, "Assessing Reproducibility in Evolutionary Computation: A Case Study using Human- and LLM-based Assessment", GECCO 2026, DOI 10.1145/3795095.3805069, arXiv:2602.07059 (BBSR best-paper nominee [S]).
  - 168 GECCO ECOM-track papers, 2016-2025: 36.9% provide any artifact; 10.7% provide code and data; 14 use persistent hosting; 6.55% of links dead; only 3 papers (1.8%) give enough to attempt a full reproduction without contacting the authors.
  - The BBSR track began in 2024; of its 18 accepted papers only one has replication as its main aim (Karns and Desell 2025).

### 4.2 GECCO [V]
- Track "Benchmarking, Benchmarks, Software, and Reproducibility" (BBSR), since 2024, listed again for 2026 (chairs M. Preuss, F. Olivetti de Franca [S]). 2024 description: https://gecco-2024.sigevo.org/Tracks.html
  - Invites reproducibility studies that rigorously replicate published experiments and shift confidence in the original results; the new findings must be explained so that the paper makes a distinct contribution (different benchmarks, scenarios, or implementation differences); replicability studies in the ACM sense (different team) are of particular interest.
  - All artifacts must be in a public repository at submission and stay available.
- Complex Systems track (2026 chairs A. Cully, T. Desell): artificial life, evolutionary robotics, evolved morphologies, in simulation or on hardware. https://gecco-2026.sigevo.org/Track?itemId=51
- GECCO 2026 call: 8 pages plus references; review criteria include whether there is enough information to permit replication; source code encouraged, with a permanent copy (e.g. Zenodo); supplementary material at most 10 MB. https://gecco-2026.sigevo.org/Call+for+Papers
- **ACM artifact badges at GECCO: I found no evidence that GECCO awards them.** The 2026 call does not mention badges or an artifact-evaluation committee. Badges exist at ACM TELO.
- GECCO 2027: 12-16 July 2027, Krakow, in person only. https://gecco-2027.sigevo.org/ . Deadlines not on the page I read. GECCO 2026 used 19 Jan (abstract) and 26 Jan (paper), so expect late January 2027.

### 4.3 Published replications and re-implementations [V]
- J. Karns, T. Desell, "Evaluation Time Bias in Asynchronous Evolutionary Algorithms: A Replication Study and a Novel Mitigation Strategy", GECCO 2025, pp. 13-21, DOI 10.1145/3712256.3726458. Reproduces an earlier experimental result from scratch, finds overlooked factors (crossover, initialisation), and adds a new method. Pattern: replication, then new insight, then extension.
- Re-implementations of Sims's evolved virtual creatures:
  - T. Taylor, C. Massey, "Recent Developments in the Evolution of Morphologies and Controllers for Physically Simulated Creatures", Artificial Life 7(1):77-87, 2001, DOI 10.1162/106454601300328034.
  - T. Miconi, A. Channon, "A virtual creatures model for studies in artificial evolution", IEEE CEC 2005, pp. 565-572, DOI 10.1109/CEC.2005.1554733. Framed as the first replication of Sims to reach comparable results, with standard neurons and Newtonian physics, offered as a general tool.
  - P. Krcah, "Evolving virtual creatures revisited", GECCO 2007, p. 341, DOI 10.1145/1276958.1284700.
  - N. Chaumont, R. Egli, C. Adami, "Evolving Virtual Creatures and Catapults", Artificial Life 13(2):139-157, 2007, DOI 10.1162/artl.2007.13.2.139.
  - Also mentioned in search summaries, not checked: Miconi and Channon 2006 (ALIFE X), Lassabe et al. 2007, Pilat and Jacob 2008 "Creature Academy" (CEC 2008).
- Medvet et al. 2020 (section 2.2): simulator paper validated by qualitative repetition of earlier studies.
- Outside EC: O. Gundersen et al., "The Unreasonable Effectiveness of Open Science in AI: A Replication Study", AAAI 2025, DOI 10.1609/aaai.v39i25.34818: access to original materials strongly raises the chance of successful reproduction.
- I found **no published replication of Cheney et al. 2013** and no formal replication study of any evolved-soft-robot result. Search incomplete.
- Venues not verified in this session: ReScience C, Journal of Open Source Software, an ALIFE-conference reproducibility track.

### 4.4 How such papers are framed
1. State the type of study in the Lopez-Ibanez taxonomy (here: replicability with new artifacts).
2. Do not sell confirmation alone. Add what the replication revealed: undocumented parameters, sensitivity of the outcome, a failure mode.
3. Release everything at submission with a permanent identifier.
4. Say explicitly what was not reproduced and why.

---

## 5. Assessment: keep the custom engine or restart?

### 5.1 Facts that decide it
- No maintained, installable, 3D, Voxelyze-compatible simulator exists in November 2026. Voxelyze 2016, VoxCAD 2015, evosoro 2018 (Python 2), voxcraft-sim 2021 (CUDA 10.1), RISE (closed binary, Linux, self-described unfinished). EvoGym is 2D and cannot host this replication.
- Mainstream engines are not safer. MuJoCo corrected its flex elastic constants in October and November 2026; Genesis fixed soft bodies sinking through the floor and a too-soft material on 17 November 2026.
- Voxelyze is not ground truth for physics (section 3.1), and its own authors document floor penetration and a time-step exploit. The defensible claim is equivalence to the 2013 reference implementation, plus honest sensitivity analysis.
- The community accepts re-implemented Hiller-Lipson mechanics without any published validation (RISE at ICLR 2025). 105 unit tests is already above the norm.

### 5.2 Recommendation
Keep the engine. Do not restart. Add a reference-simulator layer and report it.

The reference must be the 2013 code from `softbots2013Code.tgz` (headless Voxelyze of that date), not Voxelyze master, evosoro or voxcraft-sim, which all diverged. Archive that tarball with the paper's artifacts: its only public home is a personal website.

### 5.3 Cross-checks, most convincing first
1. **Deposited champions, three-way.** Take generation-1000 robots from Dryad. Their file names carry the recorded fitness (for example origFit 6.8689 for run 100). Simulate each (a) in the compiled 2013 Voxelyze and (b) in the MuJoCo engine. Report recorded value, re-run value, new-engine value, relative error, and Spearman rank correlation.
2. **Trajectory parity on canonical scenes**, with stated tolerances (the jax-evogym pattern): Hiller-Lipson cantilever deflections and modal frequencies; one voxel dropped on the floor (penetration depth, rebound); block on the floor under increasing lateral force (static and dynamic friction thresholds); two-voxel actuator (14% linear strain at TempAmp 39); the time step produced by the rule for a given stiffness and mass.
3. **Rank preservation on random bodies.** A few hundred random CPPN robots in both engines: Spearman correlation and top-k overlap. Selection acts on rank, so this is what matters for evolution.
4. **Evolution-level comparison.** Fitness-over-generation curves against the deposited GenchampData; the paper's qualitative claims (CPPN versus direct encoding, number of materials, cost functions).
5. **Artefact audit of every reported champion.** Maximum floor penetration, fraction of time in ground contact, re-evaluation at half and quarter time step, friction and floor stiffness varied, actuation-phase noise (as in the 2020 PNAS robustness filter). Report how many champions survive.
6. **Parameter provenance table**: paper text, Dryad config, 2013 source, evosoro default, value used.
7. Optional third implementation: voxcraft-sim on Colab for a handful of robots. Lower value, since its maintainer does not expect simulators to agree out of the box.

### 5.4 Open checks before writing
- What `PoissonKickBackEnabled 0` disables in the 2013 code (section 1.3).
- Whether the 2013 `VX_Environment.cpp` computes `TempAmplitude = TempAmp - TempBase` (section 1.5).
- Whether the deposited 2013 code already contains the fixes described in the Lehman et al. anecdote.
- Hiller-Lipson Table 2 direction (section 1.1) in the journal version.
