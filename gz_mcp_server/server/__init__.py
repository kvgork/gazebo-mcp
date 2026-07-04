"""
MCP Server Implementation.

The unified FastMCP app (``gz_mcp_server.server.app:build_app``) is the sole
server. The hand-rolled ``GazeboMCPServer`` and the low-level ``sdk_app`` server
were retired (P*-real C3); the curated legacy-tool registry now lives in
``registry`` and is mounted onto the unified app by ``legacy_mount``.
"""

from .mcp_tool import MCPTool

__all__ = ["MCPTool"]
