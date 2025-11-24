"""
Exception Hierarchy for Gazebo MCP.

Provides structured exceptions with helpful error messages for
ROS2, Gazebo, and MCP-specific errors.

Based on best practices from claude/skills/*/operations.py
"""

from typing import Optional, List


class GazeboMCPError(Exception):
    """
    Base exception for all Gazebo MCP errors.

    All exceptions inherit from this to allow catching all MCP-related errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        suggestions: List of suggested fixes
        example_fix: Example code to fix the issue
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        example_fix: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.suggestions = suggestions or []
        self.example_fix = example_fix
        super().__init__(self.message)

    def to_dict(self):
        """Convert exception to dictionary for OperationResult."""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "suggestions": self.suggestions,
            "example_fix": self.example_fix
        }


# ROS2 Connection Exceptions:

class ROS2Error(GazeboMCPError):
    """Base exception for ROS2-related errors."""
    pass


class ROS2NotConnectedError(ROS2Error):
    """ROS2 connection is not established."""

    def __init__(self, message: str = "ROS2 connection not established"):
        super().__init__(
            message=message,
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Check ROS2 daemon: ros2 daemon status",
                "Restart daemon: ros2 daemon stop && ros2 daemon start",
                "Source ROS2: source /opt/ros/humble/setup.bash",
                "Check network: ping localhost"
            ],
            example_fix="# Ensure ROS2 is sourced:\nsource /opt/ros/humble/setup.bash"
        )


class ROS2ConnectionLostError(ROS2Error):
    """ROS2 connection was lost during operation."""

    def __init__(self, message: str = "ROS2 connection lost"):
        super().__init__(
            message=message,
            error_code="ROS2_CONNECTION_LOST",
            suggestions=[
                "Check if ROS2 daemon is running",
                "Verify network connectivity",
                "Check system resources (CPU, memory)",
                "Restart the MCP server"
            ]
        )


class ROS2NodeError(ROS2Error):
    """Error with ROS2 node operation."""

    def __init__(self, node_name: str, details: str):
        super().__init__(
            message=f"ROS2 node '{node_name}' error: {details}",
            error_code="ROS2_NODE_ERROR",
            suggestions=[
                f"Check node status: ros2 node list",
                f"Check node info: ros2 node info /{node_name}",
                "Check ROS2 logs for details"
            ]
        )


class ROS2TopicError(ROS2Error):
    """Error with ROS2 topic operation."""

    def __init__(self, topic_name: str, details: str):
        super().__init__(
            message=f"ROS2 topic '{topic_name}' error: {details}",
            error_code="ROS2_TOPIC_ERROR",
            suggestions=[
                f"Check topic: ros2 topic info {topic_name}",
                f"List topics: ros2 topic list",
                f"Echo topic: ros2 topic echo {topic_name}"
            ]
        )


class ROS2ServiceError(ROS2Error):
    """Error with ROS2 service operation."""

    def __init__(self, service_name: str, details: str):
        super().__init__(
            message=f"ROS2 service '{service_name}' error: {details}",
            error_code="ROS2_SERVICE_ERROR",
            suggestions=[
                f"Check service: ros2 service list",
                f"Service type: ros2 service type {service_name}",
                "Ensure Gazebo is running"
            ]
        )


# Gazebo Simulation Exceptions:

class GazeboError(GazeboMCPError):
    """Base exception for Gazebo-related errors."""
    pass


class GazeboNotRunningError(GazeboError):
    """Gazebo simulation is not running."""

    def __init__(self, message: str = "Gazebo simulation is not running"):
        super().__init__(
            message=message,
            error_code="GAZEBO_NOT_RUNNING",
            suggestions=[
                "Start Gazebo: ros2 launch gazebo_ros gazebo.launch.py",
                "Check Gazebo status: ros2 topic list | grep gazebo",
                "Check for Gazebo processes: ps aux | grep gazebo"
            ],
            example_fix="ros2 launch gazebo_ros gazebo.launch.py"
        )


class GazeboTimeoutError(GazeboError):
    """Gazebo operation timed out."""

    def __init__(self, operation: str, timeout: float):
        super().__init__(
            message=f"Gazebo operation '{operation}' timed out after {timeout}s",
            error_code="GAZEBO_TIMEOUT",
            suggestions=[
                f"Increase timeout (current: {timeout}s)",
                "Check Gazebo is responsive",
                "Check system resources (CPU, memory)",
                "Reduce simulation complexity"
            ]
        )


class GazeboServiceError(GazeboError):
    """Gazebo service call failed."""

    def __init__(self, service_name: str, details: str):
        super().__init__(
            message=f"Gazebo service '{service_name}' failed: {details}",
            error_code="GAZEBO_SERVICE_ERROR",
            suggestions=[
                "Check Gazebo is running",
                "Verify service is available",
                "Check service parameters are correct",
                "Review Gazebo logs for details"
            ]
        )


class SimulationError(GazeboError):
    """General simulation error."""

    def __init__(self, details: str):
        super().__init__(
            message=f"Simulation error: {details}",
            error_code="SIMULATION_ERROR",
            suggestions=[
                "Check Gazebo logs",
                "Verify world file is valid",
                "Check for physics engine errors"
            ]
        )


# Model Exceptions:

class ModelError(GazeboMCPError):
    """Base exception for model-related errors."""
    pass


class ModelNotFoundError(ModelError):
    """Model not found in Gazebo model path."""

    def __init__(self, model_name: str):
        super().__init__(
            message=f"Model '{model_name}' not found in Gazebo model path",
            error_code="MODEL_NOT_FOUND",
            suggestions=[
                "Check model name spelling",
                "List available models: list_models()",
                "Check GAZEBO_MODEL_PATH environment variable",
                "Download model from gazebosim.org"
            ],
            example_fix=f'# Use a standard model:\nspawn_model("turtlebot3_burger", x=0, y=0)'
        )


class ModelSpawnError(ModelError):
    """Failed to spawn model."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"Failed to spawn model '{model_name}': {reason}",
            error_code="MODEL_SPAWN_FAILED",
            suggestions=[
                "Check model SDF/URDF is valid",
                "Verify spawn position is not occupied",
                "Check Gazebo physics engine",
                "Check Gazebo logs for details"
            ]
        )


class ModelDeleteError(ModelError):
    """Failed to delete model."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"Failed to delete model '{model_name}': {reason}",
            error_code="MODEL_DELETE_FAILED",
            suggestions=[
                "Check model exists: list_models()",
                "Check model name is correct",
                "Ensure model is not locked"
            ]
        )


class ModelAlreadyExistsError(ModelError):
    """Model with this name already exists."""

    def __init__(self, model_name: str):
        super().__init__(
            message=f"Model '{model_name}' already exists in simulation",
            error_code="MODEL_ALREADY_EXISTS",
            suggestions=[
                "Use a different name",
                "Delete existing model first: delete_model('{model_name}')",
                "List existing models: list_models()"
            ]
        )


# Sensor Exceptions:

class SensorError(GazeboMCPError):
    """Base exception for sensor-related errors."""
    pass


class SensorNotFoundError(SensorError):
    """Sensor not found."""

    def __init__(self, sensor_name: str):
        super().__init__(
            message=f"Sensor '{sensor_name}' not found",
            error_code="SENSOR_NOT_FOUND",
            suggestions=[
                "List available sensors: list_sensors()",
                "Check sensor name spelling",
                "Verify model with sensor is spawned"
            ]
        )


class SensorDataUnavailableError(SensorError):
    """Sensor data is not available."""

    def __init__(self, sensor_name: str, reason: str):
        super().__init__(
            message=f"Sensor '{sensor_name}' data unavailable: {reason}",
            error_code="SENSOR_DATA_UNAVAILABLE",
            suggestions=[
                "Check sensor is enabled",
                "Verify simulation is running",
                "Check sensor topic: ros2 topic echo /sensor_topic"
            ]
        )


class SensorTypeInvalidError(SensorError):
    """Invalid sensor type."""

    def __init__(self, sensor_type: str, valid_types: List[str]):
        super().__init__(
            message=f"Invalid sensor type '{sensor_type}'",
            error_code="SENSOR_TYPE_INVALID",
            suggestions=[
                f"Valid types: {', '.join(valid_types)}",
                "Check sensor documentation"
            ]
        )


# World Exceptions:

class WorldError(GazeboMCPError):
    """Base exception for world-related errors."""
    pass


class WorldLoadError(WorldError):
    """Failed to load world."""

    def __init__(self, world_name: str, reason: str):
        super().__init__(
            message=f"Failed to load world '{world_name}': {reason}",
            error_code="WORLD_LOAD_FAILED",
            suggestions=[
                "Check world file exists",
                "Validate world file: gz sdf -k world.sdf",
                "Check file permissions",
                "Check SDF syntax"
            ]
        )


class WorldSaveError(WorldError):
    """Failed to save world."""

    def __init__(self, world_name: str, reason: str):
        super().__init__(
            message=f"Failed to save world '{world_name}': {reason}",
            error_code="WORLD_SAVE_FAILED",
            suggestions=[
                "Check write permissions",
                "Verify disk space",
                "Check file path is valid"
            ]
        )


class WorldInvalidError(WorldError):
    """World file is invalid."""

    def __init__(self, world_name: str, validation_errors: List[str]):
        errors_str = "\n  - ".join(validation_errors)
        super().__init__(
            message=f"World '{world_name}' is invalid:\n  - {errors_str}",
            error_code="WORLD_INVALID",
            suggestions=[
                "Validate with: gz sdf -k world.sdf",
                "Check SDF format documentation",
                "Fix syntax errors"
            ]
        )


# Parameter Exceptions:

class ParameterError(GazeboMCPError):
    """Base exception for parameter errors."""
    pass


class InvalidParameterError(ParameterError):
    """Invalid parameter value."""

    def __init__(self, param_name: str, param_value, expected: str):
        super().__init__(
            message=f"Invalid parameter '{param_name}': got {param_value}, expected {expected}",
            error_code="INVALID_PARAMETER",
            suggestions=[
                f"Check {param_name} value",
                f"Expected: {expected}",
                "See function documentation for valid values"
            ],
            example_fix=f"# Correct usage:\n# {param_name}={expected}"
        )


class MissingParameterError(ParameterError):
    """Required parameter is missing."""

    def __init__(self, param_name: str):
        super().__init__(
            message=f"Required parameter '{param_name}' is missing",
            error_code="MISSING_PARAMETER",
            suggestions=[
                f"Provide {param_name} parameter",
                "Check function documentation for required parameters"
            ]
        )


# Timeout Exception:

class OperationTimeoutError(GazeboMCPError):
    """Operation timed out."""

    def __init__(self, operation: str, timeout: float):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout}s",
            error_code="OPERATION_TIMEOUT",
            suggestions=[
                f"Increase timeout (current: {timeout}s)",
                "Check operation is not blocked",
                "Verify ROS2/Gazebo are responsive"
            ],
            example_fix=f"# Increase timeout:\n# {operation}(timeout={timeout * 2})"
        )
