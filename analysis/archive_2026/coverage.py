"""Is <256 coverage normal? Show the 16x16 occupancy of a COMPLETED archive and where the
empty cells sit. Descriptors: x=COM height bin, y=bounce bin (auto-calibrated bounds)."""
import pickle, numpy as np, os, sys
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')

for name in ['pvp_s2', 'pvp_s3', 'egfix_s3']:
    d = pickle.load(open(f'results/{name}/archive.pkl','rb'))
    arc = d['archive']; bins = d.get('archive_bins', 16)
    grid = np.zeros((bins, bins), dtype=int)
    for (i, j) in arc.keys():
        grid[i, j] = 1
    filled = grid.sum()
    print(f"\n===== {name}: {filled}/{bins*bins} filled =====")
    print("  rows = COM-height bin (0=low ground-hugging -> 15=tall)")
    print("  cols = bounce bin     (0=smooth glide       -> 15=bouncy)")
    for i in range(bins):
        row = ''.join('#' if grid[i, j] else '.' for j in range(bins))
        print(f"   h{i:2d} |{row}|")
    # where are the empties?
    empty = [(i, j) for i in range(bins) for j in range(bins) if not grid[i, j]]
    # classify: edge/corner (outer ring) vs interior
    outer = sum(1 for (i, j) in empty if i in (0, bins-1) or j in (0, bins-1))
    hi_h_hi_b = sum(1 for (i, j) in empty if i >= bins*0.6 and j >= bins*0.5)
    print(f"  empty cells: {len(empty)}   on the outer ring: {outer}   "
          f"in the tall+bouncy region: {hi_h_hi_b}")
