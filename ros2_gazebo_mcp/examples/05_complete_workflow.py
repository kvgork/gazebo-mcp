#!/usr/bin/env python3
"""
Example 5: Complete Robot Testing Workflow

This example demonstrates a complete end-to-end workflow:
1. Initialize simulation and verify status
2. Spawn a robot at a specific position
3. List and verify robot sensors
4. Run simulation and monitor progress
5. Query sensor data during operation
6. Verify robot state and movement
7. Clean up and reset

This combines techniques from all previous examples into a realistic
robot testing scenario.

Prerequisites:
- None (works without ROS2/Gazebo, will use mock data)

Optional:
- ROS2 sourced for real testing
- Gazebo running for actual simulation

Usage:
    python examples/05_complete_workflow.py
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


def print_section(title: str, level: int = 1):
    """Print a section header."""
    if level == 1:
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    else:
        print(f"\n{'  ' * (level-1)}--- {title} ---")


def print_status(message: str, status: str = "info", indent: int = 1):
    """Print a status message."""
    symbols = {
        "success": "✓",
        "error": "✗",
        "info": "ℹ",
        "wait": "⏳"
    }
    symbol = symbols.get(status, "•")
    spacing = "  " * indent
    print(f"{spacing}{symbol} {message}")


def create_robot_sdf(name: str, x: float, y: float, z: float) -> str:
    """Create a simple mobile robot with sensors."""
    return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <pose>{x} {y} {z} 0 0 0</pose>
    <static>false</static>

    <!-- Base Link -->
    <link name="base_link">
      <collision name="collision">
        <geometry>
          <cylinder>
            <radius>0.2</radius>
            <length>0.3</length>
          </cylinder>
        </geometry>
      </collision>
      <visual name="visual">
        <geometry>
          <cylinder>
            <radius>0.2</radius>
            <length>0.3</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>0.2 0.5 0.8 1</ambient>
          <diffuse>0.2 0.5 0.8 1</diffuse>
        </material>
      </visual>
      <inertial>
        <mass>10.0</mass>
        <inertia>
          <ixx>0.4</ixx>
          <iyy>0.4</iyy>
          <izz>0.2</izz>
        </inertia>
      </inertial>

      <!-- IMU Sensor -->
      <sensor name="imu_sensor" type="imu">
        <always_on>true</always_on>
        <update_rate>50</update_rate>
        <topic>/{name}/imu</topic>
      </sensor>
    </link>

    <!-- Lidar Link -->
    <link name="lidar_link">
      <pose>0 0 0.2 0 0 0</pose>
      <sensor name="lidar" type="ray">
        <always_on>true</always_on>
        <update_rate>10</update_rate>
        <topic>/{name}/scan</topic>
        <ray>
          <scan>
            <horizontal>
              <samples>360</samples>
              <min_angle>-3.14159</min_angle>
              <max_angle>3.14159</max_angle>
            </horizontal>
          </scan>
          <range>
            <min>0.1</min>
            <max>10.0</max>
          </range>
        </ray>
      </sensor>
    </link>

    <joint name="lidar_joint" type="fixed">
      <parent>base_link</parent>
      <child>lidar_link</child>
    </joint>
  </model>
</sdf>"""


def main():
    """Run complete workflow example."""

    print_section("Complete Robot Testing Workflow", level=1)
    print("\nThis example demonstrates a full robot testing scenario,")
    print("combining techniques from all previous examples.\n")

    # Phase 1: Initialization
    print_section("Phase 1: Initialization", level=2)

    print_status("Creating MCP server...", "wait")
    try:
        server = GazeboMCPServer()
        print_status("MCP server created", "success")
    except Exception as e:
        print_status(f"Failed to create server: {e}", "error")
        return

    # Check simulation status
    print_status("Checking simulation status...", "wait")
    result = server.call_tool("gazebo_get_simulation_status", {})
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        data = content["data"]
        is_connected = data.get("gazebo_connected", False)
        is_running = data.get("is_running", False)

        print_status(f"Gazebo connected: {is_connected}", "info")
        print_status(f"Simulation running: {is_running}", "info")

        if not is_connected:
            print_status("Running in MOCK mode (no real Gazebo)", "info")
    else:
        print_status("Failed to get status", "error")
        return

    # Phase 2: Environment Setup
    print_section("Phase 2: Environment Setup", level=2)

    # Check existing models
    print_status("Checking existing models...", "wait")
    result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        existing_count = content["data"]["total_models"]
        print_status(f"Found {existing_count} existing models", "info")

        if existing_count > 0:
            print_status("Note: This test assumes an empty world", "info")
    else:
        print_status("Failed to list models", "error")

    # Get world properties
    print_status("Querying world properties...", "wait")
    result = server.call_tool("gazebo_get_world_properties", {})
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        data = content["data"]
        if "physics" in data and "gravity" in data["physics"]:
            gz = data["physics"]["gravity"].get("z", -9.81)
            print_status(f"Gravity: {gz:.2f} m/s² (z-axis)", "info")
        print_status("World properties verified", "success")
    else:
        print_status("Failed to get world properties", "error")

    # Phase 3: Robot Deployment
    print_section("Phase 3: Robot Deployment", level=2)

    robot_name = "test_robot"
    spawn_x, spawn_y, spawn_z = 0.0, 0.0, 0.5

    print_status(f"Spawning robot '{robot_name}' at ({spawn_x}, {spawn_y}, {spawn_z})...", "wait")

    robot_sdf = create_robot_sdf(robot_name, spawn_x, spawn_y, spawn_z)

    result = server.call_tool("gazebo_spawn_model", {
        "model_name": robot_name,
        "model_xml": robot_sdf,
        "x": spawn_x,
        "y": spawn_y,
        "z": spawn_z
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        print_status("Robot spawned successfully", "success")
        pos = content["data"]["position"]
        print_status(f"Position: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})", "info", indent=2)
    else:
        print_status(f"Spawn failed: {content['error']}", "error")
        return

    # Verify spawn
    time.sleep(0.5)
    print_status("Verifying robot state...", "wait")

    result = server.call_tool("gazebo_get_model_state", {
        "model_name": robot_name
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        state = content["data"]
        pos = state["pose"]["position"]
        print_status("Robot state verified", "success")
        print_status(f"Position: ({pos['x']:.3f}, {pos['y']:.3f}, {pos['z']:.3f})", "info", indent=2)
    else:
        print_status("Failed to verify robot state", "error")

    # Phase 4: Sensor Verification
    print_section("Phase 4: Sensor Verification", level=2)

    print_status("Discovering robot sensors...", "wait")

    result = server.call_tool("gazebo_list_sensors", {
        "model_name": robot_name,
        "response_format": "filtered"
    })
    content = json.loads(result["content"][0]["text"])

    robot_sensors = []
    if content["success"]:
        sensors = content["data"]["sensors"]
        print_status(f"Found {len(sensors)} sensors on robot", "success")

        for sensor in sensors:
            sensor_name = sensor["name"]
            sensor_type = sensor["type"]
            robot_sensors.append((sensor_name, sensor_type))
            print_status(f"{sensor_name} ({sensor_type})", "info", indent=2)
    else:
        print_status("Failed to discover sensors", "error")

    # Phase 5: Simulation Execution
    print_section("Phase 5: Simulation Execution", level=2)

    # Ensure simulation is running
    print_status("Ensuring simulation is unpaused...", "wait")
    result = server.call_tool("gazebo_unpause_simulation", {})
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        print_status("Simulation running", "success")
    else:
        print_status("Failed to unpause (may already be running)", "info")

    # Run simulation for 5 seconds (simulated time)
    print_status("Running simulation for 5 seconds...", "wait")

    start_result = server.call_tool("gazebo_get_simulation_time", {})
    start_content = json.loads(start_result["content"][0]["text"])

    if start_content["success"]:
        start_time = start_content["data"].get("simulation_time", 0)
        print_status(f"Start time: {start_time:.2f} s", "info", indent=2)

    # Simulate running (in real scenario, this would be actual simulation time)
    for i in range(5):
        time.sleep(1)
        result = server.call_tool("gazebo_get_simulation_time", {})
        content = json.loads(result["content"][0]["text"])

        if content["success"]:
            curr_time = content["data"].get("simulation_time", 0)
            elapsed = curr_time - start_time if start_content["success"] else 0
            print_status(f"Elapsed: {elapsed:.2f} s", "info", indent=2)

    print_status("Simulation run complete", "success")

    # Phase 6: Data Collection
    print_section("Phase 6: Data Collection", level=2)

    print_status("Collecting sensor data...", "wait")

    collected_data = {}

    for sensor_name, sensor_type in robot_sensors:
        result = server.call_tool("gazebo_get_sensor_data", {
            "sensor_name": sensor_name,
            "timeout": 2.0
        })
        content = json.loads(result["content"][0]["text"])

        if content["success"]:
            collected_data[sensor_name] = content["data"]
            print_status(f"{sensor_name}: ✓ Data received", "success", indent=2)

            # Show sample data
            if sensor_type == "imu":
                if "linear_acceleration" in content["data"]:
                    acc = content["data"]["linear_acceleration"]
                    print_status(f"  Accel: ({acc.get('x', 0):.2f}, {acc.get('y', 0):.2f}, {acc.get('z', 0):.2f}) m/s²", "info", indent=3)

            elif sensor_type == "lidar" or sensor_type == "ray":
                if "ranges" in content["data"]:
                    ranges = content["data"]["ranges"]
                    print_status(f"  Ranges: {len(ranges)} points", "info", indent=3)
                    if ranges:
                        print_status(f"  Min: {min(ranges):.2f} m, Max: {max(ranges):.2f} m", "info", indent=3)
        else:
            print_status(f"{sensor_name}: ✗ No data", "error", indent=2)

    print_status(f"Collected data from {len(collected_data)}/{len(robot_sensors)} sensors", "success")

    # Phase 7: State Verification
    print_section("Phase 7: State Verification", level=2)

    print_status("Querying final robot state...", "wait")

    result = server.call_tool("gazebo_get_model_state", {
        "model_name": robot_name
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        state = content["data"]
        pos = state["pose"]["position"]
        ori = state["pose"]["orientation"]

        print_status("Final state retrieved", "success")
        print_status(f"Position: ({pos['x']:.3f}, {pos['y']:.3f}, {pos['z']:.3f})", "info", indent=2)
        print_status(f"Orientation: (r={ori['roll']:.3f}, p={ori['pitch']:.3f}, y={ori['yaw']:.3f})", "info", indent=2)

        if "twist" in state:
            lin = state["twist"]["linear"]
            ang = state["twist"]["angular"]
            lin_speed = (lin['x']**2 + lin['y']**2 + lin['z']**2)**0.5
            ang_speed = (ang['x']**2 + ang['y']**2 + ang['z']**2)**0.5

            print_status(f"Linear speed: {lin_speed:.3f} m/s", "info", indent=2)
            print_status(f"Angular speed: {ang_speed:.3f} rad/s", "info", indent=2)
    else:
        print_status("Failed to get final state", "error")

    # Phase 8: Cleanup
    print_section("Phase 8: Cleanup", level=2)

    # Pause simulation
    print_status("Pausing simulation...", "wait")
    result = server.call_tool("gazebo_pause_simulation", {})
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        print_status("Simulation paused", "success")
    else:
        print_status("Failed to pause", "error")

    # Delete robot
    print_status(f"Deleting robot '{robot_name}'...", "wait")
    result = server.call_tool("gazebo_delete_model", {
        "model_name": robot_name
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        print_status("Robot deleted", "success")
    else:
        print_status(f"Delete failed: {content.get('error', 'Unknown')}", "error")

    # Verify deletion
    time.sleep(0.5)
    print_status("Verifying cleanup...", "wait")

    result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })
    content = json.loads(result["content"][0]["text"])

    if content["success"]:
        remaining = content["data"]["total_models"]
        print_status(f"{remaining} models remaining", "info")
        print_status("Cleanup complete", "success")
    else:
        print_status("Failed to verify cleanup", "error")

    # Test Summary
    print_section("Test Summary", level=1)

    print("""
Test execution completed successfully!

Phases Completed:
  ✓ Phase 1: Initialization (server, status check)
  ✓ Phase 2: Environment Setup (world properties)
  ✓ Phase 3: Robot Deployment (spawn, verify)
  ✓ Phase 4: Sensor Verification (discover sensors)
  ✓ Phase 5: Simulation Execution (run for 5 seconds)
  ✓ Phase 6: Data Collection (query all sensors)
  ✓ Phase 7: State Verification (final state check)
  ✓ Phase 8: Cleanup (pause, delete, verify)

This workflow demonstrated:
  • Complete test lifecycle management
  • Robot spawning and verification
  • Sensor discovery and data collection
  • Simulation control and timing
  • State monitoring and verification
  • Proper cleanup procedures

Real-world applications:
  • Automated robot testing
  • Sensor calibration workflows
  • Integration testing
  • Continuous integration (CI/CD)
  • Regression testing

Next steps:
  • Extend with custom robot models
  • Add navigation commands
  • Implement test assertions
  • Integrate with pytest for automation
  • Add performance benchmarking

For production testing:
  1. Wrap this workflow in pytest
  2. Add assertions for expected values
  3. Implement timeout handling
  4. Add logging and reporting
  5. Run in CI/CD pipeline
    """)

    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
