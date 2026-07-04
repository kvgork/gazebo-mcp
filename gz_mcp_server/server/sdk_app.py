"""
SDK-based Gazebo MCP server (Step 0 of the architecture-evolution plan).

Replaces the hand-rolled JSON-RPC stdio server (``gz_mcp_server.server.server``)
with the official MCP SDK's low-level ``Server`` + compliant stdio transport,
while reusing the EXISTING adapter tool schemas and handlers verbatim — zero
schema drift, zero behaviour change. The legacy hand-rolled server is retained
behind its own entry point during the migration (see ``gazebo_mcp.server``).

Why the low-level ``Server`` and not ``FastMCP``: ``FastMCP.add_tool`` infers a
tool's input schema from the Python function signature. The current 69 tools are
adapter-wrapped handlers with hand-curated JSON schemas (enums, defaults) and
``**kwargs``-style call surfaces, so signature inference would corrupt them. The
low-level ``Server`` lets us return the curated ``Tool`` objects unchanged. New
lean tools (P0+) are authored fresh as ``@mcp.tool`` on FastMCP; the app shell
migrates to FastMCP when its resources/Context/Streamable-HTTP features land (P3).
"""

import json
import time
from typing import Any, Dict, List

import mcp.types as types
from mcp.server.lowlevel import Server

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.utils.metrics import get_metrics_collector
# The curated tool registry now lives in the shared `registry` module (C1) so
# the surviving unified app doesn't depend on this retiring low-level server.
from gz_mcp_server.server.registry import build_registry as _build_registry

_logger = get_logger("sdk_server")


def build_server() -> Server:
    """Build the low-level MCP ``Server`` with all tools registered for parity."""
    server: Server = Server("gazebo-mcp")
    tools, handlers = _build_registry()

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return tools

    # validate_input=False: the tool handlers self-validate and return rich,
    # structured OperationResult errors (error_code + suggestions + example_fix).
    # SDK-side schema validation would reject invalid input earlier with a plain
    # message, dropping those suggestions — so we preserve the legacy behaviour.
    @server.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.ContentBlock]:
        metrics = get_metrics_collector()
        if name not in handlers:
            # SDK turns this into a protocol error with isError=True.
            raise ValueError(f"Tool '{name}' not found")

        start = time.time()
        try:
            result: OperationResult = handlers[name](**(arguments or {}))
            metrics.record_tool_call(
                tool_name=name, duration=time.time() - start, success=result.success
            )
            payload = {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "error_code": result.error_code,
                "suggestions": result.suggestions,
            }
            return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]
        except Exception as e:  # noqa: BLE001 — mirror legacy server's catch-all
            metrics.record_tool_call(
                tool_name=name, duration=time.time() - start, success=False
            )
            metrics.record_error(error_type=type(e).__name__, error_message=str(e))
            _logger.exception("Error calling tool", tool=name)
            payload = {
                "success": False,
                "data": None,
                "error": str(e),
                "error_code": "INTERNAL_ERROR",
                "suggestions": [
                    "Check tool arguments",
                    "Verify Gazebo is running",
                    "Check server logs",
                ],
            }
            return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]

    _logger.info("SDK server built", tool_count=len(tools))
    return server
