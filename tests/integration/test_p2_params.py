"""
P2 parameter acceptance: the lean ``param_*`` tools served by the FastMCP app
list, round-trip, and reject simulation parameters end-to-end over a real MCP
session, with NO Gazebo / ROS2 running.

The MOCK backend (``GAZEBO_BACKEND=mock``) seeds a deterministic in-memory param
store, so this loop is fully deterministic under ``-e dev``. Real-backend
equivalents (``-m gazebo``, ``-e sim``/``-e full``) are deferred until gz
parameter services are reachable.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern``, which OVERRIDES a shell ``GAZEBO_BACKEND=mock pixi
run``. We force mock IN-PROCESS via ``monkeypatch.setenv`` in an autouse fixture
(set before any tool call, auto-reverted afterwards, never leaking into other
test modules) and reset the bridge-helper singleton so the mock backend — and
its fresh param store — is actually constructed per test.

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


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` for the
    duration of each test and auto-reverts afterwards, so it never leaks into
    other test modules that expect the default backend. Clearing the cached
    bridge node before/after each test guarantees a fresh, deterministic param
    store rather than reusing mutations from another test.
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


def test_p2_param_list_contains_physics_max_step_size():
    """param_list -> includes the seeded 'physics.max_step_size' parameter."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            listed = _payload(await client.call_tool("param_list", {}))
            assert listed["success"] is True, listed

            names = listed["data"]["parameters"]
            assert listed["data"]["count"] == len(names)
            assert "physics.max_step_size" in names, names

    anyio.run(_run)


def test_p2_param_set_then_get_round_trips():
    """param_set('test.foo', 5) then param_get('test.foo') -> value 5."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            setres = _payload(
                await client.call_tool("param_set", {"name": "test.foo", "value": 5})
            )
            assert setres["success"] is True, setres
            assert setres["data"]["name"] == "test.foo"
            assert setres["data"]["value"] == 5
            # applied reflects the bridge honestly (mock applies deterministically).
            assert setres["data"]["applied"] is True, setres

            got = _payload(await client.call_tool("param_get", {"name": "test.foo"}))
            assert got["success"] is True, got
            assert got["data"]["value"] == 5
            assert got["data"]["name"] == "test.foo"

    anyio.run(_run)


def test_p2_param_get_unknown_rejected():
    """param_get('does.not.exist') -> success False, error_code UNKNOWN_PARAM."""

    async def _run():
        mcp = build_app()
        async with client_session(mcp._mcp_server) as client:
            got = _payload(
                await client.call_tool("param_get", {"name": "does.not.exist"})
            )
            assert got["success"] is False, got
            assert got["error_code"] == "UNKNOWN_PARAM"

    anyio.run(_run)
