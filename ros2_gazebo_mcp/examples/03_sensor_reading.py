#!/usr/bin/env python3
"""
Example 3: Reading Sensor Data

Demonstrates:
- Listing available sensors on a robot
- Reading camera data (RGB images)
- Reading LiDAR scan data
- Reading IMU data (accelerometer, gyroscope)
- Understanding sensor data formats

Prerequisites:
- TurtleBot3 model spawned (or uses mock data)
- Optional: Gazebo running with sensors active

Usage:
    # With Gazebo and TurtleBot3:
    gz sim &
    # (spawn TurtleBot3 from Example 2)
    python3 examples/03_sensor_reading.py

    # Without Gazebo (mock mode):
    python3 examples/03_sensor_reading.py
"""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import sensor_tools, model_management


def main():
    """Run sensor reading example."""

    print("=" * 60)
    print("Example 3: Reading Sensor Data")
    print("=" * 60)
    print()

    robot_name = "my_turtlebot3"

    # Step 1: Spawn robot (if not already present)
    print("Step 1: Ensuring robot is spawned...")
    result = model_management.spawn_model(
        model_name=robot_name,
        model_type="turtlebot3_burger",  # Has LiDAR sensor
        x=0.0, y=0.0, z=0.01
    )
    if result.success:
        print(f"✓ Robot '{robot_name}' ready")
    else:
        print(f"  Note: {result.error}")

    print()

    # Step 2: List available sensors
    print("Step 2: Listing sensors on robot...")
    result = sensor_tools.list_sensors(
        model_name=robot_name,
        response_format="summary"
    )

    if result.success and result.data:
        sensors = result.data.get('sensors', [])
        print(f"✓ Found {len(sensors)} sensor(s)")
        for sensor in sensors:
            print(f"  - {sensor.get('name', 'unknown')}: {sensor.get('type', 'unknown')}")
            print(f"    Topic: {sensor.get('topic', 'N/A')}")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 3: Read LiDAR data
    print("Step 3: Reading LiDAR sensor data...")
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="lidar",
        timeout=2.0
    )

    if result.success and result.data:
        print(f"✓ LiDAR data retrieved")
        sensor_data = result.data.get('sensor_data', {})
        print(f"  - Type: {sensor_data.get('type', 'unknown')}")
        print(f"  - Range min: {sensor_data.get('range_min', 0):.2f} m")
        print(f"  - Range max: {sensor_data.get('range_max', 0):.2f} m")

        ranges = sensor_data.get('ranges', [])
        if ranges:
            print(f"  - Number of readings: {len(ranges)}")
            print(f"  - Sample readings: {ranges[:5]}")
            print(f"  - Min distance: {min(ranges):.2f} m")
            print(f"  - Max distance: {max(ranges):.2f} m")

        if sensor_data.get('mock_data'):
            print(f"  - Mode: MOCK (simulated data)")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 4: Read camera data
    print("Step 4: Reading camera sensor data...")
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="camera",
        timeout=2.0
    )

    if result.success and result.data:
        print(f"✓ Camera data retrieved")
        sensor_data = result.data.get('sensor_data', {})
        print(f"  - Type: {sensor_data.get('type', 'unknown')}")
        print(f"  - Width: {sensor_data.get('width', 0)} pixels")
        print(f"  - Height: {sensor_data.get('height', 0)} pixels")
        print(f"  - Encoding: {sensor_data.get('encoding', 'unknown')}")

        data_size = len(sensor_data.get('data', b''))
        if data_size > 0:
            print(f"  - Image data size: {data_size / 1024:.1f} KB")
    else:
        print(f"  Note: Camera not available ({result.error})")

    print()

    # Step 5: Read IMU data
    print("Step 5: Reading IMU sensor data...")
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="imu",
        timeout=2.0
    )

    if result.success and result.data:
        print(f"✓ IMU data retrieved")
        sensor_data = result.data.get('sensor_data', {})

        orientation = sensor_data.get('orientation', {})
        angular_vel = sensor_data.get('angular_velocity', {})
        linear_accel = sensor_data.get('linear_acceleration', {})

        print(f"  - Orientation:")
        print(f"    Roll: {orientation.get('roll', 0):.3f} rad")
        print(f"    Pitch: {orientation.get('pitch', 0):.3f} rad")
        print(f"    Yaw: {orientation.get('yaw', 0):.3f} rad")

        print(f"  - Angular velocity:")
        print(f"    X: {angular_vel.get('x', 0):.3f} rad/s")
        print(f"    Y: {angular_vel.get('y', 0):.3f} rad/s")
        print(f"    Z: {angular_vel.get('z', 0):.3f} rad/s")

        print(f"  - Linear acceleration:")
        print(f"    X: {linear_accel.get('x', 0):.3f} m/s²")
        print(f"    Y: {linear_accel.get('y', 0):.3f} m/s²")
        print(f"    Z: {linear_accel.get('z', 0):.3f} m/s²")
    else:
        print(f"  Note: IMU not available ({result.error})")

    print()

    # Step 6: Clean up
    print("Step 6: Cleaning up...")
    result = model_management.delete_model(model_name=robot_name)
    if result.success:
        print(f"✓ Robot deleted")

    print()
    print("=" * 60)
    print("Example completed!")
    print()
    print("What you learned:")
    print("  - How to discover available sensors")
    print("  - Reading LiDAR scan data")
    print("  - Reading camera images")
    print("  - Reading IMU data (orientation, velocity, acceleration)")
    print()
    print("Sensor data formats:")
    print("  - LiDAR: ranges array, angle_min/max, range_min/max")
    print("  - Camera: width, height, encoding, binary data")
    print("  - IMU: orientation (RPY), angular_vel, linear_accel")
    print()
    print("Next steps:")
    print("  - Try Example 4: World manipulation")
    print("  - Process sensor data for obstacle detection")
    print("  - Combine sensors for SLAM or navigation")
    print("=" * 60)


if __name__ == "__main__":
    main()
