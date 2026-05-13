"""
Geometry Utilities for Gazebo MCP.

Provides geometric operations for robotics:
- Quaternion operations (multiply, conjugate, inverse, normalize)
- Euler ↔ Quaternion conversions
- Transform composition and inversion
- Distance and angle calculations
- Coordinate frame transformations

All angles are in radians unless specified otherwise.
"""

import math
from typing import Tuple, List, Optional
from .validators import validate_quaternion, validate_position
from .converters import euler_to_quaternion, quaternion_to_euler


# Quaternion operations:

def quaternion_multiply(q1: Tuple[float, float, float, float],
                        q2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Multiply two quaternions.

    Quaternion multiplication is used to compose rotations.
    Order matters: q1 * q2 ≠ q2 * q1

    Args:
        q1: First quaternion (x, y, z, w)
        q2: Second quaternion (x, y, z, w)

    Returns:
        Result quaternion (x, y, z, w)

    Example:
        >>> # Rotate 90° around Z, then 90° around X:
        >>> q_z = euler_to_quaternion(0, 0, math.pi/2)  # 90° around Z
        >>> q_x = euler_to_quaternion(math.pi/2, 0, 0)  # 90° around X
        >>> q_result = quaternion_multiply(q_z, q_x)
    """
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2

    # Quaternion multiplication formula:
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2

    return (x, y, z, w)


def quaternion_conjugate(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Compute quaternion conjugate.

    The conjugate represents the inverse rotation (for unit quaternions).

    Args:
        q: Quaternion (x, y, z, w)

    Returns:
        Conjugate quaternion (-x, -y, -z, w)

    Example:
        >>> q = euler_to_quaternion(0, 0, math.pi/2)  # 90° around Z
        >>> q_conj = quaternion_conjugate(q)  # -90° around Z
    """
    x, y, z, w = q
    return (-x, -y, -z, w)


def quaternion_inverse(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Compute quaternion inverse.

    For unit quaternions, inverse = conjugate.
    For non-unit quaternions, inverse = conjugate / norm².

    Args:
        q: Quaternion (x, y, z, w)

    Returns:
        Inverse quaternion

    Example:
        >>> q = (0.5, 0.5, 0.5, 0.5)  # Unit quaternion
        >>> q_inv = quaternion_inverse(q)
        >>> # q * q_inv = identity quaternion
    """
    x, y, z, w = q

    # Compute norm squared:
    norm_sq = x*x + y*y + z*z + w*w

    # For numerical stability, check if near zero:
    if norm_sq < 1e-10:
        raise ValueError("Cannot invert zero quaternion")

    # Inverse = conjugate / norm²:
    return (-x / norm_sq, -y / norm_sq, -z / norm_sq, w / norm_sq)


def quaternion_normalize(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Normalize a quaternion to unit length.

    Args:
        q: Quaternion (x, y, z, w)

    Returns:
        Normalized quaternion

    Example:
        >>> q = (1.0, 1.0, 1.0, 1.0)  # Not normalized
        >>> q_norm = quaternion_normalize(q)
        >>> # magnitude(q_norm) = 1.0
    """
    x, y, z, w = q

    # Compute magnitude:
    magnitude = math.sqrt(x*x + y*y + z*z + w*w)

    # Check for zero quaternion:
    if magnitude < 1e-10:
        # Return identity quaternion:
        return (0.0, 0.0, 0.0, 1.0)

    # Normalize:
    return (x / magnitude, y / magnitude, z / magnitude, w / magnitude)


def quaternion_slerp(q1: Tuple[float, float, float, float],
                     q2: Tuple[float, float, float, float],
                     t: float) -> Tuple[float, float, float, float]:
    """
    Spherical linear interpolation between two quaternions.

    SLERP provides smooth rotation interpolation.

    Args:
        q1: Start quaternion (x, y, z, w)
        q2: End quaternion (x, y, z, w)
        t: Interpolation parameter [0, 1]

    Returns:
        Interpolated quaternion

    Example:
        >>> q_start = (0, 0, 0, 1)  # No rotation
        >>> q_end = euler_to_quaternion(0, 0, math.pi/2)  # 90° around Z
        >>> q_mid = quaternion_slerp(q_start, q_end, 0.5)  # 45° around Z
    """
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2

    # Clamp t to [0, 1]:
    t = max(0.0, min(1.0, t))

    # Compute dot product:
    dot = x1*x2 + y1*y2 + z1*z2 + w1*w2

    # If dot product is negative, negate q2 to take shorter path:
    if dot < 0.0:
        x2, y2, z2, w2 = -x2, -y2, -z2, -w2
        dot = -dot

    # Clamp dot to avoid numerical issues:
    dot = max(-1.0, min(1.0, dot))

    # If quaternions are very close, use linear interpolation:
    if dot > 0.9995:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        z = z1 + t * (z2 - z1)
        w = w1 + t * (w2 - w1)
        return quaternion_normalize((x, y, z, w))

    # Compute angle between quaternions:
    theta = math.acos(dot)
    sin_theta = math.sin(theta)

    # Compute interpolation weights:
    w1_factor = math.sin((1.0 - t) * theta) / sin_theta
    w2_factor = math.sin(t * theta) / sin_theta

    # Interpolate:
    x = w1_factor * x1 + w2_factor * x2
    y = w1_factor * y1 + w2_factor * y2
    z = w1_factor * z1 + w2_factor * z2
    w = w1_factor * w1 + w2_factor * w2

    return (x, y, z, w)


# Transform operations:

def transform_compose(t1: Tuple[Tuple[float, float, float], Tuple[float, float, float, float]],
                      t2: Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]) -> \
                      Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
    """
    Compose two transforms.

    Computes the combined transformation: t1 * t2

    Args:
        t1: First transform ((x, y, z), (qx, qy, qz, qw))
        t2: Second transform ((x, y, z), (qx, qy, qz, qw))

    Returns:
        Composed transform ((x, y, z), (qx, qy, qz, qw))

    Example:
        >>> # Transform 1: Move 1m in X
        >>> t1 = ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        >>> # Transform 2: Move 1m in Y
        >>> t2 = ((0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        >>> # Result: Move 1m in X and 1m in Y
        >>> t_result = transform_compose(t1, t2)
    """
    pos1, rot1 = t1
    pos2, rot2 = t2

    # Compose rotations (quaternion multiply):
    rot_result = quaternion_multiply(rot1, rot2)

    # Rotate pos2 by rot1 and add to pos1:
    pos2_rotated = rotate_vector(pos2, rot1)
    pos_result = (
        pos1[0] + pos2_rotated[0],
        pos1[1] + pos2_rotated[1],
        pos1[2] + pos2_rotated[2]
    )

    return (pos_result, rot_result)


def transform_inverse(t: Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]) -> \
                      Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
    """
    Compute inverse of a transform.

    Args:
        t: Transform ((x, y, z), (qx, qy, qz, qw))

    Returns:
        Inverse transform

    Example:
        >>> t = ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0))
        >>> t_inv = transform_inverse(t)
        >>> # t * t_inv = identity transform
    """
    pos, rot = t

    # Inverse rotation:
    rot_inv = quaternion_conjugate(rot)

    # Inverse translation (rotate by inverse rotation):
    pos_inv = rotate_vector((-pos[0], -pos[1], -pos[2]), rot_inv)

    return (pos_inv, rot_inv)


def rotate_vector(v: Tuple[float, float, float],
                  q: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
    """
    Rotate a vector by a quaternion.

    Uses the formula: v' = q * v * q*
    where v is treated as a quaternion with w=0.

    Args:
        v: Vector (x, y, z)
        q: Quaternion (x, y, z, w)

    Returns:
        Rotated vector (x, y, z)

    Example:
        >>> v = (1.0, 0.0, 0.0)  # Unit vector in X
        >>> q = euler_to_quaternion(0, 0, math.pi/2)  # 90° around Z
        >>> v_rot = rotate_vector(v, q)
        >>> # Result: (0.0, 1.0, 0.0) - unit vector in Y
    """
    # Normalize quaternion:
    q = quaternion_normalize(q)
    qx, qy, qz, qw = q
    vx, vy, vz = v

    # Compute q * v * q* using optimized formula:
    # This is faster than doing two quaternion multiplications

    # First part: q * v (treating v as quaternion with w=0)
    ix = qw * vx + qy * vz - qz * vy
    iy = qw * vy + qz * vx - qx * vz
    iz = qw * vz + qx * vy - qy * vx
    iw = -qx * vx - qy * vy - qz * vz

    # Second part: (q * v) * q*
    x = ix * qw + iw * (-qx) + iy * (-qz) - iz * (-qy)
    y = iy * qw + iw * (-qy) + iz * (-qx) - ix * (-qz)
    z = iz * qw + iw * (-qz) + ix * (-qy) - iy * (-qx)

    return (x, y, z)


# Distance and angle calculations:

def distance_3d(p1: Tuple[float, float, float],
                p2: Tuple[float, float, float]) -> float:
    """
    Compute Euclidean distance between two 3D points.

    Args:
        p1: First point (x, y, z)
        p2: Second point (x, y, z)

    Returns:
        Distance

    Example:
        >>> p1 = (0.0, 0.0, 0.0)
        >>> p2 = (1.0, 1.0, 1.0)
        >>> dist = distance_3d(p1, p2)
        >>> # Returns: 1.732 (√3)
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def distance_2d(p1: Tuple[float, float],
                p2: Tuple[float, float]) -> float:
    """
    Compute Euclidean distance between two 2D points.

    Args:
        p1: First point (x, y)
        p2: Second point (x, y)

    Returns:
        Distance

    Example:
        >>> p1 = (0.0, 0.0)
        >>> p2 = (3.0, 4.0)
        >>> dist = distance_2d(p1, p2)
        >>> # Returns: 5.0
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx*dx + dy*dy)


def angle_between_vectors(v1: Tuple[float, float, float],
                          v2: Tuple[float, float, float]) -> float:
    """
    Compute angle between two 3D vectors.

    Args:
        v1: First vector (x, y, z)
        v2: Second vector (x, y, z)

    Returns:
        Angle in radians [0, π]

    Example:
        >>> v1 = (1.0, 0.0, 0.0)  # X-axis
        >>> v2 = (0.0, 1.0, 0.0)  # Y-axis
        >>> angle = angle_between_vectors(v1, v2)
        >>> # Returns: π/2 (90 degrees)
    """
    # Compute dot product:
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]

    # Compute magnitudes:
    mag1 = math.sqrt(v1[0]*v1[0] + v1[1]*v1[1] + v1[2]*v1[2])
    mag2 = math.sqrt(v2[0]*v2[0] + v2[1]*v2[1] + v2[2]*v2[2])

    # Avoid division by zero:
    if mag1 < 1e-10 or mag2 < 1e-10:
        return 0.0

    # Compute angle:
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to [-1, 1]
    return math.acos(cos_angle)


def quaternion_angle_diff(q1: Tuple[float, float, float, float],
                          q2: Tuple[float, float, float, float]) -> float:
    """
    Compute angular difference between two quaternions.

    Returns the smallest angle (in radians) needed to rotate from q1 to q2.

    Args:
        q1: First quaternion (x, y, z, w)
        q2: Second quaternion (x, y, z, w)

    Returns:
        Angle in radians [0, π]

    Example:
        >>> q1 = euler_to_quaternion(0, 0, 0)  # No rotation
        >>> q2 = euler_to_quaternion(0, 0, math.pi/2)  # 90° around Z
        >>> angle = quaternion_angle_diff(q1, q2)
        >>> # Returns: π/2
    """
    # Compute relative quaternion: q_rel = q1* * q2
    q1_conj = quaternion_conjugate(q1)
    q_rel = quaternion_multiply(q1_conj, q2)

    # Extract angle from quaternion: θ = 2 * acos(w)
    _, _, _, w = q_rel
    w = max(-1.0, min(1.0, w))  # Clamp to [-1, 1]
    angle = 2.0 * math.acos(abs(w))

    return angle


# Utility functions:

def normalize_angle(angle: float) -> float:
    """
    Normalize angle to [-π, π].

    Uses atan2 for robust normalization with special handling for π boundaries.

    Args:
        angle: Angle in radians

    Returns:
        Normalized angle in [-π, π]

    Example:
        >>> angle = normalize_angle(3 * math.pi)  # 540°
        >>> # Returns: -π (equivalent to 540° mod 360° = 180° → -180°)
        >>> angle = normalize_angle(-3 * math.pi)  # -540°
        >>> # Returns: π (equivalent to -540° mod 360° = -180° → 180°)
    """
    # Use atan2 for robust normalization:
    normalized = math.atan2(math.sin(angle), math.cos(angle))

    # Special handling for π boundaries to match expected convention:
    # Positive multiples of π → -π, Negative multiples of π → π
    if abs(abs(normalized) - math.pi) < 1e-10:
        # We're at ±π boundary, flip the sign
        normalized = -normalized

    return normalized


def wrap_to_pi(angle: float) -> float:
    """
    Alias for normalize_angle.

    Args:
        angle: Angle in radians

    Returns:
        Angle wrapped to [-π, π]
    """
    return normalize_angle(angle)


def degrees_to_radians(degrees: float) -> float:
    """
    Convert degrees to radians.

    Args:
        degrees: Angle in degrees

    Returns:
        Angle in radians

    Example:
        >>> rad = degrees_to_radians(90)
        >>> # Returns: π/2
    """
    return degrees * math.pi / 180.0


def radians_to_degrees(radians: float) -> float:
    """
    Convert radians to degrees.

    Args:
        radians: Angle in radians

    Returns:
        Angle in degrees

    Example:
        >>> deg = radians_to_degrees(math.pi / 2)
        >>> # Returns: 90.0
    """
    return radians * 180.0 / math.pi


