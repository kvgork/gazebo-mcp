"""
Mock Gazebo adapter — deterministic in-memory backend.

Implements the full ``GazeboInterface`` against an in-memory world so the MCP
server (and its acceptance tests) can run with NO Gazebo/ROS2 graph present —
the honest CI backend called for in P0 of the architecture-evolution plan.

Unlike the legacy per-tool inline mock data, this is a real backend object:
state mutates across calls (spawn → get_state → step → remove), enabling the
end-to-end "spawn cube → query pose → step → remove" acceptance against a fixture.
All behaviour is deterministic (no RNG, no wall-clock).
"""

from typing import Optional, List, Dict, Any

from gazebo_mcp.bridge.gazebo_interface import (
    GazeboInterface,
    EntityPose,
    EntityTwist,
    WorldInfo,
)
from gazebo_mcp.utils.exceptions import ModelNotFoundError
from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("mock_adapter")

_DEFAULT_STEP_SIZE = 0.001  # seconds per physics step (matches gz default)

# Mock physics uses a single constant mass for every entity so that the
# wrench-integration acceptance is fully deterministic and asset-independent:
#   Δpos[i] = 0.5 * (force[i] / _MOCK_MASS) * (n * step_size)**2
# With _MOCK_MASS = 1.0 and F=(10,0,0), n=100, step_size=0.001 ⇒ Δx = 0.05.
_MOCK_MASS = 1.0  # kg (constant for all entities in the mock backend)


class _MockWorld:
    """In-memory state for a single world."""

    def __init__(self, name: str, step_size: float):
        self.name = name
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.sim_time: float = 0.0
        self.paused: bool = False
        self.step_size: float = step_size
        self.rtf: float = 1.0
        self.seed_value: Optional[int] = None
        # P1 actuation state:
        #   wrenches[entity]      = {"force":[fx,fy,fz], "torque":[...], "persistent":bool}
        #   joint_targets[model][joint] = {"mode":str, "value":float}
        self.wrenches: Dict[str, dict] = {}
        self.joint_targets: Dict[str, Dict[str, dict]] = {}


class MockGazeboAdapter(GazeboInterface):
    """Deterministic in-memory implementation of GazeboInterface."""

    def __init__(
        self,
        node=None,
        default_world: str = "default",
        timeout: float = 5.0,
        step_size: float = _DEFAULT_STEP_SIZE,
    ):
        # node/timeout accepted for factory signature compatibility; unused.
        self._default_world = default_world
        self._step_size = step_size
        self._worlds: Dict[str, _MockWorld] = {}
        _logger.info("Initialized Mock Gazebo adapter", world=default_world)

    # -- internal helpers --

    def _world(self, world: str) -> _MockWorld:
        if world not in self._worlds:
            self._worlds[world] = _MockWorld(world, self._step_size)
        return self._worlds[world]

    @staticmethod
    def _pose_to_dict(pose: EntityPose) -> Dict[str, Any]:
        return {"position": list(pose.position), "orientation": list(pose.orientation)}

    @staticmethod
    def _default_twist() -> Dict[str, Any]:
        return {"linear": [0.0, 0.0, 0.0], "angular": [0.0, 0.0, 0.0]}

    # -- entity lifecycle --

    async def spawn_entity(
        self, name: str, sdf: str, pose: EntityPose, world: str = "default"
    ) -> bool:
        w = self._world(world)
        if name in w.entities:
            _logger.warning("Entity already exists; overwriting", name=name)
        w.entities[name] = {
            "name": name,
            "pose": self._pose_to_dict(pose),
            "twist": self._default_twist(),
            "sdf_len": len(sdf or ""),
        }
        return True

    async def delete_entity(self, name: str, world: str = "default") -> bool:
        w = self._world(world)
        if name not in w.entities:
            raise ModelNotFoundError(name)
        del w.entities[name]
        return True

    async def get_entity_state(self, name: str, world: str = "default") -> Dict[str, Any]:
        w = self._world(world)
        if name not in w.entities:
            raise ModelNotFoundError(name)
        e = w.entities[name]
        # Correct readback: returns the stored pose/twist (not zeros).
        return {"name": name, "pose": e["pose"], "twist": e["twist"]}

    async def set_entity_state(
        self,
        name: str,
        pose: EntityPose,
        twist: Optional[EntityTwist] = None,
        world: str = "default",
    ) -> bool:
        w = self._world(world)
        if name not in w.entities:
            raise ModelNotFoundError(name)
        w.entities[name]["pose"] = self._pose_to_dict(pose)
        if twist is not None:
            w.entities[name]["twist"] = {
                "linear": list(twist.linear),
                "angular": list(twist.angular),
            }
        return True

    async def list_entities(self, world: str = "default") -> List[str]:
        return list(self._world(world).entities.keys())

    async def get_world_properties(self, world: str = "default") -> WorldInfo:
        w = self._world(world)
        return WorldInfo(
            name=w.name,
            sim_time=w.sim_time,
            models=list(w.entities.keys()),
            paused=w.paused,
        )

    # -- lifecycle / timing --

    async def pause_simulation(self, world: str = "default") -> bool:
        self._world(world).paused = True
        return True

    async def unpause_simulation(self, world: str = "default") -> bool:
        self._world(world).paused = False
        return True

    async def reset_simulation(self, world: str = "default") -> bool:
        w = self._world(world)
        w.entities.clear()
        w.sim_time = 0.0
        return True

    async def reset_world(self, world: str = "default") -> bool:
        return await self.reset_simulation(world)

    def get_backend_name(self) -> str:
        return "mock"

    # -- physics/timing control (P0 additions) --

    async def step(self, steps: int = 1, world: str = "default") -> Dict[str, Any]:
        if steps < 1:
            raise ValueError("steps must be >= 1")
        w = self._world(world)
        w.sim_time += steps * w.step_size

        # Wrench integration (P1): constant-mass kinematics under a constant force.
        #   Δpos[i] = 0.5 * (force[i] / _MOCK_MASS) * (n * step_size)**2
        # One-shot wrenches are popped after integrating; persistent ones remain
        # and re-integrate on the next step() call. list(...) so we can pop safely.
        dt = steps * w.step_size
        for entity, wr in list(w.wrenches.items()):
            ent = w.entities.get(entity)
            if ent is not None:
                pos = ent["pose"]["position"]
                for i in range(3):
                    pos[i] += 0.5 * (wr["force"][i] / _MOCK_MASS) * (dt ** 2)
            if not wr.get("persistent", False):
                w.wrenches.pop(entity, None)

        return {"sim_time": w.sim_time, "steps": steps, "paused": w.paused}

    async def set_physics(
        self,
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: str = "default",
    ) -> bool:
        w = self._world(world)
        if step_size is not None:
            if step_size <= 0:
                raise ValueError("step_size must be positive")
            w.step_size = step_size
        if rtf is not None:
            if rtf <= 0:
                raise ValueError("rtf must be positive")
            w.rtf = rtf
        return True

    async def seed(self, value: int, world: str = "default") -> bool:
        self._world(world).seed_value = int(value)
        return True

    # -- actuation: wrench + joint commanding (P1) --

    async def apply_wrench_topic(
        self,
        entity: str,
        link: str = "",
        force: tuple = (0.0, 0.0, 0.0),
        torque: tuple = (0.0, 0.0, 0.0),
        duration: float = 0.0,
        persistent: bool = False,
        world: str = "default",
    ) -> bool:
        """Record a wrench on ``entity``; integrated lazily in ``step``."""
        w = self._world(world)
        w.wrenches[entity] = {
            "force": [float(force[0]), float(force[1]), float(force[2])],
            "torque": [float(torque[0]), float(torque[1]), float(torque[2])],
            "persistent": bool(persistent),
        }
        return True

    async def clear_wrench(self, entity: str, world: str = "default") -> bool:
        """Remove any recorded wrench for ``entity`` (idempotent)."""
        self._world(world).wrenches.pop(entity, None)
        return True

    async def command_joint(
        self,
        model: str,
        joint: str,
        mode: str,
        value: float,
        world: str = "default",
    ) -> bool:
        """
        Record a joint target. No limit checking here — limit validation is the
        tool layer's responsibility (against the model manifest).
        """
        w = self._world(world)
        w.joint_targets.setdefault(model, {})[joint] = {
            "mode": mode,
            "value": float(value),
        }
        return True

    async def command_joint_trajectory(
        self,
        model: str,
        points: list,
        world: str = "default",
    ) -> bool:
        """
        Record a joint trajectory. The mock has no joint-name list, so we store
        the LAST point dict deterministically under the reserved key
        ``"_trajectory"`` in ``joint_targets[model]`` (readable via
        ``get_joint_target(model, "_trajectory")``).
        """
        w = self._world(world)
        targets = w.joint_targets.setdefault(model, {})
        last = points[-1] if points else {}
        targets["_trajectory"] = dict(last) if isinstance(last, dict) else {"value": last}
        return True

    # -- mock-only read-backs (unit-test helpers; not part of GazeboInterface) --

    async def get_recorded_wrench(
        self, entity: str, world: str = "default"
    ) -> Optional[dict]:
        """Return the recorded wrench dict for ``entity`` or None."""
        return self._world(world).wrenches.get(entity)

    async def get_joint_target(
        self, model: str, joint: str, world: str = "default"
    ) -> Optional[dict]:
        """Return the recorded ``{"mode","value"}`` target for a joint or None."""
        return self._world(world).joint_targets.get(model, {}).get(joint)
