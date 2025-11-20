"""
Unit tests for validators module.

Tests all validation functions for input sanitization and error handling.
"""

import pytest
from pathlib import Path
import sys

# Add project to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.utils import validators
from gazebo_mcp.utils.exceptions import InvalidParameterError, MissingParameterError


class TestValidateModelName:
    """Tests for validate_model_name function."""

    def test_valid_model_names(self):
        """Test that valid model names pass validation."""
        valid_names = [
            "robot1",
            "my_robot",
            "robot-123",
            "RobotModel",
            "a",  # Single character
            "robot_model_123",
        ]
        for name in valid_names:
            result = validators.validate_model_name(name)
            assert result == name, f"Valid name '{name}' should pass"

    def test_invalid_model_names(self):
        """Test that invalid model names raise ValidationError."""
        # Empty string raises MissingParameterError
        with pytest.raises(MissingParameterError):
            validators.validate_model_name("")

        # Invalid names raise InvalidParameterError
        invalid_names = [
            " ",  # Whitespace
            "robot name",  # Space in name
            "robot!",  # Invalid character
            "robot@123",  # Invalid character
            "robot#model",  # Invalid character
            "123robot",  # Starts with number
        ]
        for name in invalid_names:
            with pytest.raises(InvalidParameterError):
                validators.validate_model_name(name)

    def test_model_name_max_length(self):
        """Test model name length limits."""
        # Validator has 64 character limit
        valid_name = "a" * 64
        result = validators.validate_model_name(valid_name)
        assert result == valid_name

        # Names over 64 characters should fail
        too_long = "a" * 65
        with pytest.raises(InvalidParameterError):
            validators.validate_model_name(too_long)


class TestValidatePosition:
    """Tests for validate_position function."""

    def test_valid_positions(self):
        """Test that valid positions pass validation."""
        # Standard positions
        assert validators.validate_position(0.0, 0.0, 0.0) == (0.0, 0.0, 0.0)
        assert validators.validate_position(1.5, -2.3, 4.7) == (1.5, -2.3, 4.7)

        # Edge cases
        assert validators.validate_position(-100.0, 100.0, 0.0) == (-100.0, 100.0, 0.0)

    def test_position_type_validation(self):
        """Test that non-numeric positions raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_position("not", "a", "number")

        with pytest.raises(InvalidParameterError):
            validators.validate_position(1.0, None, 3.0)

    def test_position_extreme_values(self):
        """Test extreme position values."""
        # Very large values should raise error when max_coord is set
        with pytest.raises(InvalidParameterError):
            validators.validate_position(10000.0, 0.0, 0.0, max_coord=1000.0)

        # Very negative values should raise error when min_coord is set
        with pytest.raises(InvalidParameterError):
            validators.validate_position(0.0, -10000.0, 0.0, min_coord=-1000.0)


class TestValidateOrientation:
    """Tests for validate_orientation function."""

    def test_valid_orientations(self):
        """Test that valid orientations pass validation."""
        # Zero rotation
        assert validators.validate_orientation(0.0, 0.0, 0.0) == (0.0, 0.0, 0.0)

        # Standard rotations
        assert validators.validate_orientation(1.57, 0.0, 3.14) == (1.57, 0.0, 3.14)

        # Negative values
        assert validators.validate_orientation(-1.57, -0.5, -3.14) == (-1.57, -0.5, -3.14)

    def test_orientation_normalization(self):
        """Test that orientations are accepted as-is (no normalization)."""
        # Validator accepts values without normalization
        roll, pitch, yaw = validators.validate_orientation(7.0, -7.0, 10.0)
        assert roll == 7.0
        assert pitch == -7.0
        assert yaw == 10.0

    def test_orientation_type_validation(self):
        """Test that non-numeric orientations raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_orientation("not", "a", "number")


class TestValidateTimeout:
    """Tests for validate_timeout function."""

    def test_valid_timeouts(self):
        """Test that valid timeouts pass validation."""
        assert validators.validate_timeout(1.0) == 1.0
        assert validators.validate_timeout(10.5) == 10.5
        assert validators.validate_timeout(0.1) == 0.1

    def test_negative_timeout(self):
        """Test that negative timeouts raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_timeout(-1.0)

        with pytest.raises(InvalidParameterError):
            validators.validate_timeout(-0.001)

    def test_zero_timeout(self):
        """Test that zero timeout raises ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_timeout(0.0)

    def test_excessive_timeout(self):
        """Test that very large timeouts raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_timeout(1000.0)

    def test_timeout_type_validation(self):
        """Test that non-numeric timeouts raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_timeout("not a number")

        with pytest.raises(InvalidParameterError):
            validators.validate_timeout(None)


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_file_paths(self):
        """Test that valid file paths pass validation."""
        # Relative path
        path = validators.validate_file_path("test.txt", must_exist=False)
        assert isinstance(path, Path)

        # Absolute path
        path = validators.validate_file_path("/tmp/test.txt", must_exist=False)
        assert isinstance(path, Path)
        assert path.is_absolute()

    def test_path_must_exist(self):
        """Test that non-existent paths raise ValidationError when required."""
        with pytest.raises(InvalidParameterError):
            validators.validate_file_path("/nonexistent/file.txt", must_exist=True)

    def test_empty_path(self):
        """Test that empty paths raise MissingParameterError."""
        with pytest.raises(MissingParameterError):
            validators.validate_file_path("", must_exist=False)


class TestValidateSensorType:
    """Tests for validate_sensor_type function."""

    def test_valid_sensor_types(self):
        """Test that valid sensor types pass validation."""
        valid_types = ["camera", "lidar", "imu", "gps"]
        for sensor_type in valid_types:
            result = validators.validate_sensor_type(sensor_type)
            assert result == sensor_type

    def test_invalid_sensor_types(self):
        """Test that invalid sensor types raise ValidationError."""
        # Empty string raises MissingParameterError
        with pytest.raises(MissingParameterError):
            validators.validate_sensor_type("")

        # Invalid types raise InvalidParameterError
        invalid_types = ["invalid", "radar", "ultrasonic"]
        for sensor_type in invalid_types:
            with pytest.raises(InvalidParameterError):
                validators.validate_sensor_type(sensor_type)

    def test_case_insensitive(self):
        """Test that sensor type validation is case-insensitive."""
        assert validators.validate_sensor_type("Camera") == "camera"
        assert validators.validate_sensor_type("LIDAR") == "lidar"
        assert validators.validate_sensor_type("Imu") == "imu"


class TestValidatePositive:
    """Tests for validate_positive function."""

    def test_valid_positive_numbers(self):
        """Test that positive numbers pass validation."""
        assert validators.validate_positive(1.0, "value") == 1.0
        assert validators.validate_positive(100.5, "value") == 100.5
        assert validators.validate_positive(0.001, "value") == 0.001

    def test_zero_value(self):
        """Test that zero raises ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_positive(0.0, "value")

    def test_negative_value(self):
        """Test that negative numbers raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_positive(-1.0, "value")

    def test_non_numeric_value(self):
        """Test that non-numeric values raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_positive("not a number", "value")


class TestValidateNonNegative:
    """Tests for validate_non_negative function."""

    def test_valid_non_negative_numbers(self):
        """Test that non-negative numbers pass validation."""
        assert validators.validate_non_negative(0.0, "value") == 0.0
        assert validators.validate_non_negative(1.0, "value") == 1.0
        assert validators.validate_non_negative(100.5, "value") == 100.5

    def test_negative_value(self):
        """Test that negative numbers raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_non_negative(-1.0, "value")

        with pytest.raises(InvalidParameterError):
            validators.validate_non_negative(-0.001, "value")


class TestValidateResponseFormat:
    """Tests for validate_response_format function."""

    def test_valid_response_formats(self):
        """Test that valid response formats pass validation."""
        valid_formats = ["summary", "filtered", "detailed", "concise"]
        for fmt in valid_formats:
            result = validators.validate_response_format(fmt)
            assert result == fmt

    def test_invalid_response_format(self):
        """Test that invalid response formats raise ValidationError."""
        with pytest.raises(InvalidParameterError):
            validators.validate_response_format("invalid")

        # Empty string raises MissingParameterError
        with pytest.raises(MissingParameterError):
            validators.validate_response_format("")
