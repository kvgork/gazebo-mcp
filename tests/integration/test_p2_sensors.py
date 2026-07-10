"""
P2 sensor acceptance: the lean ``sensor_*`` tools served by the FastMCP app
return deterministic mock sensor descriptors, typed snapshots, and a real PNG
camera image end-to-end over a real MCP session, with NO Gazebo / ROS2 running.

The MOCK backend (``GAZEBO_BACKEND=mock``) is an honest in-memory implementation,
so the sensor surface is fully deterministic under ``-e dev``. Real-backend
equivalents (``-m gazebo``, ``-e sim``/``-e full``) are deferred until ros_gz +
a live camera + gz topic introspection are installed.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern``, which OVERRIDES a shell ``GAZEBO_BACKEND=mock pixi
run``. We therefore force mock IN-PROCESS — via ``monkeypatch.setenv`` in an
autouse fixture (set before any tool call, auto-reverted afterwards, never
leaking into other test modules that rely on the default ``modern`` backend) —
and reset the bridge-helper singleton in the same fixture so the mock backend is
actually constructed. ``GazeboConfig.from_environment()`` reads ``GAZEBO_BACKEND``
lazily at ``get_bridge()`` call time, so per-test env setting is sufficient.

The session is driven via the SDK in-memory client against the FastMCP app's
low-level server (``mcp._mcp_server``), mirroring ``test_p1_actuation.py``.

The camera tool is special: its FastMCP wrapper returns a FastMCP ``Image`` on
success, which the in-memory MCP client surfaces as an ``ImageContent`` block
(``type == "image"``, ``mimeType == "image/png"``) — NOT a JSON OperationResult.
We therefore assert the content block TYPE for the success path, and only fall
back to JSON parsing for the error path.
"""

import json
import sys
from pathlib import Path

import anyio
import pytest

# Repo root + src on path so both the top-level gz_mcp_server package and the
# gazebo_mcp package (under src/) resolve.
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.shared.memory import create_connected_server_and_client_session as client_session

from gz_mcp_server.server.app import build_app


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` for the
    duration of each test and auto-reverts afterwards, so it never leaks into
    other test modules that expect the default backend. The helper caches a
    module-level bridge node; clearing it (before and after) guarantees each
    test constructs the deterministic MockGazeboAdapter rather than reusing
    state from another test or backend.
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


def _payload(result):
    """Extract the OperationResult dict from an MCP call_tool result's content."""
    assert result.content, "no content returned from tool call"
    return json.loads(result.content[0].text)


def test_p2_sensor_list_returns_descriptors_with_health_and_camera():
    """sensor_list -> >=4 sensors, each carries a ``health`` field, and a camera
    topic ``/camera/image_raw`` is present."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            listed = _payload(await client.call_tool("sensor_list", {}))
            assert listed["success"] is True, listed

            sensors = listed["data"]["sensors"]
            assert listed["data"]["count"] == len(sensors)
            assert len(sensors) >= 4, sensors

            # Every descriptor carries a health field (folds in monitor_sensor_health).
            for s in sensors:
                assert "health" in s, s

            topics = {s["topic"] for s in sensors}
            assert "/camera/image_raw" in topics, topics

    anyio.run(_run)


def test_p2_sensor_list_concise_trims_descriptor_fields():
    """response_format='concise' trims each descriptor to {name,topic,type,health}
    (token economy), while 'detailed' (default) keeps the full descriptor."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            detailed = _payload(await client.call_tool("sensor_list", {}))["data"]["sensors"]
            concise = _payload(
                await client.call_tool("sensor_list", {"response_format": "concise"})
            )["data"]["sensors"]

            assert len(concise) == len(detailed)
            allowed = {"name", "topic", "type", "health"}
            for s in concise:
                assert set(s).issubset(allowed), s
                assert "health" in s  # essential field retained
            # concise must not be strictly richer than detailed (it's a trim).
            assert sum(len(s) for s in concise) <= sum(len(s) for s in detailed)

    anyio.run(_run)


def test_p2_sensor_list_filtered_by_type_returns_only_cameras():
    """sensor_list(sensor_type="camera") -> only camera descriptors."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            listed = _payload(
                await client.call_tool("sensor_list", {"sensor_type": "camera"})
            )
            assert listed["success"] is True, listed

            sensors = listed["data"]["sensors"]
            assert len(sensors) >= 1, sensors
            assert all(s["type"] == "camera" for s in sensors), sensors
            assert {s["topic"] for s in sensors} == {"/camera/image_raw"}

    anyio.run(_run)


def test_p2_sensor_snapshot_imu_typed_sample_fixed_timestamp():
    """sensor_snapshot('/imu') -> typed imu sample with linear_acceleration and
    the fixed deterministic timestamp."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            snap = _payload(await client.call_tool("sensor_snapshot", {"topic": "/imu"}))
            assert snap["success"] is True, snap

            data = snap["data"]
            assert data["type"] == "imu"
            assert "linear_acceleration" in data, data
            assert data["timestamp"] == "2026-01-01T00:00:00Z"

    anyio.run(_run)


def test_p2_sensor_snapshot_unknown_topic_rejected():
    """sensor_snapshot('/nope') -> success False, error_code UNKNOWN_TOPIC."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            snap = _payload(await client.call_tool("sensor_snapshot", {"topic": "/nope"}))
            assert snap["success"] is False, snap
            assert snap["error_code"] == "UNKNOWN_TOPIC"

    anyio.run(_run)


def test_p2_sensor_camera_image_returns_image_content():
    """sensor_camera_image('/camera/image_raw', '320x240') -> an ImageContent
    block (type 'image', mimeType 'image/png'), NOT a JSON OperationResult."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.call_tool(
                "sensor_camera_image",
                {"topic": "/camera/image_raw", "resolution": "320x240"},
            )
            assert result.content, "no content returned from camera tool"
            block = result.content[0]

            # The FastMCP Image wrapper surfaces as an ImageContent block.
            assert getattr(block, "type", None) == "image", block
            assert getattr(block, "mimeType", None) == "image/png", block
            # A real (non-empty) base64 PNG payload is carried, not a JSON error.
            assert getattr(block, "data", None), block

    anyio.run(_run)


def test_p2_sensor_camera_image_too_large_rejected():
    """sensor_camera_image('/camera/image_raw', '9999x9999') -> a JSON error
    result with error_code IMAGE_TOO_LARGE (NOT an Image)."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.call_tool(
                "sensor_camera_image",
                {"topic": "/camera/image_raw", "resolution": "9999x9999"},
            )
            # The failure path returns the OperationResult dict as text content,
            # not an Image — so the first block is text we can JSON-parse.
            assert result.content, "no content returned from camera tool"
            block = result.content[0]
            assert getattr(block, "type", None) == "text", block

            payload = _payload(result)
            assert payload["success"] is False, payload
            assert payload["error_code"] == "IMAGE_TOO_LARGE"

    anyio.run(_run)


def test_p2_six_sensor_tools_listed_among_lean():
    """tools/list exposes all six P2 tools among the 19 lean tools.

    P3 unified the 69 curated legacy tools onto this same FastMCP app, so the
    total advertised count is now lean + legacy (~88), not 19. This test pins the
    lean-surface contract: the 19 lean tools (including the six P2 tools) are all
    present, and the legacy unification has added more tools on top.
    """

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}

            p2_tools = {
                "sensor_list",
                "sensor_snapshot",
                "sensor_camera_image",
                "param_list",
                "param_get",
                "param_set",
            }
            lean_tools = {
                "world_step",
                "world_set_physics",
                "world_seed",
                "world_get_stats",
                "scene_spawn",
                "scene_get_state",
                "scene_set_state",
                "scene_remove",
                "scene_list_models",
                "actuate_wrench",
                "actuate_clear_wrench",
                "actuate_joint",
                "actuate_joint_trajectory",
            } | p2_tools
            assert p2_tools <= names, f"missing P2 tools: {p2_tools - names}"
            assert lean_tools <= names, f"missing lean tools: {lean_tools - names}"
            assert len(lean_tools) == 19, sorted(lean_tools)
            # P3 unification mounts the legacy tools on top of the 19 lean tools.
            assert len(names) > 19, sorted(names)

    anyio.run(_run)
