"""Cheney 2013's deposited learning curves: champion fitness by generation, per run (read in memory,
nothing is extracted to disk)."""
import sys, io, tarfile, json, os
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
tgz = sys.argv[1]
want = ('2013-01-16-10^3-noCost/', '2013-01-16-10^3-costNumActuated/')
GENS = (1, 10, 30, 100, 200, 300, 600, 1000)
curves = {w: [] for w in want}
with tarfile.open(tgz, 'r:gz') as t:
    for m in t:
        if not m.isfile():
            continue
        for w in want:
            if w in m.name and m.name.endswith('.txt'):
                rows = []
                for line in t.extractfile(m).read().decode('utf-8', 'replace').splitlines():
                    p = line.split()
                    try:
                        v = [float(x) for x in p[:2]]
                        if len(v) == 2: rows.append(v)
                    except ValueError:
                        continue
                if rows:
                    curves[w].append((m.name, np.array(rows)))
out = {}
for w in want:
    cs = curves[w]
    print(f"\n{w}  ({len(cs)} runs; columns = gen, champion original fitness, champion adjusted, mean original, mean adjusted)")
    if not cs:
        continue
    print("  first rows of one file:", cs[0][1][:2].tolist())
    print(f"  {'gen':>6}{'median champ':>14}{'q25':>8}{'q75':>8}{'min':>8}{'max':>8}{'% of final median':>20}")
    fin = np.median([c[-1, 1] for _, c in cs])
    med = {}
    for g in GENS:
        v = []
        for _, c in cs:
            i = np.searchsorted(c[:, 0], g)
            i = min(i, len(c) - 1)
            v.append(c[:i + 1, 1].max())          # best original fitness seen up to generation g
        v = np.array(v)
        med[g] = float(np.median(v))
        print(f"  {g:>6}{np.median(v):>14.3f}{np.percentile(v, 25):>8.3f}{np.percentile(v, 75):>8.3f}{v.min():>8.3f}{v.max():>8.3f}{100 * np.median(v) / fin:>19.0f}%")
    out[w] = med
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cheney_curves.json'), 'w'), indent=1)
