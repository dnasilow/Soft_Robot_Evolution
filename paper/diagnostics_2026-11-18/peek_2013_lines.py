import sys, io, tarfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t = tarfile.open(sys.argv[1], "r:gz")
name, a, b = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
txt = t.extractfile(name).read().decode("utf-8", "replace").splitlines()
for i in range(a - 1, min(b, len(txt))):
    print(f"{i + 1:>5}: {txt[i].rstrip()[:185]}")
