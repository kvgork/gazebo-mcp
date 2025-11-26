"""
Sensor Tools MCP Adapter.

Exposes Gazebo sensor data tools as MCP tools:
- list_sensors: List all sensors in simulation
- get_sensor_data: Get latest sensor readings
- subscribe_sensor_stream: Subscribe to sensor topic

Supports sensor types:
- Camera (RGB, depth, RGBD)
- Lidar / Laser scanner
- IMU (orientation, angular velocity, linear acceleration)
- GPS
- Contact sensors
- Force/torque sensors
- And more...

Follows Anthropic best practices with ResultFilter pattern.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import sensor_tools


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
    Get MCP tools for sensor data operations.

    Returns:
        List of MCPTool instances
    """
    return [
        # List sensors tool:
        MCPTool(
            name="gazebo_list_sensors",
            description="""
List all sensors in Gazebo simulation.

Returns sensor data with ResultFilter pattern for token efficiency.
Filter by model name or sensor type to narrow results.

Supported sensor types:
- camera: RGB cameras
- depth_camera: Depth sensors
- rgbd_camera: RGB-D cameras
- imu: Inertial measurement units
- lidar: 3D lidar sensors
- ray: 2D laser scanners
- gps: GPS sensors
- contact: Contact/touch sensors
- force_torque: Force/torque sensors
- magnetometer: Magnetic field sensors
- altimeter: Altitude sensors
- sonar: Ultrasonic sensors

Args:
    model_name: Filter by model name (optional)
    sensor_type: Filter by sensor type (optional)
    response_format: 'filtered' (default) or 'summary' for counts only (optional)

Examples:
- List all sensors: gazebo_list_sensors()
- List robot's sensors: gazebo_list_sensors(model_name="robot1")
- List all cameras: gazebo_list_sensors(sensor_type="camera")
- Get summary: gazebo_list_sensors(response_format="summary")
            """.strip(),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Filter by model name (optional)"
                    },
                    "sensor_type": {
                        "type": "string",
                        "description": "Filter by sensor type (camera, lidar, imu, etc.) (optional)"
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response format: 'filtered' (data + examples) or 'summary' (counts)",
                        "enum": ["filtered", "summary"],
                        "default": "filtered"
                    }
                },
                "required": []
            },
            handler=sensor_tools.list_sensors
        ),

        # Get sensor data tool:
        MCPTool(
            name="gazebo_get_sensor_data",
            description="""
Get latest data from a specific sensor.

Args:
    sensor_name: Name of sensor to query (required)
    timeout: Maximum wait time for data in seconds (default: 5.0, optional)

Returns sensor data based on type:
- Camera: image_data, width, height, format
- Lidar: ranges, intensities, angle_min, angle_max
- IMU: orientation, angular_velocity, linear_acceleration
- GPS: latitude, longitude, altitude
- Contact: contacts (list of collision info)
- Force/Torque: force {x,y,z}, torque {x,y,z}

Examples:
- gazebo_get_sensor_data("front_camera")
- gazebo_get_sensor_data("lidar_sensor", timeout=10.0)
- gazebo_get_sensor_data("imu_link")
            """.strip(),
            parameters={
                "properties": {
                    "sensor_name": {
                        "type": "string",
                        "description": "Name of sensor to query"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Maximum wait time for data in seconds (default: 5.0)",
                        "default": 5.0,
                        "minimum": 0.1,
                        "maximum": 60.0
                    }
                },
                "required": ["sensor_name"]
            },
            handler=sensor_tools.get_sensor_data
        ),

        # Subscribe sensor stream tool:
        MCPTool(
            name="gazebo_subscribe_sensor_stream",
            description="""
Subscribe to sensor data stream and cache latest data.

Subscribes to a sensor's ROS2 topic and caches the latest message.
Use get_sensor_data() to retrieve cached data after subscribing.

Args:
    sensor_name: Name of sensor to subscribe to (required)
    topic_name: ROS2 topic name (required)
    message_type: ROS2 message type (optional, auto-detected from topic)
    buffer_size: Number of messages to buffer (default: 1, optional)

Returns subscription status.

Examples:
- gazebo_subscribe_sensor_stream("camera1", "/camera/image_raw")
- gazebo_subscribe_sensor_stream("lidar1", "/scan", message_type="sensor_msgs/msg/LaserScan")
- gazebo_subscribe_sensor_stream("imu1", "/imu/data", buffer_size=10)

Note: After subscribing, use get_sensor_data(sensor_name) to get latest cached data.
            """.strip(),
            parameters={
                "properties": {
                    "sensor_name": {
                        "type": "string",
                        "description": "Name of sensor (for caching)"
                    },
                    "topic_name": {
                        "type": "string",
                        "description": "ROS2 topic name to subscribe to"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "ROS2 message type (optional, auto-detected)"
                    },
                    "buffer_size": {
                        "type": "integer",
                        "description": "Number of messages to buffer (default: 1)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["sensor_name", "topic_name"]
            },
            handler=sensor_tools.subscribe_sensor_stream
        ),
    ]
