"""
Lean actuation tools (P1).

Framework-agnostic async functions that wrap the GazeboBridgeNode actuation
surface (``apply_wrench_topic`` / ``clear_wrench`` / ``command_joint`` /
``command_joint_trajectory``) and return a structured ``OperationResult``. The
FastMCP app (``gz_mcp_server.server.app``) delegates its ``@mcp.tool`` actuate_*
functions to these.

The bridge node's actuation methods are ``async`` (passthrough to the adapter),
so these wrappers ``await`` them. Each function is non-throwing: any exception is
captured into ``OperationResult(success=False, ...)`` so callers (and the MCP
transport) always receive a well-formed payload.

Joint commanding (``actuate_joint``) additionally validates the requested target
against the model manifest BEFORE touching the bridge:
  - ``mode == "pos"`` and the joint has ``lower``/``upper`` limits and the value
    is out of range  -> ``JOINT_LIMIT_EXCEEDED`` (bridge NOT called).
  - the (model, joint) pair is absent from the manifest entirely
    -> ``UNKNOWN_JOINT`` (bridge NOT called; safe-by-default per the contract).
  - a continuous joint (no limits) or a non-``pos`` mode -> no range check.

Manifest resolution: ``GazeboConfig.from_environment().model_manifest`` if set,
else the in-repo default ``<repo>/models/jetank/manifest.json`` resolved from this
file's location (``Path(__file__).resolve().parents[3]``). The loaded manifest is
cached at module level; ``_reset_manifest_cache()`` clears it (used by tests).
"""

import json
from pathlib import Path

from gazebo_mcp.bridge.config import GazeboConfig
from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("actuate_tools")

_ACTUATE_OP_FAILED = "ACTUATE_OP_FAILED"

# Repo root is three levels up from this file:
#   <repo>/src/gazebo_mcp/tools/actuate.py -> parents[3] == <repo>
_DEFAULT_MANIFEST = Path(__file__).resolve().parents[3] / "models" / "jetank" / "manifest.json"

# Module-level cache: maps the resolved manifest path -> parsed dict. Caching by
# path (rather than a bare bool) keeps the cache correct if the configured path
# changes between calls (e.g. across tests that set GAZEBO_MODEL_MANIFEST).
_manifest_cache: dict[str, dict] = {}


def _manifest_path() -> Path:
    """Resolve the manifest path: configured ``model_manifest`` or the repo default."""
    configured = GazeboConfig.from_environment().model_manifest
    if configured:
        return Path(configured)
    return _DEFAULT_MANIFEST


def _load_manifest() -> dict:
    """Load and cache the model manifest JSON.

    Non-throwing: a missing or malformed manifest yields an empty dict (and a
    debug log) so joint commanding degrades gracefully to ``UNKNOWN_JOINT``
    rather than crashing the tool.
    """
    path = _manifest_path()
    key = str(path)
    if key in _manifest_cache:
        return _manifest_cache[key]

    data: dict = {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:  # noqa: BLE001 — degrade gracefully, never crash
        _logger.debug("Model manifest unavailable; proceeding without limits",
                      path=key, error=str(e))
        data = {}

    _manifest_cache[key] = data
    return data


def _reset_manifest_cache() -> None:
    """Clear the manifest cache (test helper / config-change hook)."""
    _manifest_cache.clear()


def _joint_limits(model: str, joint: str) -> tuple | None:
    """Return ``(lower, upper)`` limits for a (model, joint), else ``None``.

    ``None`` means "no positional limits to enforce" — covers both a continuous
    joint (no ``lower``/``upper`` keys) and a missing manifest. Use
    ``_joint_known`` to distinguish a present-but-unlimited joint from an
    entirely unknown one.
    """
    joint_def = _load_manifest().get(model, {}).get("joints", {}).get(joint)
    if not isinstance(joint_def, dict):
        return None
    if "lower" in joint_def and "upper" in joint_def:
        return (float(joint_def["lower"]), float(joint_def["upper"]))
    return None


def _joint_known(model: str, joint: str) -> bool:
    """True if the (model, joint) pair is present in the manifest at all."""
    return joint in _load_manifest().get(model, {}).get("joints", {})


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
) -> OperationResult:
    """Apply a wrench (force + torque) to an entity via the wrench topic."""
    try:
        b = get_bridge()
        ok = await b.apply_wrench_topic(
            entity, "", (fx, fy, fz), (tx, ty, tz), duration, persistent, world
        )
        return OperationResult(
            success=True,
            data={
                "entity": entity,
                "applied": ok,
                "force": [fx, fy, fz],
                "torque": [tx, ty, tz],
                "duration": duration,
                "persistent": persistent,
                "world": world,
            },
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_ACTUATE_OP_FAILED)


async def actuate_clear_wrench(entity: str, world: str = "default") -> OperationResult:
    """Clear any wrench applied to an entity."""
    try:
        b = get_bridge()
        ok = await b.clear_wrench(entity, world=world)
        return OperationResult(
            success=True, data={"entity": entity, "cleared": ok, "world": world}
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_ACTUATE_OP_FAILED)


async def actuate_joint(
    model: str,
    joint: str,
    mode: str = "pos",
    value: float = 0.0,
    world: str = "default",
) -> OperationResult:
    """Command a single joint (pos/vel/force), validated against the manifest.

    Validation (before the bridge is touched):
      - unknown (model, joint)         -> UNKNOWN_JOINT
      - mode=="pos" and value out of   -> JOINT_LIMIT_EXCEEDED
        the joint's [lower, upper]
    """
    try:
        # Manifest validation BEFORE any bridge call.
        if not _joint_known(model, joint):
            return OperationResult(
                success=False,
                error=f"joint '{joint}' not found for model '{model}' in manifest",
                error_code="UNKNOWN_JOINT",
                suggestions=[
                    "Check the joint name against the model manifest",
                    "Verify the model name is correct",
                ],
            )

        if mode == "pos":
            limits = _joint_limits(model, joint)
            if limits is not None:
                lower, upper = limits
                if value < lower or value > upper:
                    return OperationResult(
                        success=False,
                        error=(
                            f"joint {joint} value {value} outside limits "
                            f"[{lower},{upper}]"
                        ),
                        error_code="JOINT_LIMIT_EXCEEDED",
                        suggestions=[
                            f"Command a value within [{lower}, {upper}]",
                        ],
                    )

        b = get_bridge()
        ok = await b.command_joint(model, joint, mode, value, world)
        return OperationResult(
            success=True,
            data={
                "model": model,
                "joint": joint,
                "mode": mode,
                "value": value,
                "applied": ok,
                "world": world,
            },
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_ACTUATE_OP_FAILED)


async def actuate_joint_trajectory(
    model: str,
    points: list,
    world: str = "default",
) -> OperationResult:
    """Command a joint trajectory for a model.

    ``points`` is a list of ``{"positions": [...], "time_from_start": float}``
    dicts. No manifest range check is performed on trajectory waypoints (the
    contract validates only single ``actuate_joint`` pos commands).
    """
    try:
        b = get_bridge()
        ok = await b.command_joint_trajectory(model, points, world)
        return OperationResult(
            success=True,
            data={
                "model": model,
                "applied": ok,
                "num_points": len(points) if points else 0,
                "world": world,
            },
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_ACTUATE_OP_FAILED)
