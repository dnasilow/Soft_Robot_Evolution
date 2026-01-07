# Masses and Springs in MuJoCo Implementation

## Current Implementation

### Masses (Voxels)
Each voxel is represented as a **rigid body** in MuJoCo:
- **Geometry**: Box shape (10mm × 10mm × 10mm)
- **Mass**: 0.2g per voxel (density: 200 kg/m³)
- **Center of Mass**: At the geometric center of each voxel
- **Degrees of Freedom**: 6 per voxel (3 translation + 3 rotation via free joint)

**Code location**: `src/physics/mujoco_converter.py` lines 117-124
```python
<body name="voxel_i" pos="x y z">
  <geom type="box" size="0.005 0.005 0.005" mass="0.000200"/>
  <joint name="joint_i" type="free"/>
</body>
```

### Springs (Connections)
Adjacent voxels are connected by **equality constraints** (soft springs):
- **Type**: `connect` constraint
- **Stiffness**: Controlled by `solref` parameter (timeconst = 0.02, dampratio = 1)
- **Impedance**: Controlled by `solimp` parameter
- **Rest Length**: Implicitly defined by anchor points (currently both at `0 0 0`)

**Code location**: `src/physics/mujoco_converter.py` lines 135-147
```python
<connect body1="voxel_i" body2="voxel_j"
         anchor="0 0 0"
         solimp="0.9 0.95 0.001"
         solref="0.02 1"/>
```

## How Springs Work in MuJoCo

MuJoCo equality constraints create **soft springs** between bodies:

1. **Connect Constraint**: Creates a spring trying to keep two anchor points at the same position
2. **Anchor Points**: Currently both at `(0,0,0)` relative to each body's center
3. **Spring Force**: `F = -k*(distance) - b*(velocity)`
   - `k` (stiffness) derived from `solref[0]` (timeconst)
   - `b` (damping) derived from `solref[1]` (dampratio)

### Stiffness Calculation
From MuJoCo documentation:
```
k = 1 / (timeconst * timestep)
```
- Lower timeconst = Stiffer spring
- Higher timeconst = Softer spring

## Current Actuation Method

**Location**: `src/physics/mujoco_physics.py` lines 87-130

**Method**: Modulate constraint stiffness by changing `solref[0]` (timeconst)

```python
base_timeconst = 0.02
actuation_signal = amplitude * sin(2π * freq * time + phase)
modulated_timeconst = base_timeconst * (1.0 + actuation_signal)
model.eq_solref[i, 0] = modulated_timeconst
```

### Why Current Actuation Doesn't Show Visible Movement

**Problem**: Modulating stiffness alone doesn't create enough force to:
1. Overcome ground friction (μ = 1.0)
2. Move the robot's mass against gravity
3. Create visible oscillation when robot is at rest

**Evidence**:
- Constraint parameters DO oscillate (verified: 0.004 → 0.035)
- But voxel distances remain constant at 10mm (no movement)

## Why You Don't See Explicit Springs

**MuJoCo uses constraint-based physics**, not explicit spring elements:
- Springs are **mathematical constraints**, not physical objects
- They don't have visual representation by default
- The connection is IMPLICIT in the simulation

**To visualize springs, you would need to:**
1. Enable contact force visualization (`mjVIS_CONTACTFORCE`)
2. Add custom geoms to draw lines between connected voxels
3. Or use site-to-site connectors with visual elements

## Why Masses Don't Repeat

**Each voxel gets a unique body with unique mass**:
- Body 0: `world` (fixed ground)
- Body 1: `voxel_0` (mass at center)
- Body 2: `voxel_1` (mass at center)
- Body 3: `voxel_2` (mass at center)
- ...

**XML structure ensures uniqueness**:
```xml
<worldbody>
  <body name="voxel_0" pos="...">  <!-- Unique name -->
    <geom name="geom_0" mass="0.0002"/>
    <joint name="joint_0" type="free"/>
  </body>
  <body name="voxel_1" pos="...">  <!-- Unique name -->
    <geom name="geom_1" mass="0.0002"/>
    <joint name="joint_1" type="free"/>
  </body>
</worldbody>
```

Each body has:
- Unique name: `voxel_0`, `voxel_1`, etc.
- Unique geom: `geom_0`, `geom_1`, etc.
- Unique joint: `joint_0`, `joint_1`, etc.
- Independent mass at its center

## Status of Requested Features

### 1. ✅ Actuation (sinusoidal control)
**Status**: IMPLEMENTED but not visually effective
- Code exists in `MuJoCoPhysicsEngine.apply_actuation()`
- Modulates constraint stiffness at 2Hz
- Constraint parameters DO oscillate
- But robot doesn't move visibly (friction too high)

**Fix needed**: Change approach from stiffness modulation to rest-length modulation

### 2. ❌ Force sensors and contact visualization
**Status**: NOT YET IMPLEMENTED
- MuJoCo has force sensors (`<sensor>` in XML)
- Contact visualization available via viewer flags
- Need to add to converter and visualization scripts

### 3. ✅ MuJoCoPhysicsEngine wrapper
**Status**: IMPLEMENTED
- File: `src/physics/mujoco_physics.py`
- Class: `MuJoCoPhysicsEngine`
- Methods: `load_robot()`, `step()`, `get_fitness()`, `apply_actuation()`

## Recommended Next Steps

1. **Fix actuation visibility**:
   - Switch from stiffness modulation to actuator-based approach
   - Use MuJoCo motors/actuators that apply forces
   - Increase actuation amplitude or reduce friction

2. **Add explicit spring visualization**:
   - Create custom geoms (capsules) between voxel centers
   - Update their length/color based on constraint forces
   - Or use MuJoCo sites with connecting tendons

3. **Implement force sensors**:
   - Add `<sensor type="force">` to XML
   - Read sensor values during simulation
   - Visualize forces as arrows or color mapping
