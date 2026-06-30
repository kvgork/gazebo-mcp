"""
P3 Streamable-HTTP acceptance: per-session bridge isolation, the
``gz://sensor/{name}`` resource notify-then-poll round-trip (subscribe →
*bare* ``notifications/resources/updated`` → read), and the unified tool count —
all over a REAL Streamable-HTTP transport, with NO Gazebo / ROS2 running.

Transport choice (verified, honest)
-----------------------------------
The unified app is served by a REAL ``uvicorn`` server on an ephemeral port and
driven by ``mcp.client.streamable_http.streamablehttp_client``. We do NOT use
``httpx.ASGITransport`` against ``mcp.streamable_http_app()`` directly: that path
never runs the StreamableHTTP *session-manager* task group (its ASGI lifespan is
not invoked by ``ASGITransport``), so the server raises ``RuntimeError("Task
group is not initialized")``. A real uvicorn server (whose lifespan boots the
session manager) is the faithful in-``-e dev`` path and is reliable here once the
MOCK backend is forced (below). See ``scratchpad/probe_asgi.py`` (ASGI failure)
vs ``scratchpad/probe_uvicorn_mock.py`` (uvicorn pass).

Backend forcing (authoritative — pixi pins ``GAZEBO_BACKEND=modern``)
---------------------------------------------------------------------
pixi ``[activation.env]`` sets ``GAZEBO_BACKEND=modern`` for the whole process,
which a real uvicorn worker would otherwise pick up (it then connects to ROS2 and
dies with ``ExternalShutdownException`` — see ``scratchpad/http.log``). The mock
must therefore be forced IN-PROCESS: an autouse fixture sets
``GAZEBO_BACKEND=mock`` via ``monkeypatch.setenv`` (process-global, so the uvicorn
thread sees it) AND resets the ``_bridge_helper`` singletons BEFORE ``build_app``
so the lifespan constructs the deterministic ``MockGazeboAdapter`` rather than a
real bridge. The env is auto-reverted, never leaking into the stdio suite.

Per-session isolation — REAL tools, both surfaces (P3 blocker, now CLOSED)
-------------------------------------------------------------------------
Two distinct ``Mcp-Session-Id`` HTTP sessions resolve to **isolated**
``GazeboSession`` objects (separate fresh bridges + subscriptions) via
``app.get_session(ctx)`` / ``_bridge_helper.get_bridge_for_ctx(ctx)``.

The isolation is now wired into the PRODUCTION tools via a ``ContextVar``
(``_bridge_helper._current_bridge``): the lean ``@mcp.tool`` wrappers bind the
per-session bridge with ``_with_session_bridge(ctx, ...)``, and the mounted
*legacy* closures (now ``async``, with an injected ``ctx: Context``) bind it then
run the sync handler via ``asyncio.to_thread`` (which copies the contextvar into
the worker thread). Both surfaces' unchanged ``get_bridge()`` calls therefore hit
the per-session world. The two tests below prove it over a REAL Streamable-HTTP
transport for BOTH the lean and the legacy surfaces:

- ``test_p3_http_lean_tool_isolation``: lean ``scene_spawn('cubeA')`` in session
  A is INVISIBLE to session B's ``scene_list_models`` (and vice-versa).
- ``test_p3_http_legacy_tool_isolation``: legacy
  ``gazebo_spawn_model('boxA', geometry='box')`` in session A is INVISIBLE to
  session B's ``gazebo_list_models``.
"""

import json
import socket
import sys
import threading
import time
from pathlib import Path

import anyio
import pytest

# Repo root + src on path so both the top-level gz_mcp_server package and the
# gazebo_mcp package (under src/) resolve.
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import uvicorn  # noqa: E402
import mcp.types as types  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402

from gz_mcp_server.server.app import build_app  # noqa: E402

# Unified tool count with the default flag (GAZEBO_LEGACY_TOOLS unset/"1"):
# 19 lean + 69 legacy = 88. (Flag "0" → 80; not exercised here.)
EXPECTED_TOOL_COUNT = 88

SDF = "<sdf version='1.7'><model name='m'><link name='l'/></model></sdf>"


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend process-wide and reset the bridge singletons.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` for each
    test (auto-reverted), and clearing the ``_bridge_helper`` module singletons
    (before AND after) guarantees the FastMCP lifespan + ``get_bridge_for_ctx``
    construct the deterministic ``MockGazeboAdapter`` against an empty world,
    never a real ROS2 bridge or another test's leftover state.
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


def _free_port() -> int:
    """Grab an ephemeral free TCP port on localhost."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _UvicornServer:
    """Start/stop a real uvicorn server hosting ``app`` on an ephemeral port.

    Used as a context manager: ``with _UvicornServer(app) as srv: ... srv.url``.
    Boots the server on a daemon thread and waits for ``server.started`` (its
    ASGI lifespan runs, so the StreamableHTTP session-manager task group is up),
    then signals a clean shutdown on exit.
    """

    def __init__(self, app):
        self.port = _free_port()
        config = uvicorn.Config(
            app, host="127.0.0.1", port=self.port, log_level="error"
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    def __enter__(self) -> "_UvicornServer":
        self.thread.start()
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if self.server.started:
                return self
            time.sleep(0.02)
        raise RuntimeError("uvicorn server did not start within 10s")

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5.0)


def test_p3_http_lean_tool_isolation():
    """REAL lean tools are per-session over HTTP (P3 blocker, the lean half).

    Session A calls the production lean ``scene_spawn('cubeA')``; session B — a
    different ``Mcp-Session-Id`` — calls the production lean ``scene_list_models``
    and must NOT see ``cubeA`` (it owns a separate fresh mock bridge). The reverse
    is also asserted (B's ``cubeB`` invisible to A). No test-only tool is used —
    the ``_with_session_bridge`` / ``ContextVar`` wiring in the real tool handlers
    is what makes this pass.
    """
    mcp = build_app()

    def _models(call_result) -> list:
        return json.loads(call_result.content[0].text)["data"]["models"]

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            # Session A spawns cubeA, lists -> sees cubeA only.
            async with streamablehttp_client(srv.url) as (r, w, get_sid):
                async with ClientSession(r, w) as sa:
                    await sa.initialize()
                    sid_a = get_sid()
                    spawn_a = await sa.call_tool(
                        "scene_spawn", {"name": "cubeA", "sdf": SDF}
                    )
                    assert json.loads(spawn_a.content[0].text)["success"], spawn_a
                    list_a = _models(await sa.call_tool("scene_list_models", {}))

            # Session B spawns cubeB, lists -> sees cubeB only, NOT cubeA.
            async with streamablehttp_client(srv.url) as (r, w, get_sid):
                async with ClientSession(r, w) as sb:
                    await sb.initialize()
                    sid_b = get_sid()
                    spawn_b = await sb.call_tool(
                        "scene_spawn", {"name": "cubeB", "sdf": SDF}
                    )
                    assert json.loads(spawn_b.content[0].text)["success"], spawn_b
                    list_b = _models(await sb.call_tool("scene_list_models", {}))

            assert sid_a and sid_b and sid_a != sid_b, (sid_a, sid_b)
            assert "cubeA" in list_a, list_a
            assert "cubeB" not in list_a, f"A saw B's model (future leak?): {list_a}"
            assert "cubeB" in list_b, list_b
            assert "cubeA" not in list_b, (
                f"LEAN isolation broken: session B saw session A's model: {list_b}"
            )

    anyio.run(_run)


def test_p3_http_legacy_tool_isolation():
    """REAL legacy tools are per-session over HTTP (P3 blocker, the legacy half).

    Session A calls the mounted legacy ``gazebo_spawn_model(model_name='boxA',
    geometry='box')``; session B — a different ``Mcp-Session-Id`` — calls the
    legacy ``gazebo_list_models`` and must NOT see ``boxA``. Proves the async
    legacy closures bind the per-session bridge and that ``asyncio.to_thread``
    propagates the ``ContextVar`` into the sync handler's ``get_bridge()``.
    """
    mcp = build_app()

    def _model_names(call_result) -> list:
        data = json.loads(call_result.content[0].text)["data"]
        return [m["name"] for m in data["models"]]

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            # Session A spawns boxA via the legacy tool.
            async with streamablehttp_client(srv.url) as (r, w, get_sid):
                async with ClientSession(r, w) as sa:
                    await sa.initialize()
                    sid_a = get_sid()
                    spawn_a = await sa.call_tool(
                        "gazebo_spawn_model",
                        {"model_name": "boxA", "geometry": "box"},
                    )
                    assert json.loads(spawn_a.content[0].text)["success"], spawn_a
                    list_a = _model_names(await sa.call_tool("gazebo_list_models", {}))

            # Session B spawns boxB; must NOT see boxA, and A must not see boxB.
            async with streamablehttp_client(srv.url) as (r, w, get_sid):
                async with ClientSession(r, w) as sb:
                    await sb.initialize()
                    sid_b = get_sid()
                    spawn_b = await sb.call_tool(
                        "gazebo_spawn_model",
                        {"model_name": "boxB", "geometry": "box"},
                    )
                    assert json.loads(spawn_b.content[0].text)["success"], spawn_b
                    list_b = _model_names(await sb.call_tool("gazebo_list_models", {}))

            assert sid_a and sid_b and sid_a != sid_b, (sid_a, sid_b)
            assert "boxA" in list_a, list_a
            assert "boxB" not in list_a, f"A saw B's model: {list_a}"
            assert "boxB" in list_b, list_b
            assert "boxA" not in list_b, (
                f"LEGACY isolation broken: session B saw session A's model: {list_b}"
            )

    anyio.run(_run)


def test_p3_http_resource_subscribe_updated_bare_then_read():
    """Resource notify-then-poll round-trip over HTTP, with a BARE updated ping.

    1. ``resources/read('gz://sensor/imu_sensor')`` returns the imu sample
       (``sensor_name == 'imu_sensor'``, ``linear_acceleration.z == 9.81``).
    2. ``resources/subscribe`` triggers EXACTLY one
       ``notifications/resources/updated`` whose params, dumped with
       ``exclude_none=True``, are EXACTLY ``{'uri': ...}`` — a BARE ping carrying
       NO data (the honest notify-then-poll contract).
    3. A follow-up ``resources/read`` returns the (now cached) imu sample.
    """
    mcp = build_app()
    updates: list = []

    async def message_handler(message):
        if isinstance(message, types.ServerNotification):
            root = message.root
            if isinstance(root, types.ResourceUpdatedNotification):
                updates.append(root)

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            async with streamablehttp_client(srv.url) as (r, w, _):
                async with ClientSession(r, w, message_handler=message_handler) as client:
                    await client.initialize()

                    # (1) initial read returns the imu sample
                    res = await client.read_resource(types.AnyUrl("gz://sensor/imu_sensor"))
                    payload = json.loads(res.contents[0].text)
                    assert payload["sensor_name"] == "imu_sensor", payload
                    assert payload["topic"] == "/imu", payload
                    assert payload["linear_acceleration"]["z"] == pytest.approx(9.81)

                    # (2) subscribe → exactly one BARE updated ping (uri only)
                    await client.subscribe_resource(types.AnyUrl("gz://sensor/imu_sensor"))
                    for _ in range(60):
                        if updates:
                            break
                        await anyio.sleep(0.05)
                    assert updates, "no notifications/resources/updated received"
                    assert len(updates) == 1, f"expected exactly one ping, got {len(updates)}"
                    pdump = updates[0].params.model_dump(exclude_none=True)
                    assert pdump.keys() == {"uri"}, f"ping carried data (not bare): {pdump}"
                    assert str(updates[0].params.uri).rstrip("/") == "gz://sensor/imu_sensor"

                    # (3) notify-then-poll: follow-up read returns the cached sample
                    res2 = await client.read_resource(types.AnyUrl("gz://sensor/imu_sensor"))
                    p2 = json.loads(res2.contents[0].text)
                    assert p2["sensor_name"] == "imu_sensor", p2
                    assert p2["topic"] == "/imu", p2

    anyio.run(_run)


def test_p3_http_unified_tool_count():
    """``tools/list`` over HTTP shows the unified 88 (19 lean + 69 legacy) tools."""
    mcp = build_app()

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            async with streamablehttp_client(srv.url) as (r, w, _):
                async with ClientSession(r, w) as client:
                    await client.initialize()
                    tools = await client.list_tools()
                    assert len(tools.tools) == EXPECTED_TOOL_COUNT, (
                        f"expected {EXPECTED_TOOL_COUNT} unified tools, "
                        f"got {len(tools.tools)}"
                    )
                    names = {t.name for t in tools.tools}
                    # Spot-check: lean + a sampled legacy tool both present.
                    assert "scene_spawn" in names
                    assert "world_step" in names

    anyio.run(_run)
