"""Statistics of the frozen protocol (paper/PROTOCOL.md, sections 5 and 9). Pure functions:
nothing here reads a run.

  compare              two samples of runs: medians, ratio of medians with its bootstrapped 95%
                       interval, Vargha-Delaney A12 with its interval, two-sided Mann-Whitney U
  verdict              the reproduction criterion, read three ways
  holm, holm_range     Holm correction; and what it can still become while a family is incomplete
  two_proportions      Fisher's exact test for a yes/no measure
  attainability        how often a PERFECT reproduction would meet the criterion, estimated from
                       the reference runs alone

The bootstrap resamples the runs of each side with replacement, independently, 10,000 times, and
takes the 2.5th and 97.5th percentiles. The random seed is fixed, so a report can be reproduced
to the last digit.
"""
import numpy as np
from scipy.stats import fisher_exact, mannwhitneyu

N_BOOT = 10000           # bootstrap resamples
SEED = 0
ATTAIN_TRIALS = 2000     # simulated perfect reproductions in attainability()
ATTAIN_BOOT = 2000       # bootstrap resamples inside each of them
CRITERION = (0.90, 1.10)
FAMILY = 5              # primary comparisons: R, Rc, A and D against the deposit, A against R


def a12(x, y):
    """Vargha-Delaney A12: the chance that a run of x beats a run of y (ties count half)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(((x[:, None] > y[None, :]).sum() + 0.5 * (x[:, None] == y[None, :]).sum()) / (len(x) * len(y)))


def ratio_of_medians(x, y):
    return float(np.median(x) / np.median(y))


def bootstrap_interval(stat, x, y, n=None, seed=None):
    """95% percentile interval of stat(x*, y*) over n resamples of the runs of each side."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = N_BOOT if n is None else n
    rng = np.random.default_rng(SEED if seed is None else seed)
    values = [stat(rng.choice(x, len(x)), rng.choice(y, len(y))) for _ in range(n)]
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def quartiles(v):
    v = np.asarray(v, float)
    return float(np.median(v)), float(np.percentile(v, 25)), float(np.percentile(v, 75))


def compare(x, y, n_boot=None, seed=None, with_ratio=True):
    """x: the arm's runs, y: the reference runs. Everything section 5 asks for one comparison."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx, x25, x75 = quartiles(x)
    my, y25, y75 = quartiles(y)
    test = mannwhitneyu(x, y, alternative='two-sided')
    out = {
        'n_arm': int(len(x)), 'n_reference': int(len(y)),
        'arm_median': mx, 'arm_q25': x25, 'arm_q75': x75,
        'reference_median': my, 'reference_q25': y25, 'reference_q75': y75,
        'a12': a12(x, y), 'a12_interval': list(bootstrap_interval(a12, x, y, n_boot, seed)),
        'mann_whitney_u': float(test.statistic), 'p': float(test.pvalue),
    }
    if with_ratio:
        out['ratio_of_medians'] = ratio_of_medians(x, y)
        out['ratio_interval'] = list(bootstrap_interval(ratio_of_medians, x, y, n_boot, seed))
    return out


def verdict(interval, window=CRITERION):
    """The criterion fixed in advance, and the two ways of not meeting it.

    'reproduces'           the interval of the ratio of medians lies inside the window
    'not distinguishable'  it does not, but it contains 1: no difference shown, and
                           reproduction within the window not shown either
    'differs'              it excludes 1
    """
    lo, hi = interval
    if lo >= window[0] and hi <= window[1]:
        return 'reproduces'
    if lo <= 1.0 <= hi:
        return 'not distinguishable'
    return 'differs'


def holm(pvalues):
    """Holm-adjusted p-values, in the order given."""
    p = np.asarray(pvalues, float)
    adjusted = np.empty(len(p))
    running = 0.0
    for rank, i in enumerate(np.argsort(p, kind='stable')):
        running = max(running, (len(p) - rank) * p[i])
        adjusted[i] = min(1.0, running)
    return adjusted.tolist()


def holm_range(p, family=FAMILY):
    """While the rest of its family is unknown, Holm leaves p somewhere in this range."""
    return float(p), float(min(1.0, family * p))


def two_proportions(k_arm, n_arm, k_ref, n_ref):
    """A yes/no measure: Fisher's exact test, two-sided."""
    p = fisher_exact([[k_arm, n_arm - k_arm], [k_ref, n_ref - k_ref]], alternative='two-sided')[1]
    return {'arm_yes': int(k_arm), 'n_arm': int(n_arm), 'reference_yes': int(k_ref),
            'n_reference': int(n_ref), 'p': float(p)}


def attainability(reference, n_runs, trials=None, n_boot=None, seed=None, window=CRITERION):
    """How often a perfect reproduction would meet the criterion.

    n_runs new runs are drawn from the reference runs themselves (so they come from the same
    distribution by construction) and analysed against the reference the way an arm is. The
    fraction of such draws whose interval lies inside the window is returned. It uses the
    reference runs alone; no run of any arm enters."""
    y = np.asarray(reference, float)
    trials = ATTAIN_TRIALS if trials is None else trials
    n_boot = ATTAIN_BOOT if n_boot is None else n_boot
    rng = np.random.default_rng(SEED if seed is None else seed)
    met = 0
    for _ in range(trials):
        x = rng.choice(y, n_runs)
        bx = np.median(rng.choice(x, (n_boot, n_runs)), axis=1)
        by = np.median(rng.choice(y, (n_boot, len(y))), axis=1)
        lo, hi = np.percentile(bx / by, [2.5, 97.5])
        met += bool(lo >= window[0] and hi <= window[1])
    return met / trials
