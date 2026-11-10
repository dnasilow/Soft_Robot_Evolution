"""
Interactive 3-D viewer for evolved robots — rotate, zoom and pan with the mouse while the robot
walks.

    python view_robot.py results/cheney_vox_s1                 # top 3 of a run, best first
    python view_robot.py results/cheney_vox_s1 --rank 2        # just the 2nd best
    python view_robot.py results/cheney_vox_s1/best_robot.pkl  # a specific saved robot
    python view_robot.py results/cheney_vox_s1 --live          # watch it actually compute

Two modes:

  playback (default)  Simulates once up front, keeps every frame, then plays the motion back on a
                      loop at true speed. Smooth, and you can scrub and slow it down. The wait is
                      roughly 30 s of computing per second of motion.
  --live              Steps the physics inside the viewer. You see the real computation, but it
                      runs about 30x slower than real time because one evaluation is ~47,000 steps.

Keys (click the 3-D view first so it has focus):
    SPACE   pause / resume
    R       restart from the beginning
    [  ]    slower / faster  (playback only)
    ,  .    step one frame back / forward while paused (playback only)
    N       next robot
Mouse: drag = rotate, right-drag = pan, wheel = zoom. Close the window to quit.
"""
import argparse
import os
import pickle
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SPEEDS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0]


def build_engine(args):
    """The same engine the run used, so what you watch is what was scored."""
    fr = None
    if args.friction is not None:
        fr = {'mode': 'single', 'mu': args.friction}
    elif args.friction_static is not None or args.friction_kinetic is not None:
        fr = {'mode': 'stickslip',
              'mu_s': args.friction_static if args.friction_static is not None else 1.0,
              'mu_k': args.friction_kinetic if args.friction_kinetic is not None else 0.5,
              'v_on': args.slip_speed, 'v_off': args.stick_speed}
    if args.body == 'beam':
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        return MuJoCoBeamPhysics(actuation_amplitude=args.amp, actuation_frequency=args.freq,
                                 fitness_mode='forward', friction=fr,
                                 poisson=args.poisson == 'on', dt_rule=args.dt_rule,
                                 materials=args.materials,
                                 floor_contact=args.floor_contact)
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    return MuJoCoTendonPhysics(actuation_amplitude=args.amp, actuation_frequency=args.freq,
                               fitness_mode='forward', friction=fr)


def load_robots(target, rank, count):
    """Return [(label, genome)] from a run directory (best first) or a single .pkl."""
    p = Path(target)
    if p.is_file():
        d = pickle.load(open(p, 'rb'))
        return [(p.stem, d['genome'])]
    for name in ('archive.pkl', 'checkpoint.pkl'):
        f = p / name
        if f.exists():
            arc = pickle.load(open(f, 'rb'))['archive']
            ranked = sorted(arc.values(), key=lambda e: -e['fitness'])
            if rank:
                ranked = ranked[rank - 1:rank]
            else:
                ranked = ranked[:count]
            return [(f"{p.name}  #{i + 1}  fitness {e['fitness']:.4f}", e['genome'])
                    for i, e in enumerate(ranked, start=(rank - 1) if rank else 0)]
    f = p / 'best_robot.pkl'
    if f.exists():
        return [(p.name, pickle.load(open(f, 'rb'))['genome'])]
    raise SystemExit(f"ERROR: no archive.pkl, checkpoint.pkl or best_robot.pkl in {p}")


def record(engine, seconds, fps):
    """Simulate once, keeping one qpos snapshot per displayed frame."""
    every = max(1, int(round(1.0 / (fps * engine.default_timestep))))
    n = int(seconds / engine.default_timestep)
    frames = [engine.data.qpos.copy()]
    t0 = time.time()
    for k in range(n):
        engine.step()
        if (k + 1) % every == 0:
            frames.append(engine.data.qpos.copy())
        if k % 5000 == 0 and k:
            done = k / n
            left = (time.time() - t0) * (1 - done) / max(done, 1e-9)
            print(f"\r  simulating {done*100:5.1f}%   ~{left:4.0f}s left", end='', flush=True)
    print(f"\r  simulated {seconds:.1f}s of motion in {time.time()-t0:.0f}s"
          f"   ({len(frames)} frames){' ' * 20}")
    return frames, every * engine.default_timestep


class Keys:
    """Viewer key state. GLFW gives us uppercase ASCII codes."""

    def __init__(self):
        self.paused = False
        self.restart = False
        self.next = False
        self.speed = SPEEDS.index(1.0)
        self.nudge = 0

    def __call__(self, code):
        c = chr(code) if 0 < code < 0x110000 else ''
        if code == 32:
            self.paused = not self.paused
        elif c == 'R':
            self.restart = True
        elif c == 'N':
            self.next = True
        elif c == '[':
            self.speed = max(0, self.speed - 1)
            print(f"  speed {SPEEDS[self.speed]}x")
        elif c == ']':
            self.speed = min(len(SPEEDS) - 1, self.speed + 1)
            print(f"  speed {SPEEDS[self.speed]}x")
        elif c == ',':
            self.nudge = -1
        elif c == '.':
            self.nudge = +1


def frame_camera(viewer, data, nbody, voxel_size):
    p = np.array(data.xpos[1:nbody])
    size = float((p.max(0) - p.min(0)).max()) + voxel_size
    viewer.cam.lookat[:] = p.mean(0)
    viewer.cam.distance = max(0.2, size * 4.0)
    viewer.cam.azimuth = 135
    viewer.cam.elevation = -15


def show(label, genome, args):
    print(f"\n=== {label} ===")
    eng = build_engine(args)
    eng.load_robot(genome)
    g = np.asarray(genome)
    print(f"  {int((g != 0).sum())} voxels   materials m1/m2/soft/bone = "
          f"{[int((g == k).sum()) for k in (1, 2, 3, 4)]}   time step "
          f"{eng.default_timestep*1e6:.2f} us")
    nbody = eng.model.nbody
    keys = Keys()

    if args.live:
        with mujoco.viewer.launch_passive(eng.model, eng.data, key_callback=keys) as v:
            frame_camera(v, eng.data, nbody, eng.voxel_size)
            per_sync = max(1, int(0.02 / eng.default_timestep))
            while v.is_running() and not keys.next:
                if keys.restart:
                    # reset in place: load_robot would build a NEW model/data and the viewer
                    # still holds the old ones
                    mujoco.mj_resetData(eng.model, eng.data)
                    eng.current_time = 0.0
                    mujoco.mj_forward(eng.model, eng.data)
                    keys.restart = False
                if not keys.paused:
                    for _ in range(per_sync):
                        eng.step()
                v.sync()
            if hasattr(eng, 'diverged') and eng.diverged():
                print("  NOTE: this robot blew up (it crushes itself) - it would score 0")
        return keys.next

    frames, frame_dt = record(eng, args.sim_time, args.fps)
    with mujoco.viewer.launch_passive(eng.model, eng.data, key_callback=keys) as v:
        frame_camera(v, eng.data, nbody, eng.voxel_size)
        i = 0
        nxt = time.time()
        while v.is_running() and not keys.next:
            if keys.restart:
                i, keys.restart = 0, False
            if keys.nudge and keys.paused:
                i = (i + keys.nudge) % len(frames)
                keys.nudge = 0
                eng.data.qpos[:] = frames[i]
                mujoco.mj_forward(eng.model, eng.data)
                v.sync()
            now = time.time()
            if not keys.paused and now >= nxt:
                eng.data.qpos[:] = frames[i]
                mujoco.mj_forward(eng.model, eng.data)
                v.sync()
                i = (i + 1) % len(frames)
                nxt = now + frame_dt / SPEEDS[keys.speed]
            else:
                time.sleep(0.002)
    return keys.next


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('target', help='a run directory (results/cheney_vox_s1) or a .pkl')
    p.add_argument('--rank', type=int, default=None, help='show only the Nth best (1 = champion)')
    p.add_argument('--count', type=int, default=3, help='how many of the best to offer (default 3)')
    p.add_argument('--live', action='store_true',
                   help='step the physics in the window (~30x slow motion) instead of playback')
    p.add_argument('--sim-time', type=float, default=3.0, help='seconds of motion to record')
    p.add_argument('--fps', type=float, default=50.0, help='playback frames per simulated second')
    p.add_argument('--amp', type=float, default=0.2)
    p.add_argument('--freq', type=float, default=10.0)
    p.add_argument('--materials', default='evosoro', choices=['evosoro', 'cheney2013'])
    p.add_argument('--floor-contact', dest='floor_contact', default='mujoco',
                   choices=['mujoco', 'voxelyze'])
    p.add_argument('--body', default='beam', choices=['springs', 'beam'])
    p.add_argument('--poisson', default='on', choices=['on', 'off'])
    p.add_argument('--dt-rule', dest='dt_rule', default='voxelyze', choices=['voxelyze', 'ours'])
    p.add_argument('--friction', type=float, default=None)
    p.add_argument('--friction-static', type=float, default=1.0)
    p.add_argument('--friction-kinetic', type=float, default=0.5)
    p.add_argument('--slip-speed', type=float, default=0.02)
    p.add_argument('--stick-speed', type=float, default=0.01)
    args = p.parse_args()

    robots = load_robots(args.target, args.rank, args.count)
    print("keys: SPACE pause | R restart | [ ] slower/faster | , . step a frame | N next robot\n"
          "mouse: drag rotate | right-drag pan | wheel zoom   (click the 3-D view first)")
    k = 0
    while 0 <= k < len(robots):
        label, genome = robots[k]
        went_next = show(label, genome, args)
        if not went_next:
            break
        k += 1
    print("done")


if __name__ == '__main__':
    main()
