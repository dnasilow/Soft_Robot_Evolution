"""Replay Cheney 2013's OWN generation-1000 robots with their muscles ON in the beam engine.

Question: "is the simulation wrong?"  His robots carry their recorded fitness in the file name
(origFit_...). If our engine gives them about the same score, the physics reproduces his and the
remaining gap (our best 2.72 vs his median 4.39) is the SEARCH. If our engine gives them much
less, the physics / actuation still differs from his.

Physics and score = exactly cheney_score_s1 (cheney2013 materials, Voxelyze floor, stick-slip
1.0/0.5, 40 Hz, 10 cycles from initialisation, |dCOM| in 3D / fixed 10-voxel workspace width).
Read-only: nothing in the project is modified (cwd is this scratch folder, so MuJoCo's log lands here).
"""
import os, re, sys, glob, json, time, pickle
import numpy as np
from multiprocessing import Pool

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(OUT, '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(OUT)
CH = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
REMAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}       # his palette -> ours (as in cheney_morphology.py)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
CHENEY = dict(direction='any', divide_by='workspace', workspace_voxels=10)
CYC = 0.25                                           # 10 cycles at 40 Hz
AMPS = (0.063, 0.10, 0.14, 0.20, 0.28, 0.39)
CONDS = ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated')


def load_vxa(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    layers = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(layers)), np.int8)
    for z, lay in enumerate(layers):
        g[:, :, z] = np.array([REMAP[int(c)] for c in lay.strip()], np.int8).reshape(ny, nx).T
    fit = float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(path)).group(1))
    return g, fit


def champions(cond):
    out = []
    for r in sorted(glob.glob(os.path.join(CH, cond, 'run_*'))):
        best, bf = None, -1.0
        for f in glob.glob(os.path.join(r, 'Gen_1000', '*.vxa')):
            try:
                g, fit = load_vxa(f)
            except Exception:
                continue
            if (g != 0).sum() and fit > bf:
                best, bf = g, fit
        if best is not None:
            out.append((os.path.basename(r), best, bf))
    return out


def job(a):
    tag, g, amp, et_off = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    t0 = time.time()
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze', **CHENEY)
    e.load_robot(g)
    kw = (dict(early_term_threshold=-1e9) if et_off
          else dict(early_term_threshold=0.02, early_term_fraction=0.5))
    f = float(e.get_fitness(CYC, 0.0, **kw))
    return tag, amp, f, bool(e.diverged()), float(e.default_timestep), time.time() - t0


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    best = pickle.load(open(os.path.join(ROOT, 'results', 'cheney_score_s1', 'best_robot.pkl'), 'rb'))
    g_ours = np.asarray(best['genome'])
    champs = {c: champions(c) for c in CONDS}
    for c in CONDS:
        print(f"{c}: {len(champs[c])} run champions loaded", flush=True)

    jobs = [('OURS|as-run', g_ours, 0.20, False), ('OURS|et-off', g_ours, 0.20, True)]
    for c in CONDS:
        for run, g, fit in champs[c]:
            jobs.append((f'{c}|{run}', g, 0.20, True))
    for run, g, fit in champs[CONDS[0]]:
        for amp in AMPS:
            if amp != 0.20:
                jobs.append((f'{CONDS[0]}|{run}', g, amp, True))
    print(f"{len(jobs)} evaluations queued", flush=True)

    res, t0 = {}, time.time()
    with Pool(24) as p:
        for k, (tag, amp, f, div, dt, secs) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            res[(tag, amp)] = dict(fit=f, div=div, dt=dt, secs=secs)
            if k % 20 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)} done  ({time.time() - t0:.0f} s)", flush=True)

    print(f"\nall done in {time.time() - t0:.0f} s\n")
    print(f"SANITY  our champion, stored {best['fitness']:.4f} W:  as-run {res[('OURS|as-run', 0.2)]['fit']:.4f}"
          f"   early-termination off {res[('OURS|et-off', 0.2)]['fit']:.4f}\n")

    dump = {'ours': {k[0]: v for k, v in res.items() if k[0].startswith('OURS')}, 'conds': {}}
    for c in CONDS:
        rows = []
        for run, g, fit in champs[c]:
            r = res[(f'{c}|{run}', 0.20)]
            rows.append(dict(run=run, vox=int((g != 0).sum()), his=fit, ours=r['fit'], div=r['div'],
                             dt=r['dt'], secs=r['secs']))
        his = np.array([r['his'] for r in rows]); ours = np.array([r['ours'] for r in rows])
        print(f"{'=' * 78}\n{c}  - his run champions in OUR engine, amplitude 0.20, 10 cycles\n{'=' * 78}")
        print(f"{'run':<10}{'vox':>5}{'HIS score':>11}{'OURS':>9}{'ours/his':>10}{'diverged':>10}")
        for r in sorted(rows, key=lambda q: -q['his']):
            print(f"{r['run']:<10}{r['vox']:>5}{r['his']:>11.3f}{r['ours']:>9.3f}"
                  f"{r['ours'] / max(r['his'], 1e-9):>10.2f}{str(r['div']):>10}")
        print(f"\n  HIS  median {np.median(his):.3f}  mean {his.mean():.3f}  range {his.min():.3f}-{his.max():.3f}")
        print(f"  OURS median {np.median(ours):.3f}  mean {ours.mean():.3f}  range {ours.min():.3f}-{ours.max():.3f}")
        print(f"  ratio ours/his: median {np.median(ours / his):.2f}   best body in our engine {ours.max():.3f}")
        print(f"  rank agreement (Spearman) {spearman(his, ours):+.2f}   moving (>0.02 W) {int((ours > 0.02).sum())}/{len(rows)}"
              f"   diverged {sum(r['div'] for r in rows)}/{len(rows)}\n")
        dump['conds'][c] = rows

    c = CONDS[0]
    print(f"{'=' * 78}\nAMPLITUDE SWEEP on his {len(champs[c])} no-cost champions (which amplitude reproduces HIS scores?)\n{'=' * 78}")
    print(f"{'amp':>6}{'median ours':>13}{'median ours/his':>17}{'max ours':>10}{'Spearman':>10}{'moving':>8}{'diverged':>10}")
    his = np.array([fit for _, _, fit in champs[c]])
    sweep = {}
    for amp in AMPS:
        ours = np.array([res[(f'{c}|{run}', amp)]['fit'] for run, _, _ in champs[c]])
        div = sum(res[(f'{c}|{run}', amp)]['div'] for run, _, _ in champs[c])
        print(f"{amp:>6.3f}{np.median(ours):>13.3f}{np.median(ours / his):>17.2f}{ours.max():>10.3f}"
              f"{spearman(his, ours):>+10.2f}{int((ours > 0.02).sum()):>8}{div:>10}")
        sweep[str(amp)] = ours.tolist()
    dump['sweep'] = dict(his=his.tolist(), ours_by_amp=sweep, runs=[r for r, _, _ in champs[c]])
    json.dump(dump, open(os.path.join(OUT, 'replay_cheney_results.json'), 'w'), indent=1)
    print(f"\nsaved {os.path.join(OUT, 'replay_cheney_results.json')}")


if __name__ == '__main__':
    main()
