#!/usr/bin/env python3
"""
Example 1: Basic Simulation

Demonstrates:
- Listing available models in the simulation
- Getting simulation status
- Basic simulation control (pause/unpause)

This example works in both modes:
- With Gazebo running: Uses real simulation data
- Without Gazebo: Uses mock data for demonstration

Prerequisites:
- None (works without Gazebo for learning)
- Optional: Start Gazebo with `gz sim` for real testing

Usage:
    python3 examples/01_basic_simulation.py
"""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import simulation_tools, model_management


def main():
    """Run basic simulation example."""

    print("=" * 60)
    print("Example 1: Basic Simulation Control")
    print("=" * 60)
    print()

    # Step 1: Get simulation status
    print("Step 1: Getting simulation status...")
    result = simulation_tools.get_simulation_status()

    if result.success:
        print(f"✓ Simulation status retrieved")
        if result.data:
            print(f"  - Paused: {result.data.get('paused', 'unknown')}")
            print(f"  - Time: {result.data.get('simulation_time', 'unknown')}")
            if result.data.get('mock_data'):
                print(f"  - Mode: MOCK (Gazebo not running)")
            else:
                print(f"  - Mode: REAL (Connected to Gazebo)")
    else:
        print(f"✗ Failed: {result.error}")
        return

    print()

    # Step 2: List all models
    print("Step 2: Listing models in simulation...")
    result = model_management.list_models(response_format="summary")

    if result.success:
        print(f"✓ Models retrieved")
        if result.data:
            models = result.data.get('models', [])
            print(f"  - Total models: {len(models)}")
            print(f"  - Model names: {[m.get('name', 'unknown') for m in models[:5]]}")
            if len(models) > 5:
                print(f"    ... and {len(models) - 5} more")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 3: Pause simulation
    print("Step 3: Pausing simulation...")
    result = simulation_tools.pause_simulation()

    if result.success:
        print(f"✓ Simulation paused")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 4: Get simulation time
    print("Step 4: Getting simulation time...")
    result = simulation_tools.get_simulation_time()

    if result.success:
        if result.data:
            time_val = result.data.get('simulation_time', 0.0)
            print(f"✓ Simulation time: {time_val:.2f} seconds")
    else:
        print(f"✗ Failed: {result.error}")

    print()

    # Step 5: Unpause simulation
    print("Step 5: Unpausing simulation...")
    result = simulation_tools.unpause_simulation()

    if result.success:
        print(f"✓ Simulation unpaused")
    else:
        print(f"✗ Failed: {result.error}")

    print()
    print("=" * 60)
    print("Example completed!")
    print()
    print("Next steps:")
    print("  - Run with real Gazebo: `gz sim` then run this script")
    print("  - Try Example 2: TurtleBot3 spawning")
    print("  - Explore the source code in src/gazebo_mcp/tools/")
    print("=" * 60)


if __name__ == "__main__":
    main()
