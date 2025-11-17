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
            handler=model_management.list_models
        ),

        # Spawn model tool:
        MCPTool(
            name="gazebo_spawn_model",
            description="""
Spawn a new model in Gazebo simulation.

Supports both URDF and SDF model formats. Model can be loaded from file or provided as XML string.

Args:
    model_name: Unique name for the model (required)
    model_file: Path to URDF/SDF file (optional if model_xml provided)
    model_xml: URDF/SDF XML content as string (optional if model_file provided)
    pose: Initial pose dict with position {x, y, z} and orientation {roll, pitch, yaw} (optional)
    reference_frame: Frame for pose, default "world" (optional)

Returns operation result with spawn status.

Examples:
- Spawn from file: gazebo_spawn_model("robot1", model_file="/path/to/robot.urdf")
- Spawn at position: gazebo_spawn_model("box1", model_file="box.sdf", pose={"position": {"x": 1, "y": 2, "z": 0.5}})
- Spawn from XML: gazebo_spawn_model("sphere", model_xml="<sdf>...</sdf>")
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
                    }
                },
                "required": ["model_name"]
            },
            handler=model_management.spawn_model
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
            handler=model_management.delete_model
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
            handler=model_management.get_model_state
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
            handler=model_management.set_model_state
        ),
    ]
