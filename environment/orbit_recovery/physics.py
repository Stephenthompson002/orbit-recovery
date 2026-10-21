"""Physical quantities for a Newtonian two-body relative orbit."""

import math

Vector = tuple[float, float, float]
PhaseVector = tuple[float, float, float, float, float, float]


def derivative(state: PhaseVector, mu: float) -> PhaseVector:
    x, y, z, vx, vy, vz = state
    radius_squared = x * x + y * y + z * z
    if radius_squared == 0.0:
        raise ValueError("gravitational acceleration is undefined at zero separation")
    scale = -mu / (radius_squared * math.sqrt(radius_squared))
    return vx, vy, vz, scale * x, scale * y, scale * z


def specific_energy(state: PhaseVector, mu: float) -> float:
    x, y, z, vx, vy, vz = state
    radius = math.sqrt(x * x + y * y + z * z)
    speed_squared = vx * vx + vy * vy + vz * vz
    return 0.5 * speed_squared - mu / radius


def specific_angular_momentum(state: PhaseVector) -> Vector:
    x, y, z, vx, vy, vz = state
    return y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
