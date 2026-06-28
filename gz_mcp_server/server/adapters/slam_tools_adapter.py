"""
SLAM Tools MCP Adapter.

Exposes Gazebo SLAM & mapping tools as MCP tools:
- start_slam: Start a SLAM session with a chosen backend
- save_slam_map: Save the current SLAM map to disk
- load_slam_map: Load a previously saved SLAM map
- localize_robot: Localize a robot within a loaded map
- get_localization_quality: Assess localization estimate quality
- detect_loop_closure: Detect loop closures in the SLAM session
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import slam_tools
from gz_mcp_server.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for SLAM and mapping operations."""
    return [
        MCPTool(
            name="gazebo_start_slam",
            description=(
                "Start a SLAM (Simultaneous Localization and Mapping) session.\n\n"
                "Supported backends: slam_toolbox, cartographer, rtabmap, orb_slam3.\n\n"
                "Args:\n"
                "  backend: SLAM backend to use (default: 'slam_toolbox')\n"
                "  robot: Robot name to attach SLAM to (optional)\n"
                "  params: Backend-specific tuning parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Default: gazebo_start_slam()\n"
                "- With robot: gazebo_start_slam(backend='cartographer', robot='turtlebot3')\n"
                "- Tuned: gazebo_start_slam(backend='rtabmap', params={'resolution': 0.05})"
            ),
            parameters={
                "properties": {
                    "backend": {
                        "type": "string",
                        "description": "SLAM backend to use (default: 'slam_toolbox')",
                        "enum": ["slam_toolbox", "cartographer", "rtabmap", "orb_slam3"],
                        "default": "slam_toolbox",
                    },
                    "robot": {
                        "type": "string",
                        "description": "Robot name to attach SLAM to (optional)",
                    },
                    "params": {
                        "type": "object",
                        "description": "Backend-specific tuning parameters (optional)",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=slam_tools.start_slam,
        ),
        MCPTool(
            name="gazebo_save_slam_map",
            description=(
                "Save the current SLAM map to disk.\n\n"
                "Supported formats: pgm_yaml, ros_map_server.\n\n"
                "Args:\n"
                "  map_name: Unique name for the map (required, overwrite allowed)\n"
                "  output_path: Output directory/prefix for the map files (optional)\n"
                "  format: Map format (default: 'pgm_yaml')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_save_slam_map(map_name='warehouse')\n"
                "- ROS map server: gazebo_save_slam_map(map_name='lab', format='ros_map_server')\n"
                "- Custom path: gazebo_save_slam_map(map_name='floor1', output_path='/maps/floor1')"
            ),
            parameters={
                "properties": {
                    "map_name": {
                        "type": "string",
                        "description": "Unique name for the map (overwrite allowed)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output directory or prefix for the map files (optional)",
                    },
                    "format": {
                        "type": "string",
                        "description": "Map format (default: 'pgm_yaml')",
                        "enum": ["pgm_yaml", "ros_map_server"],
                        "default": "pgm_yaml",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["map_name"],
            },
            handler=slam_tools.save_slam_map,
        ),
        MCPTool(
            name="gazebo_load_slam_map",
            description=(
                "Load a previously saved SLAM map for localization or continued mapping.\n\n"
                "Returns map metadata including resolution, dimensions, and origin.\n\n"
                "Args:\n"
                "  map_path: Path to the map descriptor file (required)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Load: gazebo_load_slam_map(map_path='/maps/warehouse.yaml')\n"
                "- Detailed: gazebo_load_slam_map(map_path='/maps/lab.yaml', response_format='detailed')"
            ),
            parameters={
                "properties": {
                    "map_path": {
                        "type": "string",
                        "description": "Path to the map descriptor file (e.g. '/maps/my_map.yaml')",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["map_path"],
            },
            handler=slam_tools.load_slam_map,
        ),
        MCPTool(
            name="gazebo_localize_robot",
            description=(
                "Localize a robot within a loaded map.\n\n"
                "Supported methods: amcl, map_matching, icp.\n\n"
                "Args:\n"
                "  method: Localization method (default: 'amcl')\n"
                "  initial_pose: Initial pose hint, e.g. {x, y, theta} (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- AMCL: gazebo_localize_robot(method='amcl')\n"
                "- With hint: gazebo_localize_robot(method='amcl', initial_pose={x:1.0, y:2.0, theta:0.0})\n"
                "- ICP: gazebo_localize_robot(method='icp')"
            ),
            parameters={
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "Localization method (default: 'amcl')",
                        "enum": ["amcl", "map_matching", "icp"],
                        "default": "amcl",
                    },
                    "initial_pose": {
                        "type": "object",
                        "description": "Initial pose hint dict, e.g. {x, y, theta} (optional)",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=slam_tools.localize_robot,
        ),
        MCPTool(
            name="gazebo_get_localization_quality",
            description=(
                "Assess the quality of the current localization estimate.\n\n"
                "Returns particle spread, scan match score, ambiguity, and an\n"
                "overall quality rating of 'good', 'fair', or 'poor'.\n\n"
                "Args:\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Check: gazebo_get_localization_quality()\n"
                "- Detailed: gazebo_get_localization_quality(response_format='detailed')"
            ),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=slam_tools.get_localization_quality,
        ),
        MCPTool(
            name="gazebo_detect_loop_closure",
            description=(
                "Detect loop closures in the current SLAM session.\n\n"
                "Recognizes previously visited locations to correct accumulated drift.\n"
                "Returns whether a loop closure was detected, candidate matches,\n"
                "and the detection method used.\n\n"
                "Args:\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Check: gazebo_detect_loop_closure()\n"
                "- Detailed: gazebo_detect_loop_closure(response_format='detailed')"
            ),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=slam_tools.detect_loop_closure,
        ),
    ]
