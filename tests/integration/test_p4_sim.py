"""
P4 headline acceptance: the OPTIONAL ``sim_*`` REP-2018 ``simulation_interfaces``
portability shim, mock-verified in-process, with NO Gazebo / ROS2 running.

The ``sim_*`` tools are strictly non-default: ``build_app()`` only registers
them when ``GAZEBO_SIM_TOOLS=1`` (see ``gz_mcp_server.server.app.build_app``).
This module sets that flag (alongside the existing mock-backend override) so
the tools mount for every test here, and separately verifies the OFF/default
gating behaviour in ``test_p4_sim_tools_gated_off_by_default``.

Backend selection caveat (authoritative, mirrored from ``test_p1_actuation.py``):
pixi ``[activation.env]`` sets ``GAZEBO_BACKEND=modern``, which OVERRIDES a
shell ``GAZEBO_BACKEND=mock pixi run``. We therefore force mock IN-PROCESS via
``monkeypatch.setenv`` in an autouse fixture (set before any tool call,
auto-reverted afterwards) and reset the bridge-helper singleton in the same
fixture so the mock backend is actually constructed.

The session is driven via the SDK in-memory client against the FastMCP app's
low-level server (``mcp._mcp_server``), mirroring ``test_p1_actuation.py``.
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

_SIM_TOOL_NAMES = {"sim_spawn", "sim_delete", "sim_reset", "sim_step", "sim_get_features"}


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend + enable sim_* tools for this module.

    See ``test_p1_actuation.py``'s identically-named fixture for the full
    rationale on forcing the backend in-process. This module additionally sets
    ``GAZEBO_SIM_TOOLS=1`` so the P4 shim tools are mounted by ``build_app()``;
    both env vars auto-revert after each test via ``monkeypatch``, so they never
    leak into other test modules (which expect sim_* absent by default).
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    monkeypatch.setenv("GAZEBO_SIM_TOOLS", "1")
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


def test_p4_sim_tools_gated_off_by_default(monkeypatch):
    """Without GAZEBO_SIM_TOOLS=1 (unset or "0"), sim_* is absent from list_tools."""
    monkeypatch.delenv("GAZEBO_SIM_TOOLS", raising=False)

    async def _run_unset():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert not (_SIM_TOOL_NAMES & names), f"sim_* leaked: {_SIM_TOOL_NAMES & names}"

    anyio.run(_run_unset)

    monkeypatch.setenv("GAZEBO_SIM_TOOLS", "0")

    async def _run_zero():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert not (_SIM_TOOL_NAMES & names), f"sim_* leaked: {_SIM_TOOL_NAMES & names}"

    anyio.run(_run_zero)


def test_p4_sim_tools_listed_when_enabled():
    """With GAZEBO_SIM_TOOLS=1 (set by the autouse fixture), all 5 sim_* are present."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert _SIM_TOOL_NAMES <= names, f"missing sim tools: {_SIM_TOOL_NAMES - names}"

    anyio.run(_run)


def test_p4_sim_get_features():
    """sim_get_features reports the REP-2018 shim capability, no mutation."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = _payload(await client.call_tool("sim_get_features", {}))
            assert result["success"] is True, result
            data = result["data"]
            assert "spawn" in data["supported_ops"]
            assert "step" in data["supported_ops"]
            assert data["backend"] in ("mock",)
            # The REP-2018 SimInterfacesAdapter now exists + is live-verified
            # (P4-real DONE 2026-07-08); it is reported as available but not yet
            # wired into default backend-selection.
            assert "available" in data["real_adapter"]
            assert "SimInterfacesAdapter" in data["real_adapter"]
            assert data["world"] == "default"

    anyio.run(_run)


def test_p4_sim_spawn_parity_with_scene_get_state():
    """sim_spawn(x=1,y=2,z=0.5) then scene_get_state -> pose (1,2,0.5)."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            spawn = _payload(
                await client.call_tool(
                    "sim_spawn",
                    {"name": "cube", "sdf": CUBE_SDF, "x": 1.0, "y": 2.0, "z": 0.5},
                )
            )
            assert spawn["success"] is True, spawn

            state = _payload(await client.call_tool("scene_get_state", {"name": "cube"}))
            assert state["success"] is True, state
            pos = state["data"]["pose"]["position"]
            assert pos[0] == pytest.approx(1.0)
            assert pos[1] == pytest.approx(2.0)
            assert pos[2] == pytest.approx(0.5)

    anyio.run(_run)


def test_p4_sim_step_advances_sim_time():
    """sim_step(steps=10) succeeds and sim_time advances."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            before = _payload(await client.call_tool("sim_get_features", {}))
            assert before["success"] is True, before

            step = _payload(await client.call_tool("sim_step", {"steps": 10}))
            assert step["success"] is True, step
            assert step["data"]["sim_time"] > 0.0
            assert step["data"]["steps"] == 10

    anyio.run(_run)


def test_p4_sim_delete_removes_entity():
    """sim_delete succeeds; a subsequent scene_get_state fails/absent."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            spawn = _payload(
                await client.call_tool(
                    "sim_spawn", {"name": "widget", "sdf": CUBE_SDF}
                )
            )
            assert spawn["success"] is True, spawn

            delete = _payload(await client.call_tool("sim_delete", {"name": "widget"}))
            assert delete["success"] is True, delete

            state = _payload(await client.call_tool("scene_get_state", {"name": "widget"}))
            assert state["success"] is False, state
            assert state["error_code"] == "MODEL_NOT_FOUND"

    anyio.run(_run)


def test_p4_sim_reset():
    """sim_reset succeeds and reports the world."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            result = _payload(await client.call_tool("sim_reset", {}))
            assert result["success"] is True, result
            assert result["data"]["world"] == "default"

    anyio.run(_run)
