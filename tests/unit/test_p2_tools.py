"""
Focused unit tests for the lean P2 sensor/param tools.

These exercise the framework-agnostic async functions in
``gazebo_mcp.tools.sensor`` and ``gazebo_mcp.tools.param`` DIRECTLY (not via the
FastMCP transport), asserting the ``OperationResult`` they return against the
deterministic MOCK backend. They complement the in-memory FastMCP acceptance
tests by covering the underlying tool data shapes (camera b64 under the ceiling,
param type inference) without the Image wrapper in the way.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern`` which OVERRIDES a shell ``GAZEBO_BACKEND=mock``. We
force mock IN-PROCESS via ``monkeypatch.setenv`` in an autouse fixture (set
before every tool call, auto-reverted afterwards) and reset the bridge-helper
singleton per-test so each test runs against a fresh empty mock world.
"""

import base64
import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import param as param_tools
from gazebo_mcp.tools import sensor as sensor_tools
from gazebo_mcp.tools.sensor import MAX_IMAGE_B64_BYTES


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton."""
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


# --------------------------------------------------------------------------
# sensor.sensor_camera_image
# --------------------------------------------------------------------------


def test_sensor_camera_image_b64_under_ceiling_and_decodes_to_png():
    """A modest camera image succeeds with a base64 payload under the ceiling that
    decodes to real PNG-signature bytes."""

    async def _run():
        result = await sensor_tools.sensor_camera_image(
            topic="/camera/image_raw", resolution="320x240"
        )
        assert result.success is True, result
        assert result.data["format"] == "png"
        assert result.data["width"] == 320
        assert result.data["height"] == 240

        b64 = result.data["image_b64"]
        assert result.data["bytes_b64"] == len(b64)
        assert len(b64) <= MAX_IMAGE_B64_BYTES

        raw = base64.b64decode(b64)
        assert raw.startswith(b"\x89PNG\r\n\x1a\n"), "decoded bytes are not a PNG"

    anyio.run(_run)


def test_sensor_camera_image_non_camera_topic_rejected():
    """A non-camera topic maps the bridge KeyError to error_code NOT_A_CAMERA."""

    async def _run():
        result = await sensor_tools.sensor_camera_image(topic="/scan", resolution="64x64")
        assert result.success is False, result
        assert result.error_code == "NOT_A_CAMERA"

    anyio.run(_run)


def test_sensor_camera_image_invalid_resolution_rejected():
    """A malformed resolution is rejected with INVALID_RESOLUTION before the bridge."""

    async def _run():
        result = await sensor_tools.sensor_camera_image(
            topic="/camera/image_raw", resolution="not-a-resolution"
        )
        assert result.success is False, result
        assert result.error_code == "INVALID_RESOLUTION"

    anyio.run(_run)


# --------------------------------------------------------------------------
# param type inference round-trips
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_type",
    [
        (5, "integer"),
        (0.001, "double"),
        (True, "boolean"),
        ("warehouse", "string"),
    ],
)
def test_param_set_then_get_infers_type(value, expected_type):
    """param_set infers the param type from the Python value; param_get reflects it."""

    async def _run():
        setres = await param_tools.param_set(name="test.typed", value=value)
        assert setres.success is True, setres
        assert setres.data["value"] == value

        got = await param_tools.param_get(name="test.typed")
        assert got.success is True, got
        assert got.data["value"] == value
        assert got.data["type"] == expected_type

    anyio.run(_run)


def test_param_list_includes_seeded_defaults():
    """The mock param store seeds the well-known physics/gravity defaults."""

    async def _run():
        result = await param_tools.param_list()
        assert result.success is True, result
        names = result.data["parameters"]
        assert "physics.max_step_size" in names
        assert "physics.real_time_factor" in names
        assert "gravity.z" in names

    anyio.run(_run)
