"""
CPPN Genome with NEAT-style Crossover for Soft Robot Body Plans

Maps 3D spatial coordinates to voxel material types, enabling meaningful
recombination in weight-space rather than direct voxel-space.
Reference: Cheney et al., "Unshackling Evolution", GECCO 2013.

Architecture
------------
  Inputs  (4): x_norm, y_norm, z_norm, dist_norm  — each in [-1, 1]
  Outputs (5): logits for materials 0 (empty) … 4  → argmax → material
  Hidden     : added incrementally via add-node structural mutation

NEAT crossover (Stanley & Miikkulainen, 2002)
----------------------------------------------
  Align connection genes by global innovation number.
  Matching genes  → random from either parent (50/50).
  Disjoint/excess → from the fitter parent only.
  Nodes           → union; fitter parent's activation wins on conflict.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from src.evolution.genome_config import (
    VOXEL_GRID_SHAPE,
    VOXEL_INTERIOR_MIN,
    VOXEL_INTERIOR_MAX,
    MIN_VOXELS_PER_ROBOT,
    MAX_VOXELS_PER_ROBOT,
    keep_largest_component,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
N_INPUTS    = 4   # (x_norm, y_norm, z_norm, dist_norm)
N_OUTPUTS   = 6   # A2: [presence, mat1, mat2, mat3, mat4] — presence decoupled from material
ACTIVATIONS = ('tanh', 'sin', 'gaussian', 'abs', 'linear', 'relu')

_FIRST_HIDDEN_ID = N_INPUTS + N_OUTPUTS   # 9; IDs below are reserved for I/O

# Precomputed coordinate grid — built once, reused for every to_voxel_grid() call
_COORD_CACHE: Optional[Tuple[np.ndarray, Tuple[int, int, int]]] = None


def _build_coord_grid() -> Tuple[np.ndarray, Tuple[int, int, int]]:
    """Return cached (N, 4) normalised interior coordinates and interior shape."""
    global _COORD_CACHE
    if _COORD_CACHE is not None:
        return _COORD_CACHE

    lo, hi  = VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX   # e.g. 1, 19
    n       = hi - lo                                    # 18 positions per axis
    centre  = (lo + hi - 1) / 2.0
    half    = (hi - lo) / 2.0

    idx      = np.arange(lo, hi, dtype=np.float32)
    X, Y, Z  = np.meshgrid(idx, idx, idx, indexing='ij')
    xn = (X - centre) / half
    yn = (Y - centre) / half
    zn = (Z - centre) / half
    dn = np.sqrt(xn**2 + yn**2 + zn**2) / np.sqrt(3.0)

    coords       = np.stack([xn.ravel(), yn.ravel(), zn.ravel(), dn.ravel()], axis=1)
    _COORD_CACHE = (coords.astype(np.float32), (n, n, n))
    return _COORD_CACHE


# ─────────────────────────────────────────────────────────────────────────────
# Innovation counter
# ─────────────────────────────────────────────────────────────────────────────
class InnovationCounter:
    """
    Global source of truth for structural gene IDs across an evolutionary run.

    Within a generation, two identical structural mutations reuse the same
    innovation number so NEAT crossover can align them.  Call
    flush_gen_cache() at the end of every generation.
    """

    def __init__(self) -> None:
        self._count:    int                         = _FIRST_HIDDEN_ID
        self._gen_edge: Dict[Tuple[int, int], int]  = {}

    def next_for_edge(self, from_id: int, to_id: int) -> int:
        key = (from_id, to_id)
        if key not in self._gen_edge:
            self._gen_edge[key] = self._count
            self._count        += 1
        return self._gen_edge[key]

    def next_node_id(self) -> int:
        v            = self._count
        self._count += 1
        return v

    def flush_gen_cache(self) -> None:
        self._gen_edge.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Gene classes
# ─────────────────────────────────────────────────────────────────────────────
class NodeGene:
    __slots__ = ('id', 'node_type', 'activation')

    def __init__(self, node_id: int, node_type: str,
                 activation: str = 'tanh') -> None:
        self.id         = node_id
        self.node_type  = node_type    # 'input' | 'hidden' | 'output'
        self.activation = activation

    def copy(self) -> 'NodeGene':
        return NodeGene(self.id, self.node_type, self.activation)


class ConnectionGene:
    __slots__ = ('innovation', 'from_id', 'to_id', 'weight', 'enabled')

    def __init__(self, innovation: int, from_id: int, to_id: int,
                 weight: float, enabled: bool = True) -> None:
        self.innovation = innovation
        self.from_id    = from_id
        self.to_id      = to_id
        self.weight     = weight
        self.enabled    = enabled

    def copy(self) -> 'ConnectionGene':
        return ConnectionGene(
            self.innovation, self.from_id, self.to_id,
            self.weight, self.enabled,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CPPN Genome
# ─────────────────────────────────────────────────────────────────────────────
class CPPNGenome:
    """
    CPPN body-plan encoder with NEAT-style crossover.

    Node ID layout:
      0 … N_INPUTS-1                 → input nodes  (x, y, z, dist)
      N_INPUTS … _FIRST_HIDDEN_ID-1  → output nodes (logits 0–4)
      _FIRST_HIDDEN_ID, …            → hidden nodes added by mutation
    """

    def __init__(self, innov: InnovationCounter,
                 rng: Optional[np.random.Generator] = None) -> None:
        if rng is None:
            rng = np.random.default_rng()
        self._rng = rng

        # I/O nodes
        self.nodes: Dict[int, NodeGene] = {}
        for i in range(N_INPUTS):
            self.nodes[i] = NodeGene(i, 'input', 'linear')
        for k in range(N_OUTPUTS):
            self.nodes[N_INPUTS + k] = NodeGene(N_INPUTS + k, 'output', 'tanh')

        # Minimal fully-connected topology: all inputs → all outputs
        self.connections: Dict[int, ConnectionGene] = {}
        for i in range(N_INPUTS):
            for k in range(N_OUTPUTS):
                out_id = N_INPUTS + k
                inn    = innov.next_for_edge(i, out_id)
                w      = float(rng.normal(0.0, 1.0))
                self.connections[inn] = ConnectionGene(inn, i, out_id, w)

        self._topo_cache: Optional[List[int]] = None

        # Evolvable gait genes (C6): None => legacy material-phase gait (backward compat;
        # old pickled genomes have no attribute -> getattr(...) is None). When enabled via
        # init_gait(), a 4-vector [kx, ky, kz, offset] defines a spatial traveling wave
        # phase(x,y,z) = 2*pi*(kx*xn + ky*yn + kz*zn) + offset that co-evolves with the body.
        self.gait_genes: Optional[np.ndarray] = None

    # ── Evolvable gait (C6) ────────────────────────────────────────────────
    def init_gait(self, rng: np.random.Generator) -> None:
        """Seed a random traveling-wave gait (call on the initial population when
        --evolve-gait is on). Forward (x) wavenumber gets the widest range."""
        self.gait_genes = np.array([rng.uniform(-2.0, 2.0), rng.uniform(-1.0, 1.0),
                                    rng.uniform(-1.0, 1.0), rng.uniform(0.0, 2*np.pi)],
                                   dtype=float)

    def to_gait_params(self) -> Optional[tuple]:
        g = getattr(self, 'gait_genes', None)
        return None if g is None else tuple(float(v) for v in g)

    def mutate_gait(self, rng: np.random.Generator, sigma: float = 0.4) -> None:
        if getattr(self, 'gait_genes', None) is None:
            return
        self.gait_genes = self.gait_genes + rng.normal(0.0, sigma, size=4)
        self.gait_genes[3] = float(self.gait_genes[3] % (2*np.pi))

    # ── Cache ──────────────────────────────────────────────────────────────

    def _invalidate_cache(self) -> None:
        self._topo_cache = None

    # ── Topological sort (Kahn's algorithm) ───────────────────────────────

    def _topo_order(self) -> List[int]:
        if self._topo_cache is not None:
            return self._topo_cache

        input_ids: Set[int] = {n for n, g in self.nodes.items()
                               if g.node_type == 'input'}
        non_input: Set[int] = set(self.nodes) - input_ids

        in_deg: Dict[int, int]       = {n: 0 for n in non_input}
        succs:  Dict[int, List[int]] = {n: [] for n in self.nodes}
        for conn in self.connections.values():
            if conn.enabled and conn.to_id in non_input:
                in_deg[conn.to_id] += 1
                succs[conn.from_id].append(conn.to_id)

        queue  = list(input_ids)
        order: List[int] = []
        seen   = set(input_ids)
        while queue:
            node = queue.pop(0)
            for s in succs[node]:
                in_deg[s] -= 1
                if in_deg[s] == 0 and s not in seen:
                    seen.add(s)
                    order.append(s)
                    queue.append(s)

        # Disconnected / cyclic nodes appended last (evaluate to zero input)
        for n in non_input:
            if n not in seen:
                order.append(n)

        self._topo_cache = order
        return order

    # ── Activation functions ──────────────────────────────────────────────

    @staticmethod
    def _activate(x: np.ndarray, act: str) -> np.ndarray:
        if act == 'tanh':     return np.tanh(x)
        if act == 'sin':      return np.sin(x * np.pi)
        if act == 'gaussian': return np.exp(-(x * x))
        if act == 'abs':      return np.abs(x)
        if act == 'relu':     return np.maximum(0.0, x)
        return x   # linear

    # ── Vectorised forward pass ───────────────────────────────────────────

    def evaluate_batch(self, coords: np.ndarray) -> np.ndarray:
        """
        Evaluate the CPPN at N positions simultaneously.

        coords  : (N, 4) float32 — [x_norm, y_norm, z_norm, dist_norm]
        returns : (N, N_OUTPUTS) float32 — raw logits before argmax
        """
        N = len(coords)

        # Build incoming-connection lookup once (avoids O(E) scan per node)
        conns_to: Dict[int, List[ConnectionGene]] = {n: [] for n in self.nodes}
        for conn in self.connections.values():
            if conn.enabled:
                conns_to[conn.to_id].append(conn)

        # Seed inputs
        vals: Dict[int, np.ndarray] = {i: coords[:, i] for i in range(N_INPUTS)}

        # Forward pass
        for node_id in self._topo_order():
            gene  = self.nodes[node_id]
            total = np.zeros(N, dtype=np.float32)
            for conn in conns_to[node_id]:
                if conn.from_id in vals:
                    total = total + vals[conn.from_id] * np.float32(conn.weight)
            vals[node_id] = self._activate(total, gene.activation)

        out_ids = [N_INPUTS + k for k in range(N_OUTPUTS)]
        return np.stack(
            [vals.get(oid, np.zeros(N, dtype=np.float32)) for oid in out_ids],
            axis=1,
        )

    # ── Decode to voxel grid ──────────────────────────────────────────────

    def to_voxel_grid(self) -> Optional[np.ndarray]:
        """
        Decode CPPN → voxel grid, capped at MAX_VOXELS_PER_ROBOT.

        Material 0 = empty; materials 1-4 = physical voxels.
        argmax over 5 logits determines the material at each of the 5832 interior
        positions. Empty space emerges naturally wherever logit[0] dominates.

        When more than MAX_VOXELS_PER_ROBOT positions come out non-empty, only the
        highest-confidence ones (largest winning-logit value) are kept — this bounds
        the MuJoCo tendon/actuator count to a tractable size while still letting
        evolution express bodies anywhere up to that ceiling.

        Returns None if the resulting body has fewer than MIN_VOXELS_PER_ROBOT voxels
        after keeping only the largest face-connected component.
        """
        coords, interior_dims = _build_coord_grid()
        logits   = self.evaluate_batch(coords)                    # (N, 6): [presence, m1..m4]
        # A2 (Cheney-faithful): one output gates presence, the other four pick the
        # material. This decouples "is a voxel here" from "which material", which the
        # old argmax-over-5 coupled — and which collapsed bodies to a single material.
        present   = logits[:, 0] > 0.0
        material  = (np.argmax(logits[:, 1:N_OUTPUTS], axis=1) + 1).astype(np.int8)  # 1..4
        materials = np.where(present, material, 0).astype(np.int8)

        non_empty_idx = np.where(materials != 0)[0]
        if len(non_empty_idx) > MAX_VOXELS_PER_ROBOT:
            conf    = logits[non_empty_idx, 0]   # keep the highest-presence voxels
            top_k   = np.argpartition(conf, -MAX_VOXELS_PER_ROBOT)[-MAX_VOXELS_PER_ROBOT:]
            kept    = non_empty_idx[top_k]
            trimmed = np.zeros(len(materials), dtype=np.int8)
            trimmed[kept] = materials[kept]
            materials = trimmed

        lo, hi    = VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX
        full_grid = np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8)
        full_grid[lo:hi, lo:hi, lo:hi] = materials.reshape(interior_dims)

        full_grid = keep_largest_component(full_grid)
        if int((full_grid != 0).sum()) < MIN_VOXELS_PER_ROBOT:
            return None
        return full_grid

    # ── Mutation ──────────────────────────────────────────────────────────

    def mutate(self, innov: InnovationCounter,
               rate: float = 0.3) -> 'CPPNGenome':
        """Return a mutated copy; self is unchanged."""
        child = self._clone()
        rng   = child._rng

        # Weight perturbation
        for conn in child.connections.values():
            if rng.random() < rate:
                if rng.random() < 0.9:
                    conn.weight += float(rng.normal(0.0, 0.5))
                else:
                    conn.weight = float(rng.normal(0.0, 1.0))
                conn.weight = float(np.clip(conn.weight, -5.0, 5.0))

        # Toggle connection enable/disable (5 %)
        if rng.random() < 0.05:
            conns = list(child.connections.values())
            if conns:
                c         = conns[int(rng.integers(len(conns)))]
                c.enabled = not c.enabled
                child._invalidate_cache()

        # Add connection (15 %) — bumped now that speciation protects new structure
        if rng.random() < 0.15:
            child._add_connection(innov)

        # Add node — split a connection (8 %) — bumped to feed CPPN complexification
        if rng.random() < 0.08:
            child._add_node(innov)

        # Change hidden-node activation (8 %)
        hidden = [n for n, g in child.nodes.items() if g.node_type == 'hidden']
        if hidden and rng.random() < 0.08:
            nid = hidden[int(rng.integers(len(hidden)))]
            child.nodes[nid].activation = ACTIVATIONS[int(rng.integers(len(ACTIVATIONS)))]

        # Evolvable gait: perturb the traveling-wave genes (no-op if gait not enabled)
        child.mutate_gait(rng)

        return child

    def _add_node(self, innov: InnovationCounter) -> None:
        """Split a random enabled connection by inserting a new hidden node."""
        enabled = [c for c in self.connections.values() if c.enabled]
        if not enabled:
            return
        conn         = enabled[int(self._rng.integers(len(enabled)))]
        conn.enabled = False

        new_id = innov.next_node_id()
        act    = ACTIVATIONS[int(self._rng.integers(len(ACTIVATIONS)))]
        self.nodes[new_id] = NodeGene(new_id, 'hidden', act)

        inn_a = innov.next_for_edge(conn.from_id, new_id)
        inn_b = innov.next_for_edge(new_id,       conn.to_id)
        self.connections[inn_a] = ConnectionGene(inn_a, conn.from_id, new_id, 1.0)
        self.connections[inn_b] = ConnectionGene(inn_b, new_id, conn.to_id, conn.weight)
        self._invalidate_cache()

    def _add_connection(self, innov: InnovationCounter) -> None:
        """Add a random new connection (inputs can't be destinations; outputs can't be sources)."""
        sources  = [n for n, g in self.nodes.items() if g.node_type != 'output']
        dests    = [n for n, g in self.nodes.items() if g.node_type != 'input']
        existing = {(c.from_id, c.to_id) for c in self.connections.values()}
        rng      = self._rng
        for _ in range(20):
            fr = sources[int(rng.integers(len(sources)))]
            to = dests  [int(rng.integers(len(dests)))]
            if fr != to and (fr, to) not in existing:
                inn = innov.next_for_edge(fr, to)
                self.connections[inn] = ConnectionGene(inn, fr, to,
                                                       float(rng.normal(0.0, 1.0)))
                self._invalidate_cache()
                return

    # ── NEAT compatibility distance (for speciation) ───────────────────────

    @staticmethod
    def distance(a: 'CPPNGenome', b: 'CPPNGenome',
                 c1: float = 1.0, c2: float = 1.0, c3: float = 0.4) -> float:
        """
        NEAT genetic distance between two CPPNs, aligned by innovation number:
            d = c1*E/N + c2*D/N + c3*W̄
        E = excess genes, D = disjoint genes, W̄ = mean weight diff over matching
        genes. N is the larger genome's gene count (1 for small genomes, NEAT
        convention), so a single added node/connection moves the distance enough
        to split off a protected species.
        """
        inn_a = set(a.connections)
        inn_b = set(b.connections)
        if not inn_a and not inn_b:
            return 0.0

        matching = inn_a & inn_b
        if matching:
            wd = float(np.mean([abs(a.connections[i].weight - b.connections[i].weight)
                                for i in matching]))
        else:
            wd = 0.0

        border  = min(max(inn_a) if inn_a else 0, max(inn_b) if inn_b else 0)
        excess  = sum(1 for i in (inn_a ^ inn_b) if i >  border)
        disjoint = sum(1 for i in (inn_a ^ inn_b) if i <= border)

        # N=1 (NEAT small-genome convention). These CPPNs start topologically
        # identical (24 genes, weights-only diffs), so normalising by gene count
        # would bury the structural signal: one added node = 2 new genes, which
        # must move the distance by ~2 (well above SPECIES_THRESHOLD) so the
        # complexified variant splits into its own protected species.
        return c1 * excess + c2 * disjoint + c3 * wd

    # ── NEAT crossover ────────────────────────────────────────────────────

    @classmethod
    def crossover(cls,
                  parent_a:  'CPPNGenome',
                  parent_b:  'CPPNGenome',
                  fitness_a: float,
                  fitness_b: float,
                  rng:       Optional[np.random.Generator] = None) -> 'CPPNGenome':
        """
        NEAT-style crossover aligned by innovation number.

        Matching genes  → random from either parent.
        Disjoint/excess → from the fitter parent only.
        Nodes           → union; fitter parent's activation wins on conflict.
        Tie in fitness  → parent_a treated as fitter (arbitrary).
        """
        if rng is None:
            rng = np.random.default_rng()

        fitter = parent_a if fitness_a >= fitness_b else parent_b
        weaker = parent_b if fitness_a >= fitness_b else parent_a

        child             = cls.__new__(cls)
        child._rng        = rng
        child._topo_cache = None

        # Nodes: union; fitter's activation wins on conflict
        child.nodes = {nid: gene.copy() for nid, gene in fitter.nodes.items()}
        for nid, gene in weaker.nodes.items():
            if nid not in child.nodes:
                child.nodes[nid] = gene.copy()

        # Connections: align by innovation number
        inn_a = {c.innovation: c for c in parent_a.connections.values()}
        inn_b = {c.innovation: c for c in parent_b.connections.values()}

        child.connections = {}
        for inn in set(inn_a) | set(inn_b):
            in_a = inn in inn_a
            in_b = inn in inn_b

            if in_a and in_b:
                src  = inn_a[inn] if rng.random() < 0.5 else inn_b[inn]
                gene = src.copy()
                # Both disabled → 25 % re-enable; one disabled → 75 % re-enable
                if not inn_a[inn].enabled and not inn_b[inn].enabled:
                    gene.enabled = bool(rng.random() < 0.25)
                elif not inn_a[inn].enabled or not inn_b[inn].enabled:
                    gene.enabled = bool(rng.random() < 0.75)
            elif in_a and fitter is parent_a:
                gene = inn_a[inn].copy()
            elif in_b and fitter is parent_b:
                gene = inn_b[inn].copy()
            else:
                continue   # gene only in weaker parent — skip

            # Only include if both endpoint nodes exist in child
            if gene.from_id in child.nodes and gene.to_id in child.nodes:
                child.connections[inn] = gene

        # Evolvable gait: inherit the fitter parent's gait genes (like activations)
        _gg = getattr(fitter, 'gait_genes', None)
        child.gait_genes = None if _gg is None else np.array(_gg, copy=True)
        return child

    # ── Utility ───────────────────────────────────────────────────────────

    def _clone(self) -> 'CPPNGenome':
        child             = CPPNGenome.__new__(CPPNGenome)
        child._rng        = np.random.default_rng(int(self._rng.integers(2**31)))
        child.nodes       = {k: v.copy() for k, v in self.nodes.items()}
        child.connections = {k: v.copy() for k, v in self.connections.items()}
        child._topo_cache = None
        _gg = getattr(self, 'gait_genes', None)
        child.gait_genes  = None if _gg is None else np.array(_gg, copy=True)
        return child

    def copy(self) -> 'CPPNGenome':
        return self._clone()

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_connections(self) -> int:
        return sum(1 for c in self.connections.values() if c.enabled)
