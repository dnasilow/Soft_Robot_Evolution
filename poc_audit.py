"""Proof-of-concept validation for the audit improvements (throwaway driver).
Runs short flex MAP-Elites runs varying one new knob at a time; collects final
max forward-BL + coverage to results/poc_audit_results.json."""
import subprocess, json, glob, sys

COMMON = [sys.executable, "run_tendon_evolution.py", "--flex", "--map-elites",
          "--pop", "30", "--gen", "20", "--sim-time", "2.0", "--settle", "0.3",
          "--amp", "0.6", "--freq", "7", "--workers", "28", "--seed", "11", "--no-resume"]

CONFIGS = [
    ("poc_base",   ["--gait", "material", "--fitness", "directed", "--parent", "uniform"]),
    ("poc_wave",   ["--gait", "wave", "--gait-wavenum", "2", "--fitness", "directed", "--parent", "uniform"]),
    ("poc_biased", ["--gait", "material", "--fitness", "directed", "--parent", "biased"]),
    ("poc_curio",  ["--gait", "material", "--fitness", "directed", "--parent", "curiosity"]),
    ("poc_eff",    ["--gait", "material", "--fitness", "efficiency", "--parent", "uniform"]),
]

results = {}
for name, extra in CONFIGS:
    subprocess.run(COMMON + ["--name", name] + extra, capture_output=True)
    fs = sorted(glob.glob(f"results/{name}/gen_*.json"))
    if fs:
        mx = max(json.load(open(f))["max_fitness"] for f in fs)
        last = json.load(open(fs[-1]))
        results[name] = {"max_bl": round(mx, 4), "coverage": last["coverage"],
                         "qd": round(last["qd_score"], 3), "gens": len(fs),
                         "opts": extra}
    else:
        results[name] = {"error": "no output"}
    print(name, results[name], flush=True)

json.dump(results, open("results/poc_audit_results.json", "w"), indent=2)
print("SAVED results/poc_audit_results.json", flush=True)
