"""Measure the morphology of Cheney 2013's OWN generation-1000 robots with the same scorecard we
apply to ours, so 'are their robots blobs?' is answered with their data, not with argument.

Their .vxa palette is 1=Active_+ (muscle), 2=Passive_Soft, 3=Active_- (muscle antiphase),
4=Passive_Hard  -- a different order from ours (1,2=muscle, 3=soft, 4=bone), so materials are
remapped before counting. Shape metrics use occupancy only and need no remapping.
"""
import os, re, sys, glob
import numpy as np
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
from morphology_scorecard import body_metrics

SP = os.path.join(os.environ['TEMP'], 'claude', 'C--SoftRobotEvolution',
                  '5cc73d86-944b-40cc-9802-a2f3f18f9a8b', 'scratchpad', 'cheney')
# their id -> ours (1,2 = muscle phases, 3 = soft, 4 = hard)
REMAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}


def load_vxa(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    layers = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(layers)), np.int8)
    for z, lay in enumerate(layers):
        d = np.array([REMAP[int(c)] for c in lay.strip()], np.int8).reshape(ny, nx)
        g[:, :, z] = d.T                       # layer rows are y, columns are x
    fit = float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(path)).group(1))
    return g, fit


def report(cond, files, topn=10):
    rows = []
    for f in files:
        try:
            g, fit = load_vxa(f)
        except Exception:
            continue
        if (g != 0).sum() == 0:
            continue
        m = body_metrics(g)
        m['fit'] = fit
        m['bone_frac'] = m['mats'][3] / max(m['vox'], 1)
        m['muscle_frac'] = (m['mats'][0] + m['mats'][1]) / max(m['vox'], 1)
        rows.append(m)
    rows.sort(key=lambda r: -r['fit'])
    print(f"\n{'='*94}\n{cond}   ({len(rows)} robots, generation 1000)\n{'='*94}")
    print(f"{'rank':>5}{'fitness':>10}{'vox':>6}{'feet':>6}{'feet2':>7}{'footpr':>8}{'fill':>7}"
          f"{'elong':>7}{'muscle':>8}{'bone':>7}")
    for k, r in enumerate(rows[:topn], 1):
        print(f"{k:>5}{r['fit']:>10.3f}{r['vox']:>6}{r['feet']:>6}{r['feet2']:>7}{r['footprint']:>8}"
              f"{r['fill']:>7.2f}{r['elongation']:>7.2f}{r['muscle_frac']:>8.2f}{r['bone_frac']:>7.2f}")
    a = lambda k: np.array([r[k] for r in rows], float)
    print(f"\n  all {len(rows)}: voxels median {np.median(a('vox')):.0f} (range {a('vox').min():.0f}"
          f"-{a('vox').max():.0f})   footprint median {np.median(a('footprint')):.0f}"
          f"   fill median {np.median(a('fill')):.2f}   elongation median {np.median(a('elongation')):.2f}")
    print(f"  feet: median {np.median(a('feet')):.0f}, max {a('feet').max():.0f}, "
          f"{100*np.mean(a('feet') >= 2):.0f}% have >= 2 feet   |   "
          f"footprint <= 50: {100*np.mean(a('footprint') <= 50):.0f}%")
    print(f"  muscle fraction median {np.median(a('muscle_frac')):.2f}   "
          f"bone fraction median {np.median(a('bone_frac')):.2f}")
    top = rows[:max(1, len(rows) // 35)]                     # best of each run, roughly
    at = lambda k: np.array([r[k] for r in top], float)
    print(f"  BEST-{len(top)}: feet >= 2 in {100*np.mean(at('feet') >= 2):.0f}%   "
          f"footprint median {np.median(at('footprint')):.0f}   "
          f"elongation median {np.median(at('elongation')):.2f}")
    return rows


if __name__ == '__main__':
    for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
        d = os.path.join(SP, cond)
        if not os.path.isdir(d):
            print(f"(skipping {cond}: not extracted)")
            continue
        report(cond, sorted(glob.glob(os.path.join(d, 'run_*', 'Gen_1000', '*.vxa'))))
    print("\nOURS for comparison (cheney_vox_s1, 236 bodies):")
    print("  top-10 feet 1/1, footprint 91-100, elongation 1.00, muscle ~0.82, voxels 655-801")
