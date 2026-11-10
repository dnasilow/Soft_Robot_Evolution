"""
Convert a MAP-Elites archive.pkl into a final_population.pkl that the AFPO run can
warm-start from with --seed-from.

    python seed_from_archive.py results/gait_qd3_1000

Writes results/gait_qd3_1000/final_population.pkl (keys: cppns, genomes, controllers,
fitnesses, ages, innov_next), elites sorted best-first so --seed-frac keeps the top ones.
"""
import pickle, sys
from pathlib import Path


def main(run_dir):
    run = Path(run_dir)
    d = pickle.load(open(run / "archive.pkl", "rb"))
    archive = d["archive"]                       # {(i,j): {'cppn','genome','fitness','desc'}}
    cells = sorted(archive.values(), key=lambda c: c["fitness"], reverse=True)

    cppns   = [c["cppn"]   for c in cells]
    genomes = [c["genome"] for c in cells]
    fits    = [float(c["fitness"]) for c in cells]
    ctrls   = [None] * len(cells)                # open-loop: no controllers

    # innov_next must exceed every innovation/node id in the seed so new mutations
    # never collide with existing genes.
    hi = 0
    for cp in cppns:
        for cg in cp.connections.values():
            hi = max(hi, int(cg.innovation))
        for nid in cp.nodes.keys():
            hi = max(hi, int(nid))
    innov_next = hi + 1

    out = run / "final_population.pkl"
    with open(out, "wb") as f:
        pickle.dump({
            "cppns": cppns, "genomes": genomes, "controllers": ctrls,
            "fitnesses": fits, "ages": [0] * len(cells), "innov_next": innov_next,
        }, f)
    print(f"wrote {out}  ({len(cells)} elites, best={fits[0]:.4f} BL, "
          f"innov_next={innov_next})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/gait_qd3_1000")
