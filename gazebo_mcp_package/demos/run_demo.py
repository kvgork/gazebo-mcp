#!/usr/bin/env python3
"""Unified demo launcher for all Gazebo MCP demonstrations."""
import sys
import os
import argparse
import asyncio
from pathlib import Path
from typing import Optional

# Add paths
DEMOS_DIR = Path(__file__).parent
sys.path.insert(0, str(DEMOS_DIR))
sys.path.insert(0, str(DEMOS_DIR.parent / 'src'))


def list_available_demos():
    """List all available demos."""
    demos = {
        '1': {
            'name': 'Hello World',
            'path': '01_hello_world',
            'script': 'hello_world_demo.py',
            'description': 'Simple demonstration of basic Gazebo MCP operations',
            'duration': '~10 seconds',
            'difficulty': 'Beginner'
        },
        '2': {
            'name': 'Obstacle Course',
            'path': '02_obstacle_course',
            'script': 'obstacle_course_demo.py',
            'description': 'Advanced robot navigation through obstacle course',
            'duration': '~25 seconds',
            'difficulty': 'Intermediate'
        }
    }
    return demos


def print_demo_menu():
    """Print interactive demo menu."""
    print("=" * 70)
    print("  Gazebo MCP Demo Launcher")
    print("=" * 70)
    print()
    print("Available Demos:")
    print()

    demos = list_available_demos()
    for demo_id, demo_info in demos.items():
        print(f"  [{demo_id}] {demo_info['name']}")
        print(f"      {demo_info['description']}")
        print(f"      Duration: {demo_info['duration']} | Difficulty: {demo_info['difficulty']}")
        print()

    print("=" * 70)


async def run_demo(demo_id: str) -> int:
    """Run a specific demo.

    Args:
        demo_id: Demo identifier ('1' or '2')

    Returns:
        Exit code (0 for success)
    """
    demos = list_available_demos()

    if demo_id not in demos:
        print(f"Error: Invalid demo ID '{demo_id}'")
        print(f"Valid options: {', '.join(demos.keys())}")
        return 1

    demo_info = demos[demo_id]
    demo_dir = DEMOS_DIR / demo_info['path']
    demo_script = demo_dir / demo_info['script']

    if not demo_script.exists():
        print(f"Error: Demo script not found: {demo_script}")
        return 1

    print(f"\nLaunching: {demo_info['name']}")
    print(f"Script: {demo_script}")
    print()

    # Import and run demo
    sys.path.insert(0, str(demo_dir))

    if demo_id == '1':
        from hello_world_demo import main as demo_main
    elif demo_id == '2':
        from obstacle_course_demo import main as demo_main
    else:
        print(f"Error: Demo {demo_id} not implemented")
        return 1

    # Run demo
    try:
        await demo_main()
        return 0
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nDemo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def print_setup_instructions(demo_id: str):
    """Print setup instructions for a demo.

    Args:
        demo_id: Demo identifier
    """
    demos = list_available_demos()

    if demo_id not in demos:
        print(f"Error: Invalid demo ID '{demo_id}'")
        return

    demo_info = demos[demo_id]
    demo_dir = DEMOS_DIR / demo_info['path']

    print("=" * 70)
    print(f"  Setup Instructions: {demo_info['name']}")
    print("=" * 70)
    print()

    if demo_id == '1':
        print("Hello World Demo Setup:")
        print()
        print("1. Start Modern Gazebo:")
        print("   gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf")
        print()
        print("2. In new terminal, start ros_gz_bridge:")
        print("   ros2 run ros_gz_bridge parameter_bridge \\")
        print('     "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \\')
        print('     "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \\')
        print('     "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \\')
        print('     "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"')
        print()
        print("3. Wait 2-3 seconds, then run demo:")
        print(f"   {sys.argv[0]} --run 1")

    elif demo_id == '2':
        setup_script = demo_dir / "setup.sh"
        print("Obstacle Course Demo Setup:")
        print()
        print("Option A: Automated Setup (Recommended)")
        print(f"   cd {demo_dir}")
        print("   ./setup.sh")
        print("   # Then run demo from setup terminal")
        print()
        print("Option B: Manual Setup")
        print("   See README.md in:")
        print(f"   {demo_dir / 'README.md'}")

    print()
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Gazebo MCP Demo Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive menu
  %(prog)s

  # Run specific demo
  %(prog)s --run 1

  # List all demos
  %(prog)s --list

  # Show setup instructions
  %(prog)s --setup 2
        """
    )

    parser.add_argument(
        '--run',
        type=str,
        metavar='DEMO_ID',
        help='Run specific demo by ID (1, 2, etc.)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available demos'
    )

    parser.add_argument(
        '--setup',
        type=str,
        metavar='DEMO_ID',
        help='Show setup instructions for demo'
    )

    args = parser.parse_args()

    # Handle list command
    if args.list:
        print_demo_menu()
        return 0

    # Handle setup command
    if args.setup:
        print_setup_instructions(args.setup)
        return 0

    # Handle run command
    if args.run:
        exit_code = asyncio.run(run_demo(args.run))
        return exit_code

    # Interactive mode
    print_demo_menu()
    print()
    demo_id = input("Select demo to run (1-2, or 'q' to quit): ").strip()

    if demo_id.lower() in ['q', 'quit', 'exit']:
        print("Exiting...")
        return 0

    exit_code = asyncio.run(run_demo(demo_id))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
