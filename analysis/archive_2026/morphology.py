"""How does SHAPE actually get evolved? Trace + measure:
 1. shape = a level set of the CPPN's presence field (top-K superlevel set)
 2. how much does ONE mutation move the shape?
 3. what does the champion's CPPN look like (activations/topology) & is the body symmetric?"""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter, _build_coord_grid

coords, dims = _build_coord_grid()
d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
champ = d['cppn']; G = d['genome']

# ---- 1. the presence field IS the shape ----
lg = champ.evaluate_batch(coords)[:, 0]
print("=== 1. presence field of the 1.3201 champion (one number per grid position) ===")
print(f"  5832 positions | presence logit: min={lg.min():+.3f} max={lg.max():+.3f} "
      f"mean={lg.mean():+.3f}")
print(f"  passing gate (logit>0): {int((lg>0).sum())}  -> trimmed to top-{int((G!=0).sum())} by confidence")
thr = np.sort(lg)[-int((G!=0).sum())]
print(f"  => the body is exactly the level set  {{ presence_logit >= {thr:+.4f} }}")

# ---- 2. how much does ONE mutation change the shape? ----
print("\n=== 2. effect of a single mutation on the body (Jaccard overlap with parent) ===")
innov = InnovationCounter(); rng = np.random.default_rng(0)
base = (G != 0)
ovl = []
for _ in range(25):
    ch = champ.mutate(innov, rate=0.3)
    g2 = ch.to_voxel_grid()
    if g2 is None: continue
    b2 = (g2 != 0)
    j = (base & b2).sum() / (base | b2).sum()
    ovl.append(j)
ovl = np.array(ovl)
print(f"  n={len(ovl)}  overlap: min={ovl.min():.2f} median={np.median(ovl):.2f} max={ovl.max():.2f}")
print("  -> high overlap = smooth/heritable shape change; low = mutation can jump shape")

# ---- 3. what's inside the champion CPPN, and is the body symmetric? ----
print("\n=== 3. the champion's body CPPN ===")
acts = {}
for n in champ.nodes.values():
    if n.node_type == 'hidden':
        acts[n.activation] = acts.get(n.activation, 0) + 1
print(f"  nodes={champ.n_nodes} (hidden={sum(acts.values())})  enabled connections={champ.n_connections}")
print(f"  hidden activations: {acts if acts else '(none - still the minimal 4->6 network)'}")

# symmetry: CPPNs make symmetric bodies when they depend on |y| etc.
occ = (G != 0)
for ax, nm in [(0,'X (fore-aft)'), (1,'Y (left-right)'), (2,'Z (up-down)')]:
    mir = np.flip(occ, axis=ax)
    # align by bounding box before comparing
    idx = np.argwhere(occ); lo = idx.min(0); hi = idx.max(0)
    sub = occ[lo[0]:hi[0]+1, lo[1]:hi[1]+1, lo[2]:hi[2]+1]
    sm  = np.flip(sub, axis=ax)
    j = (sub & sm).sum() / (sub | sm).sum()
    print(f"  mirror-symmetry about {nm}: {j:.2f}  (1.0 = perfectly symmetric)")
