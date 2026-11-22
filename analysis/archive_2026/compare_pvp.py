"""Compare egfix_s1 (control) vs pvp_s1 (per-voxel phase): max, top-10 mean, QD,
champion composition, and whether the treatment champion actually uses its phase CPPN."""
import pickle, json, numpy as np, os, sys, glob
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

def summarize(name):
    arc = pickle.load(open(f'results/{name}/archive.pkl','rb'))['archive']
    f = np.array(sorted((e['fitness'] for e in arc.values()), reverse=True))
    champ = pickle.load(open(f'results/{name}/best_robot.pkl','rb'))
    g = champ['genome']; c = champ.get('cppn')
    mats = {m:int((g==m).sum()) for m in (1,2,3,4)}
    gj = sorted(glob.glob(f'results/{name}/gen_*.json'))
    last = json.load(open(gj[-1]))
    # generation at which max was first reached (plateau onset)
    ys = [json.load(open(p)).get('max_fitness',0) for p in gj]
    fm = max(ys); onset = next(i+1 for i,v in enumerate(ys) if v>=fm-1e-9)
    return dict(name=name, cells=len(f), max=f[0], second=f[1], top10=f[:10].mean(),
                median=np.median(f), qd=last.get('qd_score'), cov=last.get('coverage'),
                mats=mats, has_phase=(getattr(c,'phase_cppn',None) is not None),
                onset=onset, ngen=len(ys))

ctrl = summarize('egfix_s1')
trt  = summarize('pvp_s1')
print(f"{'':22}{'CONTROL egfix_s1':>20}{'TREATMENT pvp_s1':>20}")
for k,lab in [('max','max BL'),('second','2nd cell'),('top10','TOP-10 MEAN'),
              ('median','median'),('qd','QD score'),('cov','coverage'),
              ('cells','filled cells'),('onset','max reached @gen'),('has_phase','has phase_cppn')]:
    print(f"{lab:22}{str(round(ctrl[k],4) if isinstance(ctrl[k],float) else ctrl[k]):>20}"
          f"{str(round(trt[k],4) if isinstance(trt[k],float) else trt[k]):>20}")
print(f"\nchampion materials:  control {ctrl['mats']}   treatment {trt['mats']}")
print(f"\ndelta (treatment - control):  max {trt['max']-ctrl['max']:+.4f}  "
      f"top10 {trt['top10']-ctrl['top10']:+.4f}  ({100*(trt['top10']-ctrl['top10'])/ctrl['top10']:+.1f}%)")
# historical reference points
print(f"\nreference: old tendon_eg (pre-fix) max 1.1195; old ceiling ~1.1-1.3")
