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
from gazebo_mcp.bridge.config import GazeboConfig, GazeboBackend

_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("bridge_helper")


def backend_is_mock() -> bool:
    """Return True if the configured backend is the in-memory MOCK backend."""
    return GazeboConfig.from_environment().backend == GazeboBackend.MOCK


def get_bridge() -> GazeboBridgeNode:
    """
    Get or create Gazebo bridge node (singleton).

    Two paths:
    - MOCK backend (``GAZEBO_BACKEND=mock``): build a node-less GazeboBridgeNode
      whose adapter is the deterministic MockGazeboAdapter, via the factory with
      a MOCK config and ``ros2_node=None``. No ROS2 connection / rclpy import.
    - Otherwise: the existing ConnectionManager path (connects ROS2, raises on
      failure).

    Returns:
        GazeboBridgeNode instance

    Raises:
        ROS2NotConnectedError: If a real ROS2 connection is required but fails.
    """
    global _connection_manager, _bridge_node

    if _bridge_node is not None:
        return _bridge_node

    # Mock-safe path: no ConnectionManager, no rclpy connection.
    if backend_is_mock():
        config = GazeboConfig.from_environment()
        # ros2_node=None: the MockGazeboAdapter (built by the factory's MOCK
        # branch) ignores the node, so no ROS graph is touched.
        _bridge_node = GazeboBridgeNode(
            None, config=config, world=config.world_name
        )
        _logger.info("Created MOCK Gazebo bridge node (no ROS2 connection)")
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
