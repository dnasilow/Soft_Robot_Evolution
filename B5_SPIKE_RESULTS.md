# B5 Feasibility Spike — Results & Go/No-Go (2026-06-24)

**Question:** Should we reformulate the physics from *free-rigid-body-per-voxel +
spatial-tendon* to MuJoCo **flex/deformable** bodies? B5 exists for **speed** (GPU
was ruled out). The spike had to prove three things on a small throwaway model:
(1) a flex lattice can be **actuated as muscle**, (2) it **locomotes**, (3) it is
**>=3x faster** than the working tendon model.

All spike code is throwaway and does **not** touch the production pipeline:
`b5_flex_spike.py` (contract/locomote/speed), `b5_bench_real.py`,
`b5_selfcollide_test.py`, `b5_verify.py`. Env: MuJoCo 3.4.0, Python 3.13.

---

## VERDICT: **GO** (clears the 3x bar decisively, with caveats below)

| spike test | result | pass? |
|---|---|---|
| **(1) Muscle actuation** | tendon-on-flex contracts the lattice **19.1%** (commanded -40%; FEM elasticity resists) | **PASS** |
| **(2) Locomotion** | hand-tuned traveling wave -> **+0.198 body-lengths in 4 s** (f=6 Hz, amp 0.55) | **PASS** |
| **(3) Speed (>=3x)** | flex **574 steps/s** vs working tendon **5–37 steps/s** = **15–100x raw, ~30–190x effective** | **PASS** |

The single biggest unknown — *can a MuJoCo flex body be actuated as muscle?* — is
**yes**, via spatial tendons embedded across the deformable lattice and driven by
position actuators (the de-risk approach you chose). Built programmatically with
`MjSpec`: flexcomp meshes the soft lattice, then we decorate the generated
node-bodies with sites + actuation tendons.

---

## The real speed story (why flex wins, rigorously)

Naive first benchmark said flex was **141x** faster. That number was **not
trustworthy**, and chasing it down is the important part:

1. **The tendon model's cost is almost entirely intra-robot self-collision.**
   A real 300-voxel champion produces **~7,800 contacts / ~31,000 constraint rows**
   per step — these are voxels of the *same robot* colliding with each other (the
   converter gives every voxel geom default `contype/conaffinity`, so they all
   self-collide). Measured tendon throughput on real champions:
   - `gait_qd2`: 7857 contacts -> **37 steps/s**
   - `directed_v1`: 7287 contacts -> **6 steps/s**
   - Disable voxel-voxel collision -> contacts to ~0 -> **845 steps/s (177x)**.
     So ~99% of the tendon model's time is the self-collision solve.

2. **But self-collision is load-bearing — you can't just remove it.**
   With voxel-voxel collision off, the `gait_qd2` champion's fitness collapses
   **0.640 -> 0.000**: evolved gaits rely on the body holding together / not
   self-intersecting. So the cheap "just disable it" shortcut is **not valid** —
   it changes the physics and destroys existing solutions.

3. **Flex provides that same self-intersection resistance at a fraction of the cost.**
   Flex represents the body as a continuum: internal cohesion comes from **2,541
   cheap FEM edges**, not thousands of contact constraints. During locomotion the
   flex robot has **ncon = 77** (floor only) vs the tendon model's ~1,200+ floor
   contacts *plus* ~7,800 internal ones. That is the fundamental architectural win:
   **flex replaces an expensive-but-necessary contact solve with cheap elasticity.**

### Effective throughput (governs eval wall-time; folds in timestep)
| model (300-voxel scale) | steps/s | timestep | sim-s / wall-s |
|---|---|---|---|
| tendon, status quo (self-collision ON) | 5–37 | 0.0005 | 0.003–0.019 |
| flex (this spike) | 574 | 0.001 | **0.574** |

A 2.5 s evaluation: **~2–14 min/robot** (tendon, single contended thread) vs
**~4 s/robot** (flex). Flex also runs at a **2x larger stable timestep** (better
conditioned), compounding the win.

---

## Idle-machine confirmation (2026-06-24, machine free)
Re-ran with 0 competing workers. Confirms and *strengthens* the result:
| model (300-voxel, idle) | steps/s | sim-s/wall-s |
|---|---|---|
| tendon, real champions (gait_qd3_1000 / qd2 / directed_v1) | 43–51 | 0.021–0.025 |
| flex | **3,186** | **3.19** |

**~70x raw, ~140x effective.** The idle ratio is even more favorable than under
contention (flex is compute-bound and gained more from free cores: 574 -> 3,186
steps/s). A 2.5 s eval: **~120 s/robot (tendon) -> ~0.8 s/robot (flex)**.

## Caveats / honest limits of this spike
- ~~Measured under load~~ — **resolved**: idle benchmark above confirms ~140x.
- **Shape mismatch.** Tendon = real irregular champion; flex = regular box of equal
  voxel count. Fair for throughput (internal contacts dominate, flex has none), but
  a flex build of arbitrary evolved shapes is part of the full B5, not the spike.
- **Locomotion is hand-tuned (0.198 BL), not evolved.** The spike proves the
  *mechanism*; reaching evolved-fitness parity requires the full evolution
  integration. That is the main remaining risk for the full B5 build (not the spike).
- **Compile cost is higher for flex** (~3.4 s vs ~0.4 s here). Per-morphology
  recompile matters at scale; worth measuring/caching in the full build.

---

## FULL BUILD RESULTS (2026-06-24) — engine done + fast, but v1 fitness does NOT reach parity

Built (behind a `--flex` flag; tendon model untouched):
- `src/physics/mujoco_flex_converter.py` — arbitrary voxel grid -> flexcomp `type="direct"`
  tet mesh (5 tets/voxel, shared nodes) + phase-tagged x-edge muscle tendons.
- `src/physics/mujoco_flex_physics.py` — `MuJoCoFlexPhysics`, drop-in for the tendon
  engine (same load_robot/step/get_fitness API, identical directed-BL fitness).
- `src/evolution/mujoco_tendon_evaluator.py` + `run_tendon_evolution.py` — `--flex` routes
  AFPO **and** MAP-Elites to the flex engine (open-loop only; flex voxel_size 0.05).

**Speed — confirmed in the real evolution loop.** Flex evolution runs a generation of
24–40 robots in **~3–5 s** (the tendon model takes ~350 s for 50 robots). The ~140x
per-eval speedup shows up end-to-end. Stability: `young=1e4, kp=600, dt=0.0005`,
`badqacc=0`, ~3,900 steps/s on a 300-voxel robot.

**Fitness — the v1 muscle model does NOT reach parity.** Two validation runs
(pop24/gen15 -> 0.0092 BL; pop40/gen50 -> 0.0141 BL) climbed monotonically with healthy
machinery (CPPN complexified N10->N32, 20+ species) but plateaued **~50–100x below the
tendon model** (0.6–1.08 BL). Diagnosis (all cheap, because flex is fast):
- **Not the search:** fitness climbs, CPPN complexifies, speciation active.
- **Not mainly the gait representation:** a traveling-wave phase (vs 2-phase material)
  helps only modestly (0.010 -> 0.025 BL on one body; ~flat on others).
- **Best hand-tuned flex locomotion ~0.06–0.2 BL** (production converter beam swept over
  scale/wave/freq/amp: 0.061; the spike's own builder reached 0.198). Still far under tendon.
- **Likely root cause:** the tendon model's locomotion exploits per-voxel **contact/friction**
  (voxel-voxel + per-voxel ground ratcheting) — *exactly what flex removes to get its speed*.
  A smooth flex continuum with x-edge muscles undulates gently instead of ratcheting forward.

**Honest status: B5 is a GO on SPEED, NOT-YET on FITNESS.** Closing the gap is real,
unproven R&D — candidate directions: multi-axis muscles; contact-rich flex (some
self/ground contact re-enabled, trading back some speed); limbed/elongated morphologies
(flex favors different body plans than the tendon model's blobs); volumetric contraction
actuation; and C6 evolvable per-voxel phase (helps, but not sufficient alone).

**Practical implication for the next campaign:** running the AFPO-exploit in flex *now*
would top out ~0.2 BL — far below the tendon model's 1.08 BL. The proven high-fitness path
is still the (slow) tendon model. Flex is best used, for now, as a **fast exploration /
pre-screen** tool, or as the target of a focused muscle/contact-model R&D push.

## Muscle-model R&D attempt #1 (2026-06-24): multi-axis + friction — DID NOT close the gap
Added multi-axis muscles (x forward + z lift/plant, ~90deg offset; converter `multi_axis=True`)
and a traveling-wave phase option (`wave_phase_n`), then swept gait/scale/friction:
- multi-axis alone: **no gain** (same or worse than x-only).
- multi-axis + traveling wave: ~0.05 BL (uniform beam), **worse** on the champion body.
- ground-friction sweep: modest, non-monotonic (best 0.063 BL @ friction 2.0; higher hurts).

**Every actuation/grip lever caps flex locomotion at ~0.05–0.2 BL.** This strengthens the
conclusion that the tendon model's strong locomotion fundamentally depends on the dense
per-voxel **contact ratcheting** flex removes to get its speed — i.e. flex's speed and its
(weak) locomotion are in tension. Remaining targeted idea: keep flex's cheap internal
cohesion (no self-collision) but add discrete bottom-surface **contact "feet"** for ground
grip — grip without the full contact blowup. Unproven; may still not close a 5–20x gap.

## Muscle-model R&D attempt #2 (2026-06-24): 1000-gen run — compute does NOT rescue it
Ran a full flex MAP-Elites (pop50, matching gait_qd3_1000) to test whether raw generations
close the gap (cheap now: ~6s/iter, ~1.7h for 1000 vs tendon's ~4 DAYS). Result: max fitness
hit ~0.012 BL by iter 10 then **flatlined** (0.012 -> 0.0136 @100 -> 0.0151 @260; tendon was
0.80 BL @100). Stopped early — it's a **hard structural ceiling**, not a generations problem.

## Muscle-model R&D attempt #3 (2026-07-02): grip "feet" — best yet, still short
Added discrete friction "feet" (small spheres hung below bottom-surface nodes, floor-only
contact via a 3-group collision bitmask; converter `feet=True`) to restore ground ratcheting
without the internal contact blowup, paired with multi-axis lift/plant muscles. Feet ON vs OFF
(hand-tuned + traveling wave): beam 0.054->0.084 BL, champion 0.036->0.051 (~+50%). Short
evolution WITH feet+multi-axis: **0.0318 BL @ gen40 — ~2x the feet-less flex run (0.0141)**,
still ~34x under tendon (1.08). Feet help most WITH a traveling wave, which the 2-phase
open-loop evolution can't express (would need C6 evolvable per-voxel phase). Every lever
(multi-axis, friction, compute, feet) gives ~1.5-2x; none closes the 30-70x gap.

## BOTTOM LINE
B5 delivered a **validated ~140x speed engine** (confirmed idle + in-loop), but flex v1
**cannot locomote competitively** with the tendon model (~0.015-0.2 BL vs 0.6-1.08), and
three independent attempts (multi-axis muscles, gait/friction tuning, 1000-gen compute)
failed to close the gap. The likely cause is fundamental: flex's speed comes from removing
the per-voxel contact ratcheting the tendon gaits rely on. **Recommendation: use the proven
(slow) tendon model for real high-fitness results; keep flex as a fast morphology pre-screen;
treat "contact feet" as a low-confidence last experiment only if speed becomes critical.**

## Recommended next step (full B5, when you greenlight it)
1. **Confirmatory idle-machine benchmark** (flex vs tendon) to nail the absolute speedup.
2. **`--flex` parallel mode** behind a flag (keep tendon physics intact for A/B + fallback).
3. **Arbitrary-shape flex builder**: map an evolved voxel grid -> flex mesh; map the
   4 materials (2 muscle phases -> actuated tendon groups; soft/stiff -> edge `young`).
4. **Evolve in flex** and validate it reaches comparable locomotion (fresh baseline).

### Side finding worth a separate look (independent of B5)
The tendon model spends ~99% of its time on self-collision. It is *needed* for the
current model, but **contact-solver tuning** (e.g. `condim`, `solref`/`solimp`,
contact margins, or a coarser collision proxy per voxel) might cut that cost
materially **without** a full rewrite — a cheaper partial win to evaluate alongside B5.
