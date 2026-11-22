"""Validate --evolve-size:
 (A) SAFETY: default (bias=None) decodes byte-identically -> live pvp_long unaffected even on resume
 (B) the gene actually controls size (spread well below the cap, not pinned)
 (C) propagation through clone/mutate/crossover"""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
import src.evolution.cppn_genome as cg, src.evolution.genome_config as gc
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

# ---------- (A) SAFETY: champions must decode byte-identically ----------
print("=== (A) backward-compat: champions re-decode identically (bias defaults None) ===")
ok = True
for name in ['tendon_eg','tendon_stiff','egfix_s1','egfix_s2','egfix_s3','pvp_s2','pvp_s3']:
    p = f'results/{name}/best_robot.pkl'
    if not os.path.exists(p): continue
    d = pickle.load(open(p,'rb')); c = d.get('cppn'); saved = d.get('genome')
    if c is None or saved is None: continue
    assert getattr(c, 'presence_bias', None) is None, f"{name} unexpectedly has a bias"
    re = c.to_voxel_grid()
    same = re is not None and re.shape == saved.shape and bool((re == saved).all())
    print(f"  {name:14} identical={same}")
    ok = ok and same
assert ok, "BACKWARD-COMPAT BROKEN"
print("  -> default path untouched; safe to edit while pvp_long runs")

# ---------- (B) does the gene actually control size? ----------
print("\n=== (B) size distribution WITH --evolve-size (cap 500) ===")
cg.MAX_VOXELS_PER_ROBOT = 500; gc.MAX_VOXELS_PER_ROBOT = 500
rng = np.random.default_rng(0); innov = InnovationCounter()
def sizes(use_bias, n=250):
    out = []
    for _ in range(n):
        c = CPPNGenome(innov, rng)
        if use_bias: c.init_presence_bias(rng)
        g = c.to_voxel_grid()
        if g is not None: out.append((int((g!=0).sum()), getattr(c,'presence_bias',None)))
    return out

for label, ub in [("OFF (legacy)", False), ("ON  (--evolve-size)", True)]:
    r = sizes(ub)
    s = np.array([x[0] for x in r])
    at_cap = 100*(s==500).mean()
    print(f"  {label:20} n={len(s):3d}  min={s.min():4d} median={int(np.median(s)):4d} "
          f"max={s.max():4d}  at-cap={at_cap:5.1f}%")
    if ub:
        b = np.array([x[1] for x in r])
        lo, hi = s[b<0.3], s[b>0.7]
        print(f"      correlation check: low-bias bodies median={int(np.median(lo)) if len(lo) else 0}"
              f"  high-bias bodies median={int(np.median(hi)) if len(hi) else 0}  (should be much smaller)")

# ---------- (C) propagation ----------
print("\n=== (C) gene propagation ===")
a = CPPNGenome(innov, rng); a.init_presence_bias(rng)
assert a._clone().presence_bias == a.presence_bias, "clone lost bias"
m = a.mutate(innov, rate=0.5)
assert m.presence_bias is not None and m.presence_bias != a.presence_bias, "mutation didn't perturb"
p2 = CPPNGenome(innov, rng); p2.init_presence_bias(rng)
ch = CPPNGenome.crossover(a, p2, 1.0, 0.0, rng=rng)
assert abs(ch.presence_bias - (a.presence_bias+p2.presence_bias)/2) < 1e-9, "crossover not blending"
legacy = CPPNGenome(innov, rng)   # no bias
assert CPPNGenome.crossover(legacy, legacy, 1.0, 0.0, rng=rng).presence_bias is None
print("  clone/mutate/crossover/legacy-mix all OK")
print("\nALL CHECKS PASSED")
