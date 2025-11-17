#!/usr/bin/env python3
"""
Example 4: Simulation Control

This example demonstrates:
- Getting simulation status
- Pausing and unpausing simulation
- Resetting simulation
- Querying simulation time
- Setting simulation speed
- Getting world properties

Prerequisites:
- None (works without ROS2/Gazebo, will use mock data)

Optional:
- ROS2 sourced for real control
- Gazebo running for actual simulation control

Usage:
    python examples/04_simulation_control.py
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
            return data.get("data")
        else:
            print(f"{spacing}✗ Error: {data['error']}")
            if data.get("suggestions"):
                print(f"{spacing}Suggestions:")
                for suggestion in data["suggestions"]:
                    print(f"{spacing}  - {suggestion}")
    return None


def main():
    """Run simulation control example."""

    print_section("Gazebo MCP Server - Simulation Control Example")

    # Step 1: Create MCP server
    print("\n1. Creating MCP Server...")
    try:
        server = GazeboMCPServer()
        print("   ✓ Server created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create server: {e}")
        return

    # Step 2: Get simulation status
    print_section("2. Get Simulation Status")
    print("\nQuerying simulation status...")

    result = server.call_tool("gazebo_get_simulation_status", {})
    data = print_result(result, indent=1)

    if data:
        print(f"\n   Simulation State:")
        print(f"     Running: {data.get('is_running', False)}")
        print(f"     Paused: {data.get('is_paused', False)}")
        print(f"     Gazebo Connected: {data.get('gazebo_connected', False)}")

        if "time" in data:
            print(f"\n   Time Information:")
            print(f"     Simulation Time: {data['time'].get('simulation_time', 0):.2f} s")
            print(f"     Real Time: {data['time'].get('real_time', 0):.2f} s")
            print(f"     Iterations: {data['time'].get('iterations', 0)}")

        if "performance" in data:
            perf = data["performance"]
            print(f"\n   Performance:")
            print(f"     Real-time Factor: {perf.get('real_time_factor', 0):.2f}x")
            print(f"     Update Rate: {perf.get('update_rate', 0):.1f} Hz")

    # Step 3: Get simulation time
    print_section("3. Get Simulation Time")
    print("\nQuerying detailed time information...")

    result = server.call_tool("gazebo_get_simulation_time", {})
    data = print_result(result, indent=1)

    if data:
        print(f"\n   Simulation Time: {data.get('simulation_time', 0):.3f} s")
        print(f"   Real Time: {data.get('real_time', 0):.3f} s")
        print(f"   Iterations: {data.get('iterations', 0)}")

        if "real_time_factor" in data:
            rtf = data["real_time_factor"]
            print(f"   Real-time Factor: {rtf:.2f}x")

            if rtf > 1.0:
                print(f"   → Simulation running {rtf:.1f}x faster than real-time")
            elif rtf < 1.0:
                print(f"   → Simulation running {1/rtf:.1f}x slower than real-time")
            else:
                print(f"   → Simulation running at real-time speed")

    # Step 4: Pause simulation
    print_section("4. Pause Simulation")
    print("\nAttempting to pause simulation...")

    result = server.call_tool("gazebo_pause_simulation", {
        "timeout": 5.0
    })
    data = print_result(result, indent=1)

    if data:
        print(f"\n   Previous State: {'Paused' if data.get('was_paused') else 'Running'}")
        print(f"   Current State: Paused")

        # Verify pause
        time.sleep(0.5)
        result = server.call_tool("gazebo_get_simulation_status", {})
        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            is_paused = content["data"].get("is_paused", False)
            print(f"   Verified: {'✓ Paused' if is_paused else '✗ Still running'}")

    # Step 5: Unpause simulation
    print_section("5. Unpause Simulation")
    print("\nAttempting to unpause simulation...")

    result = server.call_tool("gazebo_unpause_simulation", {
        "timeout": 5.0
    })
    data = print_result(result, indent=1)

    if data:
        print(f"\n   Previous State: Paused")
        print(f"   Current State: Running")

        # Verify unpause
        time.sleep(0.5)
        result = server.call_tool("gazebo_get_simulation_status", {})
        content = json.loads(result["content"][0]["text"])
        if content["success"]:
            is_running = content["data"].get("is_running", False)
            print(f"   Verified: {'✓ Running' if is_running else '✗ Still paused'}")

    # Step 6: Reset simulation
    print_section("6. Reset Simulation")
    print("\nAttempting to reset simulation...")

    # Get time before reset
    result = server.call_tool("gazebo_get_simulation_time", {})
    before_data = json.loads(result["content"][0]["text"])
    if before_data["success"]:
        time_before = before_data["data"].get("simulation_time", 0)
        print(f"   Time before reset: {time_before:.3f} s")

    # Reset
    result = server.call_tool("gazebo_reset_simulation", {
        "timeout": 10.0
    })
    data = print_result(result, indent=1)

    if data:
        # Get time after reset
        time.sleep(0.5)
        result = server.call_tool("gazebo_get_simulation_time", {})
        after_data = json.loads(result["content"][0]["text"])
        if after_data["success"]:
            time_after = after_data["data"].get("simulation_time", 0)
            print(f"   Time after reset: {time_after:.3f} s")

            if time_after < time_before:
                print(f"   ✓ Reset successful (time decreased)")
            else:
                print(f"   ℹ Time check inconclusive")

    # Step 7: Set simulation speed
    print_section("7. Set Simulation Speed")
    print("""
Simulation speed control allows running simulations faster or slower
than real-time. This is useful for:

- **Faster (>1.0)**: Batch testing, learning scenarios
- **Slower (<1.0)**: Debugging, visualization, recording
- **Real-time (1.0)**: Hardware-in-loop, teleoperation

Speed factor examples:
  • 0.5x = Half speed (good for watching details)
  • 1.0x = Real-time (default)
  • 2.0x = Double speed (faster testing)
  • 10.0x = 10x speed (batch simulations)
    """)

    print("\nAttempting to set simulation speed to 2.0x...")

    result = server.call_tool("gazebo_set_simulation_speed", {
        "speed_factor": 2.0
    })
    data = print_result(result, indent=1)

    if data:
        print(f"\n   Requested Speed: {data.get('requested_speed', 2.0)}x")
        if "instructions" in data:
            print(f"\n   Instructions:")
            for instruction in data["instructions"]:
                print(f"     • {instruction}")

    # Step 8: Get world properties
    print_section("8. Get World Properties")
    print("\nQuerying world properties...")

    result = server.call_tool("gazebo_get_world_properties", {})
    data = print_result(result, indent=1)

    if data:
        # Physics properties
        if "physics" in data:
            phys = data["physics"]
            print(f"\n   Physics Properties:")
            if "gravity" in phys:
                g = phys["gravity"]
                print(f"     Gravity:")
                print(f"       x: {g.get('x', 0):.2f} m/s²")
                print(f"       y: {g.get('y', 0):.2f} m/s²")
                print(f"       z: {g.get('z', -9.81):.2f} m/s²")
            if "max_step_size" in phys:
                print(f"     Max Step Size: {phys['max_step_size']} s")
            if "physics_update_rate" in phys:
                print(f"     Update Rate: {phys['physics_update_rate']} Hz")

        # Scene properties
        if "scene" in data:
            scene = data["scene"]
            print(f"\n   Scene Properties:")
            if "ambient" in scene:
                amb = scene["ambient"]
                print(f"     Ambient Light: RGB({amb.get('r', 0):.2f}, "
                      f"{amb.get('g', 0):.2f}, {amb.get('b', 0):.2f})")
            if "background" in scene:
                bg = scene["background"]
                print(f"     Background: RGB({bg.get('r', 0):.2f}, "
                      f"{bg.get('g', 0):.2f}, {bg.get('b', 0):.2f})")
            if "shadows" in scene:
                print(f"     Shadows: {'Enabled' if scene['shadows'] else 'Disabled'}")

    # Step 9: Simulation control workflow
    print_section("9. Simulation Control Workflow")
    print("""
Typical simulation control workflows:

1. **Interactive Development**:
   a) Start simulation
   b) Spawn models/robots
   c) Pause for inspection
   d) Make changes
   e) Unpause to test
   f) Reset when needed

2. **Automated Testing**:
   a) Reset simulation
   b) Spawn test scenario
   c) Set speed to 10.0x
   d) Run test
   e) Collect results
   f) Reset and repeat

3. **Data Collection**:
   a) Load world
   b) Set speed to 1.0x (real-time)
   c) Start recording
   d) Run scenario
   e) Pause for processing
   f) Save data

4. **Debugging**:
   a) Pause at error point
   b) Query world state
   c) Inspect models/sensors
   d) Step slowly (speed 0.1x)
   e) Fix and reset
    """)

    # Step 10: Performance considerations
    print_section("10. Performance Considerations")
    print("""
Simulation performance tips:

**Speed Factors**:
- Real-time factor depends on scene complexity
- Complex physics → Lower achievable speed
- Simple scenes → Can exceed 10x real-time

**Pausing**:
- Pausing is instantaneous
- Use for inspection, not synchronization
- Physics state preserved

**Resetting**:
- Full reset can take several seconds
- Restores initial world state
- Clears all dynamic objects

**Time Queries**:
- Very low overhead (< 1ms)
- Safe to call frequently
- Use for synchronization

**World Properties**:
- Cached on server side
- Infrequent updates recommended
- Query once at startup usually sufficient
    """)

    # Check if in mock mode
    result = server.call_tool("gazebo_get_simulation_status", {})
    content = json.loads(result["content"][0]["text"])
    if content["success"]:
        if not content["data"].get("gazebo_connected", False):
            print_section("11. Working with Real Simulation")
            print("""
ℹ Note: Currently running in MOCK mode

To control real Gazebo simulation:

1. **Start Gazebo**:
   ros2 launch gazebo_ros gazebo.launch.py

2. **Verify connection**:
   ros2 service list | grep gazebo

3. **Re-run this script** to control real simulation

4. **GUI controls** (alternative):
   - Pause/Play button in Gazebo GUI
   - Step button for single-step execution
   - Real-time factor display
            """)

    # Summary
    print_section("Summary")
    print("""
This example demonstrated:
  ✓ Getting simulation status (running, paused, time)
  ✓ Pausing and unpausing simulation
  ✓ Resetting simulation to initial state
  ✓ Querying simulation time and performance
  ✓ Setting simulation speed
  ✓ Getting world properties (physics, scene)

Control workflow:
  1. Query status to understand current state
  2. Pause for inspection or changes
  3. Unpause to continue
  4. Reset when starting new test
  5. Adjust speed for different use cases
  6. Monitor time and performance

Use cases:
  • Development: Pause/unpause for debugging
  • Testing: Reset between tests, speed up execution
  • Learning: Slow down for observation
  • Data collection: Control recording timing

Next steps:
  • Run Example 5 for complete workflow
  • Check examples/README.md for more examples
  • See docs/PHASE4_PLAN.md for advanced features

Note: This example works WITHOUT Gazebo running (mock mode).
      For real control, start Gazebo before running the script.
    """)

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
