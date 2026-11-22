"""Extract the REAL pvp_s1 champion (archive #1) from the RUN1 backup into a
best_robot-format pkl, so it can be rendered without touching the live pvp_s1 dir."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

arc = pickle.load(open('results/pvp_s1_archive_RUN1_BACKUP.pkl','rb'))['archive']
top = max(arc.values(), key=lambda e: e['fitness'])
c = top['cppn']
mats = {m:int((top['genome']==m).sum()) for m in (1,2,3,4)}
print(f"real pvp_s1 champion: fitness={top['fitness']:.4f}  voxels={int((top['genome']!=0).sum())}")
print(f"  materials={mats}  has_phase_cppn={getattr(c,'phase_cppn',None) is not None}")
out = {'genome': top['genome'], 'controller': None, 'fitness': top['fitness'], 'cppn': c}
with open('results/pvp_s1_champion_RUN1.pkl','wb') as f:
    pickle.dump(out, f)
print("wrote results/pvp_s1_champion_RUN1.pkl  (render this, NOT best_robot.pkl)")
