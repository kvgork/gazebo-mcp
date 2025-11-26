#!/usr/bin/env python3
"""
Example 4: World Manipulation

Demonstrates:
- Loading and saving world files
- Querying world properties
- Setting world properties
- Understanding world configuration

Prerequisites:
- Optional: Gazebo running
- Optional: Custom world SDF file

Usage:
    python3 examples/04_world_manipulation.py
"""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import world_tools, simulation_tools


def main():
    """Run world manipulation example."""

    print("=" * 60)
    print("Example 4: World Manipulation")
    print("=" * 60)
    print()

    # Step 1: Get current world properties
    print("Step 1: Getting world properties...")
    result = world_tools.get_world_properties(response_format="summary")

    if result.success and result.data:
        print(f"✓ World properties retrieved")
        props = result.data.get('properties', {})
        print(f"  - Simulation time: {props.get('sim_time', 0):.2f}s")
        print(f"  - Paused: {props.get('paused', False)}")
        print(f"  - Model count: {props.get('model_count', 0)}")

        if props.get('mock_data'):
            print(f"  - Mode: MOCK (simulated world)")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 2: Set world property
    print("Step 2: Setting world property (gravity)...")
    result = world_tools.set_world_property(
        property_name="gravity",
        value=[0.0, 0.0, -9.81]  # Standard Earth gravity
    )

    if result.success:
        print(f"✓ Gravity set to standard Earth value")
        if result.data:
            print(f"  - New value: {result.data.get('value', 'N/A')}")
    else:
        print(f"  Note: {result.error}")

    print()

    # Step 3: Get simulation time
    print("Step 3: Getting simulation time...")
    result = simulation_tools.get_simulation_time()

    if result.success and result.data:
        sim_time = result.data.get('simulation_time', 0.0)
        real_time = result.data.get('real_time', 0.0)
        print(f"✓ Time retrieved")
        print(f"  - Simulation time: {sim_time:.2f}s")
        print(f"  - Real time: {real_time:.2f}s")
        if sim_time > 0 and real_time > 0:
            factor = sim_time / real_time
            print(f"  - Real-time factor: {factor:.2f}x")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 4: Set simulation speed
    print("Step 4: Setting simulation speed to 2x...")
    result = simulation_tools.set_simulation_speed(speed_factor=2.0)

    if result.success:
        print(f"✓ Simulation speed set to 2.0x")
        if result.data:
            print(f"  - New speed: {result.data.get('speed_factor', 1.0)}x")
    else:
        print(f"  Note: {result.error}")

    print()

    # Step 5: Save world configuration
    print("Step 5: Saving current world...")
    save_path = "worlds/my_saved_world.sdf"
    result = world_tools.save_world(
        file_path=save_path,
        overwrite=True
    )

    if result.success:
        print(f"✓ World saved")
        if result.data:
            print(f"  - File path: {result.data.get('file_path', 'N/A')}")
            print(f"  - Model count: {result.data.get('model_count', 0)}")
    else:
        print(f"  Note: {result.error}")

    print()

    # Step 6: Reset simulation
    print("Step 6: Resetting simulation...")
    result = simulation_tools.reset_simulation()

    if result.success:
        print(f"✓ Simulation reset to initial state")
        if result.data:
            print(f"  - Time reset: {result.data.get('reset_time', False)}")
            print(f"  - Models reset: {result.data.get('reset_models', False)}")
    else:
        print(f"  Note: {result.error}")

    print()
    print("=" * 60)
    print("Example completed!")
    print()
    print("What you learned:")
    print("  - How to query world properties")
    print("  - How to modify world settings (gravity, speed)")
    print("  - How to save world state to SDF file")
    print("  - How to reset simulations")
    print()
    print("World properties you can modify:")
    print("  - gravity: [x, y, z] acceleration vector")
    print("  - simulation_speed: Real-time factor multiplier")
    print("  - physics_engine: Solver configuration")
    print()
    print("Next steps:")
    print("  - Create custom world SDF files")
    print("  - Experiment with different gravity settings")
    print("  - Save and load complex scenarios")
    print("  - Combine with Examples 1-3 for complete workflows")
    print("=" * 60)


if __name__ == "__main__":
    main()
