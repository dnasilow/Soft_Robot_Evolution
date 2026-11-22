# One-off analysis scripts, July to October 2026

These 100 Python scripts and 2 shell scripts were written during the working sessions that built and checked the engine. They lived in a temporary folder and were copied here on 21 November 2026 so they are not lost. They are a record, not maintained code.

- They are the evidence trail behind numbers in the research notebook: the champion verifications (`verify_*.py`), the reading of Cheney's deposited robots (`cheney_morphology.py`, `settle_properly.py`), the physics probes (`gravity_sweep.py`, `amp_sweep.py`, `pen_check.py`, `headroom.py`, `mirror_test.py`) and the notebook section builders (`nb_5c.py`, `nb_5d.py`, `nb_5f.py`).
- Most contain absolute paths to that temporary folder and read run outputs from `results/`, which is not in the repository. Expect to adjust paths before running one.
- Cheney's extracted generation-1000 robot files, which several scripts read, are now also in `research_reference/extracted/dryad_gen1000/` (kept out of git).
- Scripts that use multiprocessing must be run from a file, never piped through standard input on Windows.

Newer checks are in `paper/diagnostics_2026-11-18/`.
