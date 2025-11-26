#!/usr/bin/env python3
"""
Example 2: TurtleBot3 Spawn and Control

Demonstrates:
- Spawning a TurtleBot3 robot model
- Getting the robot's state (position, orientation)
- Setting the robot's state (moving it)
- Deleting a model

Prerequisites:
- TurtleBot3 model files (included with ros-humble-turtlebot3-gazebo)
- Optional: Gazebo running for real testing

Usage:
    # With Gazebo (real mode):
    gz sim &
    source /opt/ros/humble/setup.bash
    python3 examples/02_turtlebot3_spawn.py

    # Without Gazebo (mock mode for learning):
    python3 examples/02_turtlebot3_spawn.py
"""

import sys
from pathlib import Path
import time

# Add project to path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import model_management


def main():
    """Run TurtleBot3 spawn example."""

    print("=" * 60)
    print("Example 2: TurtleBot3 Spawn and Control")
    print("=" * 60)
    print()

    robot_name = "my_turtlebot3"

    # Step 1: Spawn TurtleBot3 Burger
    print("Step 1: Spawning TurtleBot3 Burger...")
    result = model_management.spawn_model(
        model_name=robot_name,
        model_type="turtlebot3_burger",
        x=0.0,
        y=0.0,
        z=0.01,  # Slightly above ground
        roll=0.0,
        pitch=0.0,
        yaw=0.0
    )

    if result.success:
        print(f"✓ TurtleBot3 '{robot_name}' spawned")
        if result.data:
            print(f"  - Position: ({result.data.get('position', {}).get('x', 0):.2f}, "
                  f"{result.data.get('position', {}).get('y', 0):.2f}, "
                  f"{result.data.get('position', {}).get('z', 0):.2f})")
            print(f"  - Model type: {result.data.get('model_type', 'unknown')}")
            if result.data.get('mock_data'):
                print(f"  - Mode: MOCK (simulated spawn)")
    else:
        print(f"✗ Failed to spawn: {result.error}")
        return

    print()

    # Step 2: Get robot's current state
    print("Step 2: Getting robot state...")
    result = model_management.get_model_state(model_name=robot_name)

    if result.success:
        print(f"✓ Robot state retrieved")
        if result.data:
            pose = result.data.get('pose', {})
            position = pose.get('position', {})
            orientation = pose.get('orientation', {})
            print(f"  - Position: ({position.get('x', 0):.2f}, "
                  f"{position.get('y', 0):.2f}, {position.get('z', 0):.2f})")
            print(f"  - Orientation: ({orientation.get('roll', 0):.2f}, "
                  f"{orientation.get('pitch', 0):.2f}, {orientation.get('yaw', 0):.2f}) rad")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 3: Move robot to new position
    print("Step 3: Moving robot to position (2.0, 1.5, 0.01)...")
    result = model_management.set_model_state(
        model_name=robot_name,
        x=2.0,
        y=1.5,
        z=0.01,
        roll=0.0,
        pitch=0.0,
        yaw=1.57  # 90 degrees
    )

    if result.success:
        print(f"✓ Robot moved to new position")
        if result.data:
            new_pos = result.data.get('position', {})
            print(f"  - New position: ({new_pos.get('x', 0):.2f}, "
                  f"{new_pos.get('y', 0):.2f}, {new_pos.get('z', 0):.2f})")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 4: Verify new state
    print("Step 4: Verifying new robot state...")
    result = model_management.get_model_state(model_name=robot_name)

    if result.success and result.data:
        pose = result.data.get('pose', {})
        position = pose.get('position', {})
        print(f"✓ Current position: ({position.get('x', 0):.2f}, "
              f"{position.get('y', 0):.2f}, {position.get('z', 0):.2f})")

    print()

    # Step 5: List all models
    print("Step 5: Listing all models...")
    result = model_management.list_models(response_format="summary")

    if result.success and result.data:
        models = result.data.get('models', [])
        print(f"✓ Total models in simulation: {len(models)}")
        print(f"  - Models: {[m.get('name', 'unknown') for m in models]}")

    print()

    # Step 6: Clean up - delete robot
    print("Step 6: Deleting robot...")
    result = model_management.delete_model(model_name=robot_name)

    if result.success:
        print(f"✓ Robot '{robot_name}' deleted")
    else:
        print(f"✗ Failed to delete: {result.error}")

    print()
    print("=" * 60)
    print("Example completed!")
    print()
    print("What you learned:")
    print("  - How to spawn TurtleBot3 models")
    print("  - How to query robot state (position, orientation)")
    print("  - How to set robot state (teleport)")
    print("  - How to clean up models")
    print()
    print("Next steps:")
    print("  - Try Example 3: Reading sensor data")
    print("  - Experiment with different spawn positions")
    print("  - Try different TurtleBot3 variants (waffle, waffle_pi)")
    print("=" * 60)


if __name__ == "__main__":
    main()
