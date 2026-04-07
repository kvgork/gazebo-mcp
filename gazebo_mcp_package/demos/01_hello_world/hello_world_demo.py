#!/usr/bin/env python3
"""Hello World Demo - Simple demonstration of basic Gazebo MCP operations."""
import sys
import os
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import rclpy
from rclpy.node import Node

from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose

from framework import DemoExecutor, DemoValidator, ConfigLoader


class HelloWorldDemo(DemoExecutor):
    """Hello World demo - Basic MCP operations demonstration."""

    def __init__(self, config_path: str):
        """Initialize Hello World demo.

        Args:
            config_path: Path to config.yaml
        """
        super().__init__(
            name="Hello World Demo",
            description="Demonstrates basic Gazebo MCP operations: spawn, move, delete"
        )

        # Load configuration
        self.config = ConfigLoader.load_demo_config(config_path)
        self.adapter: ModernGazeboAdapter = None
        self.node: Node = None

        # Register demo steps
        self._register_steps()

    def _register_steps(self):
        """Register all demo steps."""
        self.register_step(
            name="Validate environment",
            active_name="Validating environment",
            execute=self._step_validate_environment,
            timeout=10.0,
            critical=True
        )

        self.register_step(
            name="Initialize ROS2 and adapter",
            active_name="Initializing ROS2 and adapter",
            execute=self._step_initialize_ros2,
            timeout=15.0,
            critical=True
        )

        self.register_step(
            name="Spawn box model",
            active_name="Spawning box model",
            execute=self._step_spawn_box,
            timeout=30.0,
            critical=True
        )

        self.register_step(
            name="Move box to new position",
            active_name="Moving box to new position",
            execute=self._step_move_box,
            timeout=20.0,
            critical=True
        )

        self.register_step(
            name="Delete box model",
            active_name="Deleting box model",
            execute=self._step_delete_box,
            timeout=20.0,
            critical=True
        )

    async def _step_validate_environment(self) -> dict:
        """Step 1: Validate environment setup."""
        checks = [
            ("ROS2", lambda: DemoValidator.check_command_exists("ros2")),
            ("Gazebo", lambda: DemoValidator.check_command_exists("gz")),
            ("ros_gz_bridge", lambda: DemoValidator.check_ros2_package("ros_gz_bridge")),
            ("Gazebo Process", lambda: DemoValidator.check_gazebo_process()),
        ]

        all_passed, results = DemoValidator.validate_demo_environment(checks)

        if not all_passed:
            raise RuntimeError("Environment validation failed. Please fix issues above.")

        return {"validation_passed": True, "results": results}

    async def _step_initialize_ros2(self) -> dict:
        """Step 2: Initialize ROS2 and create adapter."""
        # Initialize ROS2
        rclpy.init()
        self.node = Node('hello_world_demo_node')

        # Create Modern Gazebo adapter
        self.adapter = ModernGazeboAdapter(
            node=self.node,
            default_world=self.config.gazebo_world,
            timeout=self.config.timeout
        )

        print(f"  └─ Using world: {self.config.gazebo_world}")
        print(f"  └─ Backend: {self.adapter.get_backend_name()}")

        return {"adapter_ready": True, "world": self.config.gazebo_world}

    async def _step_spawn_box(self) -> dict:
        """Step 3: Spawn simple box model."""
        # Get box config from YAML
        box_config = ConfigLoader.get_model_config(self.config, 'hello_box')
        if not box_config:
            raise ValueError("Box configuration not found in config.yaml")

        # Get pose
        pose_dict = box_config['pose']
        pose = EntityPose(
            position=tuple(pose_dict['position']),
            orientation=tuple(pose_dict['orientation'])
        )

        # Generate simple box SDF
        sdf_content = """
        <?xml version="1.0"?>
        <sdf version="1.8">
          <model name="hello_box">
            <static>true</static>
            <link name="link">
              <visual name="visual">
                <geometry>
                  <box><size>1 1 1</size></box>
                </geometry>
                <material>
                  <ambient>0.0 1.0 0.0 1.0</ambient>
                  <diffuse>0.0 1.0 0.0 1.0</diffuse>
                </material>
              </visual>
              <collision name="collision">
                <geometry>
                  <box><size>1 1 1</size></box>
                </geometry>
              </collision>
            </link>
          </model>
        </sdf>
        """

        # Spawn the box
        success = await self.adapter.spawn_entity(
            name="hello_box",
            sdf=sdf_content,
            pose=pose,
            world=self.config.gazebo_world
        )

        if not success:
            raise RuntimeError("Failed to spawn box")

        print(f"  └─ Box spawned at position {pose_dict['position']}")

        return {"spawned": True, "model_name": "hello_box", "pose": pose_dict}

    async def _step_move_box(self) -> dict:
        """Step 4: Move box to new position."""
        # Get new position from config
        box_config = ConfigLoader.get_model_config(self.config, 'hello_box')
        new_position = box_config.get('new_position', [3.0, 1.0, 0.5])

        new_pose = EntityPose(
            position=tuple(new_position),
            orientation=(0.0, 0.0, 0.0, 1.0)
        )

        # Move the box
        success = await self.adapter.set_entity_state(
            name="hello_box",
            pose=new_pose,
            twist=None,
            world=self.config.gazebo_world
        )

        if not success:
            raise RuntimeError("Failed to move box")

        print(f"  └─ Box moved to position {new_position}")

        return {"moved": True, "new_position": new_position}

    async def _step_delete_box(self) -> dict:
        """Step 5: Delete box model."""
        success = await self.adapter.delete_entity(
            name="hello_box",
            world=self.config.gazebo_world
        )

        if not success:
            raise RuntimeError("Failed to delete box")

        print(f"  └─ Box deleted from world")

        return {"deleted": True, "model_name": "hello_box"}

    async def setup(self) -> None:
        """Setup demo environment."""
        # Print config summary
        ConfigLoader.print_config_summary(self.config)
        print()

    async def teardown(self) -> None:
        """Cleanup demo environment."""
        # Shutdown adapter
        if self.adapter:
            self.adapter.shutdown()

        # Shutdown ROS2 node
        if self.node:
            self.node.destroy_node()

        # Shutdown ROS2
        if rclpy.ok():
            rclpy.shutdown()


async def main():
    """Main entry point."""
    # Get config path
    demo_dir = Path(__file__).parent
    config_path = demo_dir / "config.yaml"

    # Create and run demo
    demo = HelloWorldDemo(str(config_path))

    try:
        result = await demo.run_full_demo()

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
