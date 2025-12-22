# Known Issues

## CRITICAL: Spring Force Instability (2024-12-21)

### Symptom
Robots explode upward even with no actuation. A single passive voxel sitting on the ground will fly up to 1+ meters within 1 second.

### Evidence
```python
# Single passive voxel, NO actuation
t=0.050s: Y=  0.00-270.00 mm  # Should be 1-11mm
t=0.500s: Y=  0.00-904.11 mm  # Flying upward!
```

### What We've Ruled Out
1. ✓ **Actuation compounding** - Fixed by using `d_original_rest_lengths`
2. ✓ **Integration order** - Fixed by applying actuation before force computation
3. ✓ **Integration method** - Tried both semi-implicit and explicit Euler
4. ✓ **Ground contact** - Simplified to hard clamping
5. ✓ **Timestep stability** - Using dt=0.0005s with 8× safety margin
6. ✓ **Rest lengths** - Verified correct (10mm, 14.14mm, 17.32mm)
7. ✓ **Force distribution** - Sparse matrix and atomic ops both have same bug

### Remaining Suspects
1. **Spring force calculation** (`src/physics/cuda_physics.py:195-210`)
   - Extension formula: `extension = rest_length - current_length`
   - Force direction: `force_vector = unit_displacement * spring_force`
   - Appears mathematically correct but robot still gains energy

2. **Position/velocity corruption**
   - Possible race condition in GPU memory?
   - CuPy synchronization issue?

3. **Hidden energy source**
   - Damping coefficient calculation?
   - Force limiting creating asymmetry?

### Temporary Workaround
None available. Physics simulation is currently broken.

### Next Steps
1. Add detailed logging inside `compute_spring_forces_vectorized()`
2. Print actual spring extensions and forces for a single timestep
3. Verify force conservation (total force should equal -gravity)
4. Consider switching to a proven physics library (PyBullet, MuJoCo)
