"""Plumbing: do friction and early-termination settings reach the worker processes?
Scores the same robot via (a) the engine directly, (b) the evaluator sequentially, (c) the
evaluator's multiprocessing pool, for three configs; all three must agree exactly.
Then unit-tests the resume-physics guard."""
import os, sys, pickle
DEV = r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad/dev_friction'
sys.path.insert(0, DEV); os.chdir(DEV)

SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
CONFIGS = {'original floor': dict(friction=None, early_term_threshold=None),
           'stick-slip 1.0/0.5': dict(friction=SS, early_term_threshold=None),
           'early-term 10 BL (forces a stop)': dict(friction=None, early_term_threshold=10.0)}

if __name__ == '__main__':
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
    arc = pickle.load(open(r'C:/SoftRobotEvolution/results/cheney_repro_s1/archive.pkl', 'rb'))['archive']
    g = min(arc.values(), key=lambda e: int((e['genome'] != 0).sum()))['genome']
    print(f"robot: {int((g != 0).sum())} voxels\n")
    ok_all = True
    for name, cfg in CONFIGS.items():
        e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward',
                                **({} if cfg['friction'] is None else {'friction': cfg['friction']}))
        e.load_robot(g)
        kw = {} if cfg['early_term_threshold'] is None else {'early_term_threshold': cfg['early_term_threshold']}
        direct = float(e.get_fitness(simulation_time=1.0, settle_time=0.5, **kw))
        got = {}
        for nw in (1, 2):
            ev = MuJoCoTendonEvaluator(simulation_time=1.0, settle_time=0.5, actuation_amplitude=0.16,
                                       n_workers=nw, attach_controller=False, fitness_mode='forward', **cfg)
            got[nw] = [float(x) for x in ev.evaluate_batch([g, g])]
            ev.close()
        ok = all(v == direct for v in got[1] + got[2])
        ok_all &= ok
        print(f"  {name:<34} direct {direct:.6f} | sequential {got[1][0]:.6f} | pool {got[2][0]:.6f},{got[2][1]:.6f}"
              f"  -> {'MATCH' if ok else 'MISMATCH'}")
    print(f"\nplumbing: {'ALL MATCH' if ok_all else 'FAILURE'}")

    print("\nresume guard unit tests:")
    import run_tendon_evolution as R
    phys_new = {'friction': SS, 'early_term_threshold': 0.02, 'sim_time': 1.0, 'settle_time': 0.5}
    phys_def = {'friction': None, 'early_term_threshold': None, 'sim_time': 2.5, 'settle_time': 0.5}
    cases = [("old checkpoint (no record), default flags", {}, phys_def, True),
             ("old checkpoint (no record), friction flags", {}, phys_new, False),
             ("new checkpoint, same flags", {'physics': phys_new}, phys_new, True),
             ("new checkpoint, friction flags forgotten", {'physics': phys_new},
              dict(phys_new, friction=None, early_term_threshold=None), False),
             ("new checkpoint, --sim-time forgotten", {'physics': phys_new}, dict(phys_new, sim_time=2.5), False)]
    for label, ck, phys, should_pass in cases:
        try:
            R._check_resume_physics(ck, phys); passed = True
        except SystemExit:
            passed = False
        print(f"  {label:<45} {'resumes' if passed else 'REFUSES'}  -> {'OK' if passed == should_pass else 'WRONG'}")
