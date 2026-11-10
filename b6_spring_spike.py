"""
Mass-spring engine feasibility spike (throwaway).

Hypothesis: a discrete mass-spring network (corner-node point masses + Hookean
springs + PER-NODE ground contact) could hit the sweet spot the other two miss:
  - unlike FLEX: individual node masses grip/ratchet the floor (flex's missing piece)
  - unlike TENDON: no rigid per-voxel box self-collision (tendon's ~99% cost)
Risk: MuJoCo's efficient deformable path is FEM (flex); many spring tendons may be slow.
So: measure build/stability/speed/locomotion at small scale BEFORE committing.
"""
import numpy as np, time, mujoco

_CORNERS = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
# axial edges (12) + face diagonals (12) for shear stability
_AXIAL = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
_FACEDIAG = [(0,2),(1,3),(4,6),(5,7),(0,5),(1,4),(2,7),(3,6),(1,6),(2,5),(0,7),(3,4)]
_XEDGES = [(0,1),(3,2),(4,5),(7,6)]  # forward muscles


def build_spring_spec(grid, voxel_size=0.05, initial_height=0.0, k_edge=800.0,
                      k_diag=400.0, damp=2.0, muscle_kp=600.0, node_mass=2e-3,
                      timestep=0.0005, foot_friction=2.0, node_radius_frac=0.28):
    grid = np.asarray(grid); occ = np.argwhere(grid != 0)
    if len(occ) == 0: raise ValueError("empty grid")
    nid = {}; coords = []
    def node(c):
        k = tuple(int(v) for v in c)
        if k not in nid: nid[k] = len(coords); coords.append(k)
        return nid[k]
    voxel_corner_ids, mats = [], []
    for (i,j,k) in occ:
        cids = [node((i+dx,j+dy,k+dz)) for (dx,dy,dz) in _CORNERS]
        voxel_corner_ids.append(cids); mats.append(int(grid[i,j,k]))
    P = np.array(coords, float); P -= P.min(0); P *= voxel_size
    zmin = P[:,2].min()
    n_nodes = len(P)

    spec = mujoco.MjSpec()
    spec.option.timestep = timestep
    spec.option.gravity = [0,0,-9.81]
    wb = spec.worldbody
    g = wb.add_geom(); g.name="ground"; g.type=mujoco.mjtGeom.mjGEOM_PLANE
    g.size=[5,5,0.1]; g.friction=[0.7,0.005,0.0001]; g.contype=4; g.conaffinity=3
    r = voxel_size*node_radius_frac
    z_off = initial_height + voxel_size*0.5
    node_bodies = []
    for n in range(n_nodes):
        b = wb.add_body(); b.name=f"n{n}"; b.pos=[P[n,0], P[n,1], P[n,2]+z_off]
        for ax in ([1,0,0],[0,1,0],[0,0,1]):
            j = b.add_joint(); j.type=mujoco.mjtJoint.mjJNT_SLIDE; j.axis=ax; j.damping=0.2
        gm = b.add_geom(); gm.type=mujoco.mjtGeom.mjGEOM_SPHERE; gm.size[0]=r
        gm.mass=node_mass; gm.contype=2; gm.conaffinity=4; gm.friction[0]=foot_friction
        gm.rgba[:]=[0.6,0.6,0.9,1]
        s = b.add_site(); s.name=f"s{n}"; s.pos=[0,0,0]; s.size[0]=0.002
        node_bodies.append(b)

    def add_spring(a, b, kk):
        if a==b: return
        key=(min(a,b),max(a,b))
        if key in springset: return
        springset.add(key)
        rest=float(np.linalg.norm(P[a]-P[b]))
        t=spec.add_tendon(); t.name=f"sp{len(springset)}"
        t.wrap_site(f"s{a}"); t.wrap_site(f"s{b}")
        t.stiffness=kk; t.damping=damp; t.springlength=[rest,rest]
    springset=set()
    for cids in voxel_corner_ids:
        for (a,b) in _AXIAL: add_spring(cids[a],cids[b],k_edge)
        for (a,b) in _FACEDIAG: add_spring(cids[a],cids[b],k_diag)

    # muscles on x-edges of muscle voxels
    base_phases=[]; muscleset=set()
    for cids,mat in zip(voxel_corner_ids,mats):
        if mat not in (1,2): continue
        phase = 0.0 if mat==1 else np.pi
        for (a,b) in _XEDGES:
            na,nb=cids[a],cids[b]; key=(min(na,nb),max(na,nb))
            if key in muscleset: continue
            muscleset.add(key)
            rest=float(np.linalg.norm(P[na]-P[nb]))
            t=spec.add_tendon(); t.name=f"m{len(base_phases)}"
            t.wrap_site(f"s{na}"); t.wrap_site(f"s{nb}")
            a_=spec.add_actuator(); a_.name=f"act{len(base_phases)}"
            a_.trntype=mujoco.mjtTrn.mjTRN_TENDON; a_.target=t.name
            a_.gaintype=mujoco.mjtGain.mjGAIN_FIXED; a_.biastype=mujoco.mjtBias.mjBIAS_AFFINE
            a_.gainprm[0]=muscle_kp; a_.biasprm[1]=-muscle_kp
            a_.ctrlrange=[0.0, rest*1.6]; a_.ctrllimited=1
            base_phases.append(phase)
    model = spec.compile()
    return model, np.array(base_phases), dict(n_nodes=n_nodes, n_springs=len(springset),
                                              n_muscles=len(base_phases))


def run(grid, label, freq=6, amp=0.6, sim=3.0, settle=0.4):
    model, phases, info = build_spring_spec(grid)
    d = mujoco.MjData(model); mujoco.mj_forward(model, d)
    rest = np.array(d.actuator_length, copy=True); dt=model.opt.timestep; nb=model.nbody
    # speed
    t0=time.perf_counter()
    for _ in range(500): mujoco.mj_step(model,d)
    sps=500/(time.perf_counter()-t0)
    # locomotion (hand wave)
    mujoco.mj_resetData(model,d); t=0.0
    for _ in range(int(settle/dt)):
        d.ctrl[:]=rest*(1+amp*np.sin(2*np.pi*freq*t+phases)); mujoco.mj_step(model,d); t+=dt
    x0=float(np.mean(d.xpos[1:nb,0]))
    for _ in range(int(sim/dt)):
        d.ctrl[:]=rest*(1+amp*np.sin(2*np.pi*freq*t+phases)); mujoco.mj_step(model,d); t+=dt
    bl=(float(np.mean(d.xpos[1:nb,0]))-x0)/max((P_ext(d,nb)),1e-6)
    bad=int(d.warning[mujoco.mjtWarning.mjWARN_BADQACC].number)
    print(f"{label}: nodes={info['n_nodes']} springs={info['n_springs']} musc={info['n_muscles']} "
          f"steps/s={sps:.0f} badqacc={bad} loco={bl:+.3f}BL")

def P_ext(d, nb):
    x=d.xpos[1:nb]; return float((x.max(0)-x.min(0)).max())+0.05

if __name__=="__main__":
    import pickle
    beam=np.ones((10,3,2),dtype=int)
    for i in range(10): beam[i,:,:]=1 if i%2==0 else 2
    run(beam,"beam 10x3x2 (60 vox)")
    with open('results/gait_qd3_1000_CHAMPIONS_BACKUP.pkl','rb') as f:
        champ=pickle.load(f)['genomes'][0]
    run(champ,"champ (300 vox)")
