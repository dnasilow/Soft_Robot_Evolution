"""Morphology scorecard: judge "limbs vs. blob" by the same numbers for every run.

Reads a run's MAP-Elites archive (archive.pkl, or checkpoint.pkl for an unfinished run) and
reports, per body:
  feet        separate contact patches in the lowest layer (face-connected, as the physics
              connects voxels). A solid slab is 1; four legs standing on the floor is 4.
  feet2       separate pieces of the bottom TWO layers (6-connected), so legs of unequal
              length still count; a slab in layer 2 joins them back into 1.
  footprint   filled cells in the lowest layer (out of the grid's side^2)
  fill        voxels / bounding-box volume (1 = solid brick; low = gaps and protrusions)
  elongation  longest / shortest bounding-box extent
  materials   muscle-1, muscle-2, soft, stiff counts

Pre-registered success test (agreed 2026-09-15, before the friction pilot):
  PASS if at least one top-10 body has >= 2 feet, OR the champion's footprint is <= 50 cells.

--dynamic also simulates the champion and counts the floor contact patches actually present
during its gait (the undeformed design can differ from what touches the floor when it rocks).
Pass the run's physics flags (--sim-time, --settle, --amp, friction) so it matches the run.

usage:  python morphology_scorecard.py results/<run> [results/<run2> ...] [--dynamic ...]
"""
import argparse
import pickle
from collections import deque
from pathlib import Path

import numpy as np

FEET_MIN   = 2     # PASS: some top-10 body has at least this many feet
FOOT_MAX   = 50    # PASS: or the champion's footprint is at most this many cells


def _components(mask: np.ndarray) -> list:
    """Sizes of face-connected components of a boolean 2-D or 3-D mask, largest first."""
    seen, sizes = np.zeros_like(mask, bool), []
    steps = [s for s in np.eye(mask.ndim, dtype=int)] + [-s for s in np.eye(mask.ndim, dtype=int)]
    for start in zip(*np.nonzero(mask)):
        if seen[start]:
            continue
        q, n = deque([start]), 0
        seen[start] = True
        while q:
            p = q.popleft(); n += 1
            for s in steps:
                nb = tuple(np.add(p, s))
                if all(0 <= nb[k] < mask.shape[k] for k in range(mask.ndim)) and mask[nb] and not seen[nb]:
                    seen[nb] = True; q.append(nb)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def body_metrics(g: np.ndarray) -> dict:
    occ = g != 0
    idx = np.argwhere(occ)
    z0 = idx[:, 2].min()
    ext = idx.max(0) - idx.min(0) + 1
    return {
        'vox':        int(occ.sum()),
        'feet':       len(_components(occ[:, :, z0])),
        'feet2':      len(_components(occ[:, :, z0:z0 + 2])),
        'footprint':  int(occ[:, :, z0].sum()),
        'fill':       float(occ.sum() / np.prod(ext)),
        'elongation': float(ext.max() / max(ext.min(), 1)),
        'mats':       tuple(int((g == k).sum()) for k in (1, 2, 3, 4)),
    }


def load_archive(run: Path):
    for fn in ('archive.pkl', 'checkpoint.pkl'):
        p = run / fn
        if p.exists():
            return pickle.load(open(p, 'rb'))['archive'], fn
    raise SystemExit(f"ERROR: no archive.pkl or checkpoint.pkl in {run}")


def dynamic_patches(genome, args) -> dict:
    """Simulate and count voxel-floor contact patches (face-connected in the body's grid)."""
    import mujoco
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    fr = None
    if args.friction is not None:
        fr = {'mode': 'single', 'mu': args.friction}
    elif args.friction_static is not None:
        fr = {'mode': 'stickslip', 'mu_s': args.friction_static, 'mu_k': args.friction_kinetic,
              'v_on': args.slip_speed, 'v_off': args.stick_speed}
    fkw = {} if fr is None else {'friction': fr}
    if args.body == 'beam':
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        e = MuJoCoBeamPhysics(actuation_amplitude=args.amp, fitness_mode='forward',
                              poisson=getattr(args, 'poisson', 'on') == 'on',
                              dt_rule=getattr(args, 'dt_rule', 'voxelyze'), **fkw)
    else:
        e = MuJoCoTendonPhysics(actuation_amplitude=args.amp, fitness_mode='forward', **fkw)
    e.load_robot(genome)
    m, d = e.model, e.data
    ground = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, 'ground')
    cells = np.argwhere(genome != 0)          # voxel k <-> k-th nonzero cell (converter order)
    geom_voxel = {int(m.geom_bodyid[i]) - 1: None for i in range(m.ngeom)}
    for _ in range(int(args.settle / e.default_timestep)):
        e.step()
    patches, touching = [], []
    for s in range(int(args.sim_time / e.default_timestep)):
        e.step()
        if s % 20:
            continue
        vox = set()
        for i in range(d.ncon):
            c = d.contact[i]
            if ground in (c.geom1, c.geom2):
                other = c.geom2 if c.geom1 == ground else c.geom1
                vox.add(int(m.geom_bodyid[other]) - 1)
        mask = np.zeros(genome.shape, bool)
        for k in vox:
            mask[tuple(cells[k])] = True
        patches.append(len(_components(mask)) if vox else 0)
        touching.append(len(vox))
    return {'patches_mean': float(np.mean(patches)), 'patches_max': int(np.max(patches)),
            'touching_mean': float(np.mean(touching))}


def score(run: Path, args) -> bool:
    archive, src = load_archive(run)
    rows = sorted(({'fit': e['fitness'], 'genome': e['genome'], **body_metrics(e['genome'])}
                   for e in archive.values()), key=lambda r: -r['fit'])
    top10, champ = rows[:10], rows[0]
    feet = np.array([r['feet'] for r in rows])
    print(f"\n{'=' * 78}\n{run.name}   ({len(rows)} bodies, from {src})\n{'=' * 78}")
    print(f"  archive: feet=1 for {100 * (feet == 1).mean():.0f}% of bodies, max feet {feet.max()} | "
          f"footprint median {np.median([r['footprint'] for r in rows]):.0f} | "
          f"fill median {np.median([r['fill'] for r in rows]):.2f}")
    print(f"  {'rank':>4}{'fit':>8}{'vox':>5}{'feet':>5}{'feet2':>6}{'footpr':>7}{'fill':>6}{'elong':>6}   mats (m1/m2/soft/stiff)")
    for i, r in enumerate(top10, 1):
        print(f"  {i:>4}{r['fit']:>8.4f}{r['vox']:>5}{r['feet']:>5}{r['feet2']:>6}{r['footprint']:>7}"
              f"{r['fill']:>6.2f}{r['elongation']:>6.2f}   {'/'.join(map(str, r['mats']))}")
    feet_ok = any(r['feet'] >= FEET_MIN for r in top10)
    foot_ok = champ['footprint'] <= FOOT_MAX
    verdict = feet_ok or foot_ok
    print(f"  TEST  top-10 body with >= {FEET_MIN} feet: {'yes' if feet_ok else 'no'}   |   "
          f"champion footprint {champ['footprint']} <= {FOOT_MAX}: {'yes' if foot_ok else 'no'}")
    print(f"  VERDICT: {'PASS - limb-like morphology' if verdict else 'FAIL - no limbs by the agreed test'}")
    if args.dynamic:
        dp = dynamic_patches(champ['genome'], args)
        print(f"  dynamic (champion, {args.sim_time}s): floor patches mean {dp['patches_mean']:.2f} "
              f"max {dp['patches_max']} | voxels touching mean {dp['touching_mean']:.1f}")
    return verdict


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('runs', nargs='+', help='run directories, e.g. results/cheney_repro_s1')
    ap.add_argument('--dynamic', action='store_true', help='also simulate the champion')
    ap.add_argument('--sim-time', type=float, default=2.5)
    ap.add_argument('--settle', type=float, default=0.5)
    ap.add_argument('--amp', type=float, default=0.16)
    ap.add_argument('--friction', type=float, default=None)
    ap.add_argument('--friction-static', type=float, default=None)
    ap.add_argument('--friction-kinetic', type=float, default=None)
    ap.add_argument('--body', default='springs', choices=['springs', 'beam'])
    ap.add_argument('--poisson', default='on', choices=['on', 'off'])
    ap.add_argument('--dt-rule', dest='dt_rule', default='voxelyze', choices=['voxelyze', 'ours'])
    ap.add_argument('--slip-speed', type=float, default=0.02)
    ap.add_argument('--stick-speed', type=float, default=0.01)
    a = ap.parse_args()
    if (a.friction_static is None) != (a.friction_kinetic is None):
        raise SystemExit("ERROR: --friction-static and --friction-kinetic go together")
    for r in a.runs:
        score(Path(r), a)
