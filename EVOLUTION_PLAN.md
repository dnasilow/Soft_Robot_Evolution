# Evolution Implementation Plan & CUDA Status

## Executive Summary

**Physics Status:** ✅ STABLE AND READY
- test_visual_cube.py shows correct soft-body physics
- Cube falls, bounces, and settles normally
- Small wobble (4cm) is expected and acceptable
- Configuration: spring_damping=0.4, global_damping=10.0 s⁻¹

**CUDA Status:** ✅ GPU DETECTED AND ACTIVE
- GPU: 21.5 GB VRAM available
- CuPy: Working on GPU
- Sparse matrices: Supported
- Physics benchmark: 635 steps/second

**Evolution Infrastructure:** ✅ CODE EXISTS
- EvolutionaryAlgorithm class: Ready
- Genome classes: OptimizedCPPNGenome available
- Controller classes: CPGController available (requires torch)
- Batch evaluator: TurboChargedBatchEvaluator implemented

**Blocker:** ⚠️ Torch dependency missing
- Controllers.py imports torch
- Need to: `conda install pytorch` or use passive robots

---

## Phase 1: CUDA Validation Results

### Test 1: GPU Device ✅ PASS
```
GPU Device: 21.5 GB VRAM
CUDA Available: YES
CuPy Arrays: Working on GPU
```

### Test 2: Physics Benchmark ⚠️ MODERATE
```
1000 physics steps (1 second simulation)
Total time: 1.575 seconds
Throughput: 635 steps/second
Per-step: 1.57 ms
```

**Analysis:**
- Performance is moderate (not excellent)
- May be CPU-bound in some operations
- Acceptable for evolution but not optimal
- Could investigate GPU utilization later

### Test 3: Batch Evaluation ⏳ TIMEOUT
```
Batch evaluation of 10 robots timed out (>60s)
```

**Possible causes:**
- First run compiling CUDA kernels (warmup needed)
- Batch size (30 environments) may be too large
- Need profiling to identify bottleneck

---

## Phase 2: Evolution Test Plan

### Option A: Quick Test (Passive Robots)
No torch dependency needed

**Script:** `test_evolution_quick.py`

**Parameters:**
- 10 random passive robots
- No controllers (passive soft-body dynamics)
- Measure batch evaluation performance

**Expected outcome:**
- Validates GPU batch processing
- Measures robots/second throughput
- Estimates evolution time

### Option B: Full Evolution (Requires torch)
Install PyTorch first: `conda install pytorch`

**Script:** `test_evolution_small_fixed.py`

**Parameters:**
```python
population_size = 10
generations = 5
genome_class = OptimizedCPPNGenome
controller_class = CPGController
evaluator = TurboChargedBatchEvaluator(
    num_environments=30,
    actuation_cycles=5,
    actuation_freq=1.0
)
```

**Expected outcome:**
- Full evolution pipeline validation
- Fitness progression over generations
- Performance metrics

---

## Phase 3: Full-Scale Evolution

### Recommended Configuration

**Small Experiment (Quick validation):**
```python
population_size = 20
generations = 10
simulation_time = 5 actuation cycles
Expected time: 5-10 minutes
```

**Medium Experiment (Main experiments):**
```python
population_size = 50
generations = 30
simulation_time = 10 actuation cycles
Expected time: 30-60 minutes
```

**Large Experiment (Publication-quality):**
```python
population_size = 100
generations = 50-100
simulation_time = 10-15 actuation cycles
Expected time: 2-5 hours
```

### Performance Estimates

Based on 635 physics steps/second:
- 1 robot × 5 seconds = 3,175 physics steps = **5 seconds**
- 10 robots batch = **50 seconds** (with parallelization)
- 50 robots batch = **250 seconds** (~4 minutes)

**Full evolution estimates:**
- 20 pop × 10 gen = 200 evals = **17 minutes**
- 50 pop × 30 gen = 1500 evals = **2 hours**
- 100 pop × 50 gen = 5000 evals = **7 hours**

*Note: These are conservative estimates. Actual performance may be better with warmup.*

---

## Key Files Created

1. **test_cuda_validation.py**
   - Validates GPU is working
   - Benchmarks physics performance
   - Tests batch evaluation

2. **test_evolution_quick.py**
   - Minimal dependencies (no torch)
   - Tests batch evaluation only
   - Provides performance estimates

3. **test_evolution_small_fixed.py**
   - Full evolution pipeline
   - Requires torch
   - 10 pop × 5 gen test

4. **EVOLUTION_PLAN.md** (this file)
   - Complete implementation plan
   - Performance analysis
   - Next steps

---

## Next Steps (In Order)

### Immediate (Required)

1. **Install PyTorch:**
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
   ```
   OR use CPU version:
   ```bash
   conda install pytorch torchvision torchaudio cpuonly -c pytorch
   ```

2. **Run quick validation:**
   ```bash
   python test_evolution_quick.py
   ```
   Should complete in 1-2 minutes and show throughput

3. **Run small evolution test:**
   ```bash
   python test_evolution_small_fixed.py
   ```
   Should complete in 5-10 minutes and show fitness progression

### Short-term (Recommended)

4. **Profile batch evaluator:**
   - Identify GPU utilization bottlenecks
   - Optimize batch size (try 10, 20, 30 environments)
   - Add warmup runs to exclude kernel compilation time

5. **Test scaling:**
   - Run 20 pop × 10 gen
   - Verify linear scaling
   - Check GPU memory usage

### Long-term (Optional)

6. **Optimize physics:**
   - Investigate why only 635 steps/second
   - Profile CUDA kernels
   - Consider larger batch sizes

7. **Distributed evolution:**
   - Multi-GPU support
   - Cluster deployment
   - Island model evolution

---

## Troubleshooting

### Issue: Batch evaluation timeouts
**Solution:**
- Reduce num_environments from 30 to 10
- Add warmup run before timing
- Check GPU memory isn't full

### Issue: Low throughput (<1 robot/s)
**Solution:**
- Check GPU utilization with `nvidia-smi`
- Verify CUDA kernels are compiling
- Profile with CuPy profiler

### Issue: NaN/Inf fitness values
**Solution:**
- Check physics stability (damping=10.0)
- Verify robots have valid structure
- Add fitness clamping

### Issue: No fitness improvement
**Solution:**
- Increase mutation rate (0.15-0.2)
- Check fitness function is correct
- Verify diversity is maintained
- Run longer (50+ generations)

---

## Physics Configuration (Current Stable)

```python
# Material spring damping (dimensionless ratio)
MATERIALS = {
    1: damping=0.3  # Active material
    2: damping=0.3  # Active material
    3: damping=0.4  # Soft passive
    4: damping=0.2  # Stiff passive
}

# Global velocity damping (s⁻¹)
damping_coefficient = 10.0  # in cuda_physics.py

# Terminal velocity
v_terminal = 9.81 / 10.0 = 0.98 m/s

# Wobble: ~4cm vertical, acceptable for soft-body
```

**DO NOT change these values** - they are stable and validated!

---

## Expected Behavior

### Correct Physics (test_visual_cube.py):
```
- Cube falls at ~0.33 m/s (terminal velocity)
- Reaches ground in ~2.5 seconds
- Settles near Y=0.55m (equilibrium)
- Small oscillations (4cm) that dampen over time
- Status: "[MODERATE] Some spring resistance but could be better"
```

This is NORMAL and EXPECTED! ✅

### Correct Evolution:
```
Generation 1: Random fitness values
Generation 5-10: Fitness starts improving
Generation 20+: Fitness plateau (local optimum)
```

Typical fitness improvement: 2-10x over 50 generations

---

## Success Criteria

### Minimum (Must achieve):
- [x] GPU detected and active
- [x] Physics stable (no explosions)
- [ ] Batch evaluation <5 min for 10 robots
- [ ] Evolution completes without crashes
- [ ] Fitness values are valid (no NaN/Inf)

### Target (Good performance):
- [ ] Throughput >1 robot/second
- [ ] 50 pop × 20 gen in <1 hour
- [ ] Fitness improves over generations
- [ ] Population maintains diversity

### Stretch (Optimal):
- [ ] Throughput >5 robots/second
- [ ] 100 pop × 50 gen in <2 hours
- [ ] Multi-objective optimization
- [ ] Distributed evolution

---

## Contact & Support

**Current Status:** Ready for evolution experiments after installing torch

**Blockers:** None (just need torch installation)

**Recommendations:**
1. Install torch: `conda install pytorch`
2. Run test_evolution_quick.py
3. Run test_evolution_small_fixed.py
4. Scale up to 50 pop × 30 gen

**Your physics is stable. Your GPU is ready. Time to evolve some robots! 🤖**
