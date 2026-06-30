"""
P1 headline acceptance: the lean ``actuate_*`` tools served by the FastMCP app
drive deterministic mock physics end-to-end over a real MCP session, with NO
Gazebo / ROS2 running.

The MOCK backend (``GAZEBO_BACKEND=mock``) is an honest in-memory implementation,
so the wrench-integration and joint-limit chains are fully deterministic under
``-e dev``. Real-backend equivalents (``-m gazebo``, ``-e sim``/``-e full``) are
deferred until ros_gz + gz_ros2_control + the JETANK SDF are installed.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern``, which OVERRIDES a shell ``GAZEBO_BACKEND=mock pixi
run``. We therefore force mock IN-PROCESS — via ``monkeypatch.setenv`` in an
autouse fixture (set before any tool call, auto-reverted afterwards, never
leaking into other test modules that rely on the default ``modern`` backend) —
and reset the bridge-helper singleton in the same fixture so the mock backend is
actually constructed. ``GazeboConfig.from_environment()`` reads ``GAZEBO_BACKEND``
lazily at ``get_bridge()`` call time, so per-test env setting is sufficient.

The session is driven via the SDK in-memory client against the FastMCP app's
low-level server (``mcp._mcp_server``), mirroring ``test_p0_acceptance.py``.
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

CUBE_SDF = "<sdf version='1.7'/>"


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` for the
    duration of each test and auto-reverts afterwards, so it never leaks into
    other test modules that expect the default backend. The helper caches a
    module-level bridge node; clearing it (before and after) guarantees each
    test constructs the deterministic MockGazeboAdapter against an empty world
    rather than reusing state from another test or backend.
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


def test_p1_wrench_moves_entity():
    """Headline P1 chain: spawn cube@(0,0,0) -> wrench fx=10 -> step(100) ->
    read-back pose x == 0.5 * 10 * (100*0.001)**2 == 0.05 (y,z unchanged).
    """

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            spawn = _payload(
                await client.call_tool(
                    "scene_spawn",
                    {"name": "cube", "sdf": CUBE_SDF, "x": 0.0, "y": 0.0, "z": 0.0},
                )
            )
            assert spawn["success"] is True, spawn

            wrench = _payload(
                await client.call_tool("actuate_wrench", {"entity": "cube", "fx": 10.0})
            )
            assert wrench["success"] is True, wrench
            assert wrench["data"]["entity"] == "cube"
            assert wrench["data"]["force"] == pytest.approx([10.0, 0.0, 0.0])

            step = _payload(await client.call_tool("world_step", {"steps": 100}))
            assert step["success"] is True, step

            state = _payload(await client.call_tool("scene_get_state", {"name": "cube"}))
            assert state["success"] is True, state
            pos = state["data"]["pose"]["position"]
            assert pos[0] == pytest.approx(0.05)
            assert pos[1] == pytest.approx(0.0)
            assert pos[2] == pytest.approx(0.0)

    anyio.run(_run)


def test_p1_joint_within_limits():
    """A joint command inside the manifest [lower, upper] succeeds."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = _payload(
                await client.call_tool(
                    "actuate_joint",
                    {
                        "model": "jetank",
                        "joint": "arm_base_to_long_joint",
                        "mode": "pos",
                        "value": 0.5,
                    },
                )
            )
            assert result["success"] is True, result
            assert result["data"]["value"] == pytest.approx(0.5)

    anyio.run(_run)


def test_p1_joint_limit_rejected():
    """A pos command outside [lower, upper] is rejected with JOINT_LIMIT_EXCEEDED."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = _payload(
                await client.call_tool(
                    "actuate_joint",
                    {
                        "model": "jetank",
                        "joint": "arm_base_to_long_joint",
                        "mode": "pos",
                        "value": 2.0,
                    },
                )
            )
            assert result["success"] is False, result
            assert result["error_code"] == "JOINT_LIMIT_EXCEEDED"

    anyio.run(_run)


def test_p1_unknown_joint():
    """A joint absent from the manifest is rejected with UNKNOWN_JOINT."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = _payload(
                await client.call_tool(
                    "actuate_joint",
                    {
                        "model": "jetank",
                        "joint": "no_such_joint",
                        "mode": "pos",
                        "value": 0.1,
                    },
                )
            )
            assert result["success"] is False, result
            assert result["error_code"] == "UNKNOWN_JOINT"

    anyio.run(_run)


def test_p1_actuate_tools_listed():
    """tools/list exposes the four actuate_* tools."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            expected = {
                "actuate_wrench",
                "actuate_clear_wrench",
                "actuate_joint",
                "actuate_joint_trajectory",
            }
            assert expected <= names, f"missing actuate tools: {expected - names}"

    anyio.run(_run)
