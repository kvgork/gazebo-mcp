"""
Core actuation bounds — SAFETY-CRITICAL backstop (P5 hardening, Stream A).

These primitives are the deepest actuation-safety chokepoint. They are enforced
INSIDE ``GazeboBridgeNode`` (see ``bridge/gazebo_bridge_node.py``) BEFORE every
``self.adapter.*`` actuation call, so the mock / modern / classic backends, all
lean + legacy tools, and any direct bridge call are bounded identically. The
tool-layer checks (``tools/actuate.py`` JOINT_LIMIT_EXCEEDED / UNKNOWN_JOINT and
``tools/sensor.py`` image caps) STAY — these bounds are a deeper backstop, not a
replacement.

Two failure modes, selected by ``BoundsConfig.strict_bounds``:
  - ``False`` (default): CLAMP the command to the configured cap and proceed
    (scale a wrench vector to its magnitude cap preserving direction; clamp a
    scalar joint target into range). Return types stay ``bool``.
  - ``True``: RAISE :class:`ActuationBoundsExceeded` on any over-limit command.

The persistent-wrench registry caps how many simultaneous persistent wrenches
may be active (a runaway-actuation guard); the rate limiter caps per-entity
actuation frequency. Both are stateful; the rate limiter takes an injectable
clock so tests are deterministic.
"""

import math
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .exceptions import ActuationBoundsExceeded

Vector3 = Tuple[float, float, float]


@dataclass
class BoundsConfig:
    """Configured actuation caps + enforcement mode.

    Mirrors the 7 ``GAZEBO_*`` bounds fields on ``bridge.config.GazeboConfig``.
    Build one via :meth:`from_config` (tolerant of a ``None`` config or one that
    predates the bounds fields — every attribute falls back to the default).
    """

    max_force_n: float = 1000.0        # cap on |force| vector magnitude (N)
    max_torque_nm: float = 500.0       # cap on |torque| vector magnitude (N·m)
    max_joint_velocity: float = 10.0   # cap on |vel-mode value| (rad/s or m/s)
    max_joint_effort: float = 500.0    # cap on |force-mode value| (N·m or N)
    max_persistent_wrenches: int = 8   # max simultaneous persistent wrenches
    rate_limit_hz: float = 50.0        # per-entity actuation rate cap (Hz); <=0 disables
    strict_bounds: bool = False        # False => clamp; True => raise on any over-limit

    @classmethod
    def from_config(cls, cfg) -> "BoundsConfig":
        """Build a BoundsConfig from a ``GazeboConfig`` (or ``None`` -> defaults).

        Reads ``getattr(cfg, name, default)`` per field so a config object that
        predates the bounds fields (or any duck-typed stand-in) degrades safely
        to the defaults instead of raising.
        """
        if cfg is None:
            return cls()
        return cls(
            max_force_n=float(getattr(cfg, "max_force_n", cls.max_force_n)),
            max_torque_nm=float(getattr(cfg, "max_torque_nm", cls.max_torque_nm)),
            max_joint_velocity=float(
                getattr(cfg, "max_joint_velocity", cls.max_joint_velocity)
            ),
            max_joint_effort=float(
                getattr(cfg, "max_joint_effort", cls.max_joint_effort)
            ),
            max_persistent_wrenches=int(
                getattr(cfg, "max_persistent_wrenches", cls.max_persistent_wrenches)
            ),
            rate_limit_hz=float(getattr(cfg, "rate_limit_hz", cls.rate_limit_hz)),
            strict_bounds=bool(getattr(cfg, "strict_bounds", cls.strict_bounds)),
        )


def _magnitude(vec) -> float:
    """Euclidean magnitude of a 3-vector (tolerant of list/tuple input)."""
    return math.sqrt(sum(float(c) ** 2 for c in vec))


def _clamp_vector(vec, cap: float, label: str, strict: bool) -> Vector3:
    """Scale ``vec`` down to magnitude ``cap`` (preserving direction) if over.

    A negative ``cap`` disables the check. ``strict`` raises instead of clamping.
    A zero cap collapses any non-zero vector to the zero vector.
    """
    values = tuple(float(c) for c in vec)
    # NaN/inf has no finite magnitude to scale to; `nan <= cap` (and `inf <= cap`
    # for a finite cap) is False, so a non-finite command would otherwise slip
    # straight through non-strict clamping below and reach the adapter
    # unbounded. Reject ALWAYS (regardless of strict_bounds) — this is never a
    # valid, clampable command.
    if not all(math.isfinite(c) for c in values):
        raise ActuationBoundsExceeded(
            f"{label} contains a non-finite value: {values}",
            details={"kind": label, "vector": list(values)},
        )
    if cap is None or cap < 0:
        return values
    mag = _magnitude(values)
    if mag <= cap:
        return values
    if strict:
        raise ActuationBoundsExceeded(
            f"{label} magnitude {mag:.6g} exceeds cap {cap:.6g}",
            details={"kind": label, "magnitude": mag, "cap": cap, "vector": list(values)},
        )
    if mag == 0.0:  # unreachable when cap >= 0 (mag > cap >= 0 => mag > 0), kept defensive
        return values
    scale = cap / mag
    return (values[0] * scale, values[1] * scale, values[2] * scale)


def enforce_wrench(
    force,
    torque,
    duration: float,
    persistent: bool,
    cfg: BoundsConfig,
) -> Tuple[Vector3, Vector3]:
    """Bound a wrench to its configured magnitude caps.

    Scales the force vector to ``cfg.max_force_n`` and the torque vector to
    ``cfg.max_torque_nm`` (preserving direction). Returns the (possibly clamped)
    ``(force, torque)`` as float tuples. With ``cfg.strict_bounds`` True, raises
    :class:`ActuationBoundsExceeded` on any over-limit vector instead of clamping.

    ``duration`` / ``persistent`` are part of the frozen signature (accepted for
    context / future policy) but do not affect the magnitude clamp.
    """
    bounded_force = _clamp_vector(force, cfg.max_force_n, "force", cfg.strict_bounds)
    bounded_torque = _clamp_vector(
        torque, cfg.max_torque_nm, "torque", cfg.strict_bounds
    )
    return bounded_force, bounded_torque


def _clamp_scalar(value: float, cap: float, label: str, strict: bool) -> float:
    """Clamp ``value`` into ``[-cap, +cap]``. Negative cap disables the check."""
    v = float(value)
    # NaN/inf has no finite magnitude to compare/clamp against; `nan <= cap` is
    # False, so a non-finite command would otherwise slip through non-strict
    # clamping below and reach the adapter unbounded. Reject ALWAYS (regardless
    # of strict_bounds) — this is never a valid, clampable command.
    if not math.isfinite(v):
        raise ActuationBoundsExceeded(
            f"{label} value is non-finite: {v}",
            details={"kind": label, "value": v},
        )
    if cap is None or cap < 0 or abs(v) <= cap:
        return v
    if strict:
        raise ActuationBoundsExceeded(
            f"{label} value {v:.6g} exceeds cap ±{cap:.6g}",
            details={"kind": label, "value": v, "cap": cap},
        )
    return max(-cap, min(v, cap))


def enforce_joint(
    model: str,
    joint: str,
    mode: str,
    value: float,
    limits,
    cfg: BoundsConfig,
) -> float:
    """Bound a single joint command and return the (possibly clamped) value.

    - ``mode == "pos"``: clamp to ``limits == (lower, upper)`` when provided
      (``limits is None`` -> no positional clamp; the tool layer already enforces
      manifest limits and is the primary pos guard).
    - ``mode == "vel"``: clamp to ``[-max_joint_velocity, +max_joint_velocity]``.
    - ``mode in ("force", "effort")``: clamp to
      ``[-max_joint_effort, +max_joint_effort]``.
    - any other mode: passthrough (mode validation lives in the tool layer).

    With ``cfg.strict_bounds`` True, raises :class:`ActuationBoundsExceeded`
    instead of clamping.
    """
    v = float(value)
    if mode == "pos":
        if limits is None:
            return v
        lower, upper = float(limits[0]), float(limits[1])
        if lower <= v <= upper:
            return v
        if cfg.strict_bounds:
            raise ActuationBoundsExceeded(
                f"joint '{joint}' pos {v:.6g} outside limits [{lower:.6g}, {upper:.6g}]",
                details={
                    "kind": "joint_pos",
                    "model": model,
                    "joint": joint,
                    "value": v,
                    "lower": lower,
                    "upper": upper,
                },
            )
        return max(lower, min(v, upper))
    if mode == "vel":
        return _clamp_scalar(v, cfg.max_joint_velocity, f"joint '{joint}' vel", cfg.strict_bounds)
    if mode in ("force", "effort"):
        return _clamp_scalar(v, cfg.max_joint_effort, f"joint '{joint}' effort", cfg.strict_bounds)
    return v


class PersistentWrenchRegistry:
    """Cap on simultaneously-active persistent wrenches (runaway-actuation guard).

    Keyed by ``(entity, world)``. :meth:`register` is idempotent per key; adding
    a NEW key when ``max_active`` are already active raises
    :class:`ActuationBoundsExceeded` (the operator must :meth:`clear` one first).
    """

    def __init__(self, max_active: int):
        self._max = int(max_active)
        self._active: set = set()

    def register(self, entity: str, world: str) -> None:
        key = (entity, world)
        if key in self._active:
            return  # idempotent: re-registering an active persistent wrench is a no-op
        if len(self._active) >= self._max:
            raise ActuationBoundsExceeded(
                f"persistent-wrench cap reached ({self._max} active); "
                f"clear an existing persistent wrench before adding '{entity}'",
                details={
                    "kind": "persistent_wrench_cap",
                    "active": len(self._active),
                    "max": self._max,
                    "entity": entity,
                    "world": world,
                },
            )
        self._active.add(key)

    def clear(self, entity: str, world: str) -> None:
        self._active.discard((entity, world))  # no-op if absent

    def active(self) -> int:
        return len(self._active)


class RateLimiter:
    """Per-entity actuation rate cap. ``allow()`` throttles below ``1/hz``.

    The clock is injectable (``now_fn``) so tests are deterministic. ``hz <= 0``
    disables throttling (every call is allowed). The last-allowed timestamp is
    only advanced on an ALLOWED call, so a burst of throttled calls does not keep
    pushing the window forward.
    """

    def __init__(self, hz: float, now_fn: Callable[[], float] = time.monotonic):
        self._hz = float(hz)
        self._now = now_fn
        self._min_interval = (1.0 / self._hz) if self._hz > 0 else 0.0
        self._last: Dict[str, float] = {}

    def allow(self, entity: str) -> bool:
        if self._hz <= 0:
            return True
        now = self._now()
        last = self._last.get(entity)
        if last is not None and (now - last) < self._min_interval:
            return False
        self._last[entity] = now
        return True
