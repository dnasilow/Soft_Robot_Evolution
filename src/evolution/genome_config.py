"""Genome configuration constants for soft robot evolution"""

from collections import deque
import numpy as np

# ==================== VOXEL GRID CONFIGURATION ====================

VOXEL_GRID_SHAPE   = (8, 8, 8)
VOXEL_INTERIOR_MIN = 1
VOXEL_INTERIOR_MAX = 7   # exclusive → usable indices 1-6 (6×6×6 = 216 positions)
VOXEL_SIZE         = 0.01  # metres per voxel edge

# ==================== POPULATION PARAMETERS ====================

MIN_VOXELS_PER_ROBOT = 20
MAX_VOXELS_PER_ROBOT = 50

MATERIAL_TYPES         = [1, 2, 3, 4]
MATERIAL_PROBABILITIES = [0.25, 0.25, 0.25, 0.25]

# ==================== CONNECTIVITY ====================

# 6 face-neighbours only — matches the face-only spring connectivity in the
# physics engine.  A voxel that only touches the body diagonally has zero
# springs connecting it and is physically isolated, so it must be excluded.
_FACE_OFFSETS = [
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
]


def keep_largest_component(grid: np.ndarray) -> np.ndarray:
    """Return a copy of grid containing only the largest face-connected voxel cluster.

    Uses 6-connectivity (face neighbours only) to match the physics engine's
    face-only spring topology.  Voxels isolated from the main body are zeroed.
    Empty spaces (material 0) inside the body are preserved — hollow
    morphologies remain fully supported.
    """
    occupied = set(map(tuple, np.argwhere(grid != 0).tolist()))
    if not occupied:
        return grid.copy()

    unvisited  = set(occupied)
    components = []

    while unvisited:
        start = next(iter(unvisited))
        comp  = []
        q     = deque([start])
        unvisited.discard(start)
        while q:
            x, y, z = q.popleft()
            comp.append((x, y, z))
            for dx, dy, dz in _FACE_OFFSETS:
                nb = (x + dx, y + dy, z + dz)
                if nb in unvisited:
                    unvisited.discard(nb)
                    q.append(nb)
        components.append(comp)

    largest = max(components, key=len)
    result  = np.zeros_like(grid)
    for x, y, z in largest:
        result[x, y, z] = grid[x, y, z]
    return result


# ==================== GENOME CREATION ====================

def create_empty_grid() -> np.ndarray:
    return np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8)


def get_random_interior_position():
    return (
        np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX),
        np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX),
        np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX),
    )


def get_random_material() -> int:
    return int(np.random.choice(MATERIAL_TYPES, p=MATERIAL_PROBABILITIES))


def get_num_voxels() -> int:
    return int(np.random.randint(MIN_VOXELS_PER_ROBOT, MAX_VOXELS_PER_ROBOT + 1))


def get_max_usable_voxels() -> int:
    return (VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN) ** 3


def create_connected_genome() -> np.ndarray:
    """Create a random voxel body that is guaranteed to be fully connected.

    Uses a growth algorithm: start from one seed voxel and repeatedly add
    a random 26-neighbour. Empty spaces inside the body (material 0) can
    be introduced later by the mutation operator.
    """
    grid     = create_empty_grid()
    target_n = get_num_voxels()

    # Seed
    sx, sy, sz = get_random_interior_position()
    grid[sx, sy, sz] = get_random_material()
    frontier = [(sx, sy, sz)]
    placed   = 1

    while placed < target_n and frontier:
        fi         = np.random.randint(len(frontier))
        fx, fy, fz = frontier[fi]

        # Empty interior FACE neighbours of this frontier voxel
        candidates = []
        for dx, dy, dz in _FACE_OFFSETS:
            nx, ny, nz = fx + dx, fy + dy, fz + dz
            if (VOXEL_INTERIOR_MIN <= nx < VOXEL_INTERIOR_MAX and
                    VOXEL_INTERIOR_MIN <= ny < VOXEL_INTERIOR_MAX and
                    VOXEL_INTERIOR_MIN <= nz < VOXEL_INTERIOR_MAX and
                    grid[nx, ny, nz] == 0):
                candidates.append((nx, ny, nz))

        if candidates:
            cx, cy, cz = candidates[np.random.randint(len(candidates))]
            grid[cx, cy, cz] = get_random_material()
            frontier.append((cx, cy, cz))
            placed += 1
        else:
            frontier.pop(fi)   # fully surrounded — remove from frontier

    return grid


# ==================== VALIDATION ====================

def validate_config():
    issues = []
    if any(d < 5 for d in VOXEL_GRID_SHAPE):
        issues.append(f"Grid {VOXEL_GRID_SHAPE} too small (min 5x5x5)")
    if (VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN) < 3:
        issues.append("Interior range too small")
    if MAX_VOXELS_PER_ROBOT > get_max_usable_voxels():
        issues.append(f"MAX_VOXELS_PER_ROBOT ({MAX_VOXELS_PER_ROBOT}) exceeds usable space")
    if not np.isclose(sum(MATERIAL_PROBABILITIES), 1.0):
        issues.append("Material probabilities must sum to 1.0")
    return issues


if __name__ == "__main__":
    interior = VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN
    print(f"Grid: {VOXEL_GRID_SHAPE}  |  Interior: {interior}x{interior}x{interior} = {get_max_usable_voxels()} positions")
    print(f"Voxels per robot: {MIN_VOXELS_PER_ROBOT}-{MAX_VOXELS_PER_ROBOT}")
    print(f"Voxel size: {VOXEL_SIZE*100:.0f} cm")
    for issue in validate_config():
        print(f"  WARNING: {issue}")
