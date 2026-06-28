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
