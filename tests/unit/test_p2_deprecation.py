"""
P2 advanced-sensor deprecation coverage (flag-gated).

The seven redundant advanced-sensor functions are deprecated in favour of the
lean ``sensor_*`` tools, but the deprecation is FLAG-GATED so the existing
``test_advanced_sensor_tools.py`` suite stays green by default. The guard fires
ONLY when ``GAZEBO_LEGACY_TOOLS == "0"``; the default (flag absent / "1") keeps
the real tool body running.

These tests assert both halves of that contract:
  - with ``GAZEBO_LEGACY_TOOLS=0``, each of the 7 guarded functions returns
    ``success=False, error_code="DEPRECATED_TOOL"`` BEFORE executing its body;
  - ``monitor_sensor_health`` is the retained survivor — it is NOT guarded and
    still succeeds even with the flag set;
  - with the flag UNSET (default), a guarded function (``fuse_sensor_data``) is
    NOT deprecated.

``monkeypatch.setenv`` / ``delenv`` auto-revert after each test, so no env leak.
The functions are called DIRECTLY (no FastMCP transport) and import from
``gazebo_mcp.tools.advanced_sensor_tools``.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.advanced_sensor_tools import (
    calibrate_sensor,
    detect_objects_in_view,
    fuse_sensor_data,
    monitor_sensor_health,
    process_sensor_data,
    record_sensor_stream,
    segment_camera_image,
    visualize_sensor_data,
)

# Each guarded function paired with a representative set of valid arguments so
# that — were the deprecation guard absent — the body would otherwise SUCCEED.
# This proves the guard short-circuits BEFORE the real body runs.
_GUARDED_CASES = [
    (fuse_sensor_data, ("lidar_camera", ["lidar_front", "camera_rgb"]), {}),
    (visualize_sensor_data, ("lidar_front", "point_cloud"), {}),
    (process_sensor_data, ("lidar_front", "voxel_filter"), {}),
    (calibrate_sensor, ("camera_rgb", "camera_intrinsics"), {}),
    (record_sensor_stream, (["lidar_front"], "/tmp/run1"), {}),
    (detect_objects_in_view, ("camera_rgb",), {}),
    (segment_camera_image, ("camera_rgb",), {}),
]


@pytest.mark.parametrize(
    "fn, args, kwargs",
    _GUARDED_CASES,
    ids=[case[0].__name__ for case in _GUARDED_CASES],
)
def test_guarded_fn_is_deprecated_when_flag_zero(monkeypatch, fn, args, kwargs):
    """With GAZEBO_LEGACY_TOOLS=0, each of the 7 guarded fns is DEPRECATED_TOOL."""
    monkeypatch.setenv("GAZEBO_LEGACY_TOOLS", "0")
    result = fn(*args, **kwargs)
    assert result.success is False, result
    assert result.error_code == "DEPRECATED_TOOL", result


def test_monitor_sensor_health_survives_flag_zero(monkeypatch):
    """The retained survivor is NOT guarded: it still succeeds with the flag set."""
    monkeypatch.setenv("GAZEBO_LEGACY_TOOLS", "0")
    result = monitor_sensor_health()
    assert result.success is True, result
    assert result.error_code != "DEPRECATED_TOOL", result


def test_guarded_fn_not_deprecated_when_flag_unset(monkeypatch):
    """With the flag UNSET (default), a guarded fn runs its real body (not deprecated)."""
    monkeypatch.delenv("GAZEBO_LEGACY_TOOLS", raising=False)
    result = fuse_sensor_data("lidar_camera", ["lidar_front", "camera_rgb"])
    assert result.success is True, result
    assert result.error_code != "DEPRECATED_TOOL", result
