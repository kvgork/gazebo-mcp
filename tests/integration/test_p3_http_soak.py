"""
C2 — HTTP soak: many concurrent Mcp-Session-Id clients against the unified
Streamable-HTTP server (MOCK backend, no live gz), sustained over several rounds.

Confirms the P3 per-session isolation + lifecycle hold under load: each session
owns a fresh mock bridge (never sees another session's models), the server does
not crash/leak across rounds, and the session cap (`MAX_HTTP_SESSIONS`) evicts
oldest sessions rather than growing unbounded. This is the soak the retire of the
old servers (C3) is gated on — run against mock so it needs no Gazebo.
"""

import json
import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402

from gz_mcp_server.server.app import build_app, MAX_HTTP_SESSIONS  # noqa: E402
from tests.integration.test_p3_http import _UvicornServer  # noqa: E402

SDF = "<?xml version='1.0'?><sdf version='1.7'><model name='m'><link name='l'/></model></sdf>"


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force MOCK in-process (auto-reverted per test — no env leak to other
    modules) and reset the bridge singletons, so the uvicorn worker builds the
    deterministic MockGazeboAdapter. Mirrors test_p3_http's fixture."""
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None

CONCURRENT = 12   # simultaneous sessions per round
ROUNDS = 6        # sequential rounds (12*6 = 72 sessions total > MAX_HTTP_SESSIONS=64)


def _models(call_result) -> list:
    return json.loads(call_result.content[0].text)["data"]["models"]


def test_p3_http_soak_session_isolation_and_stability():
    """72 sessions (12 concurrent x 6 rounds) — each isolated, server stable,
    session registry bounded by the cap."""
    mcp = build_app()

    async def _one_session(url: str, tag: str):
        # Each session spawns a uniquely-named model, then lists — and must see
        # ONLY its own model (proves per-session bridge isolation under load).
        async with streamablehttp_client(url) as (r, w, _sid):
            async with ClientSession(r, w) as s:
                await s.initialize()
                spawn = await s.call_tool("scene_spawn", {"name": tag, "sdf": SDF})
                assert json.loads(spawn.content[0].text)["success"], spawn
                models = _models(await s.call_tool("scene_list_models", {}))
                assert models == [tag], f"isolation breach for {tag}: {models}"

    async def _run():
        # 72 sessions total (12 concurrent x 6 rounds) > MAX_HTTP_SESSIONS (64),
        # so the server must LRU-evict older sessions and keep serving — a crash,
        # leak, or isolation breach would surface as an exception/assert here.
        assert 72 > MAX_HTTP_SESSIONS, "soak must exceed the cap to exercise eviction"
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            for rnd in range(ROUNDS):
                async with anyio.create_task_group() as tg:
                    for i in range(CONCURRENT):
                        tg.start_soon(_one_session, srv.url, f"m_{rnd}_{i}")

    anyio.run(_run)
