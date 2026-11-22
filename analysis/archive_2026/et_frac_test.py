"""Validate --early-term-frac (dev code): default unchanged, plumbing, check-point timing, guard."""
import os, sys, pickle
DEV = r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad/dev_friction'
sys.path.insert(0, DEV); os.chdir(DEV)

if __name__ == '__main__':
    import numpy as np
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
    arc = pickle.load(open(r'C:/SoftRobotEvolution/results/cheney_repro_s1/archive.pkl', 'rb'))['archive']
    g = min(arc.values(), key=lambda e: int((e['genome'] != 0).sum()))['genome']

    def eng():
        e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward'); e.load_robot(g); return e

    f0 = float(eng().get_fitness(simulation_time=2.5, settle_time=0.5))
    print(f"1. flags off (25 cycles): {f0:.6f} vs pre-change 0.728415 -> {'IDENTICAL' if f'{f0:.6f}' == '0.728415' else 'DIFFERENT'}")

    # 2. timing: force a stop (impossible 10 BL bar) and compare the partial score with the
    #    robot's actual progress after 2 and 5 cycles of a 10-cycle window.
    e = eng(); nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    for _ in range(int(0.5 / e.default_timestep)): e.step()
    ix = float(e.get_position()[0]); prog = {}
    for s in range(1, int(1.0 / e.default_timestep) + 1):
        e.step()
        if s in (400, 1000): prog[s] = (float(e.get_position()[0]) - ix) / bl
    p20 = float(eng().get_fitness(simulation_time=1.0, settle_time=0.5, early_term_threshold=10.0))
    p50 = float(eng().get_fitness(simulation_time=1.0, settle_time=0.5, early_term_threshold=10.0, early_term_fraction=0.5))
    print(f"2. forced stop at 20%: {p20:.6f} (progress after 2 cycles {prog[400]:.6f})  "
          f"at 50%: {p50:.6f} (progress after 5 cycles {prog[1000]:.6f}) -> "
          f"{'OK' if abs(p20-prog[400])<1e-9 and abs(p50-prog[1000])<1e-9 else 'MISMATCH'}")

    # 3. plumbing: direct == sequential == pool with the fraction set
    got = {}
    for nw in (1, 2):
        ev = MuJoCoTendonEvaluator(simulation_time=1.0, settle_time=0.5, actuation_amplitude=0.16, n_workers=nw,
                                   attach_controller=False, fitness_mode='forward',
                                   early_term_threshold=10.0, early_term_fraction=0.5)
        got[nw] = [float(x) for x in ev.evaluate_batch([g, g])]; ev.close()
    print(f"3. plumbing (frac 0.5): direct {p50:.6f} | sequential {got[1][0]:.6f} | pool {got[2]} -> "
          f"{'MATCH' if all(v == p50 for v in got[1] + got[2]) else 'MISMATCH'}")

    # 4. resume guard incl. checkpoints that predate the fraction setting
    import run_tendon_evolution as R
    SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
    e1_era = {'physics': {'friction': SS, 'early_term_threshold': 0.02, 'sim_time': 1.0, 'settle_time': 0.5}}
    new = lambda **kw: dict({'friction': SS, 'early_term_threshold': 0.02, 'early_term_fraction': None,
                             'sim_time': 1.0, 'settle_time': 0.5}, **kw)
    cases = [("E1-era checkpoint, no frac flag", e1_era, new(), True),
             ("E1-era checkpoint, --early-term-frac 0.5", e1_era, new(early_term_fraction=0.5), False),
             ("old checkpoint, default flags", {}, {'friction': None, 'early_term_threshold': None,
                                                   'early_term_fraction': None, 'sim_time': 2.5, 'settle_time': 0.5}, True),
             ("new checkpoint frac 0.5, frac forgotten", {'physics': new(early_term_fraction=0.5)}, new(), False),
             ("new checkpoint frac 0.5, same flags", {'physics': new(early_term_fraction=0.5)}, new(early_term_fraction=0.5), True)]
    print("4. resume guard:")
    for label, ck, phys, should in cases:
        try: R._check_resume_physics(ck, phys); ok = True
        except SystemExit: ok = False
        print(f"     {label:<42} {'resumes' if ok else 'REFUSES'} -> {'OK' if ok == should else 'WRONG'}")
