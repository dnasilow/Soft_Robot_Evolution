"""Produce the presence-field + body data for the artifact (JSON, quantised to keep it small)."""
import pickle, json, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import _build_coord_grid
from src.evolution.genome_config import VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX

coords, dims = _build_coord_grid()
N = dims[0]   # 18
d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
cppn, G = d['cppn'], d['genome']

# presence field over the interior grid
lg = cppn.evaluate_batch(coords)[:, 0].reshape(dims)      # (18,18,18)
lo, hi = VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX
body = (G[lo:hi, lo:hi, lo:hi] != 0).astype(int)          # (18,18,18)
mat  = G[lo:hi, lo:hi, lo:hi].astype(int)

n_body = int(body.sum())
waterline = float(np.sort(lg.ravel())[-n_body])           # threshold that yields exactly n_body

out = {
    'n': N,
    'n_body': n_body,
    'n_positions': int(lg.size),
    'gate_pass': int((lg > 0).sum()),
    'waterline': round(waterline, 4),
    'field_min': round(float(lg.min()), 4),
    'field_max': round(float(lg.max()), 4),
    # quantise field to 3 decimals, store as nested [z][y][x] lists for easy JS indexing
    'field': [[[round(float(lg[x, y, z]), 3) for x in range(N)] for y in range(N)] for z in range(N)],
    'body':  [[[int(body[x, y, z]) for x in range(N)] for y in range(N)] for z in range(N)],
    'mat':   [[[int(mat[x, y, z]) for x in range(N)] for y in range(N)] for z in range(N)],
}
p = r'C:\Users\DNASIL~1\AppData\Local\Temp\claude\C--SoftRobotEvolution\5cc73d86-944b-40cc-9802-a2f3f18f9a8b\scratchpad\field.json'
with open(p, 'w') as f:
    json.dump(out, f, separators=(',', ':'))
print(f"positions={out['n_positions']}  gate_pass={out['gate_pass']}  body={n_body}")
print(f"field range [{out['field_min']}, {out['field_max']}]  waterline={out['waterline']}")
print(f"wrote {p}  ({os.path.getsize(p)/1024:.0f} KB)")
