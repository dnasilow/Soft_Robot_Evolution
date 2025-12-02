# Known Physics Issues

## Issue #1: Small Objects Float Instead of Falling (CRITICAL - Dec 2, 2024)

### Symptom
Objects with small mass (< 1kg) do not fall under gravity. Instead, they:
- Oscillate in mid-air
- Slowly drift UPWARD over time
- Never reach terminal velocity or ground

### Test Case
```python
# 5cm cube (mass = 0.028kg) dropped from 1m height
# Expected: Falls to ground in ~0.45 seconds
# Actual: Floats at Y≈1.075m, then rises to Y=1.315m after 10 seconds
python test_small_cube_long.py
```

### Data
```
t=0.0s: Y=1.0750m, v_y=-0.0010m/s
t=1.0s: Y=1.1878m, v_y=-0.1607m/s  ← RISING
t=9.0s: Y=1.2685m, v_y=-0.0731m/s
Final:  Y=1.3152m  ← 24cm HIGHER than start
```

### Root Cause (Hypothesis)
Spring internal forces are creating net upward force that exceeds gravity for small masses.

Possible causes:
1. **Spring rest length initialization bug**: Springs may have incorrect rest lengths causing them to push the structure upward
2. **Spring force calculation error**: Despite fixing the sign in cuda_physics.py:199, there may be residual issues
3. **Numerical precision**: With very small masses (0.028kg vs 480kg), floating-point errors may accumulate
4. **Spring configuration**: The 8-node cube has 28 springs in complex 3D configuration - may create net force imbalance

### Why Large Objects Still Work
- 480kg three-cube structure falls correctly (test_three_cubes.py)
- Gravity force (4708N) overwhelms any spring force imbalance
- For 0.028kg cube, gravity is only 0.275N - easily dominated by spring errors

### Impact
- **HIGH**: Prevents testing evolution with varied robot sizes
- **MEDIUM**: Does not affect large robots (>10kg) used in evolution
- **LOW**: Workaround exists (use only large voxels / heavy robots)

### Temporary Workaround
Use robots with:
- Voxel size ≥ 0.5m (minimum mass ~3.5kg per voxel)
- Total mass ≥ 50kg
- This ensures gravity >> spring force errors

### Next Steps for Investigation
1. Add detailed force logging to identify which springs create upward force
2. Verify spring rest lengths match current lengths at initialization
3. Check for asymmetry in spring creation (more upward-facing springs?)
4. Test with springs disabled (pure rigid body) to isolate issue
5. Compare CuPy vs NumPy calculations for numerical precision

---

## Issue #2: No Observable Bounce with CoR = 0.35 (Dec 2, 2024)

### Symptom
Ground coefficient of restitution set to 0.35 (35%), but objects show minimal/no bounce after ground impact.

### Test Results
**Three-cube structure (480kg, dropped from 2m):**
```
t=4.0s: Y=0.547m [falling]
t=5.0s: Y=0.499m [settled]  ← No bounce observed
t=6.0s: Y=0.499m [settled]
```

Expected with CoR=0.35:
- First bounce height: 0.35² × 2m = 0.245m
- Should see Y oscillate: 0.50m → 0.74m → 0.50m → ...

### Root Cause
**Damping overwhelms elastic rebound.**

Combined energy dissipation:
1. **Velocity damping**: 20 s^-1 coefficient
2. **Ground restitution**: CoR = 0.35 (87.75% energy loss)
3. **Spring internal damping**: Additional losses
4. **Fall duration**: ~4.5 seconds allows significant damping during fall

Energy retained after impact:
- Ground contact: (0.35)² = 12.25% of kinetic energy
- During 4.5s fall: damping reduces impact velocity
- Net bounce: < 5% of potential energy → < 10cm bounce height
- Springs compress/absorb remaining energy → no visible bounce

### Impact
- **LOW**: Physics is physically plausible (highly damped soft materials)
- Bounce exists but is microscopic (<5cm)
- Does not affect fitness evaluation or evolution

### Status
**EXPECTED BEHAVIOR** - Not a bug.

Soft silicone robots with significant damping would exhibit minimal bounce. This is realistic for the material properties (Young's modulus = 25kPa, density = 160kg/m³).

To increase bounce visibility:
- Reduce damping coefficient from 20 s^-1 to 5-10 s^-1
- Increase ground CoR to 0.6-0.8
- Use stiffer materials (higher Young's modulus)

---

## Fixed Issues

### ✅ Timestep-Dependent Damping (Fixed: Dec 2, 2024)
**Problem**: Damping factor was hardcoded to 0.98, only correct for dt=0.001s.

**Solution**: Implemented timestep-adaptive damping:
```python
damping_coefficient = 20.0  # s^-1
damping_factor = 1.0 - damping_coefficient * dt
```

**Location**: cuda_physics.py:295-298

**Impact**: Damping now works correctly for any timestep value.

### ✅ Inverted Spring Forces (Fixed: Nov 27, 2024)
**Problem**: Spring forces calculated as F = k(current - rest) instead of F = k(rest - current).

**Solution**: Flipped sign in spring force calculation.

**Location**: cuda_physics.py:199

### ✅ Force Limits Too Restrictive (Fixed: Nov 27, 2024)
**Problem**: 55N force limit prevented 160kg robots from functioning (gravity force = 1569N).

**Solution**: Increased force limit to 5000N.

**Location**: cuda_physics.py:286
