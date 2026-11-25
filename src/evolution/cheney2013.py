"""Rules of the Cheney et al. 2013 experiment that do not depend on the simulator.

Everything here was read from the authors' source (HCUBE_SoftbotsExperiment.cpp in
softbots2013Code.tgz) and checked against the deposited robot files:

  * how a body is written into a robot file (.vxa): ten rows of 100 digits, material numbers
    1 = active phase 1, 2 = passive soft, 3 = active phase 2, 4 = passive stiff;
  * the score: fabs(FinalCOM_Dist) / (workspace width), with the 2013 code's handling of missing,
    NaN and absurd values;
  * the optional cost penalties: fitness * (1 - (count / maximum) ** exponent). The
    actuated-voxel form reproduces the adjusted/original score ratio of 148 deposited robots to
    7.5e-8.

This project's material numbers are 1 = muscle phase 0, 2 = muscle phase pi, 3 = soft passive,
4 = stiff passive.
"""
import re

import numpy as np

WORKSPACE = 10                       # voxels per side of the 2013 workspace
VOXEL_SIZE_2013 = 0.001              # m: FixedBoundingBoxSize 10 * 0.001 / num_x_voxels
OURS_TO_2013 = {0: '0', 1: '1', 2: '3', 3: '2', 4: '4'}
FROM_2013 = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4, 5: 2}
PENALTIES = ('none', 'voxels', 'actuated', 'connections')
LAYER = re.compile(r'(<Layer><!\[CDATA\[)(.*?)(\]\]></Layer>)', re.S)
FLOOR_FITNESS = 0.0001               # what the 2013 code assigns to anything unusable
MISSING_FITNESS = 0.001              # ... and to a simulation that left no result


def workspace_grid(grid, n: int = WORKSPACE) -> np.ndarray:
    """The n x n x n workspace of a body. Our genomes are larger arrays with the workspace
    starting at genome_config.VOXEL_INTERIOR_MIN on every axis; the block is returned as it was
    decoded (not moved), which is what the 2013 pipeline simulates."""
    g = np.asarray(grid)
    if g.shape == (n, n, n):
        return g.astype(np.int8)
    from src.evolution.genome_config import VOXEL_INTERIOR_MIN as i0
    block = g[i0:i0 + n, i0:i0 + n, i0:i0 + n]
    if int((g != 0).sum()) != int((block != 0).sum()):
        raise ValueError(f"body has voxels outside the {n}-voxel workspace "
                         f"(array {g.shape}, workspace starts at index {i0})")
    return block.astype(np.int8)


def start_height(grid, n: int = WORKSPACE, voxel_size: float = VOXEL_SIZE_2013) -> float:
    """How far above the floor a body begins when it is started where it is in the workspace, as
    the 2013 simulator starts it: its lowest occupied layer times the voxel size. 0 for a body
    that touches the bottom of the workspace, and for an empty body. (The 2013 simulator lets
    such a body fall, and its score, a distance in three dimensions, includes the drop.)"""
    occupied = np.argwhere(workspace_grid(grid, n) != 0)
    return float(occupied[:, 2].min() * voxel_size) if len(occupied) else 0.0


def layer_rows(g) -> list:
    """Our n^3 grid as the rows of a robot file: one string per layer (z), row-major over y
    then x, in the 2013 material numbers."""
    g = np.asarray(g)
    return [''.join(OURS_TO_2013[int(v)] for v in g[:, :, z].T.flatten()) for z in range(g.shape[2])]


def grid_from_rows(rows, n: int = WORKSPACE) -> np.ndarray:
    """Inverse of layer_rows (reads a deposited robot file's rows into our numbering)."""
    g = np.zeros((n, n, len(rows)), np.int8)
    for z, row in enumerate(rows):
        g[:, :, z] = np.array([FROM_2013[int(c)] for c in row.strip()], np.int8).reshape(n, n).T
    return g


def fill_template(template_text: str, g) -> str:
    """The template robot file with its ten layer rows replaced by this body."""
    rows = layer_rows(g)
    if len(LAYER.findall(template_text)) != len(rows):
        raise ValueError("template and body have different numbers of layers")
    it = iter(rows)
    return LAYER.sub(lambda m: m.group(1) + next(it) + m.group(3), template_text)


def counts(g) -> dict:
    """Voxels, actuated voxels and voxel-to-voxel connections of a body (the three quantities
    the 2013 penalties use; a connection is one shared face)."""
    g = np.asarray(g)
    occ = g != 0
    conn = int((occ[1:] & occ[:-1]).sum() + (occ[:, 1:] & occ[:, :-1]).sum()
               + (occ[:, :, 1:] & occ[:, :, :-1]).sum())
    return {'voxels': int(occ.sum()), 'actuated': int(((g == 1) | (g == 2)).sum()),
            'connections': conn}


def penalty_metric(g, kind: str) -> int:
    """The count the 2013 code calls voxelPenalty. With no penalty it is the number of voxels,
    which the code also uses for its 'fewer than 2 -> not simulated' rule."""
    if kind not in PENALTIES:
        raise ValueError(f"penalty must be one of {PENALTIES}, got {kind!r}")
    return counts(g)['voxels' if kind == 'none' else kind]


def penalty_factor(g, kind: str, exponent: float = 1.0, n: int = WORKSPACE) -> float:
    """fitness multiplier 1 - (count / maximum) ** exponent; 1.0 when there is no penalty.
    Maximum: n^3 voxels, or 3 * (n^3 - n^2) connections."""
    if kind == 'none':
        return 1.0
    out_of = 3 * (n ** 3 - n ** 2) if kind == 'connections' else n ** 3
    return 1.0 - (penalty_metric(g, kind) / out_of) ** exponent


def clamp(f: float) -> float:
    """if (fitness < 0.0001) fitness = 0.0001; if (fitness > 1000) fitness = 0.0001;"""
    return FLOOR_FITNESS if (not f >= FLOOR_FITNESS or f > 1000) else float(f)


def fitness_from_result(text, n: int = WORKSPACE, voxel_size: float = VOXEL_SIZE_2013) -> float:
    """The 2013 score from the simulator's FinalCOM_Dist text (None if it left no result).
    No result -> 0.001; a value containing 'n' (nan, inf) -> 0.0001; otherwise
    fabs(distance) / (n * voxel size), then clamped."""
    if text is None or not str(text).strip():
        return MISSING_FITNESS
    t = str(text).strip()
    if 'n' in t.lower():
        return FLOOR_FITNESS
    try:
        return clamp(abs(float(t)) / (n * voxel_size))
    except ValueError:
        return MISSING_FITNESS


def penalised(original: float, g, kind: str, exponent: float = 1.0, n: int = WORKSPACE) -> float:
    """Adjusted fitness as the 2013 code computes it from the original one."""
    if kind == 'none':
        return float(original)
    return clamp(original * penalty_factor(g, kind, exponent, n))
