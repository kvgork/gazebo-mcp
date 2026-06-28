"""
Unit tests for nav2_tools module.

Tests all 10 Navigation & Path Planning (Nav2) functions in mock mode
(no Gazebo / Nav2 connection required).

Functions covered:
- initialize_nav2
- send_nav_goal, cancel_nav_goal, get_nav_status
- plan_path, visualize_path
- create_occupancy_map, update_costmap
- follow_waypoints, plan_coverage_path
"""

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import nav2_tools


def _reset_state():
    """Clear all module-level state dicts between tests."""
    nav2_tools._nav_goals.clear()
    nav2_tools._paths.clear()
    nav2_tools._costmaps.clear()
    nav2_tools._nav2_state.clear()
    nav2_tools._nav2_state.update({"active": False})


@pytest.fixture(autouse=True)
def reset_module_state():
    """Auto-reset module state before and after every test."""
    _reset_state()
    yield
    _reset_state()


class TestInitializeNav2:
    """Tests for nav2_tools.initialize_nav2()."""

    def test_initialize_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.initialize_nav2()
        assert result.success is True
        assert result.data["status"] == "active"

    def test_initialize_sets_active_state(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            nav2_tools.initialize_nav2(robot="turtlebot3")
        assert nav2_tools._nav2_state["active"] is True

    def test_initialize_returns_lifecycle_nodes(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.initialize_nav2()
        assert "lifecycle_nodes" in result.data
        assert isinstance(result.data["lifecycle_nodes"], list)
        assert len(result.data["lifecycle_nodes"]) > 0

    def test_initialize_with_robot_returns_robot(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.initialize_nav2(robot="my_robot")
        assert result.data["robot"] == "my_robot"

    def test_initialize_invalid_robot_name_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.initialize_nav2(robot="123robot")
        assert result.success is False


class TestSendNavGoal:
    """Tests for nav2_tools.send_nav_goal()."""

    def test_send_goal_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.send_nav_goal(2.0, 3.0)
        assert result.success is True
        assert result.data["status"] == "accepted"

    def test_send_goal_stores_in_dict(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.send_nav_goal(1.0, 1.0)
        goal_id = result.data["goal_id"]
        assert goal_id in nav2_tools._nav_goals
        assert goal_id.startswith("goal_")

    def test_send_goal_all_valid_planners(self):
        valid = ["DWB", "TEB", "RPP", "MPPI"]
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for p in valid:
                result = nav2_tools.send_nav_goal(1.0, 2.0, planner=p)
                assert result.success is True, f"Expected success for planner={p}"

    def test_send_goal_invalid_planner_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.send_nav_goal(1.0, 2.0, planner="BADPLANNER")
        assert result.success is False
        assert result.error_code == "INVALID_PLANNER"
        assert result.suggestions is not None

    def test_send_goal_rejects_path_only_planners(self):
        """Path-planner-only values (A*, RRT, RRT*) are NOT valid nav-goal planners."""
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for p in ["A*", "RRT", "RRT*"]:
                result = nav2_tools.send_nav_goal(1.0, 2.0, planner=p)
                assert result.success is False, f"send_nav_goal must reject planner={p}"
                assert result.error_code == "INVALID_PLANNER"

    def test_send_goal_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.send_nav_goal(2.0, 0.0, theta=1.57)
        data = result.data
        assert data["target"] == {"x": 2.0, "y": 0.0, "theta": 1.57}
        assert "eta_s" in data
        assert "goal_id" in data

    def test_send_goal_invalid_coordinate_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.send_nav_goal("notanumber", 2.0)
        assert result.success is False


class TestCancelNavGoal:
    """Tests for nav2_tools.cancel_nav_goal()."""

    def test_cancel_current_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.cancel_nav_goal()
        assert result.success is True
        assert result.data["cancelled"] == "current"
        assert result.data["status"] == "cancelled"

    def test_cancel_specific_goal(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            r = nav2_tools.send_nav_goal(1.0, 1.0)
            goal_id = r.data["goal_id"]
            result = nav2_tools.cancel_nav_goal(goal_id=goal_id)
        assert result.success is True
        assert result.data["cancelled"] == goal_id
        assert nav2_tools._nav_goals[goal_id]["status"] == "cancelled"

    def test_cancel_unknown_goal_still_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.cancel_nav_goal(goal_id="goal_999")
        assert result.success is True
        assert result.data["status"] == "cancelled"

    def test_cancel_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.cancel_nav_goal()
        assert "cancelled" in result.data
        assert "status" in result.data


class TestGetNavStatus:
    """Tests for nav2_tools.get_nav_status()."""

    def test_status_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.get_nav_status()
        assert result.success is True

    def test_status_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.get_nav_status()
        data = result.data
        assert "active_goal" in data
        assert "progress_pct" in data
        assert "distance_remaining_m" in data
        assert "obstacles_detected" in data

    def test_status_no_active_goal_is_idle(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.get_nav_status()
        assert result.data["active_goal"] is None
        assert result.data["progress_pct"] == 0.0

    def test_status_reflects_active_goal(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            r = nav2_tools.send_nav_goal(5.0, 5.0)
            result = nav2_tools.get_nav_status()
        assert result.data["active_goal"] == r.data["goal_id"]
        assert result.data["progress_pct"] > 0.0

    def test_status_detailed_includes_extra_fields(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.get_nav_status(response_format="detailed")
        assert "total_goals" in result.data


class TestPlanPath:
    """Tests for nav2_tools.plan_path()."""

    def test_plan_path_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 5, "y": 0})
        assert result.success is True
        assert result.data["path_id"].startswith("path_")

    def test_plan_path_all_valid_planners(self):
        valid = ["A*", "RRT", "RRT*", "DWB", "TEB"]
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for p in valid:
                result = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 3, "y": 4}, planner=p)
                assert result.success is True, f"Expected success for planner={p}"

    def test_plan_path_invalid_planner_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 1, "y": 1}, planner="DIJKSTRA")
        assert result.success is False
        assert result.error_code == "INVALID_PLANNER"

    def test_plan_path_rejects_goal_only_planners(self):
        """Goal-controller-only values (RPP, MPPI) are NOT valid path planners."""
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for p in ["RPP", "MPPI"]:
                result = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 1, "y": 1}, planner=p)
                assert result.success is False, f"plan_path must reject planner={p}"
                assert result.error_code == "INVALID_PLANNER"

    def test_plan_path_missing_start_keys_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_path({"x": 0}, {"x": 1, "y": 1})
        assert result.success is False
        assert result.error_code == "INVALID_START"

    def test_plan_path_missing_goal_keys_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_path({"x": 0, "y": 0}, {"y": 1})
        assert result.success is False
        assert result.error_code == "INVALID_GOAL"

    def test_plan_path_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 3, "y": 4})
        data = result.data
        assert "waypoints" in data and isinstance(data["waypoints"], list)
        assert data["length_m"] == 5.0
        assert "cost" in data
        assert "est_time_s" in data


class TestVisualizePath:
    """Tests for nav2_tools.visualize_path()."""

    def test_visualize_existing_path_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            r = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 2, "y": 2})
            result = nav2_tools.visualize_path(path_id=r.data["path_id"])
        assert result.success is True
        assert "markers" in result.data

    def test_visualize_latest_path_when_none_given(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            r = nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 1, "y": 1})
            result = nav2_tools.visualize_path()
        assert result.success is True
        assert result.data["path_id"] == r.data["path_id"]

    def test_visualize_unknown_path_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.visualize_path(path_id="path_999")
        assert result.success is False
        assert result.error_code == "PATH_NOT_FOUND"

    def test_visualize_no_paths_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.visualize_path()
        assert result.success is False
        assert result.error_code == "PATH_NOT_FOUND"

    def test_visualize_markers_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            nav2_tools.plan_path({"x": 0, "y": 0}, {"x": 2, "y": 0})
            result = nav2_tools.visualize_path()
        markers = result.data["markers"]
        assert "line_strip" in markers
        assert "topic" in markers


class TestCreateOccupancyMap:
    """Tests for nav2_tools.create_occupancy_map()."""

    def test_create_map_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.create_occupancy_map()
        assert result.success is True

    def test_create_map_invalid_resolution_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.create_occupancy_map(resolution=0.0)
        assert result.success is False

    def test_create_map_non_finite_resolution_returns_error(self):
        """Inf/NaN resolution is rejected (not silently turned into a bogus map)."""
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for bad in (float("inf"), float("nan"), float("-inf")):
                result = nav2_tools.create_occupancy_map(resolution=bad)
                assert result.success is False, f"resolution={bad} must be rejected"

    def test_create_map_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.create_occupancy_map(resolution=0.1)
        data = result.data
        assert data["resolution"] == 0.1
        assert "width" in data and "height" in data
        assert "origin" in data
        summary = data["occupancy_summary"]
        assert {"free", "occupied", "unknown"} <= set(summary.keys())

    def test_create_map_origin_keys(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.create_occupancy_map()
        origin = result.data["origin"]
        assert {"x", "y", "theta"} <= set(origin.keys())

    def test_create_map_negative_resolution_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.create_occupancy_map(resolution=-0.5)
        assert result.success is False


class TestUpdateCostmap:
    """Tests for nav2_tools.update_costmap()."""

    def test_update_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.update_costmap([{"action": "inject", "x": 1.0, "y": 2.0}])
        assert result.success is True
        assert result.data["count"] == 1

    def test_update_all_valid_actions(self):
        valid = ["inject", "clear", "inflate"]
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for a in valid:
                result = nav2_tools.update_costmap([{"action": a}])
                assert result.success is True, f"Expected success for action={a}"

    def test_update_bad_action_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.update_costmap([{"action": "explode"}])
        assert result.success is False
        assert result.error_code == "INVALID_COSTMAP_ACTION"

    def test_update_empty_list_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.update_costmap([])
        assert result.success is False
        assert result.error_code == "INVALID_UPDATES"

    def test_update_entry_missing_action_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.update_costmap([{"x": 1.0}])
        assert result.success is False
        assert result.error_code == "INVALID_UPDATE_ENTRY"

    def test_update_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.update_costmap([{"action": "clear"}, {"action": "inflate", "radius": 0.3}])
        assert result.data["count"] == 2
        assert isinstance(result.data["applied"], list)


class TestFollowWaypoints:
    """Tests for nav2_tools.follow_waypoints()."""

    def test_follow_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.follow_waypoints([{"x": 1, "y": 1}, {"x": 2, "y": 2}])
        assert result.success is True
        assert result.data["status"] == "executing"

    def test_follow_all_valid_modes(self):
        valid = ["sequence", "loop", "patrol"]
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for m in valid:
                result = nav2_tools.follow_waypoints([{"x": 1, "y": 1}], mode=m)
                assert result.success is True, f"Expected success for mode={m}"

    def test_follow_invalid_mode_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.follow_waypoints([{"x": 1, "y": 1}], mode="zigzag")
        assert result.success is False
        assert result.error_code == "INVALID_MODE"

    def test_follow_empty_waypoints_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.follow_waypoints([])
        assert result.success is False
        assert result.error_code == "INVALID_WAYPOINTS"

    def test_follow_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.follow_waypoints([{"x": 1, "y": 1}, {"x": 2, "y": 2}, {"x": 3, "y": 3}])
        data = result.data
        assert data["waypoint_count"] == 3
        assert data["mission_id"].startswith("mission_")
        assert data["mode"] == "sequence"


class TestPlanCoveragePath:
    """Tests for nav2_tools.plan_coverage_path()."""

    def test_coverage_succeeds(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_coverage_path({"min_x": 0, "min_y": 0, "max_x": 5, "max_y": 5})
        assert result.success is True

    def test_coverage_all_valid_algorithms(self):
        valid = ["boustrophedon", "spiral", "energy_efficient"]
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            for a in valid:
                result = nav2_tools.plan_coverage_path({"min_x": 0, "min_y": 0, "max_x": 3, "max_y": 3}, algorithm=a)
                assert result.success is True, f"Expected success for algorithm={a}"

    def test_coverage_invalid_algorithm_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_coverage_path({"min_x": 0, "min_y": 0, "max_x": 1, "max_y": 1}, algorithm="random")
        assert result.success is False
        assert result.error_code == "INVALID_ALGORITHM"

    def test_coverage_empty_area_returns_error(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_coverage_path({})
        assert result.success is False
        assert result.error_code == "INVALID_AREA"

    def test_coverage_data_shape(self):
        with patch.object(nav2_tools, "use_real_gazebo", return_value=False):
            result = nav2_tools.plan_coverage_path({"min_x": 0, "min_y": 0, "max_x": 4, "max_y": 4})
        data = result.data
        assert "waypoints" in data and isinstance(data["waypoints"], list)
        assert "coverage_pct" in data
        assert "path_length_m" in data
        assert data["algorithm"] == "boustrophedon"
