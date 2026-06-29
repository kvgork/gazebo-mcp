"""
Lean scene/entity tools (P0-B).

Framework-agnostic async functions that wrap the GazeboBridgeNode entity surface
(``spawn_entity`` / ``delete_entity`` / ``set_entity_state`` / ``get_model_state``
/ ``get_model_list``) and return a structured ``OperationResult``. The FastMCP app
(``gz_mcp_server.server.app``) delegates its ``@mcp.tool`` scene_* functions here.

NOTE: the bridge node's ENTITY methods are *synchronous* (they internally marshal
onto the bridge's async loop), so these wrappers call them directly — they do NOT
``await`` the entity methods. The functions themselves are declared ``async`` so
the FastMCP layer can ``await`` them uniformly alongside the world_* tools.

Each function is non-throwing: any exception is captured into
``OperationResult(success=False, ...)``.
"""

from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult

_SCENE_OP_FAILED = "SCENE_OP_FAILED"


def _pose(x: float, y: float, z: float, qx: float, qy: float, qz: float, qw: float) -> dict:
    """Build the bridge pose dict from flat scalar args."""
    return {
        "position": {"x": x, "y": y, "z": z},
        "orientation": {"x": qx, "y": qy, "z": qz, "w": qw},
    }


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
) -> OperationResult:
    """Spawn an entity from SDF/URDF content at the given pose."""
    try:
        b = get_bridge()
        pose = _pose(x, y, z, qx, qy, qz, qw)
        ok = b.spawn_entity(name, sdf, pose=pose, world=world)
        return OperationResult(
            success=True, data={"name": name, "spawned": ok, "pose": pose, "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SCENE_OP_FAILED)


async def scene_get_state(name: str, world: str = "default") -> OperationResult:
    """Get the current pose/twist of a model. MODEL_NOT_FOUND if absent."""
    try:
        b = get_bridge()
        ms = b.get_model_state(name, world=world)
        if ms is None:
            return OperationResult(
                success=False, error="model not found", error_code="MODEL_NOT_FOUND"
            )
        return OperationResult(
            success=True, data={"name": ms.name, "pose": ms.pose, "twist": ms.twist}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SCENE_OP_FAILED)


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
) -> OperationResult:
    """Set the pose of an existing model."""
    try:
        b = get_bridge()
        pose = _pose(x, y, z, qx, qy, qz, qw)
        ok = b.set_entity_state(name, pose=pose, world=world)
        return OperationResult(
            success=True, data={"name": name, "set": ok, "pose": pose, "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SCENE_OP_FAILED)


async def scene_remove(name: str, world: str = "default") -> OperationResult:
    """Delete an entity from the world."""
    try:
        b = get_bridge()
        ok = b.delete_entity(name, world=world)
        return OperationResult(
            success=True, data={"name": name, "removed": ok, "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SCENE_OP_FAILED)


async def scene_list_models(world: str = "default") -> OperationResult:
    """List the names of all models in the world."""
    try:
        b = get_bridge()
        models = [ms.name for ms in b.get_model_list(world=world)]
        return OperationResult(
            success=True, data={"models": models, "count": len(models), "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SCENE_OP_FAILED)
