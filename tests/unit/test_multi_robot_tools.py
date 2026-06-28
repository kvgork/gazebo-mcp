"""
Unit tests for multi_robot_tools module.

Tests all 6 multi-robot coordination functions in mock mode
(no Gazebo connection required).

Functions covered:
- spawn_robot_fleet
- get_fleet_status
- send_fleet_command
- apply_swarm_behavior
- visualize_robot_network
- enable_multi_robot_collision_avoidance
"""

import math

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import multi_robot_tools


def _reset_state():
    """Clear all module-level state dicts between tests."""
    multi_robot_tools._fleets.clear()


@pytest.fixture(autouse=True)
def reset_module_state():
    """Auto-reset module state before every test."""
    _reset_state()
    yield
    _reset_state()


def _spawn(count=4, formation="grid", **kw):
    """Helper: spawn a fleet in mock mode and return the OperationResult."""
    with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
        return multi_robot_tools.spawn_robot_fleet(
            robot_type="turtlebot3", count=count, formation=formation, **kw
        )


class TestSpawnRobotFleet:
    """Tests for multi_robot_tools.spawn_robot_fleet()."""

    def test_spawn_returns_fleet_id(self):
        """Spawning a fleet returns success with a fleet_id."""
        result = _spawn(count=4)
        assert result.success is True
        assert result.data["fleet_id"] == "fleet_1"
        assert result.data["count"] == 4

    def test_spawn_stores_fleet_in_state(self):
        """Fleet is stored in module _fleets dict with the expected shape."""
        result = _spawn(count=3, formation="line")
        fid = result.data["fleet_id"]
        assert fid in multi_robot_tools._fleets
        fleet = multi_robot_tools._fleets[fid]
        assert fleet["robot_type"] == "turtlebot3"
        assert len(fleet["robots"]) == 3
        assert "created" in fleet

    def test_spawn_all_valid_formations(self):
        """All valid formations succeed."""
        for formation in ["line", "grid", "circle", "random"]:
            result = _spawn(count=5, formation=formation)
            assert result.success is True, f"Expected success for formation={formation}"
            assert result.data["formation"] == formation

    def test_spawn_invalid_formation_returns_error(self):
        """Invalid formation returns a failure result."""
        result = _spawn(count=3, formation="spiral")
        assert result.success is False
        assert result.error_code == "INVALID_FORMATION"
        assert result.suggestions is not None

    def test_spawn_invalid_count_returns_error(self):
        """Non-positive count returns failure."""
        result = _spawn(count=0)
        assert result.success is False

    def test_spawn_non_integer_count_returns_error(self):
        """Float count returns failure (count must be a positive integer)."""
        result = _spawn(count=2.5)
        assert result.success is False
        assert result.error_code == "INVALID_COUNT"

    def test_spawn_invalid_spacing_returns_error(self):
        """Non-positive spacing returns failure."""
        result = _spawn(count=3, spacing=0.0)
        assert result.success is False

    def test_spawn_robots_have_distinct_poses(self):
        """Computed poses are collision-free (distinct) for a grid fleet."""
        result = _spawn(count=4, formation="grid", spacing=2.0)
        robots = result.data["robots"]
        coords = {(round(r["pose"]["x"], 6), round(r["pose"]["y"], 6)) for r in robots}
        assert len(coords) == len(robots)

    def test_spawn_line_formation_spacing(self):
        """Line formation places robots along +x at the given spacing."""
        result = _spawn(count=3, formation="line", spacing=2.0)
        xs = [r["pose"]["x"] for r in result.data["robots"]]
        assert xs == [0.0, 2.0, 4.0]

    def test_spawn_data_shape(self):
        """Concise response data contains expected keys."""
        result = _spawn(count=2)
        assert set(["fleet_id", "count", "formation", "robots"]).issubset(result.data.keys())
        for r in result.data["robots"]:
            assert "name" in r
            assert set(["x", "y", "z", "yaw"]).issubset(r["pose"].keys())

    def test_spawn_fleet_ids_increment(self):
        """Fleet ids increment as fleets are spawned."""
        r1 = _spawn(count=2)
        r2 = _spawn(count=2)
        assert r1.data["fleet_id"] == "fleet_1"
        assert r2.data["fleet_id"] == "fleet_2"


class TestGetFleetStatus:
    """Tests for multi_robot_tools.get_fleet_status()."""

    def test_status_single_fleet_succeeds(self):
        """Querying a known fleet returns per-robot status."""
        fid = _spawn(count=3).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.get_fleet_status(fleet_id=fid)
        assert result.success is True
        assert result.data["fleet_count"] == 1
        robots = result.data["fleets"][0]["robots"]
        assert len(robots) == 3

    def test_status_all_fleets(self):
        """Querying with no fleet_id returns all fleets."""
        _spawn(count=2)
        _spawn(count=2)
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.get_fleet_status()
        assert result.success is True
        assert result.data["fleet_count"] == 2

    def test_status_unknown_fleet_returns_error(self):
        """Unknown fleet_id returns FLEET_NOT_FOUND."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.get_fleet_status(fleet_id="fleet_999")
        assert result.success is False
        assert result.error_code == "FLEET_NOT_FOUND"
        assert result.suggestions is not None

    def test_status_robot_shape(self):
        """Each robot status has position, velocity, battery, task_status."""
        fid = _spawn(count=2).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.get_fleet_status(fleet_id=fid)
        robot = result.data["fleets"][0]["robots"][0]
        for key in ["name", "position", "velocity", "battery_pct", "task_status"]:
            assert key in robot
        assert "linear" in robot["velocity"]
        assert "angular" in robot["velocity"]

    def test_status_empty_no_fleets(self):
        """With no fleets, querying all returns fleet_count 0."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.get_fleet_status()
        assert result.success is True
        assert result.data["fleet_count"] == 0


class TestSendFleetCommand:
    """Tests for multi_robot_tools.send_fleet_command()."""

    def test_command_broadcast_succeeds(self):
        """Broadcasting a command dispatches to all fleet robots."""
        fid = _spawn(count=3).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.send_fleet_command(command="move", fleet_id=fid)
        assert result.success is True
        assert result.data["command"] == "move"
        assert result.data["count"] == 3
        assert len(result.data["dispatched_to"]) == 3

    def test_command_all_valid_values(self):
        """All valid commands succeed."""
        fid = _spawn(count=2).data["fleet_id"]
        for command in ["move", "stop", "formation", "sync", "return_home"]:
            with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
                result = multi_robot_tools.send_fleet_command(command=command, fleet_id=fid)
            assert result.success is True, f"Expected success for command={command}"
            assert result.data["command"] == command

    def test_command_invalid_value_returns_error(self):
        """Invalid command returns failure."""
        _spawn(count=2)
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.send_fleet_command(command="dance")
        assert result.success is False
        assert result.error_code == "INVALID_COMMAND"

    def test_command_subset_targets(self):
        """Targets subset dispatches only to those robots."""
        fid = _spawn(count=4).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.send_fleet_command(
                command="stop", fleet_id=fid, targets=["robot_1", "robot_3"]
            )
        assert result.success is True
        assert result.data["count"] == 2
        assert set(result.data["dispatched_to"]) == {"robot_1", "robot_3"}

    def test_command_unknown_fleet_returns_error(self):
        """Unknown fleet_id returns FLEET_NOT_FOUND."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.send_fleet_command(command="move", fleet_id="fleet_x")
        assert result.success is False
        assert result.error_code == "FLEET_NOT_FOUND"

    def test_command_default_fleet(self):
        """With no fleet_id, command targets the first available fleet."""
        fid = _spawn(count=2).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.send_fleet_command(command="sync")
        assert result.success is True
        assert result.data["fleet_id"] == fid


class TestApplySwarmBehavior:
    """Tests for multi_robot_tools.apply_swarm_behavior()."""

    def test_behavior_succeeds(self):
        """Applying a valid behavior returns applied_to list."""
        fid = _spawn(count=3).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.apply_swarm_behavior(behavior="flocking", fleet_id=fid)
        assert result.success is True
        assert result.data["behavior"] == "flocking"
        assert len(result.data["applied_to"]) == 3

    def test_behavior_all_valid_values(self):
        """All valid behaviors succeed."""
        fid = _spawn(count=2).data["fleet_id"]
        for behavior in ["flocking", "coverage", "formation_keeping", "leader_follower", "consensus"]:
            with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
                result = multi_robot_tools.apply_swarm_behavior(behavior=behavior, fleet_id=fid)
            assert result.success is True, f"Expected success for behavior={behavior}"
            assert result.data["behavior"] == behavior

    def test_behavior_invalid_value_returns_error(self):
        """Invalid behavior returns failure."""
        _spawn(count=2)
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.apply_swarm_behavior(behavior="teleport")
        assert result.success is False
        assert result.error_code == "INVALID_BEHAVIOR"

    def test_behavior_unknown_fleet_returns_error(self):
        """Unknown fleet_id returns FLEET_NOT_FOUND."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.apply_swarm_behavior(behavior="flocking", fleet_id="nope")
        assert result.success is False
        assert result.error_code == "FLEET_NOT_FOUND"

    def test_behavior_params_passthrough(self):
        """Provided params are returned in parameters field."""
        fid = _spawn(count=2).data["fleet_id"]
        params = {"separation": 1.5}
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.apply_swarm_behavior(
                behavior="flocking", fleet_id=fid, params=params
            )
        assert result.success is True
        assert result.data["parameters"] == params


class TestVisualizeRobotNetwork:
    """Tests for multi_robot_tools.visualize_robot_network()."""

    def test_visualize_default_all_layers(self):
        """Default visualization includes all four layers."""
        fid = _spawn(count=3).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.visualize_robot_network(fleet_id=fid)
        assert result.success is True
        assert set(result.data["visualizations"]) == {
            "comms_graph",
            "task_allocation",
            "formation_lines",
            "collision_zones",
        }
        assert set(result.data["markers"].keys()) == set(result.data["visualizations"])

    def test_visualize_each_valid_layer(self):
        """Each valid layer succeeds on its own."""
        fid = _spawn(count=3).data["fleet_id"]
        for layer in ["comms_graph", "task_allocation", "formation_lines", "collision_zones"]:
            with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
                result = multi_robot_tools.visualize_robot_network(fleet_id=fid, show=[layer])
            assert result.success is True, f"Expected success for layer={layer}"
            assert result.data["visualizations"] == [layer]

    def test_visualize_invalid_layer_returns_error(self):
        """Invalid visualization layer returns failure."""
        fid = _spawn(count=2).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.visualize_robot_network(fleet_id=fid, show=["hologram"])
        assert result.success is False
        assert result.error_code == "INVALID_VISUALIZATION"

    def test_visualize_unknown_fleet_returns_error(self):
        """Unknown fleet_id returns FLEET_NOT_FOUND."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.visualize_robot_network(fleet_id="ghost")
        assert result.success is False
        assert result.error_code == "FLEET_NOT_FOUND"

    def test_visualize_data_shape(self):
        """Result contains fleet_id, visualizations, markers, instructions."""
        fid = _spawn(count=2).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.visualize_robot_network(fleet_id=fid)
        for key in ["fleet_id", "visualizations", "markers", "instructions"]:
            assert key in result.data


class TestEnableMultiRobotCollisionAvoidance:
    """Tests for multi_robot_tools.enable_multi_robot_collision_avoidance()."""

    def test_enable_default_method_succeeds(self):
        """Default method enables collision avoidance."""
        fid = _spawn(count=3).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.enable_multi_robot_collision_avoidance(fleet_id=fid)
        assert result.success is True
        assert result.data["method"] == "velocity_obstacles"
        assert result.data["enabled"] is True

    def test_enable_all_valid_methods(self):
        """All valid methods succeed."""
        fid = _spawn(count=2).data["fleet_id"]
        for method in ["dynamic", "social_force", "velocity_obstacles", "priority"]:
            with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
                result = multi_robot_tools.enable_multi_robot_collision_avoidance(
                    fleet_id=fid, method=method
                )
            assert result.success is True, f"Expected success for method={method}"
            assert result.data["method"] == method

    def test_enable_invalid_method_returns_error(self):
        """Invalid method returns failure."""
        _spawn(count=2)
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.enable_multi_robot_collision_avoidance(method="magic")
        assert result.success is False
        assert result.error_code == "INVALID_CA_METHOD"

    def test_disable_collision_avoidance(self):
        """enabled=False is reflected in the response."""
        fid = _spawn(count=2).data["fleet_id"]
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.enable_multi_robot_collision_avoidance(
                fleet_id=fid, enabled=False
            )
        assert result.success is True
        assert result.data["enabled"] is False

    def test_enable_unknown_fleet_returns_error(self):
        """Unknown fleet_id returns FLEET_NOT_FOUND."""
        with patch.object(multi_robot_tools, "use_real_gazebo", return_value=False):
            result = multi_robot_tools.enable_multi_robot_collision_avoidance(fleet_id="zzz")
        assert result.success is False
        assert result.error_code == "FLEET_NOT_FOUND"
