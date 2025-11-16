"""
World Tools MCP Adapter.

Exposes Gazebo world management tools as MCP tools:
- load_world: Load world from SDF file (provides instructions)
- save_world: Save current world state (provides instructions)
- get_world_properties: Query physics settings, gravity, etc.
- set_world_property: Update world properties

Note: World loading/saving requires Gazebo restart or manual operations.
These tools provide guidance and validation.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import world_tools


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
    Get MCP tools for world management.

    Returns:
        List of MCPTool instances
    """
    return [
        # Load world tool:
        MCPTool(
            name="gazebo_load_world",
            description="""
Load a Gazebo world from SDF file.

Note: Gazebo must be restarted to load a different world file.
This tool validates the file and provides instructions for loading.

Args:
    world_file_path: Path to SDF world file (required)

Returns validation result and loading instructions.

Examples:
- gazebo_load_world("/path/to/my_world.sdf")
- gazebo_load_world("/usr/share/gazebo/worlds/empty.world")

Alternative: Use spawn_model() to add individual models to current world.
            """.strip(),
            parameters={
                "properties": {
                    "world_file_path": {
                        "type": "string",
                        "description": "Path to SDF world file (.sdf extension)"
                    }
                },
                "required": ["world_file_path"]
            },
            handler=world_tools.load_world
        ),

        # Save world tool:
        MCPTool(
            name="gazebo_save_world",
            description="""
Save current Gazebo world state to SDF file.

Note: World saving via MCP is not yet fully implemented.
This tool provides instructions for manual saving.

Args:
    output_path: Path where to save world file (required)

Returns save instructions and status.

Examples:
- gazebo_save_world("/tmp/saved_world.sdf")
- gazebo_save_world("~/my_worlds/experiment_01.sdf")
            """.strip(),
            parameters={
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the world file (.sdf recommended)"
                    }
                },
                "required": ["output_path"]
            },
            handler=world_tools.save_world
        ),

        # Get world properties tool:
        MCPTool(
            name="gazebo_get_world_properties",
            description="""
Get Gazebo world properties and physics settings.

Returns:
- world_name: Name of current world
- gravity: Gravity vector {x, y, z}
- physics: Physics engine settings
  - engine: Physics engine (ode, bullet, simbody, dart)
  - update_rate: Physics update rate (Hz)
  - max_step_size: Maximum simulation step size (seconds)
  - real_time_factor: Real-time factor (1.0 = real-time)
  - real_time_update_rate: Real-time update rate (Hz)
- scene: Visual settings
  - ambient: Ambient light RGBA
  - background: Background color RGBA
  - shadows: Shadow rendering enabled
  - grid: Grid display enabled
- simulation_time: Current simulation time
- real_time: Elapsed real time
- iterations: Physics iterations

Example:
- gazebo_get_world_properties()
            """.strip(),
            parameters={
                "properties": {},
                "required": []
            },
            handler=world_tools.get_world_properties
        ),

        # Set world property tool:
        MCPTool(
            name="gazebo_set_world_property",
            description="""
Set a Gazebo world property.

Note: Some properties can only be set before Gazebo starts (in world SDF file).
This tool provides guidance for manual property setting.

Supported properties:
- gravity: Gravity vector {x, y, z}
- physics_update_rate: Physics update rate (Hz)
- max_step_size: Maximum simulation step size (seconds)
- real_time_factor: Target real-time factor

Args:
    property_name: Name of property to set (required)
    value: New value for the property (required)

Returns update status and instructions.

Examples:
- gazebo_set_world_property("gravity", {"x": 0, "y": 0, "z": -9.81})
- gazebo_set_world_property("physics_update_rate", 1000.0)
- gazebo_set_world_property("real_time_factor", 2.0)
            """.strip(),
            parameters={
                "properties": {
                    "property_name": {
                        "type": "string",
                        "description": "Name of property to set (gravity, physics_update_rate, max_step_size, real_time_factor)"
                    },
                    "value": {
                        "description": "New value for the property (type depends on property)"
                    }
                },
                "required": ["property_name", "value"]
            },
            handler=world_tools.set_world_property
        ),
    ]
