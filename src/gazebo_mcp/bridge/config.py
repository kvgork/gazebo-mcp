"""
Gazebo backend configuration system.

Manages backend selection (Classic vs Modern) via environment variables.
"""

import os
from enum import Enum
from typing import Optional


class GazeboBackend(Enum):
    """Available Gazebo backends."""
    CLASSIC = "classic"
    MODERN = "modern"
    AUTO = "auto"
    MOCK = "mock"  # In-memory deterministic backend for CI / no-Gazebo dev


class GazeboConfig:
    """
    Configuration for Gazebo backend selection.

    Environment Variables:
    - GAZEBO_BACKEND: 'classic', 'modern', or 'auto' (default: modern)
    - GAZEBO_WORLD_NAME: Default world name for Modern (default: 'default')
    - GAZEBO_TIMEOUT: Service call timeout in seconds (default: 5.0)

    NOTE: Classic Gazebo is DEPRECATED and will be removed in v2.0.0.
          Default is now 'modern' to encourage migration.
    """

    def __init__(
        self,
        backend: Optional[GazeboBackend] = None,
        world_name: str = "default",
        timeout: float = 5.0,
        own_world: bool = False,
        step_size: float = 0.001,
        rtf: float = 1.0,
        model_manifest: Optional[str] = None,
    ):
        """
        Initialize Gazebo configuration.

        Args:
            backend: Gazebo backend to use (reads from env if None)
            world_name: Default world name
            timeout: Service call timeout in seconds
            own_world: If True, the bridge provisions and owns its own world
                (OWN mode); if False, it attaches to an externally-launched
                world (ATTACH mode). Reads GAZEBO_OWN_WORLD when default.
            step_size: Physics step size in seconds (max_step_size).
            rtf: Target real-time factor for the provisioned world.
            model_manifest: Optional path to a JSON manifest describing models
                to pre-spawn into a provisioned world (None = none).
        """
        # Read from environment if not provided
        # Default changed from 'auto' to 'modern' (Classic is deprecated)
        if backend is None:
            backend_str = os.getenv('GAZEBO_BACKEND', 'modern').lower()
            try:
                backend = GazeboBackend(backend_str)
            except ValueError:
                raise ValueError(
                    f"Invalid GAZEBO_BACKEND: {backend_str}. "
                    f"Must be 'classic', 'modern', 'auto', or 'mock'"
                )

        self.backend = backend
        self.world_name = world_name
        self.timeout = timeout
        self.own_world = own_world
        self.step_size = step_size
        self.rtf = rtf
        self.model_manifest = model_manifest

        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if not self.world_name:
            raise ValueError("World name cannot be empty")

        if self.step_size <= 0:
            raise ValueError("step_size must be positive")

        if self.rtf <= 0:
            raise ValueError("rtf must be positive")

    @staticmethod
    def from_environment() -> 'GazeboConfig':
        """
        Create config from environment variables.

        Environment Variables:
        - GAZEBO_BACKEND, GAZEBO_WORLD_NAME, GAZEBO_TIMEOUT
        - GAZEBO_OWN_WORLD: '1'/'true'/'yes' enables OWN mode (default: False)
        - GAZEBO_STEP_SIZE: physics step size in seconds (default: 0.001)
        - GAZEBO_RTF: target real-time factor (default: 1.0)
        - GAZEBO_MODEL_MANIFEST: path to a JSON model manifest (default: None)

        Returns:
            GazeboConfig instance
        """
        return GazeboConfig(
            backend=None,  # Read from GAZEBO_BACKEND
            world_name=os.getenv('GAZEBO_WORLD_NAME', 'default'),
            timeout=float(os.getenv('GAZEBO_TIMEOUT', '5.0')),
            own_world=os.getenv('GAZEBO_OWN_WORLD', '0').lower() in ('1', 'true', 'yes'),
            step_size=float(os.getenv('GAZEBO_STEP_SIZE', '0.001')),
            rtf=float(os.getenv('GAZEBO_RTF', '1.0')),
            model_manifest=os.getenv('GAZEBO_MODEL_MANIFEST'),
        )

    # Spec alias — `from_env()` is the name used by the P0-B contract.
    from_env = from_environment

    def __repr__(self) -> str:
        return (
            f"GazeboConfig(backend={self.backend.value}, "
            f"world_name={self.world_name}, timeout={self.timeout}, "
            f"own_world={self.own_world}, step_size={self.step_size}, "
            f"rtf={self.rtf}, model_manifest={self.model_manifest})"
        )
