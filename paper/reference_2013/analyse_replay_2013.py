"""How well does the 2013 simulator, rebuilt from the authors' source with g++ 15 in WSL, reproduce
the scores recorded in the deposited robot files?  Input: replay_2013_simulator.csv (written by
replay_in_2013_simulator.sh).  Score = final centre-of-mass distance / workspace width (10 voxels
of 1 mm = 0.01 m), exactly as in HCUBE_SoftbotsExperiment.cpp.

usage:  python paper/reference_2013/analyse_replay_2013.py
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_M = 10 * 0.001


def spearman(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def describe(name, d):
    r = d['ratio'].to_numpy()
    print(f"\n{name}  (n = {len(d)})")
    print(f"  recorded median {d['recorded'].median():.3f}   reproduced median {d['reproduced'].median():.3f}")
    print(f"  ratio reproduced/recorded: median {np.median(r):.4f}   mean {r.mean():.4f}   "
          f"5th-95th percentile {np.percentile(r, 5):.3f}-{np.percentile(r, 95):.3f}   min {r.min():.3f}  max {r.max():.3f}")
    for tol in (0.001, 0.01, 0.05, 0.20):
        print(f"  within {100 * tol:>4.1f}% of the recorded score: {100 * np.mean(np.abs(r - 1) <= tol):5.1f}%")
    print(f"  rank agreement (Spearman) {spearman(d['recorded'], d['reproduced']):+.4f}   "
          f"Pearson {np.corrcoef(d['recorded'], d['reproduced'])[0, 1]:+.4f}")


def main():
    df = pd.read_csv(os.path.join(HERE, 'replay_2013_simulator.csv'))
    df = df.rename(columns={'recorded_orig_fit': 'recorded'})
    df['reproduced'] = df['final_com_dist_m'] / WORKSPACE_M
    print(f"{len(df)} robots, {df['final_com_dist_m'].isna().sum()} without a result; "
          f"simulation time per robot: median {df['seconds'].median():.1f} s, max {df['seconds'].max():.1f} s")
    scored = df[df['recorded'] >= 0.01].copy()
    scored['ratio'] = scored['reproduced'] / scored['recorded']
    print(f"{len(df) - len(scored)} robots have a recorded score below 0.01 (failed or empty) and are left out of the ratios")

    for cond, d in scored.groupby('condition'):
        describe(f"{cond}: all final-population robots", d)
        champs = d.loc[d.groupby('run')['recorded'].idxmax()]
        describe(f"{cond}: the 35 run champions", champs)
    describe("both conditions together", scored)

    # identical genomes appear several times in a population: are their results identical too?
    g = scored.groupby(['condition', 'run', 'recorded'])['reproduced']
    spread = (g.max() - g.min())
    multi = g.count() > 1
    print(f"\nrepeat copies of the same robot within a run: {int(multi.sum())} groups; "
          f"largest difference between copies {spread[multi].max():.2e} (0 = the simulator is deterministic)")


if __name__ == '__main__':
    main()
