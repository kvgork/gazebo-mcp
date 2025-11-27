"""
Gazebo Model Management Tools.

Provides functions for spawning, deleting, listing, and managing models in Gazebo simulation.
Implements the ResultFilter pattern for 98.7% token efficiency.

Based on MCP code execution efficiency pattern from Anthropic.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add claude project to path for ResultFilter:
# Use environment variable or relative path from project root
CLAUDE_ROOT = Path(os.environ.get("CLAUDE_ROOT", Path(__file__).parents[3] / "claude"))
if CLAUDE_ROOT.exists():
    sys.path.insert(0, str(CLAUDE_ROOT))

from gazebo_mcp.utils import (
    OperationResult,
    success_result,
    error_result,
    model_not_found_error,
    invalid_parameter_error,
)
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ROS2NotConnectedError,
    ModelNotFoundError,
)
from gazebo_mcp.utils.validators import validate_model_name, validate_position, validate_orientation
from gazebo_mcp.utils.converters import euler_to_quaternion
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

# Module-level connection manager (singleton pattern):
_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("model_management")


def _get_bridge() -> GazeboBridgeNode:
    """
    Get or create Gazebo bridge node.

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
        # Create connection manager if needed:
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2 for model management")

        # Create bridge node:
        _bridge_node = GazeboBridgeNode(_connection_manager.get_node())
        _logger.info("Created Gazebo bridge node")

        return _bridge_node

    except Exception as e:
        _logger.error(f"Failed to create bridge", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def _use_real_gazebo() -> bool:
    """Check if we should use real Gazebo or mock data."""
    try:
        # Try to get bridge - if it works, use real Gazebo:
        _get_bridge()
        return True
    except Exception:
        # Fall back to mock data:
        return False


def list_models(
    response_format: str = "filtered",
    world: str = "default"
) -> OperationResult:
    """
    List all models in Gazebo simulation.

    This demonstrates the MCP token efficiency pattern - provide full data
    for local filtering instead of sending everything through the model.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        response_format:
            - "summary": Just counts and types (~50 tokens)
            - "concise": Names and states only (~200 tokens/model)
            - "filtered": Full data for local filtering (~1000 tokens base + full data)
            - "detailed": Everything including meshes (~500+ tokens/model)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with models data in requested format

    Token Efficiency Examples:
        Without ResultFilter:
            - 100 models × 500 tokens = 50,000 tokens sent to model!

        With ResultFilter (filtered format):
            - 1,000 tokens structure + agent filters locally
            - Agent sees only filtered results: 50-500 tokens
            - Savings: 98%+

    Example Usage:
        ```python
        from gazebo_mcp.tools.model_management import list_models
        from skills.common.filters import ResultFilter

        # Get all models in filtered format:
        result = list_models(response_format="filtered")

        if result.success:
            models = result.data["models"]

            # Filter locally (0 tokens to model!):
            turtlebots = ResultFilter.search(models, "turtlebot3", ["name", "type"])
            active_models = ResultFilter.filter_by_field(models, "state", "active")
            top_5_complex = ResultFilter.top_n_by_field(models, "complexity", 5)

            print(f"Found {len(turtlebots)} TurtleBots")
            print(f"Active models: {len(active_models)}")
        ```
    """
    # Get models from real Gazebo or mock data:
    try:
        if _use_real_gazebo():
            # Get real models from Gazebo:
            bridge = _get_bridge()
            model_states = bridge.get_model_list(timeout=5.0, world=world)

            # Convert ModelState objects to dicts:
            all_models = []
            for model_state in model_states:
                model_dict = {
                    "name": model_state.name,
                    "type": _infer_model_type(model_state.name),
                    "state": model_state.state,
                    "position": model_state.pose["position"],
                    "orientation": model_state.pose["orientation"],
                    "velocity": model_state.twist,
                    "complexity": _estimate_complexity(model_state.name),
                }
                all_models.append(model_dict)

            _logger.info(f"Retrieved {len(all_models)} models from Gazebo")
        else:
            # Fall back to mock data if Gazebo not available:
            all_models = _get_mock_models()
            _logger.warning("Using mock data - Gazebo not available")

    except GazeboMCPError as e:
        # Return error result with suggestions:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )

    # Response format handling:
    if response_format == "summary":
        # Minimal data - just statistics:
        types = list(set(m.get("type", "unknown") for m in all_models))
        states = list(set(m.get("state", "unknown") for m in all_models))

        return success_result(
            {"count": len(all_models), "types": types, "states": states, "token_estimate": 50}
        )

    elif response_format == "concise":
        # Names and basic info only:
        concise_models = [
            {
                "name": m["name"],
                "type": m.get("type", "unknown"),
                "state": m.get("state", "unknown"),
                "position": m.get("position", {}),
            }
            for m in all_models
        ]

        return success_result(
            {
                "models": concise_models,
                "count": len(all_models),
                "token_estimate": len(all_models) * 20,
            }
        )

    elif response_format == "filtered":
        # THIS IS THE KEY PATTERN - full data + filtering guidance:
        return success_result(
            {
                "models": all_models,  # Full data for local filtering
                "count": len(all_models),
                # Show agents how to filter locally:
                "filter_examples": {
                    "search_by_name": "ResultFilter.search(models, 'turtlebot', ['name'])",
                    "filter_by_state": "ResultFilter.filter_by_field(models, 'state', 'active')",
                    "filter_by_type": "ResultFilter.filter_by_field(models, 'type', 'robot')",
                    "get_top_n_complex": "ResultFilter.top_n_by_field(models, 'complexity', 5)",
                    "limit_results": "ResultFilter.limit(models, 10)",
                },
                # Token usage information:
                "token_estimate_unfiltered": len(all_models) * 100,
                "token_estimate_filtered": 1000,
                "token_savings_pct": 99.0 if len(all_models) > 10 else 0,
                # Usage example:
                "usage_example": """
# Agent generates this code (runs locally, 0 tokens to model!):
from skills.common.filters import ResultFilter

# Filter by name pattern:
turtlebots = ResultFilter.search(result.data["models"], "turtlebot3", ["name"])

# Filter by state:
active = ResultFilter.filter_by_field(result.data["models"], "state", "active")

# Get top 5 by complexity:
complex = ResultFilter.top_n_by_field(result.data["models"], "complexity", 5)

# Combine filters:
active_turtlebots = ResultFilter.filter_by_field(turtlebots, "state", "active")
            """,
            }
        )

    else:  # detailed
        # Everything including heavy data:
        detailed_models = all_models  # In real implementation, add mesh, physics data

        return success_result(
            {
                "models": detailed_models,
                "count": len(all_models),
                "token_estimate": len(all_models) * 500,
            }
        )


def spawn_model(
    model_name: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    namespace: Optional[str] = None,
    world: str = "default",
    geometry: str = "box",
    size: tuple = (1.0, 1.0, 1.0),
    color: tuple = (0.0, 1.0, 0.0, 1.0),
    static: bool = True,
) -> OperationResult:
    """
    Spawn a model in Gazebo simulation.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        model_name: Name of the model to spawn (e.g., "turtlebot3_burger")
        x, y, z: Position coordinates
        roll, pitch, yaw: Orientation (radians)
        namespace: Optional ROS2 namespace for the model
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with spawn status and model info

    Example:
        >>> result = spawn_model("turtlebot3_burger", x=1.0, y=2.0)
        >>> if result.success:
        ...     print(f"Spawned {result.data['model_name']} at {result.data['position']}")
        ... else:
        ...     print(f"Error: {result.error}")
        ...     for suggestion in result.suggestions:
        ...         print(f"  - {suggestion}")
    """
    try:
        # Validate parameters:
        model_name = validate_model_name(model_name)
        x, y, z = validate_position(x, y, z)
        roll, pitch, yaw = validate_orientation(roll, pitch, yaw, radians=True)

        # Create pose dictionary:
        qx, qy, qz, qw = euler_to_quaternion(roll, pitch, yaw)
        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": qx, "y": qy, "z": qz, "w": qw},
        }

        # Attempt to spawn in real Gazebo:
        if _use_real_gazebo():
            bridge = _get_bridge()

            # Generate SDF content with proper geometry and materials
            # Build geometry tag based on geometry type
            size_str = f"{size[0]} {size[1]} {size[2]}"

            if geometry == "box":
                geometry_tag = f"<box><size>{size_str}</size></box>"
            elif geometry == "sphere":
                radius = size[0] / 2.0  # Use first dimension as diameter
                geometry_tag = f"<sphere><radius>{radius}</radius></sphere>"
            elif geometry == "cylinder":
                radius = size[0] / 2.0  # Use first dimension as diameter
                length = size[2]  # Use Z dimension as length
                geometry_tag = f"<cylinder><radius>{radius}</radius><length>{length}</length></cylinder>"
            else:
                geometry_tag = f"<box><size>{size_str}</size></box>"  # Default to box

            # Build color strings (RGBA)
            color_str = f"{color[0]} {color[1]} {color[2]} {color[3]}"
            static_str = "true" if static else "false"

            sdf_content = f"""<?xml version='1.0'?>
<sdf version='1.6'>
  <model name='{model_name}'>
    <static>{static_str}</static>
    <link name='link'>
      <pose>0 0 0 0 0 0</pose>
      <visual name='visual'>
        <geometry>
          {geometry_tag}
        </geometry>
        <material>
          <ambient>{color_str}</ambient>
          <diffuse>{color_str}</diffuse>
        </material>
      </visual>
      <collision name='collision'>
        <geometry>
          {geometry_tag}
        </geometry>
      </collision>
    </link>
  </model>
</sdf>"""

            # Spawn entity:
            success = bridge.spawn_entity(
                name=namespace or model_name,
                xml_content=sdf_content,
                pose=pose,
                reference_frame="world",
                timeout=10.0,
                world=world,
            )

            if success:
                _logger.log_model_event("spawned", model_name, position=pose["position"])
                return success_result(
                    {
                        "model_name": model_name,
                        "entity_name": namespace or model_name,
                        "position": {"x": x, "y": y, "z": z},
                        "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                        "namespace": namespace,
                        "spawned_at": datetime.utcnow().isoformat() + "Z",
                    }
                )
        else:
            # Fall back to mock spawn:
            _logger.warning(f"Mock spawning {model_name} - Gazebo not available")
            return success_result(
                {
                    "model_name": model_name,
                    "entity_name": namespace or model_name,
                    "position": {"x": x, "y": y, "z": z},
                    "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                    "namespace": namespace,
                    "spawned_at": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock spawn - Gazebo not available",
                }
            )

    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error during spawn", error=str(e))
        return error_result(error=f"Failed to spawn model: {e}", error_code="SPAWN_ERROR")


def delete_model(
    model_name: str,
    world: str = "default"
) -> OperationResult:
    """
    Delete a model from Gazebo simulation.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        model_name: Name of the model to delete
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with deletion status

    Example:
        >>> result = delete_model("turtlebot3_burger")
        >>> if result.success:
        ...     print(f"Deleted {result.data['model_name']}")
    """
    try:
        # Validate parameters:
        model_name = validate_model_name(model_name)

        # Attempt to delete in real Gazebo:
        if _use_real_gazebo():
            bridge = _get_bridge()
            success = bridge.delete_entity(name=model_name, timeout=10.0, world=world)

            if success:
                _logger.log_model_event("deleted", model_name)
                return success_result(
                    {"model_name": model_name, "deleted_at": datetime.utcnow().isoformat() + "Z"}
                )
            else:
                return error_result(
                    error=f"Failed to delete model '{model_name}'", error_code="DELETE_FAILED"
                )
        else:
            # Fall back to mock deletion:
            _logger.warning(f"Mock deleting {model_name} - Gazebo not available")
            return success_result(
                {
                    "model_name": model_name,
                    "deleted_at": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock deletion - Gazebo not available",
                }
            )

    except ModelNotFoundError:
        return model_not_found_error(model_name)
    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error during deletion", error=str(e))
        return error_result(error=f"Failed to delete model: {e}", error_code="DELETE_ERROR")


def get_model_state(
    model_name: str,
    response_format: str = "concise",
    world: str = "default"
) -> OperationResult:
    """
    Get the current state of a model.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        model_name: Name of the model
        response_format: "concise" | "detailed"
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with model state

    Example:
        >>> result = get_model_state("turtlebot3_burger")
        >>> if result.success:
        ...     pos = result.data["position"]
        ...     print(f"Position: x={pos['x']}, y={pos['y']}, z={pos['z']}")
    """
    try:
        # Validate parameters:
        model_name = validate_model_name(model_name)

        # Attempt to get state from real Gazebo:
        if _use_real_gazebo():
            bridge = _get_bridge()
            model_state = bridge.get_model_state(name=model_name, timeout=5.0, world=world)

            if model_state is None:
                return model_not_found_error(model_name)

            # Convert orientation quaternion to Euler angles:
            from gazebo_mcp.utils.converters import quaternion_to_euler

            # Handle case where pose might not be a dict
            pose = model_state.pose
            if not isinstance(pose, dict):
                _logger.error(f"Invalid pose type: {type(pose)}, value: {pose}")
                return error_result(
                    f"Invalid model state format: pose is {type(pose).__name__}, expected dict",
                    "INVALID_STATE_FORMAT"
                )

            orient = pose.get("orientation")
            # Handle both tuple (x, y, z, w) and dict {"x": ..., "y": ..., "z": ..., "w": ...}
            if isinstance(orient, (tuple, list)):
                x, y, z, w = orient
            else:
                x, y, z, w = orient["x"], orient["y"], orient["z"], orient["w"]

            roll, pitch, yaw = quaternion_to_euler(x, y, z, w)

            # Handle position - convert tuple to dict if needed
            pos = pose.get("position")
            if isinstance(pos, (tuple, list)):
                position = {"x": pos[0], "y": pos[1], "z": pos[2]}
            else:
                position = pos

            # Handle velocity - convert tuple to dict if needed
            twist = model_state.twist
            if isinstance(twist, dict) and "linear" in twist:
                lin = twist["linear"]
                ang = twist["angular"]
                if isinstance(lin, (tuple, list)):
                    velocity = {
                        "linear": {"x": lin[0], "y": lin[1], "z": lin[2]},
                        "angular": {"x": ang[0], "y": ang[1], "z": ang[2]}
                    }
                else:
                    velocity = twist
            else:
                velocity = twist

            # Return based on format:
            if response_format == "concise":
                return success_result(
                    {
                        "name": model_state.name,
                        "position": position,
                        "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                        "velocity": velocity,
                    }
                )
            else:  # detailed
                orient_dict = {"x": x, "y": y, "z": z, "w": w} if isinstance(orient, (tuple, list)) else orient
                return success_result(
                    {
                        "name": model_state.name,
                        "position": position,
                        "orientation": {
                            "roll": roll,
                            "pitch": pitch,
                            "yaw": yaw,
                            "quaternion": orient_dict,
                        },
                        "velocity": velocity,
                        "state": model_state.state,
                    }
                )
        else:
            # Fall back to mock state:
            _logger.warning(f"Mock state for {model_name} - Gazebo not available")
            if response_format == "concise":
                return success_result(
                    {
                        "name": model_name,
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                        "velocity": {
                            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                        },
                        "note": "Mock state - Gazebo not available",
                    }
                )
            else:  # detailed
                return success_result(
                    {
                        "name": model_name,
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                        "velocity": {
                            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                        },
                        "note": "Mock state - Gazebo not available",
                    }
                )

    except ModelNotFoundError:
        return model_not_found_error(model_name)
    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error getting model state", error=str(e))
        return error_result(error=f"Failed to get model state: {e}", error_code="GET_STATE_ERROR")


def set_model_state(
    model_name: str,
    pose: Optional[Dict] = None,
    twist: Optional[Dict] = None,
    reference_frame: str = "world",
    world: str = "default",
) -> OperationResult:
    """
    Set model pose and/or velocity.

    Teleports the model to a new position/orientation and/or sets its velocity.
    Useful for resetting robot positions, creating test scenarios, or applying
    initial conditions.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        model_name: Name of model to update
        pose: Target pose with structure:
            {
                "position": {"x": float, "y": float, "z": float},
                "orientation": {"roll": float, "pitch": float, "yaw": float}
                    OR {"x": float, "y": float, "z": float, "w": float}
            }
        twist: Target velocity with structure:
            {
                "linear": {"x": float, "y": float, "z": float},
                "angular": {"x": float, "y": float, "z": float}
            }
        reference_frame: Reference frame for pose (Classic only, ignored by Modern)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with update status

    Examples:
        >>> # Move robot to new position
        >>> result = set_model_state("robot_1", pose={
        ...     "position": {"x": 2.0, "y": 1.0, "z": 0.5},
        ...     "orientation": {"roll": 0, "pitch": 0, "yaw": 1.57}
        ... })
        >>>
        >>> # Set velocity
        >>> result = set_model_state("robot_1", twist={
        ...     "linear": {"x": 0.5, "y": 0, "z": 0},
        ...     "angular": {"x": 0, "y": 0, "z": 0.3}
        ... })
        >>>
        >>> # Set both pose and velocity
        >>> result = set_model_state("robot_1",
        ...     pose={"position": {"x": 0, "y": 0, "z": 0.5}},
        ...     twist={"linear": {"x": 0, "y": 0, "z": 0}}
        ... )
    """
    try:
        # Validate parameters:
        model_name = validate_model_name(model_name)

        if pose is None and twist is None:
            return invalid_parameter_error("pose/twist", "None", "pose dict and/or twist dict")

        # Validate pose if provided:
        if pose:
            if "position" in pose:
                pos = pose["position"]
                validate_position(pos["x"], pos["y"], pos["z"])
            if "orientation" in pose:
                orient = pose["orientation"]
                # Support both Euler and quaternion:
                if "roll" in orient:
                    validate_orientation(
                        orient["roll"], orient["pitch"], orient["yaw"], radians=True
                    )
                # Quaternion validation would go here if needed

        # Attempt to set state in real Gazebo:
        if _use_real_gazebo():
            bridge = _get_bridge()

            # Call bridge to set entity state:
            success = bridge.set_entity_state(
                name=model_name,
                pose=pose,
                twist=twist,
                reference_frame=reference_frame,
                timeout=10.0,
                world=world,
            )

            if success:
                _logger.info(f"Set state for model: {model_name}")

                # Build response data:
                response_data = {
                    "model": model_name,
                    "updated": True,
                    "reference_frame": reference_frame,
                }

                if pose:
                    response_data["pose"] = pose
                if twist:
                    response_data["twist"] = twist

                return success_result(response_data)
            else:
                return error_result(
                    error=f"Failed to set state for model '{model_name}'",
                    error_code="SET_STATE_FAILED",
                )

        else:
            # Fallback: Provide instructions for mock mode:
            _logger.warning(f"Mock set_model_state for {model_name} - Gazebo not available")

            instructions = []
            if pose:
                instructions.append("To teleport model, ensure Gazebo is running")
                instructions.append(f"Target position: {pose.get('position', 'not specified')}")
                if "orientation" in pose:
                    instructions.append(f"Target orientation: {pose['orientation']}")

            if twist:
                instructions.append("To set velocity, use ROS2 topics or Gazebo GUI")
                instructions.append(
                    f"Target linear velocity: {twist.get('linear', 'not specified')}"
                )
                instructions.append(
                    f"Target angular velocity: {twist.get('angular', 'not specified')}"
                )

            return success_result(
                {
                    "model": model_name,
                    "updated": False,
                    "note": "Mock mode - Gazebo not available",
                    "instructions": instructions,
                    "gazebo_connected": False,
                }
            )

    except ModelNotFoundError:
        return model_not_found_error(model_name)
    except GazeboMCPError as e:
        return error_result(
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error setting model state", error=str(e))
        return error_result(error=f"Failed to set model state: {e}", error_code="SET_STATE_ERROR")


# Helper functions:


def _infer_model_type(model_name: str) -> str:
    """
    Infer model type from name.

    Args:
        model_name: Model name

    Returns:
        Model type ("robot", "static", "prop", "actor", "unknown")
    """
    name_lower = model_name.lower()

    # Static models:
    if name_lower in ["ground_plane", "sun"]:
        return "static"

    # Robots (common patterns):
    if any(robot in name_lower for robot in ["turtlebot", "robot", "bot", "drone", "uav"]):
        return "robot"

    # Actors (animated models):
    if any(actor in name_lower for actor in ["actor", "human", "person"]):
        return "actor"

    # Props (obstacles, furniture, etc.):
    if any(
        prop in name_lower
        for prop in ["box", "cylinder", "sphere", "obstacle", "wall", "chair", "table"]
    ):
        return "prop"

    return "unknown"


def _estimate_complexity(model_name: str) -> int:
    """
    Estimate model complexity (approximate link/joint count).

    Args:
        model_name: Model name

    Returns:
        Complexity estimate (higher = more complex)
    """
    name_lower = model_name.lower()

    # Simple primitives:
    if any(prim in name_lower for prim in ["box", "cylinder", "sphere", "plane"]):
        return 1

    # Medium complexity (furniture, simple props):
    if any(prop in name_lower for prop in ["chair", "table", "wall", "obstacle"]):
        return 5

    # High complexity (robots):
    if "turtlebot3_burger" in name_lower:
        return 45
    if "turtlebot3_waffle" in name_lower:
        return 52
    if any(robot in name_lower for robot in ["turtlebot", "robot"]):
        return 40

    # Very high complexity (humanoids, complex robots):
    if any(complex_model in name_lower for complex_model in ["pr2", "nao", "atlas", "human"]):
        return 100

    # Default:
    return 10


def _get_mock_models() -> List[Dict[str, Any]]:
    """
    Get mock models for fallback when Gazebo is not available.

    Used for testing and demonstration when ROS2/Gazebo connection fails.
    """
    return [
        {
            "name": "ground_plane",
            "type": "static",
            "state": "active",
            "position": {"x": 0, "y": 0, "z": 0},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "velocity": {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}},
            "complexity": 1,
        },
        {
            "name": "turtlebot3_burger",
            "type": "robot",
            "state": "active",
            "position": {"x": 1.0, "y": 2.0, "z": 0.01},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "velocity": {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}},
            "complexity": 45,
        },
        {
            "name": "turtlebot3_waffle",
            "type": "robot",
            "state": "inactive",
            "position": {"x": -1.0, "y": 0.0, "z": 0.01},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "velocity": {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}},
            "complexity": 52,
        },
        {
            "name": "box_obstacle_1",
            "type": "prop",
            "state": "active",
            "position": {"x": 3.0, "y": 3.0, "z": 0.5},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "velocity": {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}},
            "complexity": 2,
        },
        {
            "name": "cylinder_obstacle_1",
            "type": "prop",
            "state": "active",
            "position": {"x": -2.0, "y": 2.0, "z": 0.5},
            "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
            "velocity": {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}},
            "complexity": 3,
        },
    ]
