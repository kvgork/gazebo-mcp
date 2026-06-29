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
        """
        Ensure a pose-info subscriber is created for the given world.

        Subscribes to ``/world/{world}/pose/info`` using ``tf2_msgs/msg/TFMessage``.
        The ros_gz_bridge maps Gazebo's ``gz.msgs.Pose_V`` on that topic to a
        TFMessage where each entity is a ``TransformStamped``:
            - ``child_frame_id``  -> entity (model/link) name
            - ``transform.translation`` -> position (x, y, z)
            - ``transform.rotation``     -> orientation quaternion (x, y, z, w)

        The callback parses every transform and caches it in
        ``self._entity_states[world][child_frame_id]`` as
        ``{"pose": {"position": [...], "orientation": [...]}}``.

        The ``tf2_msgs`` import is LAZY (function-level) so importing this module
        never pulls ``tf2_msgs`` at module load — required for the ``-e dev``
        environment which has no tf2/ros_gz packages.
        """
        if world not in self._pose_info_subs:
            from tf2_msgs.msg import TFMessage

            topic_name = f'/world/{world}/pose/info'

            def callback(msg, _world=world):
                if _world not in self._entity_states:
                    self._entity_states[_world] = {}
                for tf in msg.transforms:
                    t = tf.transform.translation
                    r = tf.transform.rotation
                    self._entity_states[_world][tf.child_frame_id] = {
                        "pose": {
                            "position": [t.x, t.y, t.z],
                            "orientation": [r.x, r.y, r.z, r.w],
                        }
                    }

            try:
                self._pose_info_subs[world] = self.node.create_subscription(
                    TFMessage,
                    topic_name,
                    callback,
                    10,
                )
                self.logger.debug(
                    f"Created pose info subscriber for world '{world}' on {topic_name}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Could not create pose subscriber for world '{world}': {e}"
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

    async def _call_service_async(self, client, request, operation_name: str):
        """
        Call ROS2 service asynchronously with timeout.

        The blocking rclpy.spin_until_future_complete() runs in a thread-pool
        executor so it does not block the shared event loop thread.

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
        import rclpy

        # Wait for service (blocking but fast, acceptable before dispatching)
        if not client.wait_for_service(timeout_sec=self.timeout):
            raise GazeboNotRunningError(
                f"Service for {operation_name} not available. Is Modern Gazebo running?"
            )

        # Submit async call
        future = client.call_async(request)

        # Run the blocking spin in a thread pool so the event loop stays responsive
        loop = asyncio.get_event_loop()

        def _spin():
            rclpy.spin_until_future_complete(self.node, future, timeout_sec=self.timeout)

        await loop.run_in_executor(None, _spin)

        if not future.done():
            raise GazeboTimeoutError(operation_name, self.timeout)

        exception = future.exception()
        if exception is not None:
            raise GazeboServiceError(operation_name, str(exception)) from exception

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
        Get entity state (pose) from Modern Gazebo.

        Modern Gazebo has no direct "get state" service. State is published on
        ``/world/{world}/pose/info`` (bridged as ``tf2_msgs/msg/TFMessage``).
        This method ensures the subscriber exists, spins the node briefly so a
        fresh sample can arrive, then reads the cached pose for ``name``.

        Twist is not published on the pose-info topic, so it is returned as
        zeros — P0 only fixes pose readback (twist lands with a velocity topic
        subscription in a later slice).

        Args:
            name: Entity name (matches the TransformStamped child_frame_id)
            world: Target world name

        Returns:
            Dictionary with entity state (name, pose, twist)

        Raises:
            ModelNotFoundError: If entity not found after the brief wait
        """
        import rclpy

        # Ensure pose subscriber is set up.
        self._ensure_pose_info_subscriber(world)

        def _cached():
            states = self._entity_states.get(world, {})
            return states.get(name)

        # Spin briefly (off the event-loop thread) to let a pose sample arrive.
        # Poll the cache between short spins so we return as soon as data lands.
        loop = asyncio.get_event_loop()

        def _spin_until_present():
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if _cached() is not None:
                    return
                rclpy.spin_once(self.node, timeout_sec=0.05)

        await loop.run_in_executor(None, _spin_until_present)

        state = _cached()
        if state is None:
            raise ModelNotFoundError(name)

        return {
            "name": name,
            "pose": state.get("pose", {}),
            "twist": state.get(
                "twist",
                {"linear": [0.0, 0.0, 0.0], "angular": [0.0, 0.0, 0.0]},
            ),
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

        Uses the /world/{world}/scene/info service via gz or ign CLI.
        Tries gz (Gazebo Garden/Harmonic) first, then ign (Fortress/older).

        Args:
            world: Target world name

        Returns:
            List of entity names (top-level models only)
        """
        import subprocess
        import re

        service_name = f'/world/{world}/scene/info'

        # Try gz (newer) then ign (older Ignition Gazebo)
        for cli, req_type, rep_type in [
            ('gz',  'gz.msgs.Empty',         'gz.msgs.Scene'),
            ('ign', 'ignition.msgs.Empty',   'ignition.msgs.Scene'),
        ]:
            try:
                result = subprocess.run(
                    [cli, 'service', '-s', service_name,
                     '--reqtype', req_type,
                     '--reptype', rep_type,
                     '--timeout', '2000', '--req', ''],
                    capture_output=True,
                    text=True,
                    timeout=5.0
                )

                if result.returncode != 0 or not result.stdout.strip():
                    continue

                # Extract top-level model names.
                # Scene proto output looks like:
                #   model {
                #     name: "turtlebot3_burger"
                #     ...
                #   }
                # We collect the name following each top-level "model {" block.
                models = []
                lines = result.stdout.split('\n')

                for i, line in enumerate(lines):
                    stripped = line.lstrip()
                    indent = len(line) - len(stripped)

                    # Top-level model blocks have indent 0 or 2
                    if stripped.startswith('model {') and indent <= 2:
                        for j in range(i + 1, min(i + 5, len(lines))):
                            name_match = re.search(r'^\s*name:\s*"([^"]+)"', lines[j])
                            if name_match:
                                models.append(name_match.group(1))
                                break

                if models:
                    self.logger.debug(
                        f"Found {len(models)} models via {cli} in world '{world}': {models}"
                    )
                    return models

            except FileNotFoundError:
                # CLI not installed, try next
                continue
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout querying scene info via {cli} for world '{world}'")
                continue
            except Exception as e:
                self.logger.warning(f"Error listing entities via {cli}: {e}")
                continue

        self.logger.warning(
            f"Could not list entities for world '{world}' — "
            "neither gz nor ign CLI produced results"
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

    async def apply_wrench(
        self,
        name: str,
        force: tuple = (0.0, 0.0, 0.0),
        torque: tuple = (0.0, 0.0, 0.0),
        duration: float = 0.1,
        world: str = "default",
    ) -> bool:
        """
        Apply wrench (force + torque) to a model link.

        Uses the /world/{world}/apply_link_wrench service from ros_gz_interfaces.

        Args:
            name: Model name (wrench applied to base link)
            force: (fx, fy, fz) in Newtons (world frame)
            torque: (tx, ty, tz) in Newton-metres (world frame)
            duration: Duration in seconds
            world: Target world name

        Returns:
            True if wrench applied successfully
        """
        try:
            from ros_gz_interfaces.srv import ApplyLinkWrench
            from geometry_msgs.msg import Wrench, Vector3

            service_name = f"/world/{world}/apply_link_wrench"
            if not hasattr(self, "_wrench_clients"):
                self._wrench_clients: Dict[str, Any] = {}

            if world not in self._wrench_clients:
                self._wrench_clients[world] = self.node.create_client(
                    ApplyLinkWrench, service_name
                )
                self.logger.debug(f"Created wrench client for world '{world}'")

            client = self._wrench_clients[world]

            request = ApplyLinkWrench.Request()
            request.entity_name = name
            request.link_name = ""  # empty = base link
            request.wrench = Wrench(
                force=Vector3(x=float(force[0]), y=float(force[1]), z=float(force[2])),
                torque=Vector3(x=float(torque[0]), y=float(torque[1]), z=float(torque[2])),
            )
            request.duration.sec = int(duration)
            request.duration.nanosec = int((duration % 1) * 1_000_000_000)

            response = await self._call_service_async(client, request, "apply_link_wrench")
            return getattr(response, "success", True)

        except ImportError:
            self.logger.warning(
                "ros_gz_interfaces not available — cannot apply wrench. "
                "Install: sudo apt install ros-$ROS_DISTRO-ros-gz-interfaces"
            )
            return False
        except Exception as e:
            self.logger.warning(f"apply_wrench failed: {e}")
            return False

    # --- Simulation timing / physics control (P0-B) ---

    async def step(self, steps: int = 1, world: str = "default") -> Dict[str, Any]:
        """
        Advance the simulation by a fixed number of physics steps.

        Uses the ``/world/{world}/control`` service (ros_gz_interfaces/srv/
        ControlWorld) with ``world_control.pause=True`` and
        ``world_control.multi_step=steps`` — i.e. step exactly ``steps`` ticks
        while keeping the world paused (deterministic stepping).

        Args:
            steps: Number of physics steps to advance (>= 1)
            world: Target world name

        Returns:
            Dict with 'steps' executed and a best-effort 'sim_time'.
        """
        if steps < 1:
            raise ValueError("steps must be >= 1")

        client = self._get_control_client(world)

        from ros_gz_interfaces.srv import ControlWorld
        from ros_gz_interfaces.msg import WorldControl

        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.pause = True
        request.world_control.multi_step = int(steps)

        try:
            response = await self._call_service_async(
                client, request, f"step (world={world})"
            )
            if not getattr(response, "success", True):
                raise GazeboServiceError("step", f"ControlWorld returned failure for world '{world}'")
            self.logger.debug(f"Stepped world '{world}' by {steps} steps")
        except Exception as e:
            if isinstance(e, (GazeboNotRunningError, GazeboTimeoutError, GazeboServiceError)):
                raise
            raise GazeboServiceError("step", str(e)) from e

        # Best-effort sim_time: query world properties (uses /clock if wired).
        sim_time = 0.0
        try:
            info = await self.get_world_properties(world)
            sim_time = getattr(info, "sim_time", 0.0)
        except Exception as e:  # noqa: BLE001 - sim_time is best-effort only
            self.logger.debug(f"step: could not read sim_time for '{world}': {e}")

        return {"sim_time": sim_time, "steps": steps}

    async def set_physics(
        self,
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: str = "default",
    ) -> bool:
        """
        Set physics step size and/or real-time factor at runtime (best-effort).

        Modern Gazebo exposes physics tuning via the ``/world/{world}/set_physics``
        service (gz.msgs.Physics). The ros_gz_bridge does not always expose this
        as a ROS 2 service, so this is best-effort: if the bridged service is
        unavailable we log a warning and return True rather than failing the
        caller (the provisioned world's max_step_size/rtf already match config).

        Args:
            step_size: Physics step size in seconds (optional)
            rtf: Target real-time factor (optional)
            world: Target world name

        Returns:
            True (best-effort).
        """
        if step_size is not None and step_size <= 0:
            raise ValueError("step_size must be positive")
        if rtf is not None and rtf <= 0:
            raise ValueError("rtf must be positive")

        service_name = f"/world/{world}/set_physics"
        try:
            from ros_gz_interfaces.srv import SetPhysics  # type: ignore

            if not hasattr(self, "_set_physics_clients"):
                self._set_physics_clients: Dict[str, Any] = {}
            if world not in self._set_physics_clients:
                self._set_physics_clients[world] = self.node.create_client(
                    SetPhysics, service_name
                )
            client = self._set_physics_clients[world]

            request = SetPhysics.Request()
            if step_size is not None:
                request.physics.max_step_size = float(step_size)
            if rtf is not None:
                request.physics.real_time_factor = float(rtf)

            response = await self._call_service_async(
                client, request, f"set_physics (world={world})"
            )
            return bool(getattr(response, "success", True))

        except ImportError:
            self.logger.warning(
                f"set_physics: {service_name} not bridged (ros_gz_interfaces.srv.SetPhysics "
                "unavailable). Skipping runtime physics update (best-effort)."
            )
            return True
        except Exception as e:  # noqa: BLE001 - best-effort, never block the caller
            self.logger.warning(f"set_physics best-effort failed for '{world}': {e}")
            return True

    async def seed(self, value: int, world: str = "default") -> bool:
        """
        Set the simulation random seed (best-effort / no-op-with-log).

        Modern Gazebo (Harmonic) has no standard runtime "set seed" service; the
        seed is normally fixed at world-launch time. We log the request and
        return True so reproducibility plumbing works end-to-end without
        blocking. A real seed wire-up belongs at provision time.

        Args:
            value: Seed value
            world: Target world name

        Returns:
            True (best-effort).
        """
        self.logger.info(
            f"seed({value}) requested for world '{world}': Modern Gazebo has no "
            "runtime seed service; seed should be set at world-launch time "
            "(best-effort no-op)."
        )
        return True

    def shutdown(self) -> None:
        """
        Shutdown adapter and cleanup resources.

        Explicitly destroys all service clients before node destruction
        to prevent resource leaks.
        """
        self.logger.info("Shutting down Modern Gazebo adapter...")

        # Destroy all service clients explicitly
        for world, client in list(self._spawn_clients.items()):
            try:
                self.node.destroy_client(client)
                self.logger.debug(f"Destroyed spawn client for world '{world}'")
            except Exception as e:
                self.logger.warning(f"Error destroying spawn client for '{world}': {e}")

        for world, client in list(self._delete_clients.items()):
            try:
                self.node.destroy_client(client)
                self.logger.debug(f"Destroyed delete client for world '{world}'")
            except Exception as e:
                self.logger.warning(f"Error destroying delete client for '{world}': {e}")

        for world, client in list(self._set_pose_clients.items()):
            try:
                self.node.destroy_client(client)
                self.logger.debug(f"Destroyed set_pose client for world '{world}'")
            except Exception as e:
                self.logger.warning(f"Error destroying set_pose client for '{world}': {e}")

        for world, client in list(self._control_clients.items()):
            try:
                self.node.destroy_client(client)
                self.logger.debug(f"Destroyed control client for world '{world}'")
            except Exception as e:
                self.logger.warning(f"Error destroying control client for '{world}': {e}")

        # Clear dictionaries
        self._spawn_clients.clear()
        self._delete_clients.clear()
        self._set_pose_clients.clear()
        self._control_clients.clear()

        self.logger.info("Modern Gazebo adapter shutdown complete")
