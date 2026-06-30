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
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.types import TextContent

from gazebo_mcp.tools import actuate as _actuate
from gazebo_mcp.tools import param as _param
from gazebo_mcp.tools import scene as _scene
from gazebo_mcp.tools import sensor as _sensor
from gazebo_mcp.tools import world as _world
from gazebo_mcp.utils.logger import get_logger
from gz_mcp_server.server.legacy_mount import register_legacy_tools
from gz_mcp_server.server.session import GazeboSession

_logger = get_logger("fastmcp_app")

# Key under which the single shared/default session lives in the lifespan dict.
# stdio (the default transport) is a single implicit session that uses it;
# every HTTP request without an ``Mcp-Session-Id`` falls back to it too.
_DEFAULT_SESSION_KEY = "default"
_SESSIONS_KEY = "sessions"

__all__ = ["GazeboSession", "app_lifespan", "build_app", "get_session"]


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
    """
    mcp = FastMCP("gazebo-mcp", lifespan=app_lifespan)

    # ------------------------------- world_* -------------------------------

    @mcp.tool()
    async def world_step(
        steps: int = 1, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Advance the simulation by N physics steps."""
        return (await _world.world_step(steps=steps, world=world)).to_dict()

    @mcp.tool()
    async def world_set_physics(
        step_size: Optional[float] = None,
        rtf: Optional[float] = None,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Set physics step size and/or real-time factor (best-effort)."""
        return (
            await _world.world_set_physics(step_size=step_size, rtf=rtf, world=world)
        ).to_dict()

    @mcp.tool()
    async def world_seed(
        value: int, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Set the simulation random seed (best-effort)."""
        return (await _world.world_seed(value=value, world=world)).to_dict()

    @mcp.tool()
    async def world_get_stats(world: str = "default", ctx: Optional[Context] = None) -> dict:
        """Best-effort read of simulation stats (sim_time, step_size, rtf)."""
        return (await _world.world_get_stats(world=world)).to_dict()

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
        return (
            await _scene.scene_spawn(
                name=name, sdf=sdf, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw, world=world
            )
        ).to_dict()

    @mcp.tool()
    async def scene_get_state(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get the current pose/twist of a model."""
        return (await _scene.scene_get_state(name=name, world=world)).to_dict()

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
        return (
            await _scene.scene_set_state(
                name=name, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw, world=world
            )
        ).to_dict()

    @mcp.tool()
    async def scene_remove(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Delete an entity from the world."""
        return (await _scene.scene_remove(name=name, world=world)).to_dict()

    @mcp.tool()
    async def scene_list_models(world: str = "default", ctx: Optional[Context] = None) -> dict:
        """List the names of all models in the world."""
        return (await _scene.scene_list_models(world=world)).to_dict()

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
        return (
            await _actuate.actuate_wrench(
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
        ).to_dict()

    @mcp.tool()
    async def actuate_clear_wrench(
        entity: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Clear any wrench applied to an entity."""
        return (await _actuate.actuate_clear_wrench(entity=entity, world=world)).to_dict()

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
        return (
            await _actuate.actuate_joint(
                model=model, joint=joint, mode=mode, value=value, world=world
            )
        ).to_dict()

    @mcp.tool()
    async def actuate_joint_trajectory(
        model: str,
        points: list,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """Command a joint trajectory ([{positions, time_from_start}, ...]) for a model."""
        return (
            await _actuate.actuate_joint_trajectory(model=model, points=points, world=world)
        ).to_dict()

    # ------------------------------- sensor_* ------------------------------

    @mcp.tool()
    async def sensor_list(
        sensor_type: Optional[str] = None,
        world: str = "default",
        ctx: Optional[Context] = None,
    ) -> dict:
        """List sensors in the world (each descriptor carries health), optionally filtered by type."""
        return (await _sensor.sensor_list(sensor_type=sensor_type, world=world)).to_dict()

    @mcp.tool()
    async def sensor_snapshot(
        topic: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get the latest typed one-shot sample for the sensor publishing on a topic."""
        return (await _sensor.sensor_snapshot(topic=topic, world=world)).to_dict()

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
        result = await _sensor.sensor_camera_image(
            topic=topic, resolution=resolution, quality=quality, world=world
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
        return (await _param.param_list(world=world)).to_dict()

    @mcp.tool()
    async def param_get(
        name: str, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Get a single simulation parameter's value."""
        return (await _param.param_get(name=name, world=world)).to_dict()

    @mcp.tool()
    async def param_set(
        name: str, value: Any, world: str = "default", ctx: Optional[Context] = None
    ) -> dict:
        """Set (or create) a simulation parameter's value."""
        return (await _param.param_set(name=name, value=value, world=world)).to_dict()

    # P3 unification: mount the curated legacy tools as native FastMCP tools on
    # this same app (lists AND calls). Honors GAZEBO_LEGACY_TOOLS for the
    # deprecated-8 exclusion; lean tools above win on any name collision.
    legacy_count = register_legacy_tools(mcp)

    _logger.info(
        "Unified FastMCP app built (lean + legacy)",
        lean_count=19,
        legacy_count=legacy_count,
        total=19 + legacy_count,
    )
    return mcp
