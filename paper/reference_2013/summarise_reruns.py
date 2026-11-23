"""Compare re-runs of the ORIGINAL 2013 experiment (run_2013_search.sh, collected by
collect_2013_runs.sh into results/rerun2013/) with the deposited 2013 runs, generation by
generation. The score is the champion's original fitness, best so far, read the same way from
both.

usage:  python paper/reference_2013/summarise_reruns.py <prefix> [--condition noCost|costNumActuated]
        e.g.  python paper/reference_2013/summarise_reruns.py pilot10_P0
"""
import argparse
import glob
import io
import os
import sys

import numpy as np
from scipy.stats import mannwhitneyu

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from summarise_run import deposited_curves          # noqa: E402

GENS = (1, 2, 5, 10, 20, 30, 50, 100, 200, 300, 600, 1000)


def read_curve(path):
    rows = []
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.split()
        if not p or p[0].startswith('#'):
            continue
        try:
            rows.append((float(p[0]), float(p[1])))
        except (ValueError, IndexError):
            continue
    a = np.array(rows)
    return np.maximum.accumulate(a[:, 1]) if len(a) else np.zeros(0)


def run_order(folder):
    """Runs in the order of their seed number (armR_P0_s2 before armR_P0_s10). The bootstrap below
    then draws exactly as paper/analysis/analyse_arm.py does, so both give the same interval."""
    name = os.path.basename(folder)
    digits = name[len(name.rstrip('0123456789')):]
    return (int(digits) if digits else 0, name)


def a12(x, y):
    """Vargha-Delaney A12: probability that a value of x exceeds a value of y (ties count half)."""
    x, y = np.asarray(x), np.asarray(y)
    return float(((x[:, None] > y[None, :]).sum() + 0.5 * (x[:, None] == y[None, :]).sum()) / (len(x) * len(y)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('prefix')
    ap.add_argument('--condition', default='noCost', choices=['noCost', 'costNumActuated'])
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    runs = {}
    for d in sorted(glob.glob(os.path.join(ROOT, 'results', 'rerun2013', a.prefix + '*')), key=run_order):
        if not os.path.isfile(os.path.join(d, 'curve.txt')):      # log files; runs before generation 1
            continue
        c = read_curve(os.path.join(d, 'curve.txt'))
        if len(c):
            runs[os.path.basename(d)] = c
    if not runs:
        raise SystemExit(f'no collected runs match results/rerun2013/{a.prefix}*')
    dep = deposited_curves(f'2013-01-16-10^3-{a.condition}/')
    lens = [len(c) for c in runs.values()]
    print(f"{len(runs)} re-runs ({a.prefix}*), generations completed: min {min(lens)}, max {max(lens)};  "
          f"deposited: {len(dep)} runs ({a.condition})")
    print(f"\n{'gen':>5}{'re-run n':>9}{'re-run median':>15}{'(25-75%)':>14}{'deposited median':>18}{'(25-75%)':>14}"
          f"{'ratio':>7}{'A12':>6}{'p (MWU)':>9}")
    rng = np.random.default_rng(0)
    for g in GENS:
        x = np.array([c[g - 1] for c in runs.values() if len(c) >= g])
        if len(x) < 3:
            break
        y = np.array([c[min(g, len(c)) - 1] for c in dep])
        p = mannwhitneyu(x, y, alternative='two-sided').pvalue
        print(f"{g:>5}{len(x):>9}{np.median(x):>15.3f}{f'{np.percentile(x, 25):.2f}-{np.percentile(x, 75):.2f}':>14}"
              f"{np.median(y):>18.3f}{f'{np.percentile(y, 25):.2f}-{np.percentile(y, 75):.2f}':>14}"
              f"{np.median(x) / np.median(y):>7.2f}{a12(x, y):>6.2f}{p:>9.3f}")
    g = min(lens)
    x = np.array([c[g - 1] for c in runs.values()])
    y = np.array([c[min(g, len(c)) - 1] for c in dep])
    boot = [np.median(rng.choice(x, len(x))) / np.median(rng.choice(y, len(y))) for _ in range(10000)]
    print(f"\nAt generation {g}: ratio of medians {np.median(x) / np.median(y):.3f}, "
          f"bootstrapped 95% interval {np.percentile(boot, 2.5):.3f}-{np.percentile(boot, 97.5):.3f}")
    print("Per run, champion score at that generation:",
          ', '.join(f'{v:.2f}' for v in sorted(x)))
    print()
    print("This is the quick view, generation by generation. The analysis fixed in the protocol (criterion,")
    print("body measures, every seed) is:  python paper/analysis/analyse_arm.py --arm R")
    print("                                (for runs that are not an arm: --pilot <prefix> --generation N)")


if __name__ == '__main__':
    main()
