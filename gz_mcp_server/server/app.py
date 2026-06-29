"""
FastMCP application for the lean P0-B tool surface (``world_*`` / ``scene_*``).

Decision (P0-B, locked): introduce FastMCP now. The nine lean tools are authored
here as real ``@mcp.tool()`` async functions that delegate to the framework-agnostic
implementations in ``gazebo_mcp.tools.world`` and ``gazebo_mcp.tools.scene`` and
return ``result.to_dict()``.

Legacy coexistence — DOCUMENTED FALLBACK (not mounted)
------------------------------------------------------
We evaluated mounting the 69 curated legacy tools onto this FastMCP instance via
``Tool.from_function(closure, ...)`` + overriding ``Tool.parameters`` with the
curated ``inputSchema`` from ``sdk_app._build_registry()``. Empirically:
  - ``tools/list`` works: the tool appears with the curated schema.
  - ``tools/call`` does NOT: FastMCP derives a ``FuncMetadata.arg_model`` from the
    *closure signature*, and the call path validates incoming arguments against
    that inferred model — NOT against the schema we set on ``.parameters``. A
    ``**kwargs`` (or ``arguments: dict``) closure therefore rejects the real
    curated arguments at call time. Making the call work would require hand-
    building a ``FuncMetadata`` whose ``arg_model`` mirrors each curated JSON
    schema — the exact fragile hack the plan forbids.

Per the frozen contract: DO NOT block or hack. The 69 legacy tools remain served
by the retained low-level ``gz_mcp_server.server.sdk_app`` entry point
(``gazebo-mcp-sdk``). Full single-server unification (lean + legacy on one
FastMCP transport) lands in P3, when the app shell migrates to FastMCP and the
curated handlers are refactored to native ``@mcp.tool`` signatures. This P0-B
FastMCP app serves only the lean tools.

The ``GAZEBO_LEGACY_TOOLS`` env var (default ``"1"``) is read and a one-line
informational log records the chosen path; it is retained so the P3 unification
can flip behaviour without an interface change.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from gazebo_mcp.tools import scene as _scene
from gazebo_mcp.tools import world as _world
from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("fastmcp_app")


@dataclass
class GazeboSession:
    """Lifespan context: holds the shared (singleton) bridge node."""

    bridge: object


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Yield a GazeboSession holding the shared bridge when reachable.

    Best-effort by design: a backend connection failure here must NOT abort
    server startup — otherwise even ``tools/list`` would die when Gazebo is
    merely not started yet. The lean tools resolve the bridge lazily via
    ``get_bridge()`` at call time and return a structured ``OperationResult``
    error if it is down, so startup stays resilient. Mock-safe:
    ``GAZEBO_BACKEND=mock`` builds a node-less bridge and never touches ROS.
    """
    bridge = None
    try:
        bridge = get_bridge()
    except Exception as e:  # noqa: BLE001 — startup must survive a down backend
        _logger.warning(
            "Bridge unavailable at startup; tools will retry lazily per call",
            error=str(e),
        )
    yield GazeboSession(bridge=bridge)


def build_app() -> FastMCP:
    """Build the FastMCP app with the nine lean tools registered.

    Legacy 69 tools are intentionally NOT mounted here — see module docstring.
    They remain served by the retained ``gz_mcp_server.server.sdk_app`` entry
    point until the P3 single-server unification.
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

    # Legacy coexistence: documented-fallback path (see module docstring).
    if os.getenv("GAZEBO_LEGACY_TOOLS", "1") != "0":
        _logger.info(
            "Legacy 69 tools served by the retained low-level sdk_app entry "
            "point (gazebo-mcp-sdk); this FastMCP app serves the 9 lean tools. "
            "Single-server unification lands in P3.",
        )

    _logger.info("FastMCP app built (lean tools)", tool_count=9)
    return mcp
