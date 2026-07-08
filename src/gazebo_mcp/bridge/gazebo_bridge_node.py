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
import queue
import threading
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .config import GazeboConfig
from .factory import GazeboAdapterFactory
from .gazebo_interface import GazeboInterface, EntityPose, EntityTwist

from ..utils.exceptions import (
    ActuationBoundsExceeded,
    GazeboNotRunningError,
    GazeboTimeoutError,
    ModelNotFoundError,
    ModelSpawnError,
    ModelDeleteError,
    ROS2ServiceError,
    ROS2TopicError
)
from ..utils.actuation_bounds import (
    BoundsConfig,
    PersistentWrenchRegistry,
    RateLimiter,
    enforce_wrench,
    enforce_joint,
    enforce_trajectory,
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

        # Stash config (may be None for pure dependency-injection in tests).
        self.config = config

        # Actuation-bounds backstop (P5 hardening — SAFETY-CRITICAL). Enforced
        # inside the actuation methods BEFORE every self.adapter.* call so mock /
        # modern / classic backends, all lean + legacy tools, and direct bridge
        # calls are bounded identically. from_config tolerates self.config is None
        # (-> defaults) so DI/test construction stays safe.
        self._bounds = BoundsConfig.from_config(self.config)
        self._wrench_registry = PersistentWrenchRegistry(
            self._bounds.max_persistent_wrenches
        )
        self._rate_limiter = RateLimiter(self._bounds.rate_limit_hz)

        # World provisioner (P0-B): only when this bridge OWNS its world.
        # Lazy import keeps WorldProvisioner (and its template path resolution)
        # out of the import graph until actually needed.
        self.provisioner = None
        if config is not None and getattr(config, "own_world", False):
            from .world_provisioner import WorldProvisioner
            self.provisioner = WorldProvisioner(config)
            self.logger.info("Created WorldProvisioner (own_world=True)")

        # Persistent async event loop for adapter calls — avoids creating
        # a new event loop on every single bridge call (performance win).
        self._async_loop = asyncio.new_event_loop()
        self._async_thread = threading.Thread(
            target=self._async_loop.run_forever,
            name="gazebo-bridge-async",
            daemon=True,
        )
        self._async_thread.start()

        # Simulation stats cache (populated lazily via /clock subscription)
        self._sim_time_sec: float = 0.0
        self._clock_sub_started: bool = False

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

    def _run_async(self, coro, timeout: float = 30.0):
        """
        Run async adapter method on the persistent background event loop.

        Uses asyncio.run_coroutine_threadsafe so the background loop handles
        all adapter calls sequentially without creating new loops per call.

        Args:
            coro: Coroutine to run
            timeout: Max seconds to wait for result

        Returns:
            Coroutine result

        Raises:
            GazeboTimeoutError: If the call exceeds timeout
        """
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._async_loop)
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise GazeboTimeoutError("async_operation", timeout)

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
                    # F3 (P5 hardening): free any persistent-wrench registry
                    # slot held by this entity — otherwise a deleted entity
                    # permanently occupies a slot under max_persistent_wrenches
                    # even though it no longer exists. Only on a SUCCESSFUL
                    # delete: if delete failed the entity (and its wrench)
                    # still exist, so the slot must stay held.
                    self._wrench_registry.clear(name, world)
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

    # Simulation stats:

    def get_simulation_stats(self) -> Dict[str, Any]:
        """
        Get live simulation time stats from /clock.

        Subscribes to the ROS2 /clock topic on the first call and caches
        the latest sim time. Falls back to zeroes if /clock is unavailable.

        Returns:
            Dict with simulation_time, real_time, paused, iterations
        """
        if not self._clock_sub_started:
            self._clock_sub_started = True
            try:
                from rosgraph_msgs.msg import Clock

                def _clock_cb(msg):
                    self._sim_time_sec = msg.clock.sec + msg.clock.nanosec * 1e-9

                self.node.create_subscription(Clock, "/clock", _clock_cb, 10)
                self.logger.debug("Subscribed to /clock for simulation time")
            except Exception as e:
                self.logger.warning(f"Could not subscribe to /clock: {e}")

        return {
            "simulation_time": self._sim_time_sec,
            "real_time": time.time(),
            "paused": False,
            "iterations": 0,
        }

    # Force/wrench application:

    def apply_wrench(
        self,
        model_name: str,
        force: tuple = (0.0, 0.0, 0.0),
        torque: tuple = (0.0, 0.0, 0.0),
        duration: float = 0.1,
        world: Optional[str] = None,
    ) -> bool:
        """
        Apply a wrench (force + torque) to a model.

        Delegates to adapter.apply_wrench if the adapter supports it
        (ModernGazeboAdapter). Returns False silently for Classic adapter.

        Args:
            model_name: Name of model to push
            force: (fx, fy, fz) in Newtons
            torque: (tx, ty, tz) in Newton-metres
            duration: How long to apply force in seconds
            world: Target world name

        Returns:
            True if wrench applied successfully
        """
        if world is None:
            world = self.world

        # Actuation-bounds backstop BEFORE the adapter call. Placed OUTSIDE the
        # try/except so a strict-mode ActuationBoundsExceeded propagates instead
        # of being swallowed into a False return (non-strict clamps in place).
        force, torque = enforce_wrench(force, torque, duration, False, self._bounds)

        if not hasattr(self.adapter, "apply_wrench"):
            self.logger.warning("Adapter does not support apply_wrench")
            return False

        try:
            return self._run_async(
                self.adapter.apply_wrench(
                    name=model_name,
                    force=force,
                    torque=torque,
                    duration=duration,
                    world=world,
                )
            )
        except Exception as e:
            self.logger.error("Failed to apply wrench", model=model_name, error=str(e))
            return False

    # Simulation timing / physics control (P0-B):

    async def step(
        self, steps: int = 1, world: Optional[str] = None, progress_cb=None
    ) -> Dict[str, Any]:
        """
        Advance the simulation by a fixed number of physics steps.

        Async passthrough to ``adapter.step``. Unlike the legacy sync methods,
        this is awaited directly by the (async) lean tools / FastMCP layer.

        Args:
            steps: Number of physics steps to advance (>= 1)
            world: Target world name (default: self.world)
            progress_cb: Optional async ``(done, total) -> None`` callback for
                cosmetic progress reporting (P5 hardening, F5). Passed straight
                through to the adapter; it must NEVER change the resulting
                physics — see ``mock_adapter.step`` for the contract.

        Returns:
            Dict with at least 'sim_time' and 'steps'.
        """
        if world is None:
            world = self.world
        return await self.adapter.step(steps=steps, world=world, progress_cb=progress_cb)

    async def set_physics(
        self,
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: Optional[str] = None,
    ) -> bool:
        """
        Set physics step size and/or real-time factor (async passthrough).

        Args:
            step_size: Physics step size in seconds (optional)
            rtf: Target real-time factor (optional)
            world: Target world name (default: self.world)

        Returns:
            True if applied (best-effort for real backends).
        """
        if world is None:
            world = self.world
        return await self.adapter.set_physics(
            step_size=step_size, rtf=rtf, world=world
        )

    async def seed(self, value: int, world: Optional[str] = None) -> bool:
        """
        Set the simulation random seed (async passthrough).

        Args:
            value: Seed value
            world: Target world name (default: self.world)

        Returns:
            True if applied (best-effort for real backends).
        """
        if world is None:
            world = self.world
        return await self.adapter.seed(value=value, world=world)

    # Actuation: wrench topic + joint commanding (P1):

    async def apply_wrench_topic(
        self,
        entity: str,
        link: str = "",
        force: tuple = (0.0, 0.0, 0.0),
        torque: tuple = (0.0, 0.0, 0.0),
        duration: float = 0.0,
        persistent: bool = False,
        world: Optional[str] = None,
    ) -> bool:
        """
        Apply a wrench to an entity via the wrench topic (async passthrough).

        Args:
            entity: Entity (model/link) name
            link: Link within the entity ("" = base link)
            force: (fx, fy, fz) in Newtons
            torque: (tx, ty, tz) in Newton-metres
            duration: Duration in seconds (0.0 = single application)
            persistent: If True the wrench persists until cleared
            world: Target world name (default: self.world)

        Returns:
            True if applied/recorded successfully; False if rate-throttled
            (non-strict). In strict mode an over-limit wrench or a throttled call
            raises ActuationBoundsExceeded instead.
        """
        if world is None:
            world = self.world

        # Actuation-bounds backstop BEFORE the adapter call (SAFETY-CRITICAL):
        # 1) per-entity rate limit — throttled => return False (non-strict) or
        #    raise (strict) so a flood cannot reach the adapter.
        if not self._rate_limiter.allow(entity):
            if self._bounds.strict_bounds:
                raise ActuationBoundsExceeded(
                    f"wrench on '{entity}' throttled "
                    f"(> {self._bounds.rate_limit_hz} Hz)",
                    details={"kind": "rate_limit", "entity": entity},
                )
            self.logger.warning("Wrench rate-limited (throttled)", entity=entity)
            return False

        # 2) magnitude caps (clamp in place, or raise in strict mode).
        force, torque = enforce_wrench(force, torque, duration, persistent, self._bounds)

        # 3) persistent-wrench cap — registering a NEW (entity, world) beyond the
        #    cap raises ActuationBoundsExceeded (requires an explicit clear first).
        #    Registered BEFORE the adapter call so an over-cap wrench is rejected
        #    pre-apply.
        if persistent:
            self._wrench_registry.register(entity, world)

        # F4 (P5 hardening): if the adapter call raises, OR returns False (the
        # wrench did not actually take effect), roll back the slot just
        # registered above — otherwise a failed persistent-wrench attempt
        # permanently leaks a cap slot that can never be cleared (clear_wrench
        # has nothing to clear on the backend, but the registry still thinks
        # it is active).
        try:
            ok = await self.adapter.apply_wrench_topic(
                entity=entity,
                link=link,
                force=force,
                torque=torque,
                duration=duration,
                persistent=persistent,
                world=world,
            )
        except Exception:
            if persistent:
                self._wrench_registry.clear(entity, world)
            raise
        if persistent and not ok:
            self._wrench_registry.clear(entity, world)
        return ok

    async def clear_wrench(self, entity: str, world: Optional[str] = None) -> bool:
        """
        Clear a persistent wrench on an entity (async passthrough).

        Args:
            entity: Entity (model/link) name
            world: Target world name (default: self.world)

        Returns:
            True if cleared successfully.
        """
        if world is None:
            world = self.world
        # Free the persistent-wrench registry slot so a later persistent wrench
        # can take its place under the cap (no-op if never registered).
        self._wrench_registry.clear(entity, world)
        return await self.adapter.clear_wrench(entity=entity, world=world)

    async def command_joint(
        self,
        model: str,
        joint: str,
        mode: str,
        value: float,
        world: Optional[str] = None,
        *,
        limits: Optional[Tuple[float, float]] = None,
    ) -> bool:
        """
        Command a single joint in pos/vel/force mode (async passthrough).

        Args:
            model: Model name owning the joint
            joint: Joint name
            mode: One of {"pos", "vel", "force"}
            value: Target value
            world: Target world name (default: self.world)
            limits: Optional ``(lower, upper)`` positional limits for the
                actuation-bounds backstop. Keyword-only and defaulted to None so
                existing callers (e.g. the tool layer, which enforces manifest
                pos limits itself) are unaffected; when supplied, a pos command
                is clamped to (or, in strict mode, rejected against) this range.

        Returns:
            True if applied/recorded successfully. In strict mode an over-limit
            value raises ActuationBoundsExceeded.
        """
        if world is None:
            world = self.world
        # Actuation-bounds backstop BEFORE the adapter call (SAFETY-CRITICAL):
        # vel-mode -> ±max_joint_velocity, force/effort -> ±max_joint_effort,
        # pos -> clamp to `limits` when provided. Clamps in place, or raises in
        # strict mode.
        value = enforce_joint(model, joint, mode, value, limits, self._bounds)
        return await self.adapter.command_joint(
            model=model, joint=joint, mode=mode, value=value, world=world
        )

    async def command_joint_trajectory(
        self,
        model: str,
        points: list,
        world: Optional[str] = None,
        *,
        limits=None,
        joint_names=None,
    ) -> bool:
        """
        Command a joint trajectory for a model (async passthrough).

        Args:
            model: Model name
            points: List of {"positions": [...], "time_from_start": float} dicts
            world: Target world name (default: self.world)
            limits: Optional per-position manifest limits for the actuation-bounds
                backstop — a list aligned to each waypoint's ``positions`` indices,
                each entry ``(lower, upper)`` or ``None`` (no clamp for that index,
                e.g. a continuous joint). Keyword-only and defaulted to None so
                existing callers (the tool layer, which enforces manifest limits
                itself once ``joint_names`` are supplied) are unaffected; when
                supplied, each finite waypoint position is clamped to (or, in
                strict mode, rejected against) its joint's range.
            joint_names: Optional joint names index-aligned to each waypoint's
                ``positions``, forwarded verbatim to the adapter so the real
                controller maps each position to the NAMED joint rather than by
                positional default order. Keyword-only, default None (unchanged
                behaviour for callers that omit it).

        Returns:
            True if applied/recorded successfully. In strict mode an over-limit
            waypoint position raises ActuationBoundsExceeded.

        Raises:
            ActuationBoundsExceeded: If any waypoint position is non-finite
                (NaN/inf), or — in strict mode with ``limits`` supplied — outside
                its joint's range.

        Bounds coverage (P5 hardening; P5-deferred #1 — now COMPLETE for
        waypoints): non-finite (NaN/inf) positions are rejected in BOTH strict
        and non-strict mode; when ``limits`` is supplied each finite waypoint
        position is clamped to its joint's manifest range (non-strict) or raises
        (strict). Without ``limits`` only the non-finite reject runs — the tool
        layer (``actuate_joint_trajectory`` with ``joint_names``) is the primary
        per-waypoint manifest guard, this is the deeper backstop for any direct
        caller. See ``utils/actuation_bounds.enforce_trajectory``.
        """
        if world is None:
            world = self.world
        # Actuation-bounds backstop BEFORE the adapter call (SAFETY-CRITICAL):
        # reject non-finite positions always; clamp (or raise, strict) finite
        # positions to per-joint limits when supplied. Returns clamped points.
        points = enforce_trajectory(
            model, points, limits, self._bounds, joint_names=joint_names
        )
        return await self.adapter.command_joint_trajectory(
            model=model, points=points, world=world, joint_names=joint_names
        )

    # Sensors + parameters (P2):

    async def list_sensors(self, world: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List sensors in the world (async passthrough).

        Args:
            world: Target world name (default: self.world)

        Returns:
            List of sensor descriptor dicts (name/type/model/topic/frame_id/
            active/specs/health).
        """
        if world is None:
            world = self.world
        return await self.adapter.list_sensors(world=world)

    async def sensor_snapshot(
        self, topic: str, world: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the latest typed sample for the sensor at ``topic`` (async passthrough).

        Args:
            topic: Sensor topic (e.g. "/imu", "/scan")
            world: Target world name (default: self.world)

        Returns:
            A typed sample dict (shape depends on sensor type).

        Raises:
            KeyError: If no sensor publishes on ``topic``.
        """
        if world is None:
            world = self.world
        return await self.adapter.sensor_snapshot(topic=topic, world=world)

    async def sensor_camera_image(
        self,
        topic: str,
        resolution: str = "640x480",
        quality: int = 60,
        world: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a single encoded image from the camera at ``topic`` (async passthrough).

        Args:
            topic: Camera image topic (e.g. "/camera/image_raw")
            resolution: Target resolution "WxH" (each dim capped)
            quality: Encoding quality hint (0-100)
            world: Target world name (default: self.world)

        Returns:
            Dict with {"data": bytes, "format", "width", "height"}.

        Raises:
            KeyError: If ``topic`` is not a camera image topic.
        """
        if world is None:
            world = self.world
        return await self.adapter.sensor_camera_image(
            topic=topic, resolution=resolution, quality=quality, world=world
        )

    async def param_list(self, world: Optional[str] = None) -> List[str]:
        """
        List simulation parameter names (async passthrough).

        Args:
            world: Target world name (default: self.world)

        Returns:
            Sorted list of parameter names.
        """
        if world is None:
            world = self.world
        return await self.adapter.param_list(world=world)

    async def param_get(self, name: str, world: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a single parameter's value (async passthrough).

        Args:
            name: Parameter name
            world: Target world name (default: self.world)

        Returns:
            Dict with {"name", "type", "value"}.

        Raises:
            KeyError: If the parameter is unknown.
        """
        if world is None:
            world = self.world
        return await self.adapter.param_get(name=name, world=world)

    async def param_set(
        self, name: str, value: Any, world: Optional[str] = None
    ) -> bool:
        """
        Set (or create) a parameter's value (async passthrough).

        Args:
            name: Parameter name
            value: New value (type inferred from the Python type)
            world: Target world name (default: self.world)

        Returns:
            True if applied successfully.
        """
        if world is None:
            world = self.world
        return await self.adapter.param_set(name=name, value=value, world=world)

    # Joint state reading:

    def get_joint_states(
        self,
        topic_name: str = "/joint_states",
        timeout: float = 2.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Read joint states via a one-shot topic subscription.

        Subscribes to the given topic, waits up to timeout seconds for
        one message, then unsubscribes.

        Args:
            topic_name: ROS2 topic publishing sensor_msgs/JointState
            timeout: Max seconds to wait for data

        Returns:
            Dict with 'joints' list and metadata, or None if no data arrives
        """
        data_queue: queue.Queue = queue.Queue(maxsize=1)

        try:
            from sensor_msgs.msg import JointState

            def _callback(msg):
                try:
                    data_queue.put_nowait(
                        {
                            "joints": [
                                {
                                    "name": name,
                                    "position": float(pos),
                                    "velocity": float(vel),
                                    "effort": float(eff),
                                }
                                for name, pos, vel, eff in zip(
                                    msg.name,
                                    list(msg.position) or [0.0] * len(msg.name),
                                    list(msg.velocity) or [0.0] * len(msg.name),
                                    list(msg.effort) or [0.0] * len(msg.name),
                                )
                            ],
                            "topic": topic_name,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                except Exception:
                    pass

            sub = self.node.create_subscription(JointState, topic_name, _callback, 1)
            try:
                return data_queue.get(timeout=timeout)
            except queue.Empty:
                self.logger.warning(
                    f"No joint state data received from '{topic_name}' "
                    f"within {timeout}s"
                )
                return None
            finally:
                self.node.destroy_subscription(sub)

        except ImportError:
            self.logger.warning("sensor_msgs not available — cannot read joint states")
            return None
        except Exception as e:
            self.logger.warning("Failed to get joint states", topic=topic_name, error=str(e))
            return None

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

        # Shutdown background async loop:
        if self._async_loop.is_running():
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
            self._async_thread.join(timeout=5.0)


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
