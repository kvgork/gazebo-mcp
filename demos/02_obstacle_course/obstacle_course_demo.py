#!/usr/bin/env python3
"""Obstacle Course Demo - Advanced robot navigation challenge."""
import sys
import os
import asyncio
import math
from pathlib import Path
from typing import Tuple, List

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import rclpy
from rclpy.node import Node

from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose, EntityTwist

from framework import DemoExecutor, DemoValidator, ConfigLoader


class ObstacleCourseDemo(DemoExecutor):
    """Obstacle Course demo - Advanced navigation with physics and collision."""

    def __init__(self, config_path: str):
        """Initialize Obstacle Course demo.

        Args:
            config_path: Path to config.yaml
        """
        super().__init__(
            name="Obstacle Course Challenge",
            description="Navigate robot through waypoints while avoiding obstacles"
        )

        # Load configuration
        self.config = ConfigLoader.load_demo_config(config_path)
        self.adapter: ModernGazeboAdapter = None
        self.node: Node = None

        # Demo state
        self.models_spawned: List[str] = []
        self.current_waypoint_index: int = 0

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
            name="Spawn obstacles (walls)",
            active_name="Spawning obstacles (walls)",
            execute=self._step_spawn_obstacles,
            timeout=45.0,
            critical=True
        )

        self.register_step(
            name="Spawn target zone",
            active_name="Spawning target zone",
            execute=self._step_spawn_target,
            timeout=30.0,
            critical=True
        )

        self.register_step(
            name="Spawn robot",
            active_name="Spawning robot",
            execute=self._step_spawn_robot,
            timeout=30.0,
            critical=True
        )

        self.register_step(
            name="Verify world state",
            active_name="Verifying world state",
            execute=self._step_verify_world,
            timeout=20.0,
            critical=True
        )

        self.register_step(
            name="Navigate to waypoint 1",
            active_name="Navigating to waypoint 1",
            execute=self._step_navigate_waypoint_1,
            timeout=60.0,
            critical=True
        )

        self.register_step(
            name="Navigate to waypoint 2",
            active_name="Navigating to waypoint 2",
            execute=self._step_navigate_waypoint_2,
            timeout=60.0,
            critical=True
        )

        self.register_step(
            name="Navigate to waypoint 3",
            active_name="Navigating to waypoint 3",
            execute=self._step_navigate_waypoint_3,
            timeout=60.0,
            critical=True
        )

        self.register_step(
            name="Reach final target",
            active_name="Reaching final target",
            execute=self._step_reach_target,
            timeout=60.0,
            critical=True
        )

    async def _step_validate_environment(self) -> dict:
        """Step 1: Validate environment setup."""
        checks = [
            ("ROS2", lambda: DemoValidator.check_command_exists("ros2")),
            ("Gazebo", lambda: DemoValidator.check_command_exists("gz")),
            ("ros_gz_bridge", lambda: DemoValidator.check_ros2_package("ros_gz_bridge")),
            ("Gazebo Process", lambda: DemoValidator.check_gazebo_process()),
            ("World File", lambda: DemoValidator.check_file_exists(
                str(Path(__file__).parent / "worlds" / "obstacle_course.sdf"),
                "obstacle_course.sdf"
            )),
            ("Robot Model", lambda: DemoValidator.check_file_exists(
                str(Path(__file__).parent / "models" / "simple_robot.sdf"),
                "simple_robot.sdf"
            )),
        ]

        all_passed, results = DemoValidator.validate_demo_environment(checks)

        if not all_passed:
            raise RuntimeError("Environment validation failed. Please fix issues above.")

        return {"validation_passed": True, "results": results}

    async def _step_initialize_ros2(self) -> dict:
        """Step 2: Initialize ROS2 and create adapter."""
        # Initialize ROS2
        rclpy.init()
        self.node = Node('obstacle_course_demo_node')

        # Create Modern Gazebo adapter
        self.adapter = ModernGazeboAdapter(
            node=self.node,
            default_world=self.config.gazebo_world,
            timeout=self.config.timeout
        )

        print(f"  └─ Using world: {self.config.gazebo_world}")
        print(f"  └─ Backend: {self.adapter.get_backend_name()}")
        print(f"  └─ Timeout: {self.config.timeout}s")

        return {"adapter_ready": True, "world": self.config.gazebo_world}

    async def _step_spawn_obstacles(self) -> dict:
        """Step 3: Spawn wall obstacles."""
        obstacles = ['wall_1', 'wall_2']
        spawned_count = 0

        for obstacle_name in obstacles:
            # Get obstacle config
            obstacle_config = ConfigLoader.get_model_config(self.config, obstacle_name)
            if not obstacle_config:
                raise ValueError(f"Obstacle config not found: {obstacle_name}")

            # Build pose
            pose_dict = obstacle_config['pose']
            pose = EntityPose(
                position=tuple(pose_dict['position']),
                orientation=tuple(pose_dict['orientation'])
            )

            # Build SDF
            geom = obstacle_config['geometry']
            color = obstacle_config['color']
            sdf = self._build_box_sdf(
                obstacle_name,
                geom['size'],
                color,
                static=obstacle_config.get('static', True)
            )

            # Spawn
            success = await self.adapter.spawn_entity(
                name=obstacle_name,
                sdf=sdf,
                pose=pose,
                world=self.config.gazebo_world
            )

            if success:
                self.models_spawned.append(obstacle_name)
                spawned_count += 1
                print(f"  └─ Spawned {obstacle_name} at {pose_dict['position']}")
            else:
                raise RuntimeError(f"Failed to spawn {obstacle_name}")

        return {"obstacles_spawned": spawned_count, "models": obstacles}

    async def _step_spawn_target(self) -> dict:
        """Step 4: Spawn target zone."""
        target_config = ConfigLoader.get_model_config(self.config, 'target')
        if not target_config:
            raise ValueError("Target config not found")

        # Build pose
        pose_dict = target_config['pose']
        pose = EntityPose(
            position=tuple(pose_dict['position']),
            orientation=tuple(pose_dict['orientation'])
        )

        # Build SDF
        geom = target_config['geometry']
        color = target_config['color']
        sdf = self._build_cylinder_sdf(
            'target',
            geom['radius'],
            geom['length'],
            color,
            static=target_config.get('static', True)
        )

        # Spawn
        success = await self.adapter.spawn_entity(
            name='target',
            sdf=sdf,
            pose=pose,
            world=self.config.gazebo_world
        )

        if success:
            self.models_spawned.append('target')
            print(f"  └─ Target zone at {pose_dict['position']}")
        else:
            raise RuntimeError("Failed to spawn target")

        return {"target_spawned": True, "position": pose_dict['position']}

    async def _step_spawn_robot(self) -> dict:
        """Step 5: Spawn robot from SDF file."""
        robot_config = ConfigLoader.get_model_config(self.config, 'robot')
        if not robot_config:
            raise ValueError("Robot config not found")

        # Load robot SDF file
        sdf_path = Path(__file__).parent / robot_config['sdf_file']
        if not sdf_path.exists():
            raise FileNotFoundError(f"Robot SDF not found: {sdf_path}")

        with open(sdf_path, 'r') as f:
            sdf_content = f.read()

        # Build pose
        pose_dict = robot_config['pose']
        pose = EntityPose(
            position=tuple(pose_dict['position']),
            orientation=tuple(pose_dict['orientation'])
        )

        # Spawn
        success = await self.adapter.spawn_entity(
            name='simple_robot',
            sdf=sdf_content,
            pose=pose,
            world=self.config.gazebo_world
        )

        if success:
            self.models_spawned.append('simple_robot')
            print(f"  └─ Robot spawned at {pose_dict['position']}")
        else:
            raise RuntimeError("Failed to spawn robot")

        return {"robot_spawned": True, "position": pose_dict['position']}

    async def _step_verify_world(self) -> dict:
        """Step 6: Verify all models are in world."""
        # Get world properties
        world_info = await self.adapter.get_world_properties(world=self.config.gazebo_world)

        print(f"  └─ World: {world_info.name}")
        print(f"  └─ Models in world: {len(world_info.models)}")

        # Verify our models
        expected_models = ['simple_robot', 'wall_1', 'wall_2', 'target']
        found_models = [m for m in expected_models if m in world_info.models]

        print(f"  └─ Expected models: {len(expected_models)}")
        print(f"  └─ Found models: {len(found_models)}")

        if len(found_models) != len(expected_models):
            missing = set(expected_models) - set(found_models)
            raise RuntimeError(f"Missing models: {missing}")

        return {"models_verified": len(found_models), "world_models": len(world_info.models)}

    async def _step_navigate_waypoint_1(self) -> dict:
        """Step 7: Navigate to waypoint 1."""
        return await self._navigate_to_waypoint(0)

    async def _step_navigate_waypoint_2(self) -> dict:
        """Step 8: Navigate to waypoint 2."""
        return await self._navigate_to_waypoint(1)

    async def _step_navigate_waypoint_3(self) -> dict:
        """Step 9: Navigate to waypoint 3."""
        return await self._navigate_to_waypoint(2)

    async def _step_reach_target(self) -> dict:
        """Step 10: Navigate to final target."""
        return await self._navigate_to_waypoint(3)

    async def _navigate_to_waypoint(self, waypoint_index: int) -> dict:
        """Navigate robot to a specific waypoint.

        Args:
            waypoint_index: Index of waypoint in config

        Returns:
            Dict with navigation result
        """
        robot_config = ConfigLoader.get_model_config(self.config, 'robot')
        waypoints = robot_config['waypoints']

        if waypoint_index >= len(waypoints):
            raise ValueError(f"Invalid waypoint index: {waypoint_index}")

        target_2d = waypoints[waypoint_index]
        target_3d = (target_2d[0], target_2d[1], 0.1)  # Add Z coordinate

        print(f"  └─ Target waypoint: {target_2d}")

        # Get current robot pose
        robot_state = await self.adapter.get_entity_state(
            name='simple_robot',
            world=self.config.gazebo_world
        )

        current_pos = robot_state['pose']['position']
        print(f"  └─ Current position: ({current_pos[0]:.2f}, {current_pos[1]:.2f})")

        # Calculate distance
        distance = math.sqrt(
            (target_3d[0] - current_pos[0])**2 +
            (target_3d[1] - current_pos[1])**2
        )
        print(f"  └─ Distance: {distance:.2f}m")

        # Move robot (simplified - just teleport for demo)
        # In real scenario, this would involve velocity commands and gradual movement
        new_pose = EntityPose(
            position=target_3d,
            orientation=(0.0, 0.0, 0.0, 1.0)
        )

        success = await self.adapter.set_entity_state(
            name='simple_robot',
            pose=new_pose,
            twist=None,
            world=self.config.gazebo_world
        )

        if not success:
            raise RuntimeError(f"Failed to move robot to waypoint {waypoint_index}")

        print(f"  └─ Reached waypoint {waypoint_index + 1}")

        return {
            "waypoint_reached": waypoint_index,
            "position": target_3d,
            "distance_traveled": distance
        }

    def _build_box_sdf(self, name: str, size: List[float], color: List[float], static: bool = True) -> str:
        """Build SDF for box geometry.

        Args:
            name: Model name
            size: Box dimensions [x, y, z]
            color: RGBA color [r, g, b, a]
            static: Whether model is static

        Returns:
            SDF XML string
        """
        return f"""
        <?xml version="1.0"?>
        <sdf version="1.8">
          <model name="{name}">
            <static>{"true" if static else "false"}</static>
            <link name="link">
              <visual name="visual">
                <geometry>
                  <box><size>{size[0]} {size[1]} {size[2]}</size></box>
                </geometry>
                <material>
                  <ambient>{color[0]} {color[1]} {color[2]} {color[3]}</ambient>
                  <diffuse>{color[0]} {color[1]} {color[2]} {color[3]}</diffuse>
                </material>
              </visual>
              <collision name="collision">
                <geometry>
                  <box><size>{size[0]} {size[1]} {size[2]}</size></box>
                </geometry>
              </collision>
            </link>
          </model>
        </sdf>
        """

    def _build_cylinder_sdf(self, name: str, radius: float, length: float, color: List[float], static: bool = True) -> str:
        """Build SDF for cylinder geometry.

        Args:
            name: Model name
            radius: Cylinder radius
            length: Cylinder length
            color: RGBA color [r, g, b, a]
            static: Whether model is static

        Returns:
            SDF XML string
        """
        return f"""
        <?xml version="1.0"?>
        <sdf version="1.8">
          <model name="{name}">
            <static>{"true" if static else "false"}</static>
            <link name="link">
              <visual name="visual">
                <geometry>
                  <cylinder>
                    <radius>{radius}</radius>
                    <length>{length}</length>
                  </cylinder>
                </geometry>
                <material>
                  <ambient>{color[0]} {color[1]} {color[2]} {color[3]}</ambient>
                  <diffuse>{color[0]} {color[1]} {color[2]} {color[3]}</diffuse>
                </material>
              </visual>
              <collision name="collision">
                <geometry>
                  <cylinder>
                    <radius>{radius}</radius>
                    <length>{length}</length>
                  </cylinder>
                </geometry>
              </collision>
            </link>
          </model>
        </sdf>
        """

    async def setup(self) -> None:
        """Setup demo environment."""
        # Print config summary
        ConfigLoader.print_config_summary(self.config)
        print()

    async def teardown(self) -> None:
        """Cleanup demo environment."""
        # Delete all spawned models
        print("Cleaning up spawned models...")
        for model_name in self.models_spawned:
            try:
                await self.adapter.delete_entity(
                    name=model_name,
                    world=self.config.gazebo_world
                )
                print(f"  └─ Deleted {model_name}")
            except Exception as e:
                print(f"  └─ Warning: Failed to delete {model_name}: {e}")

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
    demo = ObstacleCourseDemo(str(config_path))

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
