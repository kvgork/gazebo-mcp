"""
Step-0 parity tests: the SDK low-level server exposes exactly the same tool
surface as the legacy hand-rolled server, and serves it over a compliant MCP
session (initialize → tools/list → tools/call) via the SDK in-memory client.

These tests are transport/lifecycle-level (not a `<<<` heredoc) and prove the
migration is behaviour-preserving before the legacy server is retired.
"""

import json
import sys
from pathlib import Path

import anyio

# Repo root on path so the top-level gz_mcp_server package resolves:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.shared.memory import create_connected_server_and_client_session as client_session

from gz_mcp_server.server.sdk_app import build_server, _build_registry
from gz_mcp_server.server.server import GazeboMCPServer

EXPECTED_TOOL_COUNT = 69


def test_registry_has_expected_tool_count():
    tools, handlers = _build_registry()
    assert len(tools) == EXPECTED_TOOL_COUNT
    assert len(handlers) == EXPECTED_TOOL_COUNT
    names = {t.name for t in tools}
    assert len(names) == EXPECTED_TOOL_COUNT, "duplicate tool names in registry"
    assert all(n.startswith("gazebo_") for n in names)


def test_schema_parity_with_legacy_server():
    """Every tool name + inputSchema matches the legacy hand-rolled server exactly."""
    legacy = {d["name"]: d["inputSchema"] for d in GazeboMCPServer().list_tools()}
    tools, _ = _build_registry()
    sdk = {t.name: t.inputSchema for t in tools}

    assert set(sdk) == set(legacy), "tool name set diverged from legacy server"
    for name in sdk:
        assert sdk[name] == legacy[name], f"input schema drift for {name}"


def test_in_memory_client_lists_all_tools():
    """A real MCP session (initialize handshake handled by the helper) lists all tools."""

    async def _run():
        server = build_server()
        async with client_session(server) as client:
            result = await client.list_tools()
            names = {t.name for t in result.tools}
            assert len(names) == EXPECTED_TOOL_COUNT
            # Spot-check one tool from each of the four new areas:
            for expected in (
                "gazebo_spawn_robot_fleet",
                "gazebo_fuse_sensor_data",
                "gazebo_start_slam",
                "gazebo_initialize_nav2",
            ):
                assert expected in names

    anyio.run(_run)


def test_in_memory_client_calls_a_tool():
    """A tool call over the session returns the OperationResult payload as JSON content."""

    async def _run():
        server = build_server()
        async with client_session(server) as client:
            result = await client.call_tool(
                "gazebo_spawn_robot_fleet",
                {"robot_type": "turtlebot3", "count": 4, "formation": "grid"},
            )
            assert result.content, "no content returned"
            payload = json.loads(result.content[0].text)
            assert payload["success"] is True
            assert payload["data"]["count"] == 4
            assert len(payload["data"]["robots"]) == 4

    anyio.run(_run)


def test_in_memory_client_invalid_args_surface_failure():
    """Invalid enum is reported as a failed OperationResult (success=False), not a crash."""

    async def _run():
        server = build_server()
        async with client_session(server) as client:
            result = await client.call_tool(
                "gazebo_spawn_robot_fleet",
                {"robot_type": "turtlebot3", "count": 2, "formation": "not_a_formation"},
            )
            payload = json.loads(result.content[0].text)
            assert payload["success"] is False

    anyio.run(_run)
