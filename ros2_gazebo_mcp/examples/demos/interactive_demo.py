#!/usr/bin/env python3
"""
Interactive CLI Demo

This interactive demonstration allows users to explore MCP server capabilities
through a menu-driven interface. Users can:
- Generate custom worlds
- Spawn and control models
- Monitor sensors
- Run predefined scenarios
- Get help and explanations at each step

Usage:
    python3 interactive_demo.py

Requirements:
    - ROS2 Gazebo MCP Server installed
"""

import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any

# Add src to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.world_generation import WorldGenerator
from gazebo_mcp.tools.model_management import spawn_model, get_model_state, list_models, delete_model
from gazebo_mcp.tools.sensor_tools import get_camera_image, get_lidar_scan
from gazebo_mcp.utils.logger import setup_logger

# Setup logging
logger = setup_logger("interactive_demo", level="INFO")


class InteractiveDemo:
    """Interactive demonstration controller."""

    def __init__(self):
        self.world_generator: Optional[WorldGenerator] = None
        self.spawned_models = []
        self.running = True

    def print_header(self):
        """Print the demo header."""
        print("\n" + "=" * 70)
        print("  ROS2 Gazebo MCP Server - Interactive Demo")
        print("=" * 70)
        print("\nExplore the capabilities of the MCP server through this")
        print("interactive demonstration.")
        print("")

    def print_menu(self):
        """Print the main menu."""
        print("\n" + "-" * 70)
        print("Main Menu:")
        print("-" * 70)
        print("  1. World Generation")
        print("  2. Model Management")
        print("  3. Sensor Monitoring")
        print("  4. Run Complete Scenario")
        print("  5. Help & Information")
        print("  0. Exit")
        print("-" * 70)

    def get_choice(self, prompt: str, valid_choices: list) -> str:
        """Get user choice with validation."""
        while True:
            try:
                choice = input(f"\n{prompt}: ").strip()
                if choice in valid_choices:
                    return choice
                print(f"❌ Invalid choice. Please select from: {', '.join(valid_choices)}")
            except (KeyboardInterrupt, EOFError):
                print("\n\n⚠️  Exiting...")
                sys.exit(0)

    def confirm(self, prompt: str) -> bool:
        """Ask for user confirmation."""
        response = self.get_choice(f"{prompt} (y/n)", ['y', 'n', 'yes', 'no'])
        return response.lower() in ['y', 'yes']

    def pause(self):
        """Pause and wait for user."""
        input("\nPress Enter to continue...")

    def world_generation_menu(self):
        """Handle world generation submenu."""
        while True:
            print("\n" + "=" * 70)
            print("  World Generation")
            print("=" * 70)
            print("\n1. Create simple world")
            print("2. Create world with obstacles")
            print("3. Create world with advanced features")
            print("4. Export current world")
            print("0. Back to main menu")

            choice = self.get_choice("Select option", ['0', '1', '2', '3', '4'])

            if choice == '0':
                break
            elif choice == '1':
                self.create_simple_world()
            elif choice == '2':
                self.create_obstacle_world()
            elif choice == '3':
                self.create_advanced_world()
            elif choice == '4':
                self.export_world()

    def create_simple_world(self):
        """Create a simple world."""
        print("\n📦 Creating Simple World")
        print("-" * 70)

        self.world_generator = WorldGenerator()
        self.world_generator.create_world(
            name="simple_demo_world",
            description="Simple demonstration world"
        )
        print("✅ World created")

        self.world_generator.add_ground_plane(size=(20.0, 20.0))
        print("✅ Ground plane added (20m x 20m)")

        result = self.world_generator.add_light(
            name="sun",
            light_type="directional",
            pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
            intensity=1.0
        )
        print("✅ Sun light added")

        print("\n✨ Simple world ready!")
        self.pause()

    def create_obstacle_world(self):
        """Create a world with obstacles."""
        print("\n🧱 Creating World with Obstacles")
        print("-" * 70)

        # Pattern selection
        print("\nSelect obstacle pattern:")
        print("  1. Maze")
        print("  2. Grid")
        print("  3. Circular")
        print("  4. Random")

        pattern_choice = self.get_choice("Pattern", ['1', '2', '3', '4'])
        patterns = {'1': 'maze', '2': 'grid', '3': 'circular', '4': 'random'}
        pattern = patterns[pattern_choice]

        # Difficulty
        print("\nSelect difficulty:")
        print("  1. Low (easy navigation)")
        print("  2. Medium (moderate challenge)")
        print("  3. High (difficult navigation)")

        diff_choice = self.get_choice("Difficulty", ['1', '2', '3'])
        difficulties = {'1': 'low', '2': 'medium', '3': 'high'}
        difficulty = difficulties[diff_choice]

        # Create world
        self.world_generator = WorldGenerator()
        self.world_generator.create_world(
            name="obstacle_demo_world",
            description=f"{pattern} obstacle course ({difficulty} difficulty)"
        )
        self.world_generator.add_ground_plane(size=(20.0, 20.0))

        print(f"\n⏳ Generating {pattern} obstacle course...")

        result = self.world_generator.add_obstacle_course(
            pattern=pattern,
            difficulty=difficulty,
            num_obstacles=15,
            area_size=(12.0, 12.0),
            center=(0.0, 0.0)
        )

        print(f"✅ Added {result.get('obstacles_added', 15)} obstacles")
        print(f"   Pattern: {pattern}")
        print(f"   Difficulty: {difficulty}")

        self.world_generator.add_light(
            name="sun",
            light_type="directional",
            pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
            intensity=1.0
        )

        print("\n✨ Obstacle world ready!")
        self.pause()

    def create_advanced_world(self):
        """Create a world with advanced features."""
        print("\n✨ Creating World with Advanced Features")
        print("-" * 70)

        self.world_generator = WorldGenerator()
        self.world_generator.create_world(
            name="advanced_demo_world",
            description="Advanced features demonstration"
        )
        self.world_generator.add_ground_plane(size=(20.0, 20.0))

        # Fog
        if self.confirm("Add fog effects?"):
            self.world_generator.add_fog(
                density=0.05,
                color=(0.7, 0.7, 0.8),
                fog_type="exponential"
            )
            print("✅ Fog added")

        # Wind
        if self.confirm("Add wind with turbulence?"):
            self.world_generator.add_wind(
                base_velocity=(2.0, 1.0, 0.0),
                enable_turbulence=True,
                turbulence_intensity=0.3
            )
            print("✅ Wind system added")

        # Animated obstacle
        if self.confirm("Add animated obstacle?"):
            self.world_generator.add_animated_obstacle(
                name="moving_box",
                animation_type="circular",
                center=(0, 0, 1.0),
                radius=3.0,
                duration=8.0,
                loop_mode="repeat",
                model_type="box",
                size=(1.0, 1.0, 1.0)
            )
            print("✅ Animated obstacle added")

        # Trigger zone
        if self.confirm("Add trigger zone?"):
            self.world_generator.add_trigger_zone(
                name="demo_trigger",
                zone_shape="sphere",
                center=(5, 5, 0.5),
                radius=2.0,
                events=["enter", "exit"],
                actions=[{"type": "log", "message": "Robot in zone"}],
                visualize=True
            )
            print("✅ Trigger zone added")

        # Lighting
        self.world_generator.add_light(
            name="sun",
            light_type="directional",
            pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
            intensity=1.0,
            cast_shadows=True,
            shadow_quality="high"
        )
        print("✅ Advanced lighting configured")

        print("\n✨ Advanced world ready!")
        self.pause()

    def export_world(self):
        """Export current world to file."""
        if not self.world_generator:
            print("\n❌ No world created yet. Create a world first.")
            self.pause()
            return

        print("\n💾 Exporting World")
        print("-" * 70)

        default_path = PROJECT_ROOT / "examples/demos/worlds/interactive_world.sdf"
        print(f"\nDefault path: {default_path}")

        if self.confirm("Use default path?"):
            output_path = default_path
        else:
            filename = input("Enter filename (without path): ").strip()
            if not filename.endswith('.sdf'):
                filename += '.sdf'
            output_path = PROJECT_ROOT / "examples/demos/worlds" / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sdf_content = self.world_generator.export_world()
        output_path.write_text(sdf_content)

        print(f"\n✅ World exported to: {output_path}")
        print(f"   Size: {len(sdf_content)} bytes")
        self.pause()

    def model_management_menu(self):
        """Handle model management submenu."""
        while True:
            print("\n" + "=" * 70)
            print("  Model Management")
            print("=" * 70)
            print("\n1. Spawn model")
            print("2. List models")
            print("3. Get model state")
            print("4. Delete model")
            print("0. Back to main menu")

            choice = self.get_choice("Select option", ['0', '1', '2', '3', '4'])

            if choice == '0':
                break
            elif choice == '1':
                self.spawn_model_interactive()
            elif choice == '2':
                self.list_models_interactive()
            elif choice == '3':
                self.get_model_state_interactive()
            elif choice == '4':
                self.delete_model_interactive()

    def spawn_model_interactive(self):
        """Interactively spawn a model."""
        print("\n🚀 Spawn Model")
        print("-" * 70)

        print("\nSelect model type:")
        print("  1. TurtleBot3 Burger")
        print("  2. TurtleBot3 Waffle")
        print("  3. Box")
        print("  4. Sphere")
        print("  5. Cylinder")

        model_choice = self.get_choice("Model type", ['1', '2', '3', '4', '5'])
        model_types = {
            '1': 'turtlebot3_burger',
            '2': 'turtlebot3_waffle',
            '3': 'box',
            '4': 'sphere',
            '5': 'cylinder'
        }
        model_type = model_types[model_choice]

        # Get position
        print("\nEnter position (or press Enter for default [0, 0, 0.5]):")
        pos_input = input("Position (x y z): ").strip()

        if pos_input:
            try:
                x, y, z = map(float, pos_input.split())
                position = [x, y, z]
            except:
                print("⚠️  Invalid input, using default position")
                position = [0, 0, 0.5]
        else:
            position = [0, 0, 0.5]

        # Spawn
        model_name = f"{model_type}_{len(self.spawned_models)}"
        print(f"\n⏳ Spawning {model_name}...")

        result = spawn_model(
            model_name=model_name,
            model_type=model_type,
            pose={
                "position": position,
                "orientation": [0, 0, 0]
            },
            is_static=False
        )

        if result.success:
            self.spawned_models.append(model_name)
            print(f"✅ Model spawned successfully")
            print(f"   Name: {model_name}")
            print(f"   Type: {model_type}")
            print(f"   Position: {position}")
        else:
            print(f"❌ Failed to spawn model: {result.error}")

        self.pause()

    def list_models_interactive(self):
        """List all models."""
        print("\n📋 Listing Models")
        print("-" * 70)

        result = list_models()

        if result.success:
            models = result.data
            if isinstance(models, list) and models:
                print(f"\nFound {len(models)} models:")
                for i, model in enumerate(models, 1):
                    if isinstance(model, dict):
                        name = model.get('name', 'Unknown')
                        print(f"  {i}. {name}")
            else:
                print("\nNo models found in simulation.")
        else:
            print(f"❌ Failed to list models: {result.error}")

        self.pause()

    def get_model_state_interactive(self):
        """Get state of a specific model."""
        if not self.spawned_models:
            print("\n❌ No models spawned yet. Spawn a model first.")
            self.pause()
            return

        print("\n📍 Get Model State")
        print("-" * 70)

        print("\nSpawned models:")
        for i, model in enumerate(self.spawned_models, 1):
            print(f"  {i}. {model}")

        choice = self.get_choice("Select model", [str(i) for i in range(1, len(self.spawned_models) + 1)])
        model_name = self.spawned_models[int(choice) - 1]

        print(f"\n⏳ Getting state of {model_name}...")

        result = get_model_state(model_name=model_name)

        if result.success:
            state = result.data
            print(f"\n✅ Model state retrieved:")
            if isinstance(state, dict):
                pos = state.get('pose', {}).get('position', {})
                print(f"   Position: ({pos.get('x', 0):.3f}, {pos.get('y', 0):.3f}, {pos.get('z', 0):.3f})")
                vel = state.get('twist', {}).get('linear', {})
                print(f"   Velocity: ({vel.get('x', 0):.3f}, {vel.get('y', 0):.3f}, {vel.get('z', 0):.3f})")
        else:
            print(f"❌ Failed to get model state: {result.error}")

        self.pause()

    def delete_model_interactive(self):
        """Delete a model."""
        if not self.spawned_models:
            print("\n❌ No models spawned yet.")
            self.pause()
            return

        print("\n🗑️  Delete Model")
        print("-" * 70)

        print("\nSpawned models:")
        for i, model in enumerate(self.spawned_models, 1):
            print(f"  {i}. {model}")

        choice = self.get_choice("Select model", [str(i) for i in range(1, len(self.spawned_models) + 1)])
        model_name = self.spawned_models[int(choice) - 1]

        if not self.confirm(f"Delete {model_name}?"):
            print("Cancelled.")
            self.pause()
            return

        result = delete_model(model_name=model_name)

        if result.success:
            self.spawned_models.remove(model_name)
            print(f"✅ Model deleted: {model_name}")
        else:
            print(f"❌ Failed to delete model: {result.error}")

        self.pause()

    def sensor_monitoring_menu(self):
        """Handle sensor monitoring submenu."""
        print("\n" + "=" * 70)
        print("  Sensor Monitoring")
        print("=" * 70)
        print("\nThis feature requires a robot with sensors to be spawned.")
        print("Spawn a TurtleBot3 model first from the Model Management menu.")
        self.pause()

    def run_complete_scenario(self):
        """Run a complete predefined scenario."""
        print("\n" + "=" * 70)
        print("  Complete Scenario")
        print("=" * 70)

        print("\nThis will run a complete demonstration scenario:")
        print("  1. Create a world with obstacles")
        print("  2. Spawn a TurtleBot3 robot")
        print("  3. Monitor the robot state")

        if not self.confirm("Run scenario?"):
            return

        print("\n⏳ Running scenario...")
        print("-" * 70)

        # Step 1: Create world
        print("\n[1/3] Creating world...")
        self.world_generator = WorldGenerator()
        self.world_generator.create_world(name="scenario_world", description="Complete scenario")
        self.world_generator.add_ground_plane(size=(15.0, 15.0))
        self.world_generator.add_obstacle_course(
            pattern="grid",
            difficulty="low",
            num_obstacles=8,
            area_size=(10.0, 10.0),
            center=(0.0, 0.0)
        )
        self.world_generator.add_light(
            name="sun",
            light_type="directional",
            pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
            intensity=1.0
        )
        print("✅ World created")

        # Step 2: Spawn robot
        print("\n[2/3] Spawning robot...")
        result = spawn_model(
            model_name="scenario_robot",
            model_type="turtlebot3_burger",
            pose={"position": [0, 0, 0.1], "orientation": [0, 0, 0]},
            is_static=False
        )
        if result.success:
            self.spawned_models.append("scenario_robot")
            print("✅ Robot spawned")
        else:
            print(f"❌ Failed to spawn robot: {result.error}")
            self.pause()
            return

        # Step 3: Monitor state
        print("\n[3/3] Monitoring robot...")
        result = get_model_state(model_name="scenario_robot")
        if result.success:
            print("✅ Robot state monitored")
        else:
            print(f"⚠️  Could not get robot state: {result.error}")

        print("\n✅ Scenario complete!")
        print("\nYou can now:")
        print("  • Use ROS2 to control the robot")
        print("  • Monitor sensors from the Sensor Monitoring menu")
        print("  • Export the world from the World Generation menu")

        self.pause()

    def show_help(self):
        """Show help and information."""
        print("\n" + "=" * 70)
        print("  Help & Information")
        print("=" * 70)

        print("\nROS2 Gazebo MCP Server Capabilities:")
        print("")
        print("• World Generation:")
        print("  - Create worlds with various obstacle patterns")
        print("  - Add advanced features (fog, wind, animations)")
        print("  - Export worlds to SDF format")
        print("")
        print("• Model Management:")
        print("  - Spawn robots and objects")
        print("  - Monitor model state and position")
        print("  - Delete models")
        print("")
        print("• Sensor Monitoring:")
        print("  - Read camera images")
        print("  - Get lidar scan data")
        print("  - Monitor IMU sensors")
        print("")
        print("• Advanced Features:")
        print("  - Animated obstacles")
        print("  - Trigger zones")
        print("  - Environmental effects")
        print("  - Performance metrics")

        print("\nFor more information:")
        print("  • Documentation: docs/")
        print("  • Examples: examples/")
        print("  • Tutorials: docs/tutorials/")

        self.pause()

    def run(self):
        """Run the interactive demo."""
        self.print_header()

        while self.running:
            self.print_menu()
            choice = self.get_choice("Select option", ['0', '1', '2', '3', '4', '5'])

            if choice == '0':
                print("\n👋 Thank you for using the interactive demo!")
                self.running = False
            elif choice == '1':
                self.world_generation_menu()
            elif choice == '2':
                self.model_management_menu()
            elif choice == '3':
                self.sensor_monitoring_menu()
            elif choice == '4':
                self.run_complete_scenario()
            elif choice == '5':
                self.show_help()


def main():
    """Main entry point."""
    try:
        demo = InteractiveDemo()
        demo.run()
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Demo failed")
        print(f"\n❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
