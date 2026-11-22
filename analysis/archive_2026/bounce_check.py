"""Does bouncing actually cost fitness? Correlate archive fitness vs bounce descriptor."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

for name in ['tendon_ctrl', 'tendon_eg', 'tendon_stiff', 'tendon_stiff_s2']:
    arc = pickle.load(open(f'results/{name}/archive.pkl', 'rb'))['archive']
    f = np.array([e['fitness'] for e in arc.values()])
    b = np.array([e['desc'][1] for e in arc.values()])
    ok = f > 0.01                      # ignore dead cells
    f, b = f[ok], b[ok]
    r = np.corrcoef(f, b)[0, 1]
    # binned: what does fitness look like for low vs high bounce?
    q = np.quantile(b, [0.25, 0.5, 0.75])
    lo = f[b <= q[0]]; hi = f[b >= q[2]]
    print(f'{name:16} n={len(f):3d}  corr(fitness,bounce)={r:+.3f}   '
          f'lowest-bounce-quartile mean fit={lo.mean():.3f} (max {lo.max():.3f})   '
          f'highest-bounce-quartile mean fit={hi.mean():.3f} (max {hi.max():.3f})')
