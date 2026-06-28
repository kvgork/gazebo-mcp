"""
Nav2 Tools MCP Adapter.

Exposes Gazebo Navigation & Path Planning (Nav2) tools as MCP tools:
- initialize_nav2: Bring up the Nav2 navigation stack
- send_nav_goal: Send a navigation goal pose
- cancel_nav_goal: Cancel an active navigation goal
- get_nav_status: Query current navigation status
- plan_path: Plan a global path from start to goal
- visualize_path: Get markers/instructions to visualize a planned path
- create_occupancy_map: Build an occupancy grid map of a world
- update_costmap: Apply a batch of costmap updates
- follow_waypoints: Start a waypoint-following mission
- plan_coverage_path: Plan a coverage path over an area
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import nav2_tools
from mcp.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for Nav2 navigation and path planning operations."""
    return [
        MCPTool(
            name="gazebo_initialize_nav2",
            description=(
                "Initialize and activate the Nav2 navigation stack.\n\n"
                "Brings up the navigation lifecycle and reports the lifecycle nodes.\n\n"
                "Args:\n"
                "  robot: Robot/namespace name to initialize Nav2 for (optional)\n"
                "  params: Dict of Nav2 parameter overrides (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_initialize_nav2()\n"
                "- For robot: gazebo_initialize_nav2(robot='turtlebot3')"
            ),
            parameters={
                "properties": {
                    "robot": {
                        "type": "string",
                        "description": "Robot/namespace name to initialize Nav2 for (optional)",
                    },
                    "params": {
                        "type": "object",
                        "description": "Dict of Nav2 parameter overrides (optional)",
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
            handler=nav2_tools.initialize_nav2,
        ),
        MCPTool(
            name="gazebo_send_nav_goal",
            description=(
                "Send a navigation goal pose to the Nav2 stack.\n\n"
                "Supported planners: DWB, TEB, RPP, MPPI.\n\n"
                "Args:\n"
                "  x: Target X coordinate in the map frame (required)\n"
                "  y: Target Y coordinate in the map frame (required)\n"
                "  theta: Target yaw in radians (default: 0.0)\n"
                "  planner: Controller/planner plugin (default: 'DWB')\n"
                "  behavior_tree: Path to a custom behavior tree XML (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_send_nav_goal(x=2.0, y=3.0)\n"
                "- With planner: gazebo_send_nav_goal(x=1.0, y=2.0, theta=1.57, planner='TEB')"
            ),
            parameters={
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "Target X coordinate in the map frame",
                    },
                    "y": {
                        "type": "number",
                        "description": "Target Y coordinate in the map frame",
                    },
                    "theta": {
                        "type": "number",
                        "description": "Target yaw orientation in radians (default: 0.0)",
                        "default": 0.0,
                    },
                    "planner": {
                        "type": "string",
                        "description": "Controller/planner plugin (default: 'DWB')",
                        "enum": ["DWB", "TEB", "RPP", "MPPI"],
                        "default": "DWB",
                    },
                    "behavior_tree": {
                        "type": "string",
                        "description": "Path to a custom behavior tree XML (optional)",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["x", "y"],
            },
            handler=nav2_tools.send_nav_goal,
        ),
        MCPTool(
            name="gazebo_cancel_nav_goal",
            description=(
                "Cancel an active navigation goal.\n\n"
                "If goal_id is omitted, cancels the current goal.\n\n"
                "Args:\n"
                "  goal_id: ID of the goal to cancel; omit to cancel current (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Cancel current: gazebo_cancel_nav_goal()\n"
                "- Cancel specific: gazebo_cancel_nav_goal(goal_id='goal_1')"
            ),
            parameters={
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to cancel; omit to cancel current",
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
            handler=nav2_tools.cancel_nav_goal,
        ),
        MCPTool(
            name="gazebo_get_nav_status",
            description=(
                "Get the current navigation status.\n\n"
                "Returns active goal, progress, distance remaining, and obstacles.\n\n"
                "Args:\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- gazebo_get_nav_status()"
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
            handler=nav2_tools.get_nav_status,
        ),
        MCPTool(
            name="gazebo_plan_path",
            description=(
                "Plan a global path from a start pose to a goal pose.\n\n"
                "Supported planners: A*, RRT, RRT*, DWB, TEB.\n\n"
                "Args:\n"
                "  start: Start position dict with 'x' and 'y' (required)\n"
                "  goal: Goal position dict with 'x' and 'y' (required)\n"
                "  planner: Global planner (default: 'A*')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_plan_path(start={x:0,y:0}, goal={x:5,y:3})\n"
                "- With planner: gazebo_plan_path(start={x:0,y:0}, goal={x:5,y:5}, planner='RRT*')"
            ),
            parameters={
                "properties": {
                    "start": {
                        "type": "object",
                        "description": "Start position dict with 'x' and 'y' keys",
                    },
                    "goal": {
                        "type": "object",
                        "description": "Goal position dict with 'x' and 'y' keys",
                    },
                    "planner": {
                        "type": "string",
                        "description": "Global planner (default: 'A*')",
                        "enum": ["A*", "RRT", "RRT*", "DWB", "TEB"],
                        "default": "A*",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["start", "goal"],
            },
            handler=nav2_tools.plan_path,
        ),
        MCPTool(
            name="gazebo_visualize_path",
            description=(
                "Get markers and RViz2 instructions to visualize a planned path.\n\n"
                "If path_id is omitted, visualizes the most recently planned path.\n"
                "Errors with PATH_NOT_FOUND if the id is unknown.\n\n"
                "Args:\n"
                "  path_id: ID of a previously planned path (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- gazebo_visualize_path(path_id='path_1')"
            ),
            parameters={
                "properties": {
                    "path_id": {
                        "type": "string",
                        "description": "ID of a previously planned path; omit for the latest",
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
            handler=nav2_tools.visualize_path,
        ),
        MCPTool(
            name="gazebo_create_occupancy_map",
            description=(
                "Create an occupancy grid map of the simulation world.\n\n"
                "Args:\n"
                "  resolution: Map resolution in meters/cell; must be > 0 (default: 0.05)\n"
                "  world: Name of the world to map (default: 'default')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_create_occupancy_map()\n"
                "- High-res: gazebo_create_occupancy_map(resolution=0.025, world='warehouse')"
            ),
            parameters={
                "properties": {
                    "resolution": {
                        "type": "number",
                        "description": "Map resolution in meters/cell; must be > 0 (default: 0.05)",
                        "default": 0.05,
                        "minimum": 0.001,
                    },
                    "world": {
                        "type": "string",
                        "description": "Name of the world to map (default: 'default')",
                        "default": "default",
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
            handler=nav2_tools.create_occupancy_map,
        ),
        MCPTool(
            name="gazebo_update_costmap",
            description=(
                "Apply a batch of updates to the navigation costmap.\n\n"
                "Each update is a dict with an 'action' of 'inject', 'clear', or 'inflate'.\n\n"
                "Args:\n"
                "  updates: Non-empty list of update dicts (required)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Inject: gazebo_update_costmap(updates=[{action:'inject', x:1.0, y:2.0, radius:0.5}])\n"
                "- Clear: gazebo_update_costmap(updates=[{action:'clear'}])"
            ),
            parameters={
                "properties": {
                    "updates": {
                        "type": "array",
                        "description": "Non-empty list of update dicts, each with an 'action' key",
                        "items": {"type": "object"},
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["updates"],
            },
            handler=nav2_tools.update_costmap,
        ),
        MCPTool(
            name="gazebo_follow_waypoints",
            description=(
                "Start a waypoint-following mission.\n\n"
                "Supported modes: sequence, loop, patrol.\n\n"
                "Args:\n"
                "  waypoints: Non-empty list of waypoint dicts with 'x' and 'y' (required)\n"
                "  mode: Mission mode (default: 'sequence')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Sequence: gazebo_follow_waypoints(waypoints=[{x:1,y:1},{x:2,y:2}])\n"
                "- Loop: gazebo_follow_waypoints(waypoints=[{x:1,y:1}], mode='loop')"
            ),
            parameters={
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "description": "Non-empty list of waypoint dicts with 'x' and 'y' keys",
                        "items": {"type": "object"},
                    },
                    "mode": {
                        "type": "string",
                        "description": "Mission mode (default: 'sequence')",
                        "enum": ["sequence", "loop", "patrol"],
                        "default": "sequence",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["waypoints"],
            },
            handler=nav2_tools.follow_waypoints,
        ),
        MCPTool(
            name="gazebo_plan_coverage_path",
            description=(
                "Plan a coverage path over an area (e.g. sweeping or inspection).\n\n"
                "Supported algorithms: boustrophedon, spiral, energy_efficient.\n\n"
                "Args:\n"
                "  area: Dict describing the area to cover (required)\n"
                "  algorithm: Coverage algorithm (default: 'boustrophedon')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_plan_coverage_path(area={min_x:0,min_y:0,max_x:5,max_y:5})\n"
                "- Spiral: gazebo_plan_coverage_path(area={min_x:0,min_y:0,max_x:5,max_y:5}, algorithm='spiral')"
            ),
            parameters={
                "properties": {
                    "area": {
                        "type": "object",
                        "description": "Dict describing the area to cover (e.g. bounds)",
                    },
                    "algorithm": {
                        "type": "string",
                        "description": "Coverage algorithm (default: 'boustrophedon')",
                        "enum": ["boustrophedon", "spiral", "energy_efficient"],
                        "default": "boustrophedon",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["area"],
            },
            handler=nav2_tools.plan_coverage_path,
        ),
    ]
