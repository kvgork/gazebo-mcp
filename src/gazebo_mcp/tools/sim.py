"""
Lean ``sim_*`` tools (P4, OPTIONAL / non-default).

A thin REP-2018 ``simulation_interfaces`` PORTABILITY SHIM: each ``sim_*``
function delegates to the EXISTING ``scene_*``/``world_*`` lean tools (see
``gazebo_mcp.tools.scene`` / ``gazebo_mcp.tools.world``) rather than talking to
the bridge directly, so behaviour is byte-identical to calling the underlying
tool. The point of this module is naming-surface portability (a client written
against the ``simulation_interfaces`` verb set — spawn/delete/reset/step/
get_state — can call these instead of the gz-specific ``scene_*``/``world_*``
names), NOT a new capability.

The REAL ``simulation_interfaces`` ROS adapter now EXISTS:
``bridge/adapters/sim_interfaces_adapter.py`` (``SimInterfacesAdapter``) is a
REP-2018 client that drives any ``simulation_interfaces`` backend, live-verified
against the ``ros_gz_sim`` gzserver component (P4-real DONE 2026-07-08; see
``tests/integration/test_p4_real_sim_interfaces.py``). It is not yet wired into
default bridge backend-selection, so these shim tools still route to
scene_*/world_*. ``sim_get_features`` reports the adapter status via
``real_adapter``.

Strictly optional / non-default: these functions are always importable, but the
FastMCP app (``gz_mcp_server.server.app``) only registers them as ``@mcp.tool``
wrappers when ``GAZEBO_SIM_TOOLS=1`` (see ``build_app()``), so they never
appear in the default tool surface.

Each function is non-throwing: any exception is captured into
``OperationResult(success=False, ...)``.
"""

from gazebo_mcp.tools import scene as _scene
from gazebo_mcp.tools import world as _world
from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult

_SIM_OP_FAILED = "SIM_OP_FAILED"


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
) -> OperationResult:
    """Spawn an entity — REP-2018 ``spawn_entity`` shim over ``scene_spawn``."""
    return await _scene.scene_spawn(
        name=name, sdf=sdf, x=x, y=y, z=z, qx=qx, qy=qy, qz=qz, qw=qw, world=world
    )


async def sim_delete(name: str, world: str = "default") -> OperationResult:
    """Delete an entity — REP-2018 ``delete_entity`` shim over ``scene_remove``."""
    return await _scene.scene_remove(name=name, world=world)


async def sim_reset(world: str = "default") -> OperationResult:
    """Reset the world to its initial state — REP-2018 ``reset_simulation`` shim.

    Delegates to the bridge's ``reset_world`` (models + physics reset), which is
    a synchronous (internally-marshalled) call, mirroring the scene_* wrappers'
    non-await pattern for the bridge's sync entity/reset surface.
    """
    try:
        b = get_bridge()
        ok = b.reset_world(world=world)
        return OperationResult(success=True, data={"reset": ok, "world": world})
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SIM_OP_FAILED)


async def sim_step(steps: int = 1, world: str = "default") -> OperationResult:
    """Advance the simulation — REP-2018 ``step`` shim over ``world_step``."""
    return await _world.world_step(steps=steps, world=world)


async def sim_get_features(world: str = "default") -> OperationResult:
    """Static capability report — no bridge mutation.

    Reports the REP-2018 ``simulation_interfaces`` operations this shim
    supports (routed to existing scene_*/world_* tools) and the currently
    configured backend name (best-effort; ``"unknown"`` if unavailable). The
    real ``simulation_interfaces`` ROS-service adapter
    (``bridge/adapters/sim_interfaces_adapter.py``) now EXISTS and is
    live-verified against the ``ros_gz_sim`` gzserver component backend
    (see ``tests/integration/test_p4_real_sim_interfaces.py``); it is not yet
    wired into default bridge backend-selection.

    Non-throwing and safe even with no world/backend reachable.
    """
    backend = "unknown"
    try:
        b = get_bridge()
        adapter = getattr(b, "adapter", None)
        if adapter is not None and hasattr(adapter, "get_backend_name"):
            backend = adapter.get_backend_name()
    except Exception:  # noqa: BLE001 — best-effort, never fails the report
        pass

    return OperationResult(
        success=True,
        data={
            "spec": "REP-2018 simulation_interfaces (portability shim)",
            "supported_ops": ["spawn", "delete", "reset", "step", "get_state"],
            "backend": backend,
            "real_adapter": (
                "available — SimInterfacesAdapter (REP-2018 client) live-verified "
                "against the ros_gz_sim gzserver component (/gz_server services); "
                "not yet wired into default backend-selection"
            ),
            "world": world,
        },
    )
