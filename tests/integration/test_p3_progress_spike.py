"""
#953 SPIKE — does ``ctx.report_progress(...)`` survive Streamable HTTP, in order,
on mcp 1.27.1?

WHY this spike exists
---------------------
Long-running Gazebo operations (P5) want to stream progress to the client. Before
committing to that design we must know, empirically, whether the SDK's
``Context.report_progress`` → ``notifications/progress`` actually reaches an HTTP
client and arrives IN ORDER. This is a VERDICT, not a green-at-all-costs test: if
progress were lost or reordered we would record FAIL and mark the spike result so
P5 falls back to an op-id + poll design.

WHAT the spike does (faithful, minimal)
---------------------------------------
- Registers a TEMP tool on a fresh ``build_app()`` whose body calls
  ``await ctx.report_progress(progress=p, total=1.0)`` three times (0.33 / 0.66 /
  1.0).
- Drives it over a REAL Streamable-HTTP transport (uvicorn + ``streamablehttp_client``).
- Supplies a ``progressToken`` by passing ``progress_callback=`` to
  ``ClientSession.call_tool`` — the 1.27.1 SDK injects ``_meta.progressToken`` into
  the request and routes incoming ``notifications/progress`` to that callback. A
  ``message_handler`` ALSO captures every ``ProgressNotification`` independently so
  the assertion does not depend on the callback alone.
- Asserts EVERY progress notification arrived and IN ORDER.

VERDICT (recorded 2026-06-30, mcp 1.27.1, httpx 0.28.1, uvicorn 0.48.0):
    PASS — all three progress notifications [0.33, 0.66, 1.0] arrive over
    Streamable HTTP, in order, via BOTH the message_handler and the
    progress_callback. ``report_progress`` survives HTTP. (Reproduced in
    ``scratchpad/probe_uvicorn_mock.py``.) P5 may rely on streamed progress; no
    op-id+poll fallback is required for the HTTP transport.

Backend forcing + transport rationale mirror ``test_p3_http.py`` (see that
module's docstring): MOCK is forced in-process; a real uvicorn server is used
because ``httpx.ASGITransport`` does not boot the StreamableHTTP session-manager
task group.
"""

import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import mcp.types as types  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402
from mcp.server.fastmcp import Context  # noqa: E402

from gz_mcp_server.server.app import build_app  # noqa: E402

# Reuse the verified uvicorn-server harness from the HTTP test module.
from tests.integration.test_p3_http import _UvicornServer  # noqa: E402

# The progress fractions the temp tool reports, in the order it reports them.
PROGRESS_STEPS = (0.33, 0.66, 1.0)


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force MOCK + reset bridge singletons (see ``test_p3_http`` for rationale)."""
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


def test_953_progress_survives_streamable_http_in_order():
    """#953 VERDICT: every ``report_progress`` reaches the HTTP client, in order.

    PASS criterion (recorded result): the three reported fractions
    ``[0.33, 0.66, 1.0]`` arrive as ``notifications/progress`` over Streamable
    HTTP, captured by an independent ``message_handler``, in the exact order
    emitted; the ``progress_callback`` sees the same sequence.
    """
    mcp = build_app()

    @mcp.tool()
    async def _progress_probe(ctx: Context = None) -> dict:
        """Report progress three times, then finish."""
        for p in PROGRESS_STEPS:
            await ctx.report_progress(progress=p, total=1.0)
        return {"done": True, "steps": len(PROGRESS_STEPS)}

    handler_progress: list[float] = []
    callback_progress: list[float] = []

    async def message_handler(message):
        if isinstance(message, types.ServerNotification):
            root = message.root
            if isinstance(root, types.ProgressNotification):
                handler_progress.append(root.params.progress)

    async def progress_callback(progress: float, total, message):
        # Passing this callback is what makes the SDK inject a progressToken.
        callback_progress.append(progress)

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            async with streamablehttp_client(srv.url) as (r, w, _):
                async with ClientSession(
                    r, w, message_handler=message_handler
                ) as client:
                    await client.initialize()
                    result = await client.call_tool(
                        "_progress_probe", {}, progress_callback=progress_callback
                    )
                    # Tool itself completed.
                    assert result.content, "no content returned from progress probe"

        # VERDICT assertions — every step, in order, no loss, no reordering.
        assert handler_progress == list(PROGRESS_STEPS), (
            "#953 FAIL: progress lost/reordered over HTTP. "
            f"expected {list(PROGRESS_STEPS)}, got {handler_progress}"
        )
        # The progress_callback path sees the same ordered sequence.
        assert callback_progress == list(PROGRESS_STEPS), (
            "#953 FAIL: progress_callback sequence mismatch. "
            f"expected {list(PROGRESS_STEPS)}, got {callback_progress}"
        )

    anyio.run(_run)
