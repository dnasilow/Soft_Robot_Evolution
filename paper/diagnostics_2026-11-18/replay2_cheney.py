"""Second replay: do the settings found in the 2013 source and in every deposited robot file close
the gap?  Deviations of the cheney_score_s1 configuration from the 2013 files:
   amplitude        ours +-0.20          2013: (TempAmp 39 - TempBase 25) x CTE 0.01 = +-0.14
   Poisson law      ours volumetric ON   2013: PoissonKickBackEnabled = 0
   global damping   ours zeta 0.01       2013: SlowDampingZ = 0.001
Each is switched separately on his 35 no-cost run champions (10 cycles, his score, no early stop).
Read-only: the engine's module constant ZETA_GLOBAL is changed in this process only.
"""
import os, re, sys, glob, json, time, pickle
import numpy as np
from multiprocessing import Pool

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(OUT, '..', '..'))
sys.path.insert(0, ROOT)
os.chdir(OUT)
CH = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
REMAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
CHENEY = dict(direction='any', divide_by='workspace', workspace_voxels=10)
CYC = 0.25
A = 'A as run (0.20, poisson on, damp 0.01)'
B = 'B amp 0.14 only'
C = 'C amp 0.14 + poisson off'
D = 'D amp 0.14 + poisson off + damp 0.001'
E = 'E amp 0.14 + damp 0.001 (poisson on)'
F = 'F amp 0.20 + poisson off + damp 0.001'
# name: (amplitude, poisson, zeta_global)
CONFIGS = {A: (0.20, True, 0.01), B: (0.14, True, 0.01), C: (0.14, False, 0.01),
           D: (0.14, False, 0.001), E: (0.14, True, 0.001), F: (0.20, False, 0.001)}
CONDS = ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated')


def load_vxa(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    nx = int(re.search(r'<X_Voxels>(\d+)</X_Voxels>', s).group(1))
    ny = int(re.search(r'<Y_Voxels>(\d+)</Y_Voxels>', s).group(1))
    layers = re.findall(r'<Layer><!\[CDATA\[(.*?)\]\]></Layer>', s, re.S)
    g = np.zeros((nx, ny, len(layers)), np.int8)
    for z, lay in enumerate(layers):
        g[:, :, z] = np.array([REMAP[int(c)] for c in lay.strip()], np.int8).reshape(ny, nx).T
    return g, float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(path)).group(1))


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
    tag, cfg, g = a
    amp, poisson, zeta = CONFIGS[cfg]
    import src.physics.mujoco_beam_physics as bp
    bp.ZETA_GLOBAL = zeta                                  # this worker process only
    e = bp.MuJoCoBeamPhysics(actuation_amplitude=amp, actuation_frequency=40.0, fitness_mode='forward',
                             friction=SS, materials='cheney2013', floor_contact='voxelyze',
                             poisson=poisson, **CHENEY)
    e.load_robot(g)
    f = float(e.get_fitness(CYC, 0.0, early_term_threshold=-1e9))
    return tag, cfg, f, bool(e.diverged()), float(e.default_timestep)


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    best = pickle.load(open(os.path.join(ROOT, 'results', 'cheney_score_s1', 'best_robot.pkl'), 'rb'))
    g_ours = np.asarray(best['genome'])
    champs = {c: champions(c) for c in CONDS}
    jobs = []
    for cfg in CONFIGS:
        jobs.append(('OURS', cfg, g_ours))
        if cfg not in (A, B):                              # A and B were measured in the first replay
            for run, g, fit in champs[CONDS[0]]:
                jobs.append((CONDS[0] + '|' + run, cfg, g))
    for run, g, fit in champs[CONDS[1]]:
        jobs.append((CONDS[1] + '|' + run, D, g))
    print(f"{len(jobs)} evaluations queued", flush=True)
    res, t0 = {}, time.time()
    with Pool(24) as p:
        for k, (tag, cfg, f, div, dt) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            res[(tag, cfg)] = dict(fit=f, div=div, dt=dt)
            if k % 20 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)} done  ({time.time() - t0:.0f} s)", flush=True)
    print(f"\nall done in {time.time() - t0:.0f} s\n")

    first = json.load(open(os.path.join(OUT, 'replay_cheney_results.json')))
    his = np.array([fit for _, _, fit in champs[CONDS[0]]])
    prev = {A: np.array(first['sweep']['ours_by_amp']['0.2']),
            B: np.array(first['sweep']['ours_by_amp']['0.14'])}
    print(f"HIS 35 no-cost run champions (recorded median {np.median(his):.3f}) in our engine, 10 cycles:")
    print(f"{'configuration':<44}{'median':>8}{'ours/his':>10}{'95% CI':>14}{'max':>8}{'Spearman':>10}{'diverged':>10}{'our champ':>11}")
    rng = np.random.default_rng(0)
    dump = {'his': his.tolist(), 'runs': [r for r, _, _ in champs[CONDS[0]]], 'configs': {}}
    for cfg in CONFIGS:
        if cfg in prev:
            ours, div = prev[cfg], 0
        else:
            ours = np.array([res[(CONDS[0] + '|' + run, cfg)]['fit'] for run, _, _ in champs[CONDS[0]]])
            div = sum(res[(CONDS[0] + '|' + run, cfg)]['div'] for run, _, _ in champs[CONDS[0]])
        r = ours / his
        bs = [np.median(rng.choice(r, len(r))) for _ in range(10000)]
        ci = f"{np.percentile(bs, 2.5):.2f}-{np.percentile(bs, 97.5):.2f}"
        print(f"{cfg:<44}{np.median(ours):>8.3f}{np.median(r):>10.2f}{ci:>14}"
              f"{ours.max():>8.3f}{spearman(his, ours):>+10.2f}{div:>10}{res[('OURS', cfg)]['fit']:>11.3f}")
        dump['configs'][cfg] = dict(ours=ours.tolist(), our_champion=res[('OURS', cfg)]['fit'])
    hisc = np.array([fit for _, _, fit in champs[CONDS[1]]])
    oursc = np.array([res[(CONDS[1] + '|' + run, D)]['fit'] for run, _, _ in champs[CONDS[1]]])
    print(f"\nHIS 35 actuated-cost champions under configuration D: recorded median {np.median(hisc):.3f}, "
          f"ours median {np.median(oursc):.3f}, ours/his median {np.median(oursc / hisc):.2f}, "
          f"Spearman {spearman(hisc, oursc):+.2f}")
    dump['cost_D'] = dict(his=hisc.tolist(), ours=oursc.tolist())
    print("\nper-robot table for configuration D (no-cost):")
    oursD = np.array(dump['configs'][D]['ours'])
    for i in np.argsort(-his):
        print(f"  {dump['runs'][i]:<9} his {his[i]:.3f}   ours {oursD[i]:.3f}   ratio {oursD[i] / his[i]:.2f}")
    json.dump(dump, open(os.path.join(OUT, 'replay2_cheney_results.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
