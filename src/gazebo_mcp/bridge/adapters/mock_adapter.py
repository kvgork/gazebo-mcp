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

import struct
import zlib
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

# P2: FIXED timestamp constant for ALL mock sensor snapshots so they are fully
# reproducible (NOT datetime.utcnow() — non-deterministic + deprecated).
_FIXED_TIMESTAMP = "2026-01-01T00:00:00Z"

# P2: ceiling on each image dimension for the mock camera (matches the tool
# layer's MAX_IMAGE_DIM); huge resolutions are capped, never rejected here.
MAX_IMAGE_DIM = 4096

# P2: the four deterministic mock sensor descriptors. Reuses the legacy
# _get_mock_sensors() content (sensor_tools.py). ``list_sensors`` DERIVES each
# descriptor's "health" from its "active" flag at read time (see below) so the
# status is honest rather than a hardcoded constant.
_MOCK_SENSORS: List[Dict[str, Any]] = [
    {
        "name": "lidar_front",
        "type": "lidar",
        "model": "turtlebot3_burger",
        "topic": "/scan",
        "frame_id": "base_scan",
        "active": True,
        "specs": {
            "min_range": 0.12,
            "max_range": 3.5,
            "angle_min": -3.14,
            "angle_max": 3.14,
            "resolution": 360,
        },
    },
    {
        "name": "camera_rgb",
        "type": "camera",
        "model": "turtlebot3_waffle",
        "topic": "/camera/image_raw",
        "frame_id": "camera_link",
        "active": True,
        "specs": {"width": 1920, "height": 1080, "fov": 1.3962634, "format": "RGB8"},
    },
    {
        "name": "imu_sensor",
        "type": "imu",
        "model": "turtlebot3_burger",
        "topic": "/imu",
        "frame_id": "imu_link",
        "active": True,
        "specs": {"update_rate": 200.0, "noise": 0.01},
    },
    {
        "name": "gps_sensor",
        "type": "gps",
        "model": "drone_1",
        "topic": "/gps/fix",
        "frame_id": "gps_link",
        "active": True,
        "specs": {"horizontal_accuracy": 1.0, "vertical_accuracy": 1.5},
    },
]


def _solid_png(width: int, height: int, rgb: tuple = (64, 128, 192)) -> bytes:
    """
    Hand-roll a minimal, valid solid-color RGB PNG (no Pillow dependency).

    The IHDR width/height are set to the requested ``width``/``height`` so the
    returned bytes are a real PNG of the capped dimensions. Output is fully
    deterministic for a given (width, height, rgb).
    """

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # IHDR: width, height, bit depth 8, color type 2 (truecolor RGB),
    # compression 0, filter 0, interlace 0.
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    # Raw image data: each scanline prefixed with filter byte 0, then RGB pixels.
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    idat = zlib.compress(raw, 9)

    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )

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
        # P2: deterministic in-memory parameter store, seeded with a few
        # well-known physics/gravity defaults. param_set mutates this dict.
        self._params: Dict[str, Dict[str, Any]] = {
            "physics.max_step_size": {"type": "double", "value": 0.001},
            "physics.real_time_factor": {"type": "double", "value": 1.0},
            "gravity.z": {"type": "double", "value": -9.81},
        }
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
        """Advance mock time and integrate recorded wrenches.

        HONESTY NOTE — this is a KINEMATIC LINEAR-FORCE APPROXIMATION, not real
        rigid-body dynamics:
          - Only LINEAR force is integrated, as Δx = ½·(F/m)·(n·dt)² PER step()
            call, always FROM REST (the mock carries no velocity state).
          - TORQUE is recorded by ``apply_wrench_topic`` but is NEVER applied —
            the entity's orientation does not change.
          - TWIST (linear/angular velocity) is NOT updated by stepping.
          - Mass is the constant ``_MOCK_MASS = 1.0`` for every entity,
            regardless of the spawned SDF's inertial properties.
        Callers/tests must treat the resulting pose as a deterministic fixture,
        not a physical prediction.
        """
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
        """Record a wrench on ``entity``; integrated lazily in ``step``.

        HONESTY NOTE: the recorded ``torque`` is stored but NEVER applied — the
        mock ``step`` integrates LINEAR force only (kinematic, constant
        ``_MOCK_MASS = 1.0``, from rest each call) and never rotates the entity
        or updates its twist. ``duration`` is ignored; ``persistent`` only
        controls whether the wrench survives a ``step`` call (one-shot vs
        re-integrated). See ``step`` for the full approximation contract.
        """
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

    # -- sensors + parameters (P2) --

    async def list_sensors(self, world: str = "default") -> List[Dict[str, Any]]:
        """Return deep copies of the 4 deterministic mock sensor descriptors.

        Each descriptor carries name/type/model/topic/frame_id/active/specs plus
        a ``"health"`` field DERIVED from ``active`` ("ok" if active else
        "inactive"). Copies are returned so a caller mutating the result cannot
        corrupt the module-level fixtures.

        HONESTY NOTE: this ``health`` is a BASIC active/inactive status only.
        Richer health metrics (data-rate / latency / dropout / quality, the old
        ``monitor_sensor_health`` payload) are DEFERRED to the real backend and
        are not synthesised here.
        """
        import copy

        sensors = []
        for s in _MOCK_SENSORS:
            d = copy.deepcopy(s)
            d["health"] = "ok" if d.get("active") else "inactive"
            sensors.append(d)
        return sensors

    async def sensor_snapshot(self, topic: str, world: str = "default") -> Dict[str, Any]:
        """Return the deterministic TYPED sample for the sensor at ``topic``.

        Shapes mirror the legacy ``_get_mock_sensor_data`` payloads but every
        snapshot uses the FIXED timestamp ``_FIXED_TIMESTAMP`` so the result is
        fully reproducible. Every return carries ``"typed": True`` — this is the
        typed-sample backend; the modern adapter returns raw gz-text with
        ``"typed": False`` instead (callers branch on the flag).

        Raises:
            KeyError: if no mock sensor publishes on ``topic``.
        """
        sensor = next((s for s in _MOCK_SENSORS if s["topic"] == topic), None)
        if sensor is None:
            raise KeyError(topic)

        name = sensor["name"]
        sensor_type = sensor["type"]

        if sensor_type == "lidar":
            return {
                "type": "lidar",
                "typed": True,
                "sensor_name": name,
                "topic": topic,
                "timestamp": _FIXED_TIMESTAMP,
                "ranges": [1.5, 2.0, 1.8, 2.5, 3.0] * 72,  # 360 measurements
                "angle_min": -3.14,
                "angle_max": 3.14,
                "range_min": 0.12,
                "range_max": 3.5,
            }
        elif sensor_type == "camera":
            return {
                "type": "camera",
                "typed": True,
                "sensor_name": name,
                "topic": topic,
                "timestamp": _FIXED_TIMESTAMP,
                "width": 1920,
                "height": 1080,
                "encoding": "rgb8",
                "note": "Image data not included in snapshot; use sensor_camera_image",
            }
        elif sensor_type == "imu":
            return {
                "type": "imu",
                "typed": True,
                "sensor_name": name,
                "topic": topic,
                "timestamp": _FIXED_TIMESTAMP,
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "angular_velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
                "linear_acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
            }
        else:  # gps
            return {
                "type": "gps",
                "typed": True,
                "sensor_name": name,
                "topic": topic,
                "timestamp": _FIXED_TIMESTAMP,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "altitude": 10.0,
                "status": "FIX",
            }

    async def sensor_camera_image(
        self,
        topic: str,
        resolution: str = "640x480",
        quality: int = 60,
        world: str = "default",
    ) -> Dict[str, Any]:
        """Return a deterministic solid-color PNG for the camera topic.

        Only ``/camera/image_raw`` is a valid camera topic in the mock. ``WxH``
        is parsed from ``resolution`` and each dimension is CAPPED at
        ``MAX_IMAGE_DIM``. ``quality`` is accepted for parity but unused (PNG is
        lossless; ``quality`` is reserved for the real backend's JPEG path).
        Returns {"data": <png bytes>, "format": "png", "width", "height",
        "synthetic": True, "backend": "mock"}.

        HONESTY NOTE: the returned frame is a solid-color SYNTHETIC fill, NOT a
        real rendered scene — ``synthetic=True``/``backend="mock"`` mark it so a
        vision consumer cannot mistake it for a real camera frame.

        Note: in practice the TOOL layer (``tools/sensor.py``) REJECTS dims
        > ``MAX_IMAGE_DIM`` with IMAGE_TOO_LARGE before this adapter is ever
        called, so the ``min(...)`` cap below is unreachable via the tool path
        and only guards a direct adapter call.

        Raises:
            KeyError: if ``topic`` is not the mock camera topic.
            ValueError: if ``resolution`` is not in "WxH" form.
        """
        camera = next(
            (s for s in _MOCK_SENSORS if s["type"] == "camera" and s["topic"] == topic),
            None,
        )
        if camera is None:
            raise KeyError(topic)

        try:
            w_str, h_str = resolution.lower().split("x")
            width = int(w_str)
            height = int(h_str)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid resolution '{resolution}'; expected 'WxH' (e.g. '640x480')"
            ) from e

        if width < 1 or height < 1:
            raise ValueError(f"Invalid resolution '{resolution}'; dimensions must be >= 1")

        width = min(width, MAX_IMAGE_DIM)
        height = min(height, MAX_IMAGE_DIM)

        png = _solid_png(width, height)
        return {
            "data": png,
            "format": "png",
            "width": width,
            "height": height,
            # Mark the frame as a synthetic solid-color mock fill (not a real
            # rendered scene) so downstream vision consumers cannot mistake it.
            "synthetic": True,
            "backend": "mock",
        }

    @staticmethod
    def _infer_param_type(value: Any) -> str:
        """Infer the param type string from a Python value.

        Note: bool is checked BEFORE int because ``bool`` is a subclass of ``int``.
        """
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "double"
        return "string"

    async def param_list(self, world: str = "default") -> List[str]:
        """Return the sorted list of parameter names in the in-memory store."""
        return sorted(self._params.keys())

    async def param_get(self, name: str, world: str = "default") -> Dict[str, Any]:
        """Return {"name","type","value"} for ``name``.

        Raises:
            KeyError: if ``name`` is not in the store.
        """
        if name not in self._params:
            raise KeyError(name)
        entry = self._params[name]
        return {"name": name, "type": entry["type"], "value": entry["value"]}

    async def param_set(self, name: str, value: Any, world: str = "default") -> bool:
        """Set (or create) ``name`` = ``value``, inferring the type. Returns True."""
        self._params[name] = {"type": self._infer_param_type(value), "value": value}
        return True
