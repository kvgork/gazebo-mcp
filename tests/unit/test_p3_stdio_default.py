"""
P3 unit: the ``fastmcp_server`` entry point defaults to ``--stdio``.

stdio stays the DEFAULT transport in P3 — HTTP is strictly opt-in (``--http``).
Every existing MCP client/launcher and the whole P0–P2 test suite spawn the
server over stdio, so the default must never silently flip to HTTP. These are
pure argparse assertions against ``fastmcp_server._build_parser`` — no server is
booted, no socket is opened, no backend is touched.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.fastmcp_server import (  # noqa: E402
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
    _build_parser,
)


def test_no_flags_defaults_to_stdio():
    """Parsing an empty argv yields ``transport == 'stdio'`` (the DEFAULT)."""
    args = _build_parser().parse_args([])
    assert args.transport == "stdio"


def test_explicit_stdio_flag():
    """``--stdio`` selects the stdio transport explicitly."""
    args = _build_parser().parse_args(["--stdio"])
    assert args.transport == "stdio"


def test_http_flag_selects_http():
    """``--http`` is selectable and opts into the Streamable-HTTP transport."""
    args = _build_parser().parse_args(["--http"])
    assert args.transport == "http"


def test_http_host_port_defaults():
    """Host/port carry the P3 defaults (127.0.0.1:8931) when not overridden."""
    args = _build_parser().parse_args([])
    assert args.host == DEFAULT_HTTP_HOST == "127.0.0.1"
    assert args.port == DEFAULT_HTTP_PORT == 8931


def test_http_host_port_overridable():
    """``--host``/``--port`` override the Streamable-HTTP bind."""
    args = _build_parser().parse_args(["--http", "--host", "0.0.0.0", "--port", "9999"])
    assert args.transport == "http"
    assert args.host == "0.0.0.0"
    assert args.port == 9999


def test_stdio_and_http_are_mutually_exclusive():
    """``--stdio --http`` is rejected (mutually exclusive transport group)."""
    import pytest

    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--stdio", "--http"])
