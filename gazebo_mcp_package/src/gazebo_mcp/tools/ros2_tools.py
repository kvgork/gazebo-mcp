"""
ROS2 Introspection Tools.

Provides tools for discovering and inspecting ROS2 topics, services,
and publishing messages -- enabling AI assistants to understand and
interact with the live ROS2 graph.

Tools:
- list_topics: Discover all active ROS2 topics with message types
- get_topic_info: Get details about a specific topic (publishers, subscribers, type)
- publish_twist: Publish geometry_msgs/Twist to a topic (robot velocity control)
- get_transform: Look up TF transform between coordinate frames
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from gazebo_mcp.utils import OperationResult, TokenEstimates
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ROS2NotConnectedError,
)
from gazebo_mcp.utils.validators import validate_timeout
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

__all__ = [
    "list_topics",
    "get_topic_info",
    "publish_twist",
    "get_transform",
    "get_joint_states",
]

_logger = get_logger("ros2_tools")

# Cache for publisher instances to avoid recreating them
_publisher_cache: Dict[str, Any] = {}


def list_topics(
    response_format: str = "filtered",
    filter_prefix: Optional[str] = None,
) -> OperationResult:
    """
    List all active ROS2 topics with their message types.

    This is the primary discovery tool for understanding what is happening
    in the simulation. An AI assistant should call this first to learn
    what topics are available before subscribing to sensor data or
    publishing commands.

    Args:
        response_format:
            - "summary": Count and unique message types only (~50 tokens)
            - "concise": Topic names and types (~30 tokens/topic)
            - "filtered": Full data for local filtering (default)
        filter_prefix: Only return topics starting with this prefix
            (e.g., "/camera" to find all camera topics)

    Returns:
        OperationResult with topic list data

    Example:
        >>> result = list_topics()
        >>> if result.success:
        ...     for topic in result.data["topics"]:
        ...         print(f"{topic['name']}: {topic['types']}")
    """
    try:
        if use_real_gazebo():
            bridge = get_bridge()
            node = bridge.node

            # Get all topic names and types from the ROS2 graph
            topic_names_and_types = node.get_topic_names_and_types()

            all_topics = []
            for topic_name, msg_types in topic_names_and_types:
                topic_entry = {
                    "name": topic_name,
                    "types": msg_types,
                    "category": _categorize_topic(topic_name, msg_types),
                }
                all_topics.append(topic_entry)

            _logger.info(f"Discovered {len(all_topics)} ROS2 topics")
        else:
            all_topics = _get_mock_topics()
            _logger.warning("Using mock topic data - ROS2 not available")

        # Apply prefix filter
        if filter_prefix:
            all_topics = [
                t for t in all_topics
                if t["name"].startswith(filter_prefix)
            ]

        # Format response
        if response_format == "summary":
            all_types = set()
            categories = {}
            for t in all_topics:
                for msg_type in t["types"]:
                    all_types.add(msg_type)
                cat = t.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1

            return OperationResult(
                success=True,
                data={
                    "count": len(all_topics),
                    "message_types": sorted(all_types),
                    "categories": categories,
                    "token_estimate": 50,
                },
            )

        elif response_format == "concise":
            concise_topics = [
                {"name": t["name"], "types": t["types"]}
                for t in all_topics
            ]
            return OperationResult(
                success=True,
                data={
                    "topics": concise_topics,
                    "count": len(all_topics),
                    "token_estimate": len(all_topics) * TokenEstimates.TOKENS_PER_TOPIC,
                },
            )

        else:  # filtered (default)
            return OperationResult(
                success=True,
                data={
                    "topics": all_topics,
                    "count": len(all_topics),
                    "usage_hints": {
                        "sensor_topics": "Look for sensor_msgs/* types (LaserScan, Image, Imu, etc.)",
                        "command_topics": "Look for geometry_msgs/Twist topics (usually /cmd_vel)",
                        "tf_topics": "TF data is on /tf and /tf_static",
                        "state_topics": "Look for *_states or *_status topics",
                    },
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
        _logger.exception("Unexpected error listing topics", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to list topics: {e}",
            error_code="LIST_TOPICS_ERROR",
        )


def get_topic_info(
    topic_name: str,
) -> OperationResult:
    """
    Get detailed information about a specific ROS2 topic.

    Returns the message type, publisher count, subscriber count,
    and whether the topic is actively publishing.

    Args:
        topic_name: Full topic name (e.g., "/scan", "/cmd_vel")

    Returns:
        OperationResult with topic details

    Example:
        >>> result = get_topic_info("/scan")
        >>> if result.success:
        ...     info = result.data
        ...     print(f"Type: {info['message_types']}")
        ...     print(f"Publishers: {info['publisher_count']}")
    """
    try:
        if not topic_name:
            return OperationResult(
                success=False,
                error="topic_name is required",
                error_code="MISSING_PARAMETER",
                suggestions=["Provide a topic name, e.g., '/scan' or '/cmd_vel'"],
            )

        if use_real_gazebo():
            bridge = get_bridge()
            node = bridge.node

            # Get topic names and types
            topic_names_and_types = node.get_topic_names_and_types()
            topic_types = None
            for name, types in topic_names_and_types:
                if name == topic_name:
                    topic_types = types
                    break

            if topic_types is None:
                return OperationResult(
                    success=False,
                    error=f"Topic '{topic_name}' not found",
                    error_code="TOPIC_NOT_FOUND",
                    suggestions=[
                        "Use list_topics() to see available topics",
                        "Check topic name spelling (must include leading '/')",
                    ],
                )

            # Get publisher and subscriber info
            pub_info = node.get_publishers_info_by_topic(topic_name)
            sub_info = node.get_subscriptions_info_by_topic(topic_name)

            return OperationResult(
                success=True,
                data={
                    "topic_name": topic_name,
                    "message_types": topic_types,
                    "publisher_count": len(pub_info),
                    "subscriber_count": len(sub_info),
                    "category": _categorize_topic(topic_name, topic_types),
                    "publishers": [
                        {
                            "node_name": info.node_name,
                            "node_namespace": info.node_namespace,
                        }
                        for info in pub_info
                    ],
                    "subscribers": [
                        {
                            "node_name": info.node_name,
                            "node_namespace": info.node_namespace,
                        }
                        for info in sub_info
                    ],
                },
            )
        else:
            _logger.warning("Using mock topic info - ROS2 not available")
            # Return mock info for the requested topic
            mock_topics = _get_mock_topics()
            for t in mock_topics:
                if t["name"] == topic_name:
                    return OperationResult(
                        success=True,
                        data={
                            "topic_name": topic_name,
                            "message_types": t["types"],
                            "publisher_count": 1,
                            "subscriber_count": 0,
                            "category": t.get("category", "other"),
                            "publishers": [{"node_name": "mock_gazebo", "node_namespace": "/"}],
                            "subscribers": [],
                            "note": "Mock data - ROS2 not available",
                        },
                    )
            return OperationResult(
                success=False,
                error=f"Topic '{topic_name}' not found (mock mode)",
                error_code="TOPIC_NOT_FOUND",
                suggestions=["Use list_topics() to see available topics"],
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error getting topic info", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get topic info: {e}",
            error_code="GET_TOPIC_INFO_ERROR",
        )


def publish_twist(
    topic_name: str = "/cmd_vel",
    linear_x: float = 0.0,
    linear_y: float = 0.0,
    linear_z: float = 0.0,
    angular_x: float = 0.0,
    angular_y: float = 0.0,
    angular_z: float = 0.0,
) -> OperationResult:
    """
    Publish a velocity command (geometry_msgs/Twist) to a ROS2 topic.

    This is the primary tool for driving robots in Gazebo. Most mobile
    robots subscribe to /cmd_vel for velocity commands.

    Common usage patterns:
    - Drive forward: linear_x=0.5
    - Turn left: angular_z=0.5
    - Turn right: angular_z=-0.5
    - Stop: all zeros (default)
    - Drive in arc: linear_x=0.3, angular_z=0.2

    Args:
        topic_name: Topic to publish to (default: "/cmd_vel")
        linear_x: Forward/backward velocity (m/s). Positive = forward.
        linear_y: Left/right velocity (m/s). Only for holonomic robots.
        linear_z: Up/down velocity (m/s). Only for flying robots.
        angular_x: Roll rate (rad/s). Rarely used for ground robots.
        angular_y: Pitch rate (rad/s). Rarely used for ground robots.
        angular_z: Yaw rate (rad/s). Positive = turn left (CCW).

    Returns:
        OperationResult with publish confirmation

    Example:
        >>> # Drive forward at 0.5 m/s
        >>> result = publish_twist(linear_x=0.5)
        >>>
        >>> # Turn left while moving forward
        >>> result = publish_twist(linear_x=0.3, angular_z=0.5)
        >>>
        >>> # Stop the robot
        >>> result = publish_twist()
    """
    try:
        if use_real_gazebo():
            bridge = get_bridge()
            node = bridge.node

            # Get or create publisher for this topic
            if topic_name not in _publisher_cache:
                from geometry_msgs.msg import Twist
                publisher = node.create_publisher(Twist, topic_name, 10)
                _publisher_cache[topic_name] = publisher
                _logger.info(f"Created Twist publisher for {topic_name}")

            publisher = _publisher_cache[topic_name]

            # Build and publish the message
            from geometry_msgs.msg import Twist
            msg = Twist()
            msg.linear.x = float(linear_x)
            msg.linear.y = float(linear_y)
            msg.linear.z = float(linear_z)
            msg.angular.x = float(angular_x)
            msg.angular.y = float(angular_y)
            msg.angular.z = float(angular_z)

            publisher.publish(msg)

            _logger.info(
                f"Published Twist to {topic_name}: "
                f"linear=({linear_x}, {linear_y}, {linear_z}), "
                f"angular=({angular_x}, {angular_y}, {angular_z})"
            )

            return OperationResult(
                success=True,
                data={
                    "topic": topic_name,
                    "published": True,
                    "twist": {
                        "linear": {"x": linear_x, "y": linear_y, "z": linear_z},
                        "angular": {"x": angular_x, "y": angular_y, "z": angular_z},
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Message published once. Robot will stop when no more messages arrive (depending on controller).",
                },
            )
        else:
            _logger.warning(f"Mock publish_twist to {topic_name} - ROS2 not available")
            return OperationResult(
                success=True,
                data={
                    "topic": topic_name,
                    "published": False,
                    "twist": {
                        "linear": {"x": linear_x, "y": linear_y, "z": linear_z},
                        "angular": {"x": angular_x, "y": angular_y, "z": angular_z},
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock mode - ROS2 not available. Command was not sent.",
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
        _logger.exception("Unexpected error publishing twist", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to publish twist: {e}",
            error_code="PUBLISH_TWIST_ERROR",
            suggestions=[
                "Check topic name is correct",
                "Ensure Gazebo simulation is running",
                "Check that geometry_msgs is available",
            ],
        )


def get_transform(
    target_frame: str,
    source_frame: str,
    timeout: float = 1.0,
) -> OperationResult:
    """
    Look up the TF transform between two coordinate frames.

    TF transforms describe the spatial relationship (translation + rotation)
    between coordinate frames in the robot system. Common frame lookups:

    - "map" -> "base_link": Robot position in the map
    - "base_link" -> "camera_link": Camera position relative to robot
    - "odom" -> "base_link": Odometry-based robot position
    - "base_link" -> "base_scan": Lidar position relative to robot

    Args:
        target_frame: Target frame (e.g., "map")
        source_frame: Source frame (e.g., "base_link")
        timeout: Lookup timeout in seconds (default: 1.0)

    Returns:
        OperationResult with transform data (translation + rotation)

    Example:
        >>> # Get robot position in map frame
        >>> result = get_transform("map", "base_link")
        >>> if result.success:
        ...     pos = result.data["translation"]
        ...     print(f"Robot at: x={pos['x']:.2f}, y={pos['y']:.2f}")
    """
    try:
        if not target_frame or not source_frame:
            return OperationResult(
                success=False,
                error="Both target_frame and source_frame are required",
                error_code="MISSING_PARAMETER",
                suggestions=[
                    "Common frames: 'map', 'odom', 'base_link', 'base_scan', 'camera_link'",
                    "Example: get_transform('map', 'base_link')",
                ],
            )

        timeout = validate_timeout(timeout, min_timeout=0.1, max_timeout=30.0)

        if use_real_gazebo():
            bridge = get_bridge()

            # Use the existing get_transform from the bridge
            transform_dict = bridge.get_transform(
                target_frame=target_frame,
                source_frame=source_frame,
                timeout=timeout,
            )

            if transform_dict is None:
                return OperationResult(
                    success=False,
                    error=f"Transform from '{source_frame}' to '{target_frame}' not available",
                    error_code="TRANSFORM_NOT_FOUND",
                    suggestions=[
                        f"Check that frames '{target_frame}' and '{source_frame}' exist",
                        "TF frames may not be published until a robot is spawned",
                        "Use 'ros2 run tf2_tools view_frames' to see the TF tree",
                        "Common frames: 'map', 'odom', 'base_link', 'base_footprint'",
                    ],
                )

            # Convert quaternion to Euler for easier interpretation
            from gazebo_mcp.utils.converters import quaternion_to_euler
            rot = transform_dict.get("rotation", {})
            try:
                roll, pitch, yaw = quaternion_to_euler(
                    rot.get("x", 0.0),
                    rot.get("y", 0.0),
                    rot.get("z", 0.0),
                    rot.get("w", 1.0),
                )
                euler = {"roll": roll, "pitch": pitch, "yaw": yaw}
            except Exception:
                euler = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}

            return OperationResult(
                success=True,
                data={
                    "target_frame": target_frame,
                    "source_frame": source_frame,
                    "translation": transform_dict.get("translation", {}),
                    "rotation_quaternion": transform_dict.get("rotation", {}),
                    "rotation_euler": euler,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )
        else:
            _logger.warning("Using mock transform data - ROS2 not available")
            return OperationResult(
                success=True,
                data={
                    "target_frame": target_frame,
                    "source_frame": source_frame,
                    "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_quaternion": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                    "rotation_euler": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock data - ROS2 not available",
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
        _logger.exception("Unexpected error getting transform", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get transform: {e}",
            error_code="GET_TRANSFORM_ERROR",
        )


# --- Helper functions ---


def _categorize_topic(topic_name: str, msg_types: List[str]) -> str:
    """Categorize a topic by its name and message type."""
    name_lower = topic_name.lower()
    types_str = " ".join(msg_types).lower()

    if "/tf" in name_lower:
        return "transform"
    if "cmd_vel" in name_lower or "twist" in types_str:
        return "command"
    if "/scan" in name_lower or "laserscan" in types_str:
        return "sensor_lidar"
    if "/image" in name_lower or "/camera" in name_lower:
        return "sensor_camera"
    if "/imu" in name_lower:
        return "sensor_imu"
    if "/gps" in name_lower or "/navsat" in name_lower:
        return "sensor_gps"
    if "/odom" in name_lower or "odometry" in types_str:
        return "odometry"
    if "/joint_states" in name_lower:
        return "joint_states"
    if "/map" in name_lower or "occupancygrid" in types_str:
        return "map"
    if "clock" in name_lower:
        return "clock"
    if "model_states" in name_lower or "entity_states" in name_lower:
        return "simulation_state"
    if "/parameter" in name_lower or "/rosout" in name_lower:
        return "system"
    if "sensor" in name_lower or "sensor_msgs" in types_str:
        return "sensor_other"

    return "other"


def get_joint_states(
    model_name: Optional[str] = None,
    topic_name: str = "/joint_states",
    timeout: float = 2.0,
) -> OperationResult:
    """
    Get current joint states for a robot model.

    Reads a single JointState message from the given topic.
    Most robots publish to /joint_states; TurtleBot3 publishes there too.

    Args:
        model_name: Optional filter — only return joints whose name
                    starts with model_name (e.g. 'turtlebot3_burger')
        topic_name: ROS2 topic to read (default: /joint_states)
        timeout: Seconds to wait for data (default: 2.0)

    Returns:
        OperationResult with joints list

    Examples:
        >>> get_joint_states()
        >>> get_joint_states(topic_name='/turtlebot3_burger/joint_states')
        >>> get_joint_states(model_name='turtlebot3', timeout=5.0)
    """
    try:
        timeout = validate_timeout(timeout)

        if use_real_gazebo():
            bridge = get_bridge()
            data = bridge.get_joint_states(topic_name=topic_name, timeout=timeout)

            if data is None:
                return OperationResult(
                    success=False,
                    error=f"No joint state data received from '{topic_name}' within {timeout}s",
                    error_code="JOINT_STATE_TIMEOUT",
                    suggestions=[
                        f"Verify the topic exists: gazebo_get_topic_info('{topic_name}')",
                        "Check that the robot model is spawned and running",
                        "Try a longer timeout",
                    ],
                )

            joints = data["joints"]
            if model_name:
                joints = [j for j in joints if model_name.lower() in j["name"].lower()]

            return OperationResult(
                success=True,
                data={
                    "joints": joints,
                    "count": len(joints),
                    "topic": topic_name,
                    "timestamp": data.get("timestamp"),
                    "token_estimate": len(joints) * TokenEstimates.TOKENS_PER_JOINT,
                },
            )

        else:
            # Mock data matching a typical TurtleBot3 Burger
            mock_joints = [
                {"name": "wheel_left_joint",  "position": 0.23, "velocity": 0.0, "effort": 0.0},
                {"name": "wheel_right_joint", "position": 0.21, "velocity": 0.0, "effort": 0.0},
            ]
            if model_name:
                mock_joints = [j for j in mock_joints if model_name.lower() in j["name"].lower()]
            return OperationResult(
                success=True,
                data={
                    "joints": mock_joints,
                    "count": len(mock_joints),
                    "topic": topic_name,
                    "note": "Mock data - Gazebo not available",
                    "token_estimate": len(mock_joints) * TokenEstimates.TOKENS_PER_JOINT,
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error getting joint states", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get joint states: {e}",
            error_code="GET_JOINT_STATES_ERROR",
        )


def _get_mock_topics() -> List[Dict[str, Any]]:
    """Get mock topics for fallback when ROS2 is not available."""
    return [
        {
            "name": "/scan",
            "types": ["sensor_msgs/msg/LaserScan"],
            "category": "sensor_lidar",
        },
        {
            "name": "/cmd_vel",
            "types": ["geometry_msgs/msg/Twist"],
            "category": "command",
        },
        {
            "name": "/odom",
            "types": ["nav_msgs/msg/Odometry"],
            "category": "odometry",
        },
        {
            "name": "/camera/image_raw",
            "types": ["sensor_msgs/msg/Image"],
            "category": "sensor_camera",
        },
        {
            "name": "/camera/camera_info",
            "types": ["sensor_msgs/msg/CameraInfo"],
            "category": "sensor_camera",
        },
        {
            "name": "/imu",
            "types": ["sensor_msgs/msg/Imu"],
            "category": "sensor_imu",
        },
        {
            "name": "/joint_states",
            "types": ["sensor_msgs/msg/JointState"],
            "category": "joint_states",
        },
        {
            "name": "/tf",
            "types": ["tf2_msgs/msg/TFMessage"],
            "category": "transform",
        },
        {
            "name": "/tf_static",
            "types": ["tf2_msgs/msg/TFMessage"],
            "category": "transform",
        },
        {
            "name": "/clock",
            "types": ["rosgraph_msgs/msg/Clock"],
            "category": "clock",
        },
        {
            "name": "/rosout",
            "types": ["rcl_interfaces/msg/Log"],
            "category": "system",
        },
    ]
