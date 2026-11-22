# Diagnostics of 18 November 2026

Read-only checks behind section 3 of [../PLAN.md](../PLAN.md). Nothing in the project was modified by them. Each script was run with `python -I -u <script>` from a scratch folder, with the project root added to the import path.

**Where the robot files are.** The scripts read Cheney's extracted generation-1000 robot files from `research_reference/extracted/dryad_gen1000/` (kept out of git; the same files are inside `research_reference/softbots2013Gen1000.tgz`). On 18 November they were read from a temporary folder; the paths were changed on 21 November, the results were not rerun. The `.log` files named below stay local (git ignores `*.log`).

| File | What it does | Result |
|---|---|---|
| `cheney_shapes.py`, `.json` | Shape census of the deposited generation-1000 robots (no-cost and actuated-cost), using `morphology_scorecard.body_metrics` | Plan section 3.1 |
| `cheney_curves.py`, `.json` | Champion score by generation for his 35 runs per condition, read from `softbots2013GenchampData.tgz` in memory | Plan section 3.2 |
| `replay_cheney.py`, `.log`, `_results.json` | His 70 run champions with muscles on in the beam engine, on the exact physics and score of `cheney_score_s1`; amplitude sweep ±6.3% to ±39% on the 35 no-cost champions. First reproduces our own champion (2.7170) as a sanity check | Median ratio to his recorded score 0.34 at ±20%, 0.45 at ±14% |
| `replay2_cheney.py`, `.log`, `_results.json` | Same robots with the 2013 settings switched one at a time: amplitude ±14%, volumetric law off, global damping 0.001 (`ZETA_GLOBAL` changed in the worker process only) | Plan section 3.3. All three together: median ratio 0.68 (no-cost), 0.77 (actuated-cost) |
| `origin_offset_test.py` | Tests whether his recorded scores include the start position's distance from the lattice origin (the one deposited simulator file never sets the start position) | Refuted: 165 of 1026 robots score well below that offset. `main.cpp` line 52 in the full archive sets it |
| `peek_2013_code.py`, `peek_2013_lines.py` | Print lines of the full 2013 source archive (`research_reference/repositories/softbots2013Code.tgz`) without extracting it | Amplitude formula, Poisson switch, damping, start position |
| `unittest_head.log` | `python -m unittest discover -s tests -t .` on a clean copy of commit `ebf3a28` | 105 tests, OK, 11 skipped (they need run outputs not in the repository) |

Not yet done: the same replay with the remaining 2013 settings (time-step fraction 0.9, collision settings, the older floor and friction formulas), and a comparison against the 2013 simulator built from source.
