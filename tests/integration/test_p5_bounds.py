"""
P5 hardening — CORE ACTUATION BOUNDS (Stream A, SAFETY-CRITICAL).

Two layers of proof:

1. BRIDGE-LEVEL BACKSTOP (the point of P5): construct a ``GazeboBridgeNode``
   directly against a ``MockGazeboAdapter`` (NO ``build_app``, NO tool layer) and
   show the bounds fire INSIDE the bridge, before the ``self.adapter.*`` call:
     - over-limit force is clamped (non-strict) and RAISES under strict_bounds,
     - torque magnitude is capped,
     - joint pos/vel/force targets are clamped (and raise under strict),
     - the persistent-wrench cap is enforced and requires an explicit clear,
     - a same-entity flood is rate-throttled (proved with an INJECTED fake clock),
     - a bridge built with ``config=None`` is safe (defaults, still clamps).
   The read-back uses the mock adapter's ``get_recorded_wrench`` /
   ``get_joint_target`` helpers, so we observe the value that ACTUALLY reached the
   backend after enforcement.

2. PURE / STATEFUL PRIMITIVES: ``enforce_wrench`` / ``enforce_joint`` /
   ``PersistentWrenchRegistry`` / ``RateLimiter`` are also unit-tested directly.

Runs under ``-e dev`` (mock backend, no Gazebo/ROS2). The bridge is built with an
injected adapter, so no ROS graph and no ``GAZEBO_BACKEND`` env dance is needed.
"""

import math
import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.bridge.gazebo_bridge_node import GazeboBridgeNode
from gazebo_mcp.bridge.adapters.mock_adapter import MockGazeboAdapter
from gazebo_mcp.bridge.config import GazeboConfig, GazeboBackend
from gazebo_mcp.utils.actuation_bounds import (
    BoundsConfig,
    enforce_wrench,
    enforce_joint,
    enforce_trajectory,
    PersistentWrenchRegistry,
    RateLimiter,
)
from gazebo_mcp.utils.exceptions import ActuationBoundsExceeded, GazeboMCPError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**overrides) -> GazeboConfig:
    """A MOCK-backend GazeboConfig with rate limiting DISABLED by default.

    Rate limiting is off unless a test overrides ``rate_limit_hz`` so the clamp /
    registry / strict tests are not incidentally throttled; the dedicated rate
    tests inject their own fake-clock ``RateLimiter``.
    """
    params = dict(backend=GazeboBackend.MOCK, rate_limit_hz=0.0)
    params.update(overrides)
    return GazeboConfig(**params)


def _bridge(config: GazeboConfig | None = None) -> GazeboBridgeNode:
    """Bridge over a fresh MockGazeboAdapter. ``config`` drives the bounds."""
    return GazeboBridgeNode(None, config=config, adapter=MockGazeboAdapter())


def _mag(vec) -> float:
    return math.sqrt(sum(float(c) ** 2 for c in vec))


class _FakeClock:
    """A hand-cranked monotonic clock for deterministic rate-limit tests."""

    def __init__(self, start: float = 0.0):
        self.t = float(start)

    def __call__(self) -> float:
        return self.t


# ===========================================================================
# UNIT: pure / stateful primitives
# ===========================================================================

def test_bounds_config_from_none_is_defaults():
    b = BoundsConfig.from_config(None)
    assert b.max_force_n == 1000.0
    assert b.max_torque_nm == 500.0
    assert b.max_joint_velocity == 10.0
    assert b.max_joint_effort == 500.0
    assert b.max_persistent_wrenches == 8
    assert b.rate_limit_hz == 50.0
    assert b.strict_bounds is False


def test_bounds_config_from_gazebo_config_reads_fields():
    cfg = _cfg(max_force_n=42.0, strict_bounds=True, max_persistent_wrenches=3)
    b = BoundsConfig.from_config(cfg)
    assert b.max_force_n == 42.0
    assert b.strict_bounds is True
    assert b.max_persistent_wrenches == 3


def test_enforce_wrench_clamps_force_preserving_direction():
    b = BoundsConfig()  # defaults: max_force_n=1000
    force, torque = enforce_wrench((3000.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, False, b)
    assert force == pytest.approx((1000.0, 0.0, 0.0))
    assert torque == pytest.approx((0.0, 0.0, 0.0))

    # Diagonal vector: magnitude scaled to the cap, DIRECTION preserved.
    force, _ = enforce_wrench((1000.0, 1000.0, 1000.0), (0, 0, 0), 0.0, False, b)
    assert _mag(force) == pytest.approx(1000.0)
    assert force[0] == pytest.approx(force[1]) == pytest.approx(force[2])


def test_enforce_wrench_caps_torque_magnitude():
    b = BoundsConfig()  # max_torque_nm=500
    _, torque = enforce_wrench((0, 0, 0), (0.0, 0.0, 5000.0), 0.0, False, b)
    assert torque == pytest.approx((0.0, 0.0, 500.0))


def test_enforce_wrench_within_cap_is_unchanged():
    b = BoundsConfig()
    force, torque = enforce_wrench((10.0, 0.0, 0.0), (1.0, 2.0, 3.0), 0.0, False, b)
    assert force == pytest.approx((10.0, 0.0, 0.0))
    assert torque == pytest.approx((1.0, 2.0, 3.0))


def test_enforce_wrench_strict_raises_on_overlimit():
    b = BoundsConfig(strict_bounds=True)
    with pytest.raises(ActuationBoundsExceeded) as ei:
        enforce_wrench((5000.0, 0.0, 0.0), (0, 0, 0), 0.0, False, b)
    assert ei.value.error_code == "ACTUATION_BOUNDS_EXCEEDED"
    assert isinstance(ei.value, GazeboMCPError)


def test_enforce_joint_pos_clamps_to_limits():
    b = BoundsConfig()
    assert enforce_joint("m", "j", "pos", 2.0, (-1.0, 1.0), b) == pytest.approx(1.0)
    assert enforce_joint("m", "j", "pos", -2.0, (-1.0, 1.0), b) == pytest.approx(-1.0)
    assert enforce_joint("m", "j", "pos", 0.5, (-1.0, 1.0), b) == pytest.approx(0.5)
    # limits is None => no positional clamp (tool layer is the primary pos guard).
    assert enforce_joint("m", "j", "pos", 9999.0, None, b) == pytest.approx(9999.0)


def test_enforce_joint_vel_and_effort_clamp():
    b = BoundsConfig()  # vel cap 10, effort cap 500
    assert enforce_joint("m", "j", "vel", 100.0, None, b) == pytest.approx(10.0)
    assert enforce_joint("m", "j", "vel", -100.0, None, b) == pytest.approx(-10.0)
    assert enforce_joint("m", "j", "force", 10000.0, None, b) == pytest.approx(500.0)
    # "effort" is treated identically to "force".
    assert enforce_joint("m", "j", "effort", -10000.0, None, b) == pytest.approx(-500.0)


def test_enforce_joint_strict_raises():
    b = BoundsConfig(strict_bounds=True)
    with pytest.raises(ActuationBoundsExceeded):
        enforce_joint("m", "j", "vel", 100.0, None, b)
    with pytest.raises(ActuationBoundsExceeded):
        enforce_joint("m", "j", "pos", 2.0, (-1.0, 1.0), b)


# --- enforce_trajectory (P5-deferred #1) ---

def test_enforce_trajectory_no_limits_passthrough_finite():
    """limits=None -> positions returned unchanged (only non-finite is rejected)."""
    b = BoundsConfig()
    points = [
        {"positions": [0.0, 99.0], "time_from_start": 0.0},
        {"positions": [-50.0, 5.0], "time_from_start": 1.0},
    ]
    out = enforce_trajectory("m", points, None, b)
    assert [p["positions"] for p in out] == [[0.0, 99.0], [-50.0, 5.0]]
    # time_from_start (and any other key) preserved verbatim.
    assert out[1]["time_from_start"] == 1.0


def test_enforce_trajectory_clamps_per_joint_nonstrict():
    """Each finite position is clamped to its aligned (lower,upper); None => no clamp."""
    b = BoundsConfig()  # non-strict
    limits = [(-1.0, 1.0), None, (0.0, 0.02)]
    points = [{"positions": [2.0, 12345.0, -0.5]}]
    out = enforce_trajectory("m", points, limits, b)
    assert out[0]["positions"] == pytest.approx([1.0, 12345.0, 0.0])


def test_enforce_trajectory_does_not_mutate_input():
    """The input points list + dicts are not mutated (a new list is returned)."""
    b = BoundsConfig()
    points = [{"positions": [2.0], "time_from_start": 0.5}]
    out = enforce_trajectory("m", points, [(-1.0, 1.0)], b)
    assert points[0]["positions"] == [2.0]      # original untouched
    assert out[0]["positions"] == pytest.approx([1.0])
    assert out is not points


def test_enforce_trajectory_strict_raises_on_overlimit():
    b = BoundsConfig(strict_bounds=True)
    with pytest.raises(ActuationBoundsExceeded):
        enforce_trajectory("m", [{"positions": [2.0]}], [(-1.0, 1.0)], b, joint_names=["j"])


def test_enforce_trajectory_nonfinite_raises_regardless_of_strict():
    """NaN/inf positions raise in BOTH modes, with or without limits."""
    for strict in (False, True):
        b = BoundsConfig(strict_bounds=strict)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_trajectory("m", [{"positions": [float("nan")]}], None, b)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_trajectory("m", [{"positions": [float("inf")]}], [(-1.0, 1.0)], b)


def test_enforce_trajectory_ragged_limits_only_clamp_covered_indices():
    """A positions row longer than limits leaves the uncovered indices unclamped."""
    b = BoundsConfig()
    out = enforce_trajectory("m", [{"positions": [5.0, 5.0]}], [(-1.0, 1.0)], b)
    assert out[0]["positions"] == pytest.approx([1.0, 5.0])


def test_persistent_wrench_registry_cap_and_clear():
    reg = PersistentWrenchRegistry(2)
    reg.register("e1", "default")
    reg.register("e2", "default")
    assert reg.active() == 2

    # A NEW key beyond the cap raises.
    with pytest.raises(ActuationBoundsExceeded):
        reg.register("e3", "default")

    # Re-registering an EXISTING key is idempotent (no raise, no growth).
    reg.register("e2", "default")
    assert reg.active() == 2

    # Same entity in a DIFFERENT world is a distinct key -> still over cap.
    with pytest.raises(ActuationBoundsExceeded):
        reg.register("e1", "other")

    # Clearing frees a slot so a new key fits.
    reg.clear("e1", "default")
    assert reg.active() == 1
    reg.register("e3", "default")
    assert reg.active() == 2

    reg.clear("absent", "default")  # no-op, no raise
    assert reg.active() == 2


def test_rate_limiter_throttles_with_injected_clock():
    clk = _FakeClock()
    rl = RateLimiter(10.0, now_fn=clk)  # min interval 0.1s

    assert rl.allow("a") is True    # first call always allowed
    assert rl.allow("a") is False   # same instant -> throttled
    clk.t = 0.099
    assert rl.allow("a") is False   # still inside the window
    clk.t = 0.1
    assert rl.allow("a") is True    # window elapsed
    # Distinct entities are independent.
    assert rl.allow("b") is True


def test_rate_limiter_disabled_when_hz_non_positive():
    clk = _FakeClock()
    rl = RateLimiter(0.0, now_fn=clk)
    for _ in range(5):
        assert rl.allow("a") is True
    rl_neg = RateLimiter(-1.0, now_fn=clk)
    assert rl_neg.allow("a") is True


# ===========================================================================
# INTEGRATION: bounds enforced INSIDE the bridge (before the adapter call)
# ===========================================================================

def test_bridge_wrench_topic_clamps_force_and_torque_nonstrict():
    """Over-limit force/torque reach the adapter CLAMPED (non-strict default)."""

    async def _run():
        bridge = _bridge(_cfg())  # strict_bounds False, rate limiting off
        # Force well over the 1000 N cap -> clamped magnitude 1000, +x direction.
        assert await bridge.apply_wrench_topic("cube_f", force=(5000.0, 0.0, 0.0)) is True
        rec_f = await bridge.adapter.get_recorded_wrench("cube_f")
        assert _mag(rec_f["force"]) == pytest.approx(1000.0)
        assert rec_f["force"][0] == pytest.approx(1000.0)

        # Torque over the 500 N·m cap -> clamped to 500 on z.
        assert await bridge.apply_wrench_topic("cube_t", torque=(0.0, 0.0, 5000.0)) is True
        rec_t = await bridge.adapter.get_recorded_wrench("cube_t")
        assert _mag(rec_t["torque"]) == pytest.approx(500.0)
        assert rec_t["torque"][2] == pytest.approx(500.0)

    anyio.run(_run)


def test_bridge_wrench_topic_strict_raises():
    """With strict_bounds an over-limit wrench raises before touching the adapter."""

    async def _run():
        bridge = _bridge(_cfg(strict_bounds=True))
        with pytest.raises(ActuationBoundsExceeded):
            await bridge.apply_wrench_topic("cube", force=(5000.0, 0.0, 0.0))
        # Nothing was recorded on the backend (the raise came first).
        assert await bridge.adapter.get_recorded_wrench("cube") is None

    anyio.run(_run)


def test_bridge_legacy_apply_wrench_clamps_and_strict_raises():
    """The LEGACY sync apply_wrench path enforces bounds too.

    The MockGazeboAdapter has no legacy ``apply_wrench``; attach a recorder so we
    can observe the CLAMPED force that reaches the adapter. The strict path raises
    synchronously (enforcement is before the try/except that returns False).
    """
    # Non-strict clamp path (config=None => default bounds).
    adapter = MockGazeboAdapter()
    recorded: dict = {}

    async def _legacy_apply(name, force, torque, duration, world):
        recorded["force"] = tuple(force)
        recorded["torque"] = tuple(torque)
        return True

    adapter.apply_wrench = _legacy_apply  # type: ignore[attr-defined]
    bridge = GazeboBridgeNode(None, adapter=adapter)  # config None -> defaults
    assert bridge.apply_wrench("robot", force=(5000.0, 0.0, 0.0)) is True
    assert _mag(recorded["force"]) == pytest.approx(1000.0)

    # Strict path raises (NOT swallowed into a False return).
    strict_bridge = _bridge(_cfg(strict_bounds=True))
    with pytest.raises(ActuationBoundsExceeded):
        strict_bridge.apply_wrench("robot", force=(5000.0, 0.0, 0.0))


def test_bridge_command_joint_clamps_pos_vel_force():
    """Joint pos/vel/force targets reach the adapter clamped (non-strict)."""

    async def _run():
        bridge = _bridge(_cfg())
        # vel over the 10 cap -> 10
        assert await bridge.command_joint("m", "jv", "vel", 100.0) is True
        assert (await bridge.adapter.get_joint_target("m", "jv"))["value"] == pytest.approx(10.0)

        # force over the 500 cap -> 500
        assert await bridge.command_joint("m", "jf", "force", 10000.0) is True
        assert (await bridge.adapter.get_joint_target("m", "jf"))["value"] == pytest.approx(500.0)

        # pos with explicit limits -> clamped into range
        assert await bridge.command_joint("m", "jp", "pos", 2.0, limits=(-1.0, 1.0)) is True
        assert (await bridge.adapter.get_joint_target("m", "jp"))["value"] == pytest.approx(1.0)

    anyio.run(_run)


def test_bridge_command_joint_strict_raises():
    async def _run():
        bridge = _bridge(_cfg(strict_bounds=True))
        with pytest.raises(ActuationBoundsExceeded):
            await bridge.command_joint("m", "jv", "vel", 100.0)
        assert await bridge.adapter.get_joint_target("m", "jv") is None

    anyio.run(_run)


def test_bridge_command_joint_trajectory_clamps_with_limits_nonstrict():
    """A direct-bridge trajectory with per-position limits reaches the adapter
    CLAMPED (non-strict). The mock stores the last point under ``_trajectory``."""

    async def _run():
        bridge = _bridge(_cfg())  # non-strict, rate limiting off
        points = [{"positions": [2.0, -5.0], "time_from_start": 1.0}]
        assert await bridge.command_joint_trajectory(
            "m", points, limits=[(-1.0, 1.0), (-1.0, 1.0)]
        ) is True
        stored = await bridge.adapter.get_joint_target("m", "_trajectory")
        assert stored["positions"] == pytest.approx([1.0, -1.0])
        assert stored["time_from_start"] == 1.0
        # Caller's input list is not mutated by the clamp.
        assert points[0]["positions"] == [2.0, -5.0]

    anyio.run(_run)


def test_bridge_command_joint_trajectory_strict_raises_on_overlimit():
    """strict_bounds -> an over-limit waypoint raises before touching the adapter."""

    async def _run():
        bridge = _bridge(_cfg(strict_bounds=True))
        with pytest.raises(ActuationBoundsExceeded):
            await bridge.command_joint_trajectory(
                "m", [{"positions": [2.0]}], limits=[(-1.0, 1.0)]
            )
        assert await bridge.adapter.get_joint_target("m", "_trajectory") is None

    anyio.run(_run)


def test_bridge_command_joint_trajectory_nonfinite_raises_without_limits():
    """A non-finite waypoint raises even with limits=None (the always-on guard)."""

    async def _run():
        for strict in (False, True):
            bridge = _bridge(_cfg(strict_bounds=strict))
            with pytest.raises(ActuationBoundsExceeded):
                await bridge.command_joint_trajectory(
                    "m", [{"positions": [float("inf")]}]
                )
            assert await bridge.adapter.get_joint_target("m", "_trajectory") is None

    anyio.run(_run)


def test_bridge_command_joint_trajectory_forwards_joint_names():
    """Review finding A regression: the bridge forwards joint_names to the adapter
    so the real controller gets the position->joint mapping. The mock records it."""

    async def _run():
        bridge = _bridge(_cfg())
        assert await bridge.command_joint_trajectory(
            "m",
            [{"positions": [0.5, -0.5], "time_from_start": 1.0}],
            joint_names=["j0", "j1"],
        ) is True
        forwarded = await bridge.adapter.get_joint_target(
            "m", "_trajectory_joint_names"
        )
        assert forwarded == ["j0", "j1"]

    anyio.run(_run)


def test_bridge_persistent_wrench_cap_enforced_requires_clear():
    """The persistent-wrench cap is a bridge backstop; clear frees a slot."""

    async def _run():
        bridge = _bridge(_cfg(max_persistent_wrenches=2))
        assert await bridge.apply_wrench_topic("e1", force=(1.0, 0, 0), persistent=True) is True
        assert await bridge.apply_wrench_topic("e2", force=(1.0, 0, 0), persistent=True) is True
        assert bridge._wrench_registry.active() == 2

        # Third distinct persistent wrench exceeds the cap -> raise.
        with pytest.raises(ActuationBoundsExceeded):
            await bridge.apply_wrench_topic("e3", force=(1.0, 0, 0), persistent=True)

        # Non-persistent wrenches are NOT capped.
        assert await bridge.apply_wrench_topic("e4", force=(1.0, 0, 0), persistent=False) is True
        assert bridge._wrench_registry.active() == 2

        # Clear one, then the third persistent wrench fits.
        assert await bridge.clear_wrench("e1") is True
        assert bridge._wrench_registry.active() == 1
        assert await bridge.apply_wrench_topic("e3", force=(1.0, 0, 0), persistent=True) is True
        assert bridge._wrench_registry.active() == 2

    anyio.run(_run)


def test_bridge_rate_flood_throttled_with_fake_clock():
    """A same-entity wrench flood is throttled by the bridge's rate limiter."""

    async def _run():
        bridge = _bridge(GazeboConfig(backend=GazeboBackend.MOCK))  # default 50 Hz
        clk = _FakeClock()
        # Inject a deterministic clock so throttling does not depend on wall time.
        bridge._rate_limiter = RateLimiter(50.0, now_fn=clk)  # 0.02s min interval

        assert await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0)) is True   # t=0
        assert await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0)) is False  # throttled
        clk.t = 0.019
        assert await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0)) is False  # still inside window
        clk.t = 0.02
        assert await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0)) is True   # window elapsed
        # A different entity is independent -> allowed immediately.
        assert await bridge.apply_wrench_topic("other", force=(1.0, 0, 0)) is True

    anyio.run(_run)


def test_bridge_rate_flood_strict_raises():
    async def _run():
        bridge = _bridge(_cfg(strict_bounds=True))
        clk = _FakeClock()
        bridge._rate_limiter = RateLimiter(50.0, now_fn=clk)
        assert await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0)) is True
        with pytest.raises(ActuationBoundsExceeded):
            await bridge.apply_wrench_topic("cube", force=(1.0, 0, 0))

    anyio.run(_run)


def test_bridge_none_config_is_safe_and_still_clamps():
    """A bridge built with config=None uses defaults and still enforces bounds."""

    async def _run():
        bridge = GazeboBridgeNode(None, adapter=MockGazeboAdapter())  # config None
        assert bridge.config is None
        assert bridge._bounds.max_force_n == 1000.0  # defaults applied

        assert await bridge.apply_wrench_topic("cube", force=(5000.0, 0.0, 0.0)) is True
        rec = await bridge.adapter.get_recorded_wrench("cube")
        assert _mag(rec["force"]) == pytest.approx(1000.0)

    anyio.run(_run)


# ===========================================================================
# FIX-F1: non-finite (NaN/inf) actuation bypasses the clamp — must ALWAYS raise
# regardless of strict_bounds. A NaN/inf command has no finite magnitude to
# scale to (`nan <= cap` is False), so non-strict clamping would otherwise let
# it slip through to the adapter completely unbounded.
# ===========================================================================

def test_enforce_wrench_nan_inf_raises_regardless_of_strict():
    for strict in (False, True):
        b = BoundsConfig(strict_bounds=strict)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_wrench((float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, False, b)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_wrench((float("inf"), 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, False, b)
        # A non-finite TORQUE component is caught the same way.
        with pytest.raises(ActuationBoundsExceeded):
            enforce_wrench((0.0, 0.0, 0.0), (0.0, 0.0, float("nan")), 0.0, False, b)


def test_enforce_joint_nan_inf_raises_regardless_of_strict():
    for strict in (False, True):
        b = BoundsConfig(strict_bounds=strict)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_joint("m", "j", "vel", float("nan"), None, b)
        with pytest.raises(ActuationBoundsExceeded):
            enforce_joint("m", "j", "force", float("inf"), None, b)


def test_bridge_apply_wrench_topic_nan_inf_raises_in_both_modes():
    """The bridge backstop rejects a NaN/inf wrench BEFORE the adapter is
    touched, in BOTH clamp (non-strict) and strict mode — nothing is recorded.
    """

    async def _run():
        for strict in (False, True):
            bridge = _bridge(_cfg(strict_bounds=strict))
            with pytest.raises(ActuationBoundsExceeded):
                await bridge.apply_wrench_topic("cube_nan", force=(float("nan"), 0.0, 0.0))
            with pytest.raises(ActuationBoundsExceeded):
                await bridge.apply_wrench_topic("cube_inf", force=(float("inf"), 0.0, 0.0))
            assert await bridge.adapter.get_recorded_wrench("cube_nan") is None
            assert await bridge.adapter.get_recorded_wrench("cube_inf") is None

    anyio.run(_run)


# ===========================================================================
# Error-code surfacing through the TOOL layer: ActuationBoundsExceeded must
# surface as error_code == ACTUATION_BOUNDS_EXCEEDED, NOT the generic
# ACTUATE_OP_FAILED, for both a strict-mode over-limit wrench and the
# always-on persistent-wrench cap.
# ===========================================================================

@pytest.fixture
def _mock_bridge_singleton(monkeypatch):
    """Force the MOCK backend + reset the bridge-helper singleton so the tool
    layer's ``get_bridge()`` constructs a FRESH bridge from the current env
    (mirrors ``test_p1_actuation.py``'s ``_force_mock_backend`` fixture).
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


def test_actuate_wrench_tool_surfaces_bounds_error_code(monkeypatch, _mock_bridge_singleton):
    """An over-limit force through the ``actuate_wrench`` TOOL (strict mode)
    surfaces ``ACTUATION_BOUNDS_EXCEEDED``, not ``ACTUATE_OP_FAILED``.
    """
    monkeypatch.setenv("GAZEBO_STRICT_BOUNDS", "1")
    monkeypatch.setenv("GAZEBO_MAX_FORCE_N", "10")

    from gazebo_mcp.tools import actuate as _actuate

    async def _run():
        result = await _actuate.actuate_wrench("cube", fx=5000.0)
        assert result.success is False
        assert result.error_code == "ACTUATION_BOUNDS_EXCEEDED"

    anyio.run(_run)


def test_actuate_wrench_tool_surfaces_persistent_cap_error_code(monkeypatch, _mock_bridge_singleton):
    """The persistent-wrench cap (always-on, independent of strict_bounds)
    surfaces the same ``ACTUATION_BOUNDS_EXCEEDED`` error_code via the tool.
    """
    monkeypatch.setenv("GAZEBO_MAX_PERSISTENT_WRENCHES", "1")

    from gazebo_mcp.tools import actuate as _actuate

    async def _run():
        first = await _actuate.actuate_wrench("e1", fx=1.0, persistent=True)
        assert first.success is True

        second = await _actuate.actuate_wrench("e2", fx=1.0, persistent=True)
        assert second.success is False
        assert second.error_code == "ACTUATION_BOUNDS_EXCEEDED"

    anyio.run(_run)


# ===========================================================================
# FIX-F3: delete_entity frees any persistent-wrench registry slot it held.
# ===========================================================================

def test_delete_entity_frees_persistent_wrench_slot():
    """Repeating spawn + persistent-wrench + delete more than
    ``max_persistent_wrenches`` times never exhausts the cap: each successful
    delete frees the slot, and a fresh persistent wrench keeps succeeding.
    """

    async def _run():
        bridge = _bridge(_cfg(max_persistent_wrenches=2))
        for i in range(5):  # > max_persistent_wrenches
            name = f"e{i}"
            assert bridge.spawn_entity(name, "<sdf/>") is True
            assert (
                await bridge.apply_wrench_topic(name, force=(1.0, 0, 0), persistent=True)
                is True
            )
            assert bridge._wrench_registry.active() == 1
            assert bridge.delete_entity(name) is True
            assert bridge._wrench_registry.active() == 0

        # A fresh persistent wrench still succeeds (slot not leaked).
        assert bridge.spawn_entity("final", "<sdf/>") is True
        assert (
            await bridge.apply_wrench_topic("final", force=(1.0, 0, 0), persistent=True)
            is True
        )
        assert bridge._wrench_registry.active() == 1

    anyio.run(_run)


def test_delete_entity_failure_keeps_the_slot():
    """A FAILED delete (entity does not exist) must NOT clear a slot it does
    not own — the registry key is independent of the (nonexistent) entity.
    """

    async def _run():
        bridge = _bridge(_cfg(max_persistent_wrenches=1))
        assert (
            await bridge.apply_wrench_topic("e1", force=(1.0, 0, 0), persistent=True)
            is True
        )
        assert bridge._wrench_registry.active() == 1

        from gazebo_mcp.utils.exceptions import ModelDeleteError

        with pytest.raises(ModelDeleteError):
            bridge.delete_entity("never_spawned")
        # e1's slot is untouched by the unrelated failed delete.
        assert bridge._wrench_registry.active() == 1

    anyio.run(_run)


# ===========================================================================
# FIX-F4: persistent-wrench slot is rolled back if the adapter call fails
# (returns False) or raises — otherwise a failed attempt leaks the slot
# forever (clear_wrench has nothing to clear on the backend).
# ===========================================================================

def test_apply_wrench_topic_rolls_back_slot_on_adapter_false():
    async def _run():
        adapter = MockGazeboAdapter()
        original = adapter.apply_wrench_topic

        async def _failing(*args, **kwargs):
            return False

        adapter.apply_wrench_topic = _failing  # type: ignore[method-assign]
        bridge = GazeboBridgeNode(
            None, config=_cfg(max_persistent_wrenches=1), adapter=adapter
        )

        for _ in range(3):
            assert (
                await bridge.apply_wrench_topic("e", force=(1.0, 0, 0), persistent=True)
                is False
            )
            assert bridge._wrench_registry.active() == 0

        # Restore normal adapter behaviour -> a persistent wrench now succeeds.
        adapter.apply_wrench_topic = original
        assert (
            await bridge.apply_wrench_topic("e", force=(1.0, 0, 0), persistent=True)
            is True
        )
        assert bridge._wrench_registry.active() == 1

    anyio.run(_run)


def test_apply_wrench_topic_rolls_back_slot_on_adapter_exception():
    async def _run():
        adapter = MockGazeboAdapter()

        async def _raising(*args, **kwargs):
            raise RuntimeError("boom")

        adapter.apply_wrench_topic = _raising  # type: ignore[method-assign]
        bridge = GazeboBridgeNode(
            None, config=_cfg(max_persistent_wrenches=1), adapter=adapter
        )

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await bridge.apply_wrench_topic("e", force=(1.0, 0, 0), persistent=True)
            assert bridge._wrench_registry.active() == 0

        # A subsequent successful persistent wrench (fresh adapter) still works.
        bridge2 = GazeboBridgeNode(
            None, config=_cfg(max_persistent_wrenches=1), adapter=MockGazeboAdapter()
        )
        assert (
            await bridge2.apply_wrench_topic("e", force=(1.0, 0, 0), persistent=True)
            is True
        )
        assert bridge2._wrench_registry.active() == 1

    anyio.run(_run)
