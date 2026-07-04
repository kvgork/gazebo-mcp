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

Manifest resolution (first hit wins):
  1. ``GazeboConfig.from_environment().model_manifest`` env override, if set.
  2. PACKAGE DATA ``gazebo_mcp/data/jetank_manifest.json`` resolved via
     ``importlib.resources`` — wheel-safe, works when installed into
     site-packages where the repo ``models/`` dir is absent.
  3. The in-repo human-facing asset ``<repo>/models/jetank/manifest.json``
     resolved from this file's location (``Path(__file__).resolve().parents[3]``)
     as a fallback for editable / source checkouts.
The loaded manifest is cached at module level keyed by source path;
``_reset_manifest_cache()`` clears it (used by tests).
"""

import json
from importlib.resources import files as _resource_files
from pathlib import Path

from gazebo_mcp.bridge.config import GazeboConfig
from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.exceptions import ActuationBoundsExceeded
from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("actuate_tools")

_ACTUATE_OP_FAILED = "ACTUATE_OP_FAILED"

# Repo root is three levels up from this file:
#   <repo>/src/gazebo_mcp/tools/actuate.py -> parents[3] == <repo>
# This path resolves OUTSIDE site-packages when the package is installed as a
# wheel, so it is only a SOURCE-CHECKOUT fallback — the wheel-safe path is the
# package-data manifest resolved via importlib.resources (see _manifest_path).
_REPO_MANIFEST = Path(__file__).resolve().parents[3] / "models" / "jetank" / "manifest.json"

# Module-level cache: maps the resolved manifest path -> parsed dict. Caching by
# path (rather than a bare bool) keeps the cache correct if the configured path
# changes between calls (e.g. across tests that set GAZEBO_MODEL_MANIFEST).
_manifest_cache: dict[str, dict] = {}


def _packaged_manifest_path() -> Path | None:
    """Return the wheel-safe package-data manifest path, or None if absent.

    Uses ``importlib.resources.files`` so it resolves correctly whether the
    package is an editable source checkout OR installed into site-packages as a
    wheel (where the repo ``models/`` dir does not ship). Non-throwing: any
    lookup error yields None so we fall through to the repo asset.
    """
    try:
        res = _resource_files("gazebo_mcp").joinpath("data/jetank_manifest.json")
        path = Path(str(res))
        return path if path.is_file() else None
    except Exception:  # noqa: BLE001 — degrade to the repo-asset fallback
        return None


def _manifest_path() -> Path:
    """Resolve the manifest path (first hit wins): env override -> package data
    -> in-repo asset.

    The env override always wins so operators can point at a custom manifest.
    Otherwise the wheel-safe package-data copy is preferred, falling back to the
    human-facing repo asset for source checkouts that have not shipped data/.
    """
    configured = GazeboConfig.from_environment().model_manifest
    if configured:
        return Path(configured)
    packaged = _packaged_manifest_path()
    if packaged is not None:
        return packaged
    return _REPO_MANIFEST


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
    except ActuationBoundsExceeded as e:
        # Surface the specific safety-bound error_code (strict-mode over-limit, or
        # the always-on persistent-wrench cap) instead of the generic
        # ACTUATE_OP_FAILED, so clients can distinguish a bounds rejection.
        return OperationResult(success=False, error=str(e), error_code=e.error_code)
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
    except ActuationBoundsExceeded as e:
        # Surface the specific safety-bound error_code (strict-mode over-limit, or
        # the always-on persistent-wrench cap) instead of the generic
        # ACTUATE_OP_FAILED, so clients can distinguish a bounds rejection.
        return OperationResult(success=False, error=str(e), error_code=e.error_code)
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
      - mode not in {pos,vel,force}    -> INVALID_MODE
      - unknown (model, joint)         -> UNKNOWN_JOINT
      - mode=="pos" and value out of   -> JOINT_LIMIT_EXCEEDED
        the joint's [lower, upper]
    """
    try:
        # Mode validation BEFORE any bridge call. The verified mock path accepts
        # any mode string, so validate here (the deferred modern adapter also
        # rejects unknown modes, but that path is not exercised under -e dev).
        if mode not in ("pos", "vel", "force"):
            return OperationResult(
                success=False,
                error=f"invalid mode '{mode}' (expected pos|vel|force)",
                error_code="INVALID_MODE",
                suggestions=["Use one of: pos, vel, force"],
            )

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
    except ActuationBoundsExceeded as e:
        # Surface the specific safety-bound error_code (strict-mode over-limit, or
        # the always-on persistent-wrench cap) instead of the generic
        # ACTUATE_OP_FAILED, so clients can distinguish a bounds rejection.
        return OperationResult(success=False, error=str(e), error_code=e.error_code)
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
    contract validates only single ``actuate_joint`` pos commands), but the
    SHAPE of ``points`` is validated before the bridge is touched:
      - non-empty list ...........................-> else INVALID_TRAJECTORY
      - each element a dict with a list ``positions`` -> else INVALID_TRAJECTORY
    """
    try:
        # Trajectory-shape validation BEFORE any bridge call. The mock path would
        # otherwise silently accept malformed input (e.g. None, a bare string, or
        # dicts missing ``positions``) and store garbage.
        if not isinstance(points, list) or not points:
            return OperationResult(
                success=False,
                error="points must be a non-empty list of trajectory waypoints",
                error_code="INVALID_TRAJECTORY",
                suggestions=[
                    'Pass e.g. [{"positions": [0.0, 0.5], "time_from_start": 1.0}]',
                ],
            )
        for idx, p in enumerate(points):
            if not isinstance(p, dict) or not isinstance(p.get("positions"), list):
                return OperationResult(
                    success=False,
                    error=(
                        f"trajectory point {idx} must be a dict with a list "
                        f"'positions'"
                    ),
                    error_code="INVALID_TRAJECTORY",
                    suggestions=[
                        'Each point must look like {"positions": [...], '
                        '"time_from_start": float}',
                    ],
                )

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
    except ActuationBoundsExceeded as e:
        # Surface the specific safety-bound error_code (strict-mode over-limit, or
        # the always-on persistent-wrench cap) instead of the generic
        # ACTUATE_OP_FAILED, so clients can distinguish a bounds rejection.
        return OperationResult(success=False, error=str(e), error_code=e.error_code)
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_ACTUATE_OP_FAILED)
