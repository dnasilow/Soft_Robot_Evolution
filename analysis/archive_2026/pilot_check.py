"""Pilot check for cheney_score_pilot: which way does each robot go, how much of the score is
sag, and does the 0.02 W any-direction early stop still fire?"""
import os, sys, pickle, time
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}

def job(a):
    i, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze')
    e.load_robot(g)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    W = 10 * e.voxel_size
    c0 = np.array(e.get_position())
    n = int(0.25 / e.default_timestep); half = int(n * 0.5)
    t = time.time()
    for s in range(1, n + 1):
        e.step()
        if s == half:
            ch = np.array(e.get_position()) - c0
    d = np.array(e.get_position()) - c0
    return i, dict(half_any=np.linalg.norm(ch) / W, half_x=ch[0] / bl, half_z=ch[2] / W,
                   d=d / W, bl=bl, t=time.time() - t, div=e.diverged())

def main():
    pop = pickle.load(open('results/cheney_score_pilot/final_population.pkl', 'rb'))
    fits = pop['fitnesses']
    with Pool(30) as p:
        out = dict(p.map(job, list(enumerate(pop['genomes']))))
    r = [out[i] for i in range(len(fits))]
    ha = np.array([x['half_any'] for x in r]); hx = np.array([x['half_x'] for x in r])
    hz = np.array([x['half_z'] for x in r])
    print(f"early stop at cycle 5 (0.02): any-direction W would stop {int((ha < 0.02).sum())}/30, "
          f"+X BL would stop {int((hx < 0.02).sum())}/30")
    print(f"vertical COM change by cycle 5 (W): median {np.median(hz):+.3f}, range {hz.min():+.3f}..{hz.max():+.3f}")
    print(f"{'rank':>4}{'stored W':>9}{'dx':>8}{'dy':>8}{'dz':>8}{'+X BL':>8}{'heading':>9}{'L':>4}")
    for k, i in enumerate(np.argsort(fits)[::-1][:8], 1):
        x = r[i]; d = x['d']
        head = np.degrees(np.arctan2(d[1], d[0]))
        print(f"{k:>4}{fits[i]:>9.4f}{d[0]:>8.3f}{d[1]:>8.3f}{d[2]:>8.3f}{max(0, d[0] * 0.1 / x['bl']):>8.3f}"
              f"{head:>8.0f}°{round(x['bl'] / 0.01):>4}")
    print(f"heading of all 30 (deg): {sorted(int(np.degrees(np.arctan2(x['d'][1], x['d'][0]))) for x in r)}")

if __name__ == '__main__':
    main()
