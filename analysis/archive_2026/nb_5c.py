cells.append(md(r"""## 5c. Volumetric (Poisson) material law + Voxelyze's time step (22 Sept 2026)

**The gap.** §5b's bonds were independent: each one's axial force was `E·L ×` its own extension, so a
voxel's three axes never talked to each other. Voxelyze's material is a real 3D solid (ν = 0.35):

$$\sigma \;=\; \hat E\,\big[(1-\nu)\,\varepsilon_{\text{axial}} + \nu\,(\varepsilon_{t1}+\varepsilon_{t2})\big],
\qquad \hat E = \frac{E}{(1-2\nu)(1+\nu)} = 2.469\,E,$$

and the axial force is **stress × current transverse area**, not stiffness × extension
(`CVX_Material::stress`, `CVX_Link::updateForces`). Each voxel's per-axis strain is the average of its
bonds' shares (`CVX_Voxel::strain(true)`); an axis with fewer than two bonds is free to **bulge**
instead and takes $(1+\sum\varepsilon_{\text{constrained}})^{-\nu}-1$.

The consequences are exactly what was missing:

| situation | response |
|---|---|
| a column free to contract sideways | **E** — the bulge cancels $\hat E$ back down (validated to 0.3%) |
| a voxel squeezed on all three axes (inside a body) | $\hat E(1-\nu)=$ **1.605 E** — 60% stiffer |
| two voxels alone (nothing constrained) | 1.605 E — Voxelyze's own behaviour, not a bug of ours |
| compression | free faces bulge outward, so the bond's area grows and it pushes back harder |

**Time step.** Voxelyze sizes the step per robot from the *stiffest bond and the lightest voxel*:
`recommendedTimeStep = 1/(2π·√(max k_axial / min m))`, times evosoro's `DtFrac` 0.7 — nothing about
the material is fixed in advance, so a robot with bone automatically gets a 10× smaller step than an
all-soft one. `--dt-rule voxelyze` (new default) does exactly this; `ours` is the older estimate that
also sums every bond on a voxel and includes the damping rates. Under the volumetric law
`k_axial = Ê·L`, so the step is √2.469 = 1.57× smaller than it would be without it.

**Validation** (`tests/test_beam_physics.py`, `tests/test_pipeline.py` — 62 tests, all pass).
Beyond §5b's table: Ê and the 1.605 factor against Voxelyze's formulas; the free-bar, long-chain and
solid-block responses; the bulge under compression; the strain split at a soft/bone interface; a
clamped voxel counted as constrained; stress × area reaching `forces()` with the right sign; rigid
motion still force-free; the step rule's exact value and its √Ê and √E scalings; and the pilot's
1.6401 reproduced exactly with `--poisson off --dt-rule ours`.

Two findings worth recording:

1. **A missing torque.** Once the axial force stops being `K·(extension)`, the bond's energy depends on
   the two voxels' *orientations* through the bond axis, and the bond exerts a net torque on the pair
   unless that gradient term is added. It is now applied; it vanishes identically when the law is off
   (measured residual before the fix: 3·10⁻⁴ of the force scale).
2. **The law can run away.** Compressed far enough, the bulge grows without bound and the stress flips
   sign (around ε ≈ −0.8), so a body that crushes itself explodes. This is *structural*, not a step-size
   problem — it is unchanged at 1/16 of the step — and Voxelyze has the same failure (`pow()` of a
   negative base). Measured on 32 bodies: **3 diverge** (of which only one scored anything before).
   Such a run now scores **0** rather than whatever MuJoCo produces after clamping.

**Measured, 32 bodies (16 from the pilot archive, 16 fresh random), full 10 cycles, Cheney floor:**

| | pilot physics | volumetric only | volumetric + Voxelyze step |
|---|---|---|---|
| pilot champion | 1.6401 BL | 1.9147 | **1.9145** |
| mean over 32 | 0.4020 | 0.4236 | 0.4241 |
| total simulation time | 4538 s | 4533 s | **3630 s** |
| diverged | 0/32 | 3/32 | 3/32 |

Voxelyze's step is accurate: against a half step, **+0.6% mean** over the clean bodies and ≤0.3% on every
real evolved body (the 9% outlier is a junk random body scoring 0.19). Net speed **1.25×** (per body
0.87–1.55×: bodies whose step was bone-limited gain 1.4–1.5×, bodies that were already at the 0.5 ms cap
lose a little to the smaller step). So a seed costs roughly **20 h**, not the 10–12 h estimated before the
volumetric law was in.

**Deviation kept deliberately:** Voxelyze splits a bond's strain between its two voxels as
`2ε·r/(1+r) : 2ε/(1+r)` with `r = E_pos/E_neg`, which hands the **stiffer** voxel the larger share — the
opposite of two springs in series. We reproduce it (faithfulness to Cheney); it only touches the Poisson
bookkeeping at soft/bone interfaces, and evolved bodies are ~2% bone."""))
