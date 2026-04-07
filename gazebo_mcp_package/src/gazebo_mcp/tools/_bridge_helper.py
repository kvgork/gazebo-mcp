"""
Shared Gazebo bridge initialization helper.

Provides singleton ConnectionManager and GazeboBridgeNode instances
shared across all tool modules. Eliminates duplication of _get_bridge()
and _use_real_gazebo() across model_management, sensor_tools,
simulation_tools, and world_tools.
"""

from typing import Optional
from gazebo_mcp.utils.exceptions import ROS2NotConnectedError
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("bridge_helper")


def get_bridge() -> GazeboBridgeNode:
    """
    Get or create Gazebo bridge node (singleton).

    Lazy initialization with auto-connection.

    Returns:
        GazeboBridgeNode instance

    Raises:
        ROS2NotConnectedError: If connection fails
    """
    global _connection_manager, _bridge_node

    if _bridge_node is not None:
        return _bridge_node

    try:
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2")

        _bridge_node = GazeboBridgeNode(_connection_manager.get_node())
        _logger.info("Created Gazebo bridge node")

        return _bridge_node

    except Exception as e:
        _logger.error(f"Failed to create bridge", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def use_real_gazebo() -> bool:
    """Check if we should use real Gazebo or mock data."""
    try:
        get_bridge()
        return True
    except Exception:
        return False
