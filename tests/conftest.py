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
    """True only if a LIVE Gazebo with the ros_gz bridge is reachable — i.e. the
    ``/world/default/create`` ROS service is present.

    ``import rclpy`` alone is NOT sufficient (it is importable in ``-e full``
    with no simulator running): the legacy tests using this fixture drive the
    bridge against an EXTERNALLY-launched gz + ros_gz bridge on world 'default',
    so they must SKIP (not fail) when none is up. The newer self-bring-up
    ``@pytest.mark.gazebo`` tests (test_p0b_real / test_p2_real_* /
    test_p4_real_*) manage their own gz and do NOT use this fixture."""
    try:
        import rclpy  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        return False
    import shutil
    import subprocess

    if shutil.which("ros2") is None:
        return False
    try:
        r = subprocess.run(
            ["ros2", "service", "list"], capture_output=True, text=True, timeout=10
        )
    except Exception:  # noqa: BLE001 - discovery failure -> treat as unavailable
        return False
    return "/world/default/create" in r.stdout


@pytest.fixture
def ros2_available():
    """Check if ROS2 is available (without importing rclpy at module level)."""
    try:
        import rclpy
        return True
    except (ImportError, ModuleNotFoundError):
        return False
