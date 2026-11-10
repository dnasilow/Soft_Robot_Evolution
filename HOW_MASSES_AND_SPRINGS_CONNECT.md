# How Masses and Springs Connect - Technical Explanation

## Answer to Your Questions

### Question 1: Does each corner of a cube contain only 1 mass point?

**YES - Each voxel has exactly ONE mass point at its center.**

For a 2×2×2 cube:
- **8 voxels** (corner positions)
- **8 mass points** (one per voxel, at geometric center)
- Each mass point is at coordinates: `(x, y, z)` of the voxel center

**No repetition** - each voxel gets:
- Unique body name: `voxel_0`, `voxel_1`, ..., `voxel_7`
- Unique mass: 0.2g at center
- Unique free joint: 6 DOF (3 translation + 3 rotation)

### Question 2: How are mass points connected by springs?

**CURRENT IMPLEMENTATION: ONLY EDGE NEIGHBORS (Face-Adjacent)**

**Code logic** (from `src/physics/mujoco_converter.py` lines 140-147):
```python
# Check if voxels are adjacent
dist = np.linalg.norm(v1['pos'] - v2['pos'])

# Edge connection
if abs(dist - voxel_size) < voxel_size * 0.01:
    # Create spring connection
```

**This means:**
- Only voxels separated by exactly `voxel_size` (10mm) are connected
- **NO diagonal connections** (those would be at distance √2 × 10mm or √3 × 10mm)
- Only **face-to-face neighbors** (sharing a square face)

## Visual Diagram - 2×2×2 Cube

```
     7----------6
    /|         /|
   / |        / |
  3----------2  |
  |  4-------|--5
  | /        | /
  |/         |/
  0----------1

Legend:
  0-7: Voxel IDs (each has 1 mass point at center)
  ---: Springs (edge connections only)
```

### Spring List (12 total):
```
X-direction (4 springs):
  0 ↔ 1    (bottom front edge)
  2 ↔ 3    (top front edge)
  4 ↔ 5    (bottom back edge)
  6 ↔ 7    (top back edge)

Y-direction (4 springs):
  0 ↔ 2    (left bottom edge)
  1 ↔ 3    (right bottom edge)
  4 ↔ 6    (left top edge)
  5 ↔ 7    (right top edge)

Z-direction (4 springs):
  0 ↔ 4    (front left vertical)
  1 ↔ 5    (front right vertical)
  2 ↔ 6    (back left vertical)
  3 ↔ 7    (back right vertical)
```

## What's NOT Connected (Diagonals)

### Face Diagonals (NOT connected):
```
Distance: √2 × voxel_size ≈ 14.14mm

Examples:
  0 ↔ 3  (front face diagonal)
  0 ↔ 5  (bottom face diagonal)
  0 ↔ 6  (left face diagonal)
```

### Space Diagonals (NOT connected):
```
Distance: √3 × voxel_size ≈ 17.32mm

Examples:
  0 ↔ 7  (main diagonal)
  1 ↔ 6  (opposite diagonal)
```

## Connection Pattern for Different Voxel Types

### Corner Voxel (e.g., voxel_0 in 3×3×3 cube):
- **3 edge neighbors** → 3 springs
- Example: 0 connects to 1, 2, 4

### Edge Voxel (e.g., center of edge in 3×3×3):
- **4 edge neighbors** → 4 springs
- 2 along the edge + 2 perpendicular

### Face Voxel (e.g., center of face in 3×3×3):
- **5 edge neighbors** → 5 springs
- 4 in the plane + 1 perpendicular

### Interior Voxel (e.g., center of 3×3×3):
- **6 edge neighbors** → 6 springs
- 2 in each direction (±X, ±Y, ±Z)

## How Springs Work

### Each Spring (Equality Constraint):
```xml
<connect body1="voxel_i" body2="voxel_j"
         anchor="0 0 0"
         solimp="0.9 0.95 0.001"
         solref="0.02 1"/>
```

**Parameters:**
- `anchor="0 0 0"`: Connection point at center of each voxel
- `solref="0.02 1"`: Stiffness/damping (timeconst=0.02, dampratio=1)
- `solimp`: Constraint impedance parameters

**Physical Behavior:**
- Acts like a **soft spring** trying to keep centers at fixed distance
- Rest length = initial separation = `voxel_size` = 10mm
- Force = `F = -k*(Δx) - b*(Δv)`
  - `k` (stiffness) from `solref[0]`
  - `b` (damping) from `solref[1]`

### Actuation Modulation:
```python
# Current approach (in mujoco_physics.py)
base_timeconst = 0.02
actuation_signal = amplitude * sin(2π * freq * time + phase)
modulated_timeconst = base_timeconst * (1.0 + actuation_signal)
```

**Effect:**
- Lower timeconst → Stiffer spring → Pulls voxels closer
- Higher timeconst → Softer spring → Allows voxels to separate
- **BUT**: Doesn't change rest length, just compliance

## Why Each Connection is Unique (No Repetition)

The code uses **nested loop with uniqueness check**:
```python
for i, v1 in enumerate(voxels):
    for j, v2 in enumerate(voxels):
        if j <= i:  # <-- Prevents duplicates and self-connections
            continue
```

**This ensures:**
- `i < j` always (ordered pairs)
- Each pair checked only once
- No self-connections (i ≠ j)
- No duplicate springs

**Example:** For voxels 0 and 1:
- Checks: (0,1) ✓
- Skips: (1,0) ✗ (because 0 ≤ 1 fails)
- Result: Only ONE spring between 0 and 1

## Comparison: Current vs Full Connection Scheme

### Current (Edge-Only):
```
2×2×2 cube: 12 springs
3×3×3 cube: 54 springs
5×5×5 cube: 300 springs

Advantages:
  + Simpler structure
  + Fewer constraints = faster simulation
  + Mimics real soft robot materials

Disadvantages:
  - Less structural rigidity
  - Can deform more easily
  - No shear resistance on faces
```

### If Diagonals Were Included:
```
2×2×2 cube would have:
  - 12 edge springs (current)
  - 24 face diagonal springs
  - 4 space diagonal springs
  Total: 40 springs (3.3× more!)

Advantages:
  + Much stiffer structure
  + Better shape preservation
  + Shear resistance

Disadvantages:
  - More complex
  - Slower simulation
  - Less realistic for soft robots
```

## Recommendation for Better Oscillation Visualization

**Current issue:** Ground friction prevents movement

**Solutions:**

1. **✓ Suspend in air** (already doing in new script)
   - Start at height with no ground contact
   - Cube can freely oscillate

2. **✓ Increase amplitude to ±100%** (already doing)
   - Maximum stiffness modulation
   - Larger force variations

3. **✓ Use 5×5×5 cube** (new script created)
   - More mass = more inertia = bigger movements
   - More springs = more cumulative force

4. **Consider adding diagonal springs** (future enhancement)
   - Would create more rigid structure
   - Oscillation would be more coordinated
   - Easier to see "breathing" motion

## Summary

| Question | Answer |
|----------|--------|
| **One mass per voxel?** | YES - at geometric center |
| **Connected to neighbors?** | YES - but ONLY face-adjacent (edge) neighbors |
| **Diagonal connections?** | NO - only distance = voxel_size |
| **Each connection unique?** | YES - loop ensures i < j (no duplicates) |
| **Can see oscillation?** | SHOULD with 5×5×5 suspended cube at ±100% amplitude |
