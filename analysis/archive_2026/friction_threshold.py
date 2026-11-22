"""Where between mu 0.7 (works) and 1.4 (fails) does the sliding-sole gait break?

If the current winners still do ~4 BL at mu 0.9, evolving at 0.9 applies no pressure against
sliding soles and would likely just reproduce blocks. Robots: s2 champion (bimorph, 4.08) and s1
champion (single-phase + soft, 3.54). Sliding friction of every geom scaled so contact mu = target.
"""
import os, sys, time, pickle
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
ROBOTS = {'s2 champ': 'results/cheney_repro_s2/best_robot.pkl',
          's1 champ': 'results/cheney_repro_s1/best_robot.pkl'}
MUS = (0.9, 1.05, 1.2)


def job(args):
    tag, mu = args
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    g = pickle.load(open(ROBOTS[tag], 'rb'))['genome']
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward')
    e.load_robot(g)
    e.model.geom_friction[:, 0] *= mu / 0.7          # scene default: contact mu = max(0.7, 0.6) = 0.7
    t0 = time.time()
    return tag, mu, float(e.get_fitness(simulation_time=2.5, settle_time=0.5)), time.time() - t0


if __name__ == '__main__':
    t0 = time.time()
    with Pool(len(ROBOTS) * len(MUS)) as p:
        res = p.map(job, [(t, m) for t in ROBOTS for m in MUS])
    print(f'done in {time.time()-t0:.0f}s\n')
    known = {'s2 champ': {0.175: 1.9383, 0.35: 4.1064, 0.7: 4.0823, 1.4: 0.0},
             's1 champ': {0.7: 3.5443}}
    for tag in ROBOTS:
        row = dict(known[tag]); row.update({m: f for t, m, f, _ in res if t == tag})
        base = row[0.7]
        print(f'{tag}:  ' + '   '.join(f'mu {m:<5} {row[m]:.3f} ({100*row[m]/base:.0f}%)' for m in sorted(row)))
