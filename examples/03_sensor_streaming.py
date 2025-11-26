#!/usr/bin/env python3
"""
Example 3: Sensor Data Streaming

This example demonstrates:
- Listing available sensors
- Filtering sensors by type
- Getting sensor data readings
- Subscribing to sensor streams
- Processing different sensor types (camera, lidar, IMU)

Prerequisites:
- None (works without ROS2/Gazebo, will use mock data)

Optional:
- ROS2 sourced for real sensor access
- Gazebo running with robots/sensors

Usage:
    python examples/03_sensor_streaming.py
"""

import sys
from pathlib import Path
import json
import time

# Add project to path:
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.server.server import GazeboMCPServer


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result: dict, indent: int = 0):
    """Pretty print MCP result."""
    spacing = "  " * indent

    # Extract content from MCP response:
    if "content" in result and result["content"]:
        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        if data["success"]:
            print(f"{spacing}✓ Success")
            if "data" in data and data["data"]:
                return data["data"]  # Return data for further processing
        else:
            print(f"{spacing}✗ Error: {data['error']}")
            if data.get("suggestions"):
                print(f"{spacing}Suggestions:")
                for suggestion in data["suggestions"]:
                    print(f"{spacing}  - {suggestion}")
    return None


def format_sensor_data(sensor_type: str, data: dict):
    """Format sensor data based on type."""
    if sensor_type == "camera":
        print("   Camera Data:")
        print(f"     Width: {data.get('width', 0)} px")
        print(f"     Height: {data.get('height', 0)} px")
        print(f"     Encoding: {data.get('encoding', 'N/A')}")
        print(f"     Frame ID: {data.get('frame_id', 'N/A')}")
        if "timestamp" in data:
            print(f"     Timestamp: {data['timestamp']}")

    elif sensor_type == "lidar" or sensor_type == "ray":
        print("   Lidar Data:")
        print(f"     Range Min: {data.get('range_min', 0):.2f} m")
        print(f"     Range Max: {data.get('range_max', 0):.2f} m")
        print(f"     Angle Min: {data.get('angle_min', 0):.3f} rad")
        print(f"     Angle Max: {data.get('angle_max', 0):.3f} rad")
        print(f"     Num Ranges: {len(data.get('ranges', []))}")
        if data.get('ranges'):
            ranges = data['ranges']
            print(f"     Sample Ranges (first 5): {ranges[:5]}")
            print(f"     Min Distance: {min(ranges):.2f} m")
            print(f"     Max Distance: {max(ranges):.2f} m")

    elif sensor_type == "imu":
        print("   IMU Data:")
        if "orientation" in data:
            ori = data["orientation"]
            print(f"     Orientation:")
            print(f"       x: {ori.get('x', 0):.3f}")
            print(f"       y: {ori.get('y', 0):.3f}")
            print(f"       z: {ori.get('z', 0):.3f}")
            print(f"       w: {ori.get('w', 1):.3f}")
        if "angular_velocity" in data:
            ang = data["angular_velocity"]
            print(f"     Angular Velocity:")
            print(f"       x: {ang.get('x', 0):.3f} rad/s")
            print(f"       y: {ang.get('y', 0):.3f} rad/s")
            print(f"       z: {ang.get('z', 0):.3f} rad/s")
        if "linear_acceleration" in data:
            acc = data["linear_acceleration"]
            print(f"     Linear Acceleration:")
            print(f"       x: {acc.get('x', 0):.3f} m/s²")
            print(f"       y: {acc.get('y', 0):.3f} m/s²")
            print(f"       z: {acc.get('z', 0):.3f} m/s²")

    elif sensor_type == "gps":
        print("   GPS Data:")
        print(f"     Latitude: {data.get('latitude', 0):.6f}°")
        print(f"     Longitude: {data.get('longitude', 0):.6f}°")
        print(f"     Altitude: {data.get('altitude', 0):.2f} m")

    elif sensor_type == "contact":
        print("   Contact Sensor Data:")
        print(f"     In Contact: {data.get('in_contact', False)}")
        if data.get('collision_count', 0) > 0:
            print(f"     Collision Count: {data['collision_count']}")

    else:
        print(f"   {sensor_type.upper()} Data:")
        print(json.dumps(data, indent=4))


def main():
    """Run sensor streaming example."""

    print_section("Gazebo MCP Server - Sensor Streaming Example")

    # Step 1: Create MCP server
    print("\n1. Creating MCP Server...")
    try:
        server = GazeboMCPServer()
        print("   ✓ Server created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create server: {e}")
        return

    # Step 2: List all sensors
    print_section("2. List All Sensors")
    print("\nQuerying all available sensors...")

    result = server.call_tool("gazebo_list_sensors", {
        "response_format": "summary"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        data = content["data"]
        print(f"   ✓ Found {data['total_sensors']} sensors")

        if data.get("sensor_types"):
            print("\n   Sensors by type:")
            for sensor_type, count in data["sensor_types"].items():
                print(f"     • {sensor_type}: {count}")

        if data.get("model_counts"):
            print("\n   Sensors by model:")
            for model_name, count in data["model_counts"].items():
                print(f"     • {model_name}: {count} sensors")
    else:
        print(f"   ✗ Failed to list sensors: {content['error']}")

    # Step 3: List sensors with filtering
    print_section("3. Filter Sensors by Type")
    print("\nFiltering for camera sensors...")

    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "camera",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        cameras = content["data"]["sensors"]
        print(f"   ✓ Found {len(cameras)} camera sensors:\n")

        for camera in cameras:
            print(f"   • {camera['name']}")
            print(f"     Model: {camera.get('model_name', 'N/A')}")
            print(f"     Topic: {camera.get('topic', 'N/A')}")
            print(f"     Update Rate: {camera.get('update_rate', 0)} Hz")
            print()
    else:
        print(f"   ✗ Filter failed: {content['error']}")

    print("\nFiltering for lidar sensors...")

    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "lidar",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        lidars = content["data"]["sensors"]
        print(f"   ✓ Found {len(lidars)} lidar sensors")
        for lidar in lidars:
            print(f"     • {lidar['name']} on {lidar.get('model_name', 'N/A')}")
    else:
        print(f"   ✗ Filter failed: {content['error']}")

    # Step 4: Get sensor data (camera)
    print_section("4. Get Camera Sensor Data")

    # Get camera list first to find a camera
    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "camera",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"] and content["data"]["sensors"]:
        camera_name = content["data"]["sensors"][0]["name"]
        print(f"\nQuerying data from '{camera_name}'...")

        result = server.call_tool("gazebo_get_sensor_data", {
            "sensor_name": camera_name,
            "timeout": 5.0
        })

        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            print("   ✓ Got camera data")
            format_sensor_data("camera", content["data"])
        else:
            print(f"   ✗ Query failed: {content['error']}")
    else:
        print("   ℹ No cameras available in simulation")

    # Step 5: Get sensor data (lidar)
    print_section("5. Get Lidar Sensor Data")

    # Get lidar list first
    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "lidar",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"] and content["data"]["sensors"]:
        lidar_name = content["data"]["sensors"][0]["name"]
        print(f"\nQuerying data from '{lidar_name}'...")

        result = server.call_tool("gazebo_get_sensor_data", {
            "sensor_name": lidar_name,
            "timeout": 5.0
        })

        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            print("   ✓ Got lidar data")
            format_sensor_data("lidar", content["data"])
        else:
            print(f"   ✗ Query failed: {content['error']}")
    else:
        print("   ℹ No lidars available in simulation")

    # Step 6: Get sensor data (IMU)
    print_section("6. Get IMU Sensor Data")

    # Get IMU list first
    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "imu",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"] and content["data"]["sensors"]:
        imu_name = content["data"]["sensors"][0]["name"]
        print(f"\nQuerying data from '{imu_name}'...")

        result = server.call_tool("gazebo_get_sensor_data", {
            "sensor_name": imu_name,
            "timeout": 5.0
        })

        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            print("   ✓ Got IMU data")
            format_sensor_data("imu", content["data"])
        else:
            print(f"   ✗ Query failed: {content['error']}")
    else:
        print("   ℹ No IMUs available in simulation")

    # Step 7: Subscribe to sensor stream
    print_section("7. Subscribe to Sensor Stream")
    print("""
Sensor streaming allows continuous data access:

1. **Subscribe to Topic**:
   - Call gazebo_subscribe_sensor_stream()
   - Specify sensor name and topic
   - Data cached automatically

2. **Read Latest Data**:
   - Call gazebo_get_sensor_data() repeatedly
   - Gets most recent cached reading
   - No need to re-subscribe

3. **Typical Workflow**:
   a) Subscribe to sensor stream
   b) Process data in loop
   c) Unsubscribe when done (automatic on disconnect)
    """)

    # Try to subscribe to a camera
    result = server.call_tool("gazebo_list_sensors", {
        "sensor_type": "camera",
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"] and content["data"]["sensors"]:
        camera = content["data"]["sensors"][0]
        camera_name = camera["name"]
        camera_topic = camera.get("topic", "/camera/image_raw")

        print(f"\nSubscribing to '{camera_name}' on topic '{camera_topic}'...")

        result = server.call_tool("gazebo_subscribe_sensor_stream", {
            "sensor_name": camera_name,
            "topic_name": camera_topic,
            "message_type": "auto"
        })

        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            print("   ✓ Subscribed successfully!")
            print(f"   Sensor: {content['data']['sensor_name']}")
            print(f"   Topic: {content['data']['topic']}")
            print(f"   Message Type: {content['data'].get('message_type', 'auto-detected')}")

            print("\n   Reading data from stream (simulated)...")
            for i in range(3):
                time.sleep(0.5)
                result = server.call_tool("gazebo_get_sensor_data", {
                    "sensor_name": camera_name
                })
                content = json.loads(result["content"][0]["text"])
                if content["success"]:
                    print(f"   Reading {i+1}: ✓ Got frame")
                else:
                    print(f"   Reading {i+1}: ✗ No data")
        else:
            print(f"   ✗ Subscribe failed: {content['error']}")
    else:
        print("   ℹ No cameras available for streaming")

    # Step 8: Sensor types reference
    print_section("8. Supported Sensor Types")
    print("""
The MCP server supports these sensor types:

1. **Vision Sensors**:
   • camera - RGB camera
   • depth_camera - Depth camera
   • rgbd_camera - RGB-D camera

2. **Range Sensors**:
   • lidar - 3D lidar scanner
   • ray - 2D laser scanner
   • sonar - Ultrasonic sensor

3. **Motion Sensors**:
   • imu - Inertial Measurement Unit
   • gps - Global Positioning System
   • altimeter - Altitude sensor
   • magnetometer - Magnetic field sensor

4. **Contact Sensors**:
   • contact - Collision detection
   • force_torque - Force/torque sensor

Each sensor type returns type-specific data:
- Cameras: image dimensions, encoding, frame ID
- Lidar: ranges, angles, intensities
- IMU: orientation, angular velocity, acceleration
- GPS: latitude, longitude, altitude
    """)

    # Step 9: Mock mode note
    content = json.loads(result["content"][0]["text"])
    if not content.get("data", {}).get("gazebo_connected", True):
        print_section("9. Working with Real Sensors")
        print("""
ℹ Note: Currently running in MOCK mode

To work with real sensors:

1. **Start Gazebo with a robot**:
   ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

2. **Or spawn a robot manually**:
   # Start empty Gazebo
   ros2 launch gazebo_ros gazebo.launch.py

   # Spawn TurtleBot3 with sensors
   ros2 run gazebo_ros spawn_entity.py -entity robot \\
       -file /path/to/turtlebot3.urdf \\
       -x 0 -y 0 -z 0.5

3. **Verify sensors**:
   ros2 topic list | grep -E "(camera|scan|imu)"

4. **Re-run this script** to access real sensor data
        """)

    # Summary
    print_section("Summary")
    print("""
This example demonstrated:
  ✓ Listing all sensors with summary format
  ✓ Filtering sensors by type
  ✓ Getting sensor data readings
  ✓ Subscribing to sensor streams
  ✓ Processing different sensor types

Sensor workflow:
  1. List available sensors (optionally filter by type)
  2. Get sensor data for one-time reading
  3. Subscribe to stream for continuous access
  4. Process type-specific data
  5. Unsubscribe when done (automatic)

Token efficiency:
  • Summary format: ~200 tokens
  • Filtered format: ~2,000 tokens (for 50 sensors)
  • Full details on request only

Next steps:
  • Run Example 4 for simulation control
  • Run Example 5 for complete workflow
  • Check examples/README.md for more examples

Note: This example works WITHOUT Gazebo running (mock mode).
      For real sensor data, start Gazebo with robots before running.
    """)

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
