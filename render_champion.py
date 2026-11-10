"""
Render an evolved champion to an animated GIF using MuJoCo's offscreen renderer.

Works with the current tendon-based genomes (the old pygame video_recorder.py is for
the retired spring-mass system). A tracking camera follows the robot so you can watch
it locomote. Open-loop actuation at amp 0.08 to match the evolution runs.

Usage:
    python render_champion.py results/directed_v1/best_robot.pkl
    python render_champion.py results/plateau_test_bone/best_robot.pkl --sim-time 4
"""
import argparse
import pickle

import numpy as np
import mujoco
from PIL import Image

from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics


def render(pkl_path, out_gif=None, sim_time=3.0, settle=0.5, amp=0.08,
           width=640, height=480, fps=25, friction=None, body='springs', poisson=True,
           dt_rule='voxelyze', materials='evosoro', floor_contact='mujoco', freq=10.0):
    with open(pkl_path, 'rb') as f:
        d = pickle.load(f)
    g = d['genome']
    vox = int((g != 0).sum())
    mats = {m: int((g == m).sum()) for m in (1, 2, 3, 4)}

    # A champion evolved on a non-default floor must be replayed on that floor.
    fkw = {} if friction is None else {'friction': friction}
    if body == 'beam':
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        eng = MuJoCoBeamPhysics(actuation_amplitude=amp, poisson=poisson, dt_rule=dt_rule,
                                materials=materials, floor_contact=floor_contact,
                                actuation_frequency=freq, **fkw)
    else:
        eng = MuJoCoTendonPhysics(actuation_amplitude=amp, **fkw)
    # If the champion carries evolved gait genes (--evolve-gait), apply them — otherwise
    # a single-material evolvable-gait body would render motionless under material actuation.
    _c = d.get('cppn')
    # Per-voxel-phase champions carry a control CPPN in .phase_cppn; hand that to the
    # engine (it detects it via evaluate_batch). Otherwise fall back to the 4-gene wave.
    _pc = getattr(_c, 'phase_cppn', None) if _c is not None else None
    if _pc is not None:
        gp = _pc
        print(f"  applying evolved per-voxel phase CPPN "
              f"({_pc.n_nodes} nodes, {_pc.n_connections} conns)")
    else:
        gp = _c.to_gait_params() if (_c is not None and hasattr(_c, 'to_gait_params')) else None
        if gp is not None:
            print(f"  applying evolved gait genes: {[round(x,3) for x in gp]}")
    eng.load_robot(g, gait_params=gp)
    model, data = eng.model, eng.data

    # Tracking free camera sized to the body.
    init = np.array(data.xpos[1:model.nbody])
    body_size = float((init.max(0) - init.min(0)).max()) + eng.voxel_size
    cam = mujoco.MjvCamera()
    cam.distance = max(0.18, body_size * 5.0)
    cam.elevation = -20.0
    cam.azimuth = 90.0

    renderer = mujoco.Renderer(model, height=height, width=width)
    dt = eng.default_timestep
    total_steps = int((settle + sim_time) / dt)
    render_every = max(1, int(1.0 / (fps * dt)))

    frames = []
    for s in range(total_steps):
        eng.step()
        if s % render_every == 0:
            com = np.mean(data.xpos[1:model.nbody], axis=0)
            cam.lookat[:] = com
            renderer.update_scene(data, cam)
            frames.append(Image.fromarray(renderer.render()))

    if out_gif is None:
        out_gif = pkl_path.rsplit('.', 1)[0].replace('best_robot', 'champion') + '.gif'
        if out_gif == pkl_path:
            out_gif = pkl_path + '.gif'

    frames[0].save(out_gif, save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, optimize=True)
    print(f"saved {out_gif}  ({len(frames)} frames, {width}x{height})")
    print(f"  fitness(saved)={d.get('fitness', float('nan')):.4f}  voxels={vox}  "
          f"mats act0={mats[1]} act180={mats[2]} soft={mats[3]} stiff={mats[4]}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Render an evolved champion to a GIF.")
    p.add_argument("pkl", help="path to a best_robot.pkl")
    p.add_argument("--out", default=None, help="output gif path (default: alongside the pkl)")
    p.add_argument("--sim-time", type=float, default=3.0)
    p.add_argument("--settle", type=float, default=0.5)
    p.add_argument("--amp", type=float, default=0.08)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--friction", type=float, default=None,
                   help="floor friction the run used (--friction)")
    p.add_argument("--friction-static", type=float, default=None,
                   help="stick-slip floor the run used (with --friction-kinetic)")
    p.add_argument("--friction-kinetic", type=float, default=None)
    p.add_argument("--poisson", default="on", choices=["on", "off"],
                   help="--body beam: Voxelyze volumetric coupling the run used")
    p.add_argument("--dt-rule", dest="dt_rule", default="voxelyze", choices=["voxelyze", "ours"],
                   help="--body beam: time-step rule the run used")
    p.add_argument("--materials", default="evosoro", choices=["evosoro", "cheney2013"],
                   help="--body beam: material stiffness preset the run used")
    p.add_argument("--floor-contact", dest="floor_contact", default="mujoco",
                   choices=["mujoco", "voxelyze"], help="--body beam: floor model the run used")
    p.add_argument("--freq", type=float, default=10.0, help="actuation frequency (Hz)")
    p.add_argument("--body", default="springs", choices=["springs", "beam"],
                   help="body physics the run used (--body)")
    p.add_argument("--slip-speed", type=float, default=0.02)
    p.add_argument("--stick-speed", type=float, default=0.01)
    a = p.parse_args()
    if (a.friction_static is None) != (a.friction_kinetic is None):
        raise SystemExit("ERROR: --friction-static and --friction-kinetic go together")
    fr = None
    if a.friction is not None:
        fr = {'mode': 'single', 'mu': a.friction}
    elif a.friction_static is not None:
        fr = {'mode': 'stickslip', 'mu_s': a.friction_static, 'mu_k': a.friction_kinetic,
              'v_on': a.slip_speed, 'v_off': a.stick_speed}
    render(a.pkl, a.out, a.sim_time, a.settle, a.amp, a.width, a.height, a.fps, friction=fr,
           body=a.body, poisson=a.poisson == 'on', dt_rule=a.dt_rule,
           materials=a.materials, floor_contact=a.floor_contact, freq=a.freq)
