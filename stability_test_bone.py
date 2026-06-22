"""Stability check for stiffer 'bone' material (mat4 kp 100->300)."""
import pickle
import numpy as np
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
from src.evolution.genome_config import VOXEL_GRID_SHAPE


def test_body(name, g):
    eng = MuJoCoTendonPhysics()
    try:
        eng.load_robot(g)
        fit = eng.get_fitness(simulation_time=2.5, settle_time=0.5)
        pos = eng.get_position()
        stable = bool(np.all(np.isfinite(pos))) and float(np.abs(pos).max()) < 10.0
        print(f"{name:32s} voxels={int((g != 0).sum()):3d} fit={fit:7.4f} "
              f"pos_max={np.abs(pos).max():6.3f}  STABLE={stable}")
    except Exception as e:
        print(f"{name:32s} ERROR: {e}")


# worst cases for the stiffer springs
g = np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8); g[8:14, 8:14, 8:14] = 4; g[8:14, 8:14, 8] = 1
test_body("stiff bone block + active layer", g)

g2 = np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8); g2[8:13, 8:13, 8:13] = 4
test_body("all-stiff (pure passive bone)", g2)

g3 = np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8); g3[8:14, 8:14, 8:11] = 1; g3[8:14, 8:14, 11:14] = 4
test_body("muscle + bone mix", g3)

# regression: champion has 0 stiff -> fitness must be unchanged (~0.1726)
d = pickle.load(open('results/plateau_test_elite/best_robot.pkl', 'rb'))
test_body("champion (0 stiff, regression)", d['genome'])
print("\n(champion should reproduce ~0.1726 -> non-stiff bodies are unaffected by the change)")
