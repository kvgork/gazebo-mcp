"""
Classic Gazebo adapter using gazebo_msgs.

Wraps Classic Gazebo (Gazebo 11) ROS2 integration.

⚠️  DEPRECATION WARNING ⚠️
This adapter is DEPRECATED and will be removed in v2.0.0.
Please migrate to Modern Gazebo (Fortress/Garden/Harmonic) using ModernGazeboAdapter.

Classic Gazebo 11 is no longer actively maintained. Modern Gazebo provides:
- Better performance
- Multi-world support
- Modern ROS 2 integration (ros_gz)
- Active development and support
"""

import time
import warnings
from typing import Dict, List, Optional, Any
from geometry_msgs.msg import Pose, Twist, Vector3, Quaternion, Point

# Issue deprecation warning at module import
warnings.warn(
    "ClassicGazeboAdapter is deprecated and will be removed in v2.0.0. "
    "Please migrate to Modern Gazebo (Fortress/Garden/Harmonic) using ModernGazeboAdapter.",
    DeprecationWarning,
    stacklevel=2
)

from ..gazebo_interface import (
    GazeboInterface,
    EntityPose,
    EntityTwist,
    WorldInfo
)
from ...utils.exceptions import (
    GazeboNotRunningError,
    GazeboTimeoutError,
    GazeboServiceError,
    ModelNotFoundError,
)
from ...utils.logger import get_logger


class ClassicGazeboAdapter(GazeboInterface):
    """
    Adapter for Gazebo Classic (gazebo_msgs).

    ⚠️  DEPRECATED: This adapter will be removed in v2.0.0.
    Use ModernGazeboAdapter for Modern Gazebo (Fortress/Garden/Harmonic).

    Maps GazeboInterface methods to Classic Gazebo service calls.
    Classic uses:
    - Package: gazebo_msgs
    - Service paths: /gazebo/* and /spawn_entity, /delete_entity
    - Field names: .xml (not .sdf), .initial_pose (not .pose)
    - Single world only (world parameter ignored)
    """

    def __init__(self, node, timeout: float = 5.0):
        """
        Initialize Classic Gazebo adapter.

        ⚠️  DEPRECATION WARNING: Classic Gazebo support will be removed in v2.0.0.

        Args:
            node: ROS2 node for creating service clients
            timeout: Default service call timeout
        """
        self.node = node
        self.timeout = timeout
        self.logger = get_logger("classic_adapter")

        # Issue runtime deprecation warning
        self.logger.warning(
            "⚠️  Classic Gazebo adapter is DEPRECATED and will be removed in v2.0.0. "
            "Please migrate to Modern Gazebo (Fortress/Garden/Harmonic). "
            "Set GAZEBO_BACKEND=modern to use the Modern adapter."
        )

        # Lazy-initialized service clients
        self._spawn_client = None
        self._delete_client = None
        self._set_state_client = None
        self._get_world_properties_client = None
        self._pause_client = None
        self._unpause_client = None
        self._reset_simulation_client = None
        self._reset_world_client = None

        # Model states subscriber
        self._model_states_sub = None
        self._model_states_data = None

        self.logger.info("Initialized Classic Gazebo adapter (DEPRECATED)")

    def get_backend_name(self) -> str:
        """Return backend identifier."""
        return "classic"

    # Helper methods for service clients

    def _get_spawn_client(self):
        """Get or create spawn_entity service client."""
        if self._spawn_client is None:
            from gazebo_msgs.srv import SpawnEntity
            self._spawn_client = self.node.create_client(
                SpawnEntity,
                '/spawn_entity'
            )
        return self._spawn_client

    def _get_delete_client(self):
        """Get or create delete_entity service client."""
        if self._delete_client is None:
            from gazebo_msgs.srv import DeleteEntity
            self._delete_client = self.node.create_client(
                DeleteEntity,
                '/delete_entity'
            )
        return self._delete_client

    def _get_set_state_client(self):
        """Get or create set_entity_state service client."""
        if self._set_state_client is None:
            from gazebo_msgs.srv import SetEntityState
            self._set_state_client = self.node.create_client(
                SetEntityState,
                '/gazebo/set_entity_state'
            )
        return self._set_state_client

    def _get_pause_client(self):
        """Get or create pause_physics service client."""
        if self._pause_client is None:
            from std_srvs.srv import Empty
            self._pause_client = self.node.create_client(
                Empty,
                '/gazebo/pause_physics'
            )
        return self._pause_client

    def _get_unpause_client(self):
        """Get or create unpause_physics service client."""
        if self._unpause_client is None:
            from std_srvs.srv import Empty
            self._unpause_client = self.node.create_client(
                Empty,
                '/gazebo/unpause_physics'
            )
        return self._unpause_client

    def _get_reset_simulation_client(self):
        """Get or create reset_simulation service client."""
        if self._reset_simulation_client is None:
            from std_srvs.srv import Empty
            self._reset_simulation_client = self.node.create_client(
                Empty,
                '/gazebo/reset_simulation'
            )
        return self._reset_simulation_client

    def _get_reset_world_client(self):
        """Get or create reset_world service client."""
        if self._reset_world_client is None:
            from std_srvs.srv import Empty
            self._reset_world_client = self.node.create_client(
                Empty,
                '/gazebo/reset_world'
            )
        return self._reset_world_client

    def _ensure_model_states_subscriber(self):
        """Ensure model_states subscriber is created."""
        if self._model_states_sub is None:
            from gazebo_msgs.msg import ModelStates

            def callback(msg):
                self._model_states_data = msg

            self._model_states_sub = self.node.create_subscription(
                ModelStates,
                '/gazebo/model_states',
                callback,
                10
            )

    # Helper conversion methods

    def _entity_pose_to_pose_msg(self, entity_pose: EntityPose) -> Pose:
        """Convert EntityPose to geometry_msgs/Pose."""
        pose = Pose()
        pose.position = Point(
            x=float(entity_pose.position[0]),
            y=float(entity_pose.position[1]),
            z=float(entity_pose.position[2])
        )
        pose.orientation = Quaternion(
            x=float(entity_pose.orientation[0]),
            y=float(entity_pose.orientation[1]),
            z=float(entity_pose.orientation[2]),
            w=float(entity_pose.orientation[3])
        )
        return pose

    def _entity_twist_to_twist_msg(self, entity_twist: EntityTwist) -> Twist:
        """Convert EntityTwist to geometry_msgs/Twist."""
        twist = Twist()
        twist.linear = Vector3(
            x=float(entity_twist.linear[0]),
            y=float(entity_twist.linear[1]),
            z=float(entity_twist.linear[2])
        )
        twist.angular = Vector3(
            x=float(entity_twist.angular[0]),
            y=float(entity_twist.angular[1]),
            z=float(entity_twist.angular[2])
        )
        return twist

    async def _call_service_async(self, client, request, operation_name: str):
        """
        Call ROS2 service asynchronously with timeout.

        Args:
            client: Service client
            request: Service request
            operation_name: Name for logging/errors

        Returns:
            Service response

        Raises:
            GazeboNotRunningError: If service not available
            GazeboTimeoutError: If call times out
            GazeboServiceError: If call fails
        """
        # Wait for service
        if not client.wait_for_service(timeout_sec=self.timeout):
            raise GazeboNotRunningError(
                f"Service for {operation_name} not available. Is Gazebo running?"
            )

        # Call service
        future = client.call_async(request)

        # Wait for response with timeout
        start_time = time.time()
        while not future.done():
            if time.time() - start_time > self.timeout:
                raise GazeboTimeoutError(operation_name, self.timeout)
            await asyncio.sleep(0.01)

        return future.result()

    # GazeboInterface implementation

    async def spawn_entity(
        self,
        name: str,
        sdf: str,
        pose: EntityPose,
        world: str = "default"
    ) -> bool:
        """
        Spawn entity using Classic Gazebo API.

        Note: 'world' parameter ignored (Classic supports single world only).
        """
        import asyncio

        client = self._get_spawn_client()

        # Create Classic-format request
        from gazebo_msgs.srv import SpawnEntity
        request = SpawnEntity.Request()
        request.name = name
        request.xml = sdf  # Classic uses 'xml' field
        request.initial_pose = self._entity_pose_to_pose_msg(pose)
        request.reference_frame = "world"
        request.robot_namespace = ""

        # Call service
        try:
            response = await self._call_service_async(client, request, "spawn_entity")

            if response.success:
                self.logger.info(f"Spawned entity '{name}'")
                return True
            else:
                raise GazeboServiceError(
                    "spawn_entity",
                    f"Failed to spawn '{name}': {response.status_message}"
                )
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError, GazeboServiceError)):
                raise
            raise GazeboServiceError("spawn_entity", str(e)) from e

    async def delete_entity(
        self,
        name: str,
        world: str = "default"
    ) -> bool:
        """
        Delete entity using Classic Gazebo API.

        Note: 'world' parameter ignored.
        """
        import asyncio

        client = self._get_delete_client()

        from gazebo_msgs.srv import DeleteEntity
        request = DeleteEntity.Request()
        request.name = name

        try:
            response = await self._call_service_async(client, request, "delete_entity")

            if response.success:
                self.logger.info(f"Deleted entity '{name}'")
                return True
            else:
                raise GazeboServiceError(
                    "delete_entity",
                    f"Failed to delete '{name}': {response.status_message}"
                )
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError, GazeboServiceError)):
                raise
            raise GazeboServiceError("delete_entity", str(e)) from e

    async def get_entity_state(
        self,
        name: str,
        world: str = "default"
    ) -> Dict[str, Any]:
        """
        Get entity state from model_states topic.

        Note: Classic doesn't have a get_entity_state service,
        we read from /gazebo/model_states topic.
        """
        self._ensure_model_states_subscriber()

        # Wait for data
        import asyncio
        max_wait = 2.0
        start = time.time()
        while self._model_states_data is None:
            if time.time() - start > max_wait:
                raise GazeboTimeoutError("get_model_states", max_wait)
            await asyncio.sleep(0.01)

        # Find model in list
        try:
            idx = self._model_states_data.name.index(name)
        except ValueError:
            raise ModelNotFoundError(name)

        # Extract pose and twist
        pose_msg = self._model_states_data.pose[idx]
        twist_msg = self._model_states_data.twist[idx]

        return {
            "name": name,
            "pose": {
                "position": (pose_msg.position.x, pose_msg.position.y, pose_msg.position.z),
                "orientation": (pose_msg.orientation.x, pose_msg.orientation.y,
                               pose_msg.orientation.z, pose_msg.orientation.w)
            },
            "twist": {
                "linear": (twist_msg.linear.x, twist_msg.linear.y, twist_msg.linear.z),
                "angular": (twist_msg.angular.x, twist_msg.angular.y, twist_msg.angular.z)
            }
        }

    async def set_entity_state(
        self,
        name: str,
        pose: EntityPose,
        twist: Optional[EntityTwist] = None,
        world: str = "default"
    ) -> bool:
        """Set entity state using Classic Gazebo API."""
        import asyncio

        client = self._get_set_state_client()

        from gazebo_msgs.srv import SetEntityState
        from gazebo_msgs.msg import EntityState

        request = SetEntityState.Request()
        request.state = EntityState()
        request.state.name = name
        request.state.pose = self._entity_pose_to_pose_msg(pose)
        request.state.reference_frame = "world"

        if twist:
            request.state.twist = self._entity_twist_to_twist_msg(twist)

        try:
            response = await self._call_service_async(client, request, "set_entity_state")

            if response.success:
                self.logger.debug(f"Set state for entity '{name}'")
                return True
            else:
                raise GazeboServiceError(
                    "set_entity_state",
                    f"Failed: {response.status_message}"
                )
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError, GazeboServiceError)):
                raise
            raise GazeboServiceError("set_entity_state", str(e)) from e

    async def list_entities(
        self,
        world: str = "default"
    ) -> List[str]:
        """List all entities from model_states topic."""
        self._ensure_model_states_subscriber()

        # Wait for data
        import asyncio
        max_wait = 2.0
        start = time.time()
        while self._model_states_data is None:
            if time.time() - start > max_wait:
                raise GazeboTimeoutError("get_model_states", max_wait)
            await asyncio.sleep(0.01)

        return list(self._model_states_data.name)

    async def get_world_properties(
        self,
        world: str = "default"
    ) -> WorldInfo:
        """Get world properties (limited in Classic)."""
        models = await self.list_entities(world)

        return WorldInfo(
            name=world,  # Classic doesn't report world name
            sim_time=0.0,  # Would need /clock topic
            models=models,
            paused=False  # Would need to track state
        )

    async def pause_simulation(self, world: str = "default") -> bool:
        """Pause physics simulation."""
        import asyncio

        client = self._get_pause_client()

        from std_srvs.srv import Empty
        request = Empty.Request()

        try:
            await self._call_service_async(client, request, "pause_physics")
            self.logger.info("Paused simulation")
            return True
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("pause_physics", str(e)) from e

    async def unpause_simulation(self, world: str = "default") -> bool:
        """Unpause physics simulation."""
        import asyncio

        client = self._get_unpause_client()

        from std_srvs.srv import Empty
        request = Empty.Request()

        try:
            await self._call_service_async(client, request, "unpause_physics")
            self.logger.info("Unpaused simulation")
            return True
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("unpause_physics", str(e)) from e

    async def reset_simulation(self, world: str = "default") -> bool:
        """Reset simulation to initial state."""
        import asyncio

        client = self._get_reset_simulation_client()

        from std_srvs.srv import Empty
        request = Empty.Request()

        try:
            await self._call_service_async(client, request, "reset_simulation")
            self.logger.info("Reset simulation")
            return True
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("reset_simulation", str(e)) from e

    async def reset_world(self, world: str = "default") -> bool:
        """Reset world to initial state."""
        import asyncio

        client = self._get_reset_world_client()

        from std_srvs.srv import Empty
        request = Empty.Request()

        try:
            await self._call_service_async(client, request, "reset_world")
            self.logger.info("Reset world")
            return True
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("reset_world", str(e)) from e
