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

## Issue #2: Ground Position Clamping Kills Oscillation (FIXED: Dec 3, 2024)

### Symptom
Bottom surface of cubes does NOT oscillate when in contact with ground, while top surface oscillates normally.

### Test Results
**Before fix (hard position clamping):**
```
Bottom nodes: 0.00mm oscillation (FROZEN at Y=0.0000m)
Top nodes: 50.49mm oscillation (Y=0.982m-1.009m)
Bottom velocity: -3.433 m/s (trying to move down)
Bottom position: 0.0000m (CLAMPED - cannot move!)
```

### Root Cause
**Hard position clamping at line 318:** `self.d_positions[:, 1] = cp.maximum(..., 0.0)`

This hard constraint prevented nodes from temporarily penetrating ground, which is necessary for:
1. Natural spring compression/expansion at boundary
2. Realistic soft-body ground contact
3. Visible bounce behavior

### Solution
**Replaced hard clamping with spring-based ground contact:**
- Ground acts as very stiff spring: F = k × penetration_depth
- Mass-adaptive stiffness: k = 100000 N/(m·kg) per node
- Ground damping: c = 1000 N·s/(m·kg) per node
- Allows 1-3mm penetration for realistic soft contact

### Impact
**FIXED** - Now produces realistic bounce behavior:
- 1m drop: 23 bounces, first bounce = 9.7cm
- 2m drop: 19 bounces, first bounce = 6.9cm
- 5m drop: 14 bounces, first bounce = 3.8cm

**Location**: cuda_physics.py:312-358

**Test**: `python test_bounce_heights.py`

---

## Issue #3: Spring Forces Add Energy to System (ACTIVE - Dec 4, 2024)

### Symptom
Robots gain energy over time, bouncing progressively higher despite damping.

### Test Results
**Single cube (160kg) dropped from 1m with damping=10 s⁻¹:**
```
Bounce 1: 14.9cm above rest
Bounce 2: 67.1cm above rest  (4.5× higher!)
Bounce 3: 125.9cm above rest (8.5× higher!)
Bounce 4: 188.7cm above rest (12.7× higher!)
```

Expected: Each bounce should be LOWER (energy dissipation)
Actual: Each bounce is HIGHER (energy creation!)

### Root Cause
Spring force calculation has numerical error that adds energy to the system.

**Evidence:**
1. Damping 0.1 s⁻¹: Robots fly upward indefinitely
2. Damping 2.0 s⁻¹: Excessive bouncing (7m bounce from 5m drop)
3. Damping 10.0 s⁻¹: Bounces increase over time (shown above)

The high damping (10 s⁻¹) has been **masking** this bug by dissipating the gained energy quickly enough to prevent runaway behavior.

### Why This Happens
Possible causes in cuda_physics.py spring force calculation:
1. **Sparse matrix force distribution** (line 228-231): May have sign errors
2. **Spring rest length initialization**: Springs may not be at equilibrium initially
3. **Floating-point accumulation**: Small errors compound over thousands of timesteps
4. **Force distribution to nodes**: Equal/opposite force law may not be perfectly conserved

### Impact
- **MEDIUM**: Physics works for short simulations (evolution fitness evaluation)
- **HIGH**: Long simulations show unrealistic energy gain
- **WORKAROUND**: High damping (10 s⁻¹) keeps energy bounded

### Current Status
**REQUIRES INVESTIGATION** - Damping = 10 s⁻¹ provides stable behavior but:
- Terminal velocity limited to 0.98 m/s (unrealistic)
- Cannot reduce damping without exposing energy-gain bug
- Spring-based ground contact makes issue more visible

### Next Steps
1. Add energy conservation checks (KE + PE + spring PE should be constant - damping)
2. Verify force distribution matrix conserves momentum
3. Check spring initialization (are rest lengths = current lengths at t=0?)
4. Test with explicit Euler vs implicit integration

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
