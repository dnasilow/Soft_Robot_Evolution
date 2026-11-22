"""How does a body actually SIT? Done properly this time.

Previous attempt was unsound: 0.5 s of settling under 28x gravity, and a crude "z below 1.25r"
count instead of real contacts. Here:
  - muscles OFF, gravity only, sampled at 0.25 / 0.5 / 1.0 / 1.5 s so we can see whether it has
    actually come to rest (max speed reported);
  - contact taken from MuJoCo's own contact list on the floor pairs, not a height threshold;
  - footprint = distinct (x, y) grid columns touching the floor, the same thing the scorecard
    counts, so it is comparable to Cheney's median of 26;
  - and CHENEY'S OWN robots are run through our engine as the control. If his bodies splat in our
    engine too, the engine is what differs; if they perch, it is our evolved shapes.
"""
import os, re, sys, glob, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
CH = os.path.join(os.environ['TEMP'], 'claude', 'C--SoftRobotEvolution',
                  '5cc73d86-944b-40cc-9802-a2f3f18f9a8b', 'scratchpad', 'cheney')
REMAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}
SAMPLES = (0.25, 0.5, 1.0, 1.5)


def load_vxa(p):
    s = open(p, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    lay = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(lay)), np.int8)
    for z, L in enumerate(lay):
        g[:, :, z] = np.array([REMAP[int(c)] for c in L.strip()], np.int8).reshape(ny, nx).T
    return g, float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(p)).group(1))


def job(a):
    import mujoco
    tag, (mat, fl), g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.0, fitness_mode='forward', materials=mat, floor_contact=fl)
    e.load_robot(g)
    nb = e.model.nbody
    cells = np.array(e.cells)
    p0 = np.array(e.data.xpos[1:nb])
    h0 = float(p0[:, 2].max() - p0[:, 2].min())
    gid = {int(k): i for i, k in enumerate(e._floor_geom)}
    out = []
    t = 0.0
    for target in SAMPLES:
        while t < target:
            e.step(); t += e.default_timestep
        p = np.array(e.data.xpos[1:nb])
        touch = set()
        for c in range(int(e.data.ncon)):
            con = e.data.contact[c]
            if con.dist > 0:
                continue
            for gm in (int(con.geom1), int(con.geom2)):
                if gm in gid:
                    touch.add(gid[gm])
        cols = {tuple(cells[v, :2]) for v in touch}
        out.append(dict(t=target,
                        h=float(p[:, 2].max() - p[:, 2].min()),
                        nvox=len(touch), ncol=len(cols),
                        vmax=float(np.abs(e.data.cvel[1:, 3:]).max()),
                        div=e.diverged()))
    return tag, (mat, fl), h0, len(e.cells), out


if __name__ == '__main__':
    bodies = {}
    arc = pickle.load(open('results/cheney_vox_s1/archive.pkl', 'rb'))['archive']
    for i, x in enumerate(sorted(arc.values(), key=lambda q: -q['fitness'])[:3], 1):
        bodies[f'ours vox_s1 #{i}'] = x['genome']
    bodies['ours beam_s1 ch'] = pickle.load(open('results/cheney_beam_s1/best_robot.pkl', 'rb'))['genome']
    runs = sorted(glob.glob(os.path.join(CH, '2013-01-16-10^3-noCost', 'run_*')))[:5]
    for r in runs:
        best, bf = None, -1
        for f in glob.glob(os.path.join(r, 'Gen_1000', '*.vxa')):
            try: gg, fit = load_vxa(f)
            except Exception: continue
            if (gg != 0).sum() and fit > bf: best, bf = gg, fit
        if best is not None:
            bodies[f'CHENEY {os.path.basename(r)}'] = best
    COMBOS = (('evosoro','mujoco'), ('evosoro','voxelyze'), ('cheney2013','voxelyze'))
    jobs = [(t, c, g) for t, g in bodies.items() for c in COMBOS]
    t0 = time.time()
    with Pool(6) as p:
        res = {(t, m): (h0, n, o) for t, m, h0, n, o in p.map(job, jobs)}
    print(f"done in {time.time()-t0:.0f}s   (muscles off, gravity only)\n")
    print(f"{'body':<17}{'materials/floor':<22}{'vox':>5} | " +
          " ".join(f"{s:>4.2f}s: cols/h%/v" for s in SAMPLES))
    for t in bodies:
        for m in COMBOS:
            h0, n, o = res[(t, m)]
            cells = " ".join(f"{d['ncol']:>4d}/{100*d['h']/h0:>4.0f}/{d['vmax']:>4.2f}" for d in o)
            print(f"{t:<17}{m[0]+"/"+m[1]:<22}{n:>5} | {cells}")
    print("\n  cols = distinct floor columns touching (Cheney's own champions: median 26)")
    print("  h%   = height as a percentage of the undeformed height (100 = not squashed)")
    print("  v    = fastest voxel (m/s); near 0 means it has come to rest")
    for m in COMBOS:
        ours = [res[(t, m)][2][-1]['ncol'] for t in bodies if t.startswith('ours')]
        his = [res[(t, m)][2][-1]['ncol'] for t in bodies if t.startswith('CHENEY')]
        print(f"\n  {m[0]+"/"+m[1]:<22} settled footprint: OUR bodies {np.median(ours):.0f} "
              f"(range {min(ours)}-{max(ours)})   HIS bodies {np.median(his):.0f} "
              f"(range {min(his)}-{max(his)})")
