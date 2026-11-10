"""AFPO vs MAP-Elites A/B on flex (throwaway). Matched pop/gen/seed, material gait,
vanilla settings (MAP-Elites default uniform parent). 3 seeds. Best forward-BL per run."""
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

res = {"afpo": {}, "map_elites": {}}
for seed in (1, 2, 3):
    subprocess.run(BASE + ["--seed", str(seed), "--name", f"afpo_s{seed}"], capture_output=True)
    res["afpo"][seed] = best_of(f"afpo_s{seed}")
    print(f"AFPO       seed {seed}: {res['afpo'][seed]}", flush=True)
    subprocess.run(BASE + ["--map-elites", "--seed", str(seed), "--name", f"me_s{seed}"],
                   capture_output=True)
    res["map_elites"][seed] = best_of(f"me_s{seed}")
    print(f"MAP-Elites seed {seed}: {res['map_elites'][seed]}", flush=True)

af = [res["afpo"][s] for s in (1, 2, 3)]
me = [res["map_elites"][s] for s in (1, 2, 3)]
res["summary"] = {"afpo_per_seed": af, "map_elites_per_seed": me,
                  "afpo_mean": round(float(np.mean(af)), 4),
                  "map_elites_mean": round(float(np.mean(me)), 4)}
json.dump(res, open("results/afpo_vs_me_results.json", "w"), indent=2)
print("SUMMARY:", res["summary"], flush=True)
