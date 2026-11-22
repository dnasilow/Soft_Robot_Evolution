"""(A) Quantify the pre-existing material-5 decode bug; (B) verify per-voxel phase
drives a clean muscle body."""
import numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter, N_OUTPUTS
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print(f"N_OUTPUTS={N_OUTPUTS}  -> decode slice logits[:,1:{N_OUTPUTS}] = "
      f"{N_OUTPUTS-1} material columns -> materials 1..{N_OUTPUTS-1}")

# (A) how often does a fresh random body contain material 5 (the spurious 6th output)?
rng = np.random.default_rng(0); innov = InnovationCounter()
n_bodies = 0; n_with5 = 0; muscle_body = None
for _ in range(300):
    c = CPPNGenome(innov, rng); g = c.to_voxel_grid()
    if g is None: continue
    n_bodies += 1
    if int((g == 5).sum()) > 0:
        n_with5 += 1
    elif muscle_body is None and (int((g==1).sum()) + int((g==2).sum())) > 0:
        c.init_phase_cppn(rng); muscle_body = (c, g)   # clean muscle body for (B)
print(f"(A) of {n_bodies} valid random bodies, {n_with5} ({100*n_with5/n_bodies:.0f}%) "
      f"contain material-5 voxels -> these KeyError in the converter -> caught as fitness 0")

# (B) verify mechanism on the clean muscle body
c, g = muscle_body
eng = MuJoCoTendonPhysics(actuation_amplitude=0.08)
eng.load_robot(g)
na = len(eng._base_phases)
mats = {m:int((g==m).sum()) for m in (1,2,3,4)}
print(f"\n(B) clean muscle body: voxels={int((g!=0).sum())} mats={mats} active_tendons={na}")
eng.load_robot(g, gait_params=c.phase_cppn)
bp = np.array(eng._base_phases)
print(f"    per-voxel base_phases: n={len(bp)} min={bp.min():.3f} max={bp.max():.3f} std={bp.std():.3f}")
assert len(bp)==na and bp.std()>1e-3, "phase field must vary across tendons"
eng.load_robot(g, gait_params=(0.5,-0.5,0.0,1.0))
bw=np.array(eng._base_phases)
print(f"    plane-wave std={bw.std():.3f}; per-voxel differs by mean|dphase|={np.abs(bp-bw).mean():.3f}")
print("\nMECHANISM LIVE ON MUSCLE BODY  |  material-5 bug quantified above")
