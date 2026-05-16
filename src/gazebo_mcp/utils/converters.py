"""
Message Converters for Gazebo MCP.

Provides conversion functions between ROS2 message types and Python dictionaries:
- Pose, Twist, Transform conversions
- Quaternion ↔ Euler angle conversions
- JSON serialization for ROS2 messages

These converters enable agent-friendly data formats while maintaining
compatibility with ROS2 interfaces.
"""

import json
import math
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import asdict

from .exceptions import InvalidParameterError
from .validators import validate_quaternion, validate_orientation


# Pose conversions:

def pose_to_dict(pose) -> Dict[str, Any]:
    """
    Convert ROS2 Pose message to Python dictionary.

    Args:
        pose: geometry_msgs/Pose message

    Returns:
        Dictionary with 'position' and 'orientation' keys

    Example:
        >>> from geometry_msgs.msg import Pose
        >>> pose = Pose()
        >>> pose.position.x = 1.0
        >>> pose.position.y = 2.0
        >>> pose.position.z = 0.5
        >>> pose_dict = pose_to_dict(pose)
        >>> # Returns: {
        >>> #   "position": {"x": 1.0, "y": 2.0, "z": 0.5},
        >>> #   "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        >>> # }
    """
    return {
        "position": {
            "x": float(pose.position.x),
            "y": float(pose.position.y),
            "z": float(pose.position.z)
        },
        "orientation": {
            "x": float(pose.orientation.x),
            "y": float(pose.orientation.y),
            "z": float(pose.orientation.z),
            "w": float(pose.orientation.w)
        }
    }


def dict_to_pose(pose_dict: Dict[str, Any]):
    """
    Convert Python dictionary to ROS2 Pose message.

    Args:
        pose_dict: Dictionary with 'position' and 'orientation' keys

    Returns:
        geometry_msgs/Pose message

    Raises:
        InvalidParameterError: If dictionary format is invalid

    Example:
        >>> pose_dict = {
        ...     "position": {"x": 1.0, "y": 2.0, "z": 0.5},
        ...     "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        ... }
        >>> pose = dict_to_pose(pose_dict)
    """
    try:
        from geometry_msgs.msg import Pose
    except ImportError:
        raise InvalidParameterError(
            "ros2_package",
            "geometry_msgs",
            "installed ROS2 package (source ROS2 first)"
        )

    # Validate structure:
    if "position" not in pose_dict:
        raise InvalidParameterError(
            "pose_dict",
            str(pose_dict),
            "dictionary with 'position' key"
        )

    if "orientation" not in pose_dict:
        raise InvalidParameterError(
            "pose_dict",
            str(pose_dict),
            "dictionary with 'orientation' key"
        )

    pose = Pose()

    # Set position:
    pos = pose_dict["position"]
    pose.position.x = float(pos.get("x", 0.0))
    pose.position.y = float(pos.get("y", 0.0))
    pose.position.z = float(pos.get("z", 0.0))

    # Set orientation (validate quaternion):
    orient = pose_dict["orientation"]
    x = float(orient.get("x", 0.0))
    y = float(orient.get("y", 0.0))
    z = float(orient.get("z", 0.0))
    w = float(orient.get("w", 1.0))

    # Validate quaternion is normalized:
    x, y, z, w = validate_quaternion(x, y, z, w)

    pose.orientation.x = x
    pose.orientation.y = y
    pose.orientation.z = z
    pose.orientation.w = w

    return pose


# Twist conversions:

def twist_to_dict(twist) -> Dict[str, Any]:
    """
    Convert ROS2 Twist message to Python dictionary.

    Args:
        twist: geometry_msgs/Twist message

    Returns:
        Dictionary with 'linear' and 'angular' velocity keys

    Example:
        >>> from geometry_msgs.msg import Twist
        >>> twist = Twist()
        >>> twist.linear.x = 0.5
        >>> twist.angular.z = 0.2
        >>> twist_dict = twist_to_dict(twist)
        >>> # Returns: {
        >>> #   "linear": {"x": 0.5, "y": 0.0, "z": 0.0},
        >>> #   "angular": {"x": 0.0, "y": 0.0, "z": 0.2}
        >>> # }
    """
    return {
        "linear": {
            "x": float(twist.linear.x),
            "y": float(twist.linear.y),
            "z": float(twist.linear.z)
        },
        "angular": {
            "x": float(twist.angular.x),
            "y": float(twist.angular.y),
            "z": float(twist.angular.z)
        }
    }


def dict_to_twist(twist_dict: Dict[str, Any]):
    """
    Convert Python dictionary to ROS2 Twist message.

    Args:
        twist_dict: Dictionary with 'linear' and 'angular' keys

    Returns:
        geometry_msgs/Twist message

    Example:
        >>> twist_dict = {
        ...     "linear": {"x": 0.5, "y": 0.0, "z": 0.0},
        ...     "angular": {"x": 0.0, "y": 0.0, "z": 0.2}
        ... }
        >>> twist = dict_to_twist(twist_dict)
    """
    try:
        from geometry_msgs.msg import Twist
    except ImportError:
        raise InvalidParameterError(
            "ros2_package",
            "geometry_msgs",
            "installed ROS2 package (source ROS2 first)"
        )

    twist = Twist()

    # Set linear velocity:
    if "linear" in twist_dict:
        lin = twist_dict["linear"]
        twist.linear.x = float(lin.get("x", 0.0))
        twist.linear.y = float(lin.get("y", 0.0))
        twist.linear.z = float(lin.get("z", 0.0))

    # Set angular velocity:
    if "angular" in twist_dict:
        ang = twist_dict["angular"]
        twist.angular.x = float(ang.get("x", 0.0))
        twist.angular.y = float(ang.get("y", 0.0))
        twist.angular.z = float(ang.get("z", 0.0))

    return twist


# Transform conversions:

def transform_to_dict(transform) -> Dict[str, Any]:
    """
    Convert ROS2 Transform message to Python dictionary.

    Args:
        transform: geometry_msgs/Transform message

    Returns:
        Dictionary with 'translation' and 'rotation' keys

    Example:
        >>> from geometry_msgs.msg import Transform
        >>> tf = Transform()
        >>> tf.translation.x = 1.0
        >>> tf.rotation.w = 1.0
        >>> tf_dict = transform_to_dict(tf)
    """
    return {
        "translation": {
            "x": float(transform.translation.x),
            "y": float(transform.translation.y),
            "z": float(transform.translation.z)
        },
        "rotation": {
            "x": float(transform.rotation.x),
            "y": float(transform.rotation.y),
            "z": float(transform.rotation.z),
            "w": float(transform.rotation.w)
        }
    }


def dict_to_transform(transform_dict: Dict[str, Any]):
    """
    Convert Python dictionary to ROS2 Transform message.

    Args:
        transform_dict: Dictionary with 'translation' and 'rotation' keys

    Returns:
        geometry_msgs/Transform message

    Example:
        >>> tf_dict = {
        ...     "translation": {"x": 1.0, "y": 0.0, "z": 0.0},
        ...     "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        ... }
        >>> tf = dict_to_transform(tf_dict)
    """
    try:
        from geometry_msgs.msg import Transform
    except ImportError:
        raise InvalidParameterError(
            "ros2_package",
            "geometry_msgs",
            "installed ROS2 package (source ROS2 first)"
        )

    transform = Transform()

    # Set translation:
    if "translation" in transform_dict:
        trans = transform_dict["translation"]
        transform.translation.x = float(trans.get("x", 0.0))
        transform.translation.y = float(trans.get("y", 0.0))
        transform.translation.z = float(trans.get("z", 0.0))

    # Set rotation (validate quaternion):
    if "rotation" in transform_dict:
        rot = transform_dict["rotation"]
        x = float(rot.get("x", 0.0))
        y = float(rot.get("y", 0.0))
        z = float(rot.get("z", 0.0))
        w = float(rot.get("w", 1.0))

        x, y, z, w = validate_quaternion(x, y, z, w)

        transform.rotation.x = x
        transform.rotation.y = y
        transform.rotation.z = z
        transform.rotation.w = w

    return transform


# Quaternion ↔ Euler conversions:

def quaternion_to_euler(x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
    """
    Convert quaternion to Euler angles (roll, pitch, yaw).

    Uses the ZYX rotation sequence (intrinsic rotations).

    Args:
        x, y, z, w: Quaternion components

    Returns:
        Tuple of (roll, pitch, yaw) in radians

    Example:
        >>> # Identity quaternion (no rotation):
        >>> roll, pitch, yaw = quaternion_to_euler(0.0, 0.0, 0.0, 1.0)
        >>> # Returns: (0.0, 0.0, 0.0)
        >>>
        >>> # 90-degree rotation around Z-axis:
        >>> roll, pitch, yaw = quaternion_to_euler(0.0, 0.0, 0.707, 0.707)
        >>> # Returns: (0.0, 0.0, 1.57)  # ~π/2 radians
    """
    # Validate quaternion:
    x, y, z, w = validate_quaternion(x, y, z, w)

    # Roll (x-axis rotation):
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation):
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # Use ±90° if out of range
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)


def euler_to_quaternion(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    """
    Convert Euler angles to quaternion.

    Uses the ZYX rotation sequence (intrinsic rotations).

    Args:
        roll: Rotation around x-axis (radians)
        pitch: Rotation around y-axis (radians)
        yaw: Rotation around z-axis (radians)

    Returns:
        Tuple of (x, y, z, w) quaternion components

    Example:
        >>> # No rotation:
        >>> x, y, z, w = euler_to_quaternion(0.0, 0.0, 0.0)
        >>> # Returns: (0.0, 0.0, 0.0, 1.0)
        >>>
        >>> # 90-degree rotation around Z-axis:
        >>> x, y, z, w = euler_to_quaternion(0.0, 0.0, math.pi/2)
        >>> # Returns: (0.0, 0.0, 0.707, 0.707)
    """
    # Validate angles:
    roll, pitch, yaw = validate_orientation(roll, pitch, yaw, radians=True)

    # Compute half angles:
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    # Compute quaternion:
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return (x, y, z, w)


# JSON serialization:

def ros_msg_to_json(msg) -> str:
    """
    Convert ROS2 message to JSON string.

    Args:
        msg: ROS2 message instance

    Returns:
        JSON string representation

    Example:
        >>> from geometry_msgs.msg import Pose
        >>> pose = Pose()
        >>> pose.position.x = 1.0
        >>> json_str = ros_msg_to_json(pose)
        >>> # Returns: '{"position": {"x": 1.0, "y": 0.0, "z": 0.0}, ...}'
    """
    # Try to import rosidl_runtime_py:
    try:
        from rosidl_runtime_py import message_to_ordereddict
        msg_dict = message_to_ordereddict(msg)
        return json.dumps(msg_dict, indent=2)
    except ImportError:
        # Fallback: Manual conversion for common types
        if hasattr(msg, '__class__'):
            msg_type = msg.__class__.__name__

            if msg_type == "Pose":
                return json.dumps(pose_to_dict(msg), indent=2)
            elif msg_type == "Twist":
                return json.dumps(twist_to_dict(msg), indent=2)
            elif msg_type == "Transform":
                return json.dumps(transform_to_dict(msg), indent=2)

        raise InvalidParameterError(
            "ros_msg",
            str(type(msg)),
            "supported ROS2 message type (install rosidl_runtime_py for full support)"
        )


def json_to_ros_msg(json_str: str, msg_type: str):
    """
    Convert JSON string to ROS2 message.

    Args:
        json_str: JSON string representation
        msg_type: Message type name ("Pose", "Twist", "Transform")

    Returns:
        ROS2 message instance

    Raises:
        InvalidParameterError: If message type is unsupported

    Example:
        >>> json_str = '{"position": {"x": 1.0, "y": 0.0, "z": 0.0}, ...}'
        >>> pose = json_to_ros_msg(json_str, "Pose")
    """
    msg_dict = json.loads(json_str)

    if msg_type == "Pose":
        return dict_to_pose(msg_dict)
    elif msg_type == "Twist":
        return dict_to_twist(msg_dict)
    elif msg_type == "Transform":
        return dict_to_transform(msg_dict)
    else:
        raise InvalidParameterError(
            "msg_type",
            msg_type,
            "one of: Pose, Twist, Transform"
        )


# Batch conversions:

def poses_to_dict_list(poses: List) -> List[Dict[str, Any]]:
    """
    Convert list of Pose messages to list of dictionaries.

    Args:
        poses: List of geometry_msgs/Pose messages

    Returns:
        List of pose dictionaries

    Example:
        >>> poses = [pose1, pose2, pose3]
        >>> pose_dicts = poses_to_dict_list(poses)
    """
    return [pose_to_dict(pose) for pose in poses]


def dict_list_to_poses(pose_dicts: List[Dict[str, Any]]) -> List:
    """
    Convert list of dictionaries to list of Pose messages.

    Args:
        pose_dicts: List of pose dictionaries

    Returns:
        List of geometry_msgs/Pose messages

    Example:
        >>> pose_dicts = [{"position": {...}, "orientation": {...}}, ...]
        >>> poses = dict_list_to_poses(pose_dicts)
    """
    return [dict_to_pose(pose_dict) for pose_dict in pose_dicts]


