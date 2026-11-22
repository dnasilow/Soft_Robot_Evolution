import numpy as np, sys
sys.path.insert(0, r'C:\SoftRobotEvolution')
from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics, e_scaled, EHAT, POISSON

L = 0.01
def grid(cells, mat=3, shape=(20,20,20)):
    g = np.zeros(shape, np.int8)
    for c in cells: g[c] = mat
    return g

def eng(g, poisson=True, rule='voxelyze'):
    e = MuJoCoBeamPhysics(actuation_amplitude=0.0, fitness_mode='forward', poisson=poisson, dt_rule=rule)
    e.load_robot(g)
    return e

E = e_scaled(3)
e = eng(grid([(1,1,1),(2,1,1)]))
eps = np.array([0.01])
print("2-vox ps:", e.poisson_strain(eps))
F = e.axial_bond_force(eps*L, np.array([L]))
print("2-vox F/(E L^2 eps) =", F/(E*L*L*0.01), " expect Ehat*(1-nu) =", EHAT*(1-POISSON))

e = eng(grid([(i,1,1) for i in range(9)]))
eps = np.full(len(e.bi), 0.01)
ps = e.poisson_strain(eps)
print("chain ps mid:", ps[4], "ends:", ps[0])
F = e.axial_bond_force(eps*L, np.full(len(e.bi), L))
print("chain F/(E L^2 eps): mid", F[4]/(E*L*L*0.01), " end", F[0]/(E*L*L*0.01))

cells = [(x,y,z) for x in range(5) for y in range(5) for z in range(5)]
e = eng(grid(cells))
eps = np.where(e.ba==0, 0.01, 0.0)
ps = e.poisson_strain(eps)
c = [k for k,cc in enumerate(e.cells) if cc==(2,2,2)][0]
print("block centre ps:", ps[c], "tension:", e._tension[c])
F = e.axial_bond_force(eps*L, np.full(len(e.bi), L))
mid = [b for b in range(len(e.bi)) if e.ba[b]==0 and e.cells[e.bi[b]]==(2,2,2)][0]
print("block centre-bond F/(E L^2 eps) =", F[mid]/(E*L*L*0.01), " expect", EHAT*(1-POISSON))

for rule in ('voxelyze','ours'):
    for pois in (True, False):
        e = eng(grid([(i,1,1) for i in range(6)]), poisson=pois, rule=rule)
        print(f"dt {rule:9s} poisson={pois}: raw {e.stable_dt(0.7 if rule=='voxelyze' else 0.8)*1e3:.5f} ms  used {e.default_timestep*1e3:.5f}")
