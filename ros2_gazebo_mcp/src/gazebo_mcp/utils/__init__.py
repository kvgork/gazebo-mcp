"""
Gazebo MCP Utilities.

Common utilities for Gazebo MCP server:
- OperationResult: Standardized response format
- Error codes and helpers
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

__all__ = [
    "OperationResult",
    "ErrorCodes",
    "success_result",
    "error_result",
    "model_not_found_error",
    "ros2_not_connected_error",
    "gazebo_not_running_error",
    "invalid_parameter_error",
    "operation_timeout_error",
]
