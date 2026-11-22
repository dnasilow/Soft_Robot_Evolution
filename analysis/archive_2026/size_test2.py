"""Validate --evolve-size (v2: target-size gene):
 (A) SAFETY: default decodes byte-identically -> live pvp_long unaffected
 (B) size is genuinely evolvable (spread, not pinned at cap) and tracks the gene
 (C) propagation clone/mutate/crossover + legacy mixing"""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
import src.evolution.cppn_genome as cg, src.evolution.genome_config as gc
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

print("=== (A) backward-compat: champions re-decode byte-identically ===")
ok = True
for name in ['tendon_eg','tendon_stiff','egfix_s1','egfix_s2','egfix_s3','pvp_s2','pvp_s3']:
    p = f'results/{name}/best_robot.pkl'
    if not os.path.exists(p): continue
    d = pickle.load(open(p,'rb')); c = d.get('cppn'); saved = d.get('genome')
    if c is None or saved is None: continue
    assert getattr(c, 'size_gene', None) is None
    re = c.to_voxel_grid()
    same = re is not None and re.shape == saved.shape and bool((re == saved).all())
    print(f"  {name:14} identical={same}")
    ok = ok and same
assert ok, "BACKWARD-COMPAT BROKEN"
print("  -> default path untouched; safe while pvp_long runs (even on resume)")

print("\n=== (B) size distribution, cap=500 ===")
cg.MAX_VOXELS_PER_ROBOT = 500; gc.MAX_VOXELS_PER_ROBOT = 500
rng = np.random.default_rng(0); innov = InnovationCounter()
def run(use_gene, n=250):
    out=[]
    for _ in range(n):
        c = CPPNGenome(innov, rng)
        if use_gene: c.init_size_gene(rng)
        g = c.to_voxel_grid()
        if g is not None: out.append((int((g!=0).sum()), getattr(c,'size_gene',None)))
    return out
for label, ug in [("OFF (legacy)", False), ("ON  (--evolve-size)", True)]:
    r = run(ug); s = np.array([x[0] for x in r])
    print(f"  {label:20} n={len(s):3d} min={s.min():4d} p25={int(np.percentile(s,25)):4d} "
          f"median={int(np.median(s)):4d} p75={int(np.percentile(s,75)):4d} max={s.max():4d} "
          f"at-cap={100*(s==500).mean():5.1f}%")
    if ug:
        gene = np.array([x[1] for x in r])
        corr = np.corrcoef(gene, s)[0,1]
        print(f"      gene->size correlation = {corr:+.3f} (want ~+1: gene controls size)")
        for lo,hi in [(0.15,0.35),(0.35,0.65),(0.65,1.01)]:
            m = (gene>=lo)&(gene<hi)
            if m.sum(): print(f"        gene {lo:.2f}-{hi:.2f}: median size {int(np.median(s[m])):4d}  (n={m.sum()})")

print("\n=== (C) propagation ===")
a = CPPNGenome(innov, rng); a.init_size_gene(rng)
assert a._clone().size_gene == a.size_gene
m = a.mutate(innov, rate=0.5); assert m.size_gene is not None and m.size_gene != a.size_gene
p2 = CPPNGenome(innov, rng); p2.init_size_gene(rng)
ch = CPPNGenome.crossover(a, p2, 1.0, 0.0, rng=rng)
assert abs(ch.size_gene - (a.size_gene+p2.size_gene)/2) < 1e-9
lg = CPPNGenome(innov, rng)
assert CPPNGenome.crossover(lg, lg, 1.0, 0.0, rng=rng).size_gene is None
print("  clone/mutate/crossover/legacy-mix OK")
print("\nALL CHECKS PASSED")
