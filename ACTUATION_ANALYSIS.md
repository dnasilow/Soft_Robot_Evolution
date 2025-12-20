# Actuation Strength Analysis - Per Spring Detailed Breakdown

## Question: How Much Actuation Per Spring?

**Answer: ±20% of rest length** (configurable)

---

## Location in Code

**Primary actuation application**: `src/physics/cuda_physics.py`, line 268-272

```python
def apply_actuator_forces_vectorized(self):
    # Vectorized sinusoidal actuation
    actuation = cp.sin(self.time * 2 * cp.pi * self.actuation_frequency + phases) * signals

    # Modify rest lengths (±20% actuation as per Lipson)
    original_lengths = self.d_rest_lengths[spring_ids]
    self.d_rest_lengths[spring_ids] = original_lengths * (1.0 + 0.2 * actuation)
```

**Actuation strength constant**: `src/physics/robot.py`, line 15

```python
actuation_strength: float = 0.2  # ±20% expansion
```

**Global constant**: `src/physics/constants.py`, line 38

```python
ACTUATION_STRENGTH = 0.2  # ±20% of rest length
```

---

## Detailed Breakdown

### Per Spring Actuation

**For a spring with rest length L₀:**

1. **At time t = 0 (actuation = +1)**:
   ```
   new_rest_length = L₀ × (1.0 + 0.2 × (+1))
                   = L₀ × 1.2
                   = 120% of original
   ```
   **Change**: +20% expansion

2. **At time t = 0.25s (actuation = 0)**:
   ```
   new_rest_length = L₀ × (1.0 + 0.2 × 0)
                   = L₀ × 1.0
                   = 100% (neutral)
   ```
   **Change**: 0% (neutral position)

3. **At time t = 0.5s (actuation = -1)**:
   ```
   new_rest_length = L₀ × (1.0 + 0.2 × (-1))
                   = L₀ × 0.8
                   = 80% of original
   ```
   **Change**: -20% contraction

### Full Oscillation Cycle

**For 1 Hz actuation (1 cycle per second):**

```
Time  | Sin(2πft) | Actuation | Rest Length | % Change
------|-----------|-----------|-------------|----------
0.00s |  0.0      |  0.0      | 1.00 × L₀   |   0%
0.125s|  +1.0     |  +1.0     | 1.20 × L₀   |  +20%
0.25s |  0.0      |  0.0      | 1.00 × L₀   |   0%
0.375s|  -1.0     |  -1.0     | 0.80 × L₀   |  -20%
0.50s |  0.0      |  0.0      | 1.00 × L₀   |   0%
0.625s|  +1.0     |  +1.0     | 1.20 × L₀   |  +20%
0.75s |  0.0      |  0.0      | 1.00 × L₀   |   0%
0.875s|  -1.0     |  -1.0     | 0.80 × L₀   |  -20%
1.00s |  0.0      |  0.0      | 1.00 × L₀   |   0% (cycle complete)
```

**Total range**: 0.8× to 1.2× rest length = **40% peak-to-peak**

---

## Material-Dependent Actuation

### Active 0° Material (Type 1 - GREEN)

**Actuation phase**: 0 radians

```python
actuation = sin(2π × 1.0 × t + 0)
         = sin(2πt)
```

**Behavior**:
- Starts at neutral (t=0)
- **Expands** at t=0.125s (maximum expansion)
- Returns to neutral at t=0.25s
- **Contracts** at t=0.375s (maximum contraction)
- Completes cycle at t=1.0s

**Spring length change**:
```
L(t) = L₀ × (1.0 + 0.2 × sin(2πt))
```

### Active 180° Material (Type 2 - RED)

**Actuation phase**: π radians (180°)

```python
actuation = sin(2π × 1.0 × t + π)
         = -sin(2πt)
```

**Behavior**:
- Starts at neutral (t=0)
- **Contracts** at t=0.125s (opposite of type 1)
- Returns to neutral at t=0.25s
- **Expands** at t=0.375s
- Completes cycle at t=1.0s

**Spring length change**:
```
L(t) = L₀ × (1.0 - 0.2 × sin(2πt))
     = L₀ × (1.0 + 0.2 × sin(2πt + π))
```

**Key insight**: Type 1 and Type 2 oscillate **180° out of phase** (opposite)

### Passive Materials (Type 3, 4 - CYAN, BLUE)

**Actuation**: None

```python
is_actuated = False
# Rest length never changes
L(t) = L₀  (constant)
```

---

## Example: Numerical Values

### Edge Spring (typical)

**Original specifications**:
- **Voxel size**: 0.01 m
- **Edge length**: 0.01 m
- **Rest length**: L₀ = 0.01 m

**During actuation cycle**:

| Time  | Type 1 (0°) Length | Type 2 (180°) Length | Change (mm) |
|-------|-------------------|---------------------|-------------|
| 0.00s | 0.0100 m         | 0.0100 m            | 0.0 mm      |
| 0.125s| **0.0120 m**     | **0.0080 m**        | ±2.0 mm     |
| 0.25s | 0.0100 m         | 0.0100 m            | 0.0 mm      |
| 0.375s| **0.0080 m**     | **0.0120 m**        | ±2.0 mm     |
| 0.50s | 0.0100 m         | 0.0100 m            | 0.0 mm      |

**Peak displacement**: ±2 mm for 1 cm voxels

### Body Diagonal Spring

**Original specifications**:
- **Diagonal length**: √3 × 0.01 = 0.01732 m
- **Rest length**: L₀ = 0.01732 m

**During actuation cycle**:

| Time  | Type 1 (0°) Length | Type 2 (180°) Length | Change (mm) |
|-------|-------------------|---------------------|-------------|
| 0.125s| **0.02078 m**    | **0.01386 m**       | ±3.46 mm    |
| 0.375s| **0.01386 m**    | **0.02078 m**       | ±3.46 mm    |

**Peak displacement**: ±3.46 mm for body diagonals

---

## Forces Generated

### Spring Force Formula

```
F = k × Δx
```

Where:
- `k` = spring stiffness (material-dependent)
- `Δx` = displacement from rest length

### Example Force Calculation

**Active 0° edge spring** (Type 1):
- **Stiffness**: k ≈ 500 N/m (typical for edge springs)
- **Rest length**: L₀ = 0.01 m
- **At maximum actuation** (t=0.125s):
  - Actuated rest length: 0.012 m
  - If spring compressed to actual length 0.01 m:
  - Extension = 0.01 - 0.012 = -0.002 m
  - **Force** = 500 × 0.002 = **1.0 N** (pushing outward)

**Active 180° edge spring** (Type 2):
- At same moment (t=0.125s):
  - Actuated rest length: 0.008 m
  - If spring stretched to actual length 0.01 m:
  - Extension = 0.01 - 0.008 = +0.002 m
  - **Force** = 500 × 0.002 = **1.0 N** (pulling inward)

**Combined effect**: Antagonistic muscle pairs create directed motion

---

## Impact on Robot Behavior

### Locomotion Mechanism

**4-voxel robot** (2× type 1, 2× type 2):

1. **t = 0.125s**: Type 1 expands (+20%), Type 2 contracts (-20%)
   - Robot bends in one direction
   - Center of mass shifts

2. **t = 0.375s**: Type 1 contracts (-20%), Type 2 expands (+20%)
   - Robot bends in opposite direction
   - Center of mass shifts back (net displacement if on ground)

3. **Friction with ground**: Asymmetric stick-slip creates net motion

**Result**: Wave-like or inchworm locomotion

### Energy Input

**Energy per actuation cycle** (approximate):

```
E = (1/2) × k × (ΔL)²
```

For one edge spring:
```
E = 0.5 × 500 × (0.002)² = 0.001 J per spring per cycle
```

For 28 springs per voxel × 2 active voxels × 56 actuated springs:
```
E_total ≈ 56 × 0.001 = 0.056 J per cycle
```

At 1 Hz: **Power ≈ 0.056 W** for small robot

---

## Configurability

### How to Change Actuation Strength

**Option 1: Modify robot.py material definition** (line 15, 33-34):
```python
# Conservative (less force, more stable)
actuation_strength: float = 0.1  # ±10%

# Aggressive (more force, less stable)
actuation_strength: float = 0.3  # ±30%
```

**Option 2: Modify constants.py** (line 38):
```python
# Then update robot.py to use this constant
ACTUATION_STRENGTH = 0.15  # ±15%
```

### Trade-offs

| Strength | Expansion Range | Force | Stability | Locomotion Speed |
|----------|----------------|-------|-----------|------------------|
| ±10%     | 0.9× - 1.1×    | Low   | High ✓    | Slow             |
| ±15%     | 0.85× - 1.15×  | Medium| Good      | Moderate         |
| **±20%** | **0.8× - 1.2×**| **High**| **OK**  | **Fast** ✓       |
| ±30%     | 0.7× - 1.3×    | Very high| Risky  | Very fast        |

**Current choice (±20%)**: Based on Lipson et al. soft robotics research, optimal balance

---

## Spring Extension Clamping

**New safety feature** (prevents explosions):

**Location**: `src/physics/cuda_physics.py`, lines 201-206

```python
# Clamp spring extensions to prevent explosions
max_extension = rest_lengths_safe * 0.8  # Allow 80% compression
min_extension = -rest_lengths_safe * 0.2  # Allow 20% stretch (1.2× total)
extensions = cp.clip(extensions, min_extension, max_extension)
```

**Limits**:
- **Maximum compression**: 0.2× rest length (80% compression)
- **Maximum stretch**: 1.2× rest length (20% extension)

**Interaction with actuation**:
- Actuation changes rest length: L_rest(t) = L₀ × (1 + 0.2 × sin(...))
- Extension is: extension = L_rest - L_current
- Clamping prevents: extension > 0.8×L_rest OR extension < -0.2×L_rest
- This limits actual spring length to reasonable range

**Why 1.2× instead of 2.0×?**
- **More realistic**: Real materials don't stretch 100%
- **More stable**: Smaller forces prevent numerical explosions
- **Sufficient**: 20% stretch matches actuation range
- **Tested**: Works with ±20% actuation without issues

---

## Summary

**Per Spring Actuation**:
- **Active materials**: ±20% of rest length
- **Oscillation**: Sinusoidal at 1 Hz (default)
- **Peak-to-peak**: 40% total range (0.8× to 1.2×)
- **Phase difference**: 180° between type 1 and type 2
- **Passive materials**: 0% (no actuation)

**Physical values** (1 cm voxels):
- Edge springs: ±2 mm displacement
- Diagonal springs: ±3.46 mm displacement
- Forces: ~1 N per spring at peak
- Power: ~0.05 W for small robot

**Safety limits**:
- Maximum stretch: 1.2× rest length (20%)
- Maximum compression: 0.2× rest length (80%)
- Prevents spring explosions while allowing full actuation range
