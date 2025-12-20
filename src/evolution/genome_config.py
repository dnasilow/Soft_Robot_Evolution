"""Genome configuration constants for soft robot evolution"""

import numpy as np

# ==================== VOXEL GRID CONFIGURATION ====================

# Voxel grid dimensions (X, Y, Z)
# Increased from 5×5×5 to 8×8×8 for more complex morphologies
VOXEL_GRID_SHAPE = (8, 8, 8)

# Usable interior range (to prevent edge effects)
# Outer shell reserved for connectivity
# For 8×8×8 grid: usable range is indices 1-6 (6×6×6 = 216 voxels)
VOXEL_INTERIOR_MIN = 1
VOXEL_INTERIOR_MAX = 7  # Exclusive (range 1-6 inclusive)

# Voxel physical size (meters)
VOXEL_SIZE = 0.01  # 1 cm cubes

# ==================== INITIAL POPULATION PARAMETERS ====================

# Number of voxels per robot (random range)
# Increased proportionally with larger grid
MIN_VOXELS_PER_ROBOT = 10  # Minimum voxels
MAX_VOXELS_PER_ROBOT = 30  # Maximum voxels

# Material selection probabilities
# Equal probability for all materials (uniform distribution)
MATERIAL_TYPES = [1, 2, 3, 4]
MATERIAL_PROBABILITIES = [0.25, 0.25, 0.25, 0.25]  # Equal weights

# To bias towards active materials, use:
# MATERIAL_PROBABILITIES = [0.4, 0.3, 0.2, 0.1]  # Favor types 1 and 2

# ==================== HELPER FUNCTIONS ====================

def create_empty_grid():
    """Create an empty voxel grid"""
    return np.zeros(VOXEL_GRID_SHAPE, dtype=np.int8)

def get_random_interior_position():
    """Get random position in usable interior"""
    x = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)
    y = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)
    z = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)
    return (x, y, z)

def get_random_material():
    """Get random material type"""
    return np.random.choice(MATERIAL_TYPES, p=MATERIAL_PROBABILITIES)

def get_num_voxels():
    """Get random number of voxels for new robot"""
    return np.random.randint(MIN_VOXELS_PER_ROBOT, MAX_VOXELS_PER_ROBOT + 1)

def get_max_usable_voxels():
    """Calculate maximum usable voxels"""
    interior_size = VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN
    return interior_size ** 3

# ==================== VALIDATION ====================

def validate_config():
    """Validate genome configuration"""
    issues = []

    # Check grid size
    if any(dim < 5 for dim in VOXEL_GRID_SHAPE):
        issues.append(f"WARNING: Grid size {VOXEL_GRID_SHAPE} too small (min 5×5×5)")

    # Check interior range
    interior_size = VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN
    if interior_size < 3:
        issues.append(f"WARNING: Interior range too small ({interior_size}³)")

    # Check voxel counts
    max_usable = get_max_usable_voxels()
    if MAX_VOXELS_PER_ROBOT > max_usable:
        issues.append(f"WARNING: MAX_VOXELS_PER_ROBOT ({MAX_VOXELS_PER_ROBOT}) exceeds usable space ({max_usable})")

    # Check probabilities sum to 1
    if not np.isclose(sum(MATERIAL_PROBABILITIES), 1.0):
        issues.append(f"ERROR: Material probabilities sum to {sum(MATERIAL_PROBABILITIES)}, must be 1.0")

    return issues


if __name__ == "__main__":
    print("="*70)
    print("GENOME CONFIGURATION")
    print("="*70)
    print(f"\nGrid shape: {VOXEL_GRID_SHAPE}")
    print(f"Total positions: {np.prod(VOXEL_GRID_SHAPE)}")
    print(f"Interior range: [{VOXEL_INTERIOR_MIN}, {VOXEL_INTERIOR_MAX})")
    interior_size = VOXEL_INTERIOR_MAX - VOXEL_INTERIOR_MIN
    print(f"Usable interior: {interior_size}×{interior_size}×{interior_size} = {get_max_usable_voxels()} voxels")
    print(f"\nVoxels per robot: {MIN_VOXELS_PER_ROBOT}-{MAX_VOXELS_PER_ROBOT}")
    print(f"Voxel size: {VOXEL_SIZE} m ({VOXEL_SIZE*100} cm)")
    print(f"\nMaterial probabilities:")
    for mat_id, prob in zip(MATERIAL_TYPES, MATERIAL_PROBABILITIES):
        mat_names = {1: "Active 0°", 2: "Active 180°", 3: "Soft passive", 4: "Stiff passive"}
        print(f"  Type {mat_id} ({mat_names[mat_id]}): {prob*100:.1f}%")

    issues = validate_config()
    if issues:
        print(f"\n⚠ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✓ Configuration valid")
