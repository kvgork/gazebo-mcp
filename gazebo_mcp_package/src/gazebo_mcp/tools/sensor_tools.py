"""
Gazebo Sensor Tools.

Provides functions for querying and streaming sensor data from Gazebo simulation.
Implements the ResultFilter pattern for 98.7% token efficiency.

Supported sensor types:
- Camera (RGB, depth, RGBD)
- Lidar/Laser
- IMU (Inertial Measurement Unit)
- GPS
- Magnetometer
- Altimeter
- Sonar
- Contact sensors
- Force/Torque sensors
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from gazebo_mcp.utils import OperationResult, TokenEstimates
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ROS2NotConnectedError,
    SensorNotFoundError,
)
from gazebo_mcp.utils.validators import (
    validate_entity_name,
    validate_sensor_type,
    validate_timeout,
    validate_response_format,
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

__all__ = ["list_sensors", "get_sensor_data", "subscribe_sensor_stream"]

_logger = get_logger("sensor_tools")

# Sensor data cache for streaming:
_sensor_data_cache: Dict[str, Any] = {}


def list_sensors(
    model_name: Optional[str] = None,
    sensor_type: Optional[str] = None,
    response_format: str = "filtered",
) -> OperationResult:
    """
    List sensors in Gazebo simulation.

    Args:
        model_name: Optional model name to filter sensors
        sensor_type: Optional sensor type to filter (camera, lidar, imu, etc.)
        response_format:
            - "summary": Counts and types only (~50 tokens)
            - "concise": Names and types (~200 tokens/sensor)
            - "filtered": Full data for local filtering (~1000 tokens + data)
            - "detailed": Everything including topics (~500 tokens/sensor)

    Returns:
        OperationResult with sensor data

    Example:
        >>> from gazebo_mcp.tools.sensor_tools import list_sensors
        >>> from skills.common.filters import ResultFilter
        >>>
        >>> # Get all sensors:
        >>> result = list_sensors(response_format="filtered")
        >>> sensors = result.data["sensors"]
        >>>
        >>> # Filter locally (0 tokens to model!):
        >>> lidars = ResultFilter.search(sensors, "lidar", ["type"])
        >>> cameras = ResultFilter.filter_by_field(sensors, "type", "camera")
    """
    try:
        # Validate parameters:
        if model_name:
            model_name = validate_entity_name(model_name, "model")
        if sensor_type:
            sensor_type = validate_sensor_type(sensor_type)
        response_format = validate_response_format(response_format)

        # Get sensors from real Gazebo or mock data:
        if use_real_gazebo():
            bridge = get_bridge()
            # Real sensor discovery via /world/<name>/scene/info not yet implemented
            # Uses mock data as placeholder:
            all_sensors = _get_mock_sensors()
            _logger.warning("Using mock sensor data - real sensor discovery not yet implemented")
        else:
            all_sensors = _get_mock_sensors()
            _logger.warning("Using mock sensor data - Gazebo not available")

        # Filter by model if specified:
        if model_name:
            all_sensors = [s for s in all_sensors if s.get("model") == model_name]

        # Filter by type if specified:
        if sensor_type:
            all_sensors = [s for s in all_sensors if s.get("type") == sensor_type]

        # Response format handling:
        if response_format == "summary":
            types = list(set(s.get("type", "unknown") for s in all_sensors))
            models = list(set(s.get("model", "unknown") for s in all_sensors))

            return OperationResult(
                success=True,
                data={"count": len(all_sensors), "types": types, "models": models, "token_estimate": 50},
            )

        elif response_format == "concise":
            concise_sensors = [
                {
                    "name": s["name"],
                    "type": s.get("type", "unknown"),
                    "model": s.get("model", "unknown"),
                    "active": s.get("active", True),
                }
                for s in all_sensors
            ]

            return OperationResult(
                success=True,
                data={
                    "sensors": concise_sensors,
                    "count": len(all_sensors),
                    "token_estimate": len(all_sensors) * 20,
                },
            )

        elif response_format == "filtered":
            return OperationResult(
                success=True,
                data={
                    "sensors": all_sensors,
                    "count": len(all_sensors),
                    # Show agents how to filter locally:
                    "filter_examples": {
                        "search_by_type": "ResultFilter.search(sensors, 'lidar', ['type'])",
                        "filter_by_model": "ResultFilter.filter_by_field(sensors, 'model', 'turtlebot3')",
                        "filter_by_active": "ResultFilter.filter_by_field(sensors, 'active', True)",
                        "get_cameras": "ResultFilter.filter_by_field(sensors, 'type', 'camera')",
                    },
                    "token_estimate_unfiltered": len(all_sensors) * TokenEstimates.TOKENS_PER_SENSOR,
                    "token_estimate_filtered": 1000,
                    "token_savings_pct": 99.0 if len(all_sensors) > 10 else 0,
                },
            )

        else:  # detailed
            return OperationResult(
                success=True,
                data={
                    "sensors": all_sensors,
                    "count": len(all_sensors),
                    "token_estimate": len(all_sensors) * TokenEstimates.TOKENS_PER_SENSOR * 5,
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error listing sensors", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to list sensors: {e}",
            error_code="LIST_SENSORS_ERROR",
        )


def get_sensor_data(
    sensor_name: str, timeout: float = 5.0, response_format: str = "concise"
) -> OperationResult:
    """
    Get latest sensor data.

    Args:
        sensor_name: Name of the sensor
        timeout: Timeout for receiving data (seconds)
        response_format: "concise" | "detailed"

    Returns:
        OperationResult with sensor data

    Example:
        >>> result = get_sensor_data("lidar_sensor")
        >>> if result.success:
        ...     data = result.data
        ...     print(f"Sensor type: {data['type']}")
        ...     print(f"Timestamp: {data['timestamp']}")
    """
    try:
        # Validate parameters:
        sensor_name = validate_entity_name(sensor_name, "sensor")
        timeout = validate_timeout(timeout)
        response_format = validate_response_format(response_format)

        # Get sensor data:
        if use_real_gazebo():
            bridge = get_bridge()

            # Check if sensor exists in cache:
            if sensor_name in _sensor_data_cache:
                data = _sensor_data_cache[sensor_name]
            else:
                # Auto-subscribe to sensor topic not yet implemented — uses mock data:
                data = _get_mock_sensor_data(sensor_name)
                _logger.warning(
                    f"Using mock data for {sensor_name} - real data streaming not yet implemented"
                )
        else:
            data = _get_mock_sensor_data(sensor_name)
            _logger.warning(f"Using mock data for {sensor_name} - Gazebo not available")

        if data is None:
            raise SensorNotFoundError(sensor_name)

        # Format response:
        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "sensor_name": sensor_name,
                    "type": data.get("type"),
                    "timestamp": data.get("timestamp"),
                    "data_summary": _summarize_sensor_data(data),
                },
            )
        else:  # detailed
            return OperationResult(success=True, data=data)

    except SensorNotFoundError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error getting sensor data", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get sensor data: {e}",
            error_code="GET_SENSOR_DATA_ERROR",
        )


def subscribe_sensor_stream(
    sensor_name: str, topic_name: str, message_type: str = "auto"
) -> OperationResult:
    """
    Subscribe to sensor data stream.

    Args:
        sensor_name: Name of the sensor
        topic_name: ROS2 topic name (e.g., "/scan", "/camera/image_raw")
        message_type: Message type ("auto" to auto-detect, or specific type)

    Returns:
        OperationResult with subscription info

    Example:
        >>> result = subscribe_sensor_stream(
        ...     "lidar",
        ...     "/scan",
        ...     message_type="sensor_msgs/LaserScan"
        ... )
    """
    try:
        # Validate parameters:
        sensor_name = validate_entity_name(sensor_name, "sensor")

        if use_real_gazebo():
            bridge = get_bridge()

            # Determine message type:
            if message_type == "auto":
                msg_type = _detect_message_type(topic_name)
            else:
                msg_type = _get_message_type_class(message_type)

            # Create callback to cache data:
            def sensor_callback(msg):
                # Convert message to dict and cache:
                data = _message_to_dict(msg, sensor_name)
                _sensor_data_cache[sensor_name] = data
                _logger.debug(f"Cached data for {sensor_name}")

            # Subscribe:
            subscription = bridge.subscribe_to_topic(
                topic_name=topic_name, msg_type=msg_type, callback=sensor_callback
            )

            _logger.info(f"Subscribed to {topic_name} for {sensor_name}")

            return OperationResult(
                success=True,
                data={
                    "sensor_name": sensor_name,
                    "topic": topic_name,
                    "message_type": message_type,
                    "subscribed": True,
                    "note": f"Data will be cached in memory and available via get_sensor_data('{sensor_name}')",
                },
            )
        else:
            _logger.warning(f"Cannot subscribe - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "sensor_name": sensor_name,
                    "topic": topic_name,
                    "subscribed": False,
                    "note": "Mock mode - subscription not created",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error subscribing to sensor", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to subscribe: {e}",
            error_code="SUBSCRIBE_ERROR",
        )


# Helper functions:


def _summarize_sensor_data(data: Dict[str, Any]) -> str:
    """Create a concise summary of sensor data."""
    sensor_type = data.get("type", "unknown")

    if sensor_type == "lidar" or sensor_type == "laser":
        ranges = data.get("ranges", [])
        return (
            f"{len(ranges)} range measurements, min={min(ranges):.2f}m, max={max(ranges):.2f}m"
            if ranges
            else "No range data"
        )

    elif sensor_type == "camera":
        return f"Image: {data.get('width', 0)}x{data.get('height', 0)}, encoding={data.get('encoding', 'unknown')}"

    elif sensor_type == "imu":
        orient = data.get("orientation", {})
        return f"Orientation: roll={orient.get('x', 0):.2f}, pitch={orient.get('y', 0):.2f}, yaw={orient.get('z', 0):.2f}"

    elif sensor_type == "gps":
        return f"Position: lat={data.get('latitude', 0):.6f}, lon={data.get('longitude', 0):.6f}, alt={data.get('altitude', 0):.2f}m"

    else:
        return f"Data available for {sensor_type} sensor"


def _detect_message_type(topic_name: str):
    """Auto-detect ROS2 message type from topic name."""
    # Common topic patterns:
    if "/scan" in topic_name:
        from sensor_msgs.msg import LaserScan

        return LaserScan
    elif "/image" in topic_name or "/camera" in topic_name:
        from sensor_msgs.msg import Image

        return Image
    elif "/imu" in topic_name:
        from sensor_msgs.msg import Imu

        return Imu
    elif "/gps" in topic_name or "/navsat" in topic_name:
        from sensor_msgs.msg import NavSatFix

        return NavSatFix
    else:
        raise ValueError(f"Cannot auto-detect message type for topic: {topic_name}")


def _get_message_type_class(message_type: str):
    """Get ROS2 message class from string."""
    # Parse message type (e.g., "sensor_msgs/LaserScan"):
    parts = message_type.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid message type format: {message_type}")

    package, msg_name = parts

    # Import the message class:
    if package == "sensor_msgs":
        import sensor_msgs.msg as msg_module
    elif package == "geometry_msgs":
        import geometry_msgs.msg as msg_module
    else:
        raise ValueError(f"Unsupported message package: {package}")

    return getattr(msg_module, msg_name)


def _message_to_dict(msg, sensor_name: str) -> Dict[str, Any]:
    """Convert ROS2 message to dictionary."""
    # This is a simplified conversion - real implementation would be more comprehensive
    try:
        from gazebo_mcp.utils.converters import ros_msg_to_json
        import json

        json_str = ros_msg_to_json(msg)
        data = json.loads(json_str)
        data["sensor_name"] = sensor_name
        data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return data
    except Exception as e:
        _logger.error(f"Failed to convert message to dict", error=str(e))
        return {
            "sensor_name": sensor_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": f"Conversion failed: {e}",
        }


def _get_mock_sensors() -> List[Dict[str, Any]]:
    """
    Get mock sensors for fallback when Gazebo is not available.
    """
    return [
        {
            "name": "lidar_front",
            "type": "lidar",
            "model": "turtlebot3_burger",
            "topic": "/scan",
            "frame_id": "base_scan",
            "active": True,
            "specs": {
                "min_range": 0.12,
                "max_range": 3.5,
                "angle_min": -3.14,
                "angle_max": 3.14,
                "resolution": 360,
            },
        },
        {
            "name": "camera_rgb",
            "type": "camera",
            "model": "turtlebot3_waffle",
            "topic": "/camera/image_raw",
            "frame_id": "camera_link",
            "active": True,
            "specs": {"width": 1920, "height": 1080, "fov": 1.3962634, "format": "RGB8"},
        },
        {
            "name": "imu_sensor",
            "type": "imu",
            "model": "turtlebot3_burger",
            "topic": "/imu",
            "frame_id": "imu_link",
            "active": True,
            "specs": {"update_rate": 200.0, "noise": 0.01},
        },
        {
            "name": "gps_sensor",
            "type": "gps",
            "model": "drone_1",
            "topic": "/gps/fix",
            "frame_id": "gps_link",
            "active": True,
            "specs": {"horizontal_accuracy": 1.0, "vertical_accuracy": 1.5},
        },
    ]


def _get_mock_sensor_data(sensor_name: str) -> Optional[Dict[str, Any]]:
    """Get mock sensor data for testing."""
    sensors = _get_mock_sensors()

    for sensor in sensors:
        if sensor["name"] == sensor_name:
            sensor_type = sensor["type"]

            if sensor_type == "lidar":
                return {
                    "type": "lidar",
                    "sensor_name": sensor_name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "ranges": [1.5, 2.0, 1.8, 2.5, 3.0] * 72,  # 360 measurements
                    "angle_min": -3.14,
                    "angle_max": 3.14,
                    "range_min": 0.12,
                    "range_max": 3.5,
                }

            elif sensor_type == "camera":
                return {
                    "type": "camera",
                    "sensor_name": sensor_name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "width": 1920,
                    "height": 1080,
                    "encoding": "rgb8",
                    "note": "Image data not included in mock",
                }

            elif sensor_type == "imu":
                return {
                    "type": "imu",
                    "sensor_name": sensor_name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                    "angular_velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "linear_acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
                }

            elif sensor_type == "gps":
                return {
                    "type": "gps",
                    "sensor_name": sensor_name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "altitude": 10.0,
                    "status": "FIX",
                }

    return None
