#!/usr/bin/env python3
"""
Multi-Robot Fleet Management Demo.

Demonstrates Phase 1 enhancement capabilities:
- Spawning robot fleets in various formations
- Monitoring fleet status with token efficiency
- Managing multiple robots simultaneously

Phase 1 Enhancement - Week 1
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.multi_robot_tools import (
    spawn_robot_fleet,
    get_fleet_status,
)


def demo_grid_formation():
    """Demonstrate grid formation spawning."""
    print("\n" + "=" * 60)
    print("DEMO 1: Grid Formation (3x3 = 9 robots)")
    print("=" * 60)

    result = spawn_robot_fleet(
        robot_model="turtlebot3_burger",
        count=9,
        formation="grid",
        spacing=2.0,
        start_position={"x": 0.0, "y": 0.0, "z": 0.5}
    )

    if result.success:
        print(f"✅ Success: Spawned {result.data['spawned']}/{result.data['requested']} robots")
        print(f"\nRobot positions:")
        for robot in result.data['robots'][:3]:  # Show first 3
            pos = robot['position']
            print(f"  - {robot['name']}: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})")
        if len(result.data['robots']) > 3:
            print(f"  ... and {len(result.data['robots']) - 3} more robots")
    else:
        print(f"❌ Failed: {result.error}")
        print(f"   Note: {result.data.get('note', 'No additional info')}")


def demo_circle_formation():
    """Demonstrate circle formation spawning."""
    print("\n" + "=" * 60)
    print("DEMO 2: Circle Formation (8 robots, 4m radius)")
    print("=" * 60)

    result = spawn_robot_fleet(
        robot_model="simple_robot",
        count=8,
        formation="circle",
        spacing=4.0,  # Radius
        start_position={"x": 10.0, "y": 0.0, "z": 0.5}
    )

    if result.success:
        print(f"✅ Success: Spawned {result.data['spawned']} robots in circle")
        print(f"   Formation: {result.data['formation']}")
        print(f"\nFirst robot position:")
        if result.data['robots']:
            pos = result.data['robots'][0]['position']
            ori = result.data['robots'][0]['orientation']
            print(f"  Position: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})")
            print(f"  Orientation (yaw): {ori['yaw']:.2f} rad")
    else:
        print(f"❌ Failed: {result.error}")


def demo_line_formation():
    """Demonstrate line formation spawning."""
    print("\n" + "=" * 60)
    print("DEMO 3: Line Formation (5 robots, 1.5m spacing)")
    print("=" * 60)

    result = spawn_robot_fleet(
        robot_model="mobile_robot",
        count=5,
        formation="line",
        spacing=1.5,
        start_position={"x": 0.0, "y": -10.0, "z": 0.5}
    )

    if result.success:
        print(f"✅ Success: Spawned {result.data['spawned']} robots in line")
        print(f"\nRobot spacing verification:")
        robots = result.data['robots']
        if len(robots) >= 2:
            pos1 = robots[0]['position']
            pos2 = robots[1]['position']
            import math
            distance = math.sqrt((pos2['x'] - pos1['x'])**2 + (pos2['y'] - pos1['y'])**2)
            print(f"  Distance between robot_0 and robot_1: {distance:.2f}m (expected 1.5m)")
    else:
        print(f"❌ Failed: {result.error}")


def demo_random_formation():
    """Demonstrate random formation with collision avoidance."""
    print("\n" + "=" * 60)
    print("DEMO 4: Random Formation (10 robots in 12x12m area)")
    print("=" * 60)

    result = spawn_robot_fleet(
        robot_model="explorer_bot",
        count=10,
        formation="random",
        spacing=12.0,  # Area size
        start_position={"x": 0.0, "y": 10.0, "z": 0.5}
    )

    if result.success:
        print(f"✅ Success: Spawned {result.data['spawned']} robots randomly")
        print(f"   All robots placed with collision avoidance")
        print(f"\nSample positions:")
        for robot in result.data['robots'][:3]:
            pos = robot['position']
            print(f"  - {robot['name']}: ({pos['x']:.2f}, {pos['y']:.2f})")
    else:
        print(f"❌ Failed: {result.error}")


def demo_fleet_status_summary():
    """Demonstrate fleet status with summary format (token efficient)."""
    print("\n" + "=" * 60)
    print("DEMO 5: Fleet Status - Summary Format (Token Efficient)")
    print("=" * 60)

    result = get_fleet_status(
        namespace_pattern="robot",
        response_format="summary"
    )

    if result.success:
        data = result.data
        print(f"✅ Fleet Summary:")
        print(f"   Total robots: {data['fleet_size']}")
        print(f"   Active: {data['summary']['active']}")
        print(f"   Moving: {data['summary']['moving']}")
        print(f"   Idle: {data['summary']['idle']}")
        print(f"\n📊 Token Efficiency:")
        print(f"   Tokens sent: {data['tokens_sent']}")
        print(f"   Tokens saved: {data['tokens_saved']}")
        print(f"   Savings: {data['tokens_saved'] / (data['tokens_sent'] + data['tokens_saved']) * 100:.1f}%")
        print(f"\n   Robot names: {', '.join(data['robot_names'][:5])}")
        if len(data['robot_names']) > 5:
            print(f"   ... and {len(data['robot_names']) - 5} more")
    else:
        print(f"❌ Failed: {result.error}")


def demo_fleet_status_detailed():
    """Demonstrate fleet status with detailed format."""
    print("\n" + "=" * 60)
    print("DEMO 6: Fleet Status - Detailed Format")
    print("=" * 60)

    result = get_fleet_status(
        namespace_pattern="robot",
        response_format="detailed",
        include_velocity=True
    )

    if result.success:
        data = result.data
        print(f"✅ Detailed Fleet Status:")
        print(f"   Fleet size: {data['fleet_size']}")
        print(f"\n   Sample robot data (first 2 robots):")
        for robot in data['robots'][:2]:
            print(f"\n   {robot['name']}:")
            print(f"     Position: ({robot['position']['x']:.2f}, {robot['position']['y']:.2f}, {robot['position']['z']:.2f})")
            if 'velocity' in robot:
                linear = robot['velocity']['linear']
                print(f"     Linear velocity: ({linear['x']:.2f}, {linear['y']:.2f}, {linear['z']:.2f})")
            print(f"     Status: {robot.get('status', 'unknown')}")
    else:
        print(f"❌ Failed: {result.error}")


def demo_custom_namespace():
    """Demonstrate custom namespace prefix."""
    print("\n" + "=" * 60)
    print("DEMO 7: Custom Namespace Prefix")
    print("=" * 60)

    result = spawn_robot_fleet(
        robot_model="scout_robot",
        count=4,
        formation="grid",
        spacing=2.0,
        namespace_prefix="scout",  # Custom prefix
        start_position={"x": 15.0, "y": 0.0, "z": 0.5}
    )

    if result.success:
        print(f"✅ Success: Spawned {result.data['spawned']} scouts")
        print(f"   Namespaces:")
        for robot in result.data['robots']:
            print(f"     - {robot['namespace']}")
    else:
        print(f"❌ Failed: {result.error}")


def main():
    """Run all multi-robot fleet demos."""
    print("\n" + "=" * 60)
    print("MULTI-ROBOT FLEET MANAGEMENT DEMO")
    print("Phase 1 Enhancement - Week 1")
    print("=" * 60)
    print("\nThis demo shows Phase 1 multi-robot capabilities:")
    print("1. Grid formation (3x3)")
    print("2. Circle formation (8 robots)")
    print("3. Line formation (5 robots)")
    print("4. Random formation (10 robots with collision avoidance)")
    print("5. Fleet status - Summary (token efficient)")
    print("6. Fleet status - Detailed")
    print("7. Custom namespace prefix")
    print("\n⚠️  Note: Demos use mock data when Gazebo is not running")

    # Run all demos
    demo_grid_formation()
    demo_circle_formation()
    demo_line_formation()
    demo_random_formation()
    demo_fleet_status_summary()
    demo_fleet_status_detailed()
    demo_custom_namespace()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\n✅ Phase 1 Multi-Robot Tools Demonstrated:")
    print("   - spawn_robot_fleet() with 4 formation types")
    print("   - get_fleet_status() with token efficiency")
    print("\n📚 Next Steps:")
    print("   - Implement send_fleet_command() for coordinated control")
    print("   - Add multi-robot collision avoidance")
    print("   - Integrate with Nav2 for autonomous fleets")


if __name__ == "__main__":
    main()
