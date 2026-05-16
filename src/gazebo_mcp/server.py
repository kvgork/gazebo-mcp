"""
Gazebo MCP Server entry point.

This module provides the `main()` function referenced by pyproject.toml's
`gazebo-mcp-server` console script entry point.

It delegates to the actual MCP server implementation at mcp/server/server.py.
"""

import sys
import logging
from pathlib import Path


def main():
    """
    Main entry point for the gazebo-mcp-server console script.

    Starts the MCP server in stdio mode (JSON-RPC 2.0 over stdin/stdout).
    """
    # Add the package root to path so mcp.server can be found:
    package_root = Path(__file__).parents[2]
    sys.path.insert(0, str(package_root))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    from gazebo_mcp.mcp_protocol.server.server import GazeboMCPServer

    server = GazeboMCPServer()
    server.run()


if __name__ == "__main__":
    main()
