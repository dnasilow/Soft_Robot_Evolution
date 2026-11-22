"""Re-check the 2026-09-14 friction sweep, which scaled geom_friction of EVERY geom (floor AND the
~7,000 load-bearing voxel-voxel contacts). Here only the FLOOR changes (explicit pairs), same
protocol as then: s2 champion, forward, 2.5 s after 0.5 s settle.
Earlier all-contact results: mu 0.175 -> 1.938 (47%), 1.05 -> 0.280 (7%), 1.4 -> 0.000 (0%)."""
import sys, pickle
from multiprocessing import Pool
DEV = r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad/dev_friction'
EARLIER = {0.175: 1.9383, 1.05: 0.2800, 1.4: 0.0}


def job(mu):
    sys.path.insert(0, DEV)
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    g = pickle.load(open(r'C:/SoftRobotEvolution/results/cheney_repro_s2/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward', friction={'mode': 'single', 'mu': mu})
    e.load_robot(g)
    return mu, float(e.get_fitness(simulation_time=2.5, settle_time=0.5))


if __name__ == '__main__':
    with Pool(3) as p:
        res = dict(p.map(job, sorted(EARLIER)))
    print("s2 champion, 25 cycles (baseline 4.0823 on the original 0.7 floor)")
    print(f"  {'mu':>6} {'floor + internal (09-14)':>26} {'floor only (now)':>18}")
    for mu in sorted(EARLIER):
        print(f"  {mu:>6} {EARLIER[mu]:>18.4f} ({100*EARLIER[mu]/4.0823:3.0f}%) {res[mu]:>11.4f} ({100*res[mu]/4.0823:3.0f}%)")
