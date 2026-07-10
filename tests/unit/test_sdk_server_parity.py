"""
Curated-registry integrity + unified-app parity.

Originally these asserted the SDK low-level server (``sdk_app.build_server``) and
the hand-rolled ``GazeboMCPServer`` exposed identical tool surfaces — the Step-0
migration proof. Both of those servers are RETIRED (P*-real C3); the unified
FastMCP app is the sole server. So this now guarantees:
  1. the curated registry still holds exactly the 69 legacy tools (names/schemas), and
  2. the unified app MOUNTS every one of them (name-level parity).

NOTE: the unified app's *advertised* inputSchema is INFERRED by FastMCP from the
synthesized signature, so it is NOT byte-identical to the curated schema (the
documented FastMCP-1.27.1 coupling — see plan §P3 #1). We therefore assert
name-level parity here; curated array-item fidelity is covered by
``test_p3_schema_fidelity.py``.
"""

import sys
from pathlib import Path

import anyio

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gz_mcp_server.server.registry import build_registry
from gz_mcp_server.server.app import build_app

EXPECTED_TOOL_COUNT = 69


def test_registry_has_expected_tool_count():
    tools, handlers = build_registry()
    assert len(tools) == EXPECTED_TOOL_COUNT
    assert len(handlers) == EXPECTED_TOOL_COUNT
    names = {t.name for t in tools}
    assert len(names) == EXPECTED_TOOL_COUNT, "duplicate tool names in registry"
    assert all(n.startswith("gazebo_") for n in names)


def test_unified_app_mounts_every_registry_tool():
    """Every curated registry tool name is served by the unified FastMCP app
    (name-level parity — the surviving guarantee after the low-level server retire)."""

    async def _run():
        tools, _ = build_registry()
        registry_names = {t.name for t in tools}

        mcp = build_app()
        app_names = {t.name for t in await mcp.list_tools()}

        missing = registry_names - app_names
        assert not missing, f"unified app is missing curated tools: {sorted(missing)}"

    anyio.run(_run)
