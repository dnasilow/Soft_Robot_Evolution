cells.append(md(r"""## 5d. Reading Cheney's own data, and the run log (22–25 Sept 2026)

### The ground truth we had been guessing at

`research_reference/softbots2013Gen1000.tgz` holds **26,164 of Cheney's actual generation-1000
robots**, and every one carries the full simulator configuration. `2013-01-16-10^3-noCost` is our
exact condition: 35 runs × 30 individuals. The `.vxa` files are plain XML (ten `<Layer>` rows of 100
digits), and his material order differs from ours — **1 = muscle+, 2 = soft, 3 = muscle−, 4 = hard**.

**Are his robots limbed? No.** Measured with our own scorecard, his 35 run champions:

| | Cheney | ours (`cheney_vox_s1`) |
|---|---|---|
| voxels | 652 | 564 |
| elongation | 1.00 | 1.00 |
| bodies with ≥ 2 feet | **3 %** | 0 % |
| muscle fraction | **1.00** | 0.82 |
| **footprint** | **26** | **94** |

His no-cost champions are solid blocks of **100 % muscle** with no passive material at all, and they
fail our limbs test too. The differentiated shapes in the paper come from his *cost* conditions
(`costNumActuated` champions: 377 voxels, footprint 4, muscle 0.61). The one real difference is
**footprint** — his bodies are tall and perched, ours squat and flat. His gaits come from the
spatial pattern of actuation phase inside a muscle block, not from limbs.

His penalty, from source: `fitness × (1 − (count / max)^exp)`, count = voxels, muscle voxels or
bonds. His fitness: `|ΔCOM|` in 3-D (undirected, `VX_Sim.cpp:128`) over the **fixed workspace
width** (`HCUBE_SoftbotsExperiment.cpp:392`) — so sideways motion counts and small bodies get no
bonus. Ours is +X over the robot's own bounding box: neither matches. His code also zeroes any run
with fitness > 1000 — the same divergence guard we built independently.

**His algorithm is plain CPPN-NEAT** (`softbotTest.dat`: speciation, compatibility threshold 6,
tournament 2, elitism, population 30, 1000 generations). No archive, no quality-diversity, no AFPO.
**MAP-Elites was our addition, not his.**

### The bug this exposed

Lattice dynamics depend on `E/(ρL²)` and `ρgL/E`. Our scaling corrected for density but silently
assumed the lattice was still his 1 mm; ours is 10 mm, so E needed another factor of 100.
**Our bodies were 200× too soft — 14× too floppy in natural frequency.** Fixed behind
`--materials cheney2013` (soft/muscle 10 MPa, hard 50 MPa — only **5×**, not 100×), which makes
mass, bond stiffness, natural frequency and sag per voxel match his exactly.

Raising gravity to match then exposed a second problem: **MuJoCo's contact stiffness ignores the
material**, so a body sank 2.7 voxels *through* the floor. `--floor-contact voxelyze` installs
Voxelyze's own penalty floor (`k = 2·E·L` per voxel, `CVX_Voxel::floorForce`) via a negative
`solref` pair:

| | gravity | penetration |
|---|---|---|
| old materials, MuJoCo floor | 9.81 | 13.1 % of a voxel |
| Cheney materials, MuJoCo floor | 274.68 | **266.7 %** |
| Cheney materials, Voxelyze floor | 274.68 | **0.8 %** |

### A hypothesis, tested and refuted

We predicted that stiffer bodies would stop splatting and perch like his. **They don't.** Settling
the same bodies with muscles off, footprint from real contacts:

| physics | our bodies | his bodies |
|---|---|---|
| what we had been running | 96 | 48 |
| fully corrected | **96** | **20** |

With the physics right, **his robots reproduce their own published footprint inside our engine**
(20 against his 26) while ours stay flat at 96. So the squat-versus-perched difference is the shape
evolution found, not our physics — and our engine is now validated against his morphology.

### Two things stated wrongly along the way, corrected

- **±39 % actuation strain** — retracted. The paper says "volumetric actuations of **20 %**", about
  6 % linear. Our ±20 % *linear* is roughly 3× larger, not smaller. The code mapping `TempAmp` to a
  temperature is not in the released files, so the config's 39 cannot be converted.
- **"Bone-free bodies run faster" as an argument** — the simulated duration is fixed at 10 cycles;
  only the step count and our wall-clock change, and evolution never sees that.

Gravity −27.468 m/s² (2.8 g) is real: hard-coded in his source, identical in all 26,164 files, with
no justification anywhere in the code or paper."""))

cells.append(md(r"""## 5e. Run log — the volumetric law and the algorithm comparison

All runs below: `--body beam`, volumetric law on, Voxelyze step rule, stick-slip Cheney floor
(1.0 / 0.5), amplitude ±20 %, 10 Hz, 10 cycles measured, population 30, 300 generations,
10³ workspace, early termination 0.02 BL at 50 %. Identical physics throughout, so only the search
differs. All three start from the *same* 30 random robots (generation-1 best 0.5812 in both seed-1
runs — the comparison is properly controlled).

| run | search | best BL | top-10 | cells | notes |
|---|---|---|---|---|---|
| `cheney_beam_s1` (pilot) | MAP-Elites | 1.6401 | 1.2833 | 240 | no volumetric law |
| `cheney_vox_s1` | MAP-Elites | 1.7592 | 1.7206 | 236 | volumetric law on |
| `cheney_vox_s2` | MAP-Elites | 1.9881 | 1.8240 | 163 | |
| **`cheney_neat_s1`** | **CPPN-NEAT** | **2.0195** | 1.3308 | — | **best so far** |

**The algorithm matters more than the physics did.** CPPN-NEAT leads at every checkpoint from
generation 50, and reaches 1.91 by generation 100 — a level MAP-Elites needed all 300 generations to
approach:

| generation | 50 | 100 | 200 | 300 |
|---|---|---|---|---|
| CPPN-NEAT | 1.743 | **1.913** | 2.020 | 2.020 |
| MAP-Elites s1 | 1.611 | 1.653 | 1.759 | 1.759 |
| MAP-Elites s2 | 1.475 | 1.691 | 1.874 | 1.988 |

The trade is exactly what the two methods promise: NEAT builds a better **champion** (2.0195), MAP-Elites
a better **population** (top-10 1.82 against NEAT's 1.33, with 4 of 30 scoring zero). NEAT's peak
then sat flat for its last 120 generations.

**And the NEAT champion is the first one whose shape moves toward Cheney's:**

| | previous champions | NEAT champion | Cheney |
|---|---|---|---|
| voxels | 564–801 | **290** | 652 |
| footprint | 91–100 | **71** | 26 |
| elongation | 1.00 | **1.67** | 1.00 |
| muscle fraction | 0.67–0.82 | **1.00** | 1.00 |

It is 100 % muscle with no soft or hard material, which is his composition exactly. Verified:
reproduces at 2.0195, keeps **99 %** after a 2 s settle (the MAP-Elites champions kept only 80 %),
unchanged with the ground penalty, 2.0273 at a quarter time step, and dead linear over three seconds
(2.020 / 4.029 / 6.011 BL). That is **0.202 BL per cycle, 51–58 % of Cheney's 0.35–0.40**, up from
41–47 % before this month's work. The limbs test still fails — one foot, as in every run including his.

**Divergence is steady and handled.** The volumetric law is non-linear in compression: past roughly
80 % compression the stress flips sign and a body that crushes itself explodes. This is structural,
not a step-size problem — it is unchanged at 1/16 of the step, and Voxelyze has the same failure.
Such runs score 0. Rate: 4.2 % of 9,000 evaluations, flat across a whole run (evolution does not
learn to avoid it)."""))
