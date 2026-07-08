"""
Focused unit tests for the lean P1 actuation tools.

These exercise the framework-agnostic async functions in
``gazebo_mcp.tools.actuate`` DIRECTLY (not via the FastMCP transport), asserting
the ``OperationResult`` they return and the resulting MOCK-backend state read
back via the mock adapter's helpers (``get_recorded_wrench`` /
``get_joint_target``). The adapter instance is reached from the bridge singleton
as ``get_bridge().adapter``.

Backend selection caveat (authoritative): pixi ``[activation.env]`` sets
``GAZEBO_BACKEND=modern`` which OVERRIDES a shell ``GAZEBO_BACKEND=mock``. We
force mock IN-PROCESS via ``monkeypatch.setenv`` in an autouse fixture (set
before every tool call, auto-reverted afterwards, never leaking into other test
modules that rely on the default ``modern`` backend) and reset the bridge-helper
singleton per-test so each test runs against a fresh empty mock world.
``GazeboConfig.from_environment()`` reads ``GAZEBO_BACKEND`` lazily at
``get_bridge()`` call time, so per-test env setting is sufficient.
"""

import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import actuate as actuate_tools
from gazebo_mcp.tools import scene as scene_tools
from gazebo_mcp.tools import world as world_tools
from gazebo_mcp.tools._bridge_helper import get_bridge

CUBE_SDF = "<sdf version='1.7'/>"


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` per test and
    auto-reverts, so it never leaks into other test modules. Clearing the cached
    bridge node before/after each test guarantees a fresh empty mock world. We
    also clear the actuate manifest cache so joint-limit lookups are independent
    of any path a prior test configured.
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    actuate_tools._reset_manifest_cache()
    yield
    bh._bridge_node = None
    bh._connection_manager = None
    actuate_tools._reset_manifest_cache()


def _adapter():
    """The MockGazeboAdapter instance backing the singleton bridge node."""
    return get_bridge().adapter


# --------------------------------------------------------------------------
# actuate_wrench
# --------------------------------------------------------------------------


def test_actuate_wrench_recorded_then_read_back():
    """actuate_wrench records the wrench; the mock adapter reads it back."""

    async def _run():
        result = await actuate_tools.actuate_wrench(entity="cube", fx=10.0)
        assert result.success is True
        assert result.data["force"] == [10.0, 0.0, 0.0]
        assert result.data["persistent"] is False

        recorded = await _adapter().get_recorded_wrench("cube")
        assert recorded is not None
        assert recorded["force"] == [10.0, 0.0, 0.0]
        assert recorded["persistent"] is False

    anyio.run(_run)


def test_actuate_wrench_non_persistent_cleared_after_step():
    """A non-persistent wrench is one-shot: cleared after a single world_step."""

    async def _run():
        await scene_tools.scene_spawn(name="cube", sdf=CUBE_SDF, x=0.0, y=0.0, z=0.0)
        await actuate_tools.actuate_wrench(entity="cube", fx=10.0, persistent=False)

        # Pre-step: wrench recorded.
        assert await _adapter().get_recorded_wrench("cube") is not None

        stepped = await world_tools.world_step(steps=100)
        assert stepped.success is True

        # The one-shot wrench is gone, and the cube moved x by 0.05.
        assert await _adapter().get_recorded_wrench("cube") is None
        state = await scene_tools.scene_get_state(name="cube")
        assert state.data["pose"]["position"][0] == pytest.approx(0.05)

    anyio.run(_run)


def test_actuate_wrench_persistent_reintegrates_each_step():
    """A persistent wrench survives stepping and re-integrates (monotonic + ~2x)."""

    async def _run():
        await scene_tools.scene_spawn(name="cube", sdf=CUBE_SDF, x=0.0, y=0.0, z=0.0)
        await actuate_tools.actuate_wrench(entity="cube", fx=10.0, persistent=True)

        await world_tools.world_step(steps=100)
        state_1 = await scene_tools.scene_get_state(name="cube")
        x1 = state_1.data["pose"]["position"][0]
        # First step contributes Δx = 0.5 * 10 * (0.1)**2 = 0.05.
        assert x1 == pytest.approx(0.05)

        # Wrench still recorded (persistent), so a second step adds another 0.05.
        assert await _adapter().get_recorded_wrench("cube") is not None
        await world_tools.world_step(steps=100)
        state_2 = await scene_tools.scene_get_state(name="cube")
        x2 = state_2.data["pose"]["position"][0]

        assert x2 > x1  # monotonic increase
        assert x2 == pytest.approx(0.10)  # two equal one-shot integrations

    anyio.run(_run)


def test_actuate_clear_wrench_removes_recorded_wrench():
    """actuate_clear_wrench deletes the recorded wrench (read-back -> None)."""

    async def _run():
        await actuate_tools.actuate_wrench(entity="cube", fx=5.0)
        assert await _adapter().get_recorded_wrench("cube") is not None

        cleared = await actuate_tools.actuate_clear_wrench(entity="cube")
        assert cleared.success is True
        assert cleared.data["entity"] == "cube"

        assert await _adapter().get_recorded_wrench("cube") is None

    anyio.run(_run)


# --------------------------------------------------------------------------
# actuate_joint
# --------------------------------------------------------------------------


def test_actuate_joint_stores_target():
    """A valid pos command stores {"mode","value"} on the mock adapter."""

    async def _run():
        result = await actuate_tools.actuate_joint(
            model="jetank", joint="arm_base_to_long_joint", mode="pos", value=0.5
        )
        assert result.success is True

        target = await _adapter().get_joint_target("jetank", "arm_base_to_long_joint")
        assert target == {"mode": "pos", "value": 0.5}

    anyio.run(_run)


def test_actuate_joint_limit_boundary_accepted_and_rejected():
    """value == upper (1.0) is accepted; just past it (1.0001) is rejected."""

    async def _run():
        ok = await actuate_tools.actuate_joint(
            model="jetank", joint="arm_base_to_long_joint", mode="pos", value=1.0
        )
        assert ok.success is True
        assert (
            await _adapter().get_joint_target("jetank", "arm_base_to_long_joint")
        ) == {"mode": "pos", "value": 1.0}

        rejected = await actuate_tools.actuate_joint(
            model="jetank", joint="arm_base_to_long_joint", mode="pos", value=1.0001
        )
        assert rejected.success is False
        assert rejected.error_code == "JOINT_LIMIT_EXCEEDED"
        assert rejected.data is None

    anyio.run(_run)


def test_actuate_joint_continuous_accepts_large_value():
    """A continuous joint (no limits) accepts an arbitrarily large pos value."""

    async def _run():
        result = await actuate_tools.actuate_joint(
            model="jetank",
            joint="arm_base_to_arm_bearing_joint",
            mode="pos",
            value=99.0,
        )
        assert result.success is True
        target = await _adapter().get_joint_target(
            "jetank", "arm_base_to_arm_bearing_joint"
        )
        assert target == {"mode": "pos", "value": 99.0}

    anyio.run(_run)


def test_actuate_joint_unknown_joint_rejected():
    """An unknown joint is rejected with UNKNOWN_JOINT and never touches the bridge."""

    async def _run():
        result = await actuate_tools.actuate_joint(
            model="jetank", joint="no_such_joint", mode="pos", value=0.1
        )
        assert result.success is False
        assert result.error_code == "UNKNOWN_JOINT"
        assert result.data is None

    anyio.run(_run)


# --------------------------------------------------------------------------
# actuate_joint_trajectory
# --------------------------------------------------------------------------


def test_actuate_joint_trajectory_stores_num_points_and_last_point():
    """A trajectory reports num_points and stores the LAST point on the adapter."""

    async def _run():
        points = [
            {"positions": [0.0, 0.0], "time_from_start": 0.0},
            {"positions": [0.5, -0.5], "time_from_start": 1.0},
        ]
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank", points=points
        )
        assert result.success is True
        assert result.data["num_points"] == 2

        # The mock stores the last point under the reserved "_trajectory" key.
        last = await _adapter().get_joint_target("jetank", "_trajectory")
        assert last == {"positions": [0.5, -0.5], "time_from_start": 1.0}

    anyio.run(_run)


# --------------------------------------------------------------------------
# actuate_joint_trajectory + joint_names -> per-waypoint manifest limits
# (P5-deferred #1)
# --------------------------------------------------------------------------

# jetank manifest: arm_base_to_long_joint / arm_long_to_short_joint are revolute
# [-1.0, 1.0]; left_finger_joint is prismatic [0.0, 0.02]; the bearing joint is
# continuous (no limits).
_TWO_LIMITED = ["arm_base_to_long_joint", "arm_long_to_short_joint"]


def test_trajectory_joint_names_in_range_ok_and_echoed():
    """joint_names in range -> success, echoed in data, last point stored."""

    async def _run():
        points = [
            {"positions": [0.0, 0.0], "time_from_start": 0.0},
            {"positions": [0.9, -0.9], "time_from_start": 1.0},
        ]
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank", points=points, joint_names=_TWO_LIMITED
        )
        assert result.success is True
        assert result.data["joint_names"] == _TWO_LIMITED
        last = await _adapter().get_joint_target("jetank", "_trajectory")
        assert last == {"positions": [0.9, -0.9], "time_from_start": 1.0}

    anyio.run(_run)


def test_trajectory_joint_names_out_of_range_rejected():
    """A finite waypoint position outside the joint range -> JOINT_LIMIT_EXCEEDED;
    the bridge is never touched (nothing stored)."""

    async def _run():
        points = [
            {"positions": [0.0, 0.0], "time_from_start": 0.0},
            {"positions": [1.5, 0.0], "time_from_start": 1.0},  # 1.5 > upper 1.0
        ]
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank", points=points, joint_names=_TWO_LIMITED
        )
        assert result.success is False
        assert result.error_code == "JOINT_LIMIT_EXCEEDED"
        assert result.data is None
        assert await _adapter().get_joint_target("jetank", "_trajectory") is None

    anyio.run(_run)


def test_trajectory_joint_names_boundary_accepted_and_rejected():
    """value == upper (1.0) accepted; just past it (1.0001) rejected."""

    async def _run():
        ok = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [1.0, -1.0], "time_from_start": 1.0}],
            joint_names=_TWO_LIMITED,
        )
        assert ok.success is True

        rejected = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [1.0001, 0.0], "time_from_start": 1.0}],
            joint_names=_TWO_LIMITED,
        )
        assert rejected.success is False
        assert rejected.error_code == "JOINT_LIMIT_EXCEEDED"

    anyio.run(_run)


def test_trajectory_joint_names_length_mismatch_rejected():
    """positions length != joint_names length -> INVALID_TRAJECTORY."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [0.0, 0.0, 0.0], "time_from_start": 1.0}],  # 3 != 2
            joint_names=_TWO_LIMITED,
        )
        assert result.success is False
        assert result.error_code == "INVALID_TRAJECTORY"
        assert result.data is None

    anyio.run(_run)


def test_trajectory_unknown_joint_name_rejected():
    """An unknown joint name -> UNKNOWN_JOINT; bridge untouched."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [0.0], "time_from_start": 1.0}],
            joint_names=["no_such_joint"],
        )
        assert result.success is False
        assert result.error_code == "UNKNOWN_JOINT"
        assert result.data is None
        assert await _adapter().get_joint_target("jetank", "_trajectory") is None

    anyio.run(_run)


@pytest.mark.parametrize("bad_names", [[], "arm_base_to_long_joint", [123]])
def test_trajectory_joint_names_bad_type_rejected(bad_names):
    """joint_names not a non-empty list of strings -> INVALID_TRAJECTORY."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [0.0], "time_from_start": 1.0}],
            joint_names=bad_names,
        )
        assert result.success is False
        assert result.error_code == "INVALID_TRAJECTORY"

    anyio.run(_run)


def test_trajectory_joint_names_continuous_accepts_large():
    """A continuous (limitless) joint accepts an arbitrarily large waypoint value."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [99.0], "time_from_start": 1.0}],
            joint_names=["arm_base_to_arm_bearing_joint"],  # continuous, no limits
        )
        assert result.success is True

    anyio.run(_run)


def test_trajectory_without_joint_names_stays_unbounded():
    """Backward-compat: without joint_names, an out-of-range position is accepted
    (positions carry no joint mapping, so no range check is possible)."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [999.0], "time_from_start": 1.0}],
        )
        assert result.success is True
        assert result.data["joint_names"] is None

    anyio.run(_run)


def test_trajectory_joint_names_forwarded_to_adapter():
    """Review finding A regression: joint_names must REACH the adapter (the real
    controller's position->joint mapping), not merely be validated and dropped.
    The mock records the forwarded list under _trajectory_joint_names."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [0.5, -0.5], "time_from_start": 1.0}],
            joint_names=_TWO_LIMITED,
        )
        assert result.success is True
        forwarded = await _adapter().get_joint_target(
            "jetank", "_trajectory_joint_names"
        )
        assert forwarded == _TWO_LIMITED

    anyio.run(_run)


@pytest.mark.parametrize("bad_pos", [True, False, "5.0", "0.01", None])
def test_trajectory_nonnumeric_position_rejected(bad_pos):
    """Review finding B regression: with joint_names active, a non-number position
    (bool/str/None) is rejected INVALID_TRAJECTORY. Previously it was silently
    skipped, then coerced by the bridge (float(True)=1.0, float("5.0")=5.0) to a
    FINITE float and driven UNBOUNDED past the limit guard. left_finger_joint
    limits are [0.0, 0.02]; the bridge is never touched (nothing stored)."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank",
            points=[{"positions": [bad_pos], "time_from_start": 1.0}],
            joint_names=["left_finger_joint"],
        )
        assert result.success is False
        assert result.error_code == "INVALID_TRAJECTORY"
        assert result.data is None
        assert await _adapter().get_joint_target("jetank", "_trajectory") is None

    anyio.run(_run)


# --------------------------------------------------------------------------
# P1 review fixes: INVALID_MODE / INVALID_TRAJECTORY / wheel-safe manifest
# --------------------------------------------------------------------------


def test_actuate_joint_invalid_mode_rejected():
    """A mode outside {pos,vel,force} is rejected with INVALID_MODE; bridge untouched."""

    async def _run():
        result = await actuate_tools.actuate_joint(
            model="jetank", joint="arm_base_to_long_joint", mode="torque", value=0.1
        )
        assert result.success is False
        assert result.error_code == "INVALID_MODE"
        assert result.data is None
        # Bridge was never called -> no target recorded.
        assert (
            await _adapter().get_joint_target("jetank", "arm_base_to_long_joint")
        ) is None

    anyio.run(_run)


@pytest.mark.parametrize(
    "bad_points",
    [
        None,
        [],
        "nope",
        [{"time_from_start": 1.0}],          # missing positions
        [{"positions": "0.5"}],              # positions not a list
        [{"positions": [0.0]}, "oops"],      # second element not a dict
        # time_from_start monotonicity (P1-real #8):
        [{"positions": [0.0], "time_from_start": -1.0}],   # negative time
        [{"positions": [0.0], "time_from_start": "x"}],    # non-numeric time
        [                                                   # equal (not strictly increasing)
            {"positions": [0.0], "time_from_start": 1.0},
            {"positions": [0.5], "time_from_start": 1.0},
        ],
        [                                                   # decreasing time
            {"positions": [0.0], "time_from_start": 2.0},
            {"positions": [0.5], "time_from_start": 1.0},
        ],
    ],
)
def test_actuate_joint_trajectory_malformed_rejected(bad_points):
    """Malformed trajectory input is rejected with INVALID_TRAJECTORY."""

    async def _run():
        result = await actuate_tools.actuate_joint_trajectory(
            model="jetank", points=bad_points
        )
        assert result.success is False
        assert result.error_code == "INVALID_TRAJECTORY"
        assert result.data is None

    anyio.run(_run)


def test_manifest_loads_from_package_data_when_no_env_override(monkeypatch):
    """Wheel-safe load: with no env override, the package-data manifest resolves
    and joints (including the new gripper joints) are found."""
    monkeypatch.delenv("GAZEBO_MODEL_MANIFEST", raising=False)
    actuate_tools._reset_manifest_cache()

    # The package-data path resolves via importlib.resources (wheel-safe).
    pkg_path = actuate_tools._packaged_manifest_path()
    assert pkg_path is not None, "package-data manifest should be discoverable"

    # Joints from the manifest are found through the normal loader path.
    assert actuate_tools._joint_known("jetank", "arm_base_to_long_joint") is True
    assert actuate_tools._joint_known("jetank", "left_finger_joint") is True
    assert actuate_tools._joint_known("jetank", "right_finger_joint") is True
    # The prismatic gripper joint carries its [lower, upper] limits.
    assert actuate_tools._joint_limits("jetank", "left_finger_joint") == (0.0, 0.02)
