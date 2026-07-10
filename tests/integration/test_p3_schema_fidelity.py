"""
P3 #1 — legacy-tool schema fidelity on the unified FastMCP app.

The P3 unification mounts the 69 curated legacy tools as native FastMCP tools,
whose advertised ``inputSchema`` is INFERRED from a synthesized typed signature
(``legacy_mount._make_legacy_closure`` / ``_hint_for``). Before the P3 #1 fix an
``array`` param was hinted as a bare ``list`` — so FastMCP advertised
``{"type": "array"}`` with NO ``items``, losing the curated schema's item typing.

This module locks in the fidelity fix: array params whose curated schema carries
``items: {type: ...}`` must advertise a matching ``items`` block on the unified
app's ``tools/list`` output.

RESIDUAL (documented, NOT a bug): ``object`` params stay bare ``dict`` (no nested
``properties``), and because FastMCP 1.27.1 derives BOTH the advertised schema
AND pre-handler validation from the same inferred ``arg_model``, restoring array
item typing also tightens ``tools/call`` validation to that item type — a
deliberate trade-off favouring schema fidelity + standard JSON-RPC validation
over the legacy rich-``OperationResult``-on-bad-type. See
``gz_mcp_server/server/legacy_mount.py`` and plan §P3 STATUS.
"""

import sys
from pathlib import Path

import anyio

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gz_mcp_server.server.app import build_app  # noqa: E402


def _schema(tools, name):
    for t in tools:
        if t.name == name:
            return t.inputSchema or {}
    raise AssertionError(f"tool {name!r} not found on the unified app")


def test_legacy_array_param_advertises_item_typing():
    """An array-of-string legacy param must advertise items:{type:string}."""

    async def _run():
        mcp = build_app()
        tools = await mcp.list_tools()
        # gazebo_fuse_sensor_data.sensors is a curated array-of-string param.
        schema = _schema(tools, "gazebo_fuse_sensor_data")
        sensors = schema.get("properties", {}).get("sensors", {})
        assert sensors.get("type") == "array", sensors
        assert sensors.get("items", {}).get("type") == "string", (
            f"array item typing lost (P3 #1 regression): {sensors}"
        )

    anyio.run(_run)


def test_legacy_array_of_object_param_advertises_object_items():
    """An array-of-object legacy param must advertise items:{type:object}."""

    async def _run():
        mcp = build_app()
        tools = await mcp.list_tools()
        # gazebo_follow_waypoints.waypoints is a curated array-of-object param.
        schema = _schema(tools, "gazebo_follow_waypoints")
        wp = schema.get("properties", {}).get("waypoints", {})
        assert wp.get("type") == "array", wp
        assert wp.get("items", {}).get("type") == "object", (
            f"array-of-object item typing lost (P3 #1 regression): {wp}"
        )

    anyio.run(_run)
