"""
Focused unit tests for the lean P0-B tools.

These exercise the framework-agnostic async functions in
``gazebo_mcp.tools.world`` and ``gazebo_mcp.tools.scene`` DIRECTLY (not via the
FastMCP transport), asserting the ``OperationResult`` fields they return against
the deterministic MOCK backend.

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

from gazebo_mcp.tools import scene as scene_tools
from gazebo_mcp.tools import world as world_tools

CUBE_SDF = "<sdf version='1.7'/>"


@pytest.fixture(autouse=True)
def _force_mock_backend(monkeypatch):
    """Force the MOCK backend for this module and reset the bridge singleton.

    ``monkeypatch.setenv`` overrides pixi's ``GAZEBO_BACKEND=modern`` per test and
    auto-reverts, so it never leaks into other test modules. Clearing the cached
    bridge node before/after each test guarantees a fresh empty mock world.
    """
    monkeypatch.setenv("GAZEBO_BACKEND", "mock")
    import gazebo_mcp.tools._bridge_helper as bh

    bh._bridge_node = None
    bh._connection_manager = None
    yield
    bh._bridge_node = None
    bh._connection_manager = None


# --------------------------------------------------------------------------
# scene_*
# --------------------------------------------------------------------------


def test_scene_spawn_then_get_state_roundtrip():
    """scene_spawn places a model; scene_get_state reads back the stored pose."""

    async def _run():
        spawn = await scene_tools.scene_spawn(
            name="cube", sdf=CUBE_SDF, x=1.0, y=2.0, z=0.5
        )
        assert spawn.success is True
        assert spawn.data["name"] == "cube"

        state = await scene_tools.scene_get_state(name="cube")
        assert state.success is True
        assert state.data["name"] == "cube"
        assert state.data["pose"]["position"] == pytest.approx([1.0, 2.0, 0.5])
        assert state.data["pose"]["orientation"] == pytest.approx([0.0, 0.0, 0.0, 1.0])

    anyio.run(_run)


def test_scene_get_state_missing_is_model_not_found():
    """Querying a non-existent model is a clean failure, not a crash."""

    async def _run():
        result = await scene_tools.scene_get_state(name="ghost")
        assert result.success is False
        assert result.error_code == "MODEL_NOT_FOUND"

    anyio.run(_run)


def test_scene_set_state_moves_pose():
    """scene_set_state updates an existing model's pose; readback reflects it."""

    async def _run():
        await scene_tools.scene_spawn(name="m", sdf=CUBE_SDF, x=0.0, y=0.0, z=0.0)

        moved = await scene_tools.scene_set_state(name="m", x=9.0, y=8.0, z=7.0)
        assert moved.success is True

        state = await scene_tools.scene_get_state(name="m")
        assert state.success is True
        assert state.data["pose"]["position"] == pytest.approx([9.0, 8.0, 7.0])

    anyio.run(_run)


def test_scene_remove_then_not_in_list_models():
    """scene_remove deletes the model; scene_list_models no longer lists it."""

    async def _run():
        await scene_tools.scene_spawn(name="cube", sdf=CUBE_SDF, x=1.0, y=2.0, z=0.5)

        listed = await scene_tools.scene_list_models()
        assert listed.success is True
        assert "cube" in listed.data["models"]
        assert listed.data["count"] == len(listed.data["models"])

        removed = await scene_tools.scene_remove(name="cube")
        assert removed.success is True

        listed_after = await scene_tools.scene_list_models()
        assert listed_after.success is True
        assert "cube" not in listed_after.data["models"]

    anyio.run(_run)


# --------------------------------------------------------------------------
# world_*
# --------------------------------------------------------------------------


def test_world_step_advances_sim_time():
    """world_step advances sim_time by steps * step_size (mock step_size 0.001)."""

    async def _run():
        result = await world_tools.world_step(steps=100)
        assert result.success is True
        assert result.data["steps"] == 100
        assert result.data["sim_time"] == pytest.approx(0.1)

    anyio.run(_run)


def test_world_set_physics_returns_success():
    """world_set_physics applies step_size/rtf on the mock backend."""

    async def _run():
        result = await world_tools.world_set_physics(step_size=0.01, rtf=2.0)
        assert result.success is True
        assert result.data["applied"] is True

    anyio.run(_run)


def test_world_seed_returns_success():
    """world_seed is a best-effort success on the mock backend."""

    async def _run():
        result = await world_tools.world_seed(value=42)
        assert result.success is True
        assert result.data["seed"] == 42

    anyio.run(_run)


def test_world_get_stats_reports_sim_time():
    """world_get_stats reads sim_time without advancing it."""

    async def _run():
        await world_tools.world_step(steps=100)  # sim_time -> 0.1
        stats = await world_tools.world_get_stats()
        assert stats.success is True
        assert stats.data["sim_time"] == pytest.approx(0.1)

    anyio.run(_run)


def test_world_set_physics_then_step_uses_new_step_size():
    """After set_physics(step_size=0.01), world_step(10) advances by 0.1s."""

    async def _run():
        applied = await world_tools.world_set_physics(step_size=0.01)
        assert applied.success is True
        stepped = await world_tools.world_step(steps=10)
        assert stepped.success is True
        assert stepped.data["sim_time"] == pytest.approx(0.1)  # 10 * 0.01

    anyio.run(_run)
