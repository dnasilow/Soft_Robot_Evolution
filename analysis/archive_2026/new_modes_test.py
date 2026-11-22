"""Test the new levers on the 1.32 champion:
 (A) musclecost / skipbl fitness modes behave sanely + legacy modes unchanged
 (B) shape descriptors are sensible and spread across real bodies
 (C) ACTUATION AMPLITUDE SWEEP (0.08 -> 0.20) with stability check"""
import pickle, numpy as np, os, sys, warnings
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
sys.path.insert(0, '.')
from run_tendon_evolution import _shape_descriptor

d = pickle.load(open('results/pvp_s1_champion_RUN1.pkl','rb'))
g, pc = d['genome'], d['cppn'].phase_cppn
mats = {m:int((g==m).sum()) for m in (1,2,3,4)}
n_musc = mats[1]+mats[2]
print(f"champion: {int((g!=0).sum())} voxels, muscle={n_musc}, materials={mats}\n")

def ev(mode, amp=0.08, maxv=300):
    e = MuJoCoTendonPhysics(actuation_amplitude=amp, fitness_mode=mode, max_voxels=maxv)
    e.load_robot(g, gait_params=pc)
    return float(e.get_fitness(simulation_time=2.5, settle_time=0.5))

print("=== (A) fitness modes (amp 0.08, max_voxels 300) ===")
for m in ['directed','forward','skip','skipbl','musclecost']:
    print(f"  {m:12} = {ev(m):.4f}")
print(f"  expected: musclecost ~ directed x (1 - {n_musc}/300) = "
      f"{ev('directed')*(1-min(1,n_musc/300)):.4f}  (all-muscle body -> ~0, by design)")
print("  -> an ALL-MUSCLE blob is worthless under musclecost; that's the pressure to differentiate")

print("\n=== (B) shape descriptors across real champions ===")
for name, p in [('pvp_s1','results/pvp_s1_champion_RUN1.pkl'),
                ('pvp_s2','results/pvp_s2/best_robot.pkl'),
                ('pvp_s3','results/pvp_s3/best_robot.pkl'),
                ('egfix_s2','results/egfix_s2/best_robot.pkl'),
                ('tendon_ctrl','results/tendon_ctrl/best_robot.pkl')]:
    if not os.path.exists(p): continue
    gg = pickle.load(open(p,'rb'))['genome']
    el, fl = _shape_descriptor(gg)
    print(f"  {name:12} elongation={el:.2f}  fill-density={fl:.2f}")
print("  -> archive axes will spread bodies over these; low fill = 'not a blob'")

print("\n=== (C) ACTUATION AMPLITUDE SWEEP (fitness mode 'directed') ===")
print(f"  {'amp':>6}{'fitness':>10}{'vs 0.08':>10}  stability")
base = None
for amp in [0.08, 0.12, 0.16, 0.20, 0.25]:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            f = ev('directed', amp=amp)
            unstable = any('badqacc' in str(x.message).lower() or 'nan' in str(x.message).lower() for x in w)
            stab = 'UNSTABLE' if (unstable or not np.isfinite(f)) else 'ok'
        except Exception as exc:
            f, stab = float('nan'), f'FAILED ({type(exc).__name__})'
    if base is None: base = f
    rel = f/base if (base and np.isfinite(f)) else float('nan')
    print(f"  {amp:>6.2f}{f:>10.4f}{rel:>9.2f}x  {stab}")
print("  NOTE: champion's gait was EVOLVED at amp 0.08, so higher amp is off-distribution —")
print("        this measures headroom/stability, not what evolution would find at that amp.")
