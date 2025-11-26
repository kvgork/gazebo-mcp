"""
Gazebo MCP Utilities.

Common utilities for Gazebo MCP server:
- OperationResult: Standardized response format
- Error codes and helpers
- Exceptions: Structured exception hierarchy
- Type definitions
"""

from .operation_result import (
    OperationResult,
    ErrorCodes,
    success_result,
    error_result,
    model_not_found_error,
    ros2_not_connected_error,
    gazebo_not_running_error,
    invalid_parameter_error,
    operation_timeout_error,
)

from .exceptions import (
    GazeboMCPError,
    ROS2Error,
    ROS2NotConnectedError,
    ROS2ConnectionLostError,
    ROS2NodeError,
    ROS2TopicError,
    ROS2ServiceError,
    GazeboError,
    GazeboNotRunningError,
    GazeboTimeoutError,
    SimulationError,
    ModelError,
    ModelNotFoundError,
    ModelSpawnError,
    ModelDeleteError,
    ModelAlreadyExistsError,
    SensorError,
    SensorNotFoundError,
    SensorDataUnavailableError,
    SensorTypeInvalidError,
    WorldError,
    WorldLoadError,
    WorldSaveError,
    WorldInvalidError,
    ParameterError,
    InvalidParameterError,
    MissingParameterError,
    OperationTimeoutError,
)

__all__ = [
    # OperationResult
    "OperationResult",
    "ErrorCodes",
    "success_result",
    "error_result",
    "model_not_found_error",
    "ros2_not_connected_error",
    "gazebo_not_running_error",
    "invalid_parameter_error",
    "operation_timeout_error",
    # Exceptions
    "GazeboMCPError",
    "ROS2Error",
    "ROS2NotConnectedError",
    "ROS2ConnectionLostError",
    "ROS2NodeError",
    "ROS2TopicError",
    "ROS2ServiceError",
    "GazeboError",
    "GazeboNotRunningError",
    "GazeboTimeoutError",
    "SimulationError",
    "ModelError",
    "ModelNotFoundError",
    "ModelSpawnError",
    "ModelDeleteError",
    "ModelAlreadyExistsError",
    "SensorError",
    "SensorNotFoundError",
    "SensorDataUnavailableError",
    "SensorTypeInvalidError",
    "WorldError",
    "WorldLoadError",
    "WorldSaveError",
    "WorldInvalidError",
    "ParameterError",
    "InvalidParameterError",
    "MissingParameterError",
    "OperationTimeoutError",
]
