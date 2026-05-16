"""
Shared Gazebo bridge initialization helper.

Provides singleton ConnectionManager and GazeboBridgeNode instances
shared across all tool modules. Eliminates duplication of _get_bridge()
and _use_real_gazebo() across model_management, sensor_tools,
simulation_tools, and world_tools.
"""

import os
import re
import subprocess
from typing import Optional
from gazebo_mcp.utils.exceptions import ROS2NotConnectedError
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("bridge_helper")


def _detect_world_name() -> str:
    """
    Auto-detect the active Gazebo world name.

    Checks GAZEBO_WORLD_NAME env var first, then queries the running
    Ignition/Gazebo instance via the gz/ign CLI.

    Returns:
        World name string, defaults to 'default' if not found.
    """
    # Env var takes priority
    world_name = os.getenv("GAZEBO_WORLD_NAME")
    if world_name:
        return world_name

    # Try gz (Harmonic+) then ign (Fortress)
    for cli in ("gz", "ign"):
        try:
            result = subprocess.run(
                [cli, "service", "--list"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if result.returncode == 0 and result.stdout.strip():
                worlds = sorted(
                    set(re.findall(r"/world/([^/\s]+)/control", result.stdout))
                )
                if worlds:
                    _logger.info(f"Auto-detected Gazebo world: '{worlds[0]}'")
                    return worlds[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except Exception as e:
            _logger.warning(f"World detection via {cli} failed: {e}")

    _logger.warning("Could not detect world name, defaulting to 'default'")
    return "default"


def get_bridge() -> GazeboBridgeNode:
    """
    Get or create Gazebo bridge node (singleton).

    Lazy initialization with auto-connection. Auto-detects the active
    Gazebo world name via CLI so the correct world service endpoints
    are used regardless of what name the world was launched with.

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

        world_name = _detect_world_name()
        _bridge_node = GazeboBridgeNode(_connection_manager.get_node(), world=world_name)
        _logger.info(f"Created Gazebo bridge node for world '{world_name}'")

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
