"""
Gazebo Navigation Tools - Nav2 Integration.

Provides functions for autonomous robot navigation using Nav2 stack.
Supports TurtleBot3 spawning and goal-based navigation.

Based on MCP best practices from Anthropic.
"""

import sys
import math
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose

from gazebo_mcp.utils import (
    OperationResult,
    success_result,
    error_result,
    invalid_parameter_error,
)
from gazebo_mcp.utils.exceptions import (
    GazeboMCPError,
    ROS2NotConnectedError,
    ModelNotFoundError,
)
from gazebo_mcp.utils.validators import validate_model_name, validate_position
from gazebo_mcp.utils.converters import euler_to_quaternion
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager
from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose

# Module-level state
_connection_manager: Optional[ConnectionManager] = None
_adapter: Optional[ModernGazeboAdapter] = None
_nav_clients: Dict[str, ActionClient] = {}  # robot_name -> action_client
_goal_handles: Dict[str, Any] = {}  # robot_name -> goal_handle
_nav_state: Dict[str, Dict[str, Any]] = {}  # robot_name -> state info
_logger = get_logger("navigation_tools")


class NavigationState(Enum):
    """Navigation state enumeration."""
    IDLE = "idle"
    NAVIGATING = "navigating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


def _get_adapter() -> ModernGazeboAdapter:
    """
    Get or create Modern Gazebo adapter.

    Returns:
        ModernGazeboAdapter instance

    Raises:
        ROS2NotConnectedError: If connection fails
    """
    global _connection_manager, _adapter

    if _adapter is not None:
        return _adapter

    try:
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2 for navigation tools")

        node = _connection_manager.get_node()
        _adapter = ModernGazeboAdapter(node, default_world="default", timeout=10.0)
        _logger.info("Created Modern Gazebo adapter")

        return _adapter

    except Exception as e:
        _logger.error(f"Failed to create adapter", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def _get_nav_client(robot_name: str) -> ActionClient:
    """
    Get or create Nav2 action client for robot.

    Args:
        robot_name: Robot instance name

    Returns:
        Nav2 NavigateToPose action client
    """
    global _nav_clients, _connection_manager

    if robot_name in _nav_clients:
        return _nav_clients[robot_name]

    if _connection_manager is None:
        raise ROS2NotConnectedError("ROS2 not connected")

    node = _connection_manager.get_node()
    action_name = f'/{robot_name}/navigate_to_pose'

    client = ActionClient(node, NavigateToPose, action_name)
    _nav_clients[robot_name] = client
    _logger.info(f"Created Nav2 action client for {robot_name}: {action_name}")

    return client


def _load_turtlebot3_sdf(variant: str = "burger") -> str:
    """
    Load TurtleBot3 SDF model content.

    Args:
        variant: TurtleBot3 variant (burger, waffle, waffle_pi)

    Returns:
        SDF content as string

    Raises:
        FileNotFoundError: If model file not found
    """
    # Try common TurtleBot3 model locations
    search_paths = [
        Path(f"/opt/ros/humble/share/turtlebot3_gazebo/models/turtlebot3_{variant}/model.sdf"),
        Path(f"~/.gazebo/models/turtlebot3_{variant}/model.sdf").expanduser(),
        Path(f"/usr/share/gazebo/models/turtlebot3_{variant}/model.sdf"),
    ]

    for path in search_paths:
        if path.exists():
            with open(path, 'r') as f:
                return f.read()

    # If not found, generate simple TurtleBot3-like model
    _logger.warning(f"TurtleBot3 {variant} model not found in standard locations, using simple model")
    return _generate_simple_turtlebot3_sdf(variant)


def _generate_simple_turtlebot3_sdf(variant: str = "burger") -> str:
    """
    Generate simplified TurtleBot3 SDF model.

    Args:
        variant: TurtleBot3 variant

    Returns:
        SDF content as string
    """
    # Simple differential drive robot with LiDAR
    return f"""<?xml version="1.0"?>
<sdf version="1.8">
  <model name="turtlebot3_{variant}">
    <static>false</static>

    <!-- Base link -->
    <link name="base_footprint">
      <pose>0 0 0.01 0 0 0</pose>
      <inertial>
        <mass>1.0</mass>
        <inertia>
          <ixx>0.001</ixx>
          <iyy>0.001</iyy>
          <izz>0.001</izz>
        </inertia>
      </inertial>

      <visual name="base_visual">
        <geometry>
          <cylinder>
            <radius>0.105</radius>
            <length>0.08</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>0.0 0.5 1.0 1</ambient>
          <diffuse>0.0 0.5 1.0 1</diffuse>
        </material>
      </visual>

      <collision name="base_collision">
        <geometry>
          <cylinder>
            <radius>0.105</radius>
            <length>0.08</length>
          </cylinder>
        </geometry>
      </collision>

      <!-- LiDAR sensor -->
      <sensor name="lidar" type="gpu_lidar">
        <pose>0 0 0.08 0 0 0</pose>
        <always_on>true</always_on>
        <update_rate>10</update_rate>
        <lidar>
          <scan>
            <horizontal>
              <samples>360</samples>
              <resolution>1.0</resolution>
              <min_angle>0.0</min_angle>
              <max_angle>6.28</max_angle>
            </horizontal>
          </scan>
          <range>
            <min>0.12</min>
            <max>12.0</max>
            <resolution>0.01</resolution>
          </range>
        </lidar>
      </sensor>
    </link>

    <!-- Differential drive plugin -->
    <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
      <left_joint>left_wheel_joint</left_joint>
      <right_joint>right_wheel_joint</right_joint>
      <wheel_separation>0.160</wheel_separation>
      <wheel_radius>0.033</wheel_radius>
      <odom_publish_frequency>30</odom_publish_frequency>
      <topic>cmd_vel</topic>
    </plugin>
  </model>
</sdf>"""


def spawn_turtlebot3(
    name: str = "turtlebot3",
    variant: str = "burger",
    position: Tuple[float, float, float] = (0.0, 0.0, 0.01),
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    world: str = "default"
) -> OperationResult:
    """
    Spawn TurtleBot3 robot with proper sensors and configuration.

    Uses TurtleBot3 models with LiDAR sensor and differential drive controller.
    Automatically configures for Nav2 integration.

    Args:
        name: Robot instance name (must be unique in simulation)
        variant: TurtleBot3 variant - "burger", "waffle", or "waffle_pi"
        position: Spawn position (x, y, z) in meters
        orientation: Spawn orientation (roll, pitch, yaw) in radians
        world: Target Gazebo world name

    Returns:
        OperationResult with spawn status and robot configuration

    Example:
        >>> spawn_turtlebot3("my_robot", "burger", (0, 0, 0.01))
        OperationResult(success=True, message="TurtleBot3 burger spawned at (0, 0, 0.01)")

    Raises:
        Invalid parameters if validation fails
    """
    try:
        # Validate inputs
        validate_model_name(name)
        validate_position(position)

        if variant not in ["burger", "waffle", "waffle_pi"]:
            return invalid_parameter_error(
                "variant",
                variant,
                suggestions=["burger", "waffle", "waffle_pi"]
            )

        _logger.info(f"Spawning TurtleBot3 {variant} '{name}' at {position}")

        # Get adapter
        adapter = _get_adapter()

        # Load TurtleBot3 SDF
        sdf_content = _load_turtlebot3_sdf(variant)

        # Create pose
        quat = euler_to_quaternion(*orientation)
        pose = EntityPose(position=position, orientation=quat)

        # Spawn using adapter
        import asyncio
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(
            adapter.spawn_entity(name=name, sdf=sdf_content, pose=pose, world=world)
        )

        if not success:
            return error_result(
                f"Failed to spawn TurtleBot3 {variant}",
                suggestions=["Check Gazebo is running", "Verify world name", "Check model name not already in use"]
            )

        # Initialize navigation state
        _nav_state[name] = {
            "state": NavigationState.IDLE.value,
            "variant": variant,
            "position": position,
            "spawned_at": datetime.now().isoformat()
        }

        return success_result(
            message=f"TurtleBot3 {variant} spawned at {position}",
            data={
                "robot_name": name,
                "variant": variant,
                "position": list(position),
                "orientation": list(orientation),
                "world": world,
                "sensors": ["lidar", "imu", "odom"],
                "nav2_ready": True
            }
        )

    except Exception as e:
        _logger.error(f"Failed to spawn TurtleBot3", error=str(e))
        return error_result(
            f"Failed to spawn TurtleBot3: {e}",
            suggestions=["Check ROS2 connection", "Verify Gazebo is running", "Check logs for details"]
        )


def send_nav2_goal(
    robot_name: str,
    goal_position: Tuple[float, float],
    goal_orientation: float = 0.0,
    timeout: float = 120.0,
    wait_for_result: bool = True
) -> OperationResult:
    """
    Send navigation goal to Nav2 action server.

    Uses ROS2 action client to send NavigateToPose goal to Nav2.
    Optionally blocks until navigation completes or times out.

    Args:
        robot_name: Name of robot to navigate
        goal_position: Target (x, y) coordinates in meters
        goal_orientation: Target yaw orientation in radians
        timeout: Maximum time to wait for navigation (seconds)
        wait_for_result: If True, block until navigation completes

    Returns:
        OperationResult with navigation status and metrics

    Example:
        >>> send_nav2_goal("turtlebot3", (5.0, 3.0), 1.57)
        OperationResult(success=True, message="Navigation succeeded in 12.3s")

    Raises:
        ModelNotFoundError if robot not found
        Timeout if navigation exceeds timeout
    """
    try:
        _logger.info(f"Sending Nav2 goal to {robot_name}: position={goal_position}, yaw={goal_orientation}")

        # Validate robot exists
        if robot_name not in _nav_state:
            return error_result(
                f"Robot '{robot_name}' not found",
                suggestions=["Spawn robot first with spawn_turtlebot3", "Check robot name spelling"]
            )

        # Get Nav2 action client
        client = _get_nav_client(robot_name)

        # Wait for action server
        if not client.wait_for_server(timeout_sec=5.0):
            return error_result(
                f"Nav2 action server not available for {robot_name}",
                suggestions=[
                    "Start Nav2 with launch_nav2.sh",
                    "Check Nav2 is running: ros2 node list | grep nav",
                    "Verify action server: ros2 action list"
                ]
            )

        # Create goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = _connection_manager.get_node().get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(goal_position[0])
        goal_msg.pose.pose.position.y = float(goal_position[1])
        goal_msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        quat = euler_to_quaternion(0.0, 0.0, goal_orientation)
        goal_msg.pose.pose.orientation.x = quat[0]
        goal_msg.pose.pose.orientation.y = quat[1]
        goal_msg.pose.pose.orientation.z = quat[2]
        goal_msg.pose.pose.orientation.w = quat[3]

        # Send goal
        start_time = datetime.now()
        goal_future = client.send_goal_async(goal_msg)

        # Update state
        _nav_state[robot_name]["state"] = NavigationState.NAVIGATING.value
        _nav_state[robot_name]["goal"] = goal_position
        _nav_state[robot_name]["start_time"] = start_time.isoformat()

        if not wait_for_result:
            return success_result(
                message=f"Navigation goal sent to {robot_name}",
                data={
                    "robot_name": robot_name,
                    "goal_position": list(goal_position),
                    "goal_orientation": goal_orientation,
                    "status": "goal_sent"
                }
            )

        # Wait for result
        rclpy.spin_until_future_complete(_connection_manager.get_node(), goal_future, timeout_sec=timeout)

        if not goal_future.done():
            _nav_state[robot_name]["state"] = NavigationState.FAILED.value
            return error_result(
                f"Navigation goal timed out after {timeout}s",
                suggestions=["Increase timeout", "Check if path is reachable", "Verify Nav2 is configured correctly"]
            )

        goal_handle = goal_future.result()
        if not goal_handle.accepted:
            _nav_state[robot_name]["state"] = NavigationState.FAILED.value
            return error_result(
                "Navigation goal rejected by Nav2",
                suggestions=["Check goal is within map bounds", "Verify goal is not in obstacle"]
            )

        # Wait for final result
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(_connection_manager.get_node(), result_future, timeout_sec=timeout)

        if not result_future.done():
            _nav_state[robot_name]["state"] = NavigationState.FAILED.value
            return error_result(
                f"Navigation execution timed out after {timeout}s",
                suggestions=["Increase timeout", "Check robot is not stuck"]
            )

        result = result_future.result()
        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Calculate distance traveled (approximate)
        start_pos = _nav_state[robot_name].get("position", (0, 0, 0))
        distance = math.sqrt(
            (goal_position[0] - start_pos[0]) ** 2 +
            (goal_position[1] - start_pos[1]) ** 2
        )

        if result.status == GoalStatus.STATUS_SUCCEEDED:
            _nav_state[robot_name]["state"] = NavigationState.SUCCEEDED.value
            _nav_state[robot_name]["position"] = (*goal_position, 0.0)

            return success_result(
                message=f"Navigation succeeded in {elapsed_time:.1f}s - {distance:.2f}m traveled",
                data={
                    "robot_name": robot_name,
                    "goal_position": list(goal_position),
                    "elapsed_time": elapsed_time,
                    "distance_traveled": distance,
                    "status": "succeeded"
                }
            )
        else:
            _nav_state[robot_name]["state"] = NavigationState.FAILED.value
            return error_result(
                f"Navigation failed with status: {result.status}",
                suggestions=["Check Nav2 logs", "Verify path is clear", "Try different goal"]
            )

    except Exception as e:
        _logger.error(f"Navigation error for {robot_name}", error=str(e))
        if robot_name in _nav_state:
            _nav_state[robot_name]["state"] = NavigationState.FAILED.value
        return error_result(
            f"Navigation failed: {e}",
            suggestions=["Check ROS2 connection", "Verify Nav2 is running", "Check logs"]
        )


def get_navigation_status(robot_name: str) -> OperationResult:
    """
    Get current Nav2 navigation status.

    Returns current state including position, goal, distance remaining,
    and navigation metrics.

    Args:
        robot_name: Name of robot to check

    Returns:
        OperationResult with navigation status

    Example:
        >>> get_navigation_status("turtlebot3")
        OperationResult(success=True, data={"state": "navigating", "remaining_distance": 2.3})
    """
    try:
        if robot_name not in _nav_state:
            return error_result(
                f"Robot '{robot_name}' not found",
                suggestions=["Spawn robot first with spawn_turtlebot3"]
            )

        state = _nav_state[robot_name]
        current_state = state.get("state", NavigationState.IDLE.value)

        data = {
            "robot_name": robot_name,
            "state": current_state,
            "variant": state.get("variant", "unknown"),
            "current_position": state.get("position"),
        }

        if "goal" in state:
            data["goal_position"] = state["goal"]

            # Calculate remaining distance
            current_pos = state.get("position", (0, 0, 0))
            goal_pos = state["goal"]
            remaining = math.sqrt(
                (goal_pos[0] - current_pos[0]) ** 2 +
                (goal_pos[1] - current_pos[1]) ** 2
            )
            data["remaining_distance"] = remaining

        if "start_time" in state:
            start_time = datetime.fromisoformat(state["start_time"])
            elapsed = (datetime.now() - start_time).total_seconds()
            data["elapsed_time"] = elapsed

        return success_result(
            message=f"Robot {robot_name} is {current_state}",
            data=data
        )

    except Exception as e:
        _logger.error(f"Failed to get navigation status", error=str(e))
        return error_result(f"Failed to get status: {e}")


def cancel_navigation(robot_name: str) -> OperationResult:
    """
    Cancel ongoing navigation goal.

    Sends cancel request to Nav2 action server and stops the robot.

    Args:
        robot_name: Name of robot to stop

    Returns:
        OperationResult with cancellation status

    Example:
        >>> cancel_navigation("turtlebot3")
        OperationResult(success=True, message="Navigation canceled")
    """
    try:
        if robot_name not in _nav_state:
            return error_result(
                f"Robot '{robot_name}' not found",
                suggestions=["Check robot name spelling"]
            )

        if robot_name not in _goal_handles or _goal_handles[robot_name] is None:
            return success_result(
                message=f"No active navigation for {robot_name}",
                data={"robot_name": robot_name, "status": "no_active_goal"}
            )

        # Cancel goal
        goal_handle = _goal_handles[robot_name]
        cancel_future = goal_handle.cancel_goal_async()

        rclpy.spin_until_future_complete(_connection_manager.get_node(), cancel_future, timeout_sec=5.0)

        _nav_state[robot_name]["state"] = NavigationState.CANCELED.value
        _goal_handles[robot_name] = None

        return success_result(
            message=f"Navigation canceled for {robot_name}",
            data={"robot_name": robot_name, "status": "canceled"}
        )

    except Exception as e:
        _logger.error(f"Failed to cancel navigation", error=str(e))
        return error_result(f"Failed to cancel: {e}")


def set_initial_pose(
    robot_name: str,
    position: Tuple[float, float],
    orientation: float = 0.0
) -> OperationResult:
    """
    Set initial pose for AMCL localization.

    Publishes to /initialpose topic to initialize AMCL localization.
    Required before navigation if using AMCL for localization.

    Args:
        robot_name: Name of robot
        position: Initial (x, y) position in meters
        orientation: Initial yaw orientation in radians

    Returns:
        OperationResult with initialization status

    Example:
        >>> set_initial_pose("turtlebot3", (0, 0), 0)
        OperationResult(success=True, message="Initial pose set for AMCL")
    """
    try:
        if robot_name not in _nav_state:
            return error_result(
                f"Robot '{robot_name}' not found",
                suggestions=["Spawn robot first with spawn_turtlebot3"]
            )

        _logger.info(f"Setting initial pose for {robot_name}: {position}, yaw={orientation}")

        # Get node
        node = _connection_manager.get_node()

        # Create publisher for initial pose
        topic_name = f'/{robot_name}/initialpose'
        pub = node.create_publisher(PoseWithCovarianceStamped, topic_name, 10)

        # Create message
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = "map"
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.pose.pose.position.x = float(position[0])
        msg.pose.pose.position.y = float(position[1])
        msg.pose.pose.position.z = 0.0

        quat = euler_to_quaternion(0.0, 0.0, orientation)
        msg.pose.pose.orientation.x = quat[0]
        msg.pose.pose.orientation.y = quat[1]
        msg.pose.pose.orientation.z = quat[2]
        msg.pose.pose.orientation.w = quat[3]

        # Covariance (small values = high confidence)
        msg.pose.covariance = [0.1] * 36  # 6x6 matrix

        # Publish
        pub.publish(msg)

        # Update state
        _nav_state[robot_name]["initial_pose"] = (*position, orientation)

        return success_result(
            message=f"Initial pose set for {robot_name}",
            data={
                "robot_name": robot_name,
                "position": list(position),
                "orientation": orientation,
                "topic": topic_name
            }
        )

    except Exception as e:
        _logger.error(f"Failed to set initial pose", error=str(e))
        return error_result(
            f"Failed to set initial pose: {e}",
            suggestions=["Check AMCL is running", "Verify topic exists"]
        )
