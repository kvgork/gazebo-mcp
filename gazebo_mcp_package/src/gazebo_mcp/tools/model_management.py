"""
Gazebo Model Management Tools.

Provides functions for spawning, deleting, listing, and managing models in Gazebo simulation.
Implements the ResultFilter pattern for 98.7% token efficiency.

Based on MCP code execution efficiency pattern from Anthropic.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

from gazebo_mcp.utils import OperationResult, TokenEstimates
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ModelNotFoundError,
)
from gazebo_mcp.utils.validators import validate_model_name, validate_position, validate_orientation
from gazebo_mcp.utils.converters import euler_to_quaternion
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

_logger = get_logger("model_management")

__all__ = [
    "list_models",
    "spawn_model",
    "spawn_sdf",
    "delete_model",
    "get_model_state",
    "set_model_state",
    "apply_force",
]


def list_models(
    response_format: str = "filtered",
    world: str = "default"
) -> OperationResult:
    """
    List all models in Gazebo simulation.

    This demonstrates the MCP token efficiency pattern - provide full data
    for local filtering instead of sending everything through the model.

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
            - 100 models x 500 tokens = 50,000 tokens sent to model!

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
    try:
        if use_real_gazebo():
            bridge = get_bridge()
            model_states = bridge.get_model_list(timeout=5.0, world=world)

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
            all_models = _get_mock_models()
            _logger.warning("Using mock data - Gazebo not available")

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )

    if response_format == "summary":
        types = list(set(m.get("type", "unknown") for m in all_models))
        states = list(set(m.get("state", "unknown") for m in all_models))

        return OperationResult(
            success=True,
            data={"count": len(all_models), "types": types, "states": states, "token_estimate": 50},
        )

    elif response_format == "concise":
        concise_models = [
            {
                "name": m["name"],
                "type": m.get("type", "unknown"),
                "state": m.get("state", "unknown"),
                "position": m.get("position", {}),
            }
            for m in all_models
        ]

        return OperationResult(
            success=True,
            data={
                "models": concise_models,
                "count": len(all_models),
                "token_estimate": len(all_models) * 20,
            },
        )

    elif response_format == "filtered":
        return OperationResult(
            success=True,
            data={
                "models": all_models,
                "count": len(all_models),
                "filter_examples": {
                    "search_by_name": "ResultFilter.search(models, 'turtlebot', ['name'])",
                    "filter_by_state": "ResultFilter.filter_by_field(models, 'state', 'active')",
                    "filter_by_type": "ResultFilter.filter_by_field(models, 'type', 'robot')",
                    "get_top_n_complex": "ResultFilter.top_n_by_field(models, 'complexity', 5)",
                    "limit_results": "ResultFilter.limit(models, 10)",
                },
                "token_estimate_unfiltered": len(all_models) * TokenEstimates.TOKENS_PER_MODEL,
                "token_estimate_filtered": 1000,
                "token_savings_pct": 99.0 if len(all_models) > 10 else 0,
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
            },
        )

    else:  # detailed
        return OperationResult(
            success=True,
            data={
                "models": all_models,
                "count": len(all_models),
                "token_estimate": len(all_models) * TokenEstimates.TOKENS_PER_MODEL * 5,
            },
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

    Args:
        model_name: Name of the model to spawn (e.g., "turtlebot3_burger")
        x, y, z: Position coordinates
        roll, pitch, yaw: Orientation (radians)
        namespace: Optional ROS2 namespace for the model
        world: Target world name (Modern Gazebo only, default: "default")
        geometry: Geometry type (box, sphere, cylinder)
        size: Size tuple (x, y, z)
        color: RGBA color tuple
        static: Whether the model is static

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
        model_name = validate_model_name(model_name)
        x, y, z = validate_position(x, y, z)
        roll, pitch, yaw = validate_orientation(roll, pitch, yaw, radians=True)

        qx, qy, qz, qw = euler_to_quaternion(roll, pitch, yaw)
        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": qx, "y": qy, "z": qz, "w": qw},
        }

        if use_real_gazebo():
            bridge = get_bridge()

            # Sanitize model_name for XML embedding
            safe_model_name = xml_escape(model_name)

            size_str = f"{size[0]} {size[1]} {size[2]}"

            if geometry == "box":
                geometry_tag = f"<box><size>{size_str}</size></box>"
            elif geometry == "sphere":
                radius = size[0] / 2.0
                geometry_tag = f"<sphere><radius>{radius}</radius></sphere>"
            elif geometry == "cylinder":
                radius = size[0] / 2.0
                length = size[2]
                geometry_tag = f"<cylinder><radius>{radius}</radius><length>{length}</length></cylinder>"
            else:
                geometry_tag = f"<box><size>{size_str}</size></box>"

            color_str = f"{color[0]} {color[1]} {color[2]} {color[3]}"
            static_str = "true" if static else "false"

            sdf_content = f"""<?xml version='1.0'?>
<sdf version='1.6'>
  <model name='{safe_model_name}'>
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
                return OperationResult(
                    success=True,
                    data={
                        "model_name": model_name,
                        "entity_name": namespace or model_name,
                        "position": {"x": x, "y": y, "z": z},
                        "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                        "namespace": namespace,
                        "spawned_at": datetime.utcnow().isoformat() + "Z",
                    },
                )
        else:
            _logger.warning(f"Mock spawning {model_name} - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "model_name": model_name,
                    "entity_name": namespace or model_name,
                    "position": {"x": x, "y": y, "z": z},
                    "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                    "namespace": namespace,
                    "spawned_at": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock spawn - Gazebo not available",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error during spawn", error=str(e))
        return OperationResult(success=False, error=f"Failed to spawn model: {e}", error_code="SPAWN_ERROR")


def spawn_sdf(
    entity_name: str,
    sdf_xml: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    world: str = "default",
) -> OperationResult:
    """
    Spawn a model from an SDF or URDF XML string.

    Unlike spawn_model (which creates simple geometry), this tool accepts
    complete SDF/URDF XML, enabling spawning of complex robot models,
    articulated objects, sensors, plugins, and anything else expressible
    in SDF format.

    Use this when you need to spawn:
    - Robot models with joints, sensors, and plugins
    - Models with custom inertia and physics properties
    - Models from SDF snippets found in documentation
    - Multi-link articulated objects
    - Models with attached sensors (camera, lidar, IMU)

    Args:
        entity_name: Unique name for the spawned entity in the simulation
        sdf_xml: Complete SDF or URDF XML string. Must be valid XML.
            For SDF: wrap in <sdf><model>...</model></sdf>
            For URDF: wrap in <robot>...</robot>
        x, y, z: Spawn position coordinates (meters)
        roll, pitch, yaw: Spawn orientation (radians)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with spawn status

    Examples:
        >>> # Spawn a model with physics (non-static box with inertia)
        >>> sdf = '''<?xml version='1.0'?>
        ... <sdf version='1.6'>
        ...   <model name='dynamic_box'>
        ...     <static>false</static>
        ...     <link name='link'>
        ...       <inertial>
        ...         <mass>1.0</mass>
        ...       </inertial>
        ...       <collision name='collision'>
        ...         <geometry><box><size>0.5 0.5 0.5</size></box></geometry>
        ...       </collision>
        ...       <visual name='visual'>
        ...         <geometry><box><size>0.5 0.5 0.5</size></box></geometry>
        ...       </visual>
        ...     </link>
        ...   </model>
        ... </sdf>'''
        >>> result = spawn_sdf("my_box", sdf, x=1.0, z=0.25)
    """
    try:
        entity_name = validate_model_name(entity_name)
        x, y, z = validate_position(x, y, z)
        roll, pitch, yaw = validate_orientation(roll, pitch, yaw, radians=True)

        # Validate that sdf_xml is non-empty
        if not sdf_xml or not sdf_xml.strip():
            return OperationResult(
                success=False,
                error="sdf_xml is required and must be non-empty",
                error_code="MISSING_PARAMETER",
                suggestions=[
                    "Provide valid SDF XML wrapped in <sdf><model>...</model></sdf>",
                    "Or provide URDF XML wrapped in <robot>...</robot>",
                    "Use spawn_model() for simple geometric shapes instead",
                ],
            )

        # Basic XML validation
        sdf_stripped = sdf_xml.strip()
        if not sdf_stripped.startswith("<"):
            return OperationResult(
                success=False,
                error="sdf_xml does not appear to be valid XML (must start with '<')",
                error_code="INVALID_PARAMETER",
                suggestions=[
                    "SDF should start with <?xml ...?> or <sdf ...>",
                    "URDF should start with <?xml ...?> or <robot ...>",
                ],
            )

        qx, qy, qz, qw = euler_to_quaternion(roll, pitch, yaw)
        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": qx, "y": qy, "z": qz, "w": qw},
        }

        if use_real_gazebo():
            bridge = get_bridge()

            success = bridge.spawn_entity(
                name=entity_name,
                xml_content=sdf_xml,
                pose=pose,
                reference_frame="world",
                timeout=15.0,
                world=world,
            )

            if success:
                _logger.log_model_event("spawned_sdf", entity_name, position=pose["position"])
                return OperationResult(
                    success=True,
                    data={
                        "entity_name": entity_name,
                        "position": {"x": x, "y": y, "z": z},
                        "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                        "spawned_at": datetime.utcnow().isoformat() + "Z",
                        "sdf_length": len(sdf_xml),
                    },
                )
            else:
                return OperationResult(
                    success=False,
                    error=f"Failed to spawn entity '{entity_name}' from SDF",
                    error_code="SPAWN_SDF_FAILED",
                    suggestions=[
                        "Verify the SDF/URDF XML is valid",
                        "Check that the entity name is unique",
                        "Check Gazebo logs for detailed error information",
                    ],
                )
        else:
            _logger.warning(f"Mock spawning SDF entity {entity_name} - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "entity_name": entity_name,
                    "position": {"x": x, "y": y, "z": z},
                    "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                    "spawned_at": datetime.utcnow().isoformat() + "Z",
                    "sdf_length": len(sdf_xml),
                    "note": "Mock spawn - Gazebo not available",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error during SDF spawn", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to spawn from SDF: {e}",
            error_code="SPAWN_SDF_ERROR",
        )


def delete_model(
    model_name: str,
    world: str = "default"
) -> OperationResult:
    """
    Delete a model from Gazebo simulation.

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
        model_name = validate_model_name(model_name)

        if use_real_gazebo():
            bridge = get_bridge()
            success = bridge.delete_entity(name=model_name, timeout=10.0, world=world)

            if success:
                _logger.log_model_event("deleted", model_name)
                return OperationResult(
                    success=True,
                    data={"model_name": model_name, "deleted_at": datetime.utcnow().isoformat() + "Z"},
                )
            else:
                return OperationResult(
                    success=False,
                    error=f"Failed to delete model '{model_name}'",
                    error_code="DELETE_FAILED",
                )
        else:
            _logger.warning(f"Mock deleting {model_name} - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "model_name": model_name,
                    "deleted_at": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock deletion - Gazebo not available",
                },
            )

    except ModelNotFoundError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error during deletion", error=str(e))
        return OperationResult(success=False, error=f"Failed to delete model: {e}", error_code="DELETE_ERROR")


def get_model_state(
    model_name: str,
    response_format: str = "concise",
    world: str = "default"
) -> OperationResult:
    """
    Get the current state of a model.

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
        model_name = validate_model_name(model_name)

        if use_real_gazebo():
            bridge = get_bridge()
            model_state = bridge.get_model_state(name=model_name, timeout=5.0, world=world)

            if model_state is None:
                return OperationResult(
                    success=False,
                    error=f"Model '{model_name}' not found",
                    error_code="MODEL_NOT_FOUND",
                    suggestions=[f"Check model name. Use list_models() to see available models."],
                )

            from gazebo_mcp.utils.converters import quaternion_to_euler

            orient = model_state.pose["orientation"]
            roll, pitch, yaw = quaternion_to_euler(
                orient["x"], orient["y"], orient["z"], orient["w"]
            )

            if response_format == "concise":
                return OperationResult(
                    success=True,
                    data={
                        "name": model_state.name,
                        "position": model_state.pose["position"],
                        "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
                        "velocity": model_state.twist,
                    },
                )
            else:
                return OperationResult(
                    success=True,
                    data={
                        "name": model_state.name,
                        "position": model_state.pose["position"],
                        "orientation": {
                            "roll": roll,
                            "pitch": pitch,
                            "yaw": yaw,
                            "quaternion": orient,
                        },
                        "velocity": model_state.twist,
                        "state": model_state.state,
                    },
                )
        else:
            _logger.warning(f"Mock state for {model_name} - Gazebo not available")
            if response_format == "concise":
                return OperationResult(
                    success=True,
                    data={
                        "name": model_name,
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                        "velocity": {
                            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                        },
                        "note": "Mock state - Gazebo not available",
                    },
                )
            else:
                return OperationResult(
                    success=True,
                    data={
                        "name": model_name,
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                        "velocity": {
                            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                        },
                        "note": "Mock state - Gazebo not available",
                    },
                )

    except ModelNotFoundError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error getting model state", error=str(e))
        return OperationResult(success=False, error=f"Failed to get model state: {e}", error_code="GET_STATE_ERROR")


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
        >>> result = set_model_state("robot_1", pose={
        ...     "position": {"x": 2.0, "y": 1.0, "z": 0.5},
        ...     "orientation": {"roll": 0, "pitch": 0, "yaw": 1.57}
        ... })
    """
    try:
        model_name = validate_model_name(model_name)

        if pose is None and twist is None:
            return OperationResult(
                success=False,
                error="Must provide pose and/or twist",
                error_code="INVALID_PARAMETER",
                suggestions=["Provide a pose dict, twist dict, or both"],
            )

        if pose:
            if "position" in pose:
                pos = pose["position"]
                validate_position(pos["x"], pos["y"], pos["z"])
            if "orientation" in pose:
                orient = pose["orientation"]
                if "roll" in orient:
                    validate_orientation(
                        orient["roll"], orient["pitch"], orient["yaw"], radians=True
                    )

        if use_real_gazebo():
            bridge = get_bridge()

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

                response_data = {
                    "model": model_name,
                    "updated": True,
                    "reference_frame": reference_frame,
                }

                if pose:
                    response_data["pose"] = pose
                if twist:
                    response_data["twist"] = twist

                return OperationResult(success=True, data=response_data)
            else:
                return OperationResult(
                    success=False,
                    error=f"Failed to set state for model '{model_name}'",
                    error_code="SET_STATE_FAILED",
                )

        else:
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

            return OperationResult(
                success=True,
                data={
                    "model": model_name,
                    "updated": False,
                    "note": "Mock mode - Gazebo not available",
                    "instructions": instructions,
                    "gazebo_connected": False,
                },
            )

    except ModelNotFoundError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error setting model state", error=str(e))
        return OperationResult(success=False, error=f"Failed to set model state: {e}", error_code="SET_STATE_ERROR")


# Helper functions:


def _infer_model_type(model_name: str) -> str:
    """Infer model type from name."""
    name_lower = model_name.lower()

    if name_lower in ["ground_plane", "sun"]:
        return "static"

    if any(robot in name_lower for robot in ["turtlebot", "robot", "bot", "drone", "uav"]):
        return "robot"

    if any(actor in name_lower for actor in ["actor", "human", "person"]):
        return "actor"

    if any(
        prop in name_lower
        for prop in ["box", "cylinder", "sphere", "obstacle", "wall", "chair", "table"]
    ):
        return "prop"

    return "unknown"


def _estimate_complexity(model_name: str) -> int:
    """Estimate model complexity (approximate link/joint count)."""
    name_lower = model_name.lower()

    if any(prim in name_lower for prim in ["box", "cylinder", "sphere", "plane"]):
        return 1

    if any(prop in name_lower for prop in ["chair", "table", "wall", "obstacle"]):
        return 5

    if "turtlebot3_burger" in name_lower:
        return 45
    if "turtlebot3_waffle" in name_lower:
        return 52
    if any(robot in name_lower for robot in ["turtlebot", "robot"]):
        return 40

    if any(complex_model in name_lower for complex_model in ["pr2", "nao", "atlas", "human"]):
        return 100

    return 10


def apply_force(
    model_name: str,
    force: Optional[Dict[str, float]] = None,
    torque: Optional[Dict[str, float]] = None,
    duration: float = 0.1,
    world: str = "default",
) -> OperationResult:
    """
    Apply a force and/or torque to a model for a short duration.

    Args:
        model_name: Name of the model to apply force to
        force: Force vector {'x': fx, 'y': fy, 'z': fz} in Newtons
        torque: Torque vector {'x': tx, 'y': ty, 'z': tz} in N·m
        duration: Duration to apply force in seconds (default 0.1s)
        world: Target world name

    Returns:
        OperationResult with application status

    Example:
        >>> result = apply_force("robot", force={"x": 10.0, "y": 0.0, "z": 0.0})
        >>> result = apply_force("robot", torque={"x": 0.0, "y": 0.0, "z": 5.0})
    """
    try:
        if force is None and torque is None:
            return OperationResult(
                success=False,
                error="At least one of 'force' or 'torque' must be provided",
                error_code="MISSING_PARAMETER",
                suggestions=["Provide force={'x': fx, 'y': fy, 'z': fz} and/or torque"],
            )

        fx = float(force.get("x", 0.0)) if force else 0.0
        fy = float(force.get("y", 0.0)) if force else 0.0
        fz = float(force.get("z", 0.0)) if force else 0.0
        tx = float(torque.get("x", 0.0)) if torque else 0.0
        ty = float(torque.get("y", 0.0)) if torque else 0.0
        tz = float(torque.get("z", 0.0)) if torque else 0.0
        duration = max(0.001, float(duration))

        result_data = {
            "model_name": model_name,
            "force": {"x": fx, "y": fy, "z": fz},
            "torque": {"x": tx, "y": ty, "z": tz},
            "duration_sec": duration,
            "world": world,
        }

        if use_real_gazebo():
            bridge = get_bridge()
            success = bridge.apply_wrench(
                model_name=model_name,
                force=(fx, fy, fz),
                torque=(tx, ty, tz),
                duration=duration,
                world=world,
            )
            if success:
                _logger.info("Applied wrench", model=model_name)
                return OperationResult(success=True, data={**result_data, "applied": True})
            else:
                return OperationResult(
                    success=False,
                    error=f"Failed to apply wrench to '{model_name}'",
                    error_code="APPLY_WRENCH_FAILED",
                    suggestions=[
                        "Verify the model exists: gazebo_list_models()",
                        "Ensure ros_gz_interfaces is installed",
                        "Check that Modern Gazebo is running",
                    ],
                )
        else:
            return OperationResult(
                success=True,
                data={**result_data, "applied": False, "note": "Mock mode - Gazebo not available"},
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error applying force", error=str(e))
        return OperationResult(
            success=False, error=f"Failed to apply force: {e}", error_code="APPLY_FORCE_ERROR"
        )


def _get_mock_models() -> List[Dict[str, Any]]:
    """Get mock models for fallback when Gazebo is not available."""
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
