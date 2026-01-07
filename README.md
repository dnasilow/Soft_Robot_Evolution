# Soft Robot Evolution

Evolutionary soft robotics system using MuJoCo physics simulation. This project evolves virtual soft robots made of voxels (3D blocks) with different material properties to optimize locomotion.

## Features

- **MuJoCo Physics**: Professional-grade physics simulation with stable gravity and collision detection
- **Evolutionary Algorithm**: Genetic algorithm optimizes robot morphology and material composition
- **Sinusoidal Actuation**: Active voxel materials oscillate at 2Hz to create locomotion
- **Real-time Visualization**: Interactive 3D viewer for watching robots evolve and move

## Voxel Materials

- **Material 1 (Green)**: Active 0° - oscillates at phase 0
- **Material 2 (Red)**: Active 180° - oscillates at phase π (opposite phase)
- **Material 3 (Cyan)**: Soft passive - flexible connective tissue
- **Material 4 (Blue)**: Stiff passive - rigid structural support

## Quick Start

### Prerequisites
```bash
conda create -n softrobot python=3.10
conda activate softrobot
pip install mujoco numpy
```

### Run Visualizations

```bash
# Single voxel falling (basic physics test)
python visualize_single_voxel_fall.py

# 3x3x3 cube with soft connections
python visualize_3x3x3_cube.py

# Actuating robot (4 voxels with different materials)
python test_actuation.py

# Full visualization test suite
python test_mujoco_visualization.py
```

## Project Structure

```
src/
├── physics/
│   ├── mujoco_converter.py     # Converts voxel grids to MuJoCo XML
│   └── mujoco_physics.py       # Physics engine with actuation
├── evolution/
│   ├── evolutionary_algorithm.py
│   └── mujoco_evaluator.py     # Batch fitness evaluation
└── ...

test_*.py                        # Test scripts
visualize_*.py                   # Visualization demos
```

## Coordinate System

- **X-axis (Red)**: Horizontal left/right
- **Y-axis (Green)**: Horizontal forward/back
- **Z-axis (Blue)**: Vertical UP/DOWN (height)
- **Gravity**: [0, 0, -9.81] pulling downward on Z-axis

## Physics Parameters

- Voxel size: 10mm × 10mm × 10mm (1cm cube)
- Voxel mass: 0.2g (density: 200 kg/m³)
- Timestep: 0.0005s (2000 Hz)
- Actuation: ±20% stiffness modulation at 2Hz

## Current Status

✅ MuJoCo physics integration complete
✅ Coordinate system and gravity fixed
✅ Multi-voxel positioning corrected
✅ Sinusoidal actuation implemented
⏳ Evolution pipeline integration in progress

## License

Research project - see repository for details.
