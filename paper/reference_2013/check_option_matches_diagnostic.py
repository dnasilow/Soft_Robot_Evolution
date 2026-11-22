"""The new global_damping option must give exactly what the 18 November diagnostic measured by
changing the engine's module constant: three deposited champions under the 2013 settings
(amplitude 0.14, Poisson coupling off, global damping 0.001), 10 cycles, 2013 score.

usage:  python paper/reference_2013/check_option_matches_diagnostic.py
"""
import glob
import json
import os
import re
import sys
from multiprocessing import Pool

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
DRYAD = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000', '2013-01-16-10^3-noCost')
HIS_TO_OURS = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
RUNS = ('run_124', 'run_103', 'run_112')


def champion(run):
    best = max(glob.glob(os.path.join(DRYAD, run, 'Gen_1000', '*.vxa')),
               key=lambda f: float(re.search(r'origFit_([0-9.eE+-]+)_genome', f).group(1)))
    s = open(best, encoding='iso-8859-1').read()
    rows = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((10, 10, len(rows)), np.int8)
    for z, row in enumerate(rows):
        g[:, :, z] = np.array([HIS_TO_OURS[int(c)] for c in row.strip()], np.int8).reshape(10, 10).T
    return g


def job(run):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.14, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze', poisson=False,
                          direction='any', divide_by='workspace', workspace_voxels=10,
                          global_damping=0.001)
    e.load_robot(champion(run))
    return run, float(e.get_fitness(0.25, 0.0, early_term_threshold=-1e9))


if __name__ == '__main__':
    old = json.load(open(os.path.join(ROOT, 'paper', 'diagnostics_2026-11-18', 'replay2_cheney_results.json')))
    was = dict(zip(old['runs'], old['configs']['D amp 0.14 + poisson off + damp 0.001']['ours']))
    with Pool(3) as p:
        now = dict(p.map(job, RUNS))
    ok = True
    for r in RUNS:
        same = abs(now[r] - was[r]) < 1e-9
        ok &= same
        print(f"{r}: option {now[r]:.6f}   diagnostic {was[r]:.6f}   {'identical' if same else 'DIFFERENT'}")
    raise SystemExit(0 if ok else 1)
