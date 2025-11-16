"""
Unit Tests for Gazebo MCP Utilities.

Tests validators, converters, geometry utilities, and exceptions.

Run with:
    pytest tests/test_utils.py -v
"""

import pytest
import math
from gazebo_mcp.utils.exceptions import (
    InvalidParameterError,
    MissingParameterError,
    GazeboMCPError
)
from gazebo_mcp.utils.validators import (
    validate_coordinate,
    validate_position,
    validate_angle,
    validate_orientation,
    validate_quaternion,
    validate_model_name,
    validate_entity_name,
    validate_sensor_type,
    validate_timeout,
    validate_positive,
    validate_non_negative,
    validate_response_format,
    VALID_SENSOR_TYPES
)
from gazebo_mcp.utils.converters import (
    quaternion_to_euler,
    euler_to_quaternion
)
from gazebo_mcp.utils.geometry import (
    quaternion_multiply,
    quaternion_conjugate,
    quaternion_inverse,
    quaternion_normalize,
    quaternion_slerp,
    transform_compose,
    transform_inverse,
    rotate_vector,
    distance_3d,
    distance_2d,
    angle_between_vectors,
    quaternion_angle_diff,
    normalize_angle,
    degrees_to_radians,
    radians_to_degrees
)


# Test Validators:

class TestValidators:
    """Test validation functions."""

    def test_validate_coordinate_valid(self):
        """Test valid coordinate."""
        x = validate_coordinate(1.5, "x")
        assert x == 1.5

    def test_validate_coordinate_with_range(self):
        """Test coordinate with min/max."""
        x = validate_coordinate(5.0, "x", min_value=0.0, max_value=10.0)
        assert x == 5.0

    def test_validate_coordinate_below_min(self):
        """Test coordinate below minimum."""
        with pytest.raises(InvalidParameterError):
            validate_coordinate(-1.0, "x", min_value=0.0)

    def test_validate_coordinate_above_max(self):
        """Test coordinate above maximum."""
        with pytest.raises(InvalidParameterError):
            validate_coordinate(11.0, "x", max_value=10.0)

    def test_validate_coordinate_nan(self):
        """Test NaN coordinate."""
        with pytest.raises(InvalidParameterError):
            validate_coordinate(float('nan'), "x")

    def test_validate_coordinate_inf(self):
        """Test infinite coordinate."""
        with pytest.raises(InvalidParameterError):
            validate_coordinate(float('inf'), "x")

    def test_validate_position_valid(self):
        """Test valid position."""
        pos = validate_position(1.0, 2.0, 3.0)
        assert pos == (1.0, 2.0, 3.0)

    def test_validate_position_with_range(self):
        """Test position with range."""
        pos = validate_position(1.0, 2.0, 3.0, min_coord=-10.0, max_coord=10.0)
        assert pos == (1.0, 2.0, 3.0)

    def test_validate_angle_radians(self):
        """Test angle in radians."""
        angle = validate_angle(math.pi/2, "yaw", radians=True)
        assert angle == pytest.approx(math.pi/2)

    def test_validate_angle_degrees(self):
        """Test angle in degrees."""
        angle = validate_angle(90.0, "yaw", radians=False)
        assert angle == pytest.approx(math.pi/2)

    def test_validate_orientation_radians(self):
        """Test orientation in radians."""
        orient = validate_orientation(0.0, 0.0, math.pi/2, radians=True)
        assert orient == (0.0, 0.0, pytest.approx(math.pi/2))

    def test_validate_orientation_degrees(self):
        """Test orientation in degrees."""
        orient = validate_orientation(0.0, 0.0, 90.0, radians=False)
        assert orient[2] == pytest.approx(math.pi/2)

    def test_validate_quaternion_identity(self):
        """Test identity quaternion."""
        q = validate_quaternion(0.0, 0.0, 0.0, 1.0)
        assert q == (0.0, 0.0, 0.0, 1.0)

    def test_validate_quaternion_normalized(self):
        """Test normalized quaternion."""
        # 45 degrees around Z:
        q = validate_quaternion(0.0, 0.0, 0.3826834, 0.9238795)
        assert len(q) == 4

    def test_validate_quaternion_not_normalized(self):
        """Test non-normalized quaternion."""
        with pytest.raises(InvalidParameterError):
            validate_quaternion(1.0, 1.0, 1.0, 1.0)

    def test_validate_model_name_valid(self):
        """Test valid model names."""
        assert validate_model_name("turtlebot3") == "turtlebot3"
        assert validate_model_name("my_robot_1") == "my_robot_1"
        assert validate_model_name("test-model") == "test-model"

    def test_validate_model_name_invalid_start(self):
        """Test model name starting with number."""
        with pytest.raises(InvalidParameterError):
            validate_model_name("123_invalid")

    def test_validate_model_name_invalid_chars(self):
        """Test model name with invalid characters."""
        with pytest.raises(InvalidParameterError):
            validate_model_name("model with spaces")

    def test_validate_model_name_too_long(self):
        """Test model name too long."""
        with pytest.raises(InvalidParameterError):
            validate_model_name("a" * 65)

    def test_validate_model_name_empty(self):
        """Test empty model name."""
        with pytest.raises(MissingParameterError):
            validate_model_name("")

    def test_validate_sensor_type_valid(self):
        """Test valid sensor types."""
        for sensor_type in VALID_SENSOR_TYPES:
            assert validate_sensor_type(sensor_type) == sensor_type

    def test_validate_sensor_type_case_insensitive(self):
        """Test sensor type is case-insensitive."""
        assert validate_sensor_type("LIDAR") == "lidar"
        assert validate_sensor_type("Camera") == "camera"

    def test_validate_sensor_type_invalid(self):
        """Test invalid sensor type."""
        with pytest.raises(InvalidParameterError):
            validate_sensor_type("invalid_sensor")

    def test_validate_timeout_valid(self):
        """Test valid timeout."""
        assert validate_timeout(5.0) == 5.0

    def test_validate_timeout_too_small(self):
        """Test timeout too small."""
        with pytest.raises(InvalidParameterError):
            validate_timeout(0.05, min_timeout=0.1)

    def test_validate_timeout_too_large(self):
        """Test timeout too large."""
        with pytest.raises(InvalidParameterError):
            validate_timeout(400.0, max_timeout=300.0)

    def test_validate_positive_valid(self):
        """Test positive validation."""
        assert validate_positive(5.0, "count") == 5.0

    def test_validate_positive_zero(self):
        """Test positive validation with zero."""
        with pytest.raises(InvalidParameterError):
            validate_positive(0.0, "count")

    def test_validate_positive_negative(self):
        """Test positive validation with negative."""
        with pytest.raises(InvalidParameterError):
            validate_positive(-1.0, "count")

    def test_validate_non_negative_valid(self):
        """Test non-negative validation."""
        assert validate_non_negative(0.0, "index") == 0.0
        assert validate_non_negative(5.0, "index") == 5.0

    def test_validate_non_negative_negative(self):
        """Test non-negative with negative."""
        with pytest.raises(InvalidParameterError):
            validate_non_negative(-1.0, "index")

    def test_validate_response_format_valid(self):
        """Test valid response formats."""
        assert validate_response_format("summary") == "summary"
        assert validate_response_format("concise") == "concise"
        assert validate_response_format("filtered") == "filtered"
        assert validate_response_format("detailed") == "detailed"

    def test_validate_response_format_case_insensitive(self):
        """Test response format is case-insensitive."""
        assert validate_response_format("SUMMARY") == "summary"

    def test_validate_response_format_invalid(self):
        """Test invalid response format."""
        with pytest.raises(InvalidParameterError):
            validate_response_format("invalid")


# Test Converters:

class TestConverters:
    """Test conversion functions."""

    def test_euler_to_quaternion_identity(self):
        """Test identity rotation."""
        q = euler_to_quaternion(0.0, 0.0, 0.0)
        assert q == pytest.approx((0.0, 0.0, 0.0, 1.0))

    def test_euler_to_quaternion_90deg_z(self):
        """Test 90 degree rotation around Z."""
        q = euler_to_quaternion(0.0, 0.0, math.pi/2)
        # Expected quaternion for 90° Z rotation:
        assert q[0] == pytest.approx(0.0, abs=1e-6)
        assert q[1] == pytest.approx(0.0, abs=1e-6)
        assert q[2] == pytest.approx(0.707107, abs=1e-5)
        assert q[3] == pytest.approx(0.707107, abs=1e-5)

    def test_quaternion_to_euler_identity(self):
        """Test identity quaternion to Euler."""
        roll, pitch, yaw = quaternion_to_euler(0.0, 0.0, 0.0, 1.0)
        assert roll == pytest.approx(0.0, abs=1e-6)
        assert pitch == pytest.approx(0.0, abs=1e-6)
        assert yaw == pytest.approx(0.0, abs=1e-6)

    def test_quaternion_to_euler_90deg_z(self):
        """Test 90 degree Z rotation quaternion to Euler."""
        roll, pitch, yaw = quaternion_to_euler(0.0, 0.0, 0.707107, 0.707107)
        assert roll == pytest.approx(0.0, abs=1e-5)
        assert pitch == pytest.approx(0.0, abs=1e-5)
        assert yaw == pytest.approx(math.pi/2, abs=1e-5)

    def test_euler_quaternion_roundtrip(self):
        """Test Euler -> Quaternion -> Euler roundtrip."""
        original_roll, original_pitch, original_yaw = 0.1, 0.2, 0.3

        # Convert to quaternion:
        q = euler_to_quaternion(original_roll, original_pitch, original_yaw)

        # Convert back:
        roll, pitch, yaw = quaternion_to_euler(*q)

        assert roll == pytest.approx(original_roll, abs=1e-5)
        assert pitch == pytest.approx(original_pitch, abs=1e-5)
        assert yaw == pytest.approx(original_yaw, abs=1e-5)


# Test Geometry:

class TestGeometry:
    """Test geometry utilities."""

    def test_quaternion_normalize(self):
        """Test quaternion normalization."""
        q = quaternion_normalize((1.0, 1.0, 1.0, 1.0))
        magnitude = math.sqrt(sum(x*x for x in q))
        assert magnitude == pytest.approx(1.0)

    def test_quaternion_conjugate(self):
        """Test quaternion conjugate."""
        q = (0.1, 0.2, 0.3, 0.9)
        q_conj = quaternion_conjugate(q)
        assert q_conj == (-0.1, -0.2, -0.3, 0.9)

    def test_quaternion_inverse(self):
        """Test quaternion inverse."""
        q = (0.0, 0.0, 0.707107, 0.707107)  # 90° Z rotation
        q_inv = quaternion_inverse(q)

        # q * q_inv should be identity:
        q_identity = quaternion_multiply(q, q_inv)
        assert q_identity[3] == pytest.approx(1.0, abs=1e-5)

    def test_quaternion_multiply(self):
        """Test quaternion multiplication."""
        # 90° Z rotation:
        q_z = euler_to_quaternion(0, 0, math.pi/2)
        # 90° X rotation:
        q_x = euler_to_quaternion(math.pi/2, 0, 0)

        # Compose:
        q_result = quaternion_multiply(q_z, q_x)
        assert len(q_result) == 4

    def test_quaternion_slerp_halfway(self):
        """Test SLERP at t=0.5."""
        q1 = (0, 0, 0, 1)  # Identity
        q2 = euler_to_quaternion(0, 0, math.pi/2)  # 90° Z

        q_mid = quaternion_slerp(q1, q2, 0.5)

        # Should be 45° rotation:
        _, _, yaw = quaternion_to_euler(*q_mid)
        assert yaw == pytest.approx(math.pi/4, abs=1e-5)

    def test_quaternion_slerp_endpoints(self):
        """Test SLERP at t=0 and t=1."""
        q1 = (0, 0, 0, 1)
        q2 = euler_to_quaternion(0, 0, math.pi/2)

        # At t=0, should be q1:
        q_start = quaternion_slerp(q1, q2, 0.0)
        assert all(abs(a - b) < 1e-5 for a, b in zip(q_start, q1))

        # At t=1, should be q2:
        q_end = quaternion_slerp(q1, q2, 1.0)
        assert all(abs(a - b) < 1e-5 for a, b in zip(q_end, q2))

    def test_rotate_vector(self):
        """Test vector rotation."""
        v = (1.0, 0.0, 0.0)  # X-axis
        q = euler_to_quaternion(0, 0, math.pi/2)  # 90° Z rotation

        v_rotated = rotate_vector(v, q)

        # Should point along Y-axis:
        assert v_rotated[0] == pytest.approx(0.0, abs=1e-5)
        assert v_rotated[1] == pytest.approx(1.0, abs=1e-5)
        assert v_rotated[2] == pytest.approx(0.0, abs=1e-5)

    def test_distance_3d(self):
        """Test 3D distance."""
        p1 = (0, 0, 0)
        p2 = (3, 4, 0)
        dist = distance_3d(p1, p2)
        assert dist == pytest.approx(5.0)

    def test_distance_2d(self):
        """Test 2D distance."""
        p1 = (0, 0)
        p2 = (3, 4)
        dist = distance_2d(p1, p2)
        assert dist == pytest.approx(5.0)

    def test_angle_between_vectors(self):
        """Test angle between vectors."""
        v1 = (1, 0, 0)  # X-axis
        v2 = (0, 1, 0)  # Y-axis

        angle = angle_between_vectors(v1, v2)
        assert angle == pytest.approx(math.pi/2)

    def test_quaternion_angle_diff(self):
        """Test angle difference between quaternions."""
        q1 = euler_to_quaternion(0, 0, 0)
        q2 = euler_to_quaternion(0, 0, math.pi/2)

        angle = quaternion_angle_diff(q1, q2)
        assert angle == pytest.approx(math.pi/2, abs=1e-5)

    def test_normalize_angle(self):
        """Test angle normalization."""
        # 3π should normalize to -π:
        angle = normalize_angle(3 * math.pi)
        assert angle == pytest.approx(-math.pi, abs=1e-5)

        # -3π should normalize to π:
        angle = normalize_angle(-3 * math.pi)
        assert angle == pytest.approx(math.pi, abs=1e-5)

    def test_degrees_radians_conversion(self):
        """Test degrees/radians conversion."""
        rad = degrees_to_radians(90.0)
        assert rad == pytest.approx(math.pi/2)

        deg = radians_to_degrees(math.pi/2)
        assert deg == pytest.approx(90.0)

    def test_transform_compose(self):
        """Test transform composition."""
        # Move 1m in X:
        t1 = ((1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
        # Move 1m in Y:
        t2 = ((0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))

        # Compose:
        t_result = transform_compose(t1, t2)

        # Should be at (1, 1, 0):
        pos = t_result[0]
        assert pos[0] == pytest.approx(1.0)
        assert pos[1] == pytest.approx(1.0)
        assert pos[2] == pytest.approx(0.0)

    def test_transform_inverse(self):
        """Test transform inverse."""
        t = ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0))
        t_inv = transform_inverse(t)

        # Compose with original should give identity:
        t_identity = transform_compose(t, t_inv)

        # Position should be close to (0, 0, 0):
        pos = t_identity[0]
        assert pos[0] == pytest.approx(0.0, abs=1e-5)
        assert pos[1] == pytest.approx(0.0, abs=1e-5)
        assert pos[2] == pytest.approx(0.0, abs=1e-5)


# Test Exceptions:

class TestExceptions:
    """Test exception classes."""

    def test_gazebo_mcp_error_base(self):
        """Test base GazeboMCPError."""
        err = GazeboMCPError(
            message="Test error",
            error_code="TEST_ERROR",
            suggestions=["Fix 1"],
            example_fix="example"
        )

        assert str(err) == "Test error"
        assert err.error_code == "TEST_ERROR"
        assert len(err.suggestions) == 1
        assert err.example_fix == "example"

    def test_exception_to_dict(self):
        """Test exception to_dict method."""
        err = InvalidParameterError("param", "value", "expected")
        result = err.to_dict()

        assert "error" in result
        assert "error_code" in result
        assert "suggestions" in result

    def test_invalid_parameter_error(self):
        """Test InvalidParameterError."""
        err = InvalidParameterError("x", 100, "value <= 10")

        assert "x" in err.message
        assert "100" in err.message
        assert err.error_code == "INVALID_PARAMETER"

    def test_missing_parameter_error(self):
        """Test MissingParameterError."""
        err = MissingParameterError("model_name")

        assert "model_name" in err.message
        assert err.error_code == "MISSING_PARAMETER"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
