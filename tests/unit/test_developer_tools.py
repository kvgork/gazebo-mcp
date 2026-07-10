"""
Unit tests for developer_tools module.

Tests all 12 developer experience and debugging functions in mock mode
(no Gazebo connection required).

Functions covered:
- add_debug_marker, clear_debug_markers
- highlight_model
- launch_rviz, add_rviz_visualization
- start_recording, stop_recording, playback_recording
- save_snapshot, restore_snapshot
- profile_simulation, identify_bottlenecks
"""

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import developer_tools


def _reset_state():
    """Clear all module-level state dicts between tests."""
    developer_tools._debug_markers.clear()
    developer_tools._snapshots.clear()
    developer_tools._recording_state.update(
        {
            "active": False,
            "output_path": None,
            "topics": None,
            "compression": None,
            "tags": None,
            "start_time": None,
        }
    )


@pytest.fixture(autouse=True)
def reset_module_state():
    """Auto-reset module state before every test."""
    _reset_state()
    yield
    _reset_state()


class TestAddDebugMarker:
    """Tests for developer_tools.add_debug_marker()."""

    def test_add_valid_marker_returns_marker_id(self):
        """Adding a valid marker type returns success with a marker_id."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.add_debug_marker(marker_type="arrow")

        assert result.success is True
        assert "marker_id" in result.data
        assert result.data["marker_id"].startswith("marker_")

    def test_add_marker_stores_in_dict(self):
        """Marker is stored in module _debug_markers dict."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.add_debug_marker(marker_type="point")

        marker_id = result.data["marker_id"]
        assert marker_id in developer_tools._debug_markers
        assert developer_tools._debug_markers[marker_id]["type"] == "point"

    def test_add_marker_all_valid_types(self):
        """All valid marker types succeed."""
        valid_types = ["line", "arrow", "point", "text", "bounding_box", "trajectory", "force_vector"]
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            for mtype in valid_types:
                result = developer_tools.add_debug_marker(marker_type=mtype)
                assert result.success is True, f"Expected success for marker_type={mtype}"

    def test_add_marker_invalid_type_returns_error(self):
        """Invalid marker type returns a failure result."""
        result = developer_tools.add_debug_marker(marker_type="invalid_type")

        assert result.success is False
        assert result.error_code == "INVALID_MARKER_TYPE"
        assert result.suggestions is not None

    def test_add_marker_with_label_and_color(self):
        """Marker with custom label and color stores them correctly."""
        color = {"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0}
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.add_debug_marker(
                marker_type="text",
                label="Goal",
                color=color,
                scale=2.0,
            )

        assert result.success is True
        marker_id = result.data["marker_id"]
        stored = developer_tools._debug_markers[marker_id]
        assert stored["label"] == "Goal"
        assert stored["scale"] == 2.0

    def test_add_marker_total_count_increments(self):
        """total_markers count reflects number of active markers."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            r1 = developer_tools.add_debug_marker(marker_type="line")
            r2 = developer_tools.add_debug_marker(marker_type="arrow")

        assert r1.data["total_markers"] == 1
        assert r2.data["total_markers"] == 2

    def test_add_marker_invalid_scale_returns_error(self):
        """Negative scale value returns an error."""
        result = developer_tools.add_debug_marker(marker_type="point", scale=-1.0)

        assert result.success is False


class TestClearDebugMarkers:
    """Tests for developer_tools.clear_debug_markers()."""

    def test_clear_specific_marker_removes_it(self):
        """Clearing a specific marker_id removes only that marker."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            r1 = developer_tools.add_debug_marker(marker_type="arrow")
            developer_tools.add_debug_marker(marker_type="line")

        marker_id = r1.data["marker_id"]
        result = developer_tools.clear_debug_markers(marker_id=marker_id)

        assert result.success is True
        assert result.data["removed"] == 1
        assert marker_id not in developer_tools._debug_markers
        assert len(developer_tools._debug_markers) == 1

    def test_clear_all_removes_all_markers(self):
        """Clearing without marker_id removes all markers and returns count."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            developer_tools.add_debug_marker(marker_type="line")
            developer_tools.add_debug_marker(marker_type="point")
            developer_tools.add_debug_marker(marker_type="text")

        result = developer_tools.clear_debug_markers()

        assert result.success is True
        assert result.data["removed"] == 3
        assert result.data["remaining"] == 0
        assert len(developer_tools._debug_markers) == 0

    def test_clear_nonexistent_marker_returns_error(self):
        """Clearing a marker_id that doesn't exist returns failure."""
        result = developer_tools.clear_debug_markers(marker_id="marker_999")

        assert result.success is False
        assert result.error_code == "MARKER_NOT_FOUND"

    def test_clear_all_when_empty_returns_zero(self):
        """Clearing all markers when none exist returns removed=0."""
        result = developer_tools.clear_debug_markers()

        assert result.success is True
        assert result.data["removed"] == 0


class TestHighlightModel:
    """Tests for developer_tools.highlight_model()."""

    def test_highlight_valid_effect_succeeds(self):
        """Valid model name and effect returns success."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.highlight_model(model_name="turtlebot3", effect="glow")

        assert result.success is True
        assert result.data["model_name"] == "turtlebot3"
        assert result.data["effect"] == "glow"

    def test_highlight_all_valid_effects(self):
        """All valid effects return success."""
        valid_effects = ["glow", "outline", "transparency", "color_overlay"]
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            for effect in valid_effects:
                result = developer_tools.highlight_model(model_name="robot1", effect=effect)
                assert result.success is True, f"Expected success for effect={effect}"

    def test_highlight_invalid_effect_returns_error(self):
        """Invalid effect returns a failure result."""
        result = developer_tools.highlight_model(model_name="robot1", effect="sparkle")

        assert result.success is False
        assert result.error_code == "INVALID_HIGHLIGHT_EFFECT"

    def test_highlight_invalid_model_name_returns_error(self):
        """Invalid model name (starts with digit) returns failure."""
        result = developer_tools.highlight_model(model_name="123robot", effect="glow")

        assert result.success is False

    def test_highlight_with_custom_color_and_duration(self):
        """Custom color and duration are stored in response."""
        color = {"r": 1.0, "g": 0.5, "b": 0.0, "a": 0.9}
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.highlight_model(
                model_name="obstacle", effect="color_overlay", color=color, duration=3.0
            )

        assert result.success is True
        assert result.data["duration"] == 3.0
        assert result.data["color"] == color


class TestRecordingStateMachine:
    """Tests for start_recording / stop_recording state machine."""

    def test_start_recording_succeeds(self):
        """Starting a recording sets active state and returns command."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.start_recording(
                topics=["/scan", "/odom"], output_path="test_bag"
            )

        assert result.success is True
        assert result.data["recording"] is True
        assert "command" in result.data
        assert developer_tools._recording_state["active"] is True

    def test_start_recording_twice_returns_error(self):
        """Starting a second recording while one is active returns error."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            developer_tools.start_recording(output_path="first_bag")
            result = developer_tools.start_recording(output_path="second_bag")

        assert result.success is False
        assert result.error_code == "RECORDING_ALREADY_ACTIVE"
        assert result.suggestions is not None

    def test_stop_recording_after_start_succeeds(self):
        """Stopping an active recording returns bag info."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            developer_tools.start_recording(topics=["/scan"], output_path="my_bag")
            result = developer_tools.stop_recording()

        assert result.success is True
        assert result.data["recording"] is False
        assert result.data["output_path"] == "my_bag"
        assert developer_tools._recording_state["active"] is False

    def test_stop_recording_when_inactive_returns_error(self):
        """Stopping when no recording is active returns error."""
        result = developer_tools.stop_recording()

        assert result.success is False
        assert result.error_code == "NO_ACTIVE_RECORDING"

    def test_start_invalid_compression_returns_error(self):
        """Invalid compression value returns error."""
        result = developer_tools.start_recording(compression="bzip2")

        assert result.success is False
        assert result.error_code == "INVALID_COMPRESSION"


class TestSnapshotLifecycle:
    """Tests for save_snapshot / restore_snapshot lifecycle."""

    def test_save_snapshot_succeeds(self):
        """Saving a named snapshot returns success."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.save_snapshot(name="before_test")

        assert result.success is True
        assert "before_test" in developer_tools._snapshots
        assert result.data["name"] == "before_test"
        assert "model_count" in result.data

    def test_restore_snapshot_after_save_succeeds(self):
        """Restoring a saved snapshot returns success with models_restored."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            developer_tools.save_snapshot(name="checkpoint_1")
            result = developer_tools.restore_snapshot(name="checkpoint_1")

        assert result.success is True
        assert result.data["restored"] is True
        assert "models_restored" in result.data

    def test_restore_missing_snapshot_returns_error(self):
        """Restoring a non-existent snapshot returns SNAPSHOT_NOT_FOUND."""
        result = developer_tools.restore_snapshot(name="nonexistent_snapshot")

        assert result.success is False
        assert result.error_code == "SNAPSHOT_NOT_FOUND"
        assert result.suggestions is not None

    def test_save_snapshot_overwrite_allowed(self):
        """Saving with the same name overwrites and notes overwrite in data."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            developer_tools.save_snapshot(name="state_a")
            result = developer_tools.save_snapshot(name="state_a")

        assert result.success is True
        assert result.data["overwritten"] is True

    def test_save_snapshot_with_velocities(self):
        """Snapshot includes velocity data when include_velocities=True."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.save_snapshot(name="with_vel", include_velocities=True)

        assert result.success is True
        stored = developer_tools._snapshots["with_vel"]
        assert stored["include_velocities"] is True
        # Check that at least one model has velocity info:
        model_with_vel = [m for m in stored["models"] if "velocity" in m]
        assert len(model_with_vel) > 0

    def test_save_snapshot_empty_name_returns_error(self):
        """Empty snapshot name returns error."""
        result = developer_tools.save_snapshot(name="")

        assert result.success is False
        assert result.error_code == "INVALID_SNAPSHOT_NAME"


class TestLaunchRviz:
    """Tests for developer_tools.launch_rviz()."""

    def test_launch_rviz_returns_success_with_command(self):
        """launch_rviz returns success with a command and instructions."""
        result = developer_tools.launch_rviz()

        assert result.success is True
        assert "command" in result.data
        assert "instructions" in result.data
        assert "note" in result.data

    def test_launch_rviz_with_config_file(self):
        """launch_rviz with config_file includes file path in command."""
        result = developer_tools.launch_rviz(config_file="/path/to/config.rviz")

        assert result.success is True
        assert "/path/to/config.rviz" in result.data["command"]

    def test_launch_rviz_with_map_includes_map_panel(self):
        """launch_rviz with add_map=True includes Map panel."""
        result = developer_tools.launch_rviz(add_map=True)

        assert result.success is True
        assert any("Map" in p for p in result.data["panels"])

    def test_launch_rviz_without_sensors_excludes_sensor_panels(self):
        """launch_rviz with add_sensors=False excludes sensor panels."""
        result = developer_tools.launch_rviz(add_sensors=False)

        assert result.success is True
        panel_names = " ".join(result.data["panels"])
        assert "LaserScan" not in panel_names
        assert "Camera" not in panel_names


class TestAddRvizVisualization:
    """Tests for developer_tools.add_rviz_visualization()."""

    def test_add_laser_scan_visualization_succeeds(self):
        """Adding a laser_scan visualization returns success with plugin."""
        result = developer_tools.add_rviz_visualization(
            visualization_type="laser_scan", topic="/scan"
        )

        assert result.success is True
        assert "plugin" in result.data
        assert "instructions" in result.data
        assert result.data["topic"] == "/scan"

    def test_add_all_valid_visualization_types(self):
        """All valid visualization types succeed."""
        valid_types = ["point_cloud", "marker", "trajectory", "map", "laser_scan", "image"]
        for vtype in valid_types:
            result = developer_tools.add_rviz_visualization(
                visualization_type=vtype, topic="/test_topic"
            )
            assert result.success is True, f"Expected success for visualization_type={vtype}"

    def test_add_invalid_visualization_type_returns_error(self):
        """Invalid visualization type returns error."""
        result = developer_tools.add_rviz_visualization(
            visualization_type="hologram", topic="/scan"
        )

        assert result.success is False
        assert result.error_code == "INVALID_VIZ_TYPE"

    def test_add_visualization_with_name(self):
        """Custom name is reflected in the response data."""
        result = developer_tools.add_rviz_visualization(
            visualization_type="image", topic="/camera/image_raw", name="Front Camera"
        )

        assert result.success is True
        assert result.data["name"] == "Front Camera"


class TestPlaybackRecording:
    """Tests for developer_tools.playback_recording()."""

    def test_playback_returns_command(self):
        """playback_recording returns success with a ros2 bag play command."""
        result = developer_tools.playback_recording(bag_path="my_bag")

        assert result.success is True
        assert "command" in result.data
        assert "my_bag" in result.data["command"]

    def test_playback_with_rate_includes_rate_flag(self):
        """Playback rate is included in the command."""
        result = developer_tools.playback_recording(bag_path="my_bag", rate=0.5)

        assert result.success is True
        assert "0.5" in result.data["command"]

    def test_playback_with_loop_includes_loop_flag(self):
        """Loop flag is included in the command when loop=True."""
        result = developer_tools.playback_recording(bag_path="my_bag", loop=True)

        assert result.success is True
        assert "--loop" in result.data["command"]

    def test_playback_empty_bag_path_returns_error(self):
        """Empty bag_path returns an error."""
        result = developer_tools.playback_recording(bag_path="")

        assert result.success is False
        assert result.error_code == "INVALID_BAG_PATH"

    def test_playback_invalid_rate_returns_error(self):
        """Non-positive rate returns an error."""
        result = developer_tools.playback_recording(bag_path="my_bag", rate=0.0)

        assert result.success is False


class TestProfileSimulation:
    """Tests for developer_tools.profile_simulation()."""

    def test_profile_returns_expected_metric_keys(self):
        """profile_simulation returns success with all expected metric keys."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.profile_simulation()

        assert result.success is True
        data = result.data
        assert "real_time_factor" in data
        assert "physics_step_time_ms" in data
        assert "rendering_fps" in data
        assert "memory_mb" in data

    def test_profile_detailed_includes_sensor_rates(self):
        """Detailed format includes per-sensor update rates."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.profile_simulation(duration=2.0, response_format="detailed")

        assert result.success is True
        assert "sensor_update_rates" in result.data
        assert isinstance(result.data["sensor_update_rates"], dict)

    def test_profile_invalid_duration_returns_error(self):
        """Non-positive duration returns an error."""
        result = developer_tools.profile_simulation(duration=0.0)

        assert result.success is False

    def test_profile_concise_includes_status(self):
        """Concise format includes a status field."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.profile_simulation(response_format="concise")

        assert result.success is True
        assert "status" in result.data


class TestIdentifyBottlenecks:
    """Tests for developer_tools.identify_bottlenecks()."""

    def test_identify_returns_success_with_bottlenecks(self):
        """identify_bottlenecks returns success with a bottleneck list."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.identify_bottlenecks()

        assert result.success is True
        assert "bottlenecks" in result.data
        assert "bottleneck_count" in result.data

    def test_identify_concise_filters_low_severity(self):
        """Concise mode filters out 'none'/'low' severity items."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.identify_bottlenecks(response_format="concise")

        assert result.success is True
        for b in result.data["bottlenecks"]:
            assert b["severity"] not in ("none", "low")

    def test_identify_summary_returns_all_components(self):
        """Summary mode returns all components including healthy ones."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.identify_bottlenecks(response_format="summary")

        assert result.success is True
        assert result.data["bottleneck_count"] >= 1

    def test_identify_each_bottleneck_has_required_keys(self):
        """Each bottleneck has rank, component, metric, severity, and suggestion."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.identify_bottlenecks(response_format="summary")

        required_keys = {"rank", "component", "metric", "severity", "suggestion"}
        for b in result.data["bottlenecks"]:
            missing = required_keys - set(b.keys())
            assert not missing, f"Bottleneck missing keys: {missing}"

    def test_identify_returns_timestamp(self):
        """Result includes a timestamp field."""
        with patch.object(developer_tools, "use_real_gazebo", return_value=False):
            result = developer_tools.identify_bottlenecks()

        assert result.success is True
        assert "timestamp" in result.data
