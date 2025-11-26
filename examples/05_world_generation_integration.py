#!/usr/bin/env python3
"""
Example: Complete World Generation and Object Spawning Integration

Demonstrates the end-to-end workflow for:
1. Creating an empty world
2. Saving world to file
3. Loading world from file
4. Placing objects (generating SDF)
5. Spawning objects in Gazebo simulation

This example shows both offline generation (no Gazebo required)
and online spawning (requires running Gazebo).

Prerequisites:
- ROS2 Humble or Jazzy installed and sourced
- Gazebo Harmonic or Garden running
- gazebo_ros2_control package installed

Usage:
    # Terminal 1: Start Gazebo
    ros2 launch gazebo_ros gazebo.launch.py

    # Terminal 2: Run this example
    python examples/05_world_generation_integration.py
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import world_generation


def example_offline_world_generation():
    """
    Part 1: Offline World Generation (No Gazebo Required)

    Demonstrates creating and saving worlds without a running simulation.
    """
    print("=" * 70)
    print("PART 1: Offline World Generation")
    print("=" * 70)
    print()

    # Step 1: Create an empty world with ground plane and sun
    print("1. Creating empty world...")
    result = world_generation.create_empty_world(
        world_name="demo_world",
        include_ground_plane=True,
        include_sun=True,
        physics_step_size=0.001,
        real_time_factor=1.0
    )

    if result.success:
        print(f"   ✓ Created world: {result.data['world_name']}")
        print(f"   ✓ SDF size: {len(result.data['sdf_content'])} characters")
        print()
    else:
        print(f"   ✗ Failed: {result.error}")
        return

    # Step 2: Save world to file
    print("2. Saving world to file...")
    world_path = PROJECT_ROOT / "examples" / "demo_world.sdf"
    save_result = world_generation.save_world(
        world_name="demo_world",
        sdf_content=result.data["sdf_content"],
        file_path=str(world_path)
    )

    if save_result.success:
        print(f"   ✓ Saved to: {save_result.data['file_path']}")
        print(f"   ✓ File size: {save_result.data['file_size_bytes']} bytes")
        print()
    else:
        print(f"   ✗ Failed: {save_result.error}")
        return

    # Step 3: Load world from file
    print("3. Loading world from file...")
    load_result = world_generation.load_world(str(world_path))

    if load_result.success:
        print(f"   ✓ Loaded world: {load_result.data['world_name']}")
        print(f"   ✓ File size: {load_result.data['file_size_bytes']} bytes")
        print()
    else:
        print(f"   ✗ Failed: {load_result.error}")
        return

    # Step 4: List available templates
    print("4. Available world templates:")
    templates_result = world_generation.list_world_templates()
    if templates_result.success:
        for template in templates_result.data["templates"]:
            print(f"   - {template['name']}: {template['description']}")
        print()


def example_offline_object_placement():
    """
    Part 2: Offline Object Placement (SDF Generation)

    Generate SDF content for objects without spawning them.
    """
    print("=" * 70)
    print("PART 2: Offline Object Placement (SDF Generation)")
    print("=" * 70)
    print()

    # Generate box SDF
    print("1. Generating box obstacle SDF...")
    box_result = world_generation.place_box(
        name="red_box_obstacle",
        x=2.0, y=0.0, z=0.5,
        width=1.0, height=1.0, depth=1.0,
        color={"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        static=True
    )

    if box_result.success:
        print(f"   ✓ Generated box SDF")
        print(f"   ✓ Position: {box_result.data['position']}")
        print(f"   ✓ Static: {box_result.data['static']}")
        print()
    else:
        print(f"   ✗ Failed: {box_result.error}")

    # Generate sphere SDF
    print("2. Generating sphere SDF...")
    sphere_result = world_generation.place_sphere(
        name="green_ball",
        x=1.0, y=1.0, z=0.5,
        radius=0.5,
        color={"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0},
        static=False  # This ball will roll!
    )

    if sphere_result.success:
        print(f"   ✓ Generated sphere SDF")
        print(f"   ✓ Position: {sphere_result.data['position']}")
        print(f"   ✓ Radius: {sphere_result.data['radius']}")
        print(f"   ✓ Static: {sphere_result.data['static']}")
        print()
    else:
        print(f"   ✗ Failed: {sphere_result.error}")

    # Generate cylinder SDF
    print("3. Generating cylinder SDF...")
    cylinder_result = world_generation.place_cylinder(
        name="blue_pillar",
        x=0.0, y=0.0, z=1.0,
        radius=0.2,
        length=2.0,
        color={"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0},
        static=True
    )

    if cylinder_result.success:
        print(f"   ✓ Generated cylinder SDF")
        print(f"   ✓ Position: {cylinder_result.data['position']}")
        print(f"   ✓ Radius: {cylinder_result.data['radius']}, Length: {cylinder_result.data['length']}")
        print()
    else:
        print(f"   ✗ Failed: {cylinder_result.error}")


def example_online_object_spawning():
    """
    Part 3: Online Object Spawning (Requires Running Gazebo)

    Spawn objects directly into a running Gazebo simulation.
    """
    print("=" * 70)
    print("PART 3: Online Object Spawning (Requires Running Gazebo)")
    print("=" * 70)
    print()

    print("Prerequisites:")
    print("  1. ROS2 sourced: source /opt/ros/humble/setup.bash")
    print("  2. Gazebo running: ros2 launch gazebo_ros gazebo.launch.py")
    print()
    input("Press Enter when Gazebo is ready (or Ctrl+C to skip)...")
    print()

    # Spawn a red box
    print("1. Spawning red box obstacle...")
    box_result = world_generation.spawn_box(
        name="red_box_1",
        x=2.0, y=0.0, z=0.5,
        width=1.0, height=1.0, depth=1.0,
        color={"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        static=True,
        timeout=10.0
    )

    if box_result.success:
        print(f"   ✓ Spawned: {box_result.data['name']}")
        print(f"   ✓ Position: {box_result.data['position']}")
        print()
    else:
        print(f"   ✗ Failed: {box_result.error}")
        if box_result.suggestions:
            print("   Suggestions:")
            for suggestion in box_result.suggestions:
                print(f"     - {suggestion}")
        print()

    # Spawn a green ball (dynamic - will roll!)
    print("2. Spawning green ball (physics-enabled)...")
    sphere_result = world_generation.spawn_sphere(
        name="green_ball_1",
        x=1.0, y=1.0, z=1.0,  # Spawn 1m high so it falls
        radius=0.5,
        color={"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0},
        static=False,  # Physics enabled!
        timeout=10.0
    )

    if sphere_result.success:
        print(f"   ✓ Spawned: {sphere_result.data['name']}")
        print(f"   ✓ Position: {sphere_result.data['position']}")
        print(f"   ✓ Static: {sphere_result.data['static']}")
        print(f"   ✓ Note: Watch the ball fall and roll in Gazebo!")
        print()
    else:
        print(f"   ✗ Failed: {sphere_result.error}")
        print()

    # Spawn a blue pillar
    print("3. Spawning blue pillar...")
    cylinder_result = world_generation.spawn_cylinder(
        name="blue_pillar_1",
        x=-1.0, y=0.0, z=1.0,
        radius=0.2,
        length=2.0,
        color={"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0},
        static=True,
        timeout=10.0
    )

    if cylinder_result.success:
        print(f"   ✓ Spawned: {cylinder_result.data['name']}")
        print(f"   ✓ Position: {cylinder_result.data['position']}")
        print()
    else:
        print(f"   ✗ Failed: {cylinder_result.error}")
        print()


def example_combined_workflow():
    """
    Part 4: Combined Workflow

    Demonstrates combining generation and spawning in a realistic scenario.
    """
    print("=" * 70)
    print("PART 4: Combined Workflow - Creating an Obstacle Course")
    print("=" * 70)
    print()

    # Create an obstacle course
    print("1. Creating obstacle course layout...")
    course_result = world_generation.create_obstacle_course(
        num_obstacles=5,
        area_size=10.0,
        obstacle_types=["box", "cylinder"],
        min_distance=2.0,
        seed=42
    )

    if not course_result.success:
        print(f"   ✗ Failed: {course_result.error}")
        return

    obstacles = course_result.data["obstacles"]
    print(f"   ✓ Created course with {len(obstacles)} obstacles")
    print()

    # Show obstacles (offline generation)
    print("2. Obstacle layout (offline generation):")
    for i, obs in enumerate(obstacles, 1):
        print(f"   {i}. {obs['type']} at ({obs['position']['x']:.2f}, {obs['position']['y']:.2f})")
    print()

    # Optionally spawn them in Gazebo
    try:
        input("Press Enter to spawn these obstacles in Gazebo (or Ctrl+C to skip)...")
        print()

        print("3. Spawning obstacles in Gazebo...")
        success_count = 0

        for i, obs in enumerate(obstacles, 1):
            print(f"   Spawning obstacle {i}/{len(obstacles)}...", end=" ")

            if obs["type"] == "box":
                size = obs["size"]
                result = world_generation.spawn_box(
                    name=f"obstacle_box_{i}",
                    x=obs["position"]["x"],
                    y=obs["position"]["y"],
                    z=obs["position"]["z"],
                    width=size,
                    height=size,
                    depth=size,
                    static=True
                )
            elif obs["type"] == "cylinder":
                size = obs["size"]
                result = world_generation.spawn_cylinder(
                    name=f"obstacle_cylinder_{i}",
                    x=obs["position"]["x"],
                    y=obs["position"]["y"],
                    z=obs["position"]["z"],
                    radius=size * 0.5,  # Use size as diameter
                    length=size * 2.0,  # Make cylinder taller than wide
                    static=True
                )
            elif obs["type"] == "sphere":
                size = obs["size"]
                result = world_generation.spawn_sphere(
                    name=f"obstacle_sphere_{i}",
                    x=obs["position"]["x"],
                    y=obs["position"]["y"],
                    z=obs["position"]["z"],
                    radius=size,
                    static=True
                )
            else:
                print("✗ Unknown type")
                continue

            if result.success:
                print("✓")
                success_count += 1
            else:
                print(f"✗ {result.error}")

        print()
        print(f"   Spawned {success_count}/{len(obstacles)} obstacles successfully")
        print()

    except KeyboardInterrupt:
        print("\n   Skipped spawning (Gazebo not running)")
        print()


def main():
    """Run all examples."""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "World Generation Integration Example" + " " * 22 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        # Part 1: Offline world generation
        example_offline_world_generation()

        # Part 2: Offline object placement
        example_offline_object_placement()

        # Part 3: Online spawning (requires Gazebo)
        try:
            example_online_object_spawning()
        except KeyboardInterrupt:
            print("\nSkipped online spawning")
            print()

        # Part 4: Combined workflow
        example_combined_workflow()

        print("=" * 70)
        print("Example completed!")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
