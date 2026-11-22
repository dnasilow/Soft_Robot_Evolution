"""Complete seed picture: stiff-bias (3 seeds) vs control eg (2 seeds), paired where possible."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

def champ(name):
    d = pickle.load(open(f'results/{name}/best_robot.pkl', 'rb'))
    g = d['genome']
    mats = {m: int((g == m).sum()) for m in (1, 2, 3, 4)}
    c = d.get('cppn')
    gp = c.to_gait_params() if (c is not None and hasattr(c, 'to_gait_params')) else None
    return d.get('fitness', float('nan')), int((g != 0).sum()), mats, gp

runs = {
    'tendon_eg':      ('eg control', 1),
    'tendon_eg_s2':   ('eg control', 2),
    'tendon_stiff':   ('stiff-bias', 1),
    'tendon_stiff_s2':('stiff-bias', 2),
    'tendon_stiff_s3':('stiff-bias', 3),
}
print(f"{'run':16} {'grp':10} seed  fit     vox  mat1 mat2 mat3 mat4(stiff)")
for n,(grp,sd) in runs.items():
    f,v,m,gp = champ(n)
    print(f"{n:16} {grp:10} {sd}   {f:.4f}  {v}  {m[1]:4d} {m[2]:4d} {m[3]:4d} {m[4]:4d}")

stiff = [1.3057044756561826, 0.7786101634900697, 1.0880]  # s1,s2,s3 (s3 from log max)
eg    = [1.1194743136817267, 0.9837]                       # s1,s2 (s2 from log max)
print(f"\nstiff-bias  n=3  mean={np.mean(stiff):.4f}  std={np.std(stiff,ddof=1):.4f}  "
      f"range=[{min(stiff):.3f},{max(stiff):.3f}]  spread={max(stiff)/min(stiff):.2f}x")
print(f"eg control  n=2  mean={np.mean(eg):.4f}  std={np.std(eg,ddof=1):.4f}  "
      f"range=[{min(eg):.3f},{max(eg):.3f}]  spread={max(eg)/min(eg):.2f}x")
print(f"\nPAIRED (seeds with both):")
print(f"  seed1: stiff {stiff[0]:.4f} vs eg {eg[0]:.4f}  -> stiff {stiff[0]-eg[0]:+.4f}")
print(f"  seed2: stiff {stiff[1]:.4f} vs eg {eg[1]:.4f}  -> stiff {stiff[1]-eg[1]:+.4f}")
print(f"  mean paired diff = {np.mean([stiff[0]-eg[0], stiff[1]-eg[1]]):+.4f}")
