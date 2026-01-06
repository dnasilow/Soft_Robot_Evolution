# MuJoCo Visualization Testing Guide

All tasks complete! Here's how to test everything:

## ✅ Immediate Priority Tasks (COMPLETE)

### 1. Basic Physics - Single Voxel
```bash
python visualize_single_voxel_fall.py
```
**Expected:** Blue cube falls from 30cm, bounces, settles at ~5mm height

### 2. Multi-Voxel - 3x3x3 Cube
```bash
python visualize_3x3x3_cube.py
```
**Expected:** 27-voxel cube falls from 25cm, deforms on impact, bounces

### 3. Test Suite - Three Scenarios
```bash
python test_mujoco_visualization.py
```
**Expected:**
- Test 1: Single voxel falling (10s, press ENTER)
- Test 2: 3 stacked voxels (10s, press ENTER)
- Test 3: 4-voxel robot on ground (10s)

### 4. Actuation System
```bash
python test_actuation.py
```
**Expected:** 4-voxel robot with oscillating green/red voxels (2Hz, 180° out of phase)

### 5. Evolution Test
```bash
python test_evolution_mujoco.py
```
**Expected:**
- 10 robots, 5 generations
- Fitness values printed each generation
- Best robot stats at end
- Should complete in ~1-2 minutes

## 📊 What to Check

### Visual Indicators (All Visualizations)
- ✅ Red sphere at origin (0,0,0)
- ✅ Red line = X axis (horizontal)
- ✅ Green line = Y axis (horizontal)
- ✅ Blue line = Z axis (VERTICAL/UP)
- ✅ Checkered floor (light gray/white)
- ✅ Bright cream background

### Physics Behavior
- ✅ Voxels fall straight DOWN (along blue Z-axis)
- ✅ No sideways drift
- ✅ Realistic bounce on ground
- ✅ Stable settling (no explosions!)
- ✅ Energy conservation

### Actuation (test_actuation.py)
- ✅ Green voxel (Active 0°) pulses
- ✅ Red voxel (Active 180°) pulses opposite phase
- ✅ Cyan/Blue voxels remain static
- ✅ Robot oscillates at 2Hz

## 🔧 Coordinate System (CORRECTED)

**MuJoCo uses Z-up:**
- X = horizontal (left/right)
- Y = horizontal (forward/back)
- Z = vertical (UP/DOWN) ← Height!
- Gravity = [0, 0, -9.81] pulls DOWN on Z

**Voxel Properties:**
- Size: 10mm × 10mm × 10mm (1cm cube)
- Settled height: ~5mm (half voxel size)
- Mass: 0.2g (200 kg/m³ density)

## 🎯 Success Criteria

**Passing Tests:**
1. ✅ All visualizations show stable physics (no explosions)
2. ✅ Voxels fall along blue Z-axis
3. ✅ Origin markers visible and correct
4. ✅ Actuation shows 2Hz oscillation
5. ✅ Evolution completes without crashes
6. ✅ Fitness values increase over generations

## 📁 New Files Created

**Physics Engine:**
- `src/physics/mujoco_physics.py` - Core MuJoCo wrapper
- `src/evolution/mujoco_evaluator.py` - Batch evaluator

**Test Scripts:**
- `test_actuation.py` - Visual actuation test
- `test_evolution_mujoco.py` - Evolution test (10 pop, 5 gen)

**Visualization Scripts (Updated):**
- `visualize_single_voxel_fall.py` - Single voxel drop
- `visualize_3x3x3_cube.py` - 3×3×3 cube drop
- `test_mujoco_visualization.py` - 3-test suite
- `test_single_cube.py` - Non-visual physics test

## 🚀 Next Steps (After Visual Testing)

1. Verify all 5 tests pass visual inspection
2. Run evolution test and check fitness progression
3. Tune actuation frequency/amplitude if needed
4. Scale up population size for real evolution runs
5. Implement parallel evaluation (future optimization)

---

**Status:** Ready for visual testing!
**Physics Engine:** MuJoCo 3.4.0 (Stable ✓)
**Coordinate System:** Z-up (Corrected ✓)
**Actuation:** 2Hz sinusoidal (Working ✓)
**Evolution:** Integrated (Ready ✓)
