"""
Gazebo backend detection.

Auto-detects which Gazebo version is running (Classic vs Modern).
"""

import subprocess
from typing import Optional
from .config import GazeboBackend


class GazeboDetector:
    """
    Detect which Gazebo version is running.

    Detection Methods:
    1. Check for Modern services (/world/*/create)
    2. Check for Classic services (/gazebo/spawn_entity)
    3. Check process list (gazebo vs gz sim)
    """

    def __init__(self, node):
        """
        Initialize detector.

        Args:
            node: ROS2 node for querying services
        """
        self.node = node
        self._detected_backend: Optional[GazeboBackend] = None

    def detect(self) -> GazeboBackend:
        """
        Detect running Gazebo backend.

        Returns:
            GazeboBackend.MODERN if Fortress/Harmonic detected
            GazeboBackend.CLASSIC if Classic detected

        Raises:
            RuntimeError: If no Gazebo detected
        """
        if self._detected_backend:
            return self._detected_backend

        # Method 1: Check for Modern services
        if self._check_modern_services():
            self._detected_backend = GazeboBackend.MODERN
            self.node.get_logger().info("Detected Modern Gazebo (ros_gz)")
            return self._detected_backend

        # Method 2: Check for Classic services
        if self._check_classic_services():
            self._detected_backend = GazeboBackend.CLASSIC
            self.node.get_logger().info("Detected Classic Gazebo (gazebo_ros)")
            return self._detected_backend

        # Method 3: Check processes
        if self._check_modern_process():
            self._detected_backend = GazeboBackend.MODERN
            self.node.get_logger().warn(
                "Modern Gazebo process detected but services not available. "
                "Waiting for startup..."
            )
            return self._detected_backend

        if self._check_classic_process():
            self._detected_backend = GazeboBackend.CLASSIC
            self.node.get_logger().warn(
                "Classic Gazebo process detected but services not available. "
                "Waiting for startup..."
            )
            return self._detected_backend

        raise RuntimeError(
            "No Gazebo detected. Start Gazebo first:\n"
            "  Classic: gazebo --verbose\n"
            "  Modern:  gz sim -v4"
        )

    def _check_modern_services(self) -> bool:
        """Check if Modern Gazebo services exist."""
        try:
            service_names_and_types = self.node.get_service_names_and_types()

            # Look for /world/{name}/create pattern
            for name, _ in service_names_and_types:
                if '/world/' in name and '/create' in name:
                    return True
            return False
        except Exception as e:
            self.node.get_logger().debug(f"Error checking Modern services: {e}")
            return False

    def _check_classic_services(self) -> bool:
        """Check if Classic Gazebo services exist."""
        try:
            service_names_and_types = self.node.get_service_names_and_types()

            for name, _ in service_names_and_types:
                if name.startswith('/gazebo/'):
                    return True
            return False
        except Exception as e:
            self.node.get_logger().debug(f"Error checking Classic services: {e}")
            return False

    def _check_modern_process(self) -> bool:
        """Check if 'gz sim' process is running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'gz sim'],
                capture_output=True,
                timeout=1.0
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_classic_process(self) -> bool:
        """Check if 'gzserver' process is running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'gzserver'],
                capture_output=True,
                timeout=1.0
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
