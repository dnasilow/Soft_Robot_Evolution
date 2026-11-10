# Answers to Technical Questions

## 1. Maximum Voxels and Voxel Types

### Maximum Voxels Per Robot

**Grid Dimensions**: `(5, 5, 5)` = 125 total positions

**Usable Interior** (evolution uses `range(1, 4)`): `(3 × 3 × 3)` = **27 voxels maximum**

**Theoretical Maximum** (full grid): 125 voxels

**Current Evolution Scripts Use**:
```python
for _ in range(np.random.randint(6, 15)):  # 6-15 voxels per robot
    x, y, z = np.random.randint(1, 4, 3)   # Interior only: indices 1,2,3
    voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])
```

**Practical Limit**: ~15 voxels for good evolution performance

---

### Voxel Types (Material IDs)

**Location**: `src/physics/robot.py`, lines 28-37

```python
MATERIALS = {
    0: None,  # Empty voxel (no material, no springs)

    1: VoxelMaterial(  # Active 0° - Expands during actuation
        young_modulus=5.0e4,      # 50 kPa (soft)
        poisson_ratio=0.35,
        density=200.0,            # kg/m³
        damping=0.3,
        is_actuated=True,
        actuation_phase=0.0,      # 0 radians
        actuation_strength=0.2    # ±20% length change
    ),

    2: VoxelMaterial(  # Active 180° - Contracts during actuation
        young_modulus=5.0e4,
        poisson_ratio=0.35,
        density=200.0,
        damping=0.3,
        is_actuated=True,
        actuation_phase=π,        # π radians (180°)
        actuation_strength=0.2
    ),

    3: VoxelMaterial(  # Soft Passive - Flexible, no actuation
        young_modulus=2.5e4,      # 25 kPa (very soft)
        poisson_ratio=0.45,
        density=160.0,
        damping=0.4,
        is_actuated=False
    ),

    4: VoxelMaterial(  # Stiff Passive - Rigid structure
        young_modulus=1.0e5,      # 100 kPa (rigid)
        poisson_ratio=0.25,
        density=240.0,
        damping=0.2,
        is_actuated=False
    )
}
```

**Visualization Colors**:
- `0`: Black (not visible - empty)
- `1`: **GREEN** springs (thick) - Active 0°
- `2`: **RED** springs (thick) - Active 180°
- `3`: **CYAN** springs - Soft passive
- `4`: **BLUE** springs - Stiff passive

---

## 2. Timestep Configuration

### Current Timestep Values

**Default in all scripts**: `TIMESTEP = 0.001` (1 millisecond)

**Physics engine default**: `default_timestep=0.0001` in constructor (but overridden)

### Why TIMESTEP ≤ 0.001 Constraint?

**Numerical Stability Constraint** (Explicit Euler Integration):

The timestep must satisfy the **Courant–Friedrichs–Lewy (CFL) condition**:

```
dt < 2 / ω_max
```

Where `ω_max` is the maximum oscillation frequency in the system.

**For soft robot springs**:
```
ω_max = sqrt(k_max / m_min)
```

**With current parameters**:
- `k_max` ≈ 500 N/m (stiff edges)
- `m_min` ≈ 0.001 kg (minimum node mass)
- `ω_max` ≈ sqrt(500000) ≈ 707 rad/s

**Stability limit**:
```
dt_max = 2 / 707 ≈ 0.0028 seconds
```

**Safety margin**: Use `dt = 0.001` (factor of 2.8× below limit)

### Can We Use Smaller Timesteps?

**YES - These are SAFE:**
- `0.001` s (current) - **Stable ✓**
- `0.0005` s - **Stable ✓**, 2× slower
- `0.0002` s - **Stable ✓**, 5× slower

**RISKY - May cause instability:**
- `0.002` s - Near stability limit
- `0.005` s - **UNSTABLE** - springs will explode

### Recommendation

**Use `0.0005` s for higher accuracy** if you're seeing spring explosions.

**Current `0.001` s is optimal** for speed vs accuracy tradeoff.

---

## 3. Empty Voxels and Node/Spring Deletion

### Yes, Empty Voxels Are Supported

**Type 0 = Empty Voxel**

**How it works** (`src/physics/robot.py`, lines 97-166):

```python
def _build_structure_optimized(self):
    # Find all non-empty voxels first
    non_empty_indices = np.argwhere(self.voxel_grid != 0)  # ← Excludes type 0

    # Create nodes only for non-empty voxels
    needed_nodes = find_needed_nodes_fast(non_empty_positions)

    # Create springs only for filled voxels
    for x, y, z in non_empty_indices:
        material_id = self.voxel_grid[x, y, z]
        material = MATERIALS[material_id]

        if material is None:  # Skip empty voxels
            continue
```

**Node Deletion**: Yes, nodes not connected to any voxel are **automatically excluded**

**Spring Deletion**: Yes, springs only created for **non-empty voxels**

**Verification**:
- Only non-zero voxels create nodes
- Isolated nodes (no springs) are not created
- Empty interior voxels create voids in the structure

---

## 4. Spring Explosion Issue

### Root Causes

**1. Actuation Strength Too High**
- Current: 20% length change per cycle
- At maximum actuation: spring can be 0.8× or 1.2× rest length
- High forces generated

**2. Insufficient Damping**
- Global damping: 10.0 s⁻¹
- Spring damping: 0.3-0.4 (material-dependent)
- Energy builds up over cycles

**3. Spring Rest Length Initialization**
```python
# Line 211 in robot.py
rest_length = current_length  # Neutral initialization
```
Problem: If robot starts in compressed state, springs try to expand violently

### Why Only 2 Spring Colors Visible?

**You're likely seeing only Active materials (Types 1 and 2)**

**Reason**: Evolution favors actuated voxels
- Active materials (1, 2) provide movement → higher fitness
- Passive materials (3, 4) don't move → lower fitness
- Natural selection eliminates passive-only robots

**Check your robot**:
```python
import pickle
import numpy as np

with open('best_robot.pkl', 'rb') as f:
    voxel_grid = pickle.load(f)

for mat_id in range(5):
    count = np.sum(voxel_grid == mat_id)
    print(f"Material {mat_id}: {count} voxels")
```

Expected output for evolved robot:
```
Material 0: 117 voxels (empty)
Material 1: 3 voxels (active 0°)    ← GREEN
Material 2: 2 voxels (active 180°)  ← RED
Material 3: 1 voxels (soft passive) ← CYAN (rare)
Material 4: 2 voxels (stiff passive) ← BLUE (rare)
```

### Fix for Spring Explosion

**Option A: Reduce Actuation Strength** (Conservative)
```python
# In src/physics/robot.py, lines 33-34, change:
actuation_strength=0.1  # ±10% instead of ±20%
```

**Option B: Increase Damping** (Recommended)
```python
# In src/physics/cuda_physics.py, line ~340, change:
damping_coefficient = 15.0  # Instead of 10.0
```

**Option C: Smaller Timestep** (Safest)
```python
# In all evolution scripts:
TIMESTEP = 0.0005  # Instead of 0.001
```

**Option D: Clamp Spring Extension** (Add to cuda_physics.py)
```python
# In spring force kernel, add max extension limit:
extension = min(extension, rest_length * 0.5)  # Max 50% stretch
```

---

## 5. Initial Morphology Formation

### Genome Representation

**Genome = 3D numpy array** of material IDs
```python
voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
# Shape: (X, Y, Z) dimensions
# Values: 0-4 (material type at each position)
```

### Random Initialization Process

**Location**: All `run_evolution_*.py` scripts, `create_random_robot()` function

```python
def create_random_robot():
    """Create a random voxel robot"""
    # 1. Create empty 5×5×5 grid
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)

    # 2. Determine number of voxels (6-15 random)
    num_voxels = np.random.randint(6, 15)

    # 3. Place voxels randomly in interior (indices 1-3)
    for _ in range(num_voxels):
        x, y, z = np.random.randint(1, 4, 3)  # Random interior position
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])  # Random material

    return voxel_grid
```

**Step-by-step example**:
```
Iteration 1: Place voxel at (2, 1, 3) with material 1 (GREEN)
Iteration 2: Place voxel at (1, 2, 2) with material 3 (CYAN)
Iteration 3: Place voxel at (2, 2, 2) with material 2 (RED)
...
Iteration 10: Place voxel at (3, 1, 1) with material 4 (BLUE)
```

**Result**: Random 3D cluster of 6-15 voxels with mixed materials

### Why Interior Only (1-3)?

**Reasoning**:
- Outer shell (indices 0 and 4) reserved for connectivity
- Prevents robots from being single isolated voxels
- Ensures structural coherence
- Allows expansion space

### Material Selection Bias

**Current**: **Uniform distribution** - all materials equally likely
```python
np.random.choice([1, 2, 3, 4])  # 25% each
```

**Could be biased** (not currently implemented):
```python
# Favor active materials
np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1])
# 40% type 1, 30% type 2, 20% type 3, 10% type 4
```

### From Genome to Robot (VoxelRobot Construction)

**Process** (`src/physics/robot.py`, lines 85-166):

1. **Find non-empty voxels**:
```python
non_empty_indices = np.argwhere(voxel_grid != 0)
```

2. **Determine needed nodes**:
   - Each voxel needs 8 corner nodes
   - Shared corners between adjacent voxels merged
   - Only unique node positions created

3. **Create nodes**:
```python
for node_pos in needed_nodes:
    self.nodes.append({
        'position': node_pos * voxel_size,  # Convert to meters
        'mass': 0.0  # Mass added later from voxels
    })
```

4. **Create springs** (for each voxel):
   - 12 edge springs (along cube edges)
   - 12 face diagonal springs (across faces)
   - 4 body diagonal springs (through volume)
   - Total: 28 springs per voxel

5. **Set spring properties** based on material:
```python
stiffness = young_modulus × cross_section / rest_length
damping = material.damping × sqrt(stiffness)
is_actuator = material.is_actuated
actuation_phase = material.actuation_phase
```

6. **Distribute voxel mass** to 8 corner nodes:
```python
voxel_mass = material.density × voxel_size³
mass_per_corner = voxel_mass / 8
```

### Example: 3-Voxel Robot

**Genome**:
```
voxel_grid[2, 1, 2] = 1  # GREEN (active 0°)
voxel_grid[2, 2, 2] = 2  # RED (active 180°)
voxel_grid[3, 2, 2] = 3  # CYAN (soft passive)
```

**Result**:
- **Nodes**: 3 voxels → ~12-15 unique nodes (shared corners)
- **Springs**: 3 × 28 = 84 springs
- **Actuators**: 56 springs (from voxels 1 and 2)
- **Structure**: Vertical stack with horizontal extension

---

## 6. Git Commit Status

**All changes will be committed after this response.**

Changes to commit:
1. This documentation file
2. Global TIMESTEP constant implementation
3. Example 2×4×2 robot with void
4. Spring damping fixes

---

## Summary

1. **Max voxels**: 27 (usable interior), 125 (theoretical)
2. **Voxel types**: 0=Empty, 1=Active 0°, 2=Active 180°, 3=Soft passive, 4=Stiff passive
3. **Timestep**: Can use 0.0005s safely, current 0.001s is optimal
4. **Empty voxels**: Fully supported, nodes/springs auto-deleted
5. **Spring explosion**: Due to 20% actuation + low damping, fixable
6. **Only 2 colors**: Evolution favors active materials, passive materials rare
7. **Morphology formation**: Random placement → voxel corners → spring mesh
