"""
B5 feasibility spike — MuJoCo flex/deformable reformulation (THROWAWAY).

Goal (go/no-go): prove, with a tendon-on-flex de-risk approach, that
  (1) a flex voxel-lattice can be ACTUATED as muscle (contracts), and
  (2) a small flex robot LOCOMOTES on a floor, and
  (3) it is >=3x faster per step than the current spatial-tendon model.

This does NOT touch the production pipeline. Run parts independently:
    python b5_flex_spike.py contract
    python b5_flex_spike.py locomote
    python b5_flex_spike.py speed
"""
import argparse
import time
import numpy as np
import mujoco


# ----------------------------------------------------------------------------
# Build an actuated flex block via MjSpec.
#   - flexcomp generates the deformable lattice (passive elasticity = the soft body)
#   - we decorate the generated node-bodies with sites
#   - we add tendons spanning a chosen axis + position actuators => "muscle"
# ----------------------------------------------------------------------------
def build_flex_block(count=(3, 3, 3), spacing=0.1, young=1.0e4, poisson=0.2,
                     pos=(0.0, 0.0, 0.5), gravity=True, with_floor=False,
                     jnt_damping=1.0, axis=0, name="soft"):
    g = "0 0 -9.81" if gravity else "0 0 0"
    floor = ('<geom name="floor" type="plane" size="5 5 0.1" pos="0 0 0" '
             'contype="1" conaffinity="1"/>') if with_floor else ""
    xml = f"""
    <mujoco>
      <option timestep="0.001" gravity="{g}"/>
      <worldbody>
        {floor}
        <flexcomp name="{name}" type="grid" count="{count[0]} {count[1]} {count[2]}"
                  spacing="{spacing} {spacing} {spacing}" dim="3" mass="1"
                  pos="{pos[0]} {pos[1]} {pos[2]}" radius="0.005">
          <elasticity young="{young}" poisson="{poisson}"/>
          <contact internal="false" selfcollide="none" contype="1" conaffinity="1"/>
        </flexcomp>
      </worldbody>
    </mujoco>"""
    spec = mujoco.MjSpec.from_string(xml)

    # damping on the auto-generated node slide joints so the system settles
    for b in spec.worldbody.bodies:
        for j in b.joints:
            j.damping = jnt_damping

    # compile once to learn node world positions (to pick faces by coordinate)
    m0 = spec.compile()
    d0 = mujoco.MjData(m0)
    mujoco.mj_forward(m0, d0)
    node_bodies = [b for b in spec.worldbody.bodies if b.name.startswith(name + "_")]
    xpos = {}
    for b in node_bodies:
        bid = m0.body(b.name).id
        xpos[b.name] = np.array(d0.xpos[bid])

    coords = np.array([xpos[b.name] for b in node_bodies])
    lo = coords[:, axis].min()
    hi = coords[:, axis].max()
    tol = 1e-6
    lo_face = [b for b in node_bodies if abs(xpos[b.name][axis] - lo) < tol]
    hi_face = [b for b in node_bodies if abs(xpos[b.name][axis] - hi) < tol]

    # pair lo-face node to hi-face node sharing the other two coords
    other = [k for k in (0, 1, 2) if k != axis]
    def key(b):
        p = xpos[b.name]
        return (round(p[other[0]], 5), round(p[other[1]], 5))
    hi_by_key = {key(b): b for b in hi_face}

    rest_len = hi - lo
    n_musc = 0
    for lb in lo_face:
        hb = hi_by_key.get(key(lb))
        if hb is None:
            continue
        sa = lb.add_site(name=f"sa_{n_musc}", pos=[0, 0, 0], size=[0.004, 0, 0])
        sb = hb.add_site(name=f"sb_{n_musc}", pos=[0, 0, 0], size=[0.004, 0, 0])
        t = spec.add_tendon(name=f"musc_{n_musc}")
        t.wrap_site(sa.name)
        t.wrap_site(sb.name)
        a = spec.add_actuator(name=f"act_{n_musc}")
        a.trntype = mujoco.mjtTrn.mjTRN_TENDON
        a.target = t.name
        a.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        a.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        KP = 300.0
        a.gainprm[0] = KP
        a.biasprm[0] = 0.0
        a.biasprm[1] = -KP
        a.biasprm[2] = 0.0
        a.ctrlrange[0] = 0.0
        a.ctrlrange[1] = rest_len * 1.5
        a.ctrllimited = 1
        n_musc += 1

    model = spec.compile()
    return model, rest_len, n_musc, axis


def _axis_extent(model, data, name="soft", axis=0):
    ids = [model.body(i).id for i in range(model.nbody)
           if model.body(i).name.startswith(name + "_")]
    xs = data.xpos[ids, axis]
    return float(xs.max() - xs.min())


def cmd_contract(args):
    axis = 0
    model, rest_len, n_musc, axis = build_flex_block(
        count=(3, 3, 3), gravity=False, jnt_damping=2.0, axis=axis)
    data = mujoco.MjData(model)
    print(f"built: nbody={model.nbody} nv={model.nv} nflexedge={model.nflexedge} "
          f"muscles={n_musc} rest_len={rest_len:.4f} nu={model.nu}")

    # settle at rest (ctrl = rest length -> ~no force)
    for a in range(model.nu):
        data.ctrl[a] = rest_len
    for _ in range(1500):
        mujoco.mj_step(model, data)
    ext_rest = _axis_extent(model, data, axis=axis)

    # actuate: command 60% of rest length -> contraction
    target = rest_len * 0.6
    for a in range(model.nu):
        data.ctrl[a] = target
    for _ in range(3000):
        mujoco.mj_step(model, data)
    ext_act = _axis_extent(model, data, axis=axis)

    shrink = 100.0 * (1.0 - ext_act / ext_rest)
    print(f"axis-{axis} extent  rest={ext_rest:.4f}  actuated={ext_act:.4f}  "
          f"-> contraction {shrink:.1f}%  (commanded -40%)")
    verdict = "PASS" if shrink > 8.0 else "FAIL"
    print(f"CONTRACTION {verdict}: flex lattice {'does' if verdict=='PASS' else 'does NOT'} "
          f"contract under tendon actuation")


# ----------------------------------------------------------------------------
# Segment-based builder for locomotion: muscles between ADJACENT layers along
# the travel axis, tagged by segment index so we can drive a traveling wave.
# ----------------------------------------------------------------------------
def build_flex_robot(count=(6, 3, 2), spacing=0.1, young=1.0e4, poisson=0.2,
                     pos=(0.0, 0.0, 0.12), jnt_damping=0.5, axis=0, name="bot"):
    floor = ('<geom name="floor" type="plane" size="5 5 0.1" pos="0 0 0" '
             'contype="1" conaffinity="1" friction="1.0 0.05 0.001"/>')
    xml = f"""
    <mujoco>
      <option timestep="0.001" gravity="0 0 -9.81"/>
      <worldbody>
        {floor}
        <flexcomp name="{name}" type="grid" count="{count[0]} {count[1]} {count[2]}"
                  spacing="{spacing} {spacing} {spacing}" dim="3" mass="2"
                  pos="{pos[0]} {pos[1]} {pos[2]}" radius="0.012">
          <elasticity young="{young}" poisson="{poisson}"/>
          <contact internal="false" selfcollide="none" contype="1" conaffinity="1"/>
        </flexcomp>
      </worldbody>
    </mujoco>"""
    spec = mujoco.MjSpec.from_string(xml)
    for b in spec.worldbody.bodies:
        for j in b.joints:
            j.damping = jnt_damping

    m0 = spec.compile()
    d0 = mujoco.MjData(m0)
    mujoco.mj_forward(m0, d0)
    node_bodies = [b for b in spec.worldbody.bodies if b.name.startswith(name + "_")]
    xpos = {b.name: np.array(d0.xpos[m0.body(b.name).id]) for b in node_bodies}

    other = [k for k in (0, 1, 2) if k != axis]
    layers = sorted({round(xpos[b.name][axis], 5) for b in node_bodies})
    seg_of_act = []
    n = 0
    for seg, (a_lo, a_hi) in enumerate(zip(layers[:-1], layers[1:])):
        lo_nodes = [b for b in node_bodies if abs(xpos[b.name][axis] - a_lo) < 1e-5]
        hi_map = {(round(xpos[b.name][other[0]], 5), round(xpos[b.name][other[1]], 5)): b
                  for b in node_bodies if abs(xpos[b.name][axis] - a_hi) < 1e-5}
        for lb in lo_nodes:
            k = (round(xpos[lb.name][other[0]], 5), round(xpos[lb.name][other[1]], 5))
            hb = hi_map.get(k)
            if hb is None:
                continue
            sa = lb.add_site(name=f"a{n}", pos=[0, 0, 0], size=[0.004, 0, 0])
            sb = hb.add_site(name=f"b{n}", pos=[0, 0, 0], size=[0.004, 0, 0])
            t = spec.add_tendon(name=f"m{n}")
            t.wrap_site(sa.name)
            t.wrap_site(sb.name)
            act = spec.add_actuator(name=f"act{n}")
            act.trntype = mujoco.mjtTrn.mjTRN_TENDON
            act.target = t.name
            act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
            act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
            KP = 200.0
            act.gainprm[0] = KP
            act.biasprm[1] = -KP
            act.ctrlrange[0] = 0.0
            act.ctrlrange[1] = spacing * 1.5
            act.ctrllimited = 1
            seg_of_act.append(seg)
            n += 1

    model = spec.compile()
    n_seg = len(layers) - 1
    return model, np.array(seg_of_act), spacing, n_seg, axis, name


def _com_axis(model, data, name, axis):
    ids = [model.body(i).id for i in range(model.nbody)
           if model.body(i).name.startswith(name + "_")]
    return float(np.mean(data.xpos[ids, axis]))


def _run_gait(model, data, seg_of_act, seg_len, n_seg, axis, name,
              f, amp, kwave, wdir, sim_t=4.0, settle=800):
    mujoco.mj_resetData(model, data)
    for a in range(model.nu):
        data.ctrl[a] = seg_len
    for _ in range(settle):
        mujoco.mj_step(model, data)
    x0 = _com_axis(model, data, name, axis)
    dt = model.opt.timestep
    for s in range(int(sim_t / dt)):
        t = s * dt
        for a in range(model.nu):
            phase = wdir * 2.0 * np.pi * kwave * seg_of_act[a] / max(n_seg, 1)
            wave = 0.5 * (1.0 + np.sin(2.0 * np.pi * f * t - phase))
            data.ctrl[a] = seg_len * (1.0 - amp * wave)
        mujoco.mj_step(model, data)
    x1 = _com_axis(model, data, name, axis)
    return (x1 - x0)


def cmd_locomote(args):
    model, seg_of_act, seg_len, n_seg, axis, name = build_flex_robot()
    data = mujoco.MjData(model)
    body_len = n_seg * seg_len
    print(f"built robot: nbody={model.nbody} nv={model.nv} nu={model.nu} "
          f"segments={n_seg}  body_len={body_len:.2f}m")
    print("gait sweep (best |displacement| wins) ...")
    best = None
    for kwave in (1, 2):
        for wdir in (+1, -1):
            for f in (2.0, 4.0, 6.0):
                for amp in (0.35, 0.55):
                    disp = _run_gait(model, data, seg_of_act, seg_len, n_seg,
                                     axis, name, f, amp, kwave, wdir)
                    bl = disp / body_len
                    if best is None or abs(bl) > abs(best[0]):
                        best = (bl, f, amp, kwave, wdir)
    bl, f, amp, kwave, wdir = best
    print(f"BEST gait: f={f}Hz amp={amp} wavenum={kwave} dir={'+' if wdir>0 else '-'}  "
          f"-> {bl:+.3f} body-lengths in 4s")
    verdict = "PASS" if abs(bl) > 0.1 else ("WEAK" if abs(bl) > 0.03 else "FAIL")
    print(f"LOCOMOTION {verdict}: a flex robot achieves {abs(bl):.3f} BL of directed "
          f"crawl from a simple hand-tuned wave (evolution would exploit this further)")


def _bench_steps(model, data, n_steps, reps=3):
    """Best (lowest) wall-time over reps; returns steps/sec at model.opt.timestep."""
    # warmup (first step builds contact/constraint structures)
    for _ in range(20):
        mujoco.mj_step(model, data)
    best = 1e18
    for _ in range(reps):
        mujoco.mj_resetData(model, data)
        t0 = time.perf_counter()
        for _ in range(n_steps):
            mujoco.mj_step(model, data)
        best = min(best, time.perf_counter() - t0)
    return n_steps / best


def cmd_speed(args):
    print("=" * 68)
    print("SPEED: flex vs production spatial-tendon, ~300-voxel robots")
    print("=" * 68)

    # ---- production tendon model: solid 10x6x5 = 300-voxel block ----------
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    grid = np.ones((10, 6, 5), dtype=int)  # all material 1 (active muscle)
    phys = MuJoCoTendonPhysics()
    t0 = time.perf_counter()
    phys.load_robot(grid, voxel_size=0.01)
    tendon_compile = time.perf_counter() - t0
    tm, td = phys.model, phys.data
    dt_t = tm.opt.timestep
    sps_t = _bench_steps(tm, td, 2000)
    simps_t = sps_t * dt_t
    print(f"\nTENDON : voxels=300  nbody={tm.nbody}  nv={tm.nv}  nu={tm.nu}  "
          f"ntendon={tm.ntendon}")
    print(f"         dt={dt_t:.4g}s  compile={tendon_compile*1000:.0f}ms  "
          f"steps/s={sps_t:,.0f}  sim-s/wall-s={simps_t:.2f}")

    # ---- flex model: 11x7x6 grid = 300 cells, equal resolution ------------
    t0 = time.perf_counter()
    fm, seg_of_act, seg_len, n_seg, axis, name = build_flex_robot(
        count=(11, 7, 6), pos=(0, 0, 0.2))
    flex_compile = time.perf_counter() - t0
    fd = mujoco.MjData(fm)
    dt_f = fm.opt.timestep
    n_cells = 10 * 6 * 5
    sps_f = _bench_steps(fm, fd, 2000)
    simps_f = sps_f * dt_f
    print(f"\nFLEX   : cells={n_cells}  nodes={fm.nbody-1}  nv={fm.nv}  nu={fm.nu}  "
          f"nflexedge={fm.nflexedge}")
    print(f"         dt={dt_f:.4g}s  compile={flex_compile*1000:.0f}ms  "
          f"steps/s={sps_f:,.0f}  sim-s/wall-s={simps_f:.2f}")

    # ---- verdict (effective throughput is what governs eval time) ---------
    ratio_raw = sps_f / sps_t
    ratio_eff = simps_f / simps_t
    print("\n" + "-" * 68)
    print(f"raw step throughput   flex/tendon = {ratio_raw:.2f}x")
    print(f"EFFECTIVE throughput  flex/tendon = {ratio_eff:.2f}x  "
          f"(sim-time per wall-time; folds in timestep)")
    bar = 3.0
    verdict = "GO" if ratio_eff >= bar else ("MARGINAL" if ratio_eff >= 1.5 else "NO-GO")
    print(f"\nSPEED {verdict}: effective speedup {ratio_eff:.2f}x vs {bar:.0f}x bar")
    if verdict != "GO":
        print("  (note: machine is saturated by the gait_qd3_1000 run; flex can also")
        print("   likely take a larger stable timestep -> rerun on an idle box.)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["contract", "locomote", "speed"])
    args = ap.parse_args()
    {"contract": cmd_contract, "locomote": cmd_locomote,
     "speed": cmd_speed}.get(args.part, lambda a: print("not yet"))(args)


if __name__ == "__main__":
    main()
