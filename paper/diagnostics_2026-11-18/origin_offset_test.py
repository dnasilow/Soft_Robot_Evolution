"""Hypothesis test: in the 2013 code, FinalCOM_Dist = (GetCM() - IniCM).Length() and, in the one
simulator file that was deposited, IniCM is only ever set to (0,0,0). If the driver never set it to
the start position, the recorded 'distance' is the final COM's distance from the lattice ORIGIN,
so a robot that does not move still scores |start COM| / workspace width (~0.8).
Test with his own data: do his low-scoring robots sit exactly at their own |start COM| / W ?"""
import os, re, sys, glob, io
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
CH = (r'C:\Users\dnasilowski\AppData\Local\Temp\claude\c--SoftRobotEvolution'
      r'\5cc73d86-944b-40cc-9802-a2f3f18f9a8b\scratchpad\cheney')

def load(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    layers = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(layers)), np.int8)
    for z, lay in enumerate(layers):
        g[:, :, z] = np.array([int(c) for c in lay.strip()], np.int8).reshape(ny, nx).T
    b = os.path.basename(path)
    return g, float(re.search(r'origFit_([0-9.eE+-]+)_genome', b).group(1)), float(re.search(r'adjFit_([0-9.eE+-]+)--', b).group(1))

for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
    rows = []
    for f in glob.glob(os.path.join(CH, cond, 'run_*', 'Gen_1000', '*.vxa')):
        try:
            g, fit, adj = load(f)
        except Exception:
            continue
        idx = np.argwhere(g != 0)
        if len(idx) == 0:
            continue
        c0 = (idx + 0.5).mean(0) / 10.0                 # start COM in workspace widths, origin at the lattice corner
        drop = idx[:, 2].min() / 10.0                    # gap under the body if its lowest layer is not layer 0
        rows.append((fit, float(np.linalg.norm(c0)), float(np.linalg.norm(c0[:2])), c0, drop, len(idx)))
    rows.sort(key=lambda r: r[0])
    fit = np.array([r[0] for r in rows]); c0n = np.array([r[1] for r in rows])
    print(f"\n{'=' * 84}\n{cond}: {len(rows)} final-population robots\n{'=' * 84}")
    print(f"  start-COM distance from the lattice origin, |c0|/W: median {np.median(c0n):.3f}  range {c0n.min():.3f}-{c0n.max():.3f}")
    print(f"  recorded fitness: {np.sum(fit < 0.01)} robots below 0.01 (failed/invalid), "
          f"{np.sum((fit >= 0.01) & (fit < 0.5))} between 0.01 and 0.5, {np.sum((fit >= 0.5) & (fit < 1.2))} between 0.5 and 1.2")
    print("  the 25 lowest-scoring robots that scored at all (fitness >= 0.01):")
    print(f"  {'recorded fit':>13}{'|c0|/W':>9}{'fit - |c0|/W':>14}{'voxels':>8}{'gap under body (W)':>20}")
    low = [r for r in rows if r[0] >= 0.01][:25]
    for r in low:
        print(f"  {r[0]:>13.4f}{r[1]:>9.4f}{r[0] - r[1]:>14.4f}{r[5]:>8}{r[4]:>20.2f}")
    d = np.array([r[0] - r[1] for r in rows if r[0] >= 0.01])
    print(f"  fitness - |c0|/W over all scoring robots: min {d.min():+.3f}   (a value >= ~ -0.1 for EVERY robot means nobody ever scored below its own start offset)")
    print(f"  robots scoring at all but below 0.9 x their own |c0|/W: {int(np.sum([r[0] < 0.9 * r[1] for r in rows if r[0] >= 0.01]))} of {int(np.sum(fit >= 0.01))}")
