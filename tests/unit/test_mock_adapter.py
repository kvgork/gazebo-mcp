"""
P0 acceptance: the MockGazeboAdapter is an honest in-memory backend so the
"spawn cube -> query pose -> step -> remove" loop passes with NO Gazebo/ROS2.

Runs under -e dev (no ros_gz). Real-backend equivalents run under -e sim/-e full.
"""

import sys
from pathlib import Path

import anyio
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.bridge.gazebo_interface import EntityPose, EntityTwist
from gazebo_mcp.bridge.adapters.mock_adapter import MockGazeboAdapter
from gazebo_mcp.bridge.factory import GazeboAdapterFactory
from gazebo_mcp.bridge.config import GazeboConfig, GazeboBackend
from gazebo_mcp.utils.exceptions import ModelNotFoundError


def _cube_pose():
    return EntityPose(position=(1.0, 2.0, 0.5), orientation=(0.0, 0.0, 0.0, 1.0))


def test_factory_creates_mock_backend():
    """Factory wires GazeboBackend.MOCK to the MockGazeboAdapter (no node needed)."""
    factory = GazeboAdapterFactory(node=None, config=GazeboConfig(backend=GazeboBackend.MOCK))
    adapter = factory.create_adapter()
    assert isinstance(adapter, MockGazeboAdapter)
    assert adapter.get_backend_name() == "mock"


def test_spawn_query_step_remove_acceptance():
    """The headline P0 loop: spawn -> read back pose -> step -> remove."""

    async def _run():
        gz = MockGazeboAdapter()

        # spawn
        assert await gz.spawn_entity("test_cube", "<sdf/>", _cube_pose()) is True
        assert "test_cube" in await gz.list_entities()

        # query pose — readback returns the stored pose (not zeros)
        state = await gz.get_entity_state("test_cube")
        assert state["pose"]["position"] == [1.0, 2.0, 0.5]
        assert state["pose"]["orientation"] == [0.0, 0.0, 0.0, 1.0]

        # step advances sim_time deterministically (default step_size 0.001)
        before = (await gz.get_world_properties()).sim_time
        result = await gz.step(100)
        assert result["steps"] == 100
        assert abs(result["sim_time"] - (before + 100 * 0.001)) < 1e-9
        assert abs((await gz.get_world_properties()).sim_time - 0.1) < 1e-9

        # remove
        assert await gz.delete_entity("test_cube") is True
        assert "test_cube" not in await gz.list_entities()
        with pytest.raises(ModelNotFoundError):
            await gz.get_entity_state("test_cube")

    anyio.run(_run)


def test_set_entity_state_updates_pose():
    async def _run():
        gz = MockGazeboAdapter()
        await gz.spawn_entity("m", "<sdf/>", _cube_pose())
        new = EntityPose(position=(9.0, 8.0, 7.0), orientation=(0.0, 0.0, 0.0, 1.0))
        await gz.set_entity_state("m", new, EntityTwist(linear=(1.0, 0.0, 0.0), angular=(0.0, 0.0, 0.5)))
        state = await gz.get_entity_state("m")
        assert state["pose"]["position"] == [9.0, 8.0, 7.0]
        assert state["twist"]["linear"] == [1.0, 0.0, 0.0]

    anyio.run(_run)


def test_set_physics_changes_step_size():
    async def _run():
        gz = MockGazeboAdapter()
        assert await gz.set_physics(step_size=0.01, rtf=2.0) is True
        result = await gz.step(10)
        assert abs(result["sim_time"] - 0.1) < 1e-9  # 10 * 0.01
        with pytest.raises(ValueError):
            await gz.set_physics(step_size=-1.0)

    anyio.run(_run)


def test_seed_and_step_validation():
    async def _run():
        gz = MockGazeboAdapter()
        assert await gz.seed(42) is True
        with pytest.raises(ValueError):
            await gz.step(0)

    anyio.run(_run)


def test_pause_and_reset():
    async def _run():
        gz = MockGazeboAdapter()
        await gz.spawn_entity("m", "<sdf/>", _cube_pose())
        assert await gz.pause_simulation() is True
        assert (await gz.get_world_properties()).paused is True
        assert await gz.unpause_simulation() is True
        await gz.step(50)
        assert await gz.reset_simulation() is True
        props = await gz.get_world_properties()
        assert props.sim_time == 0.0
        assert props.models == []

    anyio.run(_run)


def test_delete_missing_raises():
    async def _run():
        gz = MockGazeboAdapter()
        with pytest.raises(ModelNotFoundError):
            await gz.delete_entity("ghost")

    anyio.run(_run)
