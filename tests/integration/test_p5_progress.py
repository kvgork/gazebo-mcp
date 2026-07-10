"""
P5 acceptance: ``world_step`` streams ORDERED progress over Streamable HTTP,
AND (FIX-F5 regression) progress reporting never perturbs the physics.

Builds on the #953 spike (``test_p3_progress_spike.py``, PASS) which proved that
``ctx.report_progress`` → ``notifications/progress`` survives Streamable HTTP in
order on mcp 1.27.1. Here we exercise the PRODUCTION ``world_step`` tool (not a
temp probe): a long ``world_step(steps=30)`` must emit MULTIPLE progress
notifications, in order, whose final value reaches ``total``, while the tool's
own result still reports ``steps == 30`` (identical to a single-shot call).

FIX-F5: an earlier chunked-stepping design broke a stronger invariant — the
final POSE after a wrench + step must be IDENTICAL whether or not a progress
listener is attached (physics must never be a function of observability). The
mock adapter now runs the physics in one shot and reports a cosmetic progress
ramp of up to 10 evenly-spaced notifications FROM INSIDE that call (see
``mock_adapter.step``); ``test_bridge_step_progress_cb_does_not_alter_physics``
below is the direct regression test for that invariant.

Backend forcing + transport rationale mirror ``test_p3_http.py`` / the spike:
MOCK is forced IN-PROCESS (pixi pins ``GAZEBO_BACKEND=modern``); a REAL uvicorn
server is used because ``httpx.ASGITransport`` does not boot the StreamableHTTP
session-manager task group. The ``_UvicornServer`` harness + ``progress_callback``
+ ``message_handler`` pattern are reused verbatim from those modules.
"""

import json
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

from gz_mcp_server.server.app import build_app  # noqa: E402

from gazebo_mcp.bridge.gazebo_bridge_node import GazeboBridgeNode  # noqa: E402
from gazebo_mcp.bridge.gazebo_interface import EntityPose  # noqa: E402
from gazebo_mcp.bridge.adapters.mock_adapter import MockGazeboAdapter  # noqa: E402
from gazebo_mcp.bridge.config import GazeboConfig, GazeboBackend  # noqa: E402

# Reuse the verified uvicorn-server harness from the HTTP test module.
from tests.integration.test_p3_http import _UvicornServer  # noqa: E402

# A run long enough to span several ramp reports. FIX-F5's mock adapter reports
# an evenly-spaced ramp of up to 10 progress notifications from INSIDE the
# single native step() call (see mock_adapter.step) — independent of any
# app-layer chunk size, since there is no chunking any more.
STEPS = 30
EXPECTED_NOTIFICATIONS = min(STEPS, 10)


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


def test_world_step_streams_ordered_progress_over_http():
    """``world_step(steps=30)`` streams ordered progress; result reports steps==30.

    Assertions:
      - MULTIPLE ``notifications/progress`` arrive (one per chunk).
      - They are strictly increasing (in order) and never exceed ``total``.
      - The last progress reaches ``total == STEPS``.
      - The ``progress_callback`` path sees the same sequence in order (it may
        lag the session-level handler by the trailing notification: the per-
        request callback is torn down when ``call_tool`` returns, while over
        streamable HTTP the response and the final progress notification arrive
        on separate streams — so we assert the callback is an in-order PREFIX of
        the authoritative handler capture, not necessarily its full length).
      - The tool RESULT still reports ``data.steps == STEPS`` (payload identical
        to a single-shot call) with a final ``sim_time`` matching 30 steps.
    """
    mcp = build_app()

    handler_progress: list[float] = []
    handler_totals: list = []
    callback_progress: list[float] = []

    async def message_handler(message):
        if isinstance(message, types.ServerNotification):
            root = message.root
            if isinstance(root, types.ProgressNotification):
                handler_progress.append(root.params.progress)
                handler_totals.append(root.params.total)

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
                        "world_step",
                        {"steps": STEPS},
                        progress_callback=progress_callback,
                    )
                    assert result.content, "no content returned from world_step"
                    payload = json.loads(result.content[0].text)

        # --- tool result is identical to a single-shot world_step(steps=30) ---
        assert payload["success"], payload
        assert payload["data"]["steps"] == STEPS, (
            f"world_step result must report the TOTAL steps, got {payload['data']}"
        )
        # sim_time == steps * step_size (mock step_size default 0.001 => 0.03).
        assert payload["data"]["sim_time"] == pytest.approx(
            STEPS * 0.001
        ), payload["data"]

        # --- progress streamed, multiple, in order, last reaches total ---
        assert len(handler_progress) == EXPECTED_NOTIFICATIONS, (
            f"expected {EXPECTED_NOTIFICATIONS} progress notifications "
            f"(evenly-spaced ramp), got {len(handler_progress)}: {handler_progress}"
        )
        assert len(handler_progress) > 1, "expected MULTIPLE progress notifications"
        assert handler_progress == sorted(handler_progress), (
            f"progress arrived out of order: {handler_progress}"
        )
        assert handler_progress == list(dict.fromkeys(handler_progress)), (
            f"progress had duplicates / non-strict increase: {handler_progress}"
        )
        assert all(p <= STEPS for p in handler_progress), handler_progress
        assert handler_progress[-1] == STEPS, (
            f"last progress must reach total {STEPS}, got {handler_progress[-1]}"
        )
        assert all(t == STEPS for t in handler_totals), (
            f"every progress total must be {STEPS}, got {handler_totals}"
        )
        # The callback path proves the SDK routed the progressToken. It sees the
        # same ordered sequence as the handler, but may lag by the trailing
        # notification (see docstring) — assert it is a non-empty in-order PREFIX
        # of the authoritative handler capture.
        assert callback_progress, "progress_callback never fired (token not routed?)"
        assert callback_progress == sorted(callback_progress), (
            f"progress_callback out of order: {callback_progress}"
        )
        assert callback_progress == handler_progress[: len(callback_progress)], (
            f"progress_callback ({callback_progress}) is not an in-order prefix "
            f"of handler ({handler_progress})"
        )

    anyio.run(_run)


def test_world_step_single_shot_no_progress_over_http():
    """``world_step(steps=1)`` stays single-shot: no progress notifications.

    Guards the threshold branch: a trivial step must NOT stream progress even
    when a progressToken is supplied, and the payload is the plain single-shot
    result (``data.steps == 1``).
    """
    mcp = build_app()

    handler_progress: list[float] = []

    async def message_handler(message):
        if isinstance(message, types.ServerNotification):
            root = message.root
            if isinstance(root, types.ProgressNotification):
                handler_progress.append(root.params.progress)

    async def progress_callback(progress: float, total, message):
        handler_progress.append(progress)

    async def _run():
        with _UvicornServer(mcp.streamable_http_app()) as srv:
            async with streamablehttp_client(srv.url) as (r, w, _):
                async with ClientSession(
                    r, w, message_handler=message_handler
                ) as client:
                    await client.initialize()
                    result = await client.call_tool(
                        "world_step",
                        {"steps": 1},
                        progress_callback=progress_callback,
                    )
                    payload = json.loads(result.content[0].text)

        assert payload["success"], payload
        assert payload["data"]["steps"] == 1, payload["data"]
        assert handler_progress == [], (
            f"single-shot world_step must not stream progress, got {handler_progress}"
        )

    anyio.run(_run)


# ===========================================================================
# FIX-F5 regression: progress reporting must NEVER perturb the physics.
# ===========================================================================

def _mock_bridge() -> GazeboBridgeNode:
    """A fresh bridge over its own MockGazeboAdapter (no ROS, no singleton)."""
    return GazeboBridgeNode(
        None, config=GazeboConfig(backend=GazeboBackend.MOCK), adapter=MockGazeboAdapter()
    )


def test_bridge_step_progress_cb_does_not_alter_physics():
    """The SAME wrench + step(30) yields an IDENTICAL pose with/without a
    progress_cb attached — physics must never be a function of observability.

    This is the direct regression test for FIX-F5: a prior chunked-stepping
    design advanced the mock in fixed-size step slices when a listener was
    attached, which broke the mock's single-shot from-rest integration
    (``Δx = 0.5*(F/m)*(n*step_size)**2``) and made the final pose depend on
    whether progress was requested. It also asserts the recording callback
    receives an ORDERED progress sequence ending at ``(steps, steps)``.
    """

    async def _run():
        # Two independent bridges (each with its own MockGazeboAdapter world),
        # given the IDENTICAL persistent wrench, then stepped by the SAME
        # amount — one with a recording progress_cb, one with none.
        bridge_with_cb = _mock_bridge()
        bridge_without_cb = _mock_bridge()

        for bridge in (bridge_with_cb, bridge_without_cb):
            assert await bridge.adapter.spawn_entity(
                "cube",
                "<sdf/>",
                EntityPose(position=(0.0, 0.0, 0.0), orientation=(0.0, 0.0, 0.0, 1.0)),
            )
            assert (
                await bridge.apply_wrench_topic(
                    "cube", force=(10.0, 0.0, 0.0), persistent=True
                )
                is True
            )

        recorded: list[tuple[int, int]] = []

        async def _recording_cb(done, total):
            recorded.append((done, total))

        result_with_cb = await bridge_with_cb.step(steps=30, progress_cb=_recording_cb)
        result_without_cb = await bridge_without_cb.step(steps=30, progress_cb=None)

        pose_with_cb = (await bridge_with_cb.adapter.get_entity_state("cube"))["pose"][
            "position"
        ]
        pose_without_cb = (await bridge_without_cb.adapter.get_entity_state("cube"))[
            "pose"
        ]["position"]

        # --- the headline invariant: IDENTICAL final pose either way ---
        assert pose_with_cb == pytest.approx(pose_without_cb)
        # Δx = 0.5*(F/m)*(steps*step_size)**2 = 0.5*10*(30*0.001)**2 = 0.0045
        # (same single-shot-from-rest formula as test_p1_wrench_moves_entity,
        # just with steps=30 instead of 100 here).
        assert pose_with_cb[0] == pytest.approx(0.0045), pose_with_cb
        assert result_with_cb["sim_time"] == pytest.approx(result_without_cb["sim_time"])
        assert result_with_cb["steps"] == result_without_cb["steps"] == 30

        # --- the recording callback saw an ordered ramp ending at (30, 30) ---
        assert recorded, "progress_cb was never invoked"
        progresses = [p for p, _ in recorded]
        assert progresses == sorted(progresses), f"progress out of order: {recorded}"
        assert all(total == 30 for _, total in recorded), recorded
        assert recorded[-1] == (30, 30), f"last report must be (steps, steps), got {recorded[-1]}"

    anyio.run(_run)
