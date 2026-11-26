"""The transfer outcome under the campaign's two presets, champion by champion. PROTOCOL.md,
section 9.5, asks for the outcome under both; transfer_scores.py makes one report per preset.
This sets the two reports side by side: for every champion its transfer ratio on the hard floor
(--preset cheney2013, set on the floor: the outcome as fixed in section 9.4) and under the 2013
floor rule and start (--preset cheney2013-floor, the settings of arm D).

usage, from the project folder, when both reports are in paper/outcomes/:
    python paper/analysis/compare_presets.py

Per set of champions: how many keep more of their score under the second preset, the two-sided
Wilcoxon signed-rank test on the paired ratios (the test of the floor test of 25 November,
paper/diagnostics_2026-11-25/), and how far the champions are from keeping exactly their score
under each preset. Descriptive: no criterion, p-values not corrected. Nothing is simulated.
Written to paper/outcomes/transfer_presets.json.
"""
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

import protocol_stats as ps                                   # noqa: E402
import transfer_scores as ts                                  # noqa: E402

OUTCOMES = os.path.join(ROOT, 'paper', 'outcomes')


def compare(first, second):
    """first, second: the 'champions' of the two reports. -> {set: comparison}."""
    a = {(r['set'], r['label']): r for r in first}
    b = {(r['set'], r['label']): r for r in second}
    if set(a) != set(b):
        raise SystemExit('The two reports do not hold the same champions.')
    out = {}
    for name in dict.fromkeys(r['set'] for r in first):
        keys = [k for k in a if k[0] == name]
        if any(abs(a[k]['evolved'] - b[k]['evolved']) > 1e-12 or a[k]['voxels'] != b[k]['voxels'] for k in keys):
            raise SystemExit(f'{ts.set_title(name)}: the two reports do not hold the same robots.')
        x = np.array([a[k]['ratio'] for k in keys])
        y = np.array([b[k]['ratio'] for k in keys])
        gain = y - x
        out[name] = {'n': len(keys), 'ratio_first': list(ps.quartiles(x)), 'ratio_second': list(ps.quartiles(y)),
                     'better_under_the_second': int((gain > 0).sum()), 'worse_under_the_second': int((gain < 0).sum()),
                     'p': float(wilcoxon(gain).pvalue) if np.any(gain != 0) else 1.0,
                     'off_by_first': list(ps.quartiles(np.abs(x - 1.0))), 'off_by_second': list(ps.quartiles(np.abs(y - 1.0))),
                     'keep_less_than_half_first': int((x < 0.5).sum()), 'keep_less_than_half_second': int((y < 0.5).sum()),
                     'range_second': [float(y.min()), float(y.max())]}
    return out


def main():
    reports = []
    for name in ('transfer.json', 'transfer_floor2013.json'):
        path = os.path.join(OUTCOMES, name)
        if not os.path.isfile(path):
            raise SystemExit(f'{name} is not in paper/outcomes. Both reports of transfer_scores.py are needed.')
        with open(path, encoding='utf-8') as f:
            reports.append(json.load(f))
    first, second = reports
    if first.get('preset', ts.PRESET) != ts.PRESET or second.get('preset') != ts.FLOOR_PRESET:
        raise SystemExit('The two reports are not those of the two presets.')
    sets = compare(first['champions'], second['champions'])
    print(f"Transfer ratio per champion: --preset {ts.PRESET} (set on the floor) against --preset {ts.FLOOR_PRESET}")
    print(f"{'set':<30}  {'n':>3}  {'first preset':>18}  {'second preset':>18}  {'better':>6}  {'worse':>5}  {'p (Wilcoxon)':>12}  "
          f"{'off by, first':>18}  {'off by, second':>18}  {'under half':>10}")
    for name, s in sets.items():
        print(f"{ts.set_title(name):<30}  {s['n']:>3}  {ts.q(s['ratio_first']):>18}  {ts.q(s['ratio_second']):>18}  "
              f"{s['better_under_the_second']:>6}  {s['worse_under_the_second']:>5}  {s['p']:>12.2g}  "
              f"{ts.q(s['off_by_first']):>18}  {ts.q(s['off_by_second']):>18}  "
              f"{s['keep_less_than_half_first']:>4} / {s['keep_less_than_half_second']:<3}")
    total = sum(s['better_under_the_second'] for s in sets.values())
    print(f"All sets: {total} of {sum(s['n'] for s in sets.values())} champions keep more of their score under the second preset.")
    out = {'first': {'preset': ts.PRESET, 'made': first['made'], 'code': first['code']},
           'second': {'preset': ts.FLOOR_PRESET, 'made': second['made'], 'code': second['code']}, 'sets': sets}
    with open(os.path.join(OUTCOMES, 'transfer_presets.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print('Written to paper/outcomes/transfer_presets.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
