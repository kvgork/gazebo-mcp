"""
Model Management MCP Adapter.

Exposes Gazebo model management tools as MCP tools:
- list_models: List all models in simulation
- spawn_model: Spawn new model from URDF/SDF or geometry
- delete_model: Remove model from simulation
- get_model_state: Query model pose and velocity
- set_model_state: Update model pose and velocity
- apply_force: Apply force/torque to a model
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import model_management
from gazebo_mcp.utils import OperationResult
from gazebo_mcp.mcp_protocol.server.mcp_tool import MCPTool


def spawn_model_wrapper(
    model_name: str,
    model_file: str = None,
    model_xml: str = None,
    pose: dict = None,
    reference_frame: str = "world",
    geometry: str = "box",
    size: dict = None,
    color: dict = None,
    static: bool = True,
) -> OperationResult:
    """Wrapper for spawn_model that converts MCP parameters to function parameters."""
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

    if size is None:
        size_tuple = (1.0, 1.0, 1.0)
    else:
        size_tuple = (
            size.get("x", 1.0),
            size.get("y", 1.0),
            size.get("z", 1.0),
        )

    if color is None:
        color_tuple = (0.0, 1.0, 0.0, 1.0)
    else:
        color_tuple = (
            color.get("r", 0.0),
            color.get("g", 1.0),
            color.get("b", 0.0),
            color.get("a", 1.0),
        )

    return model_management.spawn_model(
        model_name=model_name,
        x=x,
        y=y,
        z=z,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
        world=None,
        geometry=geometry,
        size=size_tuple,
        color=color_tuple,
        static=static,
    )


def delete_model_wrapper(model_name: str) -> OperationResult:
    """Wrapper for delete_model."""
    return model_management.delete_model(model_name=model_name, world=None)


def get_model_state_wrapper(
    model_name: str, response_format: str = "concise"
) -> OperationResult:
    """Wrapper for get_model_state."""
    return model_management.get_model_state(
        model_name=model_name,
        response_format=response_format,
        world=None,
    )


def set_model_state_wrapper(
    model_name: str,
    pose: dict = None,
    twist: dict = None,
    reference_frame: str = "world",
) -> OperationResult:
    """Wrapper for set_model_state."""
    return model_management.set_model_state(
        model_name=model_name,
        pose=pose,
        twist=twist,
        reference_frame=reference_frame,
        world=None,
    )


def list_models_wrapper(response_format: str = "filtered") -> OperationResult:
    """Wrapper for list_models."""
    return model_management.list_models(response_format=response_format, world=None)


def get_tools() -> List[MCPTool]:
    """Get MCP tools for model management."""
    return [
        MCPTool(
            name="gazebo_list_models",
            description=(
                "List all models currently in Gazebo simulation.\n\n"
                "Returns model data with progressive detail levels.\n"
                "Use response_format='summary' for counts only, 'filtered' for full data (default).\n\n"
                "Examples:\n"
                "- List all models: gazebo_list_models()\n"
                "- Get summary only: gazebo_list_models(response_format='summary')"
            ),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'filtered' (default) or 'summary' (counts only)",
                        "enum": ["filtered", "summary"],
                        "default": "filtered",
                    }
                },
                "required": [],
            },
            handler=list_models_wrapper,
        ),
        MCPTool(
            name="gazebo_spawn_model",
            description=(
                "Spawn a new model in Gazebo simulation.\n\n"
                "Creates a simple geometric shape (box, sphere, cylinder) at the specified pose.\n"
                "Can also load from URDF/SDF file or XML string.\n\n"
                "Args:\n"
                "  model_name: Unique name for the model (required)\n"
                "  pose: Initial pose with position {x, y, z} and orientation {roll, pitch, yaw}\n"
                "  geometry: Shape type - 'box', 'sphere', or 'cylinder' (default: 'box')\n"
                "  size: Dimensions {x, y, z} in meters (default: 1x1x1)\n"
                "  color: Color {r, g, b, a} with values 0-1 (default: green)\n"
                "  static: If true, model won't be affected by physics (default: true)\n\n"
                "Examples:\n"
                "- Spawn box: gazebo_spawn_model('box1', pose={'position': {'x': 1, 'y': 2, 'z': 0.5}})\n"
                "- Spawn sphere: gazebo_spawn_model('s1', geometry='sphere', size={'x': 0.5, 'y': 0.5, 'z': 0.5})"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Unique name for the model",
                    },
                    "pose": {
                        "type": "object",
                        "description": "Initial pose with position {x, y, z} and orientation {roll, pitch, yaw}",
                    },
                    "geometry": {
                        "type": "string",
                        "description": "Geometry type: 'box', 'sphere', or 'cylinder'",
                        "enum": ["box", "sphere", "cylinder"],
                        "default": "box",
                    },
                    "size": {
                        "type": "object",
                        "description": "Dimensions in meters {x, y, z}",
                    },
                    "color": {
                        "type": "object",
                        "description": "Color RGBA {r, g, b, a} with values 0-1",
                    },
                    "static": {
                        "type": "boolean",
                        "description": "If true, model won't move due to physics (default: true)",
                        "default": True,
                    },
                },
                "required": ["model_name"],
            },
            handler=spawn_model_wrapper,
        ),
        MCPTool(
            name="gazebo_delete_model",
            description=(
                "Delete a model from Gazebo simulation.\n\n"
                "Args:\n"
                "  model_name: Name of model to delete (required)\n\n"
                "Example: gazebo_delete_model('robot1')"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to delete",
                    }
                },
                "required": ["model_name"],
            },
            handler=delete_model_wrapper,
        ),
        MCPTool(
            name="gazebo_get_model_state",
            description=(
                "Get current state of a model (pose and velocity).\n\n"
                "Returns position, orientation (Euler angles), and velocity.\n\n"
                "Args:\n"
                "  model_name: Name of model to query (required)\n\n"
                "Example: gazebo_get_model_state('robot1')"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to query",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'concise' (default) or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["model_name"],
            },
            handler=get_model_state_wrapper,
        ),
        MCPTool(
            name="gazebo_set_model_state",
            description=(
                "Set model pose and/or velocity (teleport or set initial conditions).\n\n"
                "At least one of pose or twist must be provided.\n\n"
                "Args:\n"
                "  model_name: Name of model to update (required)\n"
                "  pose: Target pose {position: {x, y, z}, orientation: {roll, pitch, yaw}}\n"
                "  twist: Target velocity {linear: {x, y, z}, angular: {x, y, z}}\n\n"
                "Example: gazebo_set_model_state('robot1', pose={'position': {'x': 2, 'y': 1, 'z': 0.5}})"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of model to update",
                    },
                    "pose": {
                        "type": "object",
                        "description": "Target pose with position and orientation",
                    },
                    "twist": {
                        "type": "object",
                        "description": "Target velocity (linear and angular)",
                    },
                    "reference_frame": {
                        "type": "string",
                        "description": "Reference frame for pose (default: 'world')",
                        "default": "world",
                    },
                },
                "required": ["model_name"],
            },
            handler=set_model_state_wrapper,
        ),
        MCPTool(
            name="gazebo_apply_force",
            description=(
                "Apply a force and/or torque to a model for a short duration.\n\n"
                "Useful for testing physics reactions, pushing robots, or simulating\n"
                "external disturbances.\n\n"
                "At least one of force or torque must be provided.\n\n"
                "Args:\n"
                "  model_name: Name of the model to apply force to (required)\n"
                "  force: Force vector {'x': fx, 'y': fy, 'z': fz} in Newtons\n"
                "  torque: Torque vector {'x': tx, 'y': ty, 'z': tz} in N·m\n"
                "  duration: Duration to apply force in seconds (default: 0.1)\n\n"
                "Examples:\n"
                "- Push forward: gazebo_apply_force('robot1', force={'x': 10.0, 'y': 0.0, 'z': 0.0})\n"
                "- Spin: gazebo_apply_force('robot1', torque={'x': 0.0, 'y': 0.0, 'z': 5.0})\n"
                "- Lift: gazebo_apply_force('box1', force={'x': 0.0, 'y': 0.0, 'z': 50.0}, duration=0.5)"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of the model to apply force to",
                    },
                    "force": {
                        "type": "object",
                        "description": "Force vector in Newtons: {'x': fx, 'y': fy, 'z': fz}",
                    },
                    "torque": {
                        "type": "object",
                        "description": "Torque vector in N·m: {'x': tx, 'y': ty, 'z': tz}",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration to apply force in seconds (default: 0.1)",
                        "default": 0.1,
                        "minimum": 0.001,
                        "maximum": 60.0,
                    },
                },
                "required": ["model_name"],
            },
            handler=model_management.apply_force,
        ),
    ]
