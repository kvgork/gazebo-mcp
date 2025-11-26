"""
Unit tests for geometry module.

Tests geometric calculations and conversions.
"""

import pytest
import math
from pathlib import Path
import sys

# Add project to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.utils import geometry


class TestEulerToQuaternion:
    """Tests for euler_to_quaternion function."""

    def test_zero_rotation(self):
        """Test that zero Euler angles produce identity quaternion."""
        x, y, z, w = geometry.euler_to_quaternion(0.0, 0.0, 0.0)
        assert w == pytest.approx(1.0, abs=1e-6)
        assert x == pytest.approx(0.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)
        assert z == pytest.approx(0.0, abs=1e-6)

    def test_90_degree_yaw(self):
        """Test 90 degree rotation around Z axis."""
        x, y, z, w = geometry.euler_to_quaternion(0.0, 0.0, math.pi / 2)
        # Should rotate around Z axis
        assert w == pytest.approx(math.sqrt(2) / 2, abs=1e-6)
        assert z == pytest.approx(math.sqrt(2) / 2, abs=1e-6)

    def test_quaternion_normalization(self):
        """Test that quaternions are normalized (unit length)."""
        x, y, z, w = geometry.euler_to_quaternion(1.2, 0.5, 2.3)
        magnitude = math.sqrt(w**2 + x**2 + y**2 + z**2)
        assert magnitude == pytest.approx(1.0, abs=1e-6)


class TestQuaternionToEuler:
    """Tests for quaternion_to_euler function."""

    def test_identity_quaternion(self):
        """Test that identity quaternion produces zero Euler angles."""
        roll, pitch, yaw = geometry.quaternion_to_euler(0.0, 0.0, 0.0, 1.0)
        assert roll == pytest.approx(0.0, abs=1e-6)
        assert pitch == pytest.approx(0.0, abs=1e-6)
        assert yaw == pytest.approx(0.0, abs=1e-6)

    def test_round_trip_conversion(self):
        """Test converting Euler -> Quaternion -> Euler."""
        original_roll, original_pitch, original_yaw = 0.5, 0.3, 1.2

        x, y, z, w = geometry.euler_to_quaternion(original_roll, original_pitch, original_yaw)
        roll, pitch, yaw = geometry.quaternion_to_euler(x, y, z, w)

        assert roll == pytest.approx(original_roll, abs=1e-5)
        assert pitch == pytest.approx(original_pitch, abs=1e-5)
        assert yaw == pytest.approx(original_yaw, abs=1e-5)


class TestDistance3D:
    """Tests for distance_3d function."""

    def test_zero_distance(self):
        """Test distance between same points is zero."""
        dist = geometry.distance_3d((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
        assert dist == 0.0

    def test_unit_distance(self):
        """Test simple unit distances."""
        # Distance along X axis
        dist = geometry.distance_3d((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        assert dist == pytest.approx(1.0, abs=1e-6)

        # Distance along diagonal
        dist = geometry.distance_3d((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        assert dist == pytest.approx(math.sqrt(3), abs=1e-6)

    def test_3d_distance(self):
        """Test 3D Euclidean distance calculation."""
        dist = geometry.distance_3d((1.0, 2.0, 3.0), (4.0, 6.0, 8.0))
        expected = math.sqrt((4-1)**2 + (6-2)**2 + (8-3)**2)
        assert dist == pytest.approx(expected, abs=1e-6)


class TestNormalizeAngle:
    """Tests for normalize_angle function."""

    def test_angles_within_range(self):
        """Test that angles within [-π, π] are unchanged."""
        assert geometry.normalize_angle(0.0) == pytest.approx(0.0, abs=1e-6)
        assert geometry.normalize_angle(math.pi/2) == pytest.approx(math.pi/2, abs=1e-6)
        assert geometry.normalize_angle(-math.pi/2) == pytest.approx(-math.pi/2, abs=1e-6)

    def test_angles_outside_range(self):
        """Test that angles outside [-π, π] are normalized."""
        # 2π should normalize to 0
        assert geometry.normalize_angle(2*math.pi) == pytest.approx(0.0, abs=1e-5)

        # π + 0.5 should normalize to -(π - 0.5)
        result = geometry.normalize_angle(math.pi + 0.5)
        assert -math.pi <= result <= math.pi

    def test_large_angles(self):
        """Test normalization of very large angles."""
        result = geometry.normalize_angle(10*math.pi)
        assert -math.pi <= result <= math.pi

        result = geometry.normalize_angle(-10*math.pi)
        assert -math.pi <= result <= math.pi
