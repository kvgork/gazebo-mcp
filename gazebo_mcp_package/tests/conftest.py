"""
Pytest configuration and fixtures for Gazebo MCP tests.

Provides common fixtures for testing with/without Gazebo and ROS2.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--with-gazebo",
        action="store_true",
        default=False,
        help="Run tests that require Gazebo to be running",
    )
    parser.addoption(
        "--with-ros2",
        action="store_true",
        default=False,
        help="Run tests that require ROS2 to be sourced",
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "gazebo: mark test as requiring Gazebo")
    config.addinivalue_line("markers", "ros2: mark test as requiring ROS2")
    config.addinivalue_line("markers", "slow: mark test as slow")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on markers."""
    skip_gazebo = pytest.mark.skip(reason="need --with-gazebo option to run")
    skip_ros2 = pytest.mark.skip(reason="need --with-ros2 option to run")

    for item in items:
        if "gazebo" in item.keywords and not config.getoption("--with-gazebo"):
            item.add_marker(skip_gazebo)
        if "ros2" in item.keywords and not config.getoption("--with-ros2"):
            item.add_marker(skip_ros2)


@pytest.fixture
def gazebo_available():
    """Check if Gazebo is available (without importing rclpy at module level)."""
    try:
        import rclpy
        return True
    except (ImportError, ModuleNotFoundError):
        return False


@pytest.fixture
def ros2_available():
    """Check if ROS2 is available (without importing rclpy at module level)."""
    try:
        import rclpy
        return True
    except (ImportError, ModuleNotFoundError):
        return False
