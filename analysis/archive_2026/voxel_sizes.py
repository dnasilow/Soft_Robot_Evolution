"""Confirm: with --max-voxels 500, bodies actually decode up to ~500 voxels (vs 300 cap).
This does NOT touch the live pvp_long run — it decodes fresh CPPNs with the same decoder."""
import numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
import src.evolution.cppn_genome as cg, src.evolution.genome_config as gc
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

for cap in (300, 500):
    cg.MAX_VOXELS_PER_ROBOT = cap; gc.MAX_VOXELS_PER_ROBOT = cap
    rng = np.random.default_rng(0); innov = InnovationCounter()
    sizes = []
    for _ in range(200):
        g = CPPNGenome(innov, rng).to_voxel_grid()
        if g is not None:
            sizes.append(int((g != 0).sum()))
    s = np.array(sizes)
    at_cap = int((s == cap).sum())
    print(f"cap={cap}: {len(s)} valid bodies | voxels min={s.min()} median={int(np.median(s))} "
          f"max={s.max()} | {at_cap} bodies ({100*at_cap/len(s):.0f}%) hit the {cap} cap exactly")
