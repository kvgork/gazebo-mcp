"""
FastMCP Gazebo MCP server entry point (P0-B).

Provides the ``main()`` referenced by the ``gazebo-mcp-fastmcp`` console script.
Runs the FastMCP app (``gz_mcp_server.server.app``) serving the nine lean
``world_*`` / ``scene_*`` tools over stdio.

The 69 curated legacy tools remain served by the retained low-level SDK server
(``gazebo-mcp-sdk`` → ``gazebo_mcp.sdk_server``); single-server unification lands
in P3 (see ``gz_mcp_server.server.app`` module docstring).
"""

import sys
from pathlib import Path


def main():
    """Run the FastMCP Gazebo MCP server in stdio mode."""
    # Add the repo root to path so the top-level gz_mcp_server package resolves
    # (mirrors gazebo_mcp.sdk_server.main).
    repo_root = Path(__file__).parents[2]
    sys.path.insert(0, str(repo_root))

    from gz_mcp_server.server.app import build_app

    build_app().run("stdio")


if __name__ == "__main__":
    main()
