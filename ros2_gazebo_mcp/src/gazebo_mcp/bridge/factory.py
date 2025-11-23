"""
Gazebo adapter factory.

Creates appropriate Gazebo adapter based on configuration.
"""

from .config import GazeboConfig, GazeboBackend
from .detection import GazeboDetector
from .gazebo_interface import GazeboInterface
from .adapters.classic_adapter import ClassicGazeboAdapter
from .adapters.modern_adapter import ModernGazeboAdapter


class GazeboAdapterFactory:
    """
    Factory for creating appropriate Gazebo adapter.

    Encapsulates adapter creation logic and backend selection.
    """

    def __init__(self, node, config: GazeboConfig):
        """
        Initialize factory.

        Args:
            node: ROS2 node for adapter creation
            config: Gazebo configuration
        """
        self.node = node
        self.config = config
        self.detector = GazeboDetector(node)

    def create_adapter(self) -> GazeboInterface:
        """
        Create appropriate Gazebo adapter.

        Logic:
        1. If backend explicitly set in config, use that
        2. If AUTO, detect running Gazebo version
        3. Create corresponding adapter
        4. Return via GazeboInterface (polymorphism)

        Returns:
            GazeboInterface implementation (Classic or Modern)

        Raises:
            RuntimeError: If auto-detection fails
            NotImplementedError: If Modern selected but not implemented yet
        """
        # Determine backend
        if self.config.backend == GazeboBackend.AUTO:
            backend = self.detector.detect()
            self.node.get_logger().info(
                f"Auto-detected Gazebo backend: {backend.value}"
            )
        else:
            backend = self.config.backend
            self.node.get_logger().info(
                f"Using configured backend: {backend.value}"
            )

        # Create adapter
        if backend == GazeboBackend.CLASSIC:
            return ClassicGazeboAdapter(
                self.node,
                timeout=self.config.timeout
            )
        elif backend == GazeboBackend.MODERN:
            return ModernGazeboAdapter(
                self.node,
                default_world=self.config.world_name,
                timeout=self.config.timeout
            )
        else:
            raise ValueError(f"Unknown backend: {backend}")
