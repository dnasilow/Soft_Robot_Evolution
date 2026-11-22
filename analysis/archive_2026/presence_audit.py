"""WHY do 98% of bodies sit exactly at the cap? Measure the decode pipeline stage by stage:
   presence gate (logit>0) -> trim to top-K -> keep_largest_component.
Also check evolved (not just random) CPPNs from a real archive."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
import src.evolution.cppn_genome as cg
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter, _build_coord_grid

coords, dims = _build_coord_grid()
TOTAL = len(coords)
print(f"interior positions available: {TOTAL}\n")

def presence_count(c):
    """How many voxels pass the presence gate BEFORE any cap/trim?"""
    logits = c.evaluate_batch(coords)
    return int((logits[:, 0] > 0.0).sum())

# --- 1. RANDOM CPPNs ---
rng = np.random.default_rng(0); innov = InnovationCounter()
pre = []
for _ in range(300):
    pre.append(presence_count(CPPNGenome(innov, rng)))
pre = np.array(pre)
print("=== RANDOM CPPNs: voxels passing presence gate (before cap) ===")
print(f"  min={pre.min()}  p25={int(np.percentile(pre,25))}  median={int(np.median(pre))} "
      f" p75={int(np.percentile(pre,75))}  max={pre.max()}   mean={pre.mean():.0f}")
for cap in (300, 500):
    print(f"  fraction ALREADY under a {cap} cap (i.e. cap not binding): "
          f"{100*(pre<=cap).mean():.1f}%")

# --- 2. EVOLVED CPPNs from a finished archive ---
print("\n=== EVOLVED CPPNs (pvp_s2 archive elites, evolved under a 300 cap) ===")
arc = pickle.load(open('results/pvp_s2/archive.pkl','rb'))['archive']
ev = np.array([presence_count(e['cppn']) for e in arc.values()])
print(f"  n={len(ev)}  min={ev.min()}  median={int(np.median(ev))}  max={ev.max()}")
print(f"  fraction under 300: {100*(ev<=300).mean():.1f}%   under 500: {100*(ev<=500).mean():.1f}%")
print(f"  -> evolution is asking for ~{int(np.median(ev))} voxels; the cap then trims to top-K")

# --- 3. what does the trim actually select? contiguity check ---
print("\n=== effect of the trim (cap=500) on a sample body ===")
cg.MAX_VOXELS_PER_ROBOT = 500
import src.evolution.genome_config as gc; gc.MAX_VOXELS_PER_ROBOT = 500
rng2 = np.random.default_rng(5); innov2 = InnovationCounter()
for _ in range(50):
    c = CPPNGenome(innov2, rng2)
    n_pre = presence_count(c)
    g = c.to_voxel_grid()
    if g is not None:
        n_post = int((g != 0).sum())
        # bounding box of the final body
        idx = np.argwhere(g != 0)
        bb = idx.max(0) - idx.min(0) + 1
        fill = n_post / np.prod(bb)
        print(f"  presence-gate={n_pre:5d} -> final={n_post:4d} voxels | bbox={tuple(bb)} "
              f"| fill-density={fill:.2f} (1.0 = solid brick, <0.5 = limby/hollow)")
        break
