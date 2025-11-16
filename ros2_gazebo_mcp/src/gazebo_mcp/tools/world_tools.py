"""
Gazebo World Management Tools.

Provides functions for loading, saving, and managing Gazebo world files and properties.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add claude project to path for ResultFilter:
CLAUDE_ROOT = Path("/home/koen/workspaces/hackathon-git/claude")
sys.path.insert(0, str(CLAUDE_ROOT))

from gazebo_mcp.utils import (
    OperationResult,
    success_result,
    error_result,
)
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ROS2NotConnectedError,
    WorldLoadError,
    WorldSaveError
)
from gazebo_mcp.utils.validators import (
    validate_file_path,
    validate_directory_path,
    validate_positive,
    validate_non_negative
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

# Module-level connection manager (singleton pattern):
_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("world_tools")


def _get_bridge() -> GazeboBridgeNode:
    """Get or create Gazebo bridge node."""
    global _connection_manager, _bridge_node

    if _bridge_node is not None:
        return _bridge_node

    try:
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2 for world tools")

        _bridge_node = GazeboBridgeNode(_connection_manager.get_node())
        _logger.info("Created Gazebo bridge node for world tools")

        return _bridge_node

    except Exception as e:
        _logger.error(f"Failed to create bridge", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def _use_real_gazebo() -> bool:
    """Check if we should use real Gazebo or mock data."""
    try:
        _get_bridge()
        return True
    except Exception:
        return False


def load_world(world_file_path: str) -> OperationResult:
    """
    Load a Gazebo world from SDF file.

    Note: This requires restarting Gazebo with the world file.
    This function provides guidance on how to do that.

    Args:
        world_file_path: Path to SDF world file

    Returns:
        OperationResult with load instructions

    Example:
        >>> result = load_world("/path/to/my_world.sdf")
        >>> if result.success:
        ...     print(result.data["instructions"])
    """
    try:
        # Validate file path:
        world_path = validate_file_path(world_file_path, must_exist=True)

        # Check if it's an SDF file:
        if world_path.suffix.lower() != ".sdf":
            return error_result(
                error=f"File must be .sdf format, got: {world_path.suffix}",
                error_code="INVALID_FILE_FORMAT",
                suggestions=[
                    "Provide an SDF world file (.sdf extension)",
                    "Convert URDF to SDF if needed"
                ]
            )

        _logger.info(f"Validated world file", path=str(world_path))

        # Return instructions for loading:
        return success_result({
            "world_file": str(world_path),
            "loaded": False,
            "instructions": f"""
To load this world in Gazebo:

1. Stop current Gazebo instance (if running)

2. Launch Gazebo with the world file:
   ros2 launch gazebo_ros gazebo.launch.py world:={world_path}

3. Or use gz sim directly:
   gz sim {world_path}

Note: Gazebo must be restarted to load a different world file.
The MCP server will automatically reconnect when Gazebo is ready.
            """.strip(),
            "alternative": "You can also load models individually using spawn_model() instead of loading a whole new world"
        })

    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error loading world", error=str(e))
        return error_result(
            error=f"Failed to load world: {e}",
            error_code="WORLD_LOAD_ERROR"
        )


def save_world(output_path: str) -> OperationResult:
    """
    Save current Gazebo world state to SDF file.

    Args:
        output_path: Path where to save the world file

    Returns:
        OperationResult with save status

    Example:
        >>> result = save_world("/path/to/saved_world.sdf")
    """
    try:
        # Validate output path:
        output_path_obj = Path(output_path)

        # Ensure parent directory exists:
        if not output_path_obj.parent.exists():
            return error_result(
                error=f"Parent directory does not exist: {output_path_obj.parent}",
                error_code="DIRECTORY_NOT_FOUND",
                suggestions=[
                    f"Create directory: mkdir -p {output_path_obj.parent}",
                    "Use an existing directory"
                ]
            )

        if _use_real_gazebo():
            # TODO: Implement real world saving via Gazebo services
            _logger.warning("Real world saving not yet implemented - returning instructions")

            return success_result({
                "output_path": str(output_path),
                "saved": False,
                "instructions": f"""
To save the current world state:

1. Using Gazebo GUI:
   - File → Save World As...
   - Choose location: {output_path}

2. Using gz command:
   gz sdf -p > {output_path}

3. Using ROS2 service (if available):
   ros2 service call /gazebo/save_world std_srvs/srv/Empty

Note: World saving via MCP will be implemented in a future update.
                """.strip(),
                "note": "Mock mode - save instructions provided"
            })
        else:
            return success_result({
                "output_path": str(output_path),
                "saved": False,
                "note": "Gazebo not running - cannot save world"
            })

    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error saving world", error=str(e))
        return error_result(
            error=f"Failed to save world: {e}",
            error_code="WORLD_SAVE_ERROR"
        )


def get_world_properties() -> OperationResult:
    """
    Get Gazebo world properties (physics settings, gravity, etc.).

    Returns:
        OperationResult with world properties

    Example:
        >>> result = get_world_properties()
        >>> if result.success:
        ...     gravity = result.data["gravity"]
        ...     print(f"Gravity: {gravity}")
    """
    try:
        if _use_real_gazebo():
            # TODO: Implement real world properties query
            _logger.warning("Using mock world properties - real query not yet implemented")
            properties = _get_mock_world_properties()
        else:
            properties = _get_mock_world_properties()
            properties["note"] = "Mock data - Gazebo not available"

        return success_result(properties)

    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error getting world properties", error=str(e))
        return error_result(
            error=f"Failed to get world properties: {e}",
            error_code="GET_PROPERTIES_ERROR"
        )


def set_world_property(property_name: str, value: Any) -> OperationResult:
    """
    Set a Gazebo world property.

    Args:
        property_name: Name of property to set (gravity, physics_update_rate, etc.)
        value: New value for the property

    Returns:
        OperationResult with update status

    Example:
        >>> # Set gravity:
        >>> result = set_world_property("gravity", {"x": 0, "y": 0, "z": -9.81})
        >>>
        >>> # Set physics update rate:
        >>> result = set_world_property("physics_update_rate", 1000.0)
    """
    try:
        # Validate common properties:
        if property_name == "physics_update_rate":
            value = validate_positive(value, "physics_update_rate")
        elif property_name == "max_step_size":
            value = validate_positive(value, "max_step_size")

        if _use_real_gazebo():
            # TODO: Implement real property setting
            _logger.warning(f"Real property setting not yet implemented for {property_name}")

            return success_result({
                "property": property_name,
                "value": value,
                "set": False,
                "note": "Property setting via MCP will be implemented in a future update",
                "instructions": f"""
To set {property_name} manually:

1. Edit world SDF file before launching Gazebo
2. Or use Gazebo services (if available):
   ros2 service call /gazebo/set_physics_properties ...

Note: Some properties can only be set before Gazebo starts.
                """.strip()
            })
        else:
            return success_result({
                "property": property_name,
                "value": value,
                "set": False,
                "note": "Gazebo not running - cannot set property"
            })

    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error setting world property", error=str(e))
        return error_result(
            error=f"Failed to set property: {e}",
            error_code="SET_PROPERTY_ERROR"
        )


# Helper functions:

def _get_mock_world_properties() -> Dict[str, Any]:
    """Get mock world properties for fallback."""
    return {
        "world_name": "default",
        "gravity": {
            "x": 0.0,
            "y": 0.0,
            "z": -9.81
        },
        "physics": {
            "engine": "ode",
            "update_rate": 1000.0,
            "max_step_size": 0.001,
            "real_time_factor": 1.0,
            "real_time_update_rate": 1000.0
        },
        "scene": {
            "ambient": {"r": 0.4, "g": 0.4, "b": 0.4, "a": 1.0},
            "background": {"r": 0.7, "g": 0.7, "b": 0.7, "a": 1.0},
            "shadows": True,
            "grid": True
        },
        "simulation_time": 0.0,
        "real_time": 0.0,
        "iterations": 0
    }
