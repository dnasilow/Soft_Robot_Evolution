"""Why do champions use 0% passive material? Decode-bias vs selected-out."""
import pickle
import numpy as np
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

LABELS = {1: 'act0', 2: 'act180', 3: 'soft', 4: 'stiff'}


def mat_pct(genomes):
    agg = {1: 0, 2: 0, 3: 0, 4: 0}
    for g in genomes:
        for m in (1, 2, 3, 4):
            agg[m] += int((g == m).sum())
    tot = sum(agg.values()) or 1
    return {LABELS[m]: round(100 * agg[m] / tot, 1) for m in (1, 2, 3, 4)}


# 1. RANDOM bodies (no selection) — is the decode itself biased against passive?
innov = InnovationCounter()
rng = np.random.default_rng(0)
rand = []
for _ in range(400):
    g = CPPNGenome(innov, rng).to_voxel_grid()
    if g is not None:
        rand.append(g)
print(f"RANDOM   ({len(rand)} bodies, no selection): {mat_pct(rand)}")

# 2. EVOLVED final population — what did selection keep?
d = pickle.load(open('results/plateau_test_elite/final_population.pkl', 'rb'))
print(f"EVOLVED  ({len(d['genomes'])} final robots, seed 42): {mat_pct(d['genomes'])}")

# interpretation
print("\nIf RANDOM is ~uniform (~25% each) but EVOLVED ~0% passive -> selected out (evolution's")
print("choice, Cheney-consistent). If RANDOM also suppresses passive -> a decode bias to fix.")
