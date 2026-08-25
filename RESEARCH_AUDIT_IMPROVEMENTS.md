# Deep Codebase Audit & Improvements — Soft Robot Evolution (2026-07-02)

> Scope: full-subsystem audit (fitness, physics, encoding, control, search, pipeline),
> prioritized improvements, and an autonomous implementation pass with proof-of-concept
> validation. All changes are **additive and backward-compatible** (new CLI flags; old
> behavior is the default). Companion docs: `B5_SPIKE_RESULTS.md` (flex engine),
> `SESSION_LOG_2026-06-23.md`.

## 0. Corrected baseline (the brief's "current state" was stale)
- The **0.11–0.12 BL plateau is long broken.** Tendon MAP-Elites reaches **1.0779 BL**
  (`gait_qd3_1000`). That is the number to beat.
- **Flex** (native deformable, `--flex`) is **~140× faster** but a **locomotion dead-end**:
  it plateaus ~0.03–0.04 BL (2000-gen run: 0.0427). Five levers (multi-axis muscles, friction,
  compute, grip feet, voxel resolution) each gave ≤2× and none closed the gap — flex earns its
  speed by removing the per-voxel **contact ratcheting** that crawling depends on.
- The "water density + kv" stability fix was for the **retired spring-mass** system, not the
  current tendon/flex models.

---

## 1. Audit findings (per subsystem)

### 1.1 Fitness landscape & metrics
- **Current:** `fitness = max(0, forward_+X / body_length) × ground_fraction`. Directed,
  body-length-normalized, with a robust settled-height ground threshold.
- **Findings:** the `ground_fraction` term is a blunt instrument — it zeroes out anything that
  leaves the ground, which *penalizes efficient hoppers/bounders* and couples "locomotion" with
  "stays low". There is **no notion of efficiency / cost-of-transport** (a fast but wasteful
  thrasher scores the same as an efficient crawler of equal speed), and **no smoothness/stability
  term** (jittery gaits that happen to drift forward are rewarded). For sim-to-real transfer,
  efficiency and smoothness matter as much as raw distance.
- **Bottleneck:** single hard-coded objective; no way to explore the objective space.

### 1.2 Physics engine(s)
- **Tendon** (free rigid body per voxel + spatial tendons): accurate and reaches 1.08 BL, but
  its cost is **~99% intra-robot self-collision** (~7,800 contacts / 300-voxel robot → 6–40
  steps/s). That self-collision is *load-bearing* (disabling it collapses evolved gaits), so it
  can't simply be removed. This is the real reason runs take days.
- **Flex** (FEM deformable): ~140× faster but can't ratchet (see §0).
- **Mass-spring (NEW, prototyped):** discrete node masses + Hookean springs + per-node ground
  contact — hypothesized sweet spot (grip like tendon, no box self-collision). **Result: it
  builds and is ~25× faster than tendon (1,024 steps/s @ 300 voxels), but is UNSTABLE at usable
  timesteps** (every stable-locomotion config failed `badqacc` while flex ran clean). This is the
  classic mass-spring stiffness problem and **empirically confirms why MuJoCo uses FEM (flex) for
  deformables.** Kept as `b6_spring_spike.py` for reference; **not** wired into production
  (shipping an unstable engine would violate "never break functionality").
- **Not pursued (documented):** fluid/SPH and neural-tissue models are far outside MuJoCo's
  wheelhouse and would be multi-week efforts with low expected ROI for locomotion.

### 1.3 Morphology encoding (CPPN + NEAT)
- **Findings:** CPPN is a sound choice (smooth spatial patterns → contiguous material patches;
  meaningful crossover in weight space). Two real limits: (a) evolution **converges to solid
  300-voxel blobs** because blobs score fine in tendon via contact — not an encoding-capacity
  problem (300 voxels in 20³ already allows limbs), a *search/incentive* problem; (b) the CPPN
  emits **presence + material only — no phase/gait channel**, so the gait cannot co-evolve with
  the body. Voxel resolution was tested (30³/800) and **does not help** (bigger blob, same
  ~0.02 BL, 7× compile cost).
- **Bottleneck:** morphology and control are effectively **decoupled** — the body evolves, the
  gait is fixed.

### 1.4 Control & actuation
- **Findings:** actuation is a **fixed** open-loop sine with phase = material (0 or π) — a
  *2-phase standing wave*. This is why open-loop "beats CPG": the CPG was fragile co-adaptation,
  but the real issue is that neither expresses a **traveling wave**, which is what a soft
  continuum needs to convert deformation into net motion. Hand-tests: a traveling wave gives
  flex ~0.06–0.2 BL vs ~0.01 for 2-phase. **This is the single biggest untapped lever.**
- **Bottleneck:** the "brain" is a constant; the gait cannot adapt to the body.

### 1.5 Search algorithm (MAP-Elites + AFPO)
- **Findings:** (a) **parent selection is uniform-random** over filled cells — no quality or
  novelty bias, so strong stepping-stones aren't exploited and under-explored regions aren't
  targeted; (b) **behavior descriptors = (COM height × bounce)** — the *bounce* axis is
  **degenerate for flex** (all robots ≈0 bounce → the 16×16 archive collapses toward 1-D);
  (c) elitism of 2 is fine for AFPO. Coverage 220/256 in tendon is healthy.
- **Bottleneck:** uniform parent selection leaves QD efficiency on the table; the bounce
  descriptor is a poor behavior axis for deformable bodies.

### 1.6 Evaluation pipeline
- **Findings:** solid — persistent worker pool (fixed the Windows `WinError 5` spawn deaths),
  per-gen checkpoint/resume, keep-awake for Modern Standby. Two gaps: (a) **stdout is block-
  buffered behind pipes**, so background runs look "stuck" (use per-gen JSON to monitor); (b) a
  **completed run deletes its checkpoint**, so re-running the same `--name` starts fresh and
  **overwrites** outputs — a real footgun (nearly lost the 1.08 champion this way). Validation
  measures a single deterministic rollout — no robustness-to-noise / multi-seed success metric.

---

## 2. Prioritized improvements

| # | Improvement | Dimension | ROI | Status (POC outcome) |
|---|---|---|---|---|
| 1 | **MAP-Elites parent selection** (`--parent biased`) | search | ★★★ | shipped — **POC WIN: 1.69× max, 2.2× QD** |
| 2 | **Fitness-shaping modes** (`--fitness`) | objective | ★★ | shipped — `efficiency` held distance at lower effort |
| 3 | **Evolvable gait / C6** (`--evolve-gait`) | control+encoding | ★★★ | shipped — flex 1.27× (validated); best reproducible tendon result (1.12 best-seed) but tendon margin unconfirmed under seed noise (§4d) |
| 4 | **Traveling-wave gait** (`--gait wave`) | control | ★★ | shipped — fixed-wave POC underperforms |
| 5 | **Mass-spring engine** (`b6_spring_spike.py`) | physics | ★ | prototyped → **negative result** (unstable at usable dt) |
| 6 | Warm-start MAP-Elites (`--seed-from`) | pipeline | ★★ | shipped earlier this session |

---

## 3. Improvements implemented (what / why / how)

All additive, gated by flags, default = old behavior.

### 3.1 Fitness-shaping modes — `--fitness {directed,forward,efficiency,stable}`
- `directed` (default, unchanged): `forward_BL × ground_fraction`.
- `forward`: raw `forward_BL`, no ground penalty — lets hoppers/bounders compete.
- `efficiency`: `forward_BL × ground_fraction / (1 + k·mean|actuator_force|)` — a cost-of-
  transport proxy; rewards distance *per unit actuation effort* (transfer-relevant).
- `stable`: penalizes vertical bounce — rewards smooth, low-COM gaits.
- **Where:** `get_fitness()` in both `mujoco_tendon_physics.py` and `mujoco_flex_physics.py`
  (energy accumulated from `data.actuator_force`); threaded via evaluator `fitness_mode`.

### 3.2 Traveling-wave gait — `--gait {material,wave}` + `--gait-wavenum N`
- `material` (default): phase = 0/π by material (2-phase standing wave).
- `wave`: phase = `2π·N·x/body_length` — a traveling wave along +X (the mechanism a deformable
  body needs). Flex-only for now (the tendon converter's dense per-pair actuation is different).
- **Where:** `mujoco_flex_converter.build_flex_spec(wave_phase_n=...)` (already supported) exposed
  through `MuJoCoFlexPhysics(wave_phase_n=...)` → evaluator → CLI.

### 3.3 MAP-Elites parent selection — `--parent {uniform,biased,curiosity}`
- `uniform` (default): equal probability over filled cells (classic).
- `biased`: probability ∝ (fitness − min) — concentrate breeding on strong elites.
- `curiosity`: probability ∝ 1/(1+times_selected) — favor under-explored cells (novelty push).
- **Where:** `run_map_elites()` breeding loop; per-cell selection counts tracked in `select_count`.

### 3.4 Evolvable gait / C6 — `--evolve-gait` (versioned genome, backward-compatible)
- Adds a **4-gene traveling-wave** vector `[kx, ky, kz, offset]` to `CPPNGenome` (`gait_genes`)
  that co-evolves with the body: muscle phase = `2π(kx·xn + ky·yn + kz·zn) + offset`. Mutates
  (gaussian) and is inherited from the fitter parent in crossover; the initial population is
  seeded via `init_gait()`.
- **Backward-compatible by design:** `gait_genes` defaults to `None` (→ legacy material gait), and
  every access uses `getattr(..., 'gait_genes', None)` so **old pickled CPPNs (incl. the 1.0779
  champion) load and run unchanged.** Deliberately does **not** touch `N_OUTPUTS` (which would
  shift node IDs and break saved genomes).
- **Where:** `cppn_genome.py` (genes + mutate/crossover/clone), threaded via
  `evaluate_batch(gait_params=...)` → `_eval_worker` → `load_robot(gait_params=...)`.
  **Both engines:** flex (`build_flex_spec(gait_params=...)`) AND tendon
  (`_apply_gait_params()` overrides each active tendon's material phase with the wave,
  evaluated at the tendon midpoint). Tendon smoke: 0.36 BL in 2 gens (pop 8) from scratch.
- **POC (§4):** flex A/B (300 gen) — **1.27× max, 1.84× QD, still climbing** (validated win).
  ⚠️ Run evolve-gait **from scratch**, not warm-started from a material-optimized champion
  (imposing a random wave on the 1.08 champion tanks it to 0 — the body must co-adapt).

### 3.5 Mass-spring engine (prototype, `b6_spring_spike.py`)
- Corner-node point masses + axial/face-diagonal springs (spatial tendons w/ stiffness+damping)
  + actuated muscle springs + per-node ground-contact spheres (3-group collision bitmask).
- **Outcome:** viable speed, unstable dynamics at usable dt (see §1.2). Documented, not shipped.

---

## 4. Proof-of-concept results

Short flex MAP-Elites, **pop 30 × gen 20**, sim 2.0 s, seed 11, one knob varied at a time
(baseline = material gait / directed fitness / uniform parent). Raw JSON:
`results/poc_audit_results.json`. Fitness in forward body-lengths (flex baseline is ~0.03 BL).

| config | gait | fitness | parent | **max BL** | coverage | QD-score | vs baseline |
|---|---|---|---|---|---|---|---|
| base | material | directed | uniform | 0.0149 | 137 | 0.23 | — |
| **biased** | material | directed | **biased** | **0.0252** | 129 | **0.51** | **1.69× max, 2.2× QD** ✅ |
| curio | material | directed | curiosity | 0.0191 | **148** | 0.23 | 1.28× max, +8% coverage ✅ |
| eff | material | **efficiency** | uniform | 0.0148 | 137 | 0.23 | ≈ distance held (diff. objective) |
| wave | **wave-2** | directed | uniform | 0.0007 | **170** | 0.006 | 0.05× max ❌ (but +24% coverage) |

**Interpretation (honest, single-seed flex → directional):**
- **`--parent biased` is a clear win — the headline result.** Both quality (1.69× max) *and*
  diversity (2.2× QD) improve. Concentrating breeding on strong elites finds better stepping
  stones. This should transfer to tendon (where it matters for pushing past 1.08). **Confirm first.**
- **`--parent curiosity`** gives modest quality gain (1.28×) and the **best coverage** — a
  diversity-leaning alternative.
- **`--fitness efficiency`** held forward distance essentially flat (0.0148 vs 0.0149) while
  optimizing for lower actuation effort — i.e. *comparable distance for less effort*, promising
  for transfer (a cost-of-transport readout would quantify the efficiency gain; not measured here).
- **`--gait wave` (fixed) LOSES on distance** (0.0007) though it maximizes coverage. This is an
  informative negative: a *fixed* global traveling wave strips evolution's control over phase, so
  it underperforms material 2-phase on arbitrary evolved bodies. **It confirms the mechanism helps
  only when the wave is tuned to the body → the real lever is per-voxel EVOLVABLE phase (§5), not a
  fixed wave.** The fixed flag remains useful for hand-tuned/analysis use.

**Evolvable gait (`--evolve-gait`) — loses at 20 gens, WINS with budget (A/B, 300 gens):**
| max BL @ gen | 20 | 100 | 200 | 300 | final QD |
|---|---|---|---|---|---|
| material gait + biased (control) | 0.0224 | 0.0299 | 0.0309 | 0.0330 *(flat)* | 1.35 |
| **evolvable gait + biased** | 0.0269 | 0.0320 | 0.0356 | **0.0419** *(climbing)* | **2.49** |

Matched A/B (flex, pop 40, seed 1, biased parent). **Evolvable gait wins 1.27× on max fitness and
1.84× on QD**, and is **still climbing at gen 300** while the material control has plateaued. The
earlier 20-gen POC (where it *lost*, 0.0081 vs 0.0252) was a **search-budget artifact**: the
body×gait space starts slower but overtakes once the gait genes tune.

**TENDON A/B (the headline — pop 50, gen 300, seed 1, biased parent):**
| | max BL | QD | coverage |
|---|---|---|---|
| material gait (`tendon_ctrl`) | 1.0303 | **112.5** | **216** |
| **evolvable gait (`tendon_eg`)** | **1.1195** | 95.8 | 203 |

**Evolvable gait wins max fitness +8.7% (1.1195 vs 1.0303) and sets a NEW PROJECT RECORD** — 1.1195
beats the old `gait_qd3_1000` champion (1.0779) that needed **1000** gens, in just **300**. It led
at every checkpoint (gen 6: 0.85 vs 0.44; gen 100: 0.89 vs 0.86; gen 200: 1.02 vs 0.99; gen 300:
1.12 vs 1.03) and jumped to 1.12 on the final generation — **still climbing.** On tendon it wins
*early* (opposite of flex), because tendon locomotes well enough that a good traveling wave pays off
immediately. **Tradeoff:** material gait holds higher diversity (QD 112 vs 96, 216 vs 203 cells) —
evolvable gait trades archive diversity for a higher peak. **`--evolve-gait` is now a validated win
on BOTH engines.** Caveat: single seed — confirm with multi-seed; a `--evolve-gait` + material-gait
niche hybrid could recover the diversity.

**Deep finding — evolvable gait sidesteps the body-encoder problem.** The 1.1195 champion is
**300 voxels of a SINGLE material** (all mat-2) driven by evolved gait genes
[kx=0.49, ky=−0.55, kz=−0.04, offset=6.1]. Under the material gait a single-material blob can't
locomote (everything pulses in unison — the original project failure mode the whole plateau-breaking
effort fought). Evolvable gait supplies the phase gradient **from the control side**, so a uniform
blob crawls — and beats every differentiated-material body found under material gait. This attacks
the long-standing body-encoder bottleneck from a completely different (and cheaper) direction.

**Caveats:** flex's absolute ceiling is ~0.03–0.2 BL, so these are **relative** deltas on small
single-seed runs — treat as directional and confirm the winners (esp. `--parent biased`) with the
longer multi-seed tendon commands in §5.

---

## 4b. AFPO vs MAP-Elites (controlled A/B) — corrects a prior assumption
Matched flex A/B, pop 40 / gen 60, vanilla settings, 3 seeds (`results/afpo_vs_me_results.json`):
| | seed 1 | seed 2 | seed 3 | **mean** |
|---|---|---|---|---|
| **AFPO** | 0.0305 | 0.0324 | 0.0308 | **0.0312** |
| MAP-Elites | 0.0224 | 0.0251 | 0.0288 | 0.0254 |

**AFPO won all 3 seeds (~1.23× mean).** This CONTRADICTS the earlier project lore that "MAP-Elites
dominates AFPO" — which was based on *uncontrolled* comparisons (different pop/gen, flex vs tendon).
Interpretation: at **short horizons** AFPO's direct fitness climb beats MAP-Elites' diversity
overhead; MAP-Elites' stepping-stone advantage is a **long-horizon** bet. The tendon records
(1.08–1.12) were all MAP-Elites but at gen 300–1000, and **AFPO was never tested against it at
matched scale** — so MAP-Elites' superiority in the high-fitness regime is *plausible but unproven*.
**Revised recommendation:** AFPO is competitive — wiring `--evolve-gait` into AFPO (previously
deprioritized) IS worthwhile, and an AFPO+evolve-gait tendon run is a real contender to beat 1.12.

## 4c. Full 2×2 (AFPO/MAP-Elites × material/evolvable gait) + gait-naturalness study
`--evolve-gait` is now wired into AFPO (`run_evolution`) too. 2×2 flex A/B (pop 40/gen 60, 3 seeds,
mean best forward-BL, `results/poc_2x2_results.json`):
| | material | evolvable gait |
|---|---|---|
| **AFPO** | 0.0312 | 0.0316 |
| **MAP-Elites** | 0.0254 | 0.0216 |

Reads: (1) **AFPO > MAP-Elites at short horizon** (both columns); (2) **evolvable gait is
horizon-dependent** — near-neutral/negative at gen 60 but a big win at gen 300 (flex 1.27×) and the
tendon record (1.12). No universal winner; it's an interaction.

**Gait-naturalness study (why the champion "vibrates"; is it the fastest?).** Research + experiments:
- **Biomechanics:** Saharan silver ant ≈ **108 body-lengths/s** (aerial gallop — all legs leave the
  ground) vs snail/slime ≈ **0.03 BL/s** (friction pedal waves, foot always down) → ant ~3000× faster.
  Legs win by *leaving the ground* (no friction drag) + elastic return + jointed leverage.
- **The champion ≈ 0.45 BL/s** — a limbless soft crawler (snail-family). Fast *for its class*, ~200×
  under an ant; the gap is **structural (no limbs), not tuning.**
- **Frequency:** sweep on the champion (`freq_sweep.py`) shows a **resonance peak ~10–12 Hz; the
  evolved 10 Hz IS optimal**, slower is far worse (5 Hz → 0.016 vs 10 Hz → 0.87). The fast "buzz" is
  load-bearing — a small limbless body is a high-frequency resonant crawler. Slowing ≠ more natural+fast.
- **Voxels:** not the limiter (30³/800 already tested, no gain) — needs rigid **limbs**, not more voxels.
- **Ground penalty (`ground_fraction`):** flex test inconclusive (`ground_penalty_test.py`) — flex
  barely bounces (ground_fraction≈1) so `directed`≈`forward` (identical champions). The hypothesis that
  the penalty **suppresses fast bouncing/galloping** (the ant's mechanism) is **plausible but needs a
  TENDON test** (where bouncing is possible). Our fitness currently *rewards staying grounded* — the
  opposite of how nature's fastest movers work.
- **Levers to a faster/more natural gait:** (a) rigid **limbs** (bias stiff material toward leg-like
  structures); (b) **relax the ground penalty on tendon** so hoppers/gallopers can emerge; (c)
  **co-evolve frequency** (currently a fixed 10 Hz global).

## 4d. Record arc, and the multi-seed replication that corrected it (tendon, pop50/gen300)
**Single-seed discovery arc (seed 1): 1.0779 → 1.0303 (biased) → 1.1195 (evolve-gait) → 1.3057 (stiff-bias).**
This looked like a clean +21% climb. Multi-seed replication (2026-07-23) dissolved the top of it.

- `tendon_forward` (`--fitness forward`): **NULL** — bit-identical to `tendon_eg` (1.1195). Crawlers
  stay grounded (`ground_fraction`≈1) so `forward`≈`directed`. The penalty never bound; removing it
  can't create hoppers. Note the bounce descriptor *correlates positively* with fitness across all
  archives — bouncier already scores higher, the penalty simply never bites. **To get air-time you
  must *reward* it, not just stop penalizing** — a `--fitness airtime` mode is the follow-up
  (deferred; guard against ballistic cheats).
- `tendon_stiff` (`--stiff-bias 0.3`): **NO RELIABLE EFFECT — DROPPED.** The single-seed 1.3057
  (once billed a +16.6% record) did **not** survive replication:

  | config | seeds | best per seed | mean | std |
  |---|---|---|---|---|
  | evolve-gait + biased (control) | 1,2 | 1.1195 / 0.9837 | **1.052** | 0.096 |
  | + stiff-bias 0.3 | 1,2,3 | 1.3057 / 0.7786 / 1.0880 | **1.057** | 0.265 |

  Same mean (paired diff −0.01, a wash) but **2.6× the variance**. The 1.3057 was the lucky top of a
  wide distribution, not a gain. **All five champions carry ZERO stiff voxels** — the flag has no
  locomotion mechanism (stiff material can't actuate, so selection deletes it). Removed from the
  recommended config. My earlier "stiff transmits force" reasoning was doubly wrong: not the
  mechanism, and not even a real effect.

**Two structural findings from the replication (these now steer the project):**
1. **Seed variance (~1.7× on a fixed config) > every lever effect measured.** So all single-seed
   gen-300 comparisons above are underpowered — including `--evolve-gait` (+8.7%): its seed-2 value
   (0.98) fell below material `tendon_ctrl` seed-1 (1.03). Evolve-gait keeps a mechanism + a flex win,
   so it's not discarded, but its tendon margin is **unconfirmed**. Screen future levers at 3+ seeds;
   treat <~1.5× as noise.
2. **Plateau is architectural, not compute.** Max fitness asymptotes by gen ~150–200 every run
   (`tendon_stiff_s3`: 1.067 @ iter87 → 1.088 @ iter300). A 2000-gen run at this config will very
   likely not break ~1.1–1.3. The body has collapsed to an interchangeable 300-voxel blob and the
   **evolved gait genes do all the work** → the ceiling moves only via richer control/structure
   (per-voxel evolvable phase, rigid limbs selection can keep, higher actuation authority).

**Champions rendered:** `results/{tendon_ctrl,tendon_eg,tendon_stiff,tendon_stiff_s2,afpo_stiff}/champion.gif`
(1.03 two-phase body; the rest single-material blobs driven by evolved waves — all zero stiff).
**Research archive:** `soft_robot_research.ipynb` (discovery arc + replication, seed-resolved curves,
champion gallery, findings) — build/refresh with `python build_notebook.py`.

## 5. Recommended next steps (longer validation to confirm)

**Tendon (high-fitness confirmation, run in VS Code; each is hours→~1 day):**
```bash
# Parent-selection sweep on the proven 1.08 engine (multi-seed for rigor)
python run_tendon_evolution.py --map-elites --parent biased    --pop 50 --gen 400 --sim-time 2.5 --workers 30 --seed 1 --name mp_biased_s1
python run_tendon_evolution.py --map-elites --parent curiosity --pop 50 --gen 400 --sim-time 2.5 --workers 30 --seed 1 --name mp_curio_s1
# Fitness-mode comparison (does efficiency/stable transfer better without losing much distance?)
python run_tendon_evolution.py --map-elites --fitness efficiency --pop 50 --gen 400 --sim-time 2.5 --workers 30 --seed 1 --name mp_eff_s1
# Warm-start exploit from the 1.08 champion (continue evolving)
python run_tendon_evolution.py --map-elites --seed-from results/gait_qd3_1000_CHAMPIONS_BACKUP.pkl --parent biased --pop 50 --gen 500 --sim-time 2.5 --settle 0.5 --workers 30 --seed 42 --name exploit_biased
```

**Flex (fast confirmation, minutes each):**
```bash
python run_tendon_evolution.py --flex --map-elites --gait wave --gait-wavenum 2 --pop 50 --gen 300 --sim-time 2.5 --amp 0.6 --freq 7 --workers 30 --seed 1 --name flex_wave
```

**Evolvable gait (`--evolve-gait`) — SHIPPED + VALIDATED on flex (1.27× A/B), now on tendon too.**
The 4-gene traveling wave co-evolves with the body (§3.4), on BOTH engines. The high-value run is a
**matched tendon A/B from scratch** (tendon ceiling ~1.08, ~25× flex) — each ~1–2 days in VS Code:
```bash
# control (material gait)
python run_tendon_evolution.py --map-elites --parent biased               --pop 50 --gen 300 --sim-time 2.5 --workers 30 --seed 1 --name tendon_ctrl
# treatment (evolvable gait) — MUST be from scratch, not --seed-from a material champion
python run_tendon_evolution.py --map-elites --parent biased --evolve-gait  --pop 50 --gen 300 --sim-time 2.5 --workers 30 --seed 1 --name tendon_eg
```
**Further extension (not built): per-voxel CPPN phase.** The linear 4-gene wave is a first cut; a
richer parameterization is a *second CPPN* (or phase output on a versioned CPPN) that maps
position→phase arbitrarily. More expressive than the linear wave; do it as a separate versioned
genome to preserve backward-compat (never change `N_OUTPUTS` on the existing genome).

---

## 6. Appendix

### 6.1 Files changed / added
- `src/physics/mujoco_tendon_physics.py` — `fitness_mode` + energy tracking in `get_fitness`.
- `src/physics/mujoco_flex_physics.py` — `fitness_mode`, `wave_phase_n` + same shaping.
- `src/physics/mujoco_flex_converter.py` — (earlier) `wave_phase_n`, `multi_axis`, `feet`.
- `src/evolution/cppn_genome.py` — evolvable **gait genes** (`gait_genes` + `init_gait`/
  `to_gait_params`/`mutate_gait`; propagated in `_clone`/`crossover`/`mutate`). Backward-compatible.
- `src/evolution/mujoco_tendon_evaluator.py` — thread `fitness_mode`, `wave_phase_n`, per-robot
  `gait_params`.
- `run_tendon_evolution.py` — `--fitness`, `--gait`/`--gait-wavenum`, `--parent`, `--evolve-gait`;
  parent-selection logic + `select_count`; MAP-Elites `--seed-from` (earlier).
- `b6_spring_spike.py` (NEW) — mass-spring prototype (negative result).
- `poc_audit.py` (NEW) — POC driver; `results/poc_audit_results.json` — POC output.

### 6.2 Alternatives considered but not pursued
- **Direct / graph-based / developmental encodings:** CPPN is defensible and the bottleneck is
  search incentives, not encoding capacity. Low ROI vs cost.
- **Fluid/SPH, neural-tissue physics:** far outside MuJoCo; multi-week, low locomotion ROI.
- **Re-enabling flex self-collision for grip:** reintroduces the contact blowup that motivated
  flex's speed — self-defeating.
- **Novelty-search descriptors (gait-signature, duty factor, elongation):** promising replacement
  for the degenerate bounce axis; recommended follow-up (small change to `cell_of`/descriptors).
