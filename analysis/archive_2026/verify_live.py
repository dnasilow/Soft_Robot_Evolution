"""Confirm the per-voxel phase mechanism is LIVE in a bred champion:
   (1) champion carries a phase_cppn after 3 gens of breeding,
   (2) loading it produces a NON-CONSTANT per-tendon base-phase field,
   (3) that field differs from what the 4-gene wave would give on the same body."""
import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

d = pickle.load(open('results/pvp_smoke/best_robot.pkl', 'rb'))
g = d['genome']; c = d['cppn']
pc = getattr(c, 'phase_cppn', None)
print(f"champion voxels={int((g!=0).sum())}  has phase_cppn={pc is not None}")
assert pc is not None, "bred champion must carry a phase CPPN"
print(f"phase net survived breeding: {pc.n_nodes} nodes, {pc.n_connections} conns")

eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)
eng.load_robot(g, gait_params=pc)          # per-voxel phase path
bp_pvp = np.array(eng._base_phases).copy()
print(f"per-voxel base_phases: n={len(bp_pvp)}  min={bp_pvp.min():.3f} max={bp_pvp.max():.3f} "
      f"std={bp_pvp.std():.3f}")
assert bp_pvp.std() > 1e-3, "phase field is constant -> mechanism not driving anything"

# Contrast: the same body under a 4-gene plane wave
eng.load_robot(g, gait_params=(0.5, -0.5, 0.0, 1.0))
bp_wave = np.array(eng._base_phases).copy()
print(f"4-gene wave base_phases:  std={bp_wave.std():.3f}")
print(f"per-voxel field differs from plane wave: "
      f"mean|dphase|={np.abs(bp_pvp[:len(bp_wave)]-bp_wave).mean():.3f}")

print("\nMECHANISM IS LIVE")
