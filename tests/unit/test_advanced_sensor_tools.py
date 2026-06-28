"""
Unit tests for advanced_sensor_tools module.

Tests all 8 advanced sensor capability functions in mock mode
(no Gazebo connection required).

Functions covered:
- fuse_sensor_data
- visualize_sensor_data
- process_sensor_data
- calibrate_sensor
- monitor_sensor_health
- record_sensor_stream
- detect_objects_in_view
- segment_camera_image
"""

import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import advanced_sensor_tools


def _reset_state():
    """Clear all module-level state dicts between tests."""
    advanced_sensor_tools._calibrations.clear()
    advanced_sensor_tools._sensor_recordings.clear()


@pytest.fixture(autouse=True)
def reset_module_state():
    """Auto-reset module state before every test."""
    _reset_state()
    yield
    _reset_state()


class TestFuseSensorData:
    """Tests for advanced_sensor_tools.fuse_sensor_data()."""

    def test_fuse_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.fuse_sensor_data(
                fusion_type="lidar_camera", sensors=["lidar_front", "camera_rgb"]
            )
        assert result.success is True
        assert result.data["fusion_type"] == "lidar_camera"
        assert result.data["inputs"] == ["lidar_front", "camera_rgb"]

    def test_fuse_all_valid_types(self):
        valid = ["lidar_camera", "multi_lidar", "imu_gps", "camera_depth"]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for ftype in valid:
                result = advanced_sensor_tools.fuse_sensor_data(fusion_type=ftype, sensors=["a", "b"])
                assert result.success is True, f"Expected success for fusion_type={ftype}"

    def test_fuse_invalid_type_returns_error(self):
        result = advanced_sensor_tools.fuse_sensor_data(fusion_type="magic", sensors=["a"])
        assert result.success is False
        assert result.error_code == "INVALID_FUSION_TYPE"
        assert result.suggestions is not None

    def test_fuse_empty_sensors_returns_error(self):
        result = advanced_sensor_tools.fuse_sensor_data(fusion_type="imu_gps", sensors=[])
        assert result.success is False
        assert result.error_code == "INVALID_SENSORS"

    def test_fuse_data_shape(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.fuse_sensor_data(fusion_type="camera_depth", sensors=["camera_rgb"])
        output = result.data["output"]
        assert "type" in output
        assert "summary" in output
        assert "sample" in output


class TestVisualizeSensorData:
    """Tests for advanced_sensor_tools.visualize_sensor_data()."""

    def test_visualize_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.visualize_sensor_data(
                sensor="lidar_front", visualization_type="point_cloud"
            )
        assert result.success is True
        assert result.data["sensor"] == "lidar_front"
        assert result.data["visualization_type"] == "point_cloud"

    def test_visualize_all_valid_types(self):
        valid = ["point_cloud", "camera_frustum", "imu_arrows", "gps_path", "contact_forces"]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for vtype in valid:
                result = advanced_sensor_tools.visualize_sensor_data(sensor="sensor_a", visualization_type=vtype)
                assert result.success is True, f"Expected success for visualization_type={vtype}"

    def test_visualize_invalid_type_returns_error(self):
        result = advanced_sensor_tools.visualize_sensor_data(sensor="sensor_a", visualization_type="hologram")
        assert result.success is False
        assert result.error_code == "INVALID_VISUALIZATION_TYPE"

    def test_visualize_invalid_sensor_name_returns_error(self):
        result = advanced_sensor_tools.visualize_sensor_data(sensor="123bad", visualization_type="point_cloud")
        assert result.success is False

    def test_visualize_data_shape(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.visualize_sensor_data(sensor="cam", visualization_type="camera_frustum")
        assert "markers" in result.data
        assert isinstance(result.data["markers"], dict)


class TestProcessSensorData:
    """Tests for advanced_sensor_tools.process_sensor_data()."""

    def test_process_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.process_sensor_data(sensor="lidar_front", processing="voxel_filter")
        assert result.success is True
        assert result.data["processing"] == "voxel_filter"

    def test_process_all_valid_types(self):
        valid = [
            "voxel_filter",
            "statistical_filter",
            "image_blur",
            "edge_detection",
            "segmentation",
            "imu_filter",
            "ground_removal",
        ]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for ptype in valid:
                result = advanced_sensor_tools.process_sensor_data(sensor="s", processing=ptype)
                assert result.success is True, f"Expected success for processing={ptype}"

    def test_process_invalid_type_returns_error(self):
        result = advanced_sensor_tools.process_sensor_data(sensor="s", processing="quantum_filter")
        assert result.success is False
        assert result.error_code == "INVALID_PROCESSING"

    def test_process_invalid_sensor_returns_error(self):
        result = advanced_sensor_tools.process_sensor_data(sensor="9bad", processing="voxel_filter")
        assert result.success is False

    def test_process_data_shape_and_params(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.process_sensor_data(
                sensor="lidar_front", processing="voxel_filter", params={"leaf_size": 0.1}
            )
        assert "result" in result.data
        assert result.data["result"]["leaf_size"] == 0.1


class TestCalibrateSensor:
    """Tests for advanced_sensor_tools.calibrate_sensor()."""

    def test_calibrate_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.calibrate_sensor(sensor="camera_rgb", calibration_type="camera_intrinsics")
        assert result.success is True
        assert result.data["calibration_type"] == "camera_intrinsics"

    def test_calibrate_all_valid_types(self):
        valid = ["camera_intrinsics", "camera_extrinsics", "lidar_offset", "imu_bias", "time_sync"]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for ctype in valid:
                result = advanced_sensor_tools.calibrate_sensor(sensor="sensor_a", calibration_type=ctype)
                assert result.success is True, f"Expected success for calibration_type={ctype}"

    def test_calibrate_invalid_type_returns_error(self):
        result = advanced_sensor_tools.calibrate_sensor(sensor="sensor_a", calibration_type="psychic")
        assert result.success is False
        assert result.error_code == "INVALID_CALIBRATION_TYPE"

    def test_calibrate_stores_in_dict(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            advanced_sensor_tools.calibrate_sensor(sensor="imu_sensor", calibration_type="imu_bias")
        assert "imu_sensor" in advanced_sensor_tools._calibrations
        assert advanced_sensor_tools._calibrations["imu_sensor"]["calibration_type"] == "imu_bias"

    def test_calibrate_data_shape_with_overrides(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.calibrate_sensor(
                sensor="camera_rgb", calibration_type="camera_intrinsics", params={"fx": 600.0}
            )
        assert "parameters" in result.data
        assert result.data["parameters"]["fx"] == 600.0


class TestMonitorSensorHealth:
    """Tests for advanced_sensor_tools.monitor_sensor_health()."""

    def test_monitor_all_sensors_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health()
        assert result.success is True
        assert len(result.data["sensors"]) >= 1

    def test_monitor_single_sensor(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health(sensor="lidar_front")
        assert result.success is True
        assert len(result.data["sensors"]) == 1
        assert result.data["sensors"][0]["name"] == "lidar_front"

    def test_monitor_invalid_sensor_name_returns_error(self):
        result = advanced_sensor_tools.monitor_sensor_health(sensor="1bad")
        assert result.success is False

    def test_monitor_per_sensor_shape(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health()
        required = {"name", "data_rate_hz", "latency_ms", "dropout_detected", "quality_score"}
        for entry in result.data["sensors"]:
            missing = required - set(entry.keys())
            assert not missing, f"Sensor health missing keys: {missing}"

    def test_monitor_alerts_present(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health()
        assert "alerts" in result.data
        assert isinstance(result.data["alerts"], list)

    def test_monitor_alerts_fire_for_unhealthy_sensor(self):
        """gps_sensor (dropout + quality 0.72) produces dropout and low-quality alerts."""
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health()
        alerts = result.data["alerts"]
        assert len(alerts) >= 2
        joined = " ".join(alerts)
        assert "gps_sensor" in joined
        assert "dropout" in joined.lower()
        assert "low quality" in joined.lower()

    def test_monitor_alerts_empty_for_healthy_sensor(self):
        """A healthy sensor (lidar_front) produces no alerts."""
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.monitor_sensor_health(sensor="lidar_front")
        assert result.data["alerts"] == []


class TestRecordSensorStream:
    """Tests for advanced_sensor_tools.record_sensor_stream()."""

    def test_record_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.record_sensor_stream(
                sensors=["lidar_front", "camera_rgb"], output_path="/tmp/run1"
            )
        assert result.success is True
        assert result.data["recording_id"].startswith("sensor_recording_")
        assert result.data["output_path"] == "/tmp/run1"

    def test_record_all_valid_compressions(self):
        valid = ["none", "lz4", "zstd"]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for comp in valid:
                result = advanced_sensor_tools.record_sensor_stream(
                    sensors=["s"], output_path="/tmp/r", compression=comp
                )
                assert result.success is True, f"Expected success for compression={comp}"

    def test_record_invalid_compression_returns_error(self):
        result = advanced_sensor_tools.record_sensor_stream(
            sensors=["s"], output_path="/tmp/r", compression="bzip2"
        )
        assert result.success is False
        assert result.error_code == "INVALID_COMPRESSION"

    def test_record_empty_sensors_returns_error(self):
        result = advanced_sensor_tools.record_sensor_stream(sensors=[], output_path="/tmp/r")
        assert result.success is False
        assert result.error_code == "INVALID_SENSORS"

    def test_record_empty_output_path_returns_error(self):
        result = advanced_sensor_tools.record_sensor_stream(sensors=["s"], output_path="")
        assert result.success is False
        assert result.error_code == "INVALID_OUTPUT_PATH"

    def test_record_stores_in_dict(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.record_sensor_stream(sensors=["s"], output_path="/tmp/r")
        rid = result.data["recording_id"]
        assert rid in advanced_sensor_tools._sensor_recordings


class TestDetectObjectsInView:
    """Tests for advanced_sensor_tools.detect_objects_in_view()."""

    def test_detect_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.detect_objects_in_view(camera="camera_rgb")
        assert result.success is True
        assert result.data["camera"] == "camera_rgb"
        assert isinstance(result.data["detections"], list)

    def test_detect_confidence_filters(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            low = advanced_sensor_tools.detect_objects_in_view(camera="camera_rgb", confidence=0.0)
            high = advanced_sensor_tools.detect_objects_in_view(camera="camera_rgb", confidence=0.9)
        assert len(high.data["detections"]) <= len(low.data["detections"])
        for d in high.data["detections"]:
            assert d["confidence"] >= 0.9

    def test_detect_invalid_confidence_returns_error(self):
        result = advanced_sensor_tools.detect_objects_in_view(camera="camera_rgb", confidence=1.5)
        assert result.success is False
        assert result.error_code == "INVALID_CONFIDENCE"

    def test_detect_invalid_camera_name_returns_error(self):
        result = advanced_sensor_tools.detect_objects_in_view(camera="1cam")
        assert result.success is False

    def test_detect_detection_shape(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.detect_objects_in_view(camera="camera_rgb", confidence=0.0)
        required = {"label", "confidence", "bbox", "position"}
        for d in result.data["detections"]:
            missing = required - set(d.keys())
            assert not missing, f"Detection missing keys: {missing}"
            assert set(d["bbox"].keys()) == {"x", "y", "w", "h"}


class TestSegmentCameraImage:
    """Tests for advanced_sensor_tools.segment_camera_image()."""

    def test_segment_valid_succeeds(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.segment_camera_image(camera="camera_rgb")
        assert result.success is True
        assert result.data["mode"] == "semantic"

    def test_segment_all_valid_modes(self):
        valid = ["semantic", "instance"]
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            for mode in valid:
                result = advanced_sensor_tools.segment_camera_image(camera="camera_rgb", mode=mode)
                assert result.success is True, f"Expected success for mode={mode}"

    def test_segment_invalid_mode_returns_error(self):
        result = advanced_sensor_tools.segment_camera_image(camera="camera_rgb", mode="panoptic")
        assert result.success is False
        assert result.error_code == "INVALID_SEGMENT_MODE"

    def test_segment_invalid_camera_name_returns_error(self):
        result = advanced_sensor_tools.segment_camera_image(camera="0cam")
        assert result.success is False

    def test_segment_data_shape(self):
        with patch.object(advanced_sensor_tools, "use_real_gazebo", return_value=False):
            result = advanced_sensor_tools.segment_camera_image(camera="camera_rgb", mode="instance")
        assert "classes" in result.data
        assert "mask_summary" in result.data
        assert isinstance(result.data["classes"], list)
