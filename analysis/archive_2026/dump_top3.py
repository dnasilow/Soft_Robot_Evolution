"""Write the top 3 of cheney_vox_s1 as individual best_robot-style pickles so render_champion.py
can draw each of them."""
import os, pickle, sys
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
arc = pickle.load(open('results/cheney_vox_s1/archive.pkl', 'rb'))['archive']
top = sorted(arc.values(), key=lambda e: -e['fitness'])[:3]
out = 'results/cheney_vox_s1'
for k, e in enumerate(top, 1):
    p = os.path.join(out, f'top{k}.pkl')
    with open(p, 'wb') as fh:
        pickle.dump({'genome': e['genome'], 'fitness': e['fitness'], 'cppn': e.get('cppn')}, fh)
    g = e['genome']
    print(f"top{k}: fitness {e['fitness']:.4f}  voxels {int((g != 0).sum())}  "
          f"m1/m2/soft/bone {[int((g == i).sum()) for i in (1, 2, 3, 4)]}  -> {p}")
