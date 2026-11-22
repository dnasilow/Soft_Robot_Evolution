"""If the presence gate (logit>0) lets ~50% of the grid through, the cap ALWAYS binds and
evolution can't choose body size. Sweep the presence threshold to find one where the size
distribution is actually EVOLVABLE (spread well below the cap), and check champion shape."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter, _build_coord_grid
from src.evolution.genome_config import keep_largest_component, VOXEL_GRID_SHAPE, VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX

coords, dims = _build_coord_grid()

# gather a pool of CPPNs: random + evolved elites (evolved matter most)
rng = np.random.default_rng(0); innov = InnovationCounter()
pool = [CPPNGenome(innov, rng) for _ in range(150)]
arc = pickle.load(open('results/pvp_s2/archive.pkl','rb'))['archive']
pool += [e['cppn'] for e in list(arc.values())[:150]]
L = [c.evaluate_batch(coords)[:, 0] for c in pool]   # presence logits

print("presence threshold sweep -- body size BEFORE any cap (n=%d CPPNs)" % len(L))
print(f"{'thresh':>8}{'median':>9}{'p10':>8}{'p90':>8}{'%<=500':>9}{'%<=300':>9}")
for t in [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    n = np.array([int((l > t).sum()) for l in L])
    print(f"{t:>8.1f}{int(np.median(n)):>9}{int(np.percentile(n,10)):>8}"
          f"{int(np.percentile(n,90)):>8}{100*(n<=500).mean():>8.0f}%{100*(n<=300).mean():>8.0f}%")

# --- shape of the actual record champion: is it a solid blob? ---
print("\n=== shape of the 1.3201 champion (pvp_s1) ===")
d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
g = d['genome']
idx = np.argwhere(g != 0)
bb = idx.max(0) - idx.min(0) + 1
n = int((g != 0).sum())
print(f"  voxels={n}  bbox={tuple(int(x) for x in bb)}  bbox_volume={int(np.prod(bb))}")
print(f"  fill-density = {n/np.prod(bb):.2f}   (1.00 = solid brick; lower = more limby/hollow)")
# per-layer cross-section area (z slices) -- legs would show thin lower layers
zs = sorted(set(idx[:,2].tolist()))
areas = [int((g[:,:,z]!=0).sum()) for z in zs]
print(f"  z-layer areas (bottom->top): {areas}")
print(f"  -> narrow bottom layers would indicate legs; uniform = blob/slab")
