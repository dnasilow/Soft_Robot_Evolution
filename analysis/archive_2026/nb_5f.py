cells.append(md(r"""## 5f. Cheney's own parameters, a floor bug, and the record (26 Sept – 1 Oct 2026)

### Reading his config exposed a scaling bug of ours

Lattice dynamics are fixed by two dimensionless groups: `E/(ρL²)` (natural frequency) and `ρgL/E`
(sag per voxel). Our material scaling corrected for density but silently assumed the lattice was
still his 1 mm; ours is 10 mm, so E needed another factor of `(L_ours/L_his)² = 100`.
**Our bodies had been 200× too soft — 14.1× too floppy in frequency.**

`--materials cheney2013` applies the full correction (soft/muscle 10 MPa, hard 50 MPa — only **5×**,
not the 100× evosoro implies). Mass, bond stiffness, natural frequency and sag per voxel then match
his simulation exactly. With it, 10 cycles at his 40 Hz is a 0.25 s window instead of 1.0 s, so
evaluations are **1.8× cheaper** despite a 3× smaller time step, and **nothing diverged** in a
30-robot pilot (the volumetric law's blow-ups need deformations that stiff bodies never reach).

### Then a floor bug of mine invalidated a whole run

`cheney_corr_s1` reached **4.1204 BL** and never plateaued — close to Cheney's own median of 4.39.
It was wrong, and the cause was `--floor-contact voxelyze` as I first wrote it. It set
`pair_solref = (-k, -c)` with `k = 2·E·L`, on the belief that MuJoCo reads a negative solref as
stiffness and damping in N/m. **It does not — those values act in acceleration space.** Pressing a
single resting voxel with a known force and comparing against the exact penalty-spring prediction
`F/k`:

| materials | measured ÷ F/k |
|---|---|
| evosoro | 1.91 |
| **cheney2013** | **14.33** |

A clean constant factor, growing with material stiffness. The deeper cause of the *dynamic* failure
was separate and sharper: **MuJoCo's contact softness is a time constant (20 ms by default), and a
40 Hz cycle is 25 ms**, so the contact never builds force before the cycle reverses. Static
penetration had been fine all along; only the gait failed.

I first blamed the actuation amplitude. **That was wrong too** — an amplitude sweep gave 1.02 voxels
of penetration at ±6% and 1.67 at ±20%: barely scaling, so a floor-independent baseline of ~1 voxel
was doing the damage.

**The fix** is a hard floor — `FLOOR_TIMECONST = 0.5 ms`, 2% of a 40 Hz cycle, critically damped,
floored at 2.5 time steps for stability. Voxelyze's own penalty floor is effectively hard at these
loads (under 1% of a voxel), so hard contact is the faithful choice.

| | before | after |
|---|---|---|
| peak penetration while walking, median | 1.78 voxels | **0.12** |
| peak penetration, worst of 16 bodies | 2.67 | **0.16** |
| cost per step | 0.826 ms | **0.823 ms** |

**What it cost:** `cheney_corr_s1`'s champion scores **−1.33 BL** on a correct floor — it goes
backwards. Both its 4.12 and its exciting near-Cheney footprint (29 against his 26) were artefacts of
a body partly inside the ground. Its gait had also died by cycle 40, a second reason it should not
have been believed.

### The record, and a clean plateau

| run | generations | best BL | top-10 | note |
|---|---|---|---|---|
| `cheney_neat_s1` | 300 | 2.0195 | 1.33 | old physics |
| `cheney_corr_s1` | 300 | ~~4.1204~~ | — | **invalid** (soft floor) |
| **`cheney_fix_s1`** | 300 | **2.6118** | 1.59 | corrected physics + fixed floor |
| `cheney_fix600_s1` | 600 | **2.6118** | 1.83 | same champion body, byte-identical |

**2.6118 BL verified**: reproduces exactly, 2.6160 at a quarter time step, unchanged with the ground
penalty, **super-linear over 30 cycles** (2.61 / 5.51 / 8.18 — it does not slow down), penetration 15%
of a voxel, worst bond strain 0.34 against an instability at 0.8, no divergence. That is
**0.261 BL per cycle, about 59% of Cheney's median run champion** — our best honest comparison.

**And doubling the generations changed nothing.** 2.6118 arrived at generation 287 and stayed flat for
**313 generations**, returning the byte-identical body. The population consolidated (top-10 1.59 → 1.83,
dead robots 5 → 2) while the peak did not move. This configuration is converged; more generations are
not the lever.

### Morphology: what survived the floor fix

| | `cheney_neat_s1` | `cheney_fix_s1`/600 | Cheney |
|---|---|---|---|
| voxels | 290 | 370 | 652 |
| footprint | 71 | **70** | **26** |
| elongation | 1.67 | 1.43 | 1.00 |
| muscle fraction | 1.00 | **1.00** | **1.00** |

Footprint ~70 is where **both honest runs** land, old physics and new — so the near-Cheney footprint
did not survive. The one thing that now reproduces reliably is **100% muscle, no passive material**,
which is exactly his champions' composition. The limbs test still fails (one foot) — as it does for
him, where only 3% of champions pass it.

### Process notes worth keeping

- A finished AFPO/NEAT run **deletes its own checkpoint**, so it cannot be extended by resuming; 600
  generations meant re-treading the first 300 (which reproduced identically, confirming determinism).
- I piped a multiprocessing script through stdin on Windows **twice**. Spawn re-imports `__main__`,
  the workers respawn forever, and the orphans ran for 45 hours. They also slowed `cheney_fix_s1` by
  ~40% (175 s/generation against 101 s once cleared) — a slowdown I had wrongly dismissed by reasoning
  from the one process still alive afterwards rather than the sixteen running at the time."""))
