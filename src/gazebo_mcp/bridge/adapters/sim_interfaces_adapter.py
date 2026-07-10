"""
REP-2018 ``simulation_interfaces`` adapter (P4-real cross-sim portability).

A :class:`~gazebo_mcp.bridge.gazebo_interface.GazeboInterface` implementation
that drives ANY simulator exposing the standard REP-2018
``simulation_interfaces`` ROS 2 services — not gz-specific topics/services. This
is the portable backend behind the ``sim_*`` tools: the same gazebo-mcp surface
can then control Gazebo, or any other REP-2018-compliant simulator, unchanged.

Live backend in THIS environment: the ``ros_gz_sim`` **gzserver component**
(``libgzserver_component.so``) provides the services under a configurable
namespace (default ``/gz_server``) when launched via
``ros2 launch ros_gz_sim gz_server.launch.py ... use_composition:=True
create_own_container:=True``. Verified live 2026-07-08 (see
``tests/integration/test_p4_real_sim_interfaces.py``).

Service map (GazeboInterface -> simulation_interfaces/srv):
    spawn_entity        -> SpawnEntity        (resource_string = SDF, initial_pose)
    delete_entity       -> DeleteEntity
    get_entity_state    -> GetEntityState      (-> pose/twist dict)
    set_entity_state    -> SetEntityState
    list_entities       -> GetEntities
    get_world_properties-> GetEntities + GetSimulationState
    pause_simulation    -> SetSimulationState  (STATE_PAUSED)
    unpause_simulation  -> SetSimulationState  (STATE_PLAYING)
    reset_simulation    -> ResetSimulation     (SCOPE_ALL)
    reset_world         -> ResetSimulation     (SCOPE_STATE)
    step                -> StepSimulation       (pauses first — REP-2018 requires
                                                 the sim PAUSED to single/multi-step)
    get_simulator_features (extra) -> GetSimulatorFeatures

Deliberately NOT implemented (REP-2018 core does not define them — they stay the
GazeboInterface NotImplementedError defaults, which is the honest answer for a
portable simulator backend): wrench/joint actuation, sensor snapshot/camera,
gz parameter registry, set_physics, seed.

``simulation_interfaces`` is only present in the full ROS env, so it is imported
LAZILY inside methods (top-level imports stay ``-e dev`` safe, mirroring
``modern_adapter``'s ros_gz import discipline). This module is intentionally NOT
re-exported from ``adapters/__init__`` for the same reason.
"""

import asyncio
from typing import Any, Dict, List, Optional

from geometry_msgs.msg import Point, Pose, Quaternion, Vector3

from ..gazebo_interface import (
    EntityPose,
    EntityTwist,
    GazeboInterface,
    WorldInfo,
)
from ...utils.exceptions import (
    GazeboNotRunningError,
    GazeboServiceError,
    GazeboTimeoutError,
    ModelNotFoundError,
)
from ...utils.logger import get_logger


class SimInterfacesAdapter(GazeboInterface):
    """REP-2018 ``simulation_interfaces`` client adapter (portable backend)."""

    def __init__(
        self,
        node,
        service_ns: str = "/gz_server",
        default_world: str = "default",
        timeout: float = 8.0,
    ):
        """
        Args:
            node: a live ``rclpy`` node used to create service clients.
            service_ns: namespace the REP-2018 services live under (the
                ros_gz_sim gzserver component uses ``/gz_server``). No trailing
                slash; ``""`` means the services are at the root.
            default_world: world label echoed in results (REP-2018 is
                world-implicit — the running simulator IS the world).
            timeout: per-service-call timeout in seconds.
        """
        self.node = node
        self.service_ns = service_ns.rstrip("/")
        self.default_world = default_world
        self.timeout = timeout
        self.logger = get_logger("sim_interfaces_adapter")
        self._clients: Dict[str, Any] = {}
        self.logger.info(
            f"Initialized REP-2018 sim_interfaces adapter (ns='{self.service_ns}')"
        )

    def get_backend_name(self) -> str:
        return "sim_interfaces"

    # -- service plumbing ----------------------------------------------------

    def _svc(self, name: str) -> str:
        return f"{self.service_ns}/{name}" if self.service_ns else f"/{name}"

    def _client(self, srv_type, name: str):
        """Lazily create + cache a service client keyed by full service name."""
        full = self._svc(name)
        if full not in self._clients:
            self._clients[full] = self.node.create_client(srv_type, full)
            self.logger.debug(f"Created client for '{full}'")
        return self._clients[full]

    async def _call(self, client, request, op: str):
        """Async service call mirroring ModernGazeboAdapter._call_service_async:
        blocking spin runs in a thread-pool executor so the event loop stays free."""
        import rclpy

        if not client.wait_for_service(timeout_sec=self.timeout):
            raise GazeboNotRunningError(
                f"REP-2018 service for {op} not available "
                f"(is a simulation_interfaces backend running under "
                f"'{self.service_ns}'?)"
            )
        future = client.call_async(request)
        loop = asyncio.get_event_loop()

        def _spin():
            rclpy.spin_until_future_complete(self.node, future, timeout_sec=self.timeout)

        await loop.run_in_executor(None, _spin)
        if not future.done():
            raise GazeboTimeoutError(op, self.timeout)
        exc = future.exception()
        if exc is not None:
            raise GazeboServiceError(op, str(exc)) from exc
        return future.result()

    @staticmethod
    def _is_ok(result_msg) -> bool:
        from simulation_interfaces.msg import Result

        return result_msg.result == Result.RESULT_OK

    @staticmethod
    def _is_not_found(result_msg) -> bool:
        from simulation_interfaces.msg import Result

        if result_msg.result == Result.RESULT_NOT_FOUND:
            return True
        # The ros_gz_sim gzserver backend reports a missing entity as
        # RESULT_OPERATION_FAILED (4) with a "not found" message rather than the
        # RESULT_NOT_FOUND code (verified live 2026-07-08). Treat that as
        # not-found too, so callers get a clean ModelNotFoundError regardless of
        # which REP-2018 backend coding a simulator chose.
        return "not found" in (result_msg.error_message or "").lower()

    def _pose_msg(self, pose: EntityPose) -> Pose:
        return Pose(
            position=Point(
                x=float(pose.position[0]),
                y=float(pose.position[1]),
                z=float(pose.position[2]),
            ),
            orientation=Quaternion(
                x=float(pose.orientation[0]),
                y=float(pose.orientation[1]),
                z=float(pose.orientation[2]),
                w=float(pose.orientation[3]),
            ),
        )

    # -- GazeboInterface: entities ------------------------------------------

    async def spawn_entity(
        self, name: str, sdf: str, pose: EntityPose, world: str = "default"
    ) -> bool:
        from geometry_msgs.msg import PoseStamped
        from simulation_interfaces.srv import SpawnEntity

        req = SpawnEntity.Request()
        req.name = name
        req.allow_renaming = False
        req.resource_string = sdf  # inline SDF/URDF/MJCF string
        req.initial_pose = PoseStamped()
        req.initial_pose.header.frame_id = "world"
        req.initial_pose.pose = self._pose_msg(pose)
        resp = await self._call(
            self._client(SpawnEntity, "spawn_entity"), req, "spawn_entity"
        )
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "spawn_entity",
                f"spawn '{name}' failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        self.logger.info(f"Spawned '{resp.entity_name}' via REP-2018")
        return True

    async def delete_entity(self, name: str, world: str = "default") -> bool:
        from simulation_interfaces.srv import DeleteEntity

        req = DeleteEntity.Request()
        req.entity = name
        resp = await self._call(
            self._client(DeleteEntity, "delete_entity"), req, "delete_entity"
        )
        if self._is_not_found(resp.result):
            raise ModelNotFoundError(name)
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "delete_entity",
                f"delete '{name}' failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        return True

    async def get_entity_state(self, name: str, world: str = "default") -> Dict[str, Any]:
        from simulation_interfaces.srv import GetEntityState

        req = GetEntityState.Request()
        req.entity = name
        resp = await self._call(
            self._client(GetEntityState, "get_entity_state"), req, "get_entity_state"
        )
        if self._is_not_found(resp.result):
            raise ModelNotFoundError(name)
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "get_entity_state",
                f"get_entity_state '{name}' failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        st = resp.state
        p, t = st.pose, st.twist
        return {
            "name": name,
            "pose": {
                "position": (p.position.x, p.position.y, p.position.z),
                "orientation": (
                    p.orientation.x,
                    p.orientation.y,
                    p.orientation.z,
                    p.orientation.w,
                ),
            },
            "twist": {
                "linear": (t.linear.x, t.linear.y, t.linear.z),
                "angular": (t.angular.x, t.angular.y, t.angular.z),
            },
        }

    async def set_entity_state(
        self,
        name: str,
        pose: EntityPose,
        twist: Optional[EntityTwist] = None,
        world: str = "default",
    ) -> bool:
        from simulation_interfaces.msg import EntityState
        from simulation_interfaces.srv import SetEntityState
        from geometry_msgs.msg import Twist

        req = SetEntityState.Request()
        req.entity = name
        state = EntityState()
        state.header.frame_id = "world"
        state.pose = self._pose_msg(pose)
        if twist is not None:
            state.twist = Twist(
                linear=Vector3(
                    x=float(twist.linear[0]),
                    y=float(twist.linear[1]),
                    z=float(twist.linear[2]),
                ),
                angular=Vector3(
                    x=float(twist.angular[0]),
                    y=float(twist.angular[1]),
                    z=float(twist.angular[2]),
                ),
            )
        req.state = state
        resp = await self._call(
            self._client(SetEntityState, "set_entity_state"), req, "set_entity_state"
        )
        if self._is_not_found(resp.result):
            raise ModelNotFoundError(name)
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "set_entity_state",
                f"set_entity_state '{name}' failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        return True

    async def list_entities(self, world: str = "default") -> List[str]:
        from simulation_interfaces.msg import EntityFilters
        from simulation_interfaces.srv import GetEntities

        req = GetEntities.Request()
        req.filters = EntityFilters()  # no filter -> all entities
        resp = await self._call(
            self._client(GetEntities, "get_entities"), req, "list_entities"
        )
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "list_entities",
                f"get_entities failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        return list(resp.entities)

    async def get_world_properties(self, world: str = "default") -> WorldInfo:
        models = await self.list_entities(world)
        paused = await self._is_paused()
        # REP-2018 core exposes no wall/sim clock via these services; report 0.0
        # honestly rather than fabricate a time.
        return WorldInfo(
            name=world or self.default_world,
            sim_time=0.0,
            models=models,
            paused=paused,
        )

    # -- GazeboInterface: simulation state ----------------------------------

    async def _is_paused(self) -> bool:
        from simulation_interfaces.msg import SimulationState
        from simulation_interfaces.srv import GetSimulationState

        req = GetSimulationState.Request()
        resp = await self._call(
            self._client(GetSimulationState, "get_simulation_state"),
            req,
            "get_simulation_state",
        )
        return resp.state.state == SimulationState.STATE_PAUSED

    async def _set_state(self, target_state: int, op: str) -> bool:
        from simulation_interfaces.msg import SimulationState
        from simulation_interfaces.srv import SetSimulationState

        req = SetSimulationState.Request()
        req.state = SimulationState()
        req.state.state = target_state
        resp = await self._call(
            self._client(SetSimulationState, "set_simulation_state"), req, op
        )
        # ALREADY_IN_TARGET_STATE (101) is a benign success for our intent.
        return self._is_ok(resp.result) or resp.result.result == 101

    async def pause_simulation(self, world: str = "default") -> bool:
        from simulation_interfaces.msg import SimulationState

        return await self._set_state(SimulationState.STATE_PAUSED, "pause_simulation")

    async def unpause_simulation(self, world: str = "default") -> bool:
        from simulation_interfaces.msg import SimulationState

        return await self._set_state(SimulationState.STATE_PLAYING, "unpause_simulation")

    async def _reset(self, scope: int, op: str) -> bool:
        from simulation_interfaces.srv import ResetSimulation

        req = ResetSimulation.Request()
        req.scope = scope
        resp = await self._call(
            self._client(ResetSimulation, "reset_simulation"), req, op
        )
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                op,
                f"{op} failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        return True

    async def reset_simulation(self, world: str = "default") -> bool:
        from simulation_interfaces.srv import ResetSimulation

        return await self._reset(ResetSimulation.Request.SCOPE_ALL, "reset_simulation")

    async def reset_world(self, world: str = "default") -> bool:
        from simulation_interfaces.srv import ResetSimulation

        return await self._reset(ResetSimulation.Request.SCOPE_STATE, "reset_world")

    async def step(
        self, steps: int = 1, world: str = "default", progress_cb=None
    ) -> Dict[str, Any]:
        """Advance ``steps`` physics steps via StepSimulation.

        REP-2018 requires the simulation to be PAUSED for StepSimulation (an
        unpaused sim returns RESULT_OPERATION_FAILED), so this pauses first —
        matching the discrete-stepping intent of the gazebo-mcp ``step`` verb.
        ``progress_cb`` is accepted and ignored (single service call; presence
        must not alter physics).
        """
        from simulation_interfaces.srv import StepSimulation

        await self.pause_simulation(world)
        req = StepSimulation.Request()
        req.steps = int(steps)
        resp = await self._call(
            self._client(StepSimulation, "step_simulation"), req, "step"
        )
        if not self._is_ok(resp.result):
            raise GazeboServiceError(
                "step",
                f"step({steps}) failed (result={resp.result.result}): "
                f"{resp.result.error_message}",
            )
        # REP-2018 StepSimulation carries no post-step clock; report steps done.
        return {"steps": int(steps), "sim_time": 0.0, "paused": True}

    # -- extra (not in the ABC): capability discovery -----------------------

    async def get_simulator_features(self, world: str = "default") -> List[int]:
        """Return the simulator's advertised REP-2018 feature codes
        (``simulation_interfaces/msg/SimulatorFeatures`` enum values)."""
        from simulation_interfaces.srv import GetSimulatorFeatures

        req = GetSimulatorFeatures.Request()
        resp = await self._call(
            self._client(GetSimulatorFeatures, "get_simulator_features"),
            req,
            "get_simulator_features",
        )
        return list(resp.features.features)
