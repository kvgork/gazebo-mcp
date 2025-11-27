"""
Nav2 Navigation Tools MCP Adapter.

Exposes Nav2 navigation tools as MCP tools following Anthropic best practices:
- spawn_turtlebot3: Spawn TurtleBot3 with sensors
- send_nav2_goal: Send autonomous navigation goal
- get_navigation_status: Check navigation progress
- cancel_navigation: Stop navigation
- set_initial_pose: Initialize AMCL localization

These tools enable conversational robot navigation through Claude.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import navigation_tools
from gazebo_mcp.utils import OperationResult


@dataclass
class MCPTool:
    """MCP tool definition (imported from server.py context)."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: callable


def get_tools() -> List[MCPTool]:
    """
    Get MCP tools for Nav2 navigation.

    Returns list of 5 navigation tools with proper schemas.
    """
    return [
        # Tool 1: Spawn TurtleBot3
        MCPTool(
            name="spawn_turtlebot3",
            description="""Spawn TurtleBot3 robot with proper sensors and Nav2 configuration.

Spawns a fully-configured TurtleBot3 robot ready for autonomous navigation:
- Differential drive controller
- LiDAR sensor (360° laser scan)
- IMU sensor
- Odometry
- Compatible with Nav2 navigation stack

Variants:
- burger: Basic model with LDS-01 LiDAR (recommended for demos)
- waffle: Larger with Intel RealSense camera
- waffle_pi: With Raspberry Pi camera

Example usage:
  "Spawn a TurtleBot3 burger at the origin"
  "Create a TurtleBot3 waffle at position (2, 1, 0.01)"

Agent-friendly responses:
- Summary format by default
- Full configuration details available on request
""",
            parameters={
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique robot instance name (alphanumeric, max 64 chars)",
                        "default": "turtlebot3"
                    },
                    "variant": {
                        "type": "string",
                        "enum": ["burger", "waffle", "waffle_pi"],
                        "description": "TurtleBot3 variant to spawn",
                        "default": "burger"
                    },
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Spawn position [x, y, z] in meters",
                        "default": [0.0, 0.0, 0.01]
                    },
                    "orientation": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Spawn orientation [roll, pitch, yaw] in radians",
                        "default": [0.0, 0.0, 0.0]
                    },
                    "world": {
                        "type": "string",
                        "description": "Target Gazebo world name",
                        "default": "default"
                    }
                },
                "required": ["name"]
            },
            handler=navigation_tools.spawn_turtlebot3
        ),

        # Tool 2: Send Nav2 Goal
        MCPTool(
            name="send_nav2_goal",
            description="""Send autonomous navigation goal to Nav2 stack.

Commands robot to navigate autonomously to target position using Nav2:
- Path planning around obstacles
- Dynamic obstacle avoidance
- Recovery behaviors on failure
- Progress monitoring

The robot will drive itself using actual physics simulation (no teleportation).
Nav2 uses costmaps, planners, and controllers for safe navigation.

Example usage:
  "Navigate robot to position (5, 3)"
  "Go to waypoint (4, 2) with orientation 1.57 radians"
  "Send robot to goal (6, 2) and wait for completion"

Returns:
- Navigation status (succeeded/failed/in_progress)
- Elapsed time
- Distance traveled
- Final position accuracy

Agent tips:
- Use wait_for_result=True for synchronous operation
- Use wait_for_result=False to send goal and continue
- Check status with get_navigation_status
- Cancel anytime with cancel_navigation
""",
            parameters={
                "properties": {
                    "robot_name": {
                        "type": "string",
                        "description": "Name of robot to navigate (must be spawned first)"
                    },
                    "goal_position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "Target position [x, y] in meters (map frame)"
                    },
                    "goal_orientation": {
                        "type": "number",
                        "description": "Target yaw orientation in radians (0 = facing +X axis)",
                        "default": 0.0
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Maximum navigation time in seconds",
                        "default": 120.0,
                        "minimum": 10.0,
                        "maximum": 300.0
                    },
                    "wait_for_result": {
                        "type": "boolean",
                        "description": "If true, block until navigation completes; if false, return immediately",
                        "default": True
                    }
                },
                "required": ["robot_name", "goal_position"]
            },
            handler=navigation_tools.send_nav2_goal
        ),

        # Tool 3: Get Navigation Status
        MCPTool(
            name="get_navigation_status",
            description="""Get current navigation status and progress.

Returns real-time navigation information:
- Current state (idle/navigating/succeeded/failed/canceled)
- Robot position
- Goal position (if navigating)
- Remaining distance to goal
- Elapsed time
- Robot variant and configuration

Use this to:
- Check if navigation is complete
- Monitor progress during long navigations
- Debug navigation issues
- Verify robot is ready for commands

Example usage:
  "Where is the robot now?"
  "What's the navigation status?"
  "How far from the goal?"
  "Is the robot still moving?"

Returns comprehensive state even when idle.
""",
            parameters={
                "properties": {
                    "robot_name": {
                        "type": "string",
                        "description": "Name of robot to check status for"
                    }
                },
                "required": ["robot_name"]
            },
            handler=navigation_tools.get_navigation_status
        ),

        # Tool 4: Cancel Navigation
        MCPTool(
            name="cancel_navigation",
            description="""Cancel ongoing navigation and stop robot.

Immediately cancels active Nav2 navigation goal:
- Sends cancel request to action server
- Stops robot motion
- Updates state to canceled
- Clears goal handle

Use when:
- Navigation is taking too long
- Need to change destination
- Emergency stop required
- Robot appears stuck

Example usage:
  "Cancel navigation"
  "Stop the robot"
  "Abort current goal"

Safe to call even if no navigation is active.
Returns success with appropriate message in all cases.
""",
            parameters={
                "properties": {
                    "robot_name": {
                        "type": "string",
                        "description": "Name of robot to cancel navigation for"
                    }
                },
                "required": ["robot_name"]
            },
            handler=navigation_tools.cancel_navigation
        ),

        # Tool 5: Set Initial Pose
        MCPTool(
            name="set_initial_pose",
            description="""Set initial pose for AMCL localization.

Initializes robot's estimated position in AMCL (Adaptive Monte Carlo Localization):
- Publishes to /initialpose topic
- Seeds particle filter with starting pose
- Required before first navigation with AMCL
- Improves localization accuracy

When to use:
- After spawning robot (before first navigation)
- When robot loses localization
- To reset localization after moving robot manually
- Known starting position in map

Example usage:
  "Set initial pose at origin"
  "Initialize robot position at (2, 1)"
  "Set starting pose at (0, 0) facing forward"

Note: Only needed if using AMCL for localization.
If using only odometry or ground truth, this is optional.
""",
            parameters={
                "properties": {
                    "robot_name": {
                        "type": "string",
                        "description": "Name of robot to initialize"
                    },
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "Initial position [x, y] in meters (map frame)"
                    },
                    "orientation": {
                        "type": "number",
                        "description": "Initial yaw orientation in radians",
                        "default": 0.0
                    }
                },
                "required": ["robot_name", "position"]
            },
            handler=navigation_tools.set_initial_pose
        ),
    ]


def get_tool_names() -> List[str]:
    """Get list of tool names for registration."""
    return [
        "spawn_turtlebot3",
        "send_nav2_goal",
        "get_navigation_status",
        "cancel_navigation",
        "set_initial_pose",
    ]


def get_tool_count() -> int:
    """Get number of navigation tools available."""
    return 5


# Module metadata
__all__ = ["get_tools", "get_tool_names", "get_tool_count"]
