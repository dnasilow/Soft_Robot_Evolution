"""Global physics constants for soft robot simulation

This module defines all physics parameters in one place to ensure consistency
across all scripts and prevent conflicting values.
"""

# ==================== TIMESTEP CONFIGURATION ====================

# Physics integration timestep (seconds)
# CRITICAL: Must satisfy stability constraint dt < 2/ω_max
# For soft robots: ω_max ≈ sqrt(k_max/m_min) ≈ 707 rad/s
# Stability limit: dt_max ≈ 0.0028s
# Current value provides 2.8× safety margin

GLOBAL_TIMESTEP = 0.0005  # 0.5 millisecond (HIGHER ACCURACY, 2× slower)

# Alternative values:
# GLOBAL_TIMESTEP = 0.001  # 1ms - Standard (faster)
# GLOBAL_TIMESTEP = 0.0002  # 0.2ms - Maximum accuracy, 5× slower

# DO NOT EXCEED 0.001 without stability testing!
# GLOBAL_TIMESTEP = 0.002  # RISKY - may cause spring explosions


# ==================== DAMPING CONFIGURATION ====================

# Global velocity damping coefficient (s⁻¹)
# Applied to all nodes every timestep
# Higher = more energy dissipation, prevents oscillation buildup
GLOBAL_DAMPING = 10.0  # Tested stable value

# Recommended range: 5.0 - 20.0
# - Lower (5.0): More dynamic, longer oscillations
# - Higher (20.0): Heavy damping, quick settling

# If experiencing spring explosions, increase to:
# GLOBAL_DAMPING = 15.0


# ==================== ACTUATION PARAMETERS ====================

# Default actuation frequency (Hz)
# How many expansion-contraction cycles per second
DEFAULT_ACTUATION_FREQ = 1.0  # 1 Hz (1 cycle/second)

# Actuation strength (fractional length change)
# ±20% based on Lipson et al. soft robot research
ACTUATION_STRENGTH = 0.2  # ±20% of rest length

# If springs explode, reduce to:
# ACTUATION_STRENGTH = 0.1  # ±10% (more conservative)


# ==================== GROUND CONTACT ====================

# Ground spring parameters
GROUND_STIFFNESS = 5000.0  # N/m
GROUND_DAMPING = 50.0      # Ns/m
GROUND_LEVEL = 0.0         # Y-coordinate of ground plane (meters)


# ==================== MATERIAL PROPERTIES ====================

# See src/physics/robot.py for detailed material definitions
# Material IDs:
#   0: Empty (void)
#   1: Active 0° (green) - expands during actuation
#   2: Active 180° (red) - contracts during actuation
#   3: Soft passive (cyan) - flexible, no actuation
#   4: Stiff passive (blue) - rigid structural support


# ==================== SIMULATION LIMITS ====================

# Maximum velocity (m/s)
# Prevents numerical explosions from excessive forces
MAX_VELOCITY = 100.0  # m/s (very conservative)

# Velocity clamping applied every timestep
# Typical soft robot velocities: 0.1 - 10 m/s


# ==================== NUMERICAL STABILITY ====================

# Minimum mass for nodes (kg)
# Prevents division by zero and extreme accelerations
MIN_NODE_MASS = 0.001  # 1 gram

# Maximum spring extension ratio
# Prevents springs from stretching to infinity
MAX_SPRING_EXTENSION_RATIO = 1.2  # 1.2× rest length maximum (20% stretch)
MAX_SPRING_COMPRESSION_RATIO = 0.2  # 0.2× rest length minimum (80% compression)

# Enable spring extension clamping (recommended for stability)
CLAMP_SPRING_EXTENSION = True


# ==================== PERFORMANCE TUNING ====================

# Sparse matrix threshold
# Use sparse matrices when springs/nodes ratio > this value
SPARSE_MATRIX_THRESHOLD = 5.0

# Force calculation method
# 'sparse' (fastest), 'dense' (fallback), 'atomic' (legacy)
FORCE_CALCULATION_METHOD = 'sparse'


# ==================== VALIDATION ====================

def validate_constants():
    """Validate physics constants for stability"""
    import numpy as np

    issues = []

    # Check timestep stability
    if GLOBAL_TIMESTEP > 0.001:
        issues.append(f"WARNING: GLOBAL_TIMESTEP={GLOBAL_TIMESTEP}s exceeds recommended 0.001s")

    # Check damping range
    if GLOBAL_DAMPING < 1.0:
        issues.append(f"WARNING: GLOBAL_DAMPING={GLOBAL_DAMPING} may be too low (min 1.0)")
    if GLOBAL_DAMPING > 50.0:
        issues.append(f"WARNING: GLOBAL_DAMPING={GLOBAL_DAMPING} may be too high (max 50.0)")

    # Check actuation strength
    if ACTUATION_STRENGTH > 0.3:
        issues.append(f"WARNING: ACTUATION_STRENGTH={ACTUATION_STRENGTH} may cause instability (max 0.3)")
    if ACTUATION_STRENGTH < 0.05:
        issues.append(f"WARNING: ACTUATION_STRENGTH={ACTUATION_STRENGTH} too small for locomotion (min 0.05)")

    # Check ground parameters
    if GROUND_STIFFNESS < 1000.0:
        issues.append(f"WARNING: GROUND_STIFFNESS={GROUND_STIFFNESS} too soft (min 1000)")

    return issues


if __name__ == "__main__":
    print("="*70)
    print("PHYSICS CONSTANTS VALIDATION")
    print("="*70)
    print(f"\nTimestep: {GLOBAL_TIMESTEP} s")
    print(f"Global damping: {GLOBAL_DAMPING} s⁻¹")
    print(f"Actuation strength: {ACTUATION_STRENGTH * 100}%")
    print(f"Ground stiffness: {GROUND_STIFFNESS} N/m")

    issues = validate_constants()
    if issues:
        print(f"\n⚠ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\n✓ All constants valid")
