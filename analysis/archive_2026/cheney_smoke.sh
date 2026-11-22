cd /c/SoftRobotEvolution
python run_tendon_evolution.py --map-elites --grid-size 10 --no-trim --fitness forward \
  --pop 4 --gen 2 --sim-time 0.5 --workers 4 --seed 5 --name gs_cheney_smoke 2>&1 | grep -E "Decoder|Fitness|COMPLETE"
python - <<'PY'
import pickle, numpy as np
a=pickle.load(open('results/gs_cheney_smoke/archive.pkl','rb'))['archive']
s=[int((e['genome']!=0).sum()) for e in a.values()]
ext=[(np.argwhere(e['genome']!=0).max(0)-np.argwhere(e['genome']!=0).min(0)+1).max() for e in a.values()]
print(f"  voxels min={min(s)} med={int(np.median(s))} max={max(s)}")
print(f"  max bbox extent={max(ext)}  (must be <=10 if grid-size took effect)")
print(f"  size varies (not pinned)? {len(set(s))>1}  distinct={len(set(s))}/{len(s)}")
PY
rm -rf results/gs_cheney_smoke
