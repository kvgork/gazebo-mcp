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
        timeout: float = 5.0
    ):
        """
        Initialize Gazebo configuration.

        Args:
            backend: Gazebo backend to use (reads from env if None)
            world_name: Default world name
            timeout: Service call timeout in seconds
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
                    f"Must be 'classic', 'modern', or 'auto'"
                )

        self.backend = backend
        self.world_name = world_name
        self.timeout = timeout

        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if not self.world_name:
            raise ValueError("World name cannot be empty")

    @staticmethod
    def from_environment() -> 'GazeboConfig':
        """
        Create config from environment variables.

        Returns:
            GazeboConfig instance
        """
        return GazeboConfig(
            backend=None,  # Read from GAZEBO_BACKEND
            world_name=os.getenv('GAZEBO_WORLD_NAME', 'default'),
            timeout=float(os.getenv('GAZEBO_TIMEOUT', '5.0'))
        )

    def __repr__(self) -> str:
        return (
            f"GazeboConfig(backend={self.backend.value}, "
            f"world_name={self.world_name}, timeout={self.timeout})"
        )
