"""
World Tools MCP Adapter.

Exposes Gazebo world management tools as MCP tools:
- load_world: Load world from SDF file (provides instructions)
- save_world: Save current world state (provides instructions)
- get_world_properties: Query physics settings, gravity, etc.
- set_world_property: Update world properties
- set_gravity: Set simulation gravity vector
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import world_tools
from gazebo_mcp.mcp_protocol.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for world management."""
    return [
        MCPTool(
            name="gazebo_load_world",
            description=(
                "Load a Gazebo world from SDF file.\n\n"
                "Validates the file and provides launch instructions.\n"
                "Gazebo must be restarted to load a different world.\n\n"
                "Args:\n"
                "  world_file_path: Path to SDF world file (required)\n\n"
                "Example: gazebo_load_world('/path/to/my_world.sdf')"
            ),
            parameters={
                "properties": {
                    "world_file_path": {
                        "type": "string",
                        "description": "Path to SDF world file (.sdf extension)",
                    }
                },
                "required": ["world_file_path"],
            },
            handler=world_tools.load_world,
        ),
        MCPTool(
            name="gazebo_save_world",
            description=(
                "Save current Gazebo world state to SDF file.\n\n"
                "Provides instructions for saving (manual step required).\n\n"
                "Args:\n"
                "  output_path: Path where to save world file (required)\n\n"
                "Example: gazebo_save_world('/tmp/saved_world.sdf')"
            ),
            parameters={
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the world file",
                    }
                },
                "required": ["output_path"],
            },
            handler=world_tools.save_world,
        ),
        MCPTool(
            name="gazebo_get_world_properties",
            description=(
                "Get Gazebo world properties and physics settings.\n\n"
                "Returns gravity, physics engine settings, scene configuration, "
                "and simulation time.\n\n"
                "Example: gazebo_get_world_properties()"
            ),
            parameters={
                "properties": {},
                "required": [],
            },
            handler=world_tools.get_world_properties,
        ),
        MCPTool(
            name="gazebo_set_world_property",
            description=(
                "Set a Gazebo world property.\n\n"
                "Supported: gravity, physics_update_rate, max_step_size, real_time_factor\n\n"
                "Args:\n"
                "  property_name: Name of property to set (required)\n"
                "  value: New value for the property (required)\n\n"
                "Examples:\n"
                "- gazebo_set_world_property('gravity', {'x': 0, 'y': 0, 'z': -9.81})\n"
                "- gazebo_set_world_property('physics_update_rate', 1000.0)"
            ),
            parameters={
                "properties": {
                    "property_name": {
                        "type": "string",
                        "description": "Name of property to set",
                    },
                    "value": {
                        "description": "New value for the property",
                    },
                },
                "required": ["property_name", "value"],
            },
            handler=world_tools.set_world_property,
        ),
        MCPTool(
            name="gazebo_set_gravity",
            description=(
                "Set simulation gravity vector.\n\n"
                "Standard presets:\n"
                "- Earth gravity (default): z = -9.81 m/s²\n"
                "- Zero-g (space): x=y=z=0\n"
                "- Moon gravity: z = -1.62 m/s²\n\n"
                "Returns SDF snippet for manual use when runtime change is not supported.\n\n"
                "Args:\n"
                "  x: Gravity in X axis (m/s², default 0.0)\n"
                "  y: Gravity in Y axis (m/s², default 0.0)\n"
                "  z: Gravity in Z axis (m/s², default -9.81)\n\n"
                "Examples:\n"
                "- Earth: gazebo_set_gravity()\n"
                "- Zero-g: gazebo_set_gravity(z=0.0)\n"
                "- Moon: gazebo_set_gravity(z=-1.62)"
            ),
            parameters={
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "Gravity in X axis (m/s², default 0.0)",
                        "default": 0.0,
                    },
                    "y": {
                        "type": "number",
                        "description": "Gravity in Y axis (m/s², default 0.0)",
                        "default": 0.0,
                    },
                    "z": {
                        "type": "number",
                        "description": "Gravity in Z axis (m/s², default -9.81)",
                        "default": -9.81,
                    },
                },
                "required": [],
            },
            handler=world_tools.set_gravity,
        ),
    ]
