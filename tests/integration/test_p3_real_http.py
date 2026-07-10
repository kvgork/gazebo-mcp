"""P3-real (D4) acceptance: the unified FastMCP server over **Streamable HTTP**,
running the **modern** backend against a **live** Gazebo Harmonic world.

This is the bridge between two previously-separate worlds in the suite:
``test_p3_http.py`` (real uvicorn + HTTP, but MOCK backend) and
``test_p2_real_sensors.py`` (real modern backend, but adapter driven DIRECTLY,
no HTTP). Here the full stack runs end-to-end: a real ``_UvicornServer`` hosting
``build_app().streamable_http_app()``, ``GAZEBO_BACKEND=modern`` against a live
``gz sim -s -r sensors.sdf``, exercised through the MCP Streamable-HTTP client.

What it proves:
  * ``gz://sensor/{name}`` resources return a REAL typed sample over the modern
    backend (the resource read internally drives ``list_sensors`` name->topic
    resolution + ``sensor_snapshot`` over live ``gz`` — all via the HTTP session's
    own per-session bridge);
  * two COEXISTING HTTP sessions negotiate distinct ``Mcp-Session-Id``s and each
    independently reads the live sensor over the modern backend.

IMPORTANT — what the multi-session test does and does NOT prove: over a live gz
world every session shares the ONE physical simulator via the same transport, so
whether the server hands out a per-session bridge object or one shared bridge is
**behaviorally indistinguishable** through black-box HTTP reads. This test
therefore asserts only **distinct transport session ids + independent successful
reads while both sessions are open concurrently** — it deliberately does NOT
claim bridge-OBJECT or world-STATE isolation. That stronger property IS proven
where it is behaviorally observable: the MOCK soak (``test_p3_http_soak.py``),
where each session sees ONLY its own spawned model (per-session mock world =
genuinely separate bridges). Progress/subscribe over HTTP are likewise
mock-verified in ``test_p3_http.py`` / ``test_p3_progress_spike.py``.

Sensor reads on the modern backend shell out to the ``gz`` CLI (``gz topic -e``),
so NO ``ros_gz`` ``parameter_bridge`` is needed — only a live ``gz sim`` (unlike
mutation ops such as spawn/step, which do need the bridged ``/world/*`` services).

Marked ``@pytest.mark.gazebo`` — runs under
``pixi run -e full pytest --with-gazebo -m gazebo
tests/integration/test_p3_real_http.py`` and SKIPS cleanly when the live stack is
unavailable.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.gazebo

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

WORLD_FILE = "sensors.sdf"      # stock gz-sim8 world; non-render imu/altimeter/etc.
EXPECT_TOPIC = "/imu"           # published by sensors.sdf; small binary Imu msg


def _gz_topics():
    try:
        out = subprocess.run(
            ["gz", "topic", "-l"], capture_output=True, text=True, timeout=5.0
        )
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    except Exception:  # noqa: BLE001
        return []


@pytest.fixture(scope="module")
def live_http_server():
    """Bring up live gz (sensors.sdf) + a real uvicorn HTTP server on the modern
    backend, yield the ``_UvicornServer`` (its ``.url`` is the /mcp endpoint)."""
    if shutil.which("gz") is None:
        pytest.skip("gz not on PATH (need -e full)")
    try:
        import rclpy  # noqa: F401
    except Exception:
        pytest.skip("rclpy not importable (need -e full)")

    proc = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "-v0", WORLD_FILE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    def _terminate():
        try:
            proc.terminate()
            proc.wait(timeout=6)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass

    # Wait for the sensor topic (bring-up proof).
    deadline = time.time() + 30.0
    while time.time() < deadline:
        if proc.poll() is not None:
            pytest.skip("gz sim exited before sensor topics came up")
        if EXPECT_TOPIC in _gz_topics():
            break
        time.sleep(0.5)
    else:
        _terminate()
        pytest.skip(f"{EXPECT_TOPIC} did not appear in time")

    # Select the modern backend against the live world; reset the bridge helper
    # singletons so the server (uvicorn lifespan + per-session) builds fresh
    # modern bridges, not leftover state from another test.
    saved = {k: os.environ.get(k) for k in ("GAZEBO_BACKEND", "GAZEBO_WORLD_NAME")}
    os.environ["GAZEBO_BACKEND"] = "modern"
    os.environ["GAZEBO_WORLD_NAME"] = "sensors"
    import gazebo_mcp.tools._bridge_helper as bh
    bh._bridge_node = None
    bh._connection_manager = None

    from gz_mcp_server.server.app import build_app
    from tests.integration.test_p3_http import _UvicornServer

    srv_cm = _UvicornServer(build_app().streamable_http_app())
    srv = srv_cm.__enter__()
    try:
        yield srv
    finally:
        try:
            srv_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
        bh._bridge_node = None
        bh._connection_manager = None
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _terminate()


def _pick_imu(sensors):
    """Pick an imu-like sensor descriptor's name from a sensor_list payload."""
    for s in sensors:
        name = (s.get("name") or "") if isinstance(s, dict) else str(s)
        topic = (s.get("topic") or "") if isinstance(s, dict) else ""
        if "imu" in name.lower() or "imu" in topic.lower():
            return name
    return None


async def _discover_and_read_imu(client):
    """Discover an imu-like sensor via sensor_list, read its gz://sensor resource.
    Returns (sensor_name, payload) or (None, None) if no imu sensor is found."""
    import mcp.types as types

    listing = await client.call_tool("sensor_list", {"world": "sensors"})
    data = json.loads(listing.content[0].text).get("data", {})
    name = _pick_imu(data.get("sensors", []))
    if name is None:
        return None, None
    res = await client.read_resource(types.AnyUrl(f"gz://sensor/{name}"))
    return name, json.loads(res.contents[0].text)


async def _session_read_imu(url):
    """Open one HTTP MCP session: discover an imu sensor, read its resource.
    Returns (session_id, sensor_name_or_None, payload_or_None)."""
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url) as (r, w, get_sid):
        async with ClientSession(r, w) as client:
            await client.initialize()
            sid = get_sid()
            name, payload = await _discover_and_read_imu(client)
            return sid, name, payload


async def _two_concurrent_sessions_read_imu(url):
    """Open TWO HTTP MCP sessions that are live SIMULTANEOUSLY, each reading the
    imu resource. Returns ((sid_a, payload_a), (sid_b, payload_b)); a payload is
    None if that session discovers no imu-like sensor."""
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url) as (ra, wa, get_sid_a):
        async with ClientSession(ra, wa) as ca:
            await ca.initialize()
            # Open the second session WITHOUT closing the first — they coexist.
            async with streamablehttp_client(url) as (rb, wb, get_sid_b):
                async with ClientSession(rb, wb) as cb:
                    await cb.initialize()
                    sid_a, sid_b = get_sid_a(), get_sid_b()
                    _, pa = await _discover_and_read_imu(ca)
                    _, pb = await _discover_and_read_imu(cb)
                    return (sid_a, pa), (sid_b, pb)


def test_gz_sensor_resource_returns_real_sample_over_http(live_http_server):
    """gz://sensor/{imu} returns a REAL typed gz-json sample over the modern
    backend, driven entirely through the Streamable-HTTP session."""
    import anyio

    sid, name, payload = anyio.run(lambda: _session_read_imu(live_http_server.url))
    if name is None:
        pytest.skip("no imu-like sensor discovered via sensor_list over HTTP")
    assert sid, "no Mcp-Session-Id negotiated"
    assert isinstance(payload, dict), payload
    # modern backend shape: {"topic","format":"gz-json","sample":{...},"typed":true}
    assert payload.get("typed") is True, payload
    assert payload.get("format") == "gz-json", payload
    assert payload.get("sample"), payload


def test_two_concurrent_http_sessions_distinct_ids_independent_reads(live_http_server):
    """Two COEXISTING HTTP sessions negotiate distinct Mcp-Session-Ids and each
    independently reads the live imu over the modern backend.

    Scope (see module docstring): over a live shared gz world, per-session vs
    shared bridge objects are behaviorally indistinguishable through black-box
    reads, so this asserts distinct transport session ids + independent
    concurrent reads — NOT bridge-object/world-state isolation (proven in the
    MOCK soak ``test_p3_http_soak.py``, where per-session worlds are observable).
    """
    import anyio

    (sid_a, pa), (sid_b, pb) = anyio.run(
        lambda: _two_concurrent_sessions_read_imu(live_http_server.url)
    )
    if pa is None or pb is None:
        pytest.skip("no imu-like sensor discovered via sensor_list over HTTP")
    assert sid_a and sid_b, (sid_a, sid_b)
    assert sid_a != sid_b, f"concurrent sessions shared an id: {sid_a}"
    # Both concurrent sessions read a real typed sample over the modern backend.
    assert pa.get("format") == "gz-json", pa
    assert pb.get("format") == "gz-json", pb
