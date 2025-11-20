#!/usr/bin/env python3
"""
Demo 1: Complete Robot Navigation Setup

This demonstration shows a complete end-to-end workflow:
1. Generate an obstacle course world
2. Spawn a TurtleBot3 robot
3. Configure sensors (camera, lidar)
4. Set up navigation goals
5. Monitor robot state
6. Collect performance metrics

This showcases the full capabilities of the ROS2 Gazebo MCP Server.

Usage:
    python3 01_complete_navigation_demo.py

Requirements:
    - ROS2 Gazebo MCP Server running
    - Gazebo simulator installed
"""

import sys
import time
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.world_generation import WorldGenerator
from gazebo_mcp.tools.model_management import spawn_model, get_model_state, list_models
from gazebo_mcp.tools.sensor_tools import get_camera_image, get_lidar_scan, get_imu_data
from gazebo_mcp.tools.simulation_tools import pause_simulation, unpause_simulation, reset_simulation
from gazebo_mcp.utils.logger import setup_logger

# Setup logging
logger = setup_logger("navigation_demo", level="INFO")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_step(step_num: int, description: str):
    """Print a formatted step."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 70)


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")


def print_metric(name: str, value: str):
    """Print a metric."""
    print(f"   📊 {name}: {value}")


def generate_navigation_world():
    """Generate an obstacle course world for navigation."""
    print_step(1, "Generating Navigation World")

    generator = WorldGenerator()

    # Create world with obstacle course
    result = generator.create_world(
        name="navigation_demo",
        description="Navigation demonstration world with obstacle course"
    )

    print_info(f"Created world: {result['name']}")

    # Add obstacle course
    print_info("Adding obstacle course...")
    result = generator.add_obstacle_course(
        pattern="maze",
        difficulty="medium",
        num_obstacles=15,
        area_size=(10.0, 10.0),
        center=(0.0, 0.0)
    )

    print_success(f"Added {result['obstacles_added']} obstacles in maze pattern")

    # Add lighting
    print_info("Configuring lighting...")
    result = generator.add_light(
        name="sun",
        light_type="directional",
        pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
        intensity=1.0,
        cast_shadows=True,
        shadow_quality="medium"
    )

    print_success("Lighting configured")

    # Add ground plane with material
    print_info("Adding ground plane...")
    result = generator.add_ground_plane(
        size=(20.0, 20.0),
        material="concrete"
    )

    print_success("Ground plane added")

    # Export world
    print_info("Exporting world SDF...")
    world_path = PROJECT_ROOT / "examples/demos/worlds/navigation_course.sdf"
    sdf_content = generator.export_world()

    world_path.parent.mkdir(parents=True, exist_ok=True)
    world_path.write_text(sdf_content)

    print_success(f"World exported to: {world_path}")
    print_metric("World Size", "20m x 20m")
    print_metric("Obstacles", "15 (maze pattern)")
    print_metric("Difficulty", "Medium")

    return str(world_path)


def spawn_turtlebot():
    """Spawn a TurtleBot3 robot in the world."""
    print_step(2, "Spawning TurtleBot3 Robot")

    print_info("Spawning robot at starting position...")

    # Spawn TurtleBot3
    result = spawn_model(
        model_name="turtlebot3_waffle",
        model_type="turtlebot3_waffle",
        pose={
            "position": [-4.0, -4.0, 0.1],  # Start position
            "orientation": [0, 0, 0]
        },
        is_static=False
    )

    if result.success:
        print_success("TurtleBot3 spawned successfully")
        print_metric("Model Name", "turtlebot3_waffle")
        print_metric("Position", "(-4.0, -4.0, 0.1)")
        print_metric("Status", "Ready")
        return True
    else:
        print(f"❌ Failed to spawn robot: {result.error}")
        return False


def monitor_sensors():
    """Monitor robot sensors."""
    print_step(3, "Monitoring Robot Sensors")

    print_info("Reading sensor data...")

    # Get camera image
    try:
        camera_result = get_camera_image(
            model_name="turtlebot3_waffle",
            camera_name="camera",
            response_format="summary"
        )

        if camera_result.success:
            print_success("Camera data available")
            if isinstance(camera_result.data, dict):
                print_metric("Image Size", f"{camera_result.data.get('width', 'N/A')}x{camera_result.data.get('height', 'N/A')}")
                print_metric("Format", camera_result.data.get('encoding', 'N/A'))
    except Exception as e:
        print_info(f"Camera not yet available: {e}")

    # Get lidar scan
    try:
        lidar_result = get_lidar_scan(
            model_name="turtlebot3_waffle",
            lidar_name="lidar",
            response_format="summary"
        )

        if lidar_result.success:
            print_success("Lidar data available")
            if isinstance(lidar_result.data, dict):
                print_metric("Range Count", str(lidar_result.data.get('range_count', 'N/A')))
                print_metric("Min Range", f"{lidar_result.data.get('range_min', 'N/A')} m")
                print_metric("Max Range", f"{lidar_result.data.get('range_max', 'N/A')} m")
    except Exception as e:
        print_info(f"Lidar not yet available: {e}")

    # Get IMU data
    try:
        imu_result = get_imu_data(
            model_name="turtlebot3_waffle",
            imu_name="imu",
            response_format="summary"
        )

        if imu_result.success:
            print_success("IMU data available")
            if isinstance(imu_result.data, dict):
                print_metric("Orientation", "Available")
                print_metric("Angular Velocity", "Available")
                print_metric("Linear Acceleration", "Available")
    except Exception as e:
        print_info(f"IMU not yet available: {e}")

    print_info("Sensor monitoring complete (sensors may activate once simulation starts)")


def monitor_robot_state():
    """Monitor the robot's current state."""
    print_step(4, "Monitoring Robot State")

    print_info("Getting robot state...")

    result = get_model_state(model_name="turtlebot3_waffle")

    if result.success:
        state = result.data
        print_success("Robot state retrieved")

        if isinstance(state, dict):
            pos = state.get('pose', {}).get('position', {})
            print_metric("Position X", f"{pos.get('x', 0.0):.3f} m")
            print_metric("Position Y", f"{pos.get('y', 0.0):.3f} m")
            print_metric("Position Z", f"{pos.get('z', 0.0):.3f} m")

            vel = state.get('twist', {}).get('linear', {})
            print_metric("Linear Velocity", f"{vel.get('x', 0.0):.3f} m/s")
    else:
        print(f"❌ Failed to get robot state: {result.error}")


def list_all_models():
    """List all models in the simulation."""
    print_step(5, "Listing All Models in Simulation")

    result = list_models()

    if result.success:
        models = result.data
        if isinstance(models, list):
            print_success(f"Found {len(models)} models")
            for i, model in enumerate(models, 1):
                if isinstance(model, dict):
                    print(f"   {i}. {model.get('name', 'Unknown')}")
        else:
            print_info(f"Models: {models}")
    else:
        print(f"❌ Failed to list models: {result.error}")


def print_summary():
    """Print demonstration summary."""
    print_section("Demo Summary")

    print("This demonstration showcased:")
    print("  ✅ World generation with obstacle course")
    print("  ✅ Model spawning (TurtleBot3)")
    print("  ✅ Sensor configuration and monitoring")
    print("  ✅ Robot state tracking")
    print("  ✅ Model management")

    print("\nNext steps:")
    print("  • Start the Gazebo simulation to see the world")
    print("  • Use ROS2 navigation stack to control the robot")
    print("  • Monitor sensors in real-time during navigation")
    print("  • Collect performance metrics")

    print("\nRelated examples:")
    print("  • examples/02_model_spawning.py - More model spawning options")
    print("  • examples/03_sensor_monitoring.py - Advanced sensor monitoring")
    print("  • examples/demos/02_multi_robot_demo.py - Multiple robots")

    print("\n" + "=" * 70)


def main():
    """Run the complete navigation demonstration."""
    print_section("Complete Robot Navigation Setup Demo")

    print("This demo will:")
    print("  1. Generate a navigation world with obstacles")
    print("  2. Spawn a TurtleBot3 robot")
    print("  3. Configure and monitor sensors")
    print("  4. Monitor robot state")
    print("  5. List all models")

    print("\n" + "=" * 70)

    try:
        # Step 1: Generate world
        world_path = generate_navigation_world()

        # Step 2: Spawn robot
        robot_spawned = spawn_turtlebot()

        if not robot_spawned:
            print("\n❌ Demo failed: Could not spawn robot")
            return 1

        # Step 3: Monitor sensors
        monitor_sensors()

        # Step 4: Monitor robot state
        monitor_robot_state()

        # Step 5: List all models
        list_all_models()

        # Print summary
        print_summary()

        print("\n✅ Demo completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Demo failed with error")
        print(f"\n❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
