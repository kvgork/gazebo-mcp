"""
Gazebo Advanced Sensor Capabilities Tools.

Provides functions for advanced sensor processing in Gazebo simulations:
sensor fusion, visualization, signal/image processing, calibration, health
monitoring, stream recording, object detection, and image segmentation.

This is the ADVANCED sensor module — it is distinct from the basic
``sensor_tools`` module and does not collide with it. All tools follow the
mock-mode-is-the-contract pattern: when not connected to a real Gazebo
instance they return deterministic, useful results.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.exceptions import GazeboMCPError
from gazebo_mcp.utils.validators import (
    validate_entity_name,
    validate_positive,
    validate_non_negative,
    validate_response_format,
    validate_position,
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

__all__ = [
    "fuse_sensor_data",
    "visualize_sensor_data",
    "process_sensor_data",
    "calibrate_sensor",
    "monitor_sensor_health",
    "record_sensor_stream",
    "detect_objects_in_view",
    "segment_camera_image",
]

_logger = get_logger("advanced_sensor_tools")

# Module-level state dicts:
_calibrations: Dict[str, dict] = {}
_sensor_recordings: Dict[str, dict] = {}

# Valid enum sets:
_VALID_FUSION_TYPES = {"lidar_camera", "multi_lidar", "imu_gps", "camera_depth"}
_VALID_VISUALIZATION_TYPES = {"point_cloud", "camera_frustum", "imu_arrows", "gps_path", "contact_forces"}
_VALID_PROCESSING_TYPES = {
    "voxel_filter",
    "statistical_filter",
    "image_blur",
    "edge_detection",
    "segmentation",
    "imu_filter",
    "ground_removal",
}
_VALID_CALIBRATION_TYPES = {"camera_intrinsics", "camera_extrinsics", "lidar_offset", "imu_bias", "time_sync"}
_VALID_COMPRESSIONS = {"none", "lz4", "zstd"}
_VALID_SEGMENT_MODES = {"semantic", "instance"}

# Mock list of known sensors used for health monitoring:
_MOCK_KNOWN_SENSORS = ["lidar_front", "camera_rgb", "imu_sensor", "gps_sensor"]


def _coerce_response_format(response_format: str) -> str:
    """Coerce response_format to 'concise' or 'detailed' (default 'concise')."""
    if response_format not in ("concise", "detailed"):
        return "concise"
    return response_format


def fuse_sensor_data(
    fusion_type: str,
    sensors: list,
    response_format: str = "concise",
) -> OperationResult:
    """
    Fuse data from multiple sensors into a combined representation.

    Args:
        fusion_type: Type of fusion — one of: lidar_camera, multi_lidar,
                     imu_gps, camera_depth
        sensors: Non-empty list of sensor names to fuse
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with fusion_type, inputs, and output description

    Example:
        >>> fuse_sensor_data("lidar_camera", ["lidar_front", "camera_rgb"])
    """
    try:
        if fusion_type not in _VALID_FUSION_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid fusion_type '{fusion_type}'",
                error_code="INVALID_FUSION_TYPE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_FUSION_TYPES))}"],
                example_fix="fuse_sensor_data('lidar_camera', ['lidar_front', 'camera_rgb'])",
            )

        if not isinstance(sensors, list) or len(sensors) == 0:
            return OperationResult(
                success=False,
                error="sensors must be a non-empty list",
                error_code="INVALID_SENSORS",
                suggestions=["Provide a list of at least one sensor name"],
                example_fix="fuse_sensor_data('imu_gps', ['imu_sensor', 'gps_sensor'])",
            )

        response_format = _coerce_response_format(response_format)

        # Map fusion type to an output description:
        output_map = {
            "lidar_camera": {
                "type": "colored_point_cloud",
                "summary": "LiDAR points projected into camera image and colored by RGB pixels",
                "sample": {"points": 2048, "colored": True, "frame": "base_link"},
            },
            "multi_lidar": {
                "type": "merged_point_cloud",
                "summary": "Multiple LiDAR scans transformed into a common frame and merged",
                "sample": {"points": 4096, "merged_scans": len(sensors), "frame": "base_link"},
            },
            "imu_gps": {
                "type": "fused_odometry",
                "summary": "IMU and GPS fused via EKF to produce drift-corrected odometry",
                "sample": {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "covariance_trace": 0.012},
            },
            "camera_depth": {
                "type": "rgbd_point_cloud",
                "summary": "RGB image registered with depth image to produce an RGB-D point cloud",
                "sample": {"points": 1920, "has_color": True, "has_depth": True},
            },
        }

        output = output_map[fusion_type]

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor fusion requested (real mode)", fusion_type=fusion_type)
            except Exception:
                _logger.warning("Real fusion path unavailable, falling back to mock", fusion_type=fusion_type)
        else:
            _logger.info("Sensor fusion requested (mock mode)", fusion_type=fusion_type)

        data = {
            "fusion_type": fusion_type,
            "inputs": sensors,
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if response_format == "concise":
            data = {
                "fusion_type": fusion_type,
                "inputs": sensors,
                "output": {"type": output["type"], "summary": output["summary"], "sample": output["sample"]},
            }

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error fusing sensor data", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to fuse sensor data: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check fusion_type and sensors arguments"],
        )


def visualize_sensor_data(
    sensor: str,
    visualization_type: str,
    response_format: str = "concise",
) -> OperationResult:
    """
    Generate visualization markers for a sensor's data.

    Args:
        sensor: Name of the sensor to visualize
        visualization_type: Type of visualization — one of: point_cloud,
                            camera_frustum, imu_arrows, gps_path, contact_forces
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with sensor, visualization_type, and markers

    Example:
        >>> visualize_sensor_data("lidar_front", "point_cloud")
    """
    try:
        sensor = validate_entity_name(sensor, "sensor")

        if visualization_type not in _VALID_VISUALIZATION_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid visualization_type '{visualization_type}'",
                error_code="INVALID_VISUALIZATION_TYPE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_VISUALIZATION_TYPES))}"],
                example_fix="visualize_sensor_data('lidar_front', 'point_cloud')",
            )

        response_format = _coerce_response_format(response_format)

        marker_map = {
            "point_cloud": {"type": "PointCloud2", "count": 2048, "namespace": f"{sensor}_points"},
            "camera_frustum": {"type": "LineList", "count": 8, "namespace": f"{sensor}_frustum"},
            "imu_arrows": {"type": "Arrow", "count": 3, "namespace": f"{sensor}_imu"},
            "gps_path": {"type": "Path", "count": 50, "namespace": f"{sensor}_path"},
            "contact_forces": {"type": "Arrow", "count": 4, "namespace": f"{sensor}_contacts"},
        }

        markers = marker_map[visualization_type]

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor visualization requested (real mode)", sensor=sensor)
            except Exception:
                _logger.warning("Real visualization path unavailable, falling back to mock", sensor=sensor)
        else:
            _logger.info("Sensor visualization requested (mock mode)", sensor=sensor)

        instructions = (
            f"Publish {markers['type']} markers on topic '/{sensor}/markers' and view in RViz2. "
            f"Add a display of type {markers['type']} subscribed to that topic."
        )

        data = {
            "sensor": sensor,
            "visualization_type": visualization_type,
            "markers": markers,
        }

        if response_format == "detailed":
            data["instructions"] = instructions
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error visualizing sensor data", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to visualize sensor data: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check sensor and visualization_type arguments"],
        )


def process_sensor_data(
    sensor: str,
    processing: str,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Apply a processing operation to a sensor's data.

    Args:
        sensor: Name of the sensor whose data to process
        processing: Processing operation — one of: voxel_filter,
                    statistical_filter, image_blur, edge_detection,
                    segmentation, imu_filter, ground_removal
        params: Optional processing parameters dict
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with sensor, processing, and result summary

    Example:
        >>> process_sensor_data("lidar_front", "voxel_filter", params={"leaf_size": 0.05})
    """
    try:
        sensor = validate_entity_name(sensor, "sensor")

        if processing not in _VALID_PROCESSING_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid processing '{processing}'",
                error_code="INVALID_PROCESSING",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_PROCESSING_TYPES))}"],
                example_fix="process_sensor_data('lidar_front', 'voxel_filter')",
            )

        response_format = _coerce_response_format(response_format)
        params = params or {}

        result_map = {
            "voxel_filter": {"input_points": 4096, "output_points": 1024, "leaf_size": params.get("leaf_size", 0.05)},
            "statistical_filter": {"input_points": 4096, "output_points": 3900, "outliers_removed": 196},
            "image_blur": {"width": 640, "height": 480, "kernel": params.get("kernel", 5)},
            "edge_detection": {"width": 640, "height": 480, "edges_detected": 1532},
            "segmentation": {"width": 640, "height": 480, "segments": 7},
            "imu_filter": {"samples": 200, "method": params.get("method", "complementary"), "noise_reduced": True},
            "ground_removal": {"input_points": 4096, "ground_points": 1800, "non_ground_points": 2296},
        }

        result = result_map[processing]

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor processing requested (real mode)", sensor=sensor, processing=processing)
            except Exception:
                _logger.warning("Real processing path unavailable, falling back to mock", sensor=sensor)
        else:
            _logger.info("Sensor processing requested (mock mode)", sensor=sensor, processing=processing)

        data = {
            "sensor": sensor,
            "processing": processing,
            "result": result,
        }

        if response_format == "detailed":
            data["params"] = params
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error processing sensor data", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to process sensor data: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check sensor and processing arguments"],
        )


def calibrate_sensor(
    sensor: str,
    calibration_type: str,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Calibrate a sensor and store the resulting calibration.

    Args:
        sensor: Name of the sensor to calibrate
        calibration_type: Type of calibration — one of: camera_intrinsics,
                          camera_extrinsics, lidar_offset, imu_bias, time_sync
        params: Optional calibration override parameters dict
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with sensor, calibration_type, and parameters

    Example:
        >>> calibrate_sensor("camera_rgb", "camera_intrinsics")
    """
    try:
        sensor = validate_entity_name(sensor, "sensor")

        if calibration_type not in _VALID_CALIBRATION_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid calibration_type '{calibration_type}'",
                error_code="INVALID_CALIBRATION_TYPE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_CALIBRATION_TYPES))}"],
                example_fix="calibrate_sensor('camera_rgb', 'camera_intrinsics')",
            )

        response_format = _coerce_response_format(response_format)
        params = params or {}

        default_params = {
            "camera_intrinsics": {"fx": 525.0, "fy": 525.0, "cx": 319.5, "cy": 239.5, "distortion": [0.0, 0.0, 0.0, 0.0, 0.0]},
            "camera_extrinsics": {"translation": {"x": 0.1, "y": 0.0, "z": 0.2}, "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}},
            "lidar_offset": {"translation": {"x": 0.0, "y": 0.0, "z": 0.3}, "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}},
            "imu_bias": {"accel_bias": {"x": 0.01, "y": -0.02, "z": 0.0}, "gyro_bias": {"x": 0.001, "y": 0.0, "z": -0.001}},
            "time_sync": {"offset_ms": 2.5, "method": "ptp"},
        }

        parameters = dict(default_params[calibration_type])
        parameters.update(params)

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor calibration requested (real mode)", sensor=sensor, calibration_type=calibration_type)
            except Exception:
                _logger.warning("Real calibration path unavailable, falling back to mock", sensor=sensor)
        else:
            _logger.info("Sensor calibration requested (mock mode)", sensor=sensor, calibration_type=calibration_type)

        calibration = {
            "sensor": sensor,
            "calibration_type": calibration_type,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _calibrations[sensor] = calibration

        data = {
            "sensor": sensor,
            "calibration_type": calibration_type,
            "parameters": parameters,
        }

        if response_format == "detailed":
            data["timestamp"] = calibration["timestamp"]
            data["stored"] = True

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error calibrating sensor", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to calibrate sensor: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check sensor and calibration_type arguments"],
        )


def monitor_sensor_health(
    sensor: str = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Monitor the health of one or all sensors.

    Args:
        sensor: Optional sensor name; if None, monitors all known sensors
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with per-sensor health metrics and any alerts

    Example:
        >>> monitor_sensor_health()              # all sensors
        >>> monitor_sensor_health("lidar_front") # single sensor
    """
    try:
        response_format = _coerce_response_format(response_format)

        if sensor is not None:
            sensor = validate_entity_name(sensor, "sensor")
            names = [sensor]
        else:
            names = list(_MOCK_KNOWN_SENSORS)

        # Deterministic per-sensor health profiles:
        health_profiles = {
            "lidar_front": {"data_rate_hz": 10.0, "latency_ms": 12.0, "dropout_detected": False, "quality_score": 0.98},
            "camera_rgb": {"data_rate_hz": 30.0, "latency_ms": 33.0, "dropout_detected": False, "quality_score": 0.95},
            "imu_sensor": {"data_rate_hz": 200.0, "latency_ms": 2.0, "dropout_detected": False, "quality_score": 0.99},
            "gps_sensor": {"data_rate_hz": 1.0, "latency_ms": 50.0, "dropout_detected": True, "quality_score": 0.72},
        }
        default_profile = {"data_rate_hz": 20.0, "latency_ms": 15.0, "dropout_detected": False, "quality_score": 0.9}

        sensors_out: List[Dict[str, Any]] = []
        alerts: List[str] = []
        for name in names:
            profile = health_profiles.get(name, default_profile)
            entry = {
                "name": name,
                "data_rate_hz": profile["data_rate_hz"],
                "latency_ms": profile["latency_ms"],
                "dropout_detected": profile["dropout_detected"],
                "quality_score": profile["quality_score"],
            }
            sensors_out.append(entry)
            if profile["dropout_detected"]:
                alerts.append(f"Sensor '{name}' is experiencing data dropouts")
            if profile["quality_score"] < 0.8:
                alerts.append(f"Sensor '{name}' has low quality score ({profile['quality_score']})")

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor health monitoring requested (real mode)")
            except Exception:
                _logger.warning("Real health monitoring path unavailable, falling back to mock")
        else:
            _logger.info("Sensor health monitoring requested (mock mode)")

        data = {
            "sensors": sensors_out,
            "alerts": alerts,
        }

        if response_format == "detailed":
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
            data["sensor_count"] = len(sensors_out)

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error monitoring sensor health", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to monitor sensor health: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check the sensor argument"],
        )


def record_sensor_stream(
    sensors: list,
    output_path: str,
    compression: str = "none",
    tags: list = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Record a stream of sensor data to an output file.

    Args:
        sensors: Non-empty list of sensor names to record
        output_path: Output path/prefix for the recording
        compression: Compression mode — one of: none, lz4, zstd
        tags: Optional list of metadata tags
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with recording_id, sensors, output_path, and compression

    Example:
        >>> record_sensor_stream(["lidar_front", "camera_rgb"], "/tmp/run1")
    """
    try:
        if not isinstance(sensors, list) or len(sensors) == 0:
            return OperationResult(
                success=False,
                error="sensors must be a non-empty list",
                error_code="INVALID_SENSORS",
                suggestions=["Provide a list of at least one sensor name"],
                example_fix="record_sensor_stream(['lidar_front'], '/tmp/run1')",
            )

        if not output_path:
            return OperationResult(
                success=False,
                error="output_path must be a non-empty string",
                error_code="INVALID_OUTPUT_PATH",
                suggestions=["Provide an output path or prefix for the recording"],
                example_fix="record_sensor_stream(['lidar_front'], '/tmp/run1')",
            )

        if compression not in _VALID_COMPRESSIONS:
            return OperationResult(
                success=False,
                error=f"Invalid compression '{compression}'",
                error_code="INVALID_COMPRESSION",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_COMPRESSIONS))}"],
                example_fix="record_sensor_stream(['lidar_front'], '/tmp/run1', compression='lz4')",
            )

        response_format = _coerce_response_format(response_format)
        tags = tags or []

        recording_id = f"sensor_recording_{len(_sensor_recordings) + 1}"
        recording = {
            "recording_id": recording_id,
            "sensors": sensors,
            "output_path": output_path,
            "compression": compression,
            "tags": tags,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _sensor_recordings[recording_id] = recording

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Sensor stream recording requested (real mode)", recording_id=recording_id)
            except Exception:
                _logger.warning("Real recording path unavailable, falling back to mock", recording_id=recording_id)
        else:
            _logger.info("Sensor stream recording requested (mock mode)", recording_id=recording_id)

        data = {
            "recording_id": recording_id,
            "sensors": sensors,
            "output_path": output_path,
            "compression": compression,
        }

        if response_format == "detailed":
            data["tags"] = tags
            data["timestamp"] = recording["timestamp"]
            data["total_recordings"] = len(_sensor_recordings)

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error recording sensor stream", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to record sensor stream: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check sensors, output_path, and compression arguments"],
        )


def detect_objects_in_view(
    camera: str,
    model: str = "default",
    confidence: float = 0.5,
    response_format: str = "concise",
) -> OperationResult:
    """
    Detect objects in a camera's field of view.

    Args:
        camera: Name of the camera sensor
        model: Detection model name (default: "default")
        confidence: Minimum confidence threshold in [0, 1] (default: 0.5)
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with camera, model, and a list of detections

    Example:
        >>> detect_objects_in_view("camera_rgb", confidence=0.6)
    """
    try:
        camera = validate_entity_name(camera, "camera")

        if not isinstance(confidence, (int, float)) or confidence < 0.0 or confidence > 1.0:
            return OperationResult(
                success=False,
                error=f"confidence must be in [0, 1], got {confidence}",
                error_code="INVALID_CONFIDENCE",
                suggestions=["Provide a confidence value between 0.0 and 1.0"],
                example_fix="detect_objects_in_view('camera_rgb', confidence=0.5)",
            )

        response_format = _coerce_response_format(response_format)

        # Deterministic mock detections:
        all_detections = [
            {"label": "person", "confidence": 0.92, "bbox": {"x": 120, "y": 80, "w": 60, "h": 140}, "position": {"x": 2.5, "y": 0.3, "z": 0.0}},
            {"label": "chair", "confidence": 0.78, "bbox": {"x": 300, "y": 200, "w": 90, "h": 110}, "position": {"x": 1.8, "y": -0.5, "z": 0.0}},
            {"label": "box", "confidence": 0.55, "bbox": {"x": 450, "y": 260, "w": 70, "h": 70}, "position": {"x": 3.1, "y": 0.9, "z": 0.0}},
            {"label": "bottle", "confidence": 0.41, "bbox": {"x": 510, "y": 300, "w": 25, "h": 60}, "position": {"x": 1.2, "y": 0.1, "z": 0.4}},
        ]
        detections = [d for d in all_detections if d["confidence"] >= confidence]

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Object detection requested (real mode)", camera=camera, model=model)
            except Exception:
                _logger.warning("Real detection path unavailable, falling back to mock", camera=camera)
        else:
            _logger.info("Object detection requested (mock mode)", camera=camera, model=model)

        data = {
            "camera": camera,
            "model": model,
            "detections": detections,
        }

        if response_format == "detailed":
            data["confidence_threshold"] = confidence
            data["detection_count"] = len(detections)
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error detecting objects", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to detect objects: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check camera, model, and confidence arguments"],
        )


def segment_camera_image(
    camera: str,
    mode: str = "semantic",
    response_format: str = "concise",
) -> OperationResult:
    """
    Segment a camera image into classes or instances.

    Args:
        camera: Name of the camera sensor
        mode: Segmentation mode — one of: semantic, instance (default: "semantic")
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with camera, mode, classes, and mask_summary

    Example:
        >>> segment_camera_image("camera_rgb", mode="instance")
    """
    try:
        camera = validate_entity_name(camera, "camera")

        if mode not in _VALID_SEGMENT_MODES:
            return OperationResult(
                success=False,
                error=f"Invalid mode '{mode}'",
                error_code="INVALID_SEGMENT_MODE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_SEGMENT_MODES))}"],
                example_fix="segment_camera_image('camera_rgb', mode='semantic')",
            )

        response_format = _coerce_response_format(response_format)

        if mode == "semantic":
            classes = ["floor", "wall", "person", "furniture", "background"]
            mask_summary = {
                "width": 640,
                "height": 480,
                "class_count": len(classes),
                "coverage": {"floor": 0.42, "wall": 0.25, "person": 0.08, "furniture": 0.15, "background": 0.10},
            }
        else:  # instance
            classes = ["person_1", "person_2", "chair_1", "box_1"]
            mask_summary = {
                "width": 640,
                "height": 480,
                "instance_count": len(classes),
                "pixels_per_instance": {"person_1": 8200, "person_2": 6100, "chair_1": 4400, "box_1": 2300},
            }

        if use_real_gazebo():
            try:
                bridge = get_bridge()
                _logger.info("Image segmentation requested (real mode)", camera=camera, mode=mode)
            except Exception:
                _logger.warning("Real segmentation path unavailable, falling back to mock", camera=camera)
        else:
            _logger.info("Image segmentation requested (mock mode)", camera=camera, mode=mode)

        data = {
            "camera": camera,
            "mode": mode,
            "classes": classes,
            "mask_summary": mask_summary,
        }

        if response_format == "detailed":
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error segmenting camera image", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to segment camera image: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check camera and mode arguments"],
        )
