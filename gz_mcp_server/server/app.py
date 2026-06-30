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

import base64
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP, Image

from gazebo_mcp.tools import actuate as _actuate
from gazebo_mcp.tools import param as _param
from gazebo_mcp.tools import scene as _scene
from gazebo_mcp.tools import sensor as _sensor
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
        """Capture a one-shot camera image; returns an Image on success, else a structured error."""
        result = await _sensor.sensor_camera_image(
            topic=topic, resolution=resolution, quality=quality, world=world
        )
        if result.success:
            return Image(
                data=base64.b64decode(result.data["image_b64"]),
                format=result.data["format"],
            )
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

    # Legacy coexistence: documented-fallback path (see module docstring).
    if os.getenv("GAZEBO_LEGACY_TOOLS", "1") != "0":
        _logger.info(
            "Legacy 69 tools served by the retained low-level sdk_app entry "
            "point (gazebo-mcp-sdk); this FastMCP app serves the 9 lean tools. "
            "Single-server unification lands in P3.",
        )

    _logger.info("FastMCP app built (lean tools)", tool_count=19)
    return mcp
