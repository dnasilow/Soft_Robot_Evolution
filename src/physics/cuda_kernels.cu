#include <cuda_runtime.h>
#include <math.h>

// 3D Vector operations
__device__ float3 operator+(const float3 &a, const float3 &b) {
    return make_float3(a.x + b.x, a.y + b.y, a.z + b.z);
}

__device__ float3 operator-(const float3 &a, const float3 &b) {
    return make_float3(a.x - b.x, a.y - b.y, a.z - b.z);
}

__device__ float3 operator*(const float3 &a, float b) {
    return make_float3(a.x * b, a.y * b, a.z * b);
}

__device__ float magnitude(const float3 &v) {
    return sqrtf(v.x * v.x + v.y * v.y + v.z * v.z);
}

__device__ float3 normalize(const float3 &v) {
    float mag = magnitude(v);
    if (mag > 0.0f) {
        return v * (1.0f / mag);
    }
    return make_float3(0.0f, 0.0f, 0.0f);
}

// Spring force computation kernel
__global__ void computeSpringForces(
    float3* positions,
    float3* velocities,
    float3* forces,
    int* spring_indices,  // pairs of connected nodes
    float* rest_lengths,
    float* stiffnesses,
    float* damping_coeffs,
    int num_springs,
    int num_nodes
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_springs) return;
    
    // Get spring endpoints
    int node1 = spring_indices[idx * 2];
    int node2 = spring_indices[idx * 2 + 1];
    
    // Calculate displacement
    float3 displacement = positions[node2] - positions[node1];
    float current_length = magnitude(displacement);
    
    if (current_length < 0.0001f) return;  // Avoid division by zero
    
    // Spring force (Hooke's law with nonlinearity)
    float extension = current_length - rest_lengths[idx];
    float spring_force = stiffnesses[idx] * extension * (1.0f + 0.1f * fabsf(extension));
    
    // Damping force
    float3 relative_velocity = velocities[node2] - velocities[node1];
    float3 normalized_displacement = normalize(displacement);
    float damping_force = damping_coeffs[idx] * 
                         (relative_velocity.x * normalized_displacement.x +
                          relative_velocity.y * normalized_displacement.y +
                          relative_velocity.z * normalized_displacement.z);
    
    // Total force
    float3 total_force = normalized_displacement * (spring_force + damping_force);
    
    // Apply forces (using atomic operations for thread safety)
    atomicAdd(&forces[node1].x, total_force.x);
    atomicAdd(&forces[node1].y, total_force.y);
    atomicAdd(&forces[node1].z, total_force.z);
    
    atomicAdd(&forces[node2].x, -total_force.x);
    atomicAdd(&forces[node2].y, -total_force.y);
    atomicAdd(&forces[node2].z, -total_force.z);
}

// Integration kernel (Verlet method)
__global__ void integratePositions(
    float3* positions,
    float3* velocities,
    float3* forces,
    float* masses,
    int num_nodes,
    float dt,
    float gravity
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_nodes) return;
    
    // Add gravity
    forces[idx].y -= masses[idx] * gravity;
    
    // Update velocity (with damping)
    float3 acceleration = forces[idx] * (1.0f / masses[idx]);
    velocities[idx] = velocities[idx] * 0.999f + acceleration * dt;
    
    // Update position
    positions[idx] = positions[idx] + velocities[idx] * dt;
    
    // Ground collision
    if (positions[idx].y < 0.0f) {
        positions[idx].y = 0.0f;
        velocities[idx].y = -velocities[idx].y * 0.5f;  // Bounce with damping
        velocities[idx].x *= 0.9f;  // Friction
        velocities[idx].z *= 0.9f;
    }
    
    // Clear forces for next iteration
    forces[idx] = make_float3(0.0f, 0.0f, 0.0f);
}

// Actuator control kernel
__global__ void applyActuatorForces(
    float3* positions,
    int* actuator_spring_indices,
    float* rest_lengths,
    float* actuator_signals,
    float* actuator_phases,
    int num_actuators,
    float time,
    float actuation_strength
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_actuators) return;
    
    int spring_idx = actuator_spring_indices[idx];
    
    // Sinusoidal actuation with phase offset
    float signal = actuator_signals[idx] * sinf(time * 2.0f * 3.14159f + actuator_phases[idx]);
    
    // Modify rest length (±14% as specified)
    rest_lengths[spring_idx] *= (1.0f + actuation_strength * signal * 0.14f);
}