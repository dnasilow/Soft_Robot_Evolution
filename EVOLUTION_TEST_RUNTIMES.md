# Evolution Test Runtime Estimates

## Performance Baseline
Based on **test_true_parallel.py** benchmark:
- **Throughput**: 0.42 robots/second (11.5x speedup vs sequential)
- **GPU**: NVIDIA with 21.5GB VRAM, CuPy sparse matrices
- **Simulation**: 5000 steps @ 0.001s timestep = 5 seconds per robot

---

## Test Files & Expected Runtimes

### 1. test_true_parallel.py ✓ TESTED
**Purpose**: Benchmark true parallel GPU evaluation

**Parameters**:
- 10 robots (single batch)
- 5 actuation cycles (5 seconds simulation)
- No evolution, just evaluation

**Expected Runtime**: **~24 seconds**

**Actual Runtime**: 23.9 seconds ✓

**Status**: ✓ WORKING - All 4 validation checks passed

---

### 2. test_evolution_quick.py ⚠ USES OLD EVALUATOR
**Purpose**: Quick CUDA performance validation

**Parameters**:
- 10 robots (single batch)
- 5 actuation cycles
- Uses: TurboChargedBatchEvaluator (SEQUENTIAL!)

**Expected Runtime**: **~276 seconds (4.6 minutes)** - SLOW!

**Issues**:
- Uses old sequential batch evaluator
- Not actually parallel despite name
- 11.5x slower than true parallel version

**Recommendation**: Replace with TrueParallelBatchEvaluator for 11.5x speedup

---

### 3. test_evolution_simple.py ⚠ REQUIRES TORCH
**Purpose**: Visual evolution test with CPG controllers

**Parameters**:
- Population: 5 robots
- Generations: 2
- Total evaluations: 5 × 2 = 10
- Uses: TurboChargedBatchEvaluator + CPGController + RobotViewer

**Expected Runtime** (if using TrueParallelBatchEvaluator): **~24 seconds**

**Expected Runtime** (current sequential): **~276 seconds (4.6 minutes)**

**Blockers**:
- Requires PyTorch (CPGController)
- Requires pygame (RobotViewer)
- Uses old sequential evaluator

**Status**: ⚠ NOT TESTED (missing dependencies)

---

### 4. test_evolution_small.py ⚠ REQUIRES DEPENDENCIES
**Purpose**: Small-scale evolution pipeline validation

**Parameters**:
- Population: 10 robots
- Generations: 5
- Total evaluations: 10 × 5 = 50
- Uses: SimpleEvolution class

**Expected Runtime** (with TrueParallelBatchEvaluator): **~2 minutes**

**Expected Runtime** (with old evaluator): **~23 minutes**

**Blockers**:
- Requires SimpleEvolution class implementation
- May require torch/pygame depending on controller

**Status**: ⚠ NOT TESTED (missing dependencies)

---

## Working Evolution Tests

### ✓ Recommended: Create Full Evolution Test with True Parallel

**Suggested parameters**:

#### Small Test (Quick validation)
- Population: 10 robots
- Generations: 10
- Total evaluations: 100
- **Expected time**: ~4 minutes

#### Medium Test (Real evolution)
- Population: 50 robots
- Generations: 20
- Total evaluations: 1000
- **Expected time**: ~40 minutes

#### Large Test (Production run)
- Population: 100 robots
- Generations: 50
- Total evaluations: 5000
- **Expected time**: ~3.3 hours (199 minutes)

---

## Summary Table

| Test File | Population | Generations | Total Evals | Expected Runtime | Status |
|-----------|------------|-------------|-------------|------------------|--------|
| test_true_parallel.py | 10 | 1 | 10 | 24s | ✓ TESTED |
| test_evolution_quick.py | 10 | 1 | 10 | 276s (4.6m) | ⚠ OLD EVALUATOR |
| test_evolution_simple.py | 5 | 2 | 10 | 24s | ⚠ NEEDS DEPS |
| test_evolution_small.py | 10 | 5 | 50 | 2m | ⚠ NEEDS DEPS |

---

## Recommendations

1. **Currently Working**:
   - ✓ `test_true_parallel.py` - Full true parallel evaluation working
   - ✓ `visualize_saved_robot.py` - Robot visualization working

2. **To Fix**:
   - Update `test_evolution_quick.py` to use TrueParallelBatchEvaluator
   - Install PyTorch for CPG controllers (optional)
   - Install pygame for interactive visualization (optional)

3. **Next Steps**:
   - Create `test_evolution_full.py` using TrueParallelBatchEvaluator
   - Run small test (10×10) to validate evolution pipeline
   - Scale up to medium (50×20) or large (100×50) experiments

---

## Performance Metrics

**Current System**:
- Sequential: 0.04 robots/s (old TurboChargedBatchEvaluator)
- True Parallel: 0.42 robots/s (TrueParallelBatchEvaluator)
- **Speedup: 11.5x**

**Hardware**:
- GPU: NVIDIA with 21.5GB VRAM
- CuPy: Sparse matrix support enabled
- Max capacity: ~428 nodes, ~2268 springs per batch

**Limitations**:
- Max GPU batch: ~10-15 robots (depends on complexity)
- Memory warning: >10,000 nodes or >50,000 springs
- Larger populations may need chunking into multiple batches
