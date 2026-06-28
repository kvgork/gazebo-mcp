"""
Unit tests for slam_tools module.

Tests all 6 SLAM & mapping functions in mock mode (no Gazebo connection
required).

Functions covered:
- start_slam
- save_slam_map
- load_slam_map
- localize_robot
- get_localization_quality
- detect_loop_closure
"""

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import slam_tools


def _reset_state():
    """Clear all module-level state dicts between tests."""
    slam_tools._slam_state.clear()
    slam_tools._slam_state.update({"active": False})
    slam_tools._maps.clear()
    slam_tools._localization_state.clear()
    slam_tools._localization_state.update({"active": False})


@pytest.fixture(autouse=True)
def reset_module_state():
    """Auto-reset module state before every test."""
    _reset_state()
    yield
    _reset_state()


class TestStartSlam:
    """Tests for slam_tools.start_slam()."""

    def test_start_slam_succeeds(self):
        """Default backend starts SLAM and sets active state."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.start_slam()

        assert result.success is True
        assert result.data["status"] == "running"
        assert slam_tools._slam_state["active"] is True

    def test_start_slam_all_valid_backends(self):
        """All valid backends return success."""
        valid = ["slam_toolbox", "cartographer", "rtabmap", "orb_slam3"]
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            for backend in valid:
                result = slam_tools.start_slam(backend=backend)
                assert result.success is True, f"Expected success for backend={backend}"
                assert result.data["backend"] == backend

    def test_start_slam_invalid_backend_returns_error(self):
        """Invalid backend returns failure with INVALID_BACKEND."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.start_slam(backend="gmapping")

        assert result.success is False
        assert result.error_code == "INVALID_BACKEND"
        assert result.suggestions is not None

    def test_start_slam_data_shape(self):
        """Concise response contains slam_id, backend, robot, status keys."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.start_slam(backend="slam_toolbox", robot="turtlebot3")

        for key in ("slam_id", "backend", "robot", "status"):
            assert key in result.data
        assert result.data["robot"] == "turtlebot3"

    def test_start_slam_invalid_robot_name_returns_error(self):
        """Robot name starting with a digit returns failure."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.start_slam(robot="123robot")

        assert result.success is False

    def test_start_slam_detailed_includes_params(self):
        """Detailed format echoes params."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.start_slam(
                backend="rtabmap", params={"resolution": 0.05}, response_format="detailed"
            )

        assert result.success is True
        assert result.data["params"] == {"resolution": 0.05}


class TestSaveSlamMap:
    """Tests for slam_tools.save_slam_map()."""

    def test_save_map_succeeds(self):
        """Saving a map stores it in _maps and returns files."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.save_slam_map(map_name="warehouse")

        assert result.success is True
        assert "warehouse" in slam_tools._maps
        assert isinstance(result.data["files"], list)
        assert len(result.data["files"]) >= 1

    def test_save_map_all_valid_formats(self):
        """All valid formats return success."""
        valid = ["pgm_yaml", "ros_map_server"]
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            for fmt in valid:
                result = slam_tools.save_slam_map(map_name=f"map_{fmt}", format=fmt)
                assert result.success is True, f"Expected success for format={fmt}"
                assert result.data["format"] == fmt

    def test_save_map_invalid_format_returns_error(self):
        """Invalid format returns failure with INVALID_FORMAT."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.save_slam_map(map_name="m", format="png")

        assert result.success is False
        assert result.error_code == "INVALID_FORMAT"

    def test_save_map_invalid_name_returns_error(self):
        """Invalid map name returns failure."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.save_slam_map(map_name="")

        assert result.success is False

    def test_save_map_data_shape(self):
        """Response contains map_name, format, files keys."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.save_slam_map(map_name="lab", format="pgm_yaml")

        for key in ("map_name", "format", "files"):
            assert key in result.data


class TestLoadSlamMap:
    """Tests for slam_tools.load_slam_map()."""

    def test_load_map_succeeds(self):
        """Loading a valid path returns loaded=True with map_info."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.load_slam_map(map_path="/maps/warehouse.yaml")

        assert result.success is True
        assert result.data["loaded"] is True
        assert result.data["map_path"] == "/maps/warehouse.yaml"

    def test_load_map_empty_path_returns_error(self):
        """Empty map_path returns failure."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.load_slam_map(map_path="")

        assert result.success is False
        assert result.error_code == "INVALID_MAP_PATH"

    def test_load_map_info_shape(self):
        """map_info contains resolution, width, height, origin."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.load_slam_map(map_path="/maps/lab.yaml")

        info = result.data["map_info"]
        for key in ("resolution", "width", "height", "origin"):
            assert key in info

    def test_load_map_unknown_response_format_coerced(self):
        """Unknown response_format is coerced and still succeeds."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.load_slam_map(map_path="/maps/x.yaml", response_format="weird")

        assert result.success is True


class TestLocalizeRobot:
    """Tests for slam_tools.localize_robot()."""

    def test_localize_succeeds(self):
        """Default method localizes and sets localization state active."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.localize_robot()

        assert result.success is True
        assert slam_tools._localization_state["active"] is True

    def test_localize_all_valid_methods(self):
        """All valid methods return success."""
        valid = ["amcl", "map_matching", "icp"]
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            for method in valid:
                result = slam_tools.localize_robot(method=method)
                assert result.success is True, f"Expected success for method={method}"
                assert result.data["method"] == method

    def test_localize_invalid_method_returns_error(self):
        """Invalid method returns failure with INVALID_METHOD."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.localize_robot(method="ekf")

        assert result.success is False
        assert result.error_code == "INVALID_METHOD"

    def test_localize_data_shape(self):
        """Response contains method, estimated_pose, covariance keys."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.localize_robot(method="amcl")

        for key in ("method", "estimated_pose", "covariance"):
            assert key in result.data
        pose = result.data["estimated_pose"]
        for key in ("x", "y", "theta"):
            assert key in pose
        assert isinstance(result.data["covariance"], list)
        assert len(result.data["covariance"]) in (6, 36)

    def test_localize_uses_initial_pose(self):
        """Initial pose hint is reflected in estimated pose."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.localize_robot(
                method="amcl", initial_pose={"x": 1.5, "y": 2.5, "theta": 0.3}
            )

        assert result.data["estimated_pose"]["x"] == 1.5
        assert result.data["estimated_pose"]["y"] == 2.5
        assert result.data["estimated_pose"]["theta"] == 0.3


class TestGetLocalizationQuality:
    """Tests for slam_tools.get_localization_quality()."""

    def test_quality_succeeds(self):
        """Returns success with a quality rating."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.get_localization_quality()

        assert result.success is True
        assert result.data["quality"] in ("good", "fair", "poor")

    def test_quality_data_shape(self):
        """Response contains particle_spread, match_score, ambiguity, quality."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.get_localization_quality()

        for key in ("particle_spread", "match_score", "ambiguity", "quality"):
            assert key in result.data

    def test_quality_detailed_includes_timestamp(self):
        """Detailed format includes a timestamp."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.get_localization_quality(response_format="detailed")

        assert result.success is True
        assert "timestamp" in result.data

    def test_quality_unknown_format_coerced(self):
        """Unknown response_format is coerced and still succeeds."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.get_localization_quality(response_format="nonsense")

        assert result.success is True


class TestDetectLoopClosure:
    """Tests for slam_tools.detect_loop_closure()."""

    def test_detect_succeeds(self):
        """Returns success with loop_closure_detected boolean."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.detect_loop_closure()

        assert result.success is True
        assert isinstance(result.data["loop_closure_detected"], bool)

    def test_detect_data_shape(self):
        """Response contains loop_closure_detected, candidates, method."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.detect_loop_closure()

        for key in ("loop_closure_detected", "candidates", "method"):
            assert key in result.data
        assert isinstance(result.data["candidates"], list)

    def test_detect_method_is_visual_bag_of_words(self):
        """Detection method is visual_bag_of_words."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.detect_loop_closure()

        assert result.data["method"] == "visual_bag_of_words"

    def test_detect_detailed_includes_candidate_count(self):
        """Detailed format includes candidate_count."""
        with patch.object(slam_tools, "use_real_gazebo", return_value=False):
            result = slam_tools.detect_loop_closure(response_format="detailed")

        assert result.success is True
        assert "candidate_count" in result.data
        assert result.data["candidate_count"] == len(result.data["candidates"])
