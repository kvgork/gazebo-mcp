#!/usr/bin/env python3
"""
Example 2: Spawn and Control Models

This example demonstrates:
- Spawning a simple box model from SDF
- Querying model state (position, orientation)
- Understanding model control options
- Deleting models from simulation

Prerequisites:
- None (works without ROS2/Gazebo, will use mock data)

Optional:
- ROS2 sourced for real spawning
- Gazebo running for actual simulation

Usage:
    python examples/02_spawn_and_control.py
"""

import sys
from pathlib import Path
import json

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
                print(f"{spacing}Data:")
                print(json.dumps(data["data"], indent=2))
        else:
            print(f"{spacing}✗ Error: {data['error']}")
            if data.get("suggestions"):
                print(f"{spacing}Suggestions:")
                for suggestion in data["suggestions"]:
                    print(f"{spacing}  - {suggestion}")
    else:
        print(json.dumps(result, indent=2))


def create_box_sdf(name: str, x: float, y: float, z: float) -> str:
    """Create a simple box model in SDF format."""
    return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <pose>{x} {y} {z} 0 0 0</pose>
    <static>false</static>
    <link name="link">
      <collision name="collision">
        <geometry>
          <box>
            <size>0.5 0.5 0.5</size>
          </box>
        </geometry>
      </collision>
      <visual name="visual">
        <geometry>
          <box>
            <size>0.5 0.5 0.5</size>
          </box>
        </geometry>
        <material>
          <ambient>1 0 0 1</ambient>
          <diffuse>1 0 0 1</diffuse>
        </material>
      </visual>
      <inertial>
        <mass>1.0</mass>
        <inertia>
          <ixx>0.0417</ixx>
          <iyy>0.0417</iyy>
          <izz>0.0417</izz>
        </inertia>
      </inertial>
    </link>
  </model>
</sdf>"""


def main():
    """Run spawn and control example."""

    print_section("Gazebo MCP Server - Spawn and Control Example")

    # Step 1: Create MCP server
    print("\n1. Creating MCP Server...")
    try:
        server = GazeboMCPServer()
        print("   ✓ Server created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create server: {e}")
        return

    # Step 2: List existing models
    print_section("2. Check Existing Models")
    print("\nListing current models...")
    result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        model_count = content["data"]["total_models"]
        print(f"   ✓ Found {model_count} existing models")
        if content["data"].get("model_names"):
            print("   Current models:")
            for model_name in content["data"]["model_names"]:
                print(f"     • {model_name}")
    else:
        print(f"   ✗ Failed to list models: {content['error']}")

    # Step 3: Spawn a box
    print_section("3. Spawn a Red Box")
    print("\nCreating box model at position (2.0, 1.0, 0.5)...")

    box_sdf = create_box_sdf("red_box", 2.0, 1.0, 0.5)

    result = server.call_tool("gazebo_spawn_model", {
        "model_name": "red_box",
        "model_xml": box_sdf,
        "x": 2.0,
        "y": 1.0,
        "z": 0.5
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        print("   ✓ Box spawned successfully!")
        print(f"   Model name: {content['data']['model_name']}")
        pos = content["data"]["position"]
        print(f"   Position: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})")
    else:
        print(f"   ✗ Spawn failed: {content['error']}")
        if not content["data"].get("gazebo_connected"):
            print("\n   ℹ Note: Gazebo not connected (MOCK mode)")
            print("   The spawn was simulated. To spawn in real Gazebo:")
            print("     1. Source ROS2: source /opt/ros/humble/setup.bash")
            print("     2. Start Gazebo: ros2 launch gazebo_ros gazebo.launch.py")
            print("     3. Re-run this script")

    # Step 4: Query model state
    print_section("4. Query Model State")
    print("\nQuerying state of 'red_box'...")

    result = server.call_tool("gazebo_get_model_state", {
        "model_name": "red_box"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        print("   ✓ Got model state")
        state = content["data"]

        # Position
        pos = state["pose"]["position"]
        print(f"\n   Position:")
        print(f"     x: {pos['x']:.3f}")
        print(f"     y: {pos['y']:.3f}")
        print(f"     z: {pos['z']:.3f}")

        # Orientation
        ori = state["pose"]["orientation"]
        print(f"\n   Orientation (Euler):")
        print(f"     roll:  {ori['roll']:.3f} rad")
        print(f"     pitch: {ori['pitch']:.3f} rad")
        print(f"     yaw:   {ori['yaw']:.3f} rad")

        # Velocity
        if "twist" in state:
            lin = state["twist"]["linear"]
            ang = state["twist"]["angular"]
            print(f"\n   Linear Velocity:")
            print(f"     vx: {lin['x']:.3f} m/s")
            print(f"     vy: {lin['y']:.3f} m/s")
            print(f"     vz: {lin['z']:.3f} m/s")
            print(f"\n   Angular Velocity:")
            print(f"     wx: {ang['x']:.3f} rad/s")
            print(f"     wy: {ang['y']:.3f} rad/s")
            print(f"     wz: {ang['z']:.3f} rad/s")
    else:
        print(f"   ✗ Query failed: {content['error']}")

    # Step 5: Model control information
    print_section("5. Model Control")
    print("""
Model control options in Gazebo:

1. **Apply Forces** (via ROS2 topics):
   - Publish to /red_box/cmd_vel for velocity commands
   - Use gazebo_ros_force plugin for force/torque

2. **Set State Directly** (future):
   - Use gazebo_set_model_state() when implemented
   - Teleport model to new position/orientation
   - Set velocity directly

3. **Physics Interaction**:
   - Models respond to gravity, collisions
   - Use joints for controlled movement
   - Apply impulses for one-time forces

Current implementation provides:
✓ Spawn models at specific positions
✓ Query current state (pose, velocity)
✗ Set state (planned for Phase 4, Module 4.1)
    """)

    # Step 6: Spawn another box
    print_section("6. Spawn Another Model")
    print("\nSpawning blue box at (0.0, 0.0, 1.0)...")

    blue_box_sdf = create_box_sdf("blue_box", 0.0, 0.0, 1.0)
    blue_box_sdf = blue_box_sdf.replace(
        "<ambient>1 0 0 1</ambient>",
        "<ambient>0 0 1 1</ambient>"
    ).replace(
        "<diffuse>1 0 0 1</diffuse>",
        "<diffuse>0 0 1 1</diffuse>"
    )

    result = server.call_tool("gazebo_spawn_model", {
        "model_name": "blue_box",
        "model_xml": blue_box_sdf,
        "x": 0.0,
        "y": 0.0,
        "z": 1.0
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        print("   ✓ Blue box spawned successfully!")
    else:
        print(f"   ✗ Spawn failed: {content['error']}")

    # Step 7: List all models
    print_section("7. List All Models")
    print("\nListing all models in simulation...")

    result = server.call_tool("gazebo_list_models", {
        "response_format": "filtered"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        models = content["data"]["models"]
        print(f"   ✓ Found {len(models)} models:\n")

        for i, model in enumerate(models, 1):
            print(f"   {i}. {model['name']}")
            pos = model["position"]
            print(f"      Position: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})")
    else:
        print(f"   ✗ List failed: {content['error']}")

    # Step 8: Delete red box
    print_section("8. Delete Model")
    print("\nDeleting 'red_box'...")

    result = server.call_tool("gazebo_delete_model", {
        "model_name": "red_box"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        print("   ✓ Model deleted successfully!")
        print(f"   Deleted: {content['data']['model_name']}")
    else:
        print(f"   ✗ Delete failed: {content['error']}")

    # Step 9: Verify deletion
    print_section("9. Verify Deletion")
    print("\nListing models after deletion...")

    result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        remaining = content["data"]["total_models"]
        print(f"   ✓ {remaining} models remaining")
        if content["data"].get("model_names"):
            print("   Remaining models:")
            for model_name in content["data"]["model_names"]:
                print(f"     • {model_name}")
    else:
        print(f"   ✗ List failed: {content['error']}")

    # Step 10: Cleanup
    print_section("10. Cleanup")
    print("\nDeleting 'blue_box'...")

    result = server.call_tool("gazebo_delete_model", {
        "model_name": "blue_box"
    })

    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        print("   ✓ Cleanup complete!")
    else:
        print(f"   ✗ Cleanup failed: {content['error']}")

    # Summary
    print_section("Summary")
    print("""
This example demonstrated:
  ✓ Spawning models from SDF XML strings
  ✓ Querying model state (pose and velocity)
  ✓ Listing models with different formats
  ✓ Deleting models from simulation
  ✓ Model lifecycle management

Model control workflow:
  1. Create model description (SDF/URDF)
  2. Spawn at desired position
  3. Query state to verify
  4. Control via ROS2 topics or physics
  5. Delete when done

Next steps:
  • Run Example 3 to stream sensor data
  • Run Example 4 for simulation control
  • Check examples/README.md for more examples

Note: This example works WITHOUT Gazebo running (mock mode).
      For real spawning, start Gazebo before running the script.
    """)

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
