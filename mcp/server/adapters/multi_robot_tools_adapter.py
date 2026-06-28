"""
Multi-Robot Coordination MCP Adapter.

Exposes Gazebo multi-robot coordination tools as MCP tools:
- spawn_robot_fleet: Spawn a fleet in a collision-free formation
- get_fleet_status: Query status of one fleet or all fleets
- send_fleet_command: Send a command to a fleet or subset of robots
- apply_swarm_behavior: Apply a swarm behavior to a fleet
- visualize_robot_network: Generate multi-robot network visualization markers
- enable_multi_robot_collision_avoidance: Configure fleet collision avoidance
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import multi_robot_tools
from mcp.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for multi-robot coordination operations."""
    return [
        MCPTool(
            name="gazebo_spawn_robot_fleet",
            description=(
                "Spawn a fleet of robots in a collision-free formation.\n\n"
                "Supported formations: line, grid, circle, random.\n"
                "Poses are computed deterministically so robots never overlap.\n\n"
                "Args:\n"
                "  robot_type: Robot model/type to spawn (required)\n"
                "  count: Number of robots; positive integer (required)\n"
                "  formation: Formation layout (default: 'grid')\n"
                "  spacing: Minimum spacing in meters (default: 2.0)\n"
                "  namespace_prefix: Per-robot namespace prefix (default: 'robot')\n"
                "  origin: Origin dict {x, y, z} for the formation (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Grid: gazebo_spawn_robot_fleet(robot_type='turtlebot3', count=4)\n"
                "- Line: gazebo_spawn_robot_fleet(robot_type='turtlebot3', count=3, formation='line')\n"
                "- Circle: gazebo_spawn_robot_fleet(robot_type='turtlebot3', count=6, formation='circle', spacing=1.5)"
            ),
            parameters={
                "properties": {
                    "robot_type": {
                        "type": "string",
                        "description": "Robot model/type to spawn",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of robots to spawn (positive integer)",
                        "minimum": 1,
                    },
                    "formation": {
                        "type": "string",
                        "description": "Formation layout (default: 'grid')",
                        "enum": ["line", "grid", "circle", "random"],
                        "default": "grid",
                    },
                    "spacing": {
                        "type": "number",
                        "description": "Minimum spacing between robots in meters (default: 2.0)",
                        "default": 2.0,
                        "minimum": 0.001,
                    },
                    "namespace_prefix": {
                        "type": "string",
                        "description": "Prefix for per-robot namespaces (default: 'robot')",
                        "default": "robot",
                    },
                    "origin": {
                        "type": "object",
                        "description": "Origin dict {x, y, z} for the formation (default: {0,0,0})",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["robot_type", "count"],
            },
            handler=multi_robot_tools.spawn_robot_fleet,
        ),
        MCPTool(
            name="gazebo_get_fleet_status",
            description=(
                "Get the status of one fleet or all fleets.\n\n"
                "Returns per-robot status: position, velocity, battery percentage,\n"
                "and task status. Unknown fleet_id returns FLEET_NOT_FOUND.\n\n"
                "Args:\n"
                "  fleet_id: Fleet ID to query; omit to query all fleets (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- One fleet: gazebo_get_fleet_status(fleet_id='fleet_1')\n"
                "- All fleets: gazebo_get_fleet_status()"
            ),
            parameters={
                "properties": {
                    "fleet_id": {
                        "type": "string",
                        "description": "Fleet ID to query; omit to query all fleets",
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
            handler=multi_robot_tools.get_fleet_status,
        ),
        MCPTool(
            name="gazebo_send_fleet_command",
            description=(
                "Send a command to a fleet or a subset of its robots.\n\n"
                "Supported commands: move, stop, formation, sync, return_home.\n"
                "If targets is omitted, the command broadcasts to the whole fleet.\n\n"
                "Args:\n"
                "  command: Command to dispatch (required)\n"
                "  fleet_id: Fleet to command; omit to use the first fleet (optional)\n"
                "  targets: Subset of robot names; omit to broadcast (optional)\n"
                "  params: Command parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Move: gazebo_send_fleet_command(command='move', fleet_id='fleet_1')\n"
                "- Stop subset: gazebo_send_fleet_command(command='stop', targets=['robot_1'])\n"
                "- Return home: gazebo_send_fleet_command(command='return_home')"
            ),
            parameters={
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to dispatch to the fleet",
                        "enum": ["move", "stop", "formation", "sync", "return_home"],
                    },
                    "fleet_id": {
                        "type": "string",
                        "description": "Fleet to command; omit to use the first available fleet",
                    },
                    "targets": {
                        "type": "array",
                        "description": "Subset of robot names to command; omit to broadcast",
                        "items": {"type": "string"},
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional command parameters dict",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["command"],
            },
            handler=multi_robot_tools.send_fleet_command,
        ),
        MCPTool(
            name="gazebo_apply_swarm_behavior",
            description=(
                "Apply a swarm behavior to a fleet.\n\n"
                "Supported behaviors: flocking, coverage, formation_keeping,\n"
                "leader_follower, consensus.\n\n"
                "Args:\n"
                "  behavior: Swarm behavior to apply (required)\n"
                "  fleet_id: Fleet to apply to; omit to use the first fleet (optional)\n"
                "  params: Behavior parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Flocking: gazebo_apply_swarm_behavior(behavior='flocking', fleet_id='fleet_1')\n"
                "- Coverage: gazebo_apply_swarm_behavior(behavior='coverage')\n"
                "- Leader-follower: gazebo_apply_swarm_behavior(behavior='leader_follower', params={'leader': 'robot_1'})"
            ),
            parameters={
                "properties": {
                    "behavior": {
                        "type": "string",
                        "description": "Swarm behavior to apply",
                        "enum": [
                            "flocking",
                            "coverage",
                            "formation_keeping",
                            "leader_follower",
                            "consensus",
                        ],
                    },
                    "fleet_id": {
                        "type": "string",
                        "description": "Fleet to apply behavior to; omit to use the first fleet",
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional behavior parameters dict",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["behavior"],
            },
            handler=multi_robot_tools.apply_swarm_behavior,
        ),
        MCPTool(
            name="gazebo_visualize_robot_network",
            description=(
                "Generate visualization markers for a multi-robot network.\n\n"
                "Visualization layers: comms_graph, task_allocation,\n"
                "formation_lines, collision_zones. Defaults to all four.\n"
                "RViz2 must be running to render the marker array.\n\n"
                "Args:\n"
                "  fleet_id: Fleet to visualize; omit to use the first fleet (optional)\n"
                "  show: Subset of visualization layers; omit for all (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- All layers: gazebo_visualize_robot_network(fleet_id='fleet_1')\n"
                "- Comms only: gazebo_visualize_robot_network(fleet_id='fleet_1', show=['comms_graph'])\n"
                "- Formation+zones: gazebo_visualize_robot_network(show=['formation_lines', 'collision_zones'])"
            ),
            parameters={
                "properties": {
                    "fleet_id": {
                        "type": "string",
                        "description": "Fleet to visualize; omit to use the first available fleet",
                    },
                    "show": {
                        "type": "array",
                        "description": "Subset of visualization layers; omit for all four",
                        "items": {
                            "type": "string",
                            "enum": [
                                "comms_graph",
                                "task_allocation",
                                "formation_lines",
                                "collision_zones",
                            ],
                        },
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
            handler=multi_robot_tools.visualize_robot_network,
        ),
        MCPTool(
            name="gazebo_enable_multi_robot_collision_avoidance",
            description=(
                "Enable or disable multi-robot collision avoidance for a fleet.\n\n"
                "Supported methods: dynamic, social_force, velocity_obstacles, priority.\n\n"
                "Args:\n"
                "  fleet_id: Fleet to configure; omit to use the first fleet (optional)\n"
                "  method: Avoidance method (default: 'velocity_obstacles')\n"
                "  enabled: Whether avoidance is enabled (default: True)\n"
                "  params: Method parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Default: gazebo_enable_multi_robot_collision_avoidance(fleet_id='fleet_1')\n"
                "- Priority: gazebo_enable_multi_robot_collision_avoidance(fleet_id='fleet_1', method='priority')\n"
                "- Disable: gazebo_enable_multi_robot_collision_avoidance(fleet_id='fleet_1', enabled=False)"
            ),
            parameters={
                "properties": {
                    "fleet_id": {
                        "type": "string",
                        "description": "Fleet to configure; omit to use the first available fleet",
                    },
                    "method": {
                        "type": "string",
                        "description": "Collision avoidance method (default: 'velocity_obstacles')",
                        "enum": ["dynamic", "social_force", "velocity_obstacles", "priority"],
                        "default": "velocity_obstacles",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether collision avoidance is enabled (default: true)",
                        "default": True,
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional method parameters dict",
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
            handler=multi_robot_tools.enable_multi_robot_collision_avoidance,
        ),
    ]
