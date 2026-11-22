"""Are the pvp_s1 archive fitnesses reproducible? Re-evaluate the archive's top entries
with the SAME settings evolution used (sim 2.5 / settle 0.5), engine-direct.
Also diagnose the best_robot.pkl vs archive mismatch."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

def reeval(g, gait, n=2):
    outs = []
    for _ in range(n):
        eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)   # eval default amp
        eng.load_robot(g, gait_params=gait)
        outs.append(float(eng.get_fitness(simulation_time=2.5, settle_time=0.5)))
    return outs

for name in ['egfix_s1', 'pvp_s1']:
    print(f"\n===== {name} =====")
    arc = pickle.load(open(f'results/{name}/archive.pkl','rb'))['archive']
    rows = sorted(arc.values(), key=lambda e:-e['fitness'])
    br = pickle.load(open(f'results/{name}/best_robot.pkl','rb'))
    print(f"best_robot.pkl stored fitness = {br.get('fitness'):.4f}")
    # does best_robot's genome match the archive's #1?
    same_as_top = bool((br['genome']==rows[0]['genome']).all())
    print(f"best_robot genome == archive #1 genome? {same_as_top}")
    print(f"archive top-5 stored fitness: {[round(e['fitness'],4) for e in rows[:5]]}")
    # re-evaluate the archive's top 5, twice each, to test reproducibility + determinism
    for i, e in enumerate(rows[:5]):
        c = e.get('cppn')
        gait = getattr(c,'phase_cppn',None)
        if gait is None:
            gait = c.to_gait_params() if (c is not None and hasattr(c,'to_gait_params')) else None
        r = reeval(e['genome'], gait, n=2)
        tag = 'phaseCPPN' if hasattr(gait,'evaluate_batch') else ('wave' if gait else 'material')
        print(f"  #{i+1} stored={e['fitness']:.4f}  re-eval={[round(x,4) for x in r]}  ctrl={tag}")
