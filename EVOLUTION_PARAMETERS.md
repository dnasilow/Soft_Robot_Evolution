# Evolution Experiment Parameters - Technical Reference

## Command-Line Interface

### Basic Usage

```bash
python run_evolution_small.py
python run_evolution_medium.py
python run_evolution_large.py
```

### Modifying Parameters

**To change generation count and population size, edit the script directly:**

Open the desired script (e.g., `run_evolution_medium.py`) and modify these lines:

```python
# Line 11-12
POPULATION_SIZE = 50      # Number of robots per generation
GENERATIONS = 20          # Number of evolutionary generations
```

**No command-line arguments are currently supported. All parameters must be edited in-file.**

---

## Complete Parameter Reference

### Evolution Algorithm Parameters

#### POPULATION_SIZE (integer)
- **Description**: Number of robot genomes evaluated per generation
- **Type**: `int`
- **Range**: 5 - 200 (practical limits due to GPU memory)
- **Default**:
  - Small: 10
  - Medium: 50
  - Large: 100
- **Impact**:
  - Larger = Better exploration, slower per generation
  - Smaller = Faster iteration, risk of premature convergence
- **GPU Constraint**: Total nodes across all robots < ~10,000

#### GENERATIONS (integer)
- **Description**: Number of evolutionary iterations (selection-reproduction cycles)
- **Type**: `int`
- **Range**: 1 - 1000+
- **Default**:
  - Small: 10
  - Medium: 20
  - Large: 50
- **Impact**:
  - More generations = More optimization, longer runtime
  - Typical convergence: 20-50 generations
- **Total Evaluations**: `POPULATION_SIZE × GENERATIONS`

#### MUTATION_RATE (float)
- **Description**: Probability that offspring genome undergoes mutation
- **Type**: `float`
- **Range**: 0.0 - 1.0
- **Default**:
  - Small: 0.30 (30%)
  - Medium: 0.25 (25%)
  - Large: 0.20 (20%)
- **Impact**:
  - Higher = More exploration, risk of instability
  - Lower = More exploitation, risk of stagnation
- **Recommendation**: Decrease for larger populations

#### ELITE_SIZE (integer)
- **Description**: Number of top-performing robots copied unchanged to next generation
- **Type**: `int`
- **Range**: 0 - `POPULATION_SIZE // 2`
- **Default**:
  - Small: 2 (20%)
  - Medium: 5 (10%)
  - Large: 10 (10%)
- **Impact**:
  - Larger = Preserve best solutions, less diversity
  - Zero = Pure mutation/crossover, unstable
- **Recommendation**: ~10% of population size

#### CROSSOVER_RATE (float)
- **Description**: Probability that two parent genomes are combined (vs single parent cloning)
- **Type**: `float`
- **Range**: 0.0 - 1.0
- **Default**:
  - Small: 0.70 (70%)
  - Medium: 0.75 (75%)
  - Large: 0.80 (80%)
- **Impact**:
  - Higher = More genetic mixing, better long-term optimization
  - Lower = Simpler mutations, faster short-term gains
- **Recommendation**: 0.7 - 0.9 for most cases

---

### Physics Simulation Parameters

#### ACTUATION_CYCLES (integer)
- **Description**: Number of actuation oscillations during robot evaluation
- **Type**: `int`
- **Range**: 1 - 20
- **Default**: 5
- **Physical Meaning**: Robot experiences 5 complete expansion-contraction cycles
- **Time Per Cycle**: `1 / ACTUATION_FREQ` seconds
- **Total Simulation Time**: `ACTUATION_CYCLES / ACTUATION_FREQ` seconds
- **Impact**:
  - More cycles = Better locomotion assessment, longer evaluation
  - Fewer cycles = Faster evolution, may miss slow gaits
- **Recommendation**:
  - Minimum 3 for meaningful movement
  - 5-10 for standard experiments

#### ACTUATION_FREQ (float)
- **Description**: Frequency of actuation oscillations in Hertz
- **Type**: `float`
- **Range**: 0.1 - 10.0 Hz
- **Default**: 1.0 Hz
- **Physical Meaning**: Active materials oscillate at 1 cycle/second
- **Impact**:
  - Higher frequency = Faster movement, higher forces
  - Lower frequency = Slower, more controlled motion
  - Affects resonance with robot morphology
- **Biomimetic Range**: 0.5 - 2.0 Hz (typical for soft organisms)

#### TIMESTEP (float)
- **Description**: Physics integration timestep in seconds
- **Type**: `float`
- **Range**: 0.0001 - 0.01 seconds
- **Default**: 0.001 (1 millisecond)
- **Physics Steps Per Evaluation**: `(ACTUATION_CYCLES / ACTUATION_FREQ) / TIMESTEP`
  - Example: `(5 / 1.0) / 0.001 = 5000 steps`
- **Impact**:
  - Smaller = More accurate physics, slower computation
  - Larger = Faster but unstable (springs may explode)
- **Constraint**: Must satisfy `TIMESTEP ≤ 0.001` for stability
- **DO NOT CHANGE** unless you understand numerical integration

---

### Genome Structure Parameters

#### Voxel Grid Size (hardcoded)
- **Description**: 3D lattice dimensions for robot morphology
- **Type**: `tuple[int, int, int]`
- **Default**: `(5, 5, 5)`
- **Active Region**: `(1:4, 1:4, 1:4)` - outer shell reserved
- **Maximum Voxels**: 125 total, ~64 usable
- **To Change**: Modify `create_random_robot()` function
```python
voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)  # Change dimensions here
```
- **Impact**: Larger grids = more complex robots, exponentially slower

#### Voxel Size (hardcoded)
- **Description**: Physical size of each voxel in meters
- **Type**: `float`
- **Default**: 0.01 m (1 cm cubes)
- **To Change**: Modify `VoxelRobot()` call
```python
robot = VoxelRobot(genome, voxel_size=0.01)  # Change size here
```
- **Impact**: Larger voxels = heavier robots, different dynamics

#### Material Types (enumerated)
- **Description**: Voxel material properties
- **Type**: `int` (0-4)
- **Values**:
  - `0`: Empty (no voxel)
  - `1`: Active 0° phase (expands during actuation)
  - `2`: Active 180° phase (contracts during actuation)
  - `3`: Soft passive (flexible, no actuation)
  - `4`: Stiff passive (rigid structural support)
- **Selection**: In `create_random_robot()`:
```python
voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])
```
- **To Bias**: Use weighted probabilities:
```python
voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1])
```

---

### Genetic Operators (Advanced)

#### Mutation Operator (in `mutate_genome()`)
```python
def mutate_genome(voxel_grid, mutation_rate=MUTATION_RATE):
    mutated = voxel_grid.copy()

    if np.random.random() < mutation_rate:
        num_mutations = np.random.randint(1, 5)  # ← Control mutation strength
        for _ in range(num_mutations):
            if np.random.random() < 0.5:  # ← Add/modify vs remove ratio
                # Add/modify voxel
                x, y, z = np.random.randint(1, 4, 3)
                mutated[x, y, z] = np.random.choice([1, 2, 3, 4])
            else:
                # Remove voxel
                occupied = np.argwhere(mutated != 0)
                if len(occupied) > 2:  # ← Minimum voxels constraint
                    idx = occupied[np.random.randint(len(occupied))]
                    mutated[tuple(idx)] = 0

    return mutated
```

**Tunable Sub-Parameters:**
- `num_mutations`: Range `[1, 5]` - mutations per event
- Add/remove probability: `0.5` - equal likelihood
- Minimum voxels: `2` - prevent degenerate robots

#### Crossover Operator (in `crossover()`)
```python
def crossover(parent1, parent2):
    child = np.zeros_like(parent1)

    # Random 3D split
    split_axis = np.random.randint(0, 3)  # ← X, Y, or Z axis
    split_point = np.random.randint(1, 4)  # ← Split position

    for x in range(5):
        for y in range(5):
            for z in range(5):
                coords = [x, y, z]
                if coords[split_axis] < split_point:
                    child[x, y, z] = parent1[x, y, z]
                else:
                    child[x, y, z] = parent2[x, y, z]

    # Ensure child has at least some voxels
    if np.sum(child != 0) < 3:  # ← Minimum voxels
        child = parent1.copy()

    return child
```

**Tunable Sub-Parameters:**
- Split axis: Random among {0=X, 1=Y, 2=Z}
- Split point: Range `[1, 4]` in 5x5x5 grid
- Minimum voxels: `3` - prevent empty robots

**Alternative Crossover Methods** (modify function):
- Uniform crossover: Per-voxel random selection
- Multi-point crossover: Multiple split planes
- Radial crossover: Spherical partition

#### Selection Pressure (in evolution loop)
```python
# Tournament selection
parent1_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]
parent2_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]
```

**Tunable Parameter:**
- Tournament size: `min(5, POPULATION_SIZE)`
  - Smaller (2-3) = Weaker selection, more diversity
  - Larger (10+) = Stronger selection, faster convergence

**Alternative Selection Methods:**
- Roulette wheel: Probability ∝ fitness
- Rank selection: Uniform over top-N
- Truncation: Only top 50% reproduce

---

### Fitness Function Parameters

**Location**: `src/physics/true_parallel_evaluator.py:107-119`

```python
# Fitness = horizontal displacement / (body_length * time)
displacement = np.linalg.norm(final_com[:2] - initial_com[:2])  # XZ plane
body_size = robot.get_bounding_box_size()
body_length = max(body_size[0], 0.001)

fitness = displacement / (body_length * self.simulation_time)

# Clamp to valid range
if np.isnan(fitness) or np.isinf(fitness):
    fitness = 0.0

fitness = max(0.0, min(fitness, 1000.0))  # Prevent extreme values
fitness += 0.0001  # Small existence bonus
```

**Components:**
1. **Displacement Metric**: `np.linalg.norm(final_com[:2] - initial_com[:2])`
   - 2D Euclidean distance in XZ plane (ground plane)
   - Ignores vertical (Y) motion

2. **Normalization**: `displacement / (body_length * simulation_time)`
   - Units: body_lengths per second
   - Size-independent comparison

3. **Existence Bonus**: `+ 0.0001`
   - Prevents zero fitness for stationary robots
   - Maintains population diversity

4. **Clamping**: `[0.0, 1000.0]`
   - Prevents numerical instabilities
   - Limits extreme outliers

**To Modify Fitness Function:**

Edit `src/physics/true_parallel_evaluator.py`, lines 107-119:

```python
# Example: Penalize vertical instability
vertical_penalty = abs(final_com[1] - initial_com[1]) * 0.1
fitness = displacement / (body_length * simulation_time) - vertical_penalty

# Example: Reward energy efficiency (less actuation)
actuator_count = sum(1 for s in robot.springs if s['is_actuator'])
efficiency_bonus = displacement / (actuator_count + 1)
fitness = efficiency_bonus / simulation_time

# Example: Multi-objective (distance + stability)
distance_score = displacement / body_length
stability_score = 1.0 / (1.0 + abs(final_com[1] - initial_com[1]))
fitness = (distance_score * 0.7 + stability_score * 0.3) / simulation_time
```

---

### Output and Logging Parameters

#### EXPERIMENT_NAME (string)
- **Description**: Identifier for results directory
- **Type**: `str`
- **Default**: `f"{size}_{POPULATION_SIZE}x{GENERATIONS}"`
  - Example: `"medium_50x20"`
- **Location**: Line 20
- **Impact**: Names results subdirectory

#### RESULTS_DIR (path)
- **Description**: Directory for saving evolution outputs
- **Type**: `pathlib.Path`
- **Default**: `Path("results") / EXPERIMENT_NAME`
- **Structure**:
```
results/
  medium_50x20/
    gen_001.json
    gen_002.json
    ...
    gen_020.json
    best_robot.pkl
    summary.json
```

#### Per-Generation Logging
**File**: `results/{EXPERIMENT_NAME}/gen_{N:03d}.json`

**Contents**:
```json
{
  "generation": 1,
  "best_fitness": 12.3456,
  "mean_fitness": 5.2341,
  "worst_fitness": 0.1234,
  "fitness_scores": [12.34, 8.76, ...],
  "time_seconds": 24.5
}
```

**To Disable**: Comment out lines 145-150 in evolution scripts

#### Summary Logging
**File**: `results/{EXPERIMENT_NAME}/summary.json`

**Contents**:
```json
{
  "experiment": "medium_50x20",
  "parameters": {
    "population_size": 50,
    "generations": 20,
    "mutation_rate": 0.25,
    "elite_size": 5,
    "crossover_rate": 0.75,
    "actuation_cycles": 5,
    "actuation_freq": 1.0,
    "timestep": 0.001
  },
  "performance": {
    "total_runtime_seconds": 2400.5,
    "avg_generation_time_seconds": 120.0,
    "total_evaluations": 1000,
    "throughput_robots_per_second": 0.42
  },
  "results": {
    "initial_best_fitness": 5.23,
    "final_best_fitness": 89.13,
    "fitness_improvement": 83.90,
    "percent_improvement": 1604.2,
    "best_fitness_history": [5.23, 7.45, ...],
    "mean_fitness_history": [2.11, 3.89, ...],
    "worst_fitness_history": [0.12, 0.34, ...]
  }
}
```

---

## GPU Memory Constraints

### Batch Size Limits

**Maximum robots per batch** (simultaneous evaluation):
```
max_robots_per_batch = GPU_memory / (avg_nodes_per_robot × node_memory)
```

**Typical Limits** (NVIDIA with 21.5 GB VRAM):
- Simple robots (~40 nodes): 10-15 per batch
- Complex robots (~80 nodes): 5-8 per batch
- Very complex (>100 nodes): 3-5 per batch

**Warning Thresholds** (in `true_parallel_evaluator.py:36-37`):
```python
if total_nodes > 10000 or total_springs > 50000:
    print(f"  WARNING: Large batch, may exceed GPU memory")
```

**To Handle Large Populations**:
Current implementation evaluates all robots in one batch. For populations >15:

1. **Chunking** (manual implementation required):
```python
chunk_size = 10
for i in range(0, POPULATION_SIZE, chunk_size):
    chunk = robots[i:i+chunk_size]
    chunk_fitness = evaluator.evaluate_batch(chunk, controllers)
    fitness_scores[i:i+chunk_size] = chunk_fitness
```

2. **Reduce robot complexity**:
   - Smaller voxel grid: `(4, 4, 4)` instead of `(5, 5, 5)`
   - Fewer voxels per robot: Reduce `num_voxels` in `create_random_robot()`

---

## Performance Tuning

### Benchmarked Throughput
- **Current**: 0.42 robots/second @ 5 actuation cycles
- **GPU**: NVIDIA with 21.5 GB VRAM, CuPy sparse matrices

### Runtime Estimation Formula
```
total_runtime_seconds = (POPULATION_SIZE × GENERATIONS) / throughput
total_runtime_minutes = total_runtime_seconds / 60
```

### Optimization Strategies

**To Speed Up Evolution:**
1. ↓ `ACTUATION_CYCLES`: 5 → 3 (40% faster, less accurate)
2. ↓ `POPULATION_SIZE`: 50 → 30 (40% faster, less exploration)
3. ↑ `TIMESTEP`: 0.001 → 0.002 (2x faster, **risky stability**)

**To Improve Solution Quality:**
1. ↑ `GENERATIONS`: 20 → 50 (2.5x longer)
2. ↑ `POPULATION_SIZE`: 50 → 100 (2x longer)
3. ↑ `ACTUATION_CYCLES`: 5 → 10 (2x longer)
4. ↓ `MUTATION_RATE`: 0.25 → 0.15 (exploit good solutions)

---

## Example Parameter Modifications

### Fast Prototyping (2 minutes)
```python
POPULATION_SIZE = 10
GENERATIONS = 5
ACTUATION_CYCLES = 3
# Expected runtime: ~2 min
```

### Balanced Research (1 hour)
```python
POPULATION_SIZE = 30
GENERATIONS = 30
ACTUATION_CYCLES = 5
# Expected runtime: ~60 min
```

### Publication Quality (6 hours)
```python
POPULATION_SIZE = 100
GENERATIONS = 100
ACTUATION_CYCLES = 10
MUTATION_RATE = 0.15
ELITE_SIZE = 15
# Expected runtime: ~360 min
```

---

## All Editable Locations

| Parameter | File | Line(s) | Default Value |
|-----------|------|---------|---------------|
| `POPULATION_SIZE` | `run_evolution_*.py` | 11 | 10/50/100 |
| `GENERATIONS` | `run_evolution_*.py` | 12 | 10/20/50 |
| `MUTATION_RATE` | `run_evolution_*.py` | 13 | 0.3/0.25/0.2 |
| `ELITE_SIZE` | `run_evolution_*.py` | 14 | 2/5/10 |
| `CROSSOVER_RATE` | `run_evolution_*.py` | 15 | 0.7/0.75/0.8 |
| `ACTUATION_CYCLES` | `run_evolution_*.py` | 16 | 5 |
| `ACTUATION_FREQ` | `run_evolution_*.py` | 17 | 1.0 |
| `TIMESTEP` | `run_evolution_*.py` | 18 | 0.001 |
| Voxel grid size | `run_evolution_*.py` | 29 | (5,5,5) |
| Material types | `run_evolution_*.py` | 33 | [1,2,3,4] |
| Mutation strength | `run_evolution_*.py` | 42-54 | 1-5 changes |
| Crossover method | `run_evolution_*.py` | 58-78 | 3D planar |
| Selection pressure | `run_evolution_*.py` | 133-134 | Top-5 tournament |
| Fitness function | `true_parallel_evaluator.py` | 107-119 | Distance/time |

---

## Critical Constraints

**DO NOT VIOLATE:**
1. `TIMESTEP ≤ 0.001` - Physics stability limit
2. `ELITE_SIZE < POPULATION_SIZE` - Must have offspring
3. `ACTUATION_FREQ > 0` - Prevent division by zero
4. `MUTATION_RATE ∈ [0, 1]` - Probability constraint
5. Total GPU nodes < 10,000 - Memory limit

**CHANGING THESE REQUIRES CODE MODIFICATION:**
- Fitness function: Edit `true_parallel_evaluator.py`
- Spring physics: Edit `cuda_physics.py` damping constants
- Material properties: Edit `robot.py` VoxelMaterial class
