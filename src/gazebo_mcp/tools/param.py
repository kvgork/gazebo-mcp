"""
Lean simulation-parameter tools (P2).

Framework-agnostic async functions that wrap the GazeboBridgeNode parameter
surface (``param_list`` / ``param_get`` / ``param_set``) and return a structured
``OperationResult``. The FastMCP app (``gz_mcp_server.server.app``) delegates its
``@mcp.tool`` param_* functions to these.

The bridge node's parameter methods are ``async`` (passthrough to the adapter),
so these wrappers ``await`` them. Each function is non-throwing: any exception is
captured into ``OperationResult(success=False, ...)`` so callers (and the MCP
transport) always receive a well-formed payload.
"""

from typing import Any

from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult

_PARAM_OP_FAILED = "PARAM_OP_FAILED"


async def param_list(world: str = "default") -> OperationResult:
    """List the simulation parameter names. ``data`` = {"parameters", "count", "world"}."""
    try:
        b = get_bridge()
        names = await b.param_list(world)
        return OperationResult(
            success=True,
            data={"parameters": names, "count": len(names), "world": world},
        )
    except Exception as e:  # noqa: BLE001 — surface as structured failure
        return OperationResult(success=False, error=str(e), error_code=_PARAM_OP_FAILED)


async def param_get(name: str, world: str = "default") -> OperationResult:
    """Get a single parameter's value.

    An unknown parameter (``KeyError`` from the bridge) maps to
    ``error_code="UNKNOWN_PARAM"``. ``data`` = {"name", "type", "value"}.
    """
    try:
        b = get_bridge()
        entry = await b.param_get(name, world)
        return OperationResult(success=True, data=entry)
    except KeyError:
        return OperationResult(
            success=False,
            error=f"unknown parameter '{name}'",
            error_code="UNKNOWN_PARAM",
            suggestions=["List available parameters with param_list"],
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_PARAM_OP_FAILED)


async def param_set(name: str, value: Any, world: str = "default") -> OperationResult:
    """Set (or create) a parameter's value.
    ``data`` = {"name", "value", "applied", "world"}.

    Only scalar values are accepted: ``int`` / ``float`` / ``bool`` / ``str``.
    A non-scalar (list/dict/tuple/...) or ``None`` is rejected with
    ``error_code="INVALID_PARAM_VALUE"`` BEFORE the bridge is touched (bool is a
    valid scalar; bool-before-int type inference is preserved by the adapter).

    ``data["applied"]`` reflects the bridge's return HONESTLY: the mock backend
    applies deterministically (True); the real backend returns False when the
    parameter isn't declared / the gz service didn't accept it. The op still
    ``success=True`` (it ran without error) — mirrors ``world_set_physics`` —
    so callers must check ``applied`` rather than assume a set took effect.
    """
    # bool is intentionally accepted here (it is a scalar param type); the
    # adapter's _infer_param_type checks bool BEFORE int so the type is correct.
    if not isinstance(value, (int, float, bool, str)):
        return OperationResult(
            success=False,
            error="param value must be scalar (int/float/bool/str)",
            error_code="INVALID_PARAM_VALUE",
            suggestions=["Pass a scalar value: an int, float, bool, or str"],
        )
    try:
        b = get_bridge()
        applied = await b.param_set(name, value, world)
        return OperationResult(
            success=True,
            data={"name": name, "value": value, "applied": bool(applied), "world": world},
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_PARAM_OP_FAILED)
