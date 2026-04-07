"""
ROS2 Tools MCP Adapter.

Exposes ROS2 introspection and interaction tools as MCP tools:
- list_topics: Discover all active ROS2 topics
- get_topic_info: Get details about a specific topic
- publish_twist: Publish velocity commands to drive robots
- get_transform: Look up TF transforms between coordinate frames
- spawn_sdf: Spawn models from SDF/URDF XML strings
- get_joint_states: Read current joint positions and velocities
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import ros2_tools
from gazebo_mcp.tools import model_management
from gazebo_mcp.utils import OperationResult
from mcp.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for ROS2 introspection and interaction."""
    return [
        MCPTool(
            name="gazebo_list_topics",
            description=(
                "List all active ROS2 topics with their message types.\n\n"
                "This is the primary discovery tool -- call it first to understand\n"
                "what is happening in the simulation.\n\n"
                "Topics tell you what sensors are active, what command interfaces\n"
                "exist, and what data is flowing through the system.\n\n"
                "Args:\n"
                "  response_format: 'filtered' (default), 'summary', or 'concise'\n"
                "  filter_prefix: Only return topics starting with this prefix (optional)\n\n"
                "Examples:\n"
                "- List all: gazebo_list_topics()\n"
                "- Camera topics only: gazebo_list_topics(filter_prefix='/camera')\n"
                "- Summary: gazebo_list_topics(response_format='summary')"
            ),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'filtered' (default), 'summary', or 'concise'",
                        "enum": ["filtered", "summary", "concise"],
                        "default": "filtered",
                    },
                    "filter_prefix": {
                        "type": "string",
                        "description": "Only return topics starting with this prefix (e.g., '/camera')",
                    },
                },
                "required": [],
            },
            handler=ros2_tools.list_topics,
        ),
        MCPTool(
            name="gazebo_get_topic_info",
            description=(
                "Get detailed information about a specific ROS2 topic.\n\n"
                "Returns message type, publisher count, subscriber count,\n"
                "and publisher/subscriber node names.\n\n"
                "Args:\n"
                "  topic_name: Full topic name including leading '/' (required)\n\n"
                "Examples:\n"
                "- gazebo_get_topic_info('/scan')\n"
                "- gazebo_get_topic_info('/cmd_vel')\n"
                "- gazebo_get_topic_info('/camera/image_raw')"
            ),
            parameters={
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "Full ROS2 topic name (e.g., '/scan', '/cmd_vel')",
                    },
                },
                "required": ["topic_name"],
            },
            handler=ros2_tools.get_topic_info,
        ),
        MCPTool(
            name="gazebo_publish_twist",
            description=(
                "Publish a velocity command (Twist) to drive a robot.\n\n"
                "This is the primary tool for controlling robot movement.\n"
                "Most mobile robots listen on /cmd_vel for velocity commands.\n\n"
                "For differential-drive robots (e.g., TurtleBot3):\n"
                "- linear_x: forward/backward speed (m/s)\n"
                "- angular_z: turning speed (rad/s, positive = turn left)\n\n"
                "Args:\n"
                "  topic_name: Topic to publish to (default: '/cmd_vel')\n"
                "  linear_x: Forward velocity in m/s (default: 0.0)\n"
                "  linear_y: Lateral velocity in m/s (default: 0.0)\n"
                "  linear_z: Vertical velocity in m/s (default: 0.0)\n"
                "  angular_x: Roll rate in rad/s (default: 0.0)\n"
                "  angular_y: Pitch rate in rad/s (default: 0.0)\n"
                "  angular_z: Yaw rate in rad/s (default: 0.0)\n\n"
                "Examples:\n"
                "- Drive forward: gazebo_publish_twist(linear_x=0.5)\n"
                "- Turn left: gazebo_publish_twist(angular_z=0.5)\n"
                "- Drive in arc: gazebo_publish_twist(linear_x=0.3, angular_z=0.2)\n"
                "- Stop: gazebo_publish_twist()"
            ),
            parameters={
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "ROS2 topic to publish to (default: '/cmd_vel')",
                        "default": "/cmd_vel",
                    },
                    "linear_x": {
                        "type": "number",
                        "description": "Forward velocity (m/s). Positive = forward.",
                        "default": 0.0,
                    },
                    "linear_y": {
                        "type": "number",
                        "description": "Lateral velocity (m/s). Only for holonomic robots.",
                        "default": 0.0,
                    },
                    "linear_z": {
                        "type": "number",
                        "description": "Vertical velocity (m/s). Only for flying robots.",
                        "default": 0.0,
                    },
                    "angular_x": {
                        "type": "number",
                        "description": "Roll rate (rad/s).",
                        "default": 0.0,
                    },
                    "angular_y": {
                        "type": "number",
                        "description": "Pitch rate (rad/s).",
                        "default": 0.0,
                    },
                    "angular_z": {
                        "type": "number",
                        "description": "Yaw rate (rad/s). Positive = turn left (CCW).",
                        "default": 0.0,
                    },
                },
                "required": [],
            },
            handler=ros2_tools.publish_twist,
        ),
        MCPTool(
            name="gazebo_get_transform",
            description=(
                "Look up the TF transform between two coordinate frames.\n\n"
                "Returns translation (x,y,z) and rotation (quaternion + euler)\n"
                "describing the spatial relationship between frames.\n\n"
                "Common frame lookups:\n"
                "- 'map' -> 'base_link': Robot position in the map\n"
                "- 'odom' -> 'base_link': Odometry-based position\n"
                "- 'base_link' -> 'camera_link': Camera relative to robot\n"
                "- 'base_link' -> 'base_scan': Lidar relative to robot\n\n"
                "Args:\n"
                "  target_frame: Target coordinate frame (required)\n"
                "  source_frame: Source coordinate frame (required)\n"
                "  timeout: Lookup timeout in seconds (default: 1.0)\n\n"
                "Examples:\n"
                "- Robot in map: gazebo_get_transform('map', 'base_link')\n"
                "- Camera pose: gazebo_get_transform('base_link', 'camera_link')"
            ),
            parameters={
                "properties": {
                    "target_frame": {
                        "type": "string",
                        "description": "Target coordinate frame (e.g., 'map', 'odom')",
                    },
                    "source_frame": {
                        "type": "string",
                        "description": "Source coordinate frame (e.g., 'base_link')",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Lookup timeout in seconds (default: 1.0)",
                        "default": 1.0,
                        "minimum": 0.1,
                        "maximum": 30.0,
                    },
                },
                "required": ["target_frame", "source_frame"],
            },
            handler=ros2_tools.get_transform,
        ),
        MCPTool(
            name="gazebo_spawn_sdf",
            description=(
                "Spawn a model from SDF or URDF XML string.\n\n"
                "Unlike gazebo_spawn_model (simple geometry only), this tool accepts\n"
                "complete SDF/URDF XML for spawning complex models:\n"
                "- Robot models with joints, sensors, and plugins\n"
                "- Models with custom physics (inertia, friction)\n"
                "- Multi-link articulated objects\n"
                "- Models with attached sensors (camera, lidar, IMU)\n\n"
                "Args:\n"
                "  entity_name: Unique name for the entity (required)\n"
                "  sdf_xml: Complete SDF or URDF XML string (required)\n"
                "  x, y, z: Spawn position in meters (default: 0,0,0)\n"
                "  roll, pitch, yaw: Spawn orientation in radians (default: 0,0,0)\n\n"
                "Example:\n"
                "  gazebo_spawn_sdf(\n"
                "    entity_name='my_robot',\n"
                "    sdf_xml='<sdf version=\"1.6\"><model name=\"robot\">...</model></sdf>',\n"
                "    x=1.0, y=2.0, z=0.0\n"
                "  )"
            ),
            parameters={
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Unique name for the entity in the simulation",
                    },
                    "sdf_xml": {
                        "type": "string",
                        "description": "Complete SDF or URDF XML string",
                    },
                    "x": {
                        "type": "number",
                        "description": "Spawn X position in meters (default: 0.0)",
                        "default": 0.0,
                    },
                    "y": {
                        "type": "number",
                        "description": "Spawn Y position in meters (default: 0.0)",
                        "default": 0.0,
                    },
                    "z": {
                        "type": "number",
                        "description": "Spawn Z position in meters (default: 0.0)",
                        "default": 0.0,
                    },
                    "roll": {
                        "type": "number",
                        "description": "Spawn roll angle in radians (default: 0.0)",
                        "default": 0.0,
                    },
                    "pitch": {
                        "type": "number",
                        "description": "Spawn pitch angle in radians (default: 0.0)",
                        "default": 0.0,
                    },
                    "yaw": {
                        "type": "number",
                        "description": "Spawn yaw angle in radians (default: 0.0)",
                        "default": 0.0,
                    },
                },
                "required": ["entity_name", "sdf_xml"],
            },
            handler=model_management.spawn_sdf,
        ),
        MCPTool(
            name="gazebo_get_joint_states",
            description=(
                "Read current joint positions and velocities from a robot.\n\n"
                "Subscribes to the JointState topic (typically /joint_states) and\n"
                "returns the current state of all joints: position, velocity, effort.\n\n"
                "Args:\n"
                "  topic_name: JointState topic name (default: '/joint_states')\n"
                "  timeout: Subscription timeout in seconds (default: 2.0)\n\n"
                "Examples:\n"
                "- Default: gazebo_get_joint_states()\n"
                "- Specific robot: gazebo_get_joint_states('/my_robot/joint_states')"
            ),
            parameters={
                "properties": {
                    "topic_name": {
                        "type": "string",
                        "description": "JointState topic name (default: '/joint_states')",
                        "default": "/joint_states",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Subscription timeout in seconds (default: 2.0)",
                        "default": 2.0,
                        "minimum": 0.5,
                        "maximum": 30.0,
                    },
                },
                "required": [],
            },
            handler=ros2_tools.get_joint_states,
        ),
    ]
