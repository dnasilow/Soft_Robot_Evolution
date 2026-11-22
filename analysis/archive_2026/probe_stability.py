"""Which combination makes the cheney_floor_s1 champion blow up? Reports MuJoCo's BADQACC
warning counter (MuJoCo silently resets the whole state when it fires), peak |qvel| and the
step actually used."""
import os, sys, pickle
import numpy as np
import mujoco
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics

g = pickle.load(open('results/cheney_floor_s1/best_robot.pkl', 'rb'))['genome']
print(f"body: {int((g != 0).sum())} voxels, bone {int((g == 4).sum())}")
for pois in (False, True):
    for rule in ('ours', 'voxelyze'):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                              poisson=pois, dt_rule=rule)
        e.load_robot(g)
        vmax = 0.0
        amax = 0.0
        nsteps = int(0.3 / e.default_timestep)
        for _ in range(nsteps):
            e.step()
            vmax = max(vmax, float(np.abs(e.data.qvel).max()))
            amax = max(amax, float(np.abs(e.data.qacc).max()))
        w = int(e.data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number)
        print(f"  poisson={str(pois):5s} rule={rule:9s} dt={e.default_timestep*1e6:7.2f} us  "
              f"steps={nsteps:5d}  BADQACC={w:3d}  peak|qvel|={vmax:10.2f}  peak|qacc|={amax:.3e}")
