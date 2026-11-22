"""Write robots from this project as .vxa files the 2013 simulator can run (the reverse transplant).

A deposited 2013 robot file is used as the template, so every simulation setting is the original
one; only the ten <Layer> rows (the body) are replaced.

Material numbers differ:   ours 1 = muscle phase 0   -> 2013 file 1 (Active_+)
                           ours 2 = muscle phase pi  -> 2013 file 3 (Active_-)
                           ours 3 = soft passive     -> 2013 file 2 (Passive_Soft)
                           ours 4 = stiff passive    -> 2013 file 4 (Passive_Hard)
Our bodies are stored inside a larger array; the occupied box is cut out and placed in the corner
of the 10 x 10 x 10 workspace with its lowest layer on the floor, which is also where our engine
starts a body. The workspace stays 10 voxels wide, so the 2013 score keeps its divisor.

usage:  python paper/reference_2013/export_to_vxa.py
writes: research_reference/extracted/reverse_transplant_vxa/   (kept out of git)
"""
import glob
import os
import pickle
import re
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
DRYAD = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
OUT = os.path.join(ROOT, 'research_reference', 'extracted', 'reverse_transplant_vxa')
HIS_TO_OURS = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}
OURS_TO_HIS = {0: '0', 1: '1', 2: '3', 3: '2', 4: '4'}
LAYER = re.compile(r'(<Layer><!\[CDATA\[)(.*?)(\]\]></Layer>)', re.S)
N = 10


def read_vxa(path):
    text = open(path, encoding='iso-8859-1').read()
    rows = [m.group(2).strip() for m in LAYER.finditer(text)]
    g = np.zeros((N, N, len(rows)), np.int8)
    for z, row in enumerate(rows):
        g[:, :, z] = np.array([HIS_TO_OURS[int(c)] for c in row], np.int8).reshape(N, N).T
    fit = float(re.search(r'origFit_([0-9.eE+-]+)_genome', os.path.basename(path)).group(1))
    return text, rows, g, fit


def layer_rows(g10):
    """Our 10x10x10 grid -> the ten 100-character rows of a .vxa (row-major over y, then x)."""
    return [''.join(OURS_TO_HIS[int(v)] for v in g10[:, :, z].T.flatten()) for z in range(N)]


def to_corner(g):
    """Cut out the occupied box and put it in the workspace corner, lowest layer on the floor."""
    idx = np.argwhere(np.asarray(g) != 0)
    lo, hi = idx.min(0), idx.max(0)
    ext = hi - lo + 1
    if (ext > N).any():
        raise ValueError(f'body is {ext} voxels, larger than the {N}-voxel workspace')
    out = np.zeros((N, N, N), np.int8)
    out[:ext[0], :ext[1], :ext[2]] = np.asarray(g)[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
    return out


def write_vxa(template_text, g10, path):
    rows = iter(layer_rows(g10))
    text = LAYER.sub(lambda m: m.group(1) + next(rows) + m.group(3), template_text)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='iso-8859-1', newline='\n') as f:
        f.write(text)


def name(tag, score, g10):
    return f'{tag}--adjFit_{score:.8f}--numFilled_{int((g10 != 0).sum()):04d}--origFit_{score:.8f}_genome.vxa'


def champions(cond):
    for run in sorted(glob.glob(os.path.join(DRYAD, cond, 'run_*'))):
        best = max(glob.glob(os.path.join(run, 'Gen_1000', '*.vxa')),
                   key=lambda f: float(re.search(r'origFit_([0-9.eE+-]+)_genome', f).group(1)))
        yield os.path.basename(run), best


def main():
    cond = '2013-01-16-10^3-noCost'
    champs = list(champions(cond))
    template_text, rows, g, _ = read_vxa(champs[0][1])

    # 1. the writer must reproduce a deposited body exactly when nothing is moved
    bad = 0
    for run, path in champs:
        _, rows, g, _ = read_vxa(path)
        if '5' not in ''.join(rows) and layer_rows(g) != rows:
            bad += 1
    print(f'round trip of {len(champs)} deposited champions through read_vxa/layer_rows: {bad} mismatches')
    if bad:
        raise SystemExit('exporter is wrong - stopping')

    # 2. control: deposited champions moved to the corner, to show the move itself changes nothing
    n = 0
    for run, path in champs[:12]:
        _, _, g, fit = read_vxa(path)
        g10 = to_corner(g)
        shift = np.argwhere(g != 0).min(0)
        write_vxa(template_text, g10, os.path.join(OUT, 'control-moved-to-corner', run, 'Gen_1000',
                                                   name(f'control--{run}--shift{shift[0]}{shift[1]}{shift[2]}', fit, g10)))
        n += 1
    print(f'wrote {n} control files (deposited champions moved to the corner)')

    # 3. our robots: the whole final population of cheney_score_s1, plus two other champions
    pop = pickle.load(open(os.path.join(ROOT, 'results', 'cheney_score_s1', 'final_population.pkl'), 'rb'))
    fits = np.array(pop['fitnesses'], float)
    n = 0
    for rank, k in enumerate(np.argsort(-fits), 1):
        g = np.asarray(pop['genomes'][k])
        if not (g != 0).any():
            continue
        g10 = to_corner(g)
        write_vxa(template_text, g10, os.path.join(OUT, 'ours-cheney_score_s1', 'final_population', 'Gen_1000',
                                                   name(f'ours--cheney_score_s1--rank{rank:02d}', fits[k], g10)))
        n += 1
    for run in ('cheney_fix600_s1', 'cheney_corr_s1'):
        b = pickle.load(open(os.path.join(ROOT, 'results', run, 'best_robot.pkl'), 'rb'))
        g10 = to_corner(np.asarray(b['genome']))
        write_vxa(template_text, g10, os.path.join(OUT, f'ours-{run}', 'champion', 'Gen_1000',
                                                   name(f'ours--{run}--champion', float(b['fitness']), g10)))
        n += 1
    print(f'wrote {n} of our robots to {OUT}')


if __name__ == '__main__':
    main()
