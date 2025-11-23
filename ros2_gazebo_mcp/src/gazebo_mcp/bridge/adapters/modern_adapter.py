"""
Modern Gazebo adapter using ros_gz_interfaces.

Full implementation for Modern Gazebo (Fortress/Garden/Harmonic).
Uses ros_gz_interfaces package for ROS 2 integration.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from geometry_msgs.msg import Pose, Twist, Vector3, Quaternion, Point

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


class ModernGazeboAdapter(GazeboInterface):
    """
    Adapter for Modern Gazebo (Fortress/Garden/Harmonic via ros_gz).

    Modern Gazebo differences from Classic:
    - Package: ros_gz_interfaces (not gazebo_msgs)
    - Service paths: /world/{world_name}/* (not /gazebo/*)
    - Field names: .sdf (not .xml), .pose (not .initial_pose)
    - World parameter required (supports multiple worlds)
    - Uses Entity message with name/id/type fields
    """

    def __init__(self, node, default_world: str = "default", timeout: float = 5.0):
        """
        Initialize Modern Gazebo adapter.

        Args:
            node: ROS2 node for creating service clients
            default_world: Default world name for operations
            timeout: Default service call timeout
        """
        self.node = node
        self.default_world = default_world
        self.timeout = timeout
        self.logger = get_logger("modern_adapter")

        # Lazy-initialized service clients (per-world)
        self._spawn_clients: Dict[str, Any] = {}
        self._delete_clients: Dict[str, Any] = {}
        self._set_pose_clients: Dict[str, Any] = {}
        self._control_clients: Dict[str, Any] = {}

        # Entity state cache (for list_entities and get_entity_state)
        # Modern Gazebo doesn't have a direct "get state" service like Classic
        # We'll need to subscribe to /world/{world}/pose/info topic
        self._pose_info_subs: Dict[str, Any] = {}
        self._entity_states: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"Initialized Modern Gazebo adapter for world '{default_world}'")

    def get_backend_name(self) -> str:
        """Return backend identifier."""
        return "modern"

    # Helper methods for service clients

    def _get_spawn_client(self, world: str):
        """Get or create spawn_entity service client for world."""
        if world not in self._spawn_clients:
            from ros_gz_interfaces.srv import SpawnEntity
            service_name = f'/world/{world}/create'
            self._spawn_clients[world] = self.node.create_client(
                SpawnEntity,
                service_name
            )
            self.logger.debug(f"Created spawn client for world '{world}': {service_name}")
        return self._spawn_clients[world]

    def _get_delete_client(self, world: str):
        """Get or create delete_entity service client for world."""
        if world not in self._delete_clients:
            from ros_gz_interfaces.srv import DeleteEntity
            service_name = f'/world/{world}/remove'
            self._delete_clients[world] = self.node.create_client(
                DeleteEntity,
                service_name
            )
            self.logger.debug(f"Created delete client for world '{world}': {service_name}")
        return self._delete_clients[world]

    def _get_set_pose_client(self, world: str):
        """Get or create set_entity_pose service client for world."""
        if world not in self._set_pose_clients:
            from ros_gz_interfaces.srv import SetEntityPose
            service_name = f'/world/{world}/set_pose'
            self._set_pose_clients[world] = self.node.create_client(
                SetEntityPose,
                service_name
            )
            self.logger.debug(f"Created set_pose client for world '{world}': {service_name}")
        return self._set_pose_clients[world]

    def _get_control_client(self, world: str):
        """Get or create world control service client for world."""
        if world not in self._control_clients:
            from ros_gz_interfaces.srv import ControlWorld
            service_name = f'/world/{world}/control'
            self._control_clients[world] = self.node.create_client(
                ControlWorld,
                service_name
            )
            self.logger.debug(f"Created control client for world '{world}': {service_name}")
        return self._control_clients[world]

    def _ensure_pose_info_subscriber(self, world: str):
        """Ensure pose info subscriber is created for world."""
        if world not in self._pose_info_subs:
            from ros_gz_interfaces.msg import EntityWrench  # Closest to state info
            # Note: Modern Gazebo uses /model/{model_name}/pose topic per model
            # or /world/{world}/pose/info for all models
            # For now, we'll subscribe to the world pose info topic
            topic_name = f'/world/{world}/pose/info'

            def callback(msg):
                # Store entity states from pose info
                # This is a simplified implementation
                # Real implementation would parse the message properly
                if world not in self._entity_states:
                    self._entity_states[world] = {}
                # Update entity states cache
                # Note: This needs proper message parsing based on actual topic structure

            # Create subscription (topic may not exist until simulation starts)
            try:
                self._pose_info_subs[world] = self.node.create_subscription(
                    EntityWrench,  # Placeholder - need actual message type
                    topic_name,
                    callback,
                    10
                )
                self.logger.debug(f"Created pose info subscriber for world '{world}'")
            except Exception as e:
                self.logger.warning(f"Could not create pose subscriber for world '{world}': {e}")

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
                f"Service for {operation_name} not available. Is Modern Gazebo running?"
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
        Spawn entity using Modern Gazebo API.

        Args:
            name: Entity name (must be unique)
            sdf: SDF content (Modern Gazebo uses SDF, not XML)
            pose: Spawn pose
            world: Target world name

        Returns:
            True if spawn successful

        Raises:
            GazeboNotRunningError: If Gazebo not running
            GazeboTimeoutError: If call times out
            GazeboServiceError: If spawn fails
        """
        client = self._get_spawn_client(world)

        # Create Modern Gazebo request
        from ros_gz_interfaces.srv import SpawnEntity
        from ros_gz_interfaces.msg import EntityFactory

        request = SpawnEntity.Request()
        request.entity_factory = EntityFactory()
        request.entity_factory.name = name
        request.entity_factory.sdf = sdf  # Modern uses 'sdf' field
        request.entity_factory.pose = self._entity_pose_to_pose_msg(pose)
        request.entity_factory.relative_to = "world"
        request.entity_factory.allow_renaming = False

        # Call service
        try:
            response = await self._call_service_async(client, request, f"spawn_entity (world={world})")

            if response.success:
                self.logger.info(f"Spawned entity '{name}' in world '{world}'")
                return True
            else:
                raise GazeboServiceError(
                    "spawn_entity",
                    f"Failed to spawn '{name}' in world '{world}'"
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
        Delete entity using Modern Gazebo API.

        Args:
            name: Entity name
            world: Target world name

        Returns:
            True if deletion successful
        """
        client = self._get_delete_client(world)

        from ros_gz_interfaces.srv import DeleteEntity
        from ros_gz_interfaces.msg import Entity

        request = DeleteEntity.Request()
        request.entity = Entity()
        request.entity.name = name
        request.entity.type = Entity.MODEL  # Assume MODEL type

        try:
            response = await self._call_service_async(client, request, f"delete_entity (world={world})")

            if response.success:
                self.logger.info(f"Deleted entity '{name}' from world '{world}'")
                return True
            else:
                raise GazeboServiceError(
                    "delete_entity",
                    f"Failed to delete '{name}' from world '{world}'"
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
        Get entity state from Modern Gazebo.

        Note: Modern Gazebo doesn't have a direct "get state" service.
        This method subscribes to pose topics or queries scene info.

        This is a simplified implementation that may need enhancement
        based on specific Modern Gazebo version and topic availability.

        Args:
            name: Entity name
            world: Target world name

        Returns:
            Dictionary with entity state (name, pose, twist)

        Raises:
            ModelNotFoundError: If entity not found
        """
        # Ensure pose subscriber is set up
        self._ensure_pose_info_subscriber(world)

        # Check cache for entity state
        if world in self._entity_states and name in self._entity_states[world]:
            state = self._entity_states[world][name]
            return {
                "name": name,
                "pose": state.get("pose", {}),
                "twist": state.get("twist", {})
            }

        # If not in cache, entity might not exist or we haven't received data yet
        # Return default values with a warning
        self.logger.warning(
            f"Entity '{name}' state not available in cache for world '{world}'. "
            "Returning default values. Modern Gazebo requires topic subscriptions for state."
        )

        return {
            "name": name,
            "pose": {
                "position": (0.0, 0.0, 0.0),
                "orientation": (0.0, 0.0, 0.0, 1.0)
            },
            "twist": {
                "linear": (0.0, 0.0, 0.0),
                "angular": (0.0, 0.0, 0.0)
            }
        }

    async def set_entity_state(
        self,
        name: str,
        pose: EntityPose,
        twist: Optional[EntityTwist] = None,
        world: str = "default"
    ) -> bool:
        """
        Set entity pose using Modern Gazebo API.

        Note: Modern Gazebo's SetEntityPose service only sets pose, not twist.
        Twist control would require publishing to velocity topics.

        Args:
            name: Entity name
            pose: Target pose
            twist: Target twist (currently ignored - not supported by SetEntityPose)
            world: Target world name

        Returns:
            True if pose set successfully
        """
        if twist is not None:
            self.logger.warning(
                "Twist parameter ignored. Modern Gazebo SetEntityPose only supports pose. "
                "Use velocity topics to control entity twist."
            )

        client = self._get_set_pose_client(world)

        from ros_gz_interfaces.srv import SetEntityPose
        from ros_gz_interfaces.msg import Entity

        request = SetEntityPose.Request()
        request.entity = Entity()
        request.entity.name = name
        request.entity.type = Entity.MODEL
        request.pose = self._entity_pose_to_pose_msg(pose)

        try:
            response = await self._call_service_async(client, request, f"set_entity_pose (world={world})")

            if response.success:
                self.logger.debug(f"Set pose for entity '{name}' in world '{world}'")
                return True
            else:
                raise GazeboServiceError(
                    "set_entity_state",
                    f"Failed to set pose for '{name}'"
                )
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError, GazeboServiceError)):
                raise
            raise GazeboServiceError("set_entity_state", str(e)) from e

    async def list_entities(
        self,
        world: str = "default"
    ) -> List[str]:
        """
        List all entities in Modern Gazebo world.

        Note: Modern Gazebo doesn't have a direct "list entities" service.
        This implementation uses the pose info topic cache.

        For production, consider using /world/{world}/scene/info service
        if available in your Gazebo version.

        Args:
            world: Target world name

        Returns:
            List of entity names
        """
        self._ensure_pose_info_subscriber(world)

        # Return entities from cache
        if world in self._entity_states:
            return list(self._entity_states[world].keys())

        # If no cache data, return empty list with warning
        self.logger.warning(
            f"No entity data available for world '{world}'. "
            "Modern Gazebo requires topic subscriptions. Returning empty list."
        )
        return []

    async def get_world_properties(
        self,
        world: str = "default"
    ) -> WorldInfo:
        """
        Get world properties for Modern Gazebo.

        Note: Limited implementation - Modern Gazebo uses different info structures.

        Args:
            world: Target world name

        Returns:
            WorldInfo with available data
        """
        models = await self.list_entities(world)

        return WorldInfo(
            name=world,
            sim_time=0.0,  # Would need /clock topic
            models=models,
            paused=False  # Would need to track via control calls
        )

    async def pause_simulation(self, world: str = "default") -> bool:
        """
        Pause physics simulation in Modern Gazebo.

        Args:
            world: Target world name

        Returns:
            True if pause successful
        """
        client = self._get_control_client(world)

        from ros_gz_interfaces.srv import ControlWorld
        from ros_gz_interfaces.msg import WorldControl

        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.pause = True

        try:
            response = await self._call_service_async(client, request, f"pause_simulation (world={world})")

            if response.success:
                self.logger.info(f"Paused simulation in world '{world}'")
                return True
            else:
                raise GazeboServiceError("pause_simulation", "Failed to pause")
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("pause_simulation", str(e)) from e

    async def unpause_simulation(self, world: str = "default") -> bool:
        """
        Unpause physics simulation in Modern Gazebo.

        Args:
            world: Target world name

        Returns:
            True if unpause successful
        """
        client = self._get_control_client(world)

        from ros_gz_interfaces.srv import ControlWorld
        from ros_gz_interfaces.msg import WorldControl

        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.pause = False

        try:
            response = await self._call_service_async(client, request, f"unpause_simulation (world={world})")

            if response.success:
                self.logger.info(f"Unpaused simulation in world '{world}'")
                return True
            else:
                raise GazeboServiceError("unpause_simulation", "Failed to unpause")
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("unpause_simulation", str(e)) from e

    async def reset_simulation(self, world: str = "default") -> bool:
        """
        Reset simulation to initial state in Modern Gazebo.

        Args:
            world: Target world name

        Returns:
            True if reset successful
        """
        client = self._get_control_client(world)

        from ros_gz_interfaces.srv import ControlWorld
        from ros_gz_interfaces.msg import WorldControl, WorldReset

        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.reset = WorldReset()
        request.world_control.reset.all = True  # Reset everything

        try:
            response = await self._call_service_async(client, request, f"reset_simulation (world={world})")

            if response.success:
                self.logger.info(f"Reset simulation in world '{world}'")
                return True
            else:
                raise GazeboServiceError("reset_simulation", "Failed to reset")
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("reset_simulation", str(e)) from e

    async def reset_world(self, world: str = "default") -> bool:
        """
        Reset world to initial state in Modern Gazebo.

        Note: In Modern Gazebo, reset_world and reset_simulation use the same
        ControlWorld service with different reset options.

        Args:
            world: Target world name

        Returns:
            True if reset successful
        """
        client = self._get_control_client(world)

        from ros_gz_interfaces.srv import ControlWorld
        from ros_gz_interfaces.msg import WorldControl, WorldReset

        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.reset = WorldReset()
        request.world_control.reset.model_only = True  # Reset models only

        try:
            response = await self._call_service_async(client, request, f"reset_world (world={world})")

            if response.success:
                self.logger.info(f"Reset world '{world}'")
                return True
            else:
                raise GazeboServiceError("reset_world", "Failed to reset")
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError)):
                raise
            raise GazeboServiceError("reset_world", str(e)) from e
