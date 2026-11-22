"""Unit test: per-voxel phase CPPN genome mechanics (breeding, propagation, backward-compat)."""
import numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

rng = np.random.default_rng(0)
innov = InnovationCounter()

# 1. Fresh genome: no phase CPPN by default (backward compat)
a = CPPNGenome(innov, rng)
assert a.phase_cppn is None, "default should be None"
assert not a.has_phase_cppn()

# 2. init_phase_cppn creates a separate control net
a.init_phase_cppn(rng)
assert a.has_phase_cppn(), "should have phase cppn after init"
assert a.phase_cppn.phase_cppn is None, "phase net must not have its own phase net (no recursion)"
print(f"phase net: {a.phase_cppn.n_nodes} nodes, {a.phase_cppn.n_connections} conns")

# 3. Phase net evaluates to per-position phases
coords = np.random.default_rng(1).uniform(-1, 1, size=(50, 4)).astype(np.float32)
raw = a.phase_cppn.evaluate_batch(coords)[:, 0]
phases = np.pi * raw
assert raw.shape == (50,), raw.shape
assert np.all(np.abs(phases) <= np.pi + 1e-6), "phases must be in [-pi,pi]"
print(f"phase output: min={phases.min():.3f} max={phases.max():.3f} spread={np.ptp(phases):.3f}")
assert np.ptp(phases) > 0.01, "phase field should not be constant"

# 4. Clone propagates phase net (independent copy)
b = a._clone()
assert b.has_phase_cppn() and b.phase_cppn is not a.phase_cppn, "clone must deep-copy phase net"

# 5. Mutation co-evolves the phase net (produces a different net)
before = a.phase_cppn.evaluate_batch(coords)[:, 0].copy()
c = a.mutate(innov, rate=1.0)   # high rate to force change
after = c.phase_cppn.evaluate_batch(coords)[:, 0]
assert c.has_phase_cppn()
d = float(np.abs(before - after).mean())
print(f"mutation changed phase field by mean |dphase|={np.pi*d:.4f}")
assert d > 1e-6, "mutation should perturb the phase net"
# original unchanged (mutate returns a copy)
assert np.allclose(before, a.phase_cppn.evaluate_batch(coords)[:, 0]), "parent must be unchanged"

# 6. Crossover inherits fitter parent's phase net
p1 = CPPNGenome(innov, rng); p1.init_phase_cppn(rng)
p2 = CPPNGenome(innov, rng); p2.init_phase_cppn(rng)
child = CPPNGenome.crossover(p1, p2, 1.0, 0.0, rng=rng)  # p1 fitter
assert child.has_phase_cppn(), "crossover child should carry a phase net"

# 7. Backward compat: a genome pickled WITHOUT phase_cppn (simulate old pickle) still works
old = CPPNGenome(innov, rng)
del old.phase_cppn                      # simulate a genome from before this attribute existed
assert getattr(old, 'phase_cppn', None) is None
o2 = old._clone()                        # getattr-guarded paths must not crash
assert getattr(o2, 'phase_cppn', None) is None
og = old.mutate(innov, rate=0.3)         # mutate must not crash on missing attr
print("backward-compat (missing phase_cppn attr): OK")

print("\nALL UNIT CHECKS PASSED")
