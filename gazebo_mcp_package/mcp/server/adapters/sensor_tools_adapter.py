"""
Sensor Tools MCP Adapter.

Exposes Gazebo sensor data tools as MCP tools:
- list_sensors: List all sensors in simulation
- get_sensor_data: Get latest sensor readings
- subscribe_sensor_stream: Subscribe to sensor topic
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import sensor_tools
from mcp.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for sensor data operations."""
    return [
        MCPTool(
            name="gazebo_list_sensors",
            description=(
                "List all sensors in Gazebo simulation.\n\n"
                "Supports filtering by model name or sensor type.\n\n"
                "Supported types: camera, depth_camera, rgbd_camera, imu, lidar, "
                "ray, gps, contact, force_torque, magnetometer, altimeter, sonar\n\n"
                "Args:\n"
                "  model_name: Filter by model name (optional)\n"
                "  sensor_type: Filter by sensor type (optional)\n"
                "  response_format: 'filtered' (default) or 'summary'\n\n"
                "Examples:\n"
                "- List all: gazebo_list_sensors()\n"
                "- By model: gazebo_list_sensors(model_name='robot1')\n"
                "- By type: gazebo_list_sensors(sensor_type='camera')"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Filter by model name (optional)",
                    },
                    "sensor_type": {
                        "type": "string",
                        "description": "Filter by sensor type (optional)",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'filtered' or 'summary'",
                        "enum": ["filtered", "summary"],
                        "default": "filtered",
                    },
                },
                "required": [],
            },
            handler=sensor_tools.list_sensors,
        ),
        MCPTool(
            name="gazebo_get_sensor_data",
            description=(
                "Get latest data from a specific sensor.\n\n"
                "Returns data based on sensor type (lidar ranges, camera image info, "
                "IMU orientation/acceleration, GPS coordinates).\n\n"
                "Args:\n"
                "  sensor_name: Name of sensor to query (required)\n"
                "  timeout: Max wait time in seconds (default: 5.0)\n\n"
                "Examples:\n"
                "- gazebo_get_sensor_data('front_camera')\n"
                "- gazebo_get_sensor_data('lidar_sensor', timeout=10.0)"
            ),
            parameters={
                "properties": {
                    "sensor_name": {
                        "type": "string",
                        "description": "Name of sensor to query",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Max wait time for data in seconds (default: 5.0)",
                        "default": 5.0,
                        "minimum": 0.1,
                        "maximum": 60.0,
                    },
                },
                "required": ["sensor_name"],
            },
            handler=sensor_tools.get_sensor_data,
        ),
        MCPTool(
            name="gazebo_subscribe_sensor_stream",
            description=(
                "Subscribe to sensor data stream and cache latest data.\n\n"
                "After subscribing, use get_sensor_data() to retrieve cached data.\n\n"
                "Args:\n"
                "  sensor_name: Name of sensor to subscribe to (required)\n"
                "  topic_name: ROS2 topic name (required)\n"
                "  message_type: ROS2 message type (optional, auto-detected)\n\n"
                "Examples:\n"
                "- gazebo_subscribe_sensor_stream('camera1', '/camera/image_raw')\n"
                "- gazebo_subscribe_sensor_stream('lidar1', '/scan')"
            ),
            parameters={
                "properties": {
                    "sensor_name": {
                        "type": "string",
                        "description": "Name of sensor (for caching)",
                    },
                    "topic_name": {
                        "type": "string",
                        "description": "ROS2 topic name to subscribe to",
                    },
                    "message_type": {
                        "type": "string",
                        "description": "ROS2 message type (optional, auto-detected)",
                    },
                },
                "required": ["sensor_name", "topic_name"],
            },
            handler=sensor_tools.subscribe_sensor_stream,
        ),
    ]
