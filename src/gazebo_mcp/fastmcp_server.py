"""
FastMCP Gazebo MCP server entry point (P0-B + P3).

Provides the ``main()`` referenced by the ``gazebo-mcp-fastmcp`` console script.
Runs the unified FastMCP app (``gz_mcp_server.server.app``) serving the 19 lean
``world_*`` / ``scene_*`` / ``sensor_*`` / ... tools **plus** the curated legacy
tools (P3 unification) and the ``gz://sensor/{name}`` resources.

Transports (P3)
---------------
- ``--stdio`` (DEFAULT): run over stdio — what an MCP client spawns. Unchanged
  from P0-B; this is what every existing test and launcher uses.
- ``--http``: run over Streamable HTTP (``mcp.run(transport="streamable-http")``)
  on ``--host``/``--port`` (default ``127.0.0.1:8931``). Opt-in.

Host/port are applied to FastMCP via ``mcp.settings.host`` / ``mcp.settings.port``
(the values ``run_streamable_http_async`` reads to configure uvicorn on mcp
1.27.1). ``--stdio`` ignores host/port.
"""

import argparse
import sys
from pathlib import Path

from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("fastmcp_server")

# Default Streamable-HTTP bind (P3): localhost:8931. Bind to loopback by default
# (#4/#14) — the server has NO authentication, so it must not be reachable beyond
# localhost unless an operator deliberately fronts it with a proxy/auth.
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8931


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser. ``--stdio`` is the default transport."""
    parser = argparse.ArgumentParser(
        prog="gazebo-mcp-fastmcp",
        description="Unified FastMCP Gazebo MCP server (lean + legacy tools + resources).",
    )
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument(
        "--stdio",
        dest="transport",
        action="store_const",
        const="stdio",
        help="Run over stdio (DEFAULT).",
    )
    transport.add_argument(
        "--http",
        dest="transport",
        action="store_const",
        const="http",
        help="Run over Streamable HTTP (opt-in).",
    )
    parser.set_defaults(transport="stdio")  # stdio is the DEFAULT transport.
    parser.add_argument(
        "--host",
        default=DEFAULT_HTTP_HOST,
        help=f"Host to bind for --http (default {DEFAULT_HTTP_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=f"Port to bind for --http (default {DEFAULT_HTTP_PORT}).",
    )
    return parser


def main(argv=None):
    """Run the unified FastMCP Gazebo MCP server (stdio by default)."""
    # Add the repo root to path so the top-level gz_mcp_server package resolves
    # (mirrors gazebo_mcp.sdk_server.main).
    repo_root = Path(__file__).parents[2]
    sys.path.insert(0, str(repo_root))

    args = _build_parser().parse_args(argv)

    from gz_mcp_server.server.app import build_app

    mcp = build_app()

    if args.transport == "http":
        # Apply host/port to FastMCP settings (read by run_streamable_http_async
        # to configure uvicorn on mcp 1.27.1), then run Streamable HTTP.
        mcp.settings.host = args.host
        mcp.settings.port = args.port

        # HTTP auth/bind safety (#4/#14): the Streamable-HTTP transport serves
        # every tool (incl. actuation: wrenches, joint commands, trajectories)
        # with NO authentication. Warn loudly at startup; warn LOUDER if bound to
        # a non-loopback interface (0.0.0.0 / any external host).
        tool_count = len(mcp._tool_manager._tools)
        bind = f"{args.host}:{args.port}"
        base_warning = (
            f"Streamable-HTTP serves {tool_count} tools (incl. actuation) with NO "
            f"authentication; bound to {bind}. Do not expose beyond localhost "
            f"without a proxy/auth."
        )
        if args.host not in ("127.0.0.1", "localhost", "::1"):
            _logger.warning(
                f"!!! INSECURE BIND !!! {base_warning} Host {args.host!r} is "
                f"NON-LOOPBACK: this server is reachable from OTHER machines with "
                f"ZERO authentication and can actuate the simulation. Put it behind "
                f"a reverse proxy with auth, or bind --host 127.0.0.1."
            )
        else:
            _logger.warning(base_warning)

        mcp.run(transport="streamable-http")
    else:
        # DEFAULT path: stdio, unchanged from P0-B.
        mcp.run("stdio")


if __name__ == "__main__":
    main()
