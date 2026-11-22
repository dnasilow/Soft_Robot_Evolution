"""Verify per-voxel phase drives a MUSCLE body: find an archive elite with active
tendons, confirm its phase_cppn produces a non-constant per-tendon phase field."""
import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

arc = pickle.load(open('results/pvp_smoke/archive.pkl', 'rb'))['archive']
champ = pickle.load(open('results/pvp_smoke/best_robot.pkl', 'rb'))
mats = {m: int((champ['genome'] == m).sum()) for m in (1,2,3,4)}
print(f"smoke champion materials {mats}  (mat1,2=muscle; 3=soft,4=stiff)")

eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)

def n_active(g):
    eng.load_robot(g)
    return int(len(eng._base_phases))

# scan archive for an elite whose body has muscle (active tendons)
found = None
for cell, e in sorted(arc.items(), key=lambda kv: -kv[1]['fitness']):
    if n_active(e['genome']) > 0 and getattr(e['cppn'], 'phase_cppn', None) is not None:
        found = e; break

if found is None:
    print("no muscle-bearing elite in this tiny 3-gen smoke archive; testing on a FRESH muscle body")
    from src.evolution.cppn_genome import CPPNGenome, InnovationCounter
    rng = np.random.default_rng(7); innov = InnovationCounter()
    for _ in range(200):
        c = CPPNGenome(innov, rng); g = c.to_voxel_grid()
        if g is not None and n_active(g) > 0:
            c.init_phase_cppn(rng); found = {'genome': g, 'cppn': c, 'fitness': float('nan')}
            break

g = found['genome']; pc = found['cppn'].phase_cppn
na = n_active(g)
print(f"muscle body: voxels={int((g!=0).sum())}  active tendons={na}  fitness={found['fitness']}")

eng.load_robot(g, gait_params=pc)
bp = np.array(eng._base_phases)
print(f"per-voxel base_phases: n={len(bp)} min={bp.min():.3f} max={bp.max():.3f} "
      f"std={bp.std():.3f} spread={np.ptp(bp):.3f}")
assert len(bp) == na and bp.std() > 1e-3, "phase field must be non-constant over active tendons"

eng.load_robot(g, gait_params=(0.5, -0.5, 0.0, 1.0))
bw = np.array(eng._base_phases)
print(f"plane-wave base_phases:  std={bw.std():.3f}   "
      f"per-voxel differs by mean|dphase|={np.abs(bp-bw).mean():.3f}")
print("\nMECHANISM IS LIVE ON MUSCLE BODIES")
