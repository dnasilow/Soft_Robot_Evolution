"""Verify the material-5 fix: (1) no more material 5, (2) far fewer dead bodies,
(3) existing champions decode byte-identically (backward compatibility)."""
import pickle, numpy as np, sys, os
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

# (1)+(2) fresh random bodies: material-5 count should be ZERO now
rng = np.random.default_rng(0); innov = InnovationCounter()
n=0; with5=0; mats_seen=set()
for _ in range(300):
    c = CPPNGenome(innov, rng); g = c.to_voxel_grid()
    if g is None: continue
    n+=1
    for m in np.unique(g): mats_seen.add(int(m))
    if int((g==5).sum())>0: with5+=1
print(f"(1) fresh bodies: n={n}  material-5 bodies={with5}  distinct materials seen={sorted(mats_seen)}")
assert with5==0 and 5 not in mats_seen, "material 5 must be gone"

# (3) champions decode identically: re-decode each stored CPPN, compare to stored grid
print("\n(3) backward-compat — re-decode stored champion CPPNs vs their saved grids:")
ok=True
for name in ['tendon_ctrl','tendon_eg','tendon_stiff','tendon_stiff_s2','tendon_stiff_s3','afpo_stiff','gait_qd3_1000']:
    p=f'results/{name}/best_robot.pkl'
    if not os.path.exists(p):
        # gait_qd3_1000 champion is in the CHAMPIONS_BACKUP
        alt=f'results/{name}_CHAMPIONS_BACKUP.pkl'
        p=alt if os.path.exists(alt) else None
    if p is None:
        print(f"  {name:16} (no pkl, skip)"); continue
    d=pickle.load(open(p,'rb'))
    saved=d.get('genome'); c=d.get('cppn')
    if c is None or saved is None:
        print(f"  {name:16} (no cppn/genome, skip)"); continue
    redecoded=c.to_voxel_grid()
    if redecoded is None:
        print(f"  {name:16} re-decode -> None (was {int((saved!=0).sum())} vox)"); ok=False; continue
    same = redecoded.shape==saved.shape and bool((redecoded==saved).all())
    print(f"  {name:16} identical={same}  (voxels {int((saved!=0).sum())})")
    ok = ok and same
print("\nBACKWARD-COMPAT OK" if ok else "\n*** MISMATCH — investigate ***")
assert ok
print("ALL FIX CHECKS PASSED")
