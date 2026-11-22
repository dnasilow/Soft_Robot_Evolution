"""Why do our top robots use so few voxels (187-370 of 1000) when Cheney's use ~650?

No simulation: reads stored fitnesses and decodes body size from the genomes.
  - our fitness  = forward displacement / OWN body length (longest bbox side)
  - Cheney's     = |dCOM| / FIXED workspace width (10 voxels)
So under ours a body half as long needs half the distance for the same score.
Prints, per population: voxel count, longest side, fill, and how voxel count
relates to BL score vs to absolute distance.
"""
import os, sys, glob, pickle
import numpy as np
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
from morphology_scorecard import body_metrics
SP = os.path.join(os.environ['TEMP'], 'claude', 'C--SoftRobotEvolution',
                  '5cc73d86-944b-40cc-9802-a2f3f18f9a8b', 'scratchpad')
sys.path.insert(0, SP)
from cheney_morphology import load_vxa

VS = 0.01          # metres per voxel in our beam runs (fast1: 1.6208 BL = 0.162 m, 10 voxels long)


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def shape(g):
    g = np.asarray(g)
    occ = g > 0
    idx = np.argwhere(occ)
    ext = idx.max(0) - idx.min(0) + 1
    m = body_metrics(g)
    return dict(vox=int(occ.sum()), longest=int(ext.max()), ext=tuple(int(e) for e in sorted(ext)),
                bbox=int(np.prod(ext)), fill=m['fill'])


def summarise(name, genomes, fits, ours=True):
    rows = [dict(shape(g), fit=float(f)) for g, f in zip(genomes, fits) if (np.asarray(g) > 0).any()]
    rows.sort(key=lambda r: -r['fit'])
    a = lambda k: np.array([r[k] for r in rows], float)
    print(f"\n=== {name}  ({len(rows)} bodies) ===")
    print(f"  voxels  median {np.median(a('vox')):.0f}  range {a('vox').min():.0f}-{a('vox').max():.0f}"
          f"   longest side median {np.median(a('longest')):.0f}   bbox median {np.median(a('bbox')):.0f}"
          f"   fill median {np.median(a('fill')):.2f}")
    if ours:
        metres = a('fit') * a('longest') * VS
        chen = metres / (10 * VS)                 # Cheney's denominator: fixed 10-voxel workspace
        print(f"  spearman(voxels, BL score)       {spearman(a('vox'), a('fit')):+.2f}")
        print(f"  spearman(voxels, metres moved)   {spearman(a('vox'), metres):+.2f}")
        print(f"  spearman(longest side, BL)       {spearman(a('longest'), a('fit')):+.2f}")
        print(f"  {'rank':>4}{'BL':>8}{'metres':>8}{'Cheney-style':>13}{'vox':>6}{'longest':>8}"
              f"{'sorted bbox':>14}{'fill':>6}")
        for i, (r, m, c) in enumerate(zip(rows[:6], metres[:6], chen[:6]), 1):
            print(f"  {i:>4}{r['fit']:>8.4f}{m:>8.3f}{c:>13.3f}{r['vox']:>6}{r['longest']:>8}"
                  f"{str(r['ext']):>14}{r['fill']:>6.2f}")
        best_m = int(np.argmax(metres))
        print(f"  farthest in METRES: rank {best_m + 1} by BL, {metres[best_m]:.3f} m, "
              f"{rows[best_m]['vox']} vox, BL {rows[best_m]['fit']:.4f}")
    else:
        print(f"  spearman(voxels, his fitness)    {spearman(a('vox'), a('fit')):+.2f}")
        print(f"  spearman(longest side, fitness)  {spearman(a('longest'), a('fit')):+.2f}")
        print(f"  {'rank':>4}{'fitness':>9}{'vox':>6}{'longest':>8}{'sorted bbox':>14}{'fill':>6}")
        for i, r in enumerate(rows[:6], 1):
            print(f"  {i:>4}{r['fit']:>9.3f}{r['vox']:>6}{r['longest']:>8}{str(r['ext']):>14}{r['fill']:>6.2f}")
    return rows


def main():
    for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
        files = glob.glob(os.path.join(SP, 'cheney', cond, '**', '*.vxa'), recursive=True)
        gs, fs = [], []
        for f in files:
            try:
                g, fit = load_vxa(f)
            except Exception:
                continue
            gs.append(g); fs.append(fit)
        summarise(f"Cheney {cond}", gs, fs, ours=False)

    d = pickle.load(open('results/cheney_fix600_s1/final_population.pkl', 'rb'))
    summarise("cheney_fix600_s1 final population (CPPN-NEAT, record 2.6118)", d['genomes'], d['fitnesses'])

    arc = pickle.load(open('results/beamstage2_s1/archive.pkl', 'rb'))['archive']
    summarise("beamstage2_s1 archive (stage-1 bodies + evolved gait, untaxed BL)",
              [e['genome'] for e in arc.values()], [e['fitness'] for e in arc.values()])

    arc1 = pickle.load(open('results/beamstage1_s1/archive.pkl', 'rb'))['archive']
    sz = [e['cppn'] for e in arc1.values()]
    has = sum(getattr(c, 'size_gene', None) is not None for c in sz)
    vals = [c.size_gene for c in sz if getattr(c, 'size_gene', None) is not None]
    print(f"\nstage-1 genomes carrying an evolvable size gene: {has}/{len(sz)}"
          + (f"  (values {min(vals):.3f}..{max(vals):.3f}, median {np.median(vals):.3f})" if vals else ""))


if __name__ == '__main__':
    main()
