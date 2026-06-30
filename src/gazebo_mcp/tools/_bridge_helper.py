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


async def get_bridge_for_ctx(ctx) -> GazeboBridgeNode:
    """
    Resolve the bridge for the current MCP request, Context-aware.

    Two transports, two paths (verified on mcp 1.27.1):

    - **HTTP (opt-in):** when ``ctx`` belongs to a request that has a per-session
      ``GazeboSession`` (keyed by ``Mcp-Session-Id``), return *that session's*
      bridge so two distinct HTTP sessions stay isolated. Resolved via
      ``gz_mcp_server.server.app.get_session(ctx)``.
    - **stdio / back-compat:** when there is no ctx, no session, or the session's
      bridge is unavailable, fall back to the process singleton ``get_bridge()``.

    The lean tools keep calling the no-arg :func:`get_bridge` (stdio singleton);
    this helper is used by the per-session resource/HTTP layer (P3 Exec-C).

    Args:
        ctx: The FastMCP tool/resource ``Context`` (or ``None``).

    Returns:
        GazeboBridgeNode: the session's bridge if available, else the singleton.
    """
    if ctx is not None:
        try:
            # Lazy import avoids a hard cycle: app.py imports session.py which
            # imports this module; importing app here at module load would loop.
            from gz_mcp_server.server.app import get_session

            session = await get_session(ctx)
            if getattr(session, "bridge", None) is not None:
                return session.bridge
        except Exception as e:  # noqa: BLE001 — fall back to the singleton
            _logger.debug("Per-session bridge resolution failed; using singleton",
                          error=str(e))
    return get_bridge()


def build_fresh_bridge() -> GazeboBridgeNode:
    """
    Build a NEW, independent bridge node — NOT the process singleton.

    Used for per-HTTP-session isolation (P3): each ``Mcp-Session-Id`` owns its
    own bridge so state (spawned models, params, wrenches) does not leak between
    sessions. In MOCK mode this is a node-less ``GazeboBridgeNode`` whose
    ``MockGazeboAdapter`` has its own ``_worlds`` dict; in real mode it connects
    its own ROS2 graph via a dedicated ``ConnectionManager``.

    The stdio default session and the lean tools keep using the shared
    :func:`get_bridge` singleton — only HTTP sessions get a fresh bridge.

    Returns:
        GazeboBridgeNode: a freshly constructed bridge node.

    Raises:
        ROS2NotConnectedError: If a real ROS2 connection is required but fails.
    """
    if backend_is_mock():
        config = GazeboConfig.from_environment()
        return GazeboBridgeNode(None, config=config, world=config.world_name)

    # Real backend: own a dedicated ConnectionManager so aclose() can tear it
    # down without touching the process singleton's connection.
    manager = ConnectionManager()
    manager.connect(timeout=10.0)
    bridge = GazeboBridgeNode(manager.get_node())
    # Stash the owning manager on the bridge so the session can disconnect it.
    bridge._owning_connection_manager = manager  # type: ignore[attr-defined]
    return bridge


def use_real_gazebo() -> bool:
    """Check if we should use real Gazebo or mock data."""
    try:
        get_bridge()
        return True
    except Exception:
        return False
