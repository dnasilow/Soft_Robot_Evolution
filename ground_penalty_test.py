"""Does the ground_fraction penalty cap speed? (throwaway)
Ants are fast BECAUSE they leave the ground (aerial gallop); our 'directed' fitness
PENALISES leaving the ground. Compare evolved champions under:
  directed  = forward_BL x ground_fraction  (default; penalises air time)
  forward   = forward_BL                     (no ground penalty; bouncing allowed)
Then re-measure each champion's RAW forward distance + bounce, head to head."""
import subprocess, json, glob, sys, pickle
import numpy as np
from src.physics.mujoco_flex_physics import MuJoCoFlexPhysics

BASE = [sys.executable, "run_tendon_evolution.py", "--flex", "--map-elites",
        "--parent", "biased", "--pop", "40", "--gen", "60", "--sim-time", "2.0",
        "--settle", "0.3", "--amp", "0.6", "--freq", "7", "--workers", "28",
        "--seed", "1", "--no-resume"]

for mode, name in [("directed", "gp_directed"), ("forward", "gp_forward")]:
    subprocess.run(BASE + ["--fitness", mode, "--name", name], capture_output=True)

def raw_measure(name):
    """Re-measure the champion's raw forward BL + vertical bounce (mode-independent)."""
    d = pickle.load(open(f"results/{name}/best_robot.pkl", "rb"))
    eng = MuJoCoFlexPhysics(actuation_frequency=7, actuation_amplitude=0.6)
    eng.load_robot(d["genome"], voxel_size=0.05)
    f, (height, bounce) = eng.get_fitness(simulation_time=2.0, settle_time=0.3,
                                          return_descriptors=True)
    return round(f, 4), round(height, 4), round(bounce, 4)

res = {}
for mode, name in [("directed", "gp_directed"), ("forward", "gp_forward")]:
    fwd, h, b = raw_measure(name)
    res[mode] = {"raw_forward_bl": fwd, "com_height": h, "bounce": b}
    print(f"{mode:9s}: raw_forward={fwd} BL  com_height={h}  bounce={b}", flush=True)
json.dump(res, open("results/ground_penalty_results.json", "w"), indent=2)
print("SAVED results/ground_penalty_results.json", flush=True)
