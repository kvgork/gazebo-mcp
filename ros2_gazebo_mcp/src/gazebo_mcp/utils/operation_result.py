"""
Operation Result Pattern for Agent-Friendly Responses.

Provides standardized response format with helpful error messages,
suggestions, and example fixes - making it easy for AI agents to
understand and recover from errors.

Based on: claude/skills/*/operations.py pattern
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import json


@dataclass
class OperationResult:
    """
    Standardized operation result for agent-friendly responses.

    This pattern ensures consistent error handling and provides
    agents with actionable suggestions when operations fail.

    Attributes:
        success: Whether the operation succeeded
        data: Operation result data (if successful)
        error: Human-readable error message (if failed)
        error_code: Machine-readable error code (if failed)
        suggestions: List of suggested actions to fix the error
        example_fix: Example code showing how to fix the issue
        metadata: Additional operation metadata

    Example:
        >>> # Success case:
        >>> result = OperationResult(
        ...     success=True,
        ...     data={"model_name": "turtlebot3_burger", "position": {"x": 0, "y": 0}}
        ... )

        >>> # Error case with helpful suggestions:
        >>> result = OperationResult(
        ...     success=False,
        ...     error="Model 'my_robot' not found in Gazebo model path",
        ...     error_code="MODEL_NOT_FOUND",
        ...     suggestions=[
        ...         "Check model name spelling",
        ...         "List available models: list_models()",
        ...         "Check GAZEBO_MODEL_PATH environment variable"
        ...     ],
        ...     example_fix='spawn_model("turtlebot3_burger", x=0, y=0)'
        ... )
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    suggestions: Optional[List[str]] = None
    example_fix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationResult':
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'OperationResult':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return f"OperationResult(success=True, data={self.data})"
        else:
            return f"OperationResult(success=False, error='{self.error}', code={self.error_code})"


# Common error codes for Gazebo operations:
class ErrorCodes:
    """Standard error codes for Gazebo MCP operations."""

    # ROS2 connection errors:
    ROS2_NOT_CONNECTED = "ROS2_NOT_CONNECTED"
    ROS2_CONNECTION_LOST = "ROS2_CONNECTION_LOST"
    ROS2_NODE_ERROR = "ROS2_NODE_ERROR"

    # Gazebo errors:
    GAZEBO_NOT_RUNNING = "GAZEBO_NOT_RUNNING"
    GAZEBO_TIMEOUT = "GAZEBO_TIMEOUT"
    SIMULATION_ERROR = "SIMULATION_ERROR"

    # Model errors:
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_SPAWN_FAILED = "MODEL_SPAWN_FAILED"
    MODEL_DELETE_FAILED = "MODEL_DELETE_FAILED"
    MODEL_ALREADY_EXISTS = "MODEL_ALREADY_EXISTS"

    # Sensor errors:
    SENSOR_NOT_FOUND = "SENSOR_NOT_FOUND"
    SENSOR_DATA_UNAVAILABLE = "SENSOR_DATA_UNAVAILABLE"
    SENSOR_TYPE_INVALID = "SENSOR_TYPE_INVALID"

    # World errors:
    WORLD_LOAD_FAILED = "WORLD_LOAD_FAILED"
    WORLD_SAVE_FAILED = "WORLD_SAVE_FAILED"
    WORLD_INVALID = "WORLD_INVALID"

    # Parameter errors:
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"

    # General errors:
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


def success_result(data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> OperationResult:
    """
    Create a success result.

    Args:
        data: Operation result data
        metadata: Optional metadata

    Returns:
        OperationResult with success=True
    """
    return OperationResult(
        success=True,
        data=data,
        metadata=metadata
    )


def error_result(
    error: str,
    error_code: str,
    suggestions: Optional[List[str]] = None,
    example_fix: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> OperationResult:
    """
    Create an error result with helpful suggestions.

    Args:
        error: Human-readable error message
        error_code: Machine-readable error code
        suggestions: List of suggested fixes
        example_fix: Example code to fix the issue
        metadata: Optional metadata

    Returns:
        OperationResult with success=False
    """
    return OperationResult(
        success=False,
        error=error,
        error_code=error_code,
        suggestions=suggestions or [],
        example_fix=example_fix,
        metadata=metadata
    )


# Helper functions for common error scenarios:

def model_not_found_error(model_name: str) -> OperationResult:
    """Create error result for model not found."""
    return error_result(
        error=f"Model '{model_name}' not found in Gazebo model path",
        error_code=ErrorCodes.MODEL_NOT_FOUND,
        suggestions=[
            "Check model name spelling",
            "List available models: list_models()",
            "Check GAZEBO_MODEL_PATH environment variable",
            "Download model from gazebosim.org"
        ],
        example_fix=f'# Use a standard model:\nspawn_model("turtlebot3_burger", x=0, y=0)'
    )


def ros2_not_connected_error() -> OperationResult:
    """Create error result for ROS2 not connected."""
    return error_result(
        error="ROS2 connection not established",
        error_code=ErrorCodes.ROS2_NOT_CONNECTED,
        suggestions=[
            "Check ROS2 daemon: ros2 daemon status",
            "Restart daemon: ros2 daemon stop && ros2 daemon start",
            "Source ROS2: source /opt/ros/humble/setup.bash",
            "Check network: ping localhost"
        ],
        example_fix="# Ensure ROS2 is sourced before running"
    )


def gazebo_not_running_error() -> OperationResult:
    """Create error result for Gazebo not running."""
    return error_result(
        error="Gazebo simulation is not running",
        error_code=ErrorCodes.GAZEBO_NOT_RUNNING,
        suggestions=[
            "Start Gazebo: ros2 launch gazebo_ros gazebo.launch.py",
            "Check Gazebo status: ros2 topic list | grep gazebo",
            "Check for Gazebo processes: ps aux | grep gazebo"
        ],
        example_fix="# Start Gazebo first:\n# ros2 launch gazebo_ros gazebo.launch.py"
    )


def invalid_parameter_error(param_name: str, param_value: Any, expected: str) -> OperationResult:
    """Create error result for invalid parameter."""
    return error_result(
        error=f"Invalid parameter '{param_name}': got {param_value}, expected {expected}",
        error_code=ErrorCodes.INVALID_PARAMETER,
        suggestions=[
            f"Check {param_name} value",
            f"Expected: {expected}",
            "See function documentation for valid values"
        ],
        example_fix=f"# Correct usage:\n# {param_name}={expected}"
    )


def operation_timeout_error(operation: str, timeout: int) -> OperationResult:
    """Create error result for operation timeout."""
    return error_result(
        error=f"Operation '{operation}' timed out after {timeout}s",
        error_code=ErrorCodes.OPERATION_TIMEOUT,
        suggestions=[
            f"Increase timeout (current: {timeout}s)",
            "Check Gazebo/ROS2 are responsive",
            "Check system resources (CPU, memory)"
        ],
        example_fix=f"# Increase timeout:\n# {operation}(timeout={timeout * 2})"
    )
