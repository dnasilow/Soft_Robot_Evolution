"""Shape statistics of Cheney 2013's deposited generation-1000 robots (no-cost and actuated-cost
conditions), using the project's own scorecard. Read-only."""
import os, re, sys, glob, json
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(OUT, '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(OUT)
from morphology_scorecard import body_metrics

CH = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
REMAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}


def load_vxa(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    layers = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(layers)), np.int8)
    for z, lay in enumerate(layers):
        g[:, :, z] = np.array([REMAP[int(c)] for c in lay.strip()], np.int8).reshape(ny, nx).T
    fit = float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(path)).group(1))
    return g, fit


def q(a):
    a = np.asarray(a, float)
    return f"{np.median(a):.2f} [{np.percentile(a, 25):.2f}-{np.percentile(a, 75):.2f}] (min {a.min():.2f}, max {a.max():.2f})"


out = {}
for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
    champs, everyone = [], []
    for r in sorted(glob.glob(os.path.join(CH, cond, 'run_*'))):
        best, bf = None, -1.0
        for f in glob.glob(os.path.join(r, 'Gen_1000', '*.vxa')):
            try:
                g, fit = load_vxa(f)
            except Exception:
                continue
            if (g != 0).sum() == 0:
                continue
            m = body_metrics(g); m['fit'] = fit
            m['muscle'] = (m['mats'][0] + m['mats'][1]) / max(m['vox'], 1)
            m['bone'] = m['mats'][3] / max(m['vox'], 1)
            m['soft'] = m['mats'][2] / max(m['vox'], 1)
            everyone.append(m)
            if fit > bf:
                best, bf = m, fit
        if best is not None:
            champs.append(best)
    print(f"\n{'=' * 80}\n{cond}: {len(champs)} run champions, {len(everyone)} robots in total\n{'=' * 80}")
    for name, rows in (('RUN CHAMPIONS', champs), ('ALL FINAL-POPULATION ROBOTS', everyone)):
        a = lambda k: np.array([r[k] for r in rows], float)
        print(f"  {name} (n={len(rows)})")
        print(f"    recorded fitness   {q(a('fit'))}")
        print(f"    voxels             {q(a('vox'))}")
        print(f"    footprint          {q(a('footprint'))}")
        print(f"    fill               {q(a('fill'))}")
        print(f"    elongation         {q(a('elongation'))}")
        print(f"    muscle fraction    {q(a('muscle'))}")
        print(f"    soft / bone frac   {np.median(a('soft')):.2f} / {np.median(a('bone')):.2f} (medians)")
        print(f"    feet  >= 2: {100 * np.mean(a('feet') >= 2):.0f}%   >= 3: {100 * np.mean(a('feet') >= 3):.0f}%   max {int(a('feet').max())}")
        print(f"    feet2 >= 2: {100 * np.mean(a('feet2') >= 2):.0f}%   >= 3: {100 * np.mean(a('feet2') >= 3):.0f}%   max {int(a('feet2').max())}")
        print(f"    footprint <= 50: {100 * np.mean(a('footprint') <= 50):.0f}%   <= 10: {100 * np.mean(a('footprint') <= 10):.0f}%")
        print(f"    PASS by the project's limb test (feet >= 2 or footprint <= 50): {100 * np.mean((a('feet') >= 2) | (a('footprint') <= 50)):.0f}%")
    out[cond] = [{k: (v if not isinstance(v, tuple) else list(v)) for k, v in r.items()} for r in champs]
    # relation between shape and recorded fitness among run champions
    a = lambda k: np.array([r[k] for r in champs], float)
    rk = lambda v: np.argsort(np.argsort(v)).astype(float)
    for k in ('vox', 'footprint', 'fill', 'muscle'):
        print(f"    Spearman(fitness, {k:<9}) among champions: {np.corrcoef(rk(a('fit')), rk(a(k)))[0, 1]:+.2f}")
json.dump(out, open(os.path.join(OUT, 'cheney_shapes.json'), 'w'), indent=1)
