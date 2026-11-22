"""Read (in memory, nothing extracted to disk) the 2013 source tarball and print the lines that
decide: actuation amplitude, start-position bookkeeping, Poisson option, damping, floor."""
import sys, io, tarfile, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t = tarfile.open(sys.argv[1], 'r:gz')
names = [m.name for m in t if m.isfile()]
src = [n for n in names if re.search(r'\.(cpp|h|hpp|c|cc)$', n)]
print(f"{len(names)} files, {len(src)} C/C++ sources")
vox = [n for n in src if 'Voxelyze' in n or 'Voxel_Sim' in n]
print("Voxelyze-side sources:", len(vox))
for n in sorted(vox)[:60]:
    print("   ", n)
pats = [r'IniCM', r'TempAmp', r'TempBase', r'CurTemp\s*=', r'TempPeriod', r'PoissonKickBack', r'SlowDampingZ|GlobalDamp|SlowDampZ',
        r'uStatic|uDynamic|StaticFric|DynamicFric', r'FloorEnabled|FloorSlope', r'FinalCOM']
for n in sorted(vox):
    try:
        txt = t.extractfile(n).read().decode('utf-8', 'replace')
    except Exception:
        continue
    hits = []
    for i, line in enumerate(txt.splitlines(), 1):
        if any(re.search(p, line) for p in pats[:6]) and not line.strip().startswith('//'):
            hits.append((i, line.strip()[:170]))
    if hits:
        print(f"\n--- {n} ({len(hits)} matching lines; first 40)")
        for i, l in hits[:40]:
            print(f"  {i:>5}: {l}")
