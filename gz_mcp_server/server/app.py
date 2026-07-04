"""
FastMCP application for the lean P0-B tool surface (``world_*`` / ``scene_*``).

Decision (P0-B, locked): introduce FastMCP now. The nine lean tools are authored
here as real ``@mcp.tool()`` async functions that delegate to the framework-agnostic
implementations in ``gazebo_mcp.tools.world`` and ``gazebo_mcp.tools.scene`` and
return ``result.to_dict()``.

Legacy unification — UNIFIED IN P3
----------------------------------
The 69 curated legacy tools are now mounted onto this same FastMCP instance as
*native* callable tools (see ``gz_mcp_server.server.legacy_mount``), so ONE
FastMCP server serves the lean (19) + legacy (69) surfaces over BOTH stdio and
Streamable HTTP. The P0-B blocker (``tools/call`` rejecting curated arguments
because FastMCP inferred an ``arg_model`` from a ``**kwargs`` closure) is solved
by synthesizing a closure whose ``__signature__`` mirrors each curated JSON
schema — so the inferred ``arg_model`` matches the curated surface and calls
succeed. ``register_legacy_tools(mcp)`` runs after the lean tools below.

The low-level ``gz_mcp_server.server.sdk_app`` entry point (``gazebo-mcp-sdk``)
is RETAINED as a revert path, but the FastMCP app is now the unified one.

The ``GAZEBO_LEGACY_TOOLS`` env var (default ``"1"``) gates the deprecated 8
advanced-sensor tools: ``"1"`` mounts all 69 (back-compat); ``"0"`` mounts the
61 non-deprecated legacy tools only.
"""

import base64
import os
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Optional

from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.types import TextContent

from gazebo_mcp.tools import actuate as _actuate
from gazebo_mcp.tools import param as _param
from gazebo_mcp.tools import scene as _scene
from gazebo_mcp.tools import sensor as _sensor
from gazebo_mcp.tools import sim as _sim
from gazebo_mcp.tools import world as _world
from gazebo_mcp.tools._bridge_helper import (
    get_bridge_for_ctx,
    reset_current_bridge,
    set_current_bridge,
)
from gazebo_mcp.utils.logger import get_logger
from gz_mcp_server.server.legacy_mount import register_legacy_tools
from gz_mcp_server.server.resources.sensors import register_sensor_resources
from gz_mcp_server.server.session import GazeboSession

_logger = get_logger("fastmcp_app")

# world_step progress streaming (P5, FIX-F5). When a client supplies a
# progressToken (ctx present) and asks for MORE than 1 step, a progress_cb is
# passed all the way down to the adapter's SINGLE native step() call, which
# reports an evenly-spaced cosmetic ramp from INSIDE that one call — the sim is
# NEVER chunked at this layer (chunking previously made the final pose depend
# on whether a progressToken was present; see mock_adapter.step's docstring).
# steps <= 1 (or ctx is None, e.g. stdio, or no token) => progress_cb is None.

# Key under which the single shared/default session lives in the lifespan dict.
# stdio (the default transport) is a single implicit session that uses it;
# every HTTP request without an ``Mcp-Session-Id`` falls back to it too.
_DEFAULT_SESSION_KEY = "default"
_SESSIONS_KEY = "sessions"

# Per-server cap on the live HTTP-session registry (P3 #2/#5). mcp 1.27.1 exposes
# NO per-HTTP-session teardown callback into the FastMCP lifespan context, so a
# long-lived server would otherwise accumulate one GazeboSession per distinct
# Mcp-Session-Id forever. This cap is the leak guard: on overflow we evict the
# oldest (insertion-order = LRU-ish) session and aclose() its bridge.
MAX_HTTP_SESSIONS = 64

__all__ = ["GazeboSession", "app_lifespan", "build_app", "get_session"]


async def _with_session_bridge(
    ctx: Optional[Context], coro_fn: Callable[[], Awaitable[Any]]
) -> Any:
    """Run ``coro_fn()`` with the request's per-session bridge bound (P3).

    This is the single place that makes every (unchanged-body) lean tool
    per-session over HTTP: it resolves the bridge for ``ctx`` (the per-session
    ``GazeboSession`` bridge when ctx carries an ``Mcp-Session-Id``, else the
    process singleton) and binds it into the ``_current_bridge`` contextvar, so
    the delegate's ``get_bridge()`` calls transparently hit that bridge. Over
    stdio / when ctx has no reachable session, this resolves to the singleton —
    identical to today's behaviour, so the existing suite is unaffected.

    The bind is always reset in ``finally`` (contextvars are copied per asyncio
    Task, so concurrent HTTP requests never clobber each other's binding).
    """
    bridge = await get_bridge_for_ctx(ctx)
    token = set_current_bridge(bridge)
    try:
        return await coro_fn()
    finally:
        reset_current_bridge(token)


async def _to_dict(result_coro: Awaitable[Any]) -> dict:
    """Await a lean-tool delegate coroutine and return its ``OperationResult`` dict."""
    return (await result_coro).to_dict()


def _has_progress_token(ctx: Optional[Context]) -> bool:
    """True iff the current request carries a ``progressToken`` (a listener).

    ``Context.report_progress`` is a no-op without a token (verified in mcp
    1.27.1: it reads ``request_context.meta.progressToken`` and returns early
    when absent). So when there is no token we gain nothing by wiring a
    ``progress_cb`` into the adapter call — skipping it there keeps the
    no-listener path byte-identical to the pre-P5 single-shot behaviour (and
    avoids paying the callback overhead for a report_progress that is a no-op
    anyway).
    """
    if ctx is None:
        return False
    try:
        meta = ctx.request_context.meta
    except Exception:  # noqa: BLE001 — no active request context (unit Context)
        return False
    return bool(meta is not None and getattr(meta, "progressToken", None) is not None)


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Initialize the per-session registry; close every session on shutdown.

    The yielded value becomes ``ctx.request_context.lifespan_context`` for every
    tool/resource call on this server (a *per-server* singleton dict shared
    across all MCP sessions — verified empirically on mcp 1.27.1). It holds:

    - ``"sessions"``: ``dict[str(Mcp-Session-Id) -> GazeboSession]`` — populated
      lazily by ``get_session(ctx)`` on first access per HTTP session.
    - ``"default"``: the single shared ``GazeboSession`` used by stdio (the
      default transport, one implicit session) and by any HTTP request that
      carries no ``Mcp-Session-Id``.

    Resilient startup (P0-B): ``GazeboSession.create()`` never raises on a down
    backend, so ``tools/list`` works even when Gazebo is not yet up.

    Teardown: the code after ``yield`` runs on the lowlevel server's lifespan
    shutdown (the SDK enters this as an ``async with`` — see
    ``mcp.server.lowlevel.server.Server.run``). mcp 1.27.1 exposes no per-HTTP-
    session teardown callback into the FastMCP lifespan-context state, so we
    close every cached session here on server shutdown (mock = no-op-safe).
    """
    # The default/stdio session binds to the process singleton so the lean tools
    # (which call get_bridge() directly) and this session share one world.
    default_session = await GazeboSession.create(use_singleton=True)
    registry: dict = {_SESSIONS_KEY: {}, _DEFAULT_SESSION_KEY: default_session}
    try:
        yield registry
    finally:
        # Close per-session bridges first, then the shared/default one.
        for sid, session in list(registry[_SESSIONS_KEY].items()):
            try:
                await session.aclose()
            except Exception as e:  # noqa: BLE001 — best-effort teardown
                _logger.warning("Session aclose failed", session_id=sid, error=str(e))
        registry[_SESSIONS_KEY].clear()
        try:
            await default_session.aclose()
        except Exception as e:  # noqa: BLE001 — best-effort teardown
            _logger.warning("Default session aclose failed", error=str(e))


def _session_id_from_ctx(ctx: Optional[Context]) -> Optional[str]:
    """Return the ``Mcp-Session-Id`` for this request, or ``None`` for stdio.

    Verified on mcp 1.27.1: over Streamable HTTP the Starlette request is at
    ``ctx.request_context.request`` and carries the canonical session id in the
    ``mcp-session-id`` header (it matches the client-negotiated id). Over stdio
    / in-memory there is no Starlette request (``request is None``), so there is
    no session id and the caller falls back to the default session.
    """
    if ctx is None:
        return None
    try:
        request = getattr(ctx.request_context, "request", None)
    except Exception:  # noqa: BLE001 — request_context unavailable outside a call
        return None
    if request is None:
        return None
    try:
        return request.headers.get("mcp-session-id")
    except Exception:  # noqa: BLE001 — defensive
        return None


async def get_session(ctx: Optional[Context]) -> GazeboSession:
    """Resolve (creating + caching on first access) the request's GazeboSession.

    Resolution:
    - HTTP request with an ``Mcp-Session-Id`` → the per-session ``GazeboSession``
      stored in ``lifespan_context["sessions"][session_id]``, created on first
      access. Two distinct session ids therefore get isolated bridges +
      subscriptions.
    - stdio / no session id / no reachable lifespan registry → the single shared
      ``lifespan_context["default"]`` session (falling back to the process
      singleton bridge when even the registry is absent, e.g. a unit test that
      builds a bare ``Context``).

    Args:
        ctx: The tool/resource ``Context`` for the current request (may be
            ``None`` outside a request).

    Returns:
        The ``GazeboSession`` for this request.
    """
    registry = None
    if ctx is not None:
        try:
            lc = ctx.request_context.lifespan_context
            if isinstance(lc, dict) and _SESSIONS_KEY in lc:
                registry = lc
        except Exception:  # noqa: BLE001 — no active request context
            registry = None

    # No lifespan registry reachable (e.g. a unit-test Context, or a tool called
    # outside the server run loop) → synthesize a one-off session over the
    # process singleton so callers always get a usable bridge.
    if registry is None:
        return await GazeboSession.create()

    session_id = _session_id_from_ctx(ctx)
    if session_id is None:
        return registry[_DEFAULT_SESSION_KEY]

    sessions: dict = registry[_SESSIONS_KEY]
    session = sessions.get(session_id)
    if session is None:
        # Bound the registry (P3 #2/#5): mcp 1.27.1 has NO per-HTTP-session
        # teardown hook, so evict the oldest (insertion-order) session and close
        # its bridge before inserting a new one once we hit the cap.
        while len(sessions) >= MAX_HTTP_SESSIONS:
            old_sid, old_session = next(iter(sessions.items()))
            del sessions[old_sid]
            try:
                await old_session.aclose()
            except Exception as e:  # noqa: BLE001 — best-effort eviction
                _logger.warning(
                    "Evicted-session aclose failed", session_id=old_sid, error=str(e)
                )
            _logger.info(
                "Evicted oldest HTTP session (cap reached)",
                evicted=old_sid,
                cap=MAX_HTTP_SESSIONS,
            )
        session = await GazeboSession.create()
        sessions[session_id] = session
        _logger.info("Created per-session GazeboSession", session_id=session_id)
    return session


def build_app() -> FastMCP:
    """Build the unified FastMCP app: 19 lean tools + the curated legacy tools.

    The 19 lean ``@mcp.tool`` functions are registered first, then
    ``register_legacy_tools(mcp)`` mounts the curated legacy tools as native
    FastMCP tools (P3 unification — see module docstring). Result: one FastMCP
    app serving lean + legacy over both stdio and Streamable HTTP.

    The ``GAZEBO_LEGACY_TOOLS`` env var (default ``"1"``) gates only the
    deprecated 8 advanced-sensor tools: legacy is always mounted; ``"0"`` simply
    excludes those 8 (P2 #17).

    The ``GAZEBO_SIM_TOOLS`` env var (default ``"0"``, OPTIONAL/non-default —
    P4) additionally mounts 5 ``sim_*`` tools (a thin REP-2018
    ``simulation_interfaces`` portability shim routed to the scene_*/world_*
    tools above) when set to ``"1"``. Absent/``"0"`` leaves the default tool
    surface unchanged.
    """
    mcp = FastMCP("gazebo-mcp", lifespan=app_lifespan)

    # ------------------------------- world_* -------------------------------

    @mcp.tool()
    async def world_step(
        steps: int = 1, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Advance the simulation by N physics steps.

        FIX-F5 (P5 hardening): physics is ALWAYS a single native adapter call —
        it is never chunked. A prior chunked-stepping design advanced the sim in
        fixed-size slices to emit incremental progress, but that made the FINAL
        POSE depend on whether a progressToken was present (chunking is not
        composable with the mock's from-rest integration — see
        ``mock_adapter.step``'s docstring). Progress is now reported from
        INSIDE the single adapter call instead (an evenly-spaced cosmetic ramp
        for the mock backend; a no-op for backends that don't support it yet),
        so the result is physics-IDENTICAL regardless of whether a listener is
        attached. ``report_progress`` is best-effort: a progress failure never
        fails the tool.
        """

        async def _run() -> dict:
            progress_cb = None
            if ctx is not None and steps > 1 and _has_progress_token(ctx):

                async def progress_cb(done, total):  # noqa: F811 - inner def
                    try:
                        await ctx.report_progress(progress=done, total=total)
                    except Exception as e:  # noqa: BLE001 — progress is advisory
                        _logger.debug(
                            "world_step progress report failed", error=str(e)
                        )

            return await _to_dict(
                _world.world_step(steps=steps, world=world, progress_cb=progress_cb)
            )

        return await _with_session_bridge(ctx, _run)

    @mcp.tool()
    async def world_set_physics(
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Set physics step size and/or real-time factor (best-effort)."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _world.world_set_physics(step_size=step_size, rtf=rtf, world=world)
            ),
        )

    @mcp.tool()
    async def world_seed(
        value: int, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Set the simulation random seed (best-effort)."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_world.world_seed(value=value, world=world))
        )

    @mcp.tool()
    async def world_get_stats(world: str = "default", ctx: Optional[Context] = None) -> dict:
        """Best-effort read of simulation stats (sim_time, step_size, rtf)."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_world.world_get_stats(world=world))
        )

    # ------------------------------- scene_* -------------------------------

    @mcp.tool()
    async def scene_spawn(
        name: str,
        sdf: str,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        qx: float = 0.0,
        qy: float = 0.0,
        qz: float = 0.0,
        qw: float = 1.0,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Spawn an entity from SDF/URDF content at the given pose."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _scene.scene_spawn(
                    name=name, sdf=sdf, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw, world=world
                )
            ),
        )

    @mcp.tool()
    async def scene_get_state(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get the current pose/twist of a model."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_scene.scene_get_state(name=name, world=world))
        )

    @mcp.tool()
    async def scene_set_state(
        name: str,
        x: float,
        y: float,
        z: float,
        qx: float = 0.0,
        qy: float = 0.0,
        qz: float = 0.0,
        qw: float = 1.0,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Set the pose of an existing model."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _scene.scene_set_state(
                    name=name, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw, world=world
                )
            ),
        )

    @mcp.tool()
    async def scene_remove(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Delete an entity from the world."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_scene.scene_remove(name=name, world=world))
        )

    @mcp.tool()
    async def scene_list_models(world: str = "default", ctx: Optional[Context] = None) -> dict:
        """List the names of all models in the world."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_scene.scene_list_models(world=world))
        )

    # ------------------------------ actuate_* ------------------------------

    @mcp.tool()
    async def actuate_wrench(
        entity: str,
        fx: float = 0.0,
        fy: float = 0.0,
        fz: float = 0.0,
        tx: float = 0.0,
        ty: float = 0.0,
        tz: float = 0.0,
        duration: float = 0.0,
        persistent: bool = False,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Apply a wrench (force + torque) to an entity via the wrench topic."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _actuate.actuate_wrench(
                    entity=entity,
                    fx=fx,
                    fy=fy,
                    fz=fz,
                    tx=tx,
                    ty=ty,
                    tz=tz,
                    duration=duration,
                    persistent=persistent,
                    world=world,
                )
            ),
        )

    @mcp.tool()
    async def actuate_clear_wrench(
        entity: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Clear any wrench applied to an entity."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_actuate.actuate_clear_wrench(entity=entity, world=world))
        )

    @mcp.tool()
    async def actuate_joint(
        model: str,
        joint: str,
        mode: str = "pos",
        value: float = 0.0,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Command a single joint (pos/vel/force), validated against the manifest."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _actuate.actuate_joint(
                    model=model, joint=joint, mode=mode, value=value, world=world
                )
            ),
        )

    @mcp.tool()
    async def actuate_joint_trajectory(
        model: str,
        points: list,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Command a joint trajectory ([{positions, time_from_start}, ...]) for a model."""
        return await _with_session_bridge(
            ctx,
            lambda: _to_dict(
                _actuate.actuate_joint_trajectory(model=model, points=points, world=world)
            ),
        )

    # ------------------------------- sensor_* ------------------------------

    @mcp.tool()
    async def sensor_list(
        sensor_type: Optional[str] = None,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """List sensors in the world (each descriptor carries health), optionally filtered by type."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_sensor.sensor_list(sensor_type=sensor_type, world=world))
        )

    @mcp.tool()
    async def sensor_snapshot(
        topic: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get the latest typed one-shot sample for the sensor publishing on a topic."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_sensor.sensor_snapshot(topic=topic, world=world))
        )

    @mcp.tool()
    async def sensor_camera_image(
        topic: str,
        resolution: str = "640x480",
        quality: int = 60,
        world: str = "default",
        ctx: Optional[Context] = None,
    ):
        """Capture a one-shot camera image; returns an Image on success, else a structured error.

        When the backend marks the frame as synthetic (the mock solid-color
        fill), the success return is a content LIST ``[Image, TextContent]``
        where the trailing text warns "synthetic mock frame (backend=mock)" so a
        vision consumer cannot mistake the fill for a real rendered frame. The
        Image is always first, so callers that read ``content[0]`` are unchanged.
        """
        result = await _with_session_bridge(
            ctx,
            lambda: _sensor.sensor_camera_image(
                topic=topic, resolution=resolution, quality=quality, world=world
            ),
        )
        if result.success:
            image = Image(
                data=base64.b64decode(result.data["image_b64"]),
                format=result.data["format"],
            )
            if result.data.get("synthetic"):
                backend = result.data.get("backend", "mock")
                return [
                    image,
                    TextContent(
                        type="text",
                        text=f"synthetic mock frame (backend={backend})",
                    ),
                ]
            return image
        return result.to_dict()

    # ------------------------------- param_* -------------------------------

    @mcp.tool()
    async def param_list(world: str = "default", ctx: Optional[Context] = None) -> dict:
        """List the simulation parameter names."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_param.param_list(world=world))
        )

    @mcp.tool()
    async def param_get(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get a single simulation parameter's value."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_param.param_get(name=name, world=world))
        )

    @mcp.tool()
    async def param_set(
        name: str, value: Any, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Set (or create) a simulation parameter's value."""
        return await _with_session_bridge(
            ctx, lambda: _to_dict(_param.param_set(name=name, value=value, world=world))
        )

    # -------------------------------- sim_* --------------------------------
    # P4 (OPTIONAL, non-default): a thin REP-2018 `simulation_interfaces`
    # portability shim routed to the scene_*/world_* tools above. Gated behind
    # GAZEBO_SIM_TOOLS so the default tool surface (list_tools count) is
    # UNCHANGED unless an operator opts in.
    sim_tools_enabled = os.getenv("GAZEBO_SIM_TOOLS", "0") == "1"
    if sim_tools_enabled:

        @mcp.tool()
        async def sim_spawn(
            name: str,
            sdf: str,
            x: float = 0.0,
            y: float = 0.0,
            z: float = 0.0,
            qx: float = 0.0,
            qy: float = 0.0,
            qz: float = 0.0,
            qw: float = 1.0,
            world: str = "default",
            ctx: Optional[Context] = None,
        ) -> dict:
            """Spawn an entity — REP-2018 shim over ``scene_spawn``."""
            return await _with_session_bridge(
                ctx,
                lambda: _to_dict(
                    _sim.sim_spawn(
                        name=name, sdf=sdf, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw,
                        world=world,
                    )
                ),
            )

        @mcp.tool()
        async def sim_delete(
            name: str, world: str = "default", ctx: Optional[Context] = None
        ) -> dict:
            """Delete an entity — REP-2018 shim over ``scene_remove``."""
            return await _with_session_bridge(
                ctx, lambda: _to_dict(_sim.sim_delete(name=name, world=world))
            )

        @mcp.tool()
        async def sim_reset(world: str = "default", ctx: Optional[Context] = None) -> dict:
            """Reset the world — REP-2018 shim over the bridge's ``reset_world``."""
            return await _with_session_bridge(
                ctx, lambda: _to_dict(_sim.sim_reset(world=world))
            )

        @mcp.tool()
        async def sim_step(
            steps: int = 1, world: str = "default", ctx: Optional[Context] = None
        ) -> dict:
            """Advance the simulation — REP-2018 shim over ``world_step``."""
            return await _with_session_bridge(
                ctx, lambda: _to_dict(_sim.sim_step(steps=steps, world=world))
            )

        @mcp.tool()
        async def sim_get_features(
            world: str = "default", ctx: Optional[Context] = None
        ) -> dict:
            """Static REP-2018 ``simulation_interfaces`` capability report."""
            return await _with_session_bridge(
                ctx, lambda: _to_dict(_sim.sim_get_features(world=world))
            )

    # P3 unification: mount the curated legacy tools as native FastMCP tools on
    # this same app (lists AND calls). Honors GAZEBO_LEGACY_TOOLS for the
    # deprecated-8 exclusion; lean tools above win on any name collision.
    legacy_count = register_legacy_tools(mcp)

    # P3 resources: expose gz://sensor/{name} (latest cached sample) + the
    # notify-then-poll subscribe/updated(bare ping)/read wiring.
    register_sensor_resources(mcp)

    sim_count = 5 if sim_tools_enabled else 0
    _logger.info(
        "Unified FastMCP app built (lean + legacy)",
        lean_count=19,
        sim_count=sim_count,
        legacy_count=legacy_count,
        total=19 + sim_count + legacy_count,
    )
    return mcp
