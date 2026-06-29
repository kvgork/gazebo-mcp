"""
Lean world-control tools (P0-B).

Framework-agnostic async functions that wrap the GazeboBridgeNode physics/timing
control surface (``step`` / ``set_physics`` / ``seed``) and return a structured
``OperationResult``. The FastMCP app (``gz_mcp_server.server.app``) delegates its
``@mcp.tool`` world_* functions to these.

The bridge node's physics methods are ``async`` (passthrough to the adapter), so
these wrappers ``await`` them. Each function is non-throwing: any exception is
captured into ``OperationResult(success=False, ...)`` so callers (and the MCP
transport) always receive a well-formed payload.
"""

from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult

_WORLD_OP_FAILED = "WORLD_OP_FAILED"


async def world_step(steps: int = 1, world: str = "default") -> OperationResult:
    """Advance the simulation by ``steps`` physics steps.

    Returns OperationResult(data={"sim_time": float, "steps": int, ...}).
    """
    try:
        b = get_bridge()
        result = await b.step(steps=steps, world=world)
        return OperationResult(success=True, data=result)
    except Exception as e:  # noqa: BLE001 — surface as structured failure
        return OperationResult(success=False, error=str(e), error_code=_WORLD_OP_FAILED)


async def world_set_physics(
    step_size: float | None = None,
    rtf: float | None = None,
    world: str = "default",
) -> OperationResult:
    """Set physics step size and/or real-time factor (best-effort)."""
    try:
        b = get_bridge()
        applied = await b.set_physics(step_size=step_size, rtf=rtf, world=world)
        return OperationResult(
            success=True,
            data={"applied": applied, "step_size": step_size, "rtf": rtf, "world": world},
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_WORLD_OP_FAILED)


async def world_seed(value: int, world: str = "default") -> OperationResult:
    """Set the simulation random seed (best-effort)."""
    try:
        b = get_bridge()
        applied = await b.seed(value, world=world)
        return OperationResult(
            success=True, data={"applied": applied, "seed": value, "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_WORLD_OP_FAILED)


async def world_get_stats(world: str = "default") -> OperationResult:
    """Best-effort read of simulation stats: sim_time, step_size, rtf.

    Robust / non-throwing: reads sim_time via the adapter's world properties
    (a safe, non-advancing read) and step_size/rtf from the adapter's world
    object when exposed. Missing values fall back to ``None`` rather than
    raising — this is not part of headline acceptance.
    """
    try:
        b = get_bridge()
        sim_time: float | None = None
        step_size: float | None = None
        rtf: float | None = None

        adapter = getattr(b, "adapter", None)

        # sim_time: prefer the adapter's non-advancing world-properties read.
        if adapter is not None and hasattr(adapter, "get_world_properties"):
            try:
                info = await adapter.get_world_properties(world=world)
                sim_time = getattr(info, "sim_time", None)
            except Exception:  # noqa: BLE001 — best-effort
                pass

        # step_size / rtf: best-effort read off the mock adapter's world object.
        if adapter is not None:
            try:
                world_obj = None
                if hasattr(adapter, "_world"):
                    world_obj = adapter._world(world)
                elif hasattr(adapter, "_worlds"):
                    world_obj = adapter._worlds.get(world)
                if world_obj is not None:
                    step_size = getattr(world_obj, "step_size", None)
                    rtf = getattr(world_obj, "rtf", None)
                    if sim_time is None:
                        sim_time = getattr(world_obj, "sim_time", None)
            except Exception:  # noqa: BLE001 — best-effort
                pass

        return OperationResult(
            success=True,
            data={"sim_time": sim_time, "step_size": step_size, "rtf": rtf, "world": world},
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_WORLD_OP_FAILED)
