"""Summarise one evolution run against the deposited 2013 no-cost runs.

  * its champion score by generation next to the deposited runs at the same generations;
  * the champion's body, measured like the deposited robots;
  * the champion scored in the OTHER simulator (a run in the 2013 simulator is scored in the MuJoCo
    engine with the 2013 preset, and the other way round), unless --no-transfer.

usage:  python paper/reference_2013/summarise_run.py results/<run> [--no-transfer]
"""
import argparse
import io
import json
import os
import pickle
import sys
import tarfile

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
CURVES = os.path.join(ROOT, 'research_reference', 'DRYAD_CheneyEtALL', 'softbots2013GenchampData.tgz')
GENS = (1, 10, 30, 100, 200, 300, 600, 1000)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def deposited_curves(cond='2013-01-16-10^3-noCost/'):
    """Best champion original score up to each generation, per deposited run (read in memory)."""
    out = []
    with tarfile.open(CURVES, 'r:gz') as t:
        for m in t:
            if m.isfile() and cond in m.name and m.name.endswith('.txt'):
                rows = []
                for line in t.extractfile(m).read().decode('utf-8', 'replace').splitlines():
                    p = line.split()
                    try:
                        rows.append((float(p[0]), float(p[1])))
                    except (ValueError, IndexError):
                        continue
                if rows:
                    a = np.array(rows)
                    out.append(np.maximum.accumulate(a[:, 1]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run')
    ap.add_argument('--no-transfer', action='store_true')
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    run = a.run if os.path.isabs(a.run) else os.path.join(ROOT, a.run)

    hist = json.load(open(os.path.join(run, 'history.json')))
    best = np.maximum.accumulate(np.array(hist['best_fitness'], float))
    manifest = {}
    mpath = os.path.join(run, 'manifest.json')
    if os.path.exists(mpath):
        manifest = json.load(open(mpath))['invocations'][0]['settings']
    simulator = manifest.get('simulator', 'mujoco')
    print(f"{os.path.basename(run)}: {len(best)} generations, simulator {simulator}, "
          f"penalty {manifest.get('penalty', 'none')}, seed {manifest.get('seed', '?')}")

    if os.path.exists(CURVES):
        dep = deposited_curves()
        print(f"\nChampion score by generation (deposited: {len(dep)} no-cost runs)")
        print(f"{'generation':>11}{'this run':>10}{'deposited median':>18}{'q25':>7}{'q75':>7}{'min':>7}{'max':>7}{'runs below this one':>21}")
        for g in GENS:
            if g > len(best):
                break
            v = np.array([c[min(g, len(c)) - 1] for c in dep])
            print(f"{g:>11}{best[g - 1]:>10.3f}{np.median(v):>18.3f}{np.percentile(v, 25):>7.2f}"
                  f"{np.percentile(v, 75):>7.2f}{v.min():>7.2f}{v.max():>7.2f}{int((v < best[g - 1]).sum()):>14} of {len(v)}")
    else:
        print("\n(deposited learning curves not present - skipping the comparison)")

    from morphology_scorecard import body_metrics
    from src.evolution import cheney2013 as c13
    champ = pickle.load(open(os.path.join(run, 'best_robot.pkl'), 'rb'))
    g10 = c13.workspace_grid(np.asarray(champ['genome']))
    m = body_metrics(g10)
    n = max(m['vox'], 1)
    print(f"\nChampion (stored fitness {champ['fitness']:.4f}): {m['vox']} voxels, footprint {m['footprint']}, "
          f"fill {m['fill']:.2f}, feet {m['feet']}, muscle {(m['mats'][0] + m['mats'][1]) / n:.2f}, "
          f"soft {m['mats'][2] / n:.2f}, stiff {m['mats'][3] / n:.2f}")
    print("  deposited no-cost champions for comparison: 652 voxels, footprint 26, fill 0.65, muscle 1.00 (medians)")

    if a.no_transfer:
        return
    if simulator == 'voxelyze2013':
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        e = MuJoCoBeamPhysics(actuation_amplitude=0.14, actuation_frequency=40.0, fitness_mode='forward',
                              friction=SS, materials='cheney2013', floor_contact='voxelyze', poisson=False,
                              direction='any', divide_by='workspace', workspace_voxels=10,
                              global_damping=0.001)
        e.load_robot(np.asarray(champ['genome']))
        other = float(e.get_fitness(0.25, 0.0, early_term_threshold=-1e9))
        print(f"\nTransfer: the champion scores {other:.3f} in the MuJoCo engine with the 2013 preset "
              f"({other / max(champ['fitness'], 1e-9):.2f} of its score in the 2013 simulator)")
    else:
        from src.evolution.voxelyze2013_evaluator import Voxelyze2013Evaluator
        other = Voxelyze2013Evaluator(n_workers=1).evaluate_single(np.asarray(champ['genome']))
        print(f"\nTransfer: the champion scores {other:.3f} in the 2013 simulator "
              f"({other / max(champ['fitness'], 1e-9):.2f} of its score in the engine it evolved in)")


if __name__ == '__main__':
    main()
