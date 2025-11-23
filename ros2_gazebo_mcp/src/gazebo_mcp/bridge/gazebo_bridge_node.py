"""
Gazebo Bridge Node for Gazebo MCP.

ROS2 node that interfaces with Gazebo simulation:
- Service clients for Gazebo services (spawn, delete, get state, etc.)
- Topic subscriptions for sensor data
- Transform listener for TF data
- Action clients for complex operations

This is a CRITICAL component - it provides the actual Gazebo integration.

REFACTORED (Phase 1B): Now uses adapter pattern for dual Gazebo support.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .config import GazeboConfig
from .factory import GazeboAdapterFactory
from .gazebo_interface import GazeboInterface, EntityPose, EntityTwist

from ..utils.exceptions import (
    GazeboNotRunningError,
    GazeboTimeoutError,
    ModelNotFoundError,
    ModelSpawnError,
    ModelDeleteError,
    ROS2ServiceError,
    ROS2TopicError
)
from ..utils.logger import get_logger
from ..utils.converters import pose_to_dict, dict_to_pose
from ..utils.validators import (
    validate_model_name,
    validate_position,
    validate_timeout
)


@dataclass
class ModelState:
    """Model state information."""
    name: str
    pose: Dict[str, Any]
    twist: Optional[Dict[str, Any]] = None
    state: str = "active"


class GazeboBridgeNode:
    """
    ROS2 node for Gazebo simulation interface.

    Provides high-level interface to Gazebo services and topics.

    REFACTORED (Phase 1B): Uses adapter pattern for dual Gazebo backend support.
    - Supports both Classic Gazebo and Modern Gazebo (Fortress/Harmonic)
    - Backend selection via environment variables (GAZEBO_BACKEND)
    - Dependency injection for testing

    Example:
        >>> # Auto-detect backend (default)
        >>> node = GazeboBridgeNode(ros2_node)
        >>>
        >>> # Explicit backend selection
        >>> config = GazeboConfig(backend=GazeboBackend.CLASSIC)
        >>> node = GazeboBridgeNode(ros2_node, config=config)
        >>>
        >>> # Dependency injection for testing
        >>> mock_adapter = MockGazeboAdapter()
        >>> node = GazeboBridgeNode(ros2_node, adapter=mock_adapter)
        >>>
        >>> # Use as before
        >>> models = node.get_model_list()
        >>> node.spawn_entity("turtlebot3", sdf_content, pose)
    """

    def __init__(
        self,
        ros2_node,
        config: Optional[GazeboConfig] = None,
        adapter: Optional[GazeboInterface] = None,
        world: str = "default"
    ):
        """
        Initialize Gazebo bridge node.

        Args:
            ros2_node: ROS2 node instance from ConnectionManager
            config: Gazebo configuration (default: from environment variables)
            adapter: Gazebo adapter (default: auto-created from config via factory)
            world: Default world name for multi-world Modern Gazebo (default: "default")

        Notes:
            - If adapter is provided, config is ignored (for testing)
            - If neither adapter nor config provided, uses environment variables
            - Backend auto-detection happens if GAZEBO_BACKEND=auto
        """
        self.node = ros2_node
        self.logger = get_logger("gazebo_bridge")
        self.world = world  # Default world for operations

        # Adapter pattern (Phase 1B refactor):
        if adapter is not None:
            # Dependency injection (for testing)
            self.adapter = adapter
            self.logger.info(f"Using injected adapter: {adapter.get_backend_name()}")
        else:
            # Production: Create adapter via factory
            if config is None:
                config = GazeboConfig.from_environment()

            factory = GazeboAdapterFactory(ros2_node, config)
            self.adapter = factory.create_adapter()

            self.logger.info(
                f"Initialized Gazebo bridge with {self.adapter.get_backend_name()} backend",
                world=self.world
            )

        # Legacy service clients (DEPRECATED - kept for gradual migration):
        # These will be removed in Phase 3
        self._spawn_entity_client = None
        self._delete_entity_client = None
        self._get_model_list_client = None
        self._get_model_state_client = None
        self._set_model_state_client = None
        self._pause_physics_client = None
        self._unpause_physics_client = None
        self._reset_simulation_client = None
        self._reset_world_client = None

        # Subscribers (still used for compatibility):
        self._model_states_subscriber = None
        self._model_states_data = None

        # TF listener (unchanged):
        self._tf_buffer = None
        self._tf_listener = None

    # Helper methods:

    def _run_async(self, coro):
        """
        Run async adapter method synchronously.

        Args:
            coro: Coroutine to run

        Returns:
            Coroutine result
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _dict_to_entity_pose(self, pose_dict: Dict[str, Any]) -> EntityPose:
        """
        Convert pose dictionary to EntityPose.

        Args:
            pose_dict: Pose as dictionary {position: {x,y,z}, orientation: {x,y,z,w}}

        Returns:
            EntityPose object
        """
        pos = pose_dict.get("position", {})
        orient = pose_dict.get("orientation", {})

        return EntityPose(
            position=(
                pos.get("x", 0.0),
                pos.get("y", 0.0),
                pos.get("z", 0.0)
            ),
            orientation=(
                orient.get("x", 0.0),
                orient.get("y", 0.0),
                orient.get("z", 0.0),
                orient.get("w", 1.0)
            )
        )

    def _dict_to_entity_twist(self, twist_dict: Dict[str, Any]) -> EntityTwist:
        """
        Convert twist dictionary to EntityTwist.

        Args:
            twist_dict: Twist as dictionary {linear: {x,y,z}, angular: {x,y,z}}

        Returns:
            EntityTwist object
        """
        lin = twist_dict.get("linear", {})
        ang = twist_dict.get("angular", {})

        return EntityTwist(
            linear=(
                lin.get("x", 0.0),
                lin.get("y", 0.0),
                lin.get("z", 0.0)
            ),
            angular=(
                ang.get("x", 0.0),
                ang.get("y", 0.0),
                ang.get("z", 0.0)
            )
        )

    # Service client creation (lazy initialization - DEPRECATED):

    def _get_spawn_entity_client(self):
        """Get or create spawn_entity service client."""
        if self._spawn_entity_client is None:
            try:
                from gazebo_msgs.srv import SpawnEntity
                self._spawn_entity_client = self.node.create_client(
                    SpawnEntity,
                    '/spawn_entity'
                )
                self.logger.debug("Created spawn_entity service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/spawn_entity",
                    "Failed to import gazebo_msgs - ensure Gazebo ROS packages are installed"
                ) from e
        return self._spawn_entity_client

    def _get_delete_entity_client(self):
        """Get or create delete_entity service client."""
        if self._delete_entity_client is None:
            try:
                from gazebo_msgs.srv import DeleteEntity
                self._delete_entity_client = self.node.create_client(
                    DeleteEntity,
                    '/delete_entity'
                )
                self.logger.debug("Created delete_entity service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/delete_entity",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._delete_entity_client

    def _get_set_model_state_client(self):
        """Get or create set_model_state service client."""
        if self._set_model_state_client is None:
            try:
                from gazebo_msgs.srv import SetEntityState
                self._set_model_state_client = self.node.create_client(
                    SetEntityState,
                    '/gazebo/set_entity_state'
                )
                self.logger.debug("Created set_entity_state service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._set_model_state_client

    def _get_model_states_subscriber(self):
        """Get or create model_states topic subscriber."""
        if self._model_states_subscriber is None:
            try:
                from gazebo_msgs.msg import ModelStates

                def callback(msg):
                    self._model_states_data = msg

                self._model_states_subscriber = self.node.create_subscription(
                    ModelStates,
                    '/gazebo/model_states',
                    callback,
                    10
                )
                self.logger.debug("Created model_states subscriber")
            except ImportError as e:
                raise ROS2TopicError(
                    "/gazebo/model_states",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._model_states_subscriber

    # Entity management:

    def spawn_entity(
        self,
        name: str,
        xml_content: str,
        pose: Optional[Dict[str, Any]] = None,
        reference_frame: str = "world",
        timeout: float = 10.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Spawn an entity in Gazebo.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            name: Entity name (must be unique)
            xml_content: SDF or URDF XML content
            pose: Spawn pose (position and orientation)
            reference_frame: Reference frame for pose (Classic only, ignored by Modern)
            timeout: Service call timeout (currently ignored, adapter handles timeout)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if spawn successful

        Raises:
            ModelSpawnError: If spawn fails
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running

        Example:
            >>> pose = {
            ...     "position": {"x": 1.0, "y": 2.0, "z": 0.0},
            ...     "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
            ... }
            >>> node.spawn_entity("my_robot", urdf_content, pose)
            >>>
            >>> # Modern Gazebo with specific world
            >>> node.spawn_entity("my_robot", sdf_content, pose, world="world2")
        """
        with self.logger.operation("spawn_entity", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            # Use default world if not specified:
            if world is None:
                world = self.world

            # Convert pose to EntityPose:
            entity_pose = EntityPose(
                position=(0.0, 0.0, 0.0),
                orientation=(0.0, 0.0, 0.0, 1.0)
            )
            if pose:
                entity_pose = self._dict_to_entity_pose(pose)

            # Delegate to adapter:
            try:
                success = self._run_async(
                    self.adapter.spawn_entity(
                        name=name,
                        sdf=xml_content,
                        pose=entity_pose,
                        world=world
                    )
                )

                if success:
                    self.logger.log_model_event("spawned", name, world=world)
                    return True
                else:
                    raise ModelSpawnError(name, "Adapter returned False")

            except Exception as e:
                if isinstance(e, (ModelSpawnError, GazeboTimeoutError, GazeboNotRunningError)):
                    raise
                raise ModelSpawnError(name, f"Adapter call failed: {e}") from e

    def delete_entity(
        self,
        name: str,
        timeout: float = 10.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Delete an entity from Gazebo.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            name: Entity name
            timeout: Service call timeout (currently ignored, adapter handles timeout)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if deletion successful

        Raises:
            ModelDeleteError: If deletion fails
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running

        Example:
            >>> node.delete_entity("my_robot")
            >>> # Modern Gazebo with specific world
            >>> node.delete_entity("my_robot", world="world2")
        """
        with self.logger.operation("delete_entity", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            # Use default world if not specified:
            if world is None:
                world = self.world

            # Delegate to adapter:
            try:
                success = self._run_async(
                    self.adapter.delete_entity(
                        name=name,
                        world=world
                    )
                )

                if success:
                    self.logger.log_model_event("deleted", name, world=world)
                    return True
                else:
                    raise ModelDeleteError(name, "Adapter returned False")

            except Exception as e:
                if isinstance(e, (ModelDeleteError, GazeboTimeoutError, GazeboNotRunningError)):
                    raise
                raise ModelDeleteError(name, f"Adapter call failed: {e}") from e

    def set_entity_state(
        self,
        name: str,
        pose: Optional[Dict[str, Any]] = None,
        twist: Optional[Dict[str, Any]] = None,
        reference_frame: str = "world",
        timeout: float = 10.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Set entity state (pose and/or twist) in Gazebo.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            name: Entity name
            pose: Target pose {position: {x,y,z}, orientation: {x,y,z,w}} or {roll,pitch,yaw}
            twist: Target velocity {linear: {x,y,z}, angular: {x,y,z}}
            reference_frame: Reference frame for pose (Classic only, ignored by Modern)
            timeout: Service call timeout (currently ignored, adapter handles timeout)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if state set successfully

        Raises:
            ModelNotFoundError: If model doesn't exist
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running
            ROS2ServiceError: If service call fails

        Example:
            >>> # Set position only
            >>> node.set_entity_state("robot", pose={"position": {"x": 1, "y": 2, "z": 0.5}})
            >>>
            >>> # Set position and velocity
            >>> node.set_entity_state(
            ...     "robot",
            ...     pose={"position": {"x": 1, "y": 2, "z": 0.5}},
            ...     twist={"linear": {"x": 0.5, "y": 0, "z": 0}}
            ... )
        """
        with self.logger.operation("set_entity_state", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            if pose is None and twist is None:
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    "Must provide either pose or twist (or both)"
                )

            # Use default world if not specified:
            if world is None:
                world = self.world

            # Convert to EntityPose/EntityTwist:
            entity_pose = None
            entity_twist = None

            if pose:
                entity_pose = self._dict_to_entity_pose(pose)

            if twist:
                entity_twist = self._dict_to_entity_twist(twist)

            # Delegate to adapter:
            try:
                success = self._run_async(
                    self.adapter.set_entity_state(
                        name=name,
                        pose=entity_pose,
                        twist=entity_twist,
                        world=world
                    )
                )

                if success:
                    self.logger.log_model_event("state_updated", name, world=world)
                    return True
                else:
                    raise ROS2ServiceError(
                        "/gazebo/set_entity_state",
                        "Adapter returned False"
                    )

            except Exception as e:
                if isinstance(e, (ModelNotFoundError, GazeboTimeoutError, ROS2ServiceError, GazeboNotRunningError)):
                    raise
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    f"Adapter call failed: {e}"
                ) from e

    def get_model_list(
        self,
        timeout: float = 5.0,
        world: Optional[str] = None
    ) -> List[ModelState]:
        """
        Get list of models in Gazebo.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            timeout: Timeout for receiving model states (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            List of ModelState objects

        Raises:
            GazeboNotRunningError: If Gazebo is not running
            GazeboTimeoutError: If timeout exceeded

        Example:
            >>> models = node.get_model_list()
            >>> for model in models:
            ...     print(f"{model.name}: {model.pose}")
        """
        with self.logger.operation("get_model_list"):
            # Validate timeout:
            timeout = validate_timeout(timeout)

            # Use default world if not specified:
            if world is None:
                world = self.world

            # Delegate to adapter (gets entity names only):
            try:
                entity_names = self._run_async(
                    self.adapter.list_entities(world=world)
                )

                # Create ModelState objects with minimal info
                # (full state retrieval would require get_entity_state per model)
                models = []
                for name in entity_names:
                    # Skip ground_plane and other static models:
                    if name == "ground_plane":
                        continue

                    # Get full state for this entity:
                    try:
                        state_dict = self._run_async(
                            self.adapter.get_entity_state(name=name, world=world)
                        )

                        model = ModelState(
                            name=state_dict["name"],
                            pose=state_dict.get("pose", {}),
                            twist=state_dict.get("twist", {}),
                            state="active"
                        )
                        models.append(model)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to get state for entity '{name}'",
                            error=str(e)
                        )
                        # Add minimal ModelState
                        models.append(ModelState(
                            name=name,
                            pose={},
                            twist={},
                            state="unknown"
                        ))

                self.logger.info(f"Retrieved model list", count=len(models), world=world)
                return models

            except Exception as e:
                if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                    raise
                raise GazeboTimeoutError("get_model_list", timeout) from e

    def get_model_state(
        self,
        name: str,
        timeout: float = 5.0,
        world: Optional[str] = None
    ) -> Optional[ModelState]:
        """
        Get state of a specific model.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            name: Model name
            timeout: Timeout for receiving data (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            ModelState object or None if not found

        Example:
            >>> state = node.get_model_state("turtlebot3")
            >>> print(state.pose)
        """
        # Validate parameters:
        name = validate_model_name(name)

        # Use default world if not specified:
        if world is None:
            world = self.world

        # Delegate to adapter:
        try:
            state_dict = self._run_async(
                self.adapter.get_entity_state(name=name, world=world)
            )

            return ModelState(
                name=state_dict["name"],
                pose=state_dict.get("pose", {}),
                twist=state_dict.get("twist", {}),
                state="active"
            )

        except ModelNotFoundError:
            return None
        except Exception as e:
            self.logger.warning(
                f"Failed to get model state",
                model=name,
                error=str(e)
            )
            return None

    # Physics control:

    def pause_physics(
        self,
        timeout: float = 5.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Pause Gazebo physics simulation.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            timeout: Service call timeout (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if successful

        Example:
            >>> node.pause_physics()
        """
        if world is None:
            world = self.world

        try:
            success = self._run_async(
                self.adapter.pause_simulation(world=world)
            )
            if success:
                self.logger.info("Paused physics", world=world)
            return success
        except Exception as e:
            self.logger.error(f"Failed to pause physics", error=str(e))
            return False

    def unpause_physics(
        self,
        timeout: float = 5.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Unpause Gazebo physics simulation.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            timeout: Service call timeout (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if successful

        Example:
            >>> node.unpause_physics()
        """
        if world is None:
            world = self.world

        try:
            success = self._run_async(
                self.adapter.unpause_simulation(world=world)
            )
            if success:
                self.logger.info("Unpaused physics", world=world)
            return success
        except Exception as e:
            self.logger.error(f"Failed to unpause physics", error=str(e))
            return False

    # Simulation control:

    def reset_simulation(
        self,
        timeout: float = 10.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Reset Gazebo simulation to initial state.

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            timeout: Service call timeout (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if successful

        Example:
            >>> node.reset_simulation()
        """
        if world is None:
            world = self.world

        try:
            success = self._run_async(
                self.adapter.reset_simulation(world=world)
            )
            if success:
                self.logger.info("Reset simulation", world=world)
            return success
        except Exception as e:
            self.logger.error(f"Failed to reset simulation", error=str(e))
            return False

    def reset_world(
        self,
        timeout: float = 10.0,
        world: Optional[str] = None
    ) -> bool:
        """
        Reset world to initial state (models + physics).

        REFACTORED (Phase 1B): Uses adapter pattern, supports multi-world.

        Args:
            timeout: Service call timeout (currently ignored)
            world: Target world name (Modern Gazebo only, default: self.world)

        Returns:
            True if successful

        Example:
            >>> node.reset_world()
        """
        if world is None:
            world = self.world

        try:
            success = self._run_async(
                self.adapter.reset_world(world=world)
            )
            if success:
                self.logger.info("Reset world", world=world)
            return success
        except Exception as e:
            self.logger.error(f"Failed to reset world", error=str(e))
            return False

    # TF (Transform) operations:

    def get_transform(
        self,
        target_frame: str,
        source_frame: str,
        timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Get transform between two frames.

        Args:
            target_frame: Target frame name
            source_frame: Source frame name
            timeout: Lookup timeout

        Returns:
            Transform dictionary or None if not available

        Example:
            >>> tf = node.get_transform("map", "base_link")
            >>> print(tf["translation"])
        """
        # Initialize TF listener if needed:
        if self._tf_buffer is None:
            try:
                from tf2_ros import Buffer, TransformListener
                self._tf_buffer = Buffer()
                self._tf_listener = TransformListener(self._tf_buffer, self.node)
                self.logger.debug("Created TF listener")
            except ImportError:
                self.logger.error("tf2_ros not available")
                return None

        # Lookup transform:
        try:
            from rclpy.time import Time, Duration
            transform_stamped = self._tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                Time(),
                timeout=Duration(seconds=timeout)
            )

            # Convert to dictionary:
            from ..utils.converters import transform_to_dict
            return transform_to_dict(transform_stamped.transform)

        except Exception as e:
            self.logger.warning(
                f"Failed to get transform",
                target=target_frame,
                source=source_frame,
                error=str(e)
            )
            return None

    # Sensor data access:

    def subscribe_to_topic(
        self,
        topic_name: str,
        msg_type,
        callback,
        qos_profile=10
    ):
        """
        Subscribe to a ROS2 topic.

        Args:
            topic_name: Topic name
            msg_type: Message type class
            callback: Callback function
            qos_profile: QoS profile

        Returns:
            Subscription object

        Example:
            >>> from sensor_msgs.msg import LaserScan
            >>> def laser_callback(msg):
            ...     print(f"Laser ranges: {len(msg.ranges)}")
            >>> sub = node.subscribe_to_topic("/scan", LaserScan, laser_callback)
        """
        try:
            subscription = self.node.create_subscription(
                msg_type,
                topic_name,
                callback,
                qos_profile
            )
            self.logger.info(f"Subscribed to topic", topic=topic_name)
            return subscription
        except Exception as e:
            raise ROS2TopicError(topic_name, f"Failed to subscribe: {e}") from e

    # Cleanup:

    def destroy(self):
        """Clean up resources."""
        self.logger.info("Destroying Gazebo bridge node")

        # Destroy service clients:
        if self._spawn_entity_client:
            self.node.destroy_client(self._spawn_entity_client)
        if self._delete_entity_client:
            self.node.destroy_client(self._delete_entity_client)

        # Destroy subscribers:
        if self._model_states_subscriber:
            self.node.destroy_subscription(self._model_states_subscriber)


# Example usage:
if __name__ == "__main__":
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    # Initialize ROS2:
    rclpy.init()

    try:
        # Create node:
        node = rclpy.create_node('gazebo_bridge_test')

        # Create bridge:
        bridge = GazeboBridgeNode(node)

        # Get model list:
        print("Getting model list...")
        models = bridge.get_model_list(timeout=5.0)
        print(f"Found {len(models)} models:")
        for model in models:
            print(f"  - {model.name}: {model.pose['position']}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Cleanup:
        bridge.destroy()
        node.destroy_node()
        rclpy.shutdown()
