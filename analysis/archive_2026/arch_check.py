"""Is the 1.31 a lucky single cell? And does anything in the archive actually bounce?"""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution')
os.chdir(r'C:\SoftRobotEvolution')

for name in ['tendon_ctrl', 'tendon_eg', 'tendon_stiff', 'tendon_stiff_s2']:
    p = f'results/{name}/archive.pkl'
    if not os.path.exists(p):
        print(f'{name:16} no archive.pkl'); continue
    d = pickle.load(open(p, 'rb'))
    arc = d['archive']
    rows = sorted(arc.values(), key=lambda e: -e['fitness'])
    f = np.array([e['fitness'] for e in rows])
    bounce = np.array([e['desc'][1] for e in rows])
    height = np.array([e['desc'][0] for e in rows])
    # stiff usage among the top 10 bodies
    stiff = [int((e['genome'] == 4).sum()) for e in rows[:10]]
    tot = [int((e['genome'] != 0).sum()) for e in rows[:10]]
    print(f'\n{name}   cells={len(f)}')
    print(f'  max={f[0]:.4f}  2nd={f[1]:.4f}  3rd={f[2]:.4f}   gap(max-2nd)={f[0]-f[1]:+.4f} ({100*(f[0]-f[1])/f[1]:+.0f}%)')
    print(f'  top10 fitness: {np.round(f[:10],3).tolist()}')
    print(f'  top10 stiff voxels: {stiff}  (of {tot})')
    print(f'  bounce desc: max={bounce.max():.5f} mean={bounce.mean():.5f} '
          f'| top10 bounce={np.round(bounce[:10],4).tolist()}')
    print(f'  COM height desc: min={height.min():.3f} max={height.max():.3f}')
