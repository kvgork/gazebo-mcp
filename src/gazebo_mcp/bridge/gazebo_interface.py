"""
Gazebo Interface - Abstract base class for Gazebo backends.

Provides a common interface for both Classic and Modern Gazebo,
enabling runtime backend selection without code changes.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class EntityPose:
    """Common pose representation across backends."""
    position: tuple  # (x, y, z)
    orientation: tuple  # (x, y, z, w) quaternion


@dataclass
class EntityTwist:
    """Common twist (velocity) representation."""
    linear: tuple  # (vx, vy, vz)
    angular: tuple  # (wx, wy, wz)


@dataclass
class WorldInfo:
    """Common world information across backends."""
    name: str
    sim_time: float
    models: List[str]
    paused: bool


class GazeboInterface(ABC):
    """
    Abstract interface for Gazebo operations.

    Hides differences between Classic Gazebo (gazebo_msgs) and
    Modern Gazebo (ros_gz_interfaces), allowing seamless backend switching.

    Design Principles:
    - Simple methods (one action per method)
    - Return bool for success/failure or raise exceptions
    - No backend-specific types in signatures
    - Common data structures (EntityPose, WorldInfo, etc.)
    """

    @abstractmethod
    async def spawn_entity(
        self,
        name: str,
        sdf: str,
        pose: EntityPose,
        world: str = "default"
    ) -> bool:
        """
        Spawn a model in the simulation.

        Args:
            name: Unique model name
            sdf: SDF XML string (version-agnostic internally)
            pose: Initial position and orientation
            world: World name (Classic ignores this, Modern requires it)

        Returns:
            True if spawned successfully

        Raises:
            GazeboConnectionError: If Gazebo not running
            GazeboServiceError: If spawn service fails
        """
        pass

    @abstractmethod
    async def delete_entity(
        self,
        name: str,
        world: str = "default"
    ) -> bool:
        """
        Delete a model from simulation.

        Args:
            name: Model name to delete
            world: World name (Classic ignores, Modern uses)

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def get_entity_state(
        self,
        name: str,
        world: str = "default"
    ) -> Dict[str, Any]:
        """
        Get entity state (pose, twist).

        Args:
            name: Model name
            world: World name

        Returns:
            Dict with 'pose', 'twist', 'name'
        """
        pass

    @abstractmethod
    async def set_entity_state(
        self,
        name: str,
        pose: EntityPose,
        twist: Optional[EntityTwist] = None,
        world: str = "default"
    ) -> bool:
        """
        Update entity position and velocity.

        Args:
            name: Model name
            pose: New position and orientation
            twist: New velocity (optional)
            world: World name

        Returns:
            True if state updated successfully
        """
        pass

    @abstractmethod
    async def list_entities(
        self,
        world: str = "default"
    ) -> List[str]:
        """
        List all models in simulation.

        Args:
            world: World name

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def get_world_properties(
        self,
        world: str = "default"
    ) -> WorldInfo:
        """
        Get current world state.

        Args:
            world: World name

        Returns:
            WorldInfo with name, time, models, paused state
        """
        pass

    @abstractmethod
    async def pause_simulation(self, world: str = "default") -> bool:
        """
        Pause physics simulation.

        Args:
            world: World name

        Returns:
            True if paused successfully
        """
        pass

    @abstractmethod
    async def unpause_simulation(self, world: str = "default") -> bool:
        """
        Resume physics simulation.

        Args:
            world: World name

        Returns:
            True if unpaused successfully
        """
        pass

    @abstractmethod
    async def reset_simulation(self, world: str = "default") -> bool:
        """
        Reset simulation to initial state.

        Args:
            world: World name

        Returns:
            True if reset successfully
        """
        pass

    @abstractmethod
    async def reset_world(self, world: str = "default") -> bool:
        """
        Reset world to initial state.

        Args:
            world: World name

        Returns:
            True if reset successfully
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """
        Get backend identifier.

        Returns:
            "classic", "modern", or "mock"
        """
        pass

    # --- Simulation timing/physics control (added in P0 of the evolution plan) ---
    # These are NON-abstract with a NotImplementedError default so existing
    # adapters remain instantiable; backends implement them incrementally.
    # The mock backend implements all three; real backends land them in the
    # sim-env slice (map to /control multi_step, /set_physics, and reset seed).

    async def step(self, steps: int = 1, world: str = "default") -> Dict[str, Any]:
        """
        Advance the simulation by a fixed number of steps.

        Args:
            steps: Number of physics steps to advance (>= 1)
            world: World name

        Returns:
            Dict with at least 'sim_time' (float) after stepping and 'steps' executed.
        """
        raise NotImplementedError(
            f"step() not implemented for backend '{self.get_backend_name()}'"
        )

    async def set_physics(
        self,
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: str = "default",
    ) -> bool:
        """
        Set physics step size and/or real-time factor at runtime.

        Args:
            step_size: Physics step size in seconds (optional)
            rtf: Target real-time factor (optional)
            world: World name

        Returns:
            True if applied successfully.
        """
        raise NotImplementedError(
            f"set_physics() not implemented for backend '{self.get_backend_name()}'"
        )

    async def seed(self, value: int, world: str = "default") -> bool:
        """
        Set the simulation random seed for reproducibility.

        Args:
            value: Seed value
            world: World name

        Returns:
            True if applied successfully.
        """
        raise NotImplementedError(
            f"seed() not implemented for backend '{self.get_backend_name()}'"
        )

    # --- Actuation: wrench + joint commanding (added in P1 of the evolution plan) ---
    # NON-abstract with NotImplementedError defaults so existing adapters remain
    # instantiable; backends implement them incrementally. The mock backend
    # records and integrates them; the modern backend publishes the real topics
    # (EntityWrench, Float64, JointTrajectory); classic raises NotImplementedError.

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
        """
        Apply a wrench (force + torque) to an entity via the wrench topic.

        Modern Gazebo (Harmonic) exposes wrench application as an
        ``ros_gz_interfaces/msg/EntityWrench`` published to
        ``/world/<world>/wrench`` (and a clear topic), superseding the
        legacy service-based ``apply_wrench``.

        Args:
            entity: Entity (model/link) name to apply the wrench to
            link: Link name within the entity ("" = base/canonical link)
            force: (fx, fy, fz) in Newtons (world frame)
            torque: (tx, ty, tz) in Newton-metres (world frame)
            duration: Duration in seconds (0.0 = single application; the
                gz wrench system / launch handles timed application)
            persistent: If True the wrench is re-applied every step until
                cleared; if False it is one-shot
            world: World name

        Returns:
            True if the wrench was applied/recorded successfully.
        """
        raise NotImplementedError(
            f"apply_wrench_topic() not implemented for backend '{self.get_backend_name()}'"
        )

    async def clear_wrench(self, entity: str, world: str = "default") -> bool:
        """
        Clear any persistent wrench currently applied to an entity.

        Args:
            entity: Entity (model/link) name to clear the wrench for
            world: World name

        Returns:
            True if the clear was applied successfully.
        """
        raise NotImplementedError(
            f"clear_wrench() not implemented for backend '{self.get_backend_name()}'"
        )

    async def command_joint(
        self,
        model: str,
        joint: str,
        mode: str,
        value: float,
        world: str = "default",
    ) -> bool:
        """
        Command a single joint in position, velocity, or force mode.

        Args:
            model: Model name owning the joint
            joint: Joint name
            mode: One of {"pos", "vel", "force"}
            value: Target value (radians/metres for pos, rad/s or m/s for vel,
                N or N*m for force)
            world: World name

        Returns:
            True if the command was applied/recorded successfully.
        """
        raise NotImplementedError(
            f"command_joint() not implemented for backend '{self.get_backend_name()}'"
        )

    async def command_joint_trajectory(
        self,
        model: str,
        points: list,
        world: str = "default",
    ) -> bool:
        """
        Command a joint trajectory for a model.

        Args:
            model: Model name
            points: List of {"positions": [...], "time_from_start": float} dicts
            world: World name

        Returns:
            True if the trajectory was applied/recorded successfully.
        """
        raise NotImplementedError(
            f"command_joint_trajectory() not implemented for backend '{self.get_backend_name()}'"
        )

    # --- Sensors + parameters (added in P2 of the evolution plan) ---
    # NON-abstract with NotImplementedError defaults so existing adapters remain
    # instantiable; backends implement them incrementally. The mock backend
    # serves deterministic fixtures; the modern backend reads the live graph
    # (gz topic / scene info + gz parameter services); classic raises.

    async def list_sensors(self, world: str = "default") -> List[Dict[str, Any]]:
        """
        List sensors present in the world.

        Args:
            world: World name

        Returns:
            List of sensor descriptor dicts, each with at least
            name/type/model/topic/frame_id/active/specs and a "health" field.

        Note:
            ``health`` is a BASIC active/inactive status only (the mock derives
            it from each sensor's ``active`` flag). Richer health metrics
            (data-rate / latency / dropout / quality — the old
            ``monitor_sensor_health`` payload) are DEFERRED to the real backend.
        """
        raise NotImplementedError(
            f"list_sensors() not implemented for backend '{self.get_backend_name()}'"
        )

    async def sensor_snapshot(self, topic: str, world: str = "default") -> Dict[str, Any]:
        """
        Return the latest sample for the sensor publishing on ``topic``.

        Backend-dependent shape (callers branch on the ``"typed"`` flag):
          - MOCK backend: a deterministic TYPED dict (per-sensor-type fields,
            ``"typed": True``).
          - MODERN backend: a RAW gz-text echo (``{"format": "gz-text", "raw":
            ..., "typed": False}``); typed parsing into the mock-equivalent
            shapes is DEFERRED to P2-real ros_gz subscription parsing.

        Args:
            topic: The sensor's topic (e.g. "/scan", "/imu")
            world: World name

        Returns:
            A sample dict; shape depends on backend + sensor type (see above).

        Raises:
            KeyError: If no sensor publishes on ``topic``.
        """
        raise NotImplementedError(
            f"sensor_snapshot() not implemented for backend '{self.get_backend_name()}'"
        )

    async def sensor_camera_image(
        self,
        topic: str,
        resolution: str = "640x480",
        quality: int = 60,
        world: str = "default",
    ) -> Dict[str, Any]:
        """
        Return a single encoded image from the camera publishing on ``topic``.

        Args:
            topic: Camera image topic (e.g. "/camera/image_raw")
            resolution: Target image resolution as "WxH" (each dim capped)
            quality: Encoding quality hint (0-100, used for lossy formats)
            world: World name

        Returns:
            Dict with {"data": bytes, "format": "png"|"jpeg", "width": int, "height": int}

        Raises:
            KeyError: If ``topic`` is not a camera image topic.
        """
        raise NotImplementedError(
            f"sensor_camera_image() not implemented for backend '{self.get_backend_name()}'"
        )

    async def param_list(self, world: str = "default") -> List[str]:
        """
        List available simulation parameter names.

        Args:
            world: World name

        Returns:
            Sorted list of parameter names.
        """
        raise NotImplementedError(
            f"param_list() not implemented for backend '{self.get_backend_name()}'"
        )

    async def param_get(self, name: str, world: str = "default") -> Dict[str, Any]:
        """
        Get a single parameter's value.

        Args:
            name: Parameter name
            world: World name

        Returns:
            Dict with {"name", "type", "value"}.

        Raises:
            KeyError: If the parameter is unknown.
        """
        raise NotImplementedError(
            f"param_get() not implemented for backend '{self.get_backend_name()}'"
        )

    async def param_set(self, name: str, value: Any, world: str = "default") -> bool:
        """
        Set (or create) a parameter's value.

        Args:
            name: Parameter name
            value: New value (type inferred from the Python type)
            world: World name

        Returns:
            True if applied successfully.
        """
        raise NotImplementedError(
            f"param_set() not implemented for backend '{self.get_backend_name()}'"
        )
