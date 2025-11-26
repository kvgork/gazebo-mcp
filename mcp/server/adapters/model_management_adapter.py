"""
Model Management MCP Adapter.

Exposes Gazebo model management tools as MCP tools:
- list_models: List all models in simulation
- spawn_model: Spawn new model from URDF/SDF
- delete_model: Remove model from simulation
- get_model_state: Query model pose and velocity
- set_model_state: Update model pose and velocity

Follows Anthropic best practices:
- Progressive disclosure (summary by default)
- ResultFilter pattern for token efficiency
- Clear parameter descriptions
- Agent-friendly responses
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import model_management
from gazebo_mcp.utils import OperationResult


def spawn_model_wrapper(
    model_name: str,
    model_file: str = None,
    model_xml: str = None,
    pose: dict = None,
    reference_frame: str = "world",
    geometry: str = "box",
    size: dict = None,
    color: dict = None,
    static: bool = True
) -> OperationResult:
    """
    Wrapper for spawn_model that converts MCP parameters to function parameters.
    """
    # Extract position and orientation from pose dict
    x, y, z = 0.0, 0.0, 0.0
    roll, pitch, yaw = 0.0, 0.0, 0.0

    if pose:
        if "position" in pose:
            x = pose["position"].get("x", 0.0)
            y = pose["position"].get("y", 0.0)
            z = pose["position"].get("z", 0.0)
        if "orientation" in pose:
            roll = pose["orientation"].get("roll", 0.0)
            pitch = pose["orientation"].get("pitch", 0.0)
            yaw = pose["orientation"].get("yaw", 0.0)

    # Convert size dict to tuple
    if size is None:
        size_tuple = (1.0, 1.0, 1.0)
    else:
        size_tuple = (
            size.get("x", 1.0),
            size.get("y", 1.0),
            size.get("z", 1.0)
        )

    # Convert color dict to tuple (RGBA)
    if color is None:
        color_tuple = (0.0, 1.0, 0.0, 1.0)  # Green default
    else:
        color_tuple = (
            color.get("r", 0.0),
            color.get("g", 1.0),
            color.get("b", 0.0),
            color.get("a", 1.0)
        )

    # Call the underlying function with the empty world
    return model_management.spawn_model(
        model_name=model_name,
        x=x,
        y=y,
        z=z,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
        world="empty",
        geometry=geometry,
        size=size_tuple,
        color=color_tuple,
        static=static
    )


def delete_model_wrapper(model_name: str) -> OperationResult:
    """Wrapper for delete_model that uses the empty world."""
    return model_management.delete_model(model_name=model_name, world="empty")


def get_model_state_wrapper(model_name: str, response_format: str = "concise") -> OperationResult:
    """Wrapper for get_model_state that uses the empty world."""
    return model_management.get_model_state(
        model_name=model_name,
        response_format=response_format,
        world="empty"
    )


def set_model_state_wrapper(
    model_name: str,
    pose: dict = None,
    twist: dict = None,
    reference_frame: str = "world"
) -> OperationResult:
    """Wrapper for set_model_state that uses the empty world."""
    return model_management.set_model_state(
        model_name=model_name,
        pose=pose,
        twist=twist,
        reference_frame=reference_frame,
        world="empty"
    )


def list_models_wrapper(response_format: str = "filtered") -> OperationResult:
    """Wrapper for list_models that uses the empty world."""
    return model_management.list_models(response_format=response_format, world="empty")


class MCPTool:
    """MCP tool definition (imported from server.py context)."""

    def __init__(self, name, description, parameters, handler):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", [])
            }
        }


def get_tools() -> List[MCPTool]:
    """
    Get MCP tools for model management.

    Returns:
        List of MCPTool instances
    """
    return [
        # List models tool:
        MCPTool(
            name="gazebo_list_models",
            description="""
List all models currently in Gazebo simulation.

Returns model data with ResultFilter pattern for token efficiency.
By default, returns all models with filter examples.

Use response_format="summary" for just counts and names (recommended for large simulations).
Use response_format="filtered" to get data that you can filter locally (default).

Examples:
- List all models: gazebo_list_models()
- Get summary only: gazebo_list_models(response_format="summary")
            """.strip(),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'filtered' (default, returns data + filter examples) or 'summary' (counts only)",
                        "enum": ["filtered", "summary"],
                        "default": "filtered"
                    }
                },
                "required": []
            },
            handler=list_models_wrapper
        ),

        # Spawn model tool:
        MCPTool(
            name="gazebo_spawn_model",
            description="""
Spawn a new model in Gazebo simulation.

Supports both URDF and SDF model formats. Model can be loaded from file or provided as XML string.
If no model_file or model_xml is provided, generates a simple geometric model.

Args:
    model_name: Unique name for the model (required)
    model_file: Path to URDF/SDF file (optional if model_xml provided)
    model_xml: URDF/SDF XML content as string (optional if model_file provided)
    pose: Initial pose dict with position {x, y, z} and orientation {roll, pitch, yaw} (optional)
    reference_frame: Frame for pose, default "world" (optional)
    geometry: Shape type - "box", "sphere", or "cylinder" (default: "box")
    size: Dimensions {x, y, z} in meters (default: {x:1, y:1, z:1})
    color: Color {r, g, b, a} with values 0-1 (default: {r:0, g:1, b:0, a:1} - green)
    static: If true, model won't be affected by physics (default: true)

Returns operation result with spawn status.

Examples:
- Spawn green box: gazebo_spawn_model("box1", pose={"position": {"x": 1, "y": 2, "z": 0.5}})
- Spawn red wall: gazebo_spawn_model("wall1", pose={"position": {"x": 0, "y": 3, "z": 0.5}}, size={"x": 0.2, "y": 4, "z": 1}, color={"r": 0.8, "g": 0.2, "b": 0.2, "a": 1})
- Spawn blue sphere: gazebo_spawn_model("sphere1", geometry="sphere", size={"x": 0.5, "y": 0.5, "z": 0.5}, color={"r": 0, "g": 0, "b": 1, "a": 1})
- Spawn from file: gazebo_spawn_model("robot1", model_file="/path/to/robot.urdf")
            """.strip(),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Unique name for the model (1-50 chars, alphanumeric + underscore)"
                    },
                    "model_file": {
                        "type": "string",
                        "description": "Path to URDF or SDF file (optional if model_xml provided)"
                    },
                    "model_xml": {
                        "type": "string",
                        "description": "URDF or SDF XML content as string (optional if model_file provided)"
                    },
                    "pose": {
                        "type": "object",
                        "description": "Initial pose with position {x, y, z} and orientation {roll, pitch, yaw}",
                        "properties": {
                            "position": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "z": {"type": "number"}
                                }
                            },
                            "orientation": {
                                "type": "object",
                                "properties": {
                                    "roll": {"type": "number", "description": "Roll in radians"},
                                    "pitch": {"type": "number", "description": "Pitch in radians"},
                                    "yaw": {"type": "number", "description": "Yaw in radians"}
                                }
                            }
                        }
                    },
                    "reference_frame": {
                        "type": "string",
                        "description": "Reference frame for pose (default: 'world')",
                        "default": "world"
                    },
                    "geometry": {
                        "type": "string",
                        "description": "Geometry type: 'box', 'sphere', or 'cylinder' (default: 'box')",
                        "enum": ["box", "sphere", "cylinder"],
                        "default": "box"
                    },
                    "size": {
                        "type": "object",
                        "description": "Dimensions in meters {x, y, z} (default: 1x1x1)",
                        "properties": {
                            "x": {"type": "number", "description": "Width (default: 1.0)"},
                            "y": {"type": "number", "description": "Depth (default: 1.0)"},
                            "z": {"type": "number", "description": "Height (default: 1.0)"}
                        }
                    },
                    "color": {
                        "type": "object",
                        "description": "Color RGBA with values 0-1 (default: green)",
                        "properties": {
                            "r": {"type": "number", "description": "Red (0-1, default: 0)"},
                            "g": {"type": "number", "description": "Green (0-1, default: 1)"},
                            "b": {"type": "number", "description": "Blue (0-1, default: 0)"},
                            "a": {"type": "number", "description": "Alpha/opacity (0-1, default: 1)"}
                        }
                    },
                    "static": {
                        "type": "boolean",
                        "description": "If true, model won't move due to physics (default: true)",
                        "default": True
                    }
                },
                "required": ["model_name"]
            },
            handler=spawn_model_wrapper
        ),

        # Delete model tool:
        MCPTool(
            name="gazebo_delete_model",
            description="""
Delete a model from Gazebo simulation.

Args:
    model_name: Name of model to delete (required)

Returns operation result with deletion status.

Example:
- gazebo_delete_model("robot1")
            """.strip(),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to delete"
                    }
                },
                "required": ["model_name"]
            },
            handler=delete_model_wrapper
        ),

        # Get model state tool:
        MCPTool(
            name="gazebo_get_model_state",
            description="""
Get current state of a model (pose and velocity).

Args:
    model_name: Name of model to query (required)
    reference_frame: Reference frame for pose (default: "world", optional)

Returns model state with:
- pose: {position: {x, y, z}, orientation: {x, y, z, w}}
- twist: {linear: {x, y, z}, angular: {x, y, z}}

Example:
- gazebo_get_model_state("robot1")
- gazebo_get_model_state("robot1", reference_frame="world")
            """.strip(),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to query"
                    },
                    "reference_frame": {
                        "type": "string",
                        "description": "Reference frame for pose (default: 'world')",
                        "default": "world"
                    }
                },
                "required": ["model_name"]
            },
            handler=get_model_state_wrapper
        ),

        # Set model state tool:
        MCPTool(
            name="gazebo_set_model_state",
            description="""
Set model pose and/or velocity (teleport model or set initial conditions).

Args:
    model_name: Name of model to update (required)
    pose: Target pose (optional):
        {
            "position": {"x": float, "y": float, "z": float},
            "orientation": {"roll": float, "pitch": float, "yaw": float}
                OR {"x": float, "y": float, "z": float, "w": float}
        }
    twist: Target velocity (optional):
        {
            "linear": {"x": float, "y": float, "z": float},
            "angular": {"x": float, "y": float, "z": float}
        }
    reference_frame: Reference frame for pose (default: "world", optional)

At least one of pose or twist must be provided.

Returns operation result with update status.

Examples:
- gazebo_set_model_state("robot1", pose={"position": {"x": 2, "y": 1, "z": 0.5}})
- gazebo_set_model_state("robot1", twist={"linear": {"x": 0.5, "y": 0, "z": 0}})
- gazebo_set_model_state("robot1",
    pose={"position": {"x": 0, "y": 0, "z": 0.5}, "orientation": {"roll": 0, "pitch": 0, "yaw": 1.57}},
    twist={"linear": {"x": 0, "y": 0, "z": 0}}
  )
            """.strip(),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to update"
                    },
                    "pose": {
                        "type": "object",
                        "description": "Target pose with position and orientation",
                        "properties": {
                            "position": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "z": {"type": "number"}
                                },
                                "required": ["x", "y", "z"]
                            },
                            "orientation": {
                                "type": "object",
                                "description": "Euler angles (roll, pitch, yaw) or quaternion (x, y, z, w)"
                            }
                        }
                    },
                    "twist": {
                        "type": "object",
                        "description": "Target velocity (linear and angular)",
                        "properties": {
                            "linear": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "z": {"type": "number"}
                                },
                                "required": ["x", "y", "z"]
                            },
                            "angular": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "z": {"type": "number"}
                                },
                                "required": ["x", "y", "z"]
                            }
                        }
                    },
                    "reference_frame": {
                        "type": "string",
                        "description": "Reference frame for pose (default: 'world')",
                        "default": "world"
                    }
                },
                "required": ["model_name"]
            },
            handler=set_model_state_wrapper
        ),
    ]
