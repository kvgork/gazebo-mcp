"""
GazeboDetector backend-fallback policy (P*-real #6).

When no live Gazebo is detected, the detector falls back to the MOCK backend so
no-Gazebo dev/CI stays usable — but in PRODUCTION that would silently serve fake
data behind a real-looking API. ``GAZEBO_STRICT_BACKEND`` is the opt-in gate that
turns the fallback into a hard failure. These tests pin BOTH modes and need no
live Gazebo (a stub node reports zero services; no gz process is running in CI).
"""

import pytest

from gazebo_mcp.bridge.detection import GazeboDetector
from gazebo_mcp.bridge.config import GazeboBackend
from gazebo_mcp.utils.exceptions import GazeboNotRunningError


class _Logger:
    def info(self, *a, **k): ...
    def warn(self, *a, **k): ...
    def debug(self, *a, **k): ...


class _NoGazeboNode:
    """A ROS node stub that advertises no services (i.e. no live Gazebo)."""

    def get_service_names_and_types(self):
        return []

    def get_logger(self):
        return _Logger()


@pytest.fixture
def no_gazebo_detector(monkeypatch):
    """A detector whose service AND process checks all report 'no Gazebo', so the
    fallback/gate logic is exercised hermetically — independent of any real
    ``gz sim`` process that may be running on the host (e.g. a leftover from a
    live test)."""
    monkeypatch.setattr(GazeboDetector, "_check_modern_process", lambda self: False)
    monkeypatch.setattr(GazeboDetector, "_check_classic_process", lambda self: False)
    return GazeboDetector(_NoGazeboNode())


def test_fallback_to_mock_when_not_strict(monkeypatch, no_gazebo_detector):
    monkeypatch.setenv("GAZEBO_STRICT_BACKEND", "0")
    assert no_gazebo_detector.detect() is GazeboBackend.MOCK


def test_fallback_to_mock_when_gate_unset(monkeypatch, no_gazebo_detector):
    monkeypatch.delenv("GAZEBO_STRICT_BACKEND", raising=False)
    assert no_gazebo_detector.detect() is GazeboBackend.MOCK


@pytest.mark.parametrize("val", ["1", "true", "yes"])
def test_strict_gate_hard_fails(monkeypatch, no_gazebo_detector, val):
    monkeypatch.setenv("GAZEBO_STRICT_BACKEND", val)
    with pytest.raises(GazeboNotRunningError):
        no_gazebo_detector.detect()
