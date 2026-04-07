"""
Input Validators for Gazebo MCP.

Provides validation functions for common parameter types:
- Coordinates (x, y, z)
- Orientations (roll, pitch, yaw, quaternions)
- Model names
- Sensor types
- Timeouts and numeric ranges
- File paths

Raises appropriate exceptions with helpful messages when validation fails.
"""

import re
from typing import Optional, List, Tuple, Union
from pathlib import Path
import math

from .exceptions import InvalidParameterError, MissingParameterError


# Coordinate validation:

def validate_coordinate(
    value: float,
    name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    """
    Validate a coordinate value.

    Args:
        value: Coordinate value to validate
        name: Parameter name (for error messages)
        min_value: Optional minimum value
        max_value: Optional maximum value

    Returns:
        Validated coordinate value

    Raises:
        InvalidParameterError: If validation fails

    Example:
        >>> x = validate_coordinate(1.5, "x", min_value=-10, max_value=10)
        >>> # Returns: 1.5
        >>>
        >>> x = validate_coordinate(100, "x", max_value=10)
        >>> # Raises: InvalidParameterError
    """
    # Check type:
    if not isinstance(value, (int, float)):
        raise InvalidParameterError(
            name,
            value,
            "numeric value (int or float)"
        )

    # Check if NaN or Inf:
    if math.isnan(value) or math.isinf(value):
        raise InvalidParameterError(
            name,
            value,
            "finite numeric value (not NaN or Inf)"
        )

    # Check range:
    if min_value is not None and value < min_value:
        raise InvalidParameterError(
            name,
            value,
            f"value >= {min_value}"
        )

    if max_value is not None and value > max_value:
        raise InvalidParameterError(
            name,
            value,
            f"value <= {max_value}"
        )

    return float(value)


def validate_position(
    x: float,
    y: float,
    z: float,
    min_coord: Optional[float] = None,
    max_coord: Optional[float] = None
) -> Tuple[float, float, float]:
    """
    Validate a 3D position.

    Args:
        x, y, z: Position coordinates
        min_coord: Optional minimum coordinate value
        max_coord: Optional maximum coordinate value

    Returns:
        Validated (x, y, z) tuple

    Example:
        >>> pos = validate_position(1.0, 2.0, 0.5)
        >>> # Returns: (1.0, 2.0, 0.5)
    """
    x = validate_coordinate(x, "x", min_coord, max_coord)
    y = validate_coordinate(y, "y", min_coord, max_coord)
    z = validate_coordinate(z, "z", min_coord, max_coord)

    return (x, y, z)


# Orientation validation:

def validate_angle(value: float, name: str, radians: bool = True) -> float:
    """
    Validate an angle.

    Args:
        value: Angle value
        name: Parameter name
        radians: If True, expect radians; if False, expect degrees

    Returns:
        Validated angle (always in radians)

    Example:
        >>> roll = validate_angle(0.5, "roll")  # Radians
        >>> yaw = validate_angle(90, "yaw", radians=False)  # Degrees -> radians
    """
    if not isinstance(value, (int, float)):
        raise InvalidParameterError(name, value, "numeric value")

    if math.isnan(value) or math.isinf(value):
        raise InvalidParameterError(name, value, "finite numeric value")

    # Convert to radians if needed:
    if radians:
        return float(value)
    else:
        return math.radians(value)


def validate_orientation(
    roll: float,
    pitch: float,
    yaw: float,
    radians: bool = True
) -> Tuple[float, float, float]:
    """
    Validate Euler angles orientation.

    Args:
        roll, pitch, yaw: Euler angles
        radians: If True, angles are in radians; if False, in degrees

    Returns:
        Validated (roll, pitch, yaw) tuple in radians

    Example:
        >>> orient = validate_orientation(0.0, 0.0, 1.57)  # Radians
        >>> orient = validate_orientation(0, 0, 90, radians=False)  # Degrees
    """
    roll = validate_angle(roll, "roll", radians)
    pitch = validate_angle(pitch, "pitch", radians)
    yaw = validate_angle(yaw, "yaw", radians)

    return (roll, pitch, yaw)


def validate_quaternion(x: float, y: float, z: float, w: float) -> Tuple[float, float, float, float]:
    """
    Validate a quaternion.

    Args:
        x, y, z, w: Quaternion components

    Returns:
        Validated (x, y, z, w) tuple

    Raises:
        InvalidParameterError: If quaternion is not normalized

    Example:
        >>> q = validate_quaternion(0.0, 0.0, 0.0, 1.0)  # Identity quaternion
    """
    # Validate each component:
    for val, name in [(x, "qx"), (y, "qy"), (z, "qz"), (w, "qw")]:
        if not isinstance(val, (int, float)):
            raise InvalidParameterError(name, val, "numeric value")
        if math.isnan(val) or math.isinf(val):
            raise InvalidParameterError(name, val, "finite numeric value")

    # Check if normalized (within tolerance):
    magnitude = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isclose(magnitude, 1.0, rel_tol=1e-3):
        raise InvalidParameterError(
            "quaternion",
            f"(x={x}, y={y}, z={z}, w={w})",
            f"normalized quaternion (magnitude should be 1.0, got {magnitude:.4f})"
        )

    return (float(x), float(y), float(z), float(w))


# Name validation:

def validate_model_name(name: str) -> str:
    """
    Validate a model name.

    Model names must:
    - Be non-empty
    - Start with a letter
    - Contain only alphanumeric, underscore, dash
    - Be <= 64 characters

    Args:
        name: Model name to validate

    Returns:
        Validated model name

    Raises:
        InvalidParameterError: If validation fails

    Example:
        >>> name = validate_model_name("turtlebot3_burger")  # Valid
        >>> name = validate_model_name("123_invalid")  # Invalid - starts with number
    """
    if not name:
        raise MissingParameterError("model_name")

    if not isinstance(name, str):
        raise InvalidParameterError("model_name", name, "string")

    # Check length:
    if len(name) > 64:
        raise InvalidParameterError(
            "model_name",
            name,
            "string with <= 64 characters"
        )

    # Check format:
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        raise InvalidParameterError(
            "model_name",
            name,
            "string starting with letter, containing only alphanumeric, underscore, dash"
        )

    return name


def validate_entity_name(name: str, entity_type: str = "entity") -> str:
    """
    Validate a generic entity name (model, sensor, world, etc.).

    Args:
        name: Entity name to validate
        entity_type: Type of entity (for error messages)

    Returns:
        Validated entity name

    Example:
        >>> name = validate_entity_name("my_sensor", "sensor")
    """
    if not name:
        raise MissingParameterError(f"{entity_type}_name")

    if not isinstance(name, str):
        raise InvalidParameterError(f"{entity_type}_name", name, "string")

    if len(name) > 64:
        raise InvalidParameterError(
            f"{entity_type}_name",
            name,
            "string with <= 64 characters"
        )

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        raise InvalidParameterError(
            f"{entity_type}_name",
            name,
            "string starting with letter, containing only alphanumeric, underscore, dash"
        )

    return name


# Sensor type validation:

VALID_SENSOR_TYPES = [
    "camera",
    "depth_camera",
    "rgbd_camera",
    "lidar",
    "laser",
    "imu",
    "gps",
    "magnetometer",
    "altimeter",
    "sonar",
    "contact",
    "force_torque"
]


def validate_sensor_type(sensor_type: str) -> str:
    """
    Validate sensor type.

    Args:
        sensor_type: Sensor type to validate

    Returns:
        Validated sensor type (lowercase)

    Raises:
        InvalidParameterError: If sensor type is invalid

    Example:
        >>> stype = validate_sensor_type("lidar")  # Valid
        >>> stype = validate_sensor_type("CAMERA")  # Valid (normalized to lowercase)
        >>> stype = validate_sensor_type("invalid")  # Invalid
    """
    if not sensor_type:
        raise MissingParameterError("sensor_type")

    if not isinstance(sensor_type, str):
        raise InvalidParameterError("sensor_type", sensor_type, "string")

    sensor_type_lower = sensor_type.lower()

    if sensor_type_lower not in VALID_SENSOR_TYPES:
        raise InvalidParameterError(
            "sensor_type",
            sensor_type,
            f"one of: {', '.join(VALID_SENSOR_TYPES)}"
        )

    return sensor_type_lower


# Numeric range validation:

def validate_timeout(timeout: float, min_timeout: float = 0.1, max_timeout: float = 300.0) -> float:
    """
    Validate a timeout value.

    Args:
        timeout: Timeout in seconds
        min_timeout: Minimum allowed timeout
        max_timeout: Maximum allowed timeout

    Returns:
        Validated timeout

    Example:
        >>> timeout = validate_timeout(5.0)  # 5 seconds
    """
    if not isinstance(timeout, (int, float)):
        raise InvalidParameterError("timeout", timeout, "numeric value (seconds)")

    if timeout < min_timeout:
        raise InvalidParameterError("timeout", timeout, f">= {min_timeout} seconds")

    if timeout > max_timeout:
        raise InvalidParameterError("timeout", timeout, f"<= {max_timeout} seconds")

    return float(timeout)


def validate_positive(value: Union[int, float], name: str) -> Union[int, float]:
    """
    Validate that a value is positive.

    Args:
        value: Value to validate
        name: Parameter name

    Returns:
        Validated value

    Example:
        >>> count = validate_positive(10, "count")
    """
    if not isinstance(value, (int, float)):
        raise InvalidParameterError(name, value, "numeric value")

    if value <= 0:
        raise InvalidParameterError(name, value, "positive value (> 0)")

    return value


def validate_non_negative(value: Union[int, float], name: str) -> Union[int, float]:
    """
    Validate that a value is non-negative.

    Args:
        value: Value to validate
        name: Parameter name

    Returns:
        Validated value

    Example:
        >>> index = validate_non_negative(0, "index")
    """
    if not isinstance(value, (int, float)):
        raise InvalidParameterError(name, value, "numeric value")

    if value < 0:
        raise InvalidParameterError(name, value, "non-negative value (>= 0)")

    return value


# File path validation:

def validate_file_path(path: str, must_exist: bool = False) -> Path:
    """
    Validate a file path.

    Args:
        path: File path to validate
        must_exist: If True, file must exist

    Returns:
        Validated Path object

    Raises:
        InvalidParameterError: If validation fails

    Example:
        >>> world_file = validate_file_path("worlds/my_world.sdf", must_exist=True)
    """
    if not path:
        raise MissingParameterError("file_path")

    if not isinstance(path, str):
        raise InvalidParameterError("file_path", path, "string")

    path_obj = Path(path)

    if must_exist and not path_obj.exists():
        raise InvalidParameterError(
            "file_path",
            path,
            f"existing file (file not found: {path})"
        )

    return path_obj


def validate_directory_path(path: str, must_exist: bool = False, create: bool = False) -> Path:
    """
    Validate a directory path.

    Args:
        path: Directory path to validate
        must_exist: If True, directory must exist
        create: If True, create directory if it doesn't exist

    Returns:
        Validated Path object

    Example:
        >>> log_dir = validate_directory_path("/var/log/gazebo_mcp", create=True)
    """
    if not path:
        raise MissingParameterError("directory_path")

    if not isinstance(path, str):
        raise InvalidParameterError("directory_path", path, "string")

    path_obj = Path(path)

    if must_exist and not path_obj.exists():
        raise InvalidParameterError(
            "directory_path",
            path,
            f"existing directory (not found: {path})"
        )

    if create and not path_obj.exists():
        path_obj.mkdir(parents=True, exist_ok=True)

    return path_obj


# Response format validation:

VALID_RESPONSE_FORMATS = ["summary", "concise", "filtered", "detailed"]


def validate_response_format(format: str) -> str:
    """
    Validate response_format parameter.

    Args:
        format: Response format to validate

    Returns:
        Validated format (lowercase)

    Example:
        >>> fmt = validate_response_format("filtered")
    """
    if not format:
        raise MissingParameterError("response_format")

    if not isinstance(format, str):
        raise InvalidParameterError("response_format", format, "string")

    format_lower = format.lower()

    if format_lower not in VALID_RESPONSE_FORMATS:
        raise InvalidParameterError(
            "response_format",
            format,
            f"one of: {', '.join(VALID_RESPONSE_FORMATS)}"
        )

    return format_lower


# Batch validation:

def validate_parameters(
    params: dict,
    schema: dict
) -> dict:
    """
    Validate multiple parameters against a schema.

    Args:
        params: Parameters to validate
        schema: Validation schema

    Returns:
        Validated parameters

    Example:
        >>> schema = {
        ...     "x": {"type": "coordinate", "min": -10, "max": 10},
        ...     "y": {"type": "coordinate", "min": -10, "max": 10},
        ...     "model_name": {"type": "model_name"},
        ...     "timeout": {"type": "timeout", "optional": True}
        ... }
        >>> validated = validate_parameters(
        ...     {"x": 1.0, "y": 2.0, "model_name": "turtlebot3"},
        ...     schema
        ... )
    """
    validated = {}

    for param_name, param_schema in schema.items():
        # Check if parameter is required:
        if param_name not in params:
            if not param_schema.get("optional", False):
                raise MissingParameterError(param_name)
            continue

        value = params[param_name]
        param_type = param_schema.get("type")

        # Validate based on type:
        if param_type == "coordinate":
            validated[param_name] = validate_coordinate(
                value,
                param_name,
                param_schema.get("min"),
                param_schema.get("max")
            )
        elif param_type == "model_name":
            validated[param_name] = validate_model_name(value)
        elif param_type == "sensor_type":
            validated[param_name] = validate_sensor_type(value)
        elif param_type == "timeout":
            validated[param_name] = validate_timeout(value)
        elif param_type == "positive":
            validated[param_name] = validate_positive(value, param_name)
        elif param_type == "non_negative":
            validated[param_name] = validate_non_negative(value, param_name)
        elif param_type == "file_path":
            validated[param_name] = validate_file_path(value, param_schema.get("must_exist", False))
        elif param_type == "response_format":
            validated[param_name] = validate_response_format(value)
        else:
            # No validation - pass through:
            validated[param_name] = value

    return validated
