"""
SDK-based Gazebo MCP Server entry point (Step 0 of the architecture-evolution plan).

Provides the ``main()`` referenced by the ``gazebo-mcp-sdk`` console script.
It runs the MCP SDK low-level server (``gz_mcp_server.server.sdk_app``) over the
SDK's compliant stdio transport. This is the migration target that replaces the
legacy hand-rolled JSON-RPC server (``gazebo_mcp.server`` → ``gazebo-mcp-server``),
which is retained in parallel until the new path is validated.
"""

import sys
import logging
from pathlib import Path

import anyio


def main():
    """Run the SDK low-level MCP server in stdio mode."""
    # Add the package root to path so the top-level gz_mcp_server package resolves:
    package_root = Path(__file__).parents[2]
    sys.path.insert(0, str(package_root))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    from gz_mcp_server.server.sdk_app import build_server
    from mcp.server.stdio import stdio_server

    server = build_server()
    init_options = server.create_initialization_options()

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, init_options)

    anyio.run(_run)


if __name__ == "__main__":
    main()
