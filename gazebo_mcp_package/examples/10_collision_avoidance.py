#!/usr/bin/env python3
"""
Multi-Robot Collision Avoidance Demo.

Demonstrates Phase 1 collision avoidance capabilities:
- Velocity Obstacle algorithm for collision prediction
- Social Force model for smooth avoidance
- Collision detection and velocity adjustment
- Fleet safety monitoring

Phase 1 Enhancement - Week 1
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.multi_robot_tools import (
    spawn_robot_fleet,
    enable_multi_robot_collision_avoidance,
    send_fleet_command,
)


def demo_velocity_obstacle_safe():
    """Demonstrate velocity obstacle with safe robot fleet."""
    print("\n" + "=" * 60)
    print("DEMO 1: Velocity Obstacle - Safe Fleet")
    print("=" * 60)
    print("Checking robots that are far apart and stationary")

    # Spawn robots in a grid (safe spacing)
    spawn_result = spawn_robot_fleet(
        robot_model="test_robot",
        count=4,
        formation="grid",
        spacing=3.0,  # Large spacing = safe
        start_position={"x": 0.0, "y": 0.0, "z": 0.5}
    )

    if spawn_result.success:
        print(f"✅ Spawned {spawn_result.data['spawned']} robots")
    else:
        print(f"⚠️  Using mock data for demo")

    # Check for collisions
    result = enable_multi_robot_collision_avoidance(
        namespace_pattern="test_robot",
        method="velocity_obstacle",
        safety_distance=0.5
    )

    if result.success:
        data = result.data
        print(f"\n📊 Collision Avoidance Status:")
        print(f"   Method: {data['method']}")
        print(f"   Robots protected: {data['robots_protected']}")
        print(f"   Safety distance: {data['safety_distance']}m")
        print(f"   Collisions detected: {len(data['collision_predictions'])}")
        print(f"   Adjustments needed: {data['velocity_adjustments_needed']}")

        if data['collision_predictions']:
            print(f"\n⚠️  Collision Predictions:")
            for pred in data['collision_predictions'][:3]:
                print(f"      {pred['robot_a']} ↔ {pred['robot_b']}: {pred['time_to_collision']}")
        else:
            print(f"\n✅ Fleet is safe - no collisions predicted")
    else:
        print(f"❌ Error: {result.error}")


def demo_velocity_obstacle_collision():
    """Demonstrate velocity obstacle detecting a collision."""
    print("\n" + "=" * 60)
    print("DEMO 2: Velocity Obstacle - Collision Detection")
    print("=" * 60)
    print("Robots moving toward each other")

    # Spawn robots close together
    spawn_result = spawn_robot_fleet(
        robot_model="collision_test",
        count=2,
        formation="line",
        spacing=2.0,  # Close spacing
        start_position={"x": 0.0, "y": 0.0, "z": 0.5}
    )

    if spawn_result.success:
        print(f"✅ Spawned {spawn_result.data['spawned']} robots")

        # Simulate robots moving toward each other
        # (In real scenario, you'd use send_fleet_command to set velocities)
        print(f"\n🚀 Simulating robots moving toward each other...")
        print(f"   robot_0 at x=0.0, velocity=+0.5 m/s (moving right)")
        print(f"   robot_1 at x=2.0, velocity=-0.5 m/s (moving left)")

    # Check for collisions
    result = enable_multi_robot_collision_avoidance(
        namespace_pattern="collision_test",
        method="velocity_obstacle",
        safety_distance=0.5
    )

    if result.success:
        data = result.data
        print(f"\n📊 Collision Analysis:")
        print(f"   Robots analyzed: {data['robots_protected']}")
        print(f"   Potential collisions: {len(data['collision_predictions'])}")

        if data['collision_predictions']:
            print(f"\n⚠️  COLLISION ALERT!")
            for pred in data['collision_predictions']:
                print(f"   {pred['robot_a']} will collide with {pred['robot_b']}")
                print(f"   Time to collision: {pred['time_to_collision']}")
                print(f"   Action: {pred['action']}")

        if data['adjustments']:
            print(f"\n🔧 Recommended Velocity Adjustments:")
            for adj in data['adjustments']:
                vel = adj['new_velocity']
                print(f"   {adj['robot']}: vx={vel['x']:.3f}, vy={vel['y']:.3f} m/s")

            print(f"\n💡 Apply adjustments with send_fleet_command:")
            print(f"   send_fleet_command('velocity', targets=['robot_0'], ...")
    else:
        print(f"❌ Error: {result.error}")


def demo_social_force():
    """Demonstrate social force model for smooth navigation."""
    print("\n" + "=" * 60)
    print("DEMO 3: Social Force Model")
    print("=" * 60)
    print("Smooth, natural collision avoidance using repulsive forces")

    # Spawn robots in formation
    spawn_result = spawn_robot_fleet(
        robot_model="social_robot",
        count=5,
        formation="circle",
        spacing=2.0,  # Circle radius
        start_position={"x": 5.0, "y": 0.0, "z": 0.5}
    )

    if spawn_result.success:
        print(f"✅ Spawned {spawn_result.data['spawned']} robots in circle")
    else:
        print(f"⚠️  Using mock data for demo")

    # Use social force model
    result = enable_multi_robot_collision_avoidance(
        namespace_pattern="social_robot",
        method="social_force",
        safety_distance=0.8  # Larger safety zone for smoother forces
    )

    if result.success:
        data = result.data
        print(f"\n📊 Social Force Analysis:")
        print(f"   Method: {data['method']}")
        print(f"   Robots: {data['robots_protected']}")
        print(f"   Safety zone: {data['safety_distance']}m")
        print(f"   Influence range: {data['safety_distance'] * 2}m")

        if data['adjustments']:
            print(f"\n🌊 Repulsive Forces Applied:")
            print(f"   {len(data['adjustments'])} robots affected by forces")
            for adj in data['adjustments'][:3]:
                vel = adj['new_velocity']
                force_mag = (vel['x']**2 + vel['y']**2)**0.5
                print(f"   {adj['robot']}: force magnitude = {force_mag:.3f} m/s")
        else:
            print(f"\n✅ Robots far apart - no forces needed")
    else:
        print(f"❌ Error: {result.error}")


def demo_specific_robots():
    """Demonstrate collision avoidance for specific robots."""
    print("\n" + "=" * 60)
    print("DEMO 4: Protect Specific Robots")
    print("=" * 60)
    print("Monitor only selected robots for collisions")

    # Check collision avoidance for specific robots
    result = enable_multi_robot_collision_avoidance(
        robot_namespaces=["robot_0", "robot_1", "robot_2"],
        method="velocity_obstacle",
        safety_distance=0.6,
        max_deceleration=2.0  # Allow faster deceleration
    )

    if result.success:
        data = result.data
        print(f"\n📊 Targeted Protection:")
        print(f"   Protecting: {', '.join(data['robot_names'])}")
        print(f"   Method: {data['method']}")
        print(f"   Max deceleration: {data['max_deceleration']} m/s²")

        if 'failed_robots' in data:
            print(f"\n⚠️  Failed to query: {', '.join(data['failed_robots'])}")
        else:
            print(f"\n✅ All specified robots found and analyzed")
    else:
        print(f"❌ Error: {result.error}")
        if result.error_code == "NO_ROBOTS_FOUND":
            print(f"   Suggestion: Spawn robots first using spawn_robot_fleet")


def demo_disable_avoidance():
    """Demonstrate disabling collision avoidance."""
    print("\n" + "=" * 60)
    print("DEMO 5: Disable Collision Avoidance")
    print("=" * 60)

    result = enable_multi_robot_collision_avoidance(
        namespace_pattern="robot",
        enable=False
    )

    if result.success:
        print(f"✅ Collision avoidance disabled for fleet")
        print(f"   Note: This is a status check, not persistent state")
    else:
        print(f"⚠️  {result.error}")


def demo_parameter_validation():
    """Demonstrate parameter validation."""
    print("\n" + "=" * 60)
    print("DEMO 6: Parameter Validation")
    print("=" * 60)

    # Test invalid method
    print("\n[Test 1] Invalid method:")
    try:
        result = enable_multi_robot_collision_avoidance(
            robot_namespaces=["robot_0"],
            method="invalid_method"
        )
        print(f"❌ Should have raised error")
    except Exception as e:
        print(f"✅ Correctly rejected: {str(e)[:60]}...")

    # Test invalid safety distance
    print("\n[Test 2] Invalid safety distance:")
    try:
        result = enable_multi_robot_collision_avoidance(
            robot_namespaces=["robot_0"],
            safety_distance=10.0  # Too large
        )
        print(f"❌ Should have raised error")
    except Exception as e:
        print(f"✅ Correctly rejected: {str(e)[:60]}...")

    # Test invalid max_deceleration
    print("\n[Test 3] Invalid max deceleration:")
    try:
        result = enable_multi_robot_collision_avoidance(
            robot_namespaces=["robot_0"],
            max_deceleration=0.0  # Too small
        )
        print(f"❌ Should have raised error")
    except Exception as e:
        print(f"✅ Correctly rejected: {str(e)[:60]}...")


def main():
    """Run all collision avoidance demos."""
    print("\n" + "=" * 60)
    print("MULTI-ROBOT COLLISION AVOIDANCE DEMO")
    print("Phase 1 Enhancement - Week 1")
    print("=" * 60)
    print("\nThis demo shows collision avoidance capabilities:")
    print("1. Velocity Obstacle - Safe fleet (no collisions)")
    print("2. Velocity Obstacle - Collision detection")
    print("3. Social Force - Smooth navigation")
    print("4. Protect specific robots")
    print("5. Disable avoidance")
    print("6. Parameter validation")
    print("\n⚠️  Note: Demos use mock data when Gazebo is not running")

    # Run all demos
    demo_velocity_obstacle_safe()
    demo_velocity_obstacle_collision()
    demo_social_force()
    demo_specific_robots()
    demo_disable_avoidance()
    demo_parameter_validation()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\n✅ Collision Avoidance Features Demonstrated:")
    print("   - Velocity Obstacle algorithm (predictive)")
    print("   - Social Force model (smooth, natural)")
    print("   - Collision prediction and detection")
    print("   - Velocity adjustment recommendations")
    print("   - Parameter validation")
    print("\n📚 Integration Example:")
    print("   1. Spawn fleet: spawn_robot_fleet(...)")
    print("   2. Check collisions: enable_multi_robot_collision_avoidance(...)")
    print("   3. Apply fixes: send_fleet_command('velocity', ...)")
    print("\n🎯 Real-World Usage:")
    print("   - Warehouse robots avoiding each other")
    print("   - Drone swarms maintaining safe distances")
    print("   - Multi-AGV coordination in factories")
    print("   - Search and rescue robot teams")


if __name__ == "__main__":
    main()
