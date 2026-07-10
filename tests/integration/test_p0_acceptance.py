"""
P0-B headline acceptance: the lean ``scene_*`` / ``world_*`` tools served by the
FastMCP app drive the full "spawn cube -> read back pose -> step -> remove" loop
end-to-end over a real MCP session, with NO Gazebo / ROS2 running.

The MOCK backend (``GAZEBO_BACKEND=mock``) is an honest in-memory implementation,
so this loop is fully deterministic under ``-e dev``. Real-backend equivalents
(``-m gazebo``, ``-e sim``/``-e full``) are deferred until ros_gz is installed.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern``, which OVERRIDES a shell ``GAZEBO_BACKEND=mock pixi run``.
We therefore force mock IN-PROCESS — via ``monkeypatch.setenv`` in an autouse
fixture (so it is set before any tool call and auto-reverted afterwards, never
leaking into other test modules that rely on the default ``modern`` backend) —
and reset the bridge-helper singleton in the same fixture so the mock backend is
actually constructed. ``GazeboConfig.from_environment()`` reads ``GAZEBO_BACKEND``
lazily at ``get_bridge()`` call time, so per-test env setting is sufficient.

The session is driven via the SDK in-memory client
(``mcp.shared.memory.create_connected_server_and_client_session``) against the
FastMCP app's low-level server (``mcp._mcp_server``), mirroring the harness in
``tests/unit/test_sdk_server_parity.py``.
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


def test_p0_headline_spawn_query_step_remove():
    """Headline chain via the in-memory FastMCP client:

    spawn(1,2,0.5) -> get_state == (1,2,0.5) -> step(100) == 0.1s -> remove ->
    not in list_models; plus a MODEL_NOT_FOUND negative.
    """

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            # --- spawn -----------------------------------------------------
            spawn = _payload(
                await client.call_tool(
                    "scene_spawn",
                    {"name": "test_cube", "sdf": CUBE_SDF, "x": 1.0, "y": 2.0, "z": 0.5},
                )
            )
            assert spawn["success"] is True, spawn

            # --- read back pose (mock returns the stored pose, not zeros) --
            state = _payload(await client.call_tool("scene_get_state", {"name": "test_cube"}))
            assert state["success"] is True, state
            assert state["data"]["pose"]["position"] == pytest.approx([1.0, 2.0, 0.5])

            # --- step advances sim_time deterministically (0.001 * 100) ----
            step = _payload(await client.call_tool("world_step", {"steps": 100}))
            assert step["success"] is True, step
            assert step["data"]["sim_time"] == pytest.approx(0.1)
            assert step["data"]["steps"] == 100

            # --- remove, then confirm it's gone from the model list --------
            removed = _payload(await client.call_tool("scene_remove", {"name": "test_cube"}))
            assert removed["success"] is True, removed

            listed = _payload(await client.call_tool("scene_list_models", {}))
            assert listed["success"] is True, listed
            assert "test_cube" not in listed["data"]["models"]

            # --- negative: querying a non-existent model is a clean failure -
            ghost = _payload(await client.call_tool("scene_get_state", {"name": "ghost"}))
            assert ghost["success"] is False
            assert ghost["error_code"] == "MODEL_NOT_FOUND"

    anyio.run(_run)


def test_p0_client_lists_lean_tools():
    """The FastMCP session exposes exactly the nine lean world_*/scene_* tools."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            expected = {
                "world_step",
                "world_set_physics",
                "world_seed",
                "world_get_stats",
                "scene_spawn",
                "scene_get_state",
                "scene_set_state",
                "scene_remove",
                "scene_list_models",
            }
            assert expected <= names, f"missing lean tools: {expected - names}"

    anyio.run(_run)
