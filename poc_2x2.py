"""Complete the 2x2: AFPO/MAP-Elites x material/evolvable-gait on flex (throwaway).
Material results reused from results/afpo_vs_me_results.json; here we run the two
evolve-gait combos (3 seeds), then assemble the full grid."""
import subprocess, json, glob, sys
import numpy as np

BASE = [sys.executable, "run_tendon_evolution.py", "--flex", "--pop", "40", "--gen", "60",
        "--sim-time", "2.0", "--settle", "0.3", "--amp", "0.6", "--freq", "7",
        "--workers", "28", "--no-resume"]

def best_of(name):
    fs = sorted(glob.glob(f"results/{name}/gen_*.json"))
    if not fs:
        return None
    vals = [json.load(open(f)).get("best_fitness", json.load(open(f)).get("max_fitness", 0))
            for f in fs]
    return round(max(vals), 4)

new = {"afpo_evolve": {}, "me_evolve": {}}
for seed in (1, 2, 3):
    subprocess.run(BASE + ["--evolve-gait", "--seed", str(seed), "--name", f"afpoeg_s{seed}"],
                   capture_output=True)
    new["afpo_evolve"][seed] = best_of(f"afpoeg_s{seed}")
    print(f"AFPO+evolve  seed {seed}: {new['afpo_evolve'][seed]}", flush=True)
    subprocess.run(BASE + ["--map-elites", "--evolve-gait", "--seed", str(seed),
                           "--name", f"meeg_s{seed}"], capture_output=True)
    new["me_evolve"][seed] = best_of(f"meeg_s{seed}")
    print(f"ME+evolve    seed {seed}: {new['me_evolve'][seed]}", flush=True)

mat = json.load(open("results/afpo_vs_me_results.json"))
def mean(d): return round(float(np.mean([d[s] for s in (1, 2, 3)])), 4)
grid = {
    "afpo_material":   {"per_seed": mat["afpo"],       "mean": mat["summary"]["afpo_mean"]},
    "afpo_evolve":     {"per_seed": new["afpo_evolve"], "mean": mean(new["afpo_evolve"])},
    "me_material":     {"per_seed": mat["map_elites"], "mean": mat["summary"]["map_elites_mean"]},
    "me_evolve":       {"per_seed": new["me_evolve"],  "mean": mean(new["me_evolve"])},
}
json.dump(grid, open("results/poc_2x2_results.json", "w"), indent=2)
print("\n2x2 GRID (mean best forward-BL, flex pop40/gen60, 3 seeds):", flush=True)
for k, v in grid.items():
    print(f"  {k:16s} mean={v['mean']}  seeds={list(v['per_seed'].values())}", flush=True)
