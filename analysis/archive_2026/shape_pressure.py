"""Two questions:
 (1) what does '5% of the grid' actually mean, concretely?
 (2) does our body-length normalisation PENALISE elongated bodies? (correlate shape vs fitness)
 (3) numbers needed to design a sensible ground-penalty threshold.
Archive reads only - no simulation, so it won't disturb pvp_long."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

GRID = 18  # interior 18^3 = 5832 positions

def shape_stats(g):
    idx = np.argwhere(g != 0)
    n = len(idx)
    ext = idx.max(0) - idx.min(0) + 1          # bbox extents (x,y,z)
    body_length = ext.max() + 1                 # what fitness divides by
    elong = ext.max() / max(ext.min(), 1)       # 1 = cubic, higher = elongated
    fill = n / np.prod(ext)                     # density inside its own bbox
    return n, ext, body_length, elong, fill

print("=== (1) what '5%' means: champion vs the available design space ===")
print(f"grid interior = {GRID}^3 = {GRID**3} positions\n")
print(f"{'run':16}{'voxels':>7}{'%grid':>7}{'bbox':>12}{'bodylen':>8}{'elong':>7}{'fill':>6}")
for name, path in [('pvp_s1(1.32)','results/pvp_s1_champion_RUN1.pkl'),
                   ('pvp_s2','results/pvp_s2/best_robot.pkl'),
                   ('pvp_s3','results/pvp_s3/best_robot.pkl'),
                   ('egfix_s1','results/egfix_s1/best_robot.pkl'),
                   ('tendon_eg','results/tendon_eg/best_robot.pkl')]:
    if not os.path.exists(path): continue
    g = pickle.load(open(path,'rb'))['genome']
    n, ext, bl, el, fl = shape_stats(g)
    print(f"{name:16}{n:>7}{100*n/GRID**3:>6.1f}%{str(tuple(int(x) for x in ext)):>12}"
          f"{bl:>8}{el:>7.2f}{fl:>6.2f}")
print("\n  Cheney default: 10^3 = 1000 positions, bodies ~200-400 voxels => ~20-40% of grid")

print("\n=== (2) does body-length normalisation punish elongated bodies? ===")
print("   fitness = displacement / body_length, and body_length = LONGEST bbox extent.")
print("   So an elongated robot must travel FARTHER for the same score. Test on archives:")
for name in ['pvp_s2','pvp_s3','egfix_s2','egfix_s3']:
    p = f'results/{name}/archive.pkl'
    if not os.path.exists(p): continue
    arc = pickle.load(open(p,'rb'))['archive']
    rows = [(e['fitness'],) + shape_stats(e['genome'])[2:4] for e in arc.values() if e['fitness'] > 0.01]
    if len(rows) < 20: continue
    f  = np.array([r[0] for r in rows])
    bl = np.array([r[1] for r in rows], dtype=float)
    el = np.array([r[2] for r in rows])
    print(f"  {name:10} n={len(f):3d} | corr(fitness, body_length)={np.corrcoef(f,bl)[0,1]:+.3f}"
          f"  corr(fitness, elongation)={np.corrcoef(f,el)[0,1]:+.3f}"
          f"  | median bodylen={np.median(bl):.0f} elong={np.median(el):.2f}")
print("   (negative corr => compact bodies score better = normalisation favours blobs)")

print("\n=== (3) numbers for designing the ground penalty ===")
g = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))['genome']
n, ext, bl, el, fl = shape_stats(g)
vs = 0.01  # voxel size (m)
print(f"  champion: bbox {tuple(int(x) for x in ext)} voxels -> body_length = {bl} voxels = {bl*vs:.3f} m")
print(f"  a 'flat' robot's resting COM height is roughly half its Z extent:"
      f" ~{ext[2]/2*vs:.3f} m  (2x that = {ext[2]*vs:.3f} m)")
print(f"  1 body-length of clearance would be {bl*vs:.3f} m  ({bl/(ext[2]/2):.1f}x resting COM)")
print("  -> '2x resting height' is a MORPHOLOGY-DEPENDENT threshold: tiny for flat robots,")
print("     generous for tall ones. A body-length-relative threshold is consistent across shapes.")
