"""
Curated legacy-tool registry — the single source of truth for the 69 hand-curated
adapter tools (name, description, inputSchema, handler).

Extracted from ``sdk_app`` (P*-real C1) so the surviving unified FastMCP app
(via ``legacy_mount``) no longer depends on the retiring low-level ``sdk_app``
server. Both the unified app and any remaining low-level entry point build their
tool surface from ``build_registry()``.
"""

from typing import Callable, Dict, List, Tuple

import mcp.types as types

from gz_mcp_server.server import adapters as _adapters_pkg


def build_registry() -> Tuple[List[types.Tool], Dict[str, Callable]]:
    """Collect curated Tool definitions + handlers from every adapter.

    Returns ``(tools, handlers)`` — the (name, description, inputSchema) surface
    the curated adapters expose, built from their hand-written JSON schemas.
    """
    tools: List[types.Tool] = []
    handlers: Dict[str, Callable] = {}
    for module_name in _adapters_pkg.__all__:
        adapter = getattr(_adapters_pkg, module_name)
        for mcp_tool in adapter.get_tools():
            tools.append(
                types.Tool(
                    name=mcp_tool.name,
                    description=mcp_tool.description,
                    inputSchema={
                        "type": "object",
                        "properties": mcp_tool.parameters.get("properties", {}),
                        "required": mcp_tool.parameters.get("required", []),
                    },
                )
            )
            handlers[mcp_tool.name] = mcp_tool.handler
    return tools, handlers
