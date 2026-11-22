"""Authoritative 3-seed comparison: per-voxel phase (pvp) vs evolve-gait control (egfix),
all post-decode-fix. Uses RUN1 backups for seed-1 (pvp_s1 was clobbered by a re-run)."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

SRC = {
    ('pvp',1):   'results/pvp_s1_archive_RUN1_BACKUP.pkl',
    ('pvp',2):   'results/pvp_s2/archive.pkl',
    ('pvp',3):   'results/pvp_s3/archive.pkl',
    ('egfix',1): 'results/egfix_s1_archive_RUN1_BACKUP.pkl',
    ('egfix',2): 'results/egfix_s2/archive.pkl',
    ('egfix',3): 'results/egfix_s3/archive.pkl',
}
def stats(path):
    arc = pickle.load(open(path,'rb'))['archive']
    f = np.array(sorted((e['fitness'] for e in arc.values()), reverse=True))
    return f[0], f[:10].mean(), len(f)

rows = {}
print(f"{'run':10}{'max':>9}{'top10':>9}{'cells':>7}")
for (cfg,sd),p in SRC.items():
    mx, t10, n = stats(p); rows[(cfg,sd)] = (mx, t10)
    print(f"{cfg}_s{sd:<6}{mx:>9.4f}{t10:>9.4f}{n:>7}")

for metric, idx in [('MAX',0), ('TOP-10 MEAN',1)]:
    pv = np.array([rows[('pvp',s)][idx] for s in (1,2,3)])
    eg = np.array([rows[('egfix',s)][idx] for s in (1,2,3)])
    print(f"\n=== {metric} ===")
    print(f"  pvp   seeds {np.round(pv,4).tolist()}  mean {pv.mean():.4f}  range[{pv.min():.4f},{pv.max():.4f}]")
    print(f"  egfix seeds {np.round(eg,4).tolist()}  mean {eg.mean():.4f}  range[{eg.min():.4f},{eg.max():.4f}]")
    print(f"  mean diff = {pv.mean()-eg.mean():+.4f}  ({100*(pv.mean()-eg.mean())/eg.mean():+.1f}%)")
    paired = pv - eg
    print(f"  paired (pvp-egfix) per seed: {np.round(paired,4).tolist()}  -> pvp wins {int((paired>0).sum())}/3")
    sep = pv.min() > eg.max()
    print(f"  distribution separation: pvp_min({pv.min():.4f}) > egfix_max({eg.max():.4f})? {sep}")
