"""
Unit tests for ROS2 introspection tools.

Tests list_topics, get_topic_info, publish_twist, get_transform,
and spawn_sdf in mock mode (no Gazebo required).
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.ros2_tools import (
    list_topics,
    get_topic_info,
    publish_twist,
    get_transform,
)
from gazebo_mcp.tools.model_management import spawn_sdf


# ============================================================
# list_topics tests
# ============================================================


class TestListTopics:
    """Tests for list_topics tool."""

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_mock_mode_filtered(self, mock_use_real):
        """list_topics returns mock topics in filtered format."""
        result = list_topics(response_format="filtered")
        assert result.success is True
        assert "topics" in result.data
        assert "count" in result.data
        assert result.data["count"] > 0
        # Check that mock topics include expected names
        topic_names = [t["name"] for t in result.data["topics"]]
        assert "/scan" in topic_names
        assert "/cmd_vel" in topic_names
        assert "/odom" in topic_names

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_mock_mode_summary(self, mock_use_real):
        """list_topics summary returns counts and types."""
        result = list_topics(response_format="summary")
        assert result.success is True
        assert "count" in result.data
        assert "message_types" in result.data
        assert "categories" in result.data
        assert result.data["count"] > 0

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_mock_mode_concise(self, mock_use_real):
        """list_topics concise returns names and types only."""
        result = list_topics(response_format="concise")
        assert result.success is True
        assert "topics" in result.data
        for topic in result.data["topics"]:
            assert "name" in topic
            assert "types" in topic

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_filter_prefix(self, mock_use_real):
        """list_topics filters by prefix correctly."""
        result = list_topics(filter_prefix="/camera")
        assert result.success is True
        for topic in result.data["topics"]:
            assert topic["name"].startswith("/camera")

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_filter_prefix_no_match(self, mock_use_real):
        """list_topics with non-matching prefix returns empty list."""
        result = list_topics(filter_prefix="/nonexistent_prefix")
        assert result.success is True
        assert result.data["count"] == 0

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_list_topics_categories(self, mock_use_real):
        """list_topics assigns categories to mock topics."""
        result = list_topics(response_format="filtered")
        assert result.success is True
        for topic in result.data["topics"]:
            assert "category" in topic
            assert topic["category"] in [
                "sensor_lidar", "command", "odometry", "sensor_camera",
                "sensor_imu", "sensor_gps", "joint_states", "transform",
                "clock", "system", "sensor_other", "map",
                "simulation_state", "other",
            ]


# ============================================================
# get_topic_info tests
# ============================================================


class TestGetTopicInfo:
    """Tests for get_topic_info tool."""

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_topic_info_mock_found(self, mock_use_real):
        """get_topic_info returns info for known mock topic."""
        result = get_topic_info("/scan")
        assert result.success is True
        assert result.data["topic_name"] == "/scan"
        assert "message_types" in result.data
        assert "publisher_count" in result.data
        assert "subscriber_count" in result.data

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_topic_info_mock_not_found(self, mock_use_real):
        """get_topic_info returns error for unknown topic."""
        result = get_topic_info("/nonexistent_topic")
        assert result.success is False
        assert "TOPIC_NOT_FOUND" in result.error_code

    def test_get_topic_info_empty_name(self):
        """get_topic_info returns error for empty name."""
        result = get_topic_info("")
        assert result.success is False
        assert "MISSING_PARAMETER" in result.error_code

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_topic_info_cmd_vel(self, mock_use_real):
        """get_topic_info returns correct category for /cmd_vel."""
        result = get_topic_info("/cmd_vel")
        assert result.success is True
        assert result.data["category"] == "command"


# ============================================================
# publish_twist tests
# ============================================================


class TestPublishTwist:
    """Tests for publish_twist tool."""

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_publish_twist_mock_mode_defaults(self, mock_use_real):
        """publish_twist in mock mode returns success with zero twist."""
        result = publish_twist()
        assert result.success is True
        assert result.data["published"] is False  # Mock mode
        twist = result.data["twist"]
        assert twist["linear"]["x"] == 0.0
        assert twist["angular"]["z"] == 0.0

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_publish_twist_mock_mode_forward(self, mock_use_real):
        """publish_twist records forward velocity correctly."""
        result = publish_twist(linear_x=0.5)
        assert result.success is True
        assert result.data["twist"]["linear"]["x"] == 0.5
        assert result.data["twist"]["angular"]["z"] == 0.0

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_publish_twist_mock_mode_turn(self, mock_use_real):
        """publish_twist records turn velocity correctly."""
        result = publish_twist(angular_z=1.0)
        assert result.success is True
        assert result.data["twist"]["linear"]["x"] == 0.0
        assert result.data["twist"]["angular"]["z"] == 1.0

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_publish_twist_mock_mode_custom_topic(self, mock_use_real):
        """publish_twist uses custom topic name."""
        result = publish_twist(topic_name="/robot1/cmd_vel", linear_x=0.3)
        assert result.success is True
        assert result.data["topic"] == "/robot1/cmd_vel"

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_publish_twist_mock_mode_all_axes(self, mock_use_real):
        """publish_twist records all velocity axes."""
        result = publish_twist(
            linear_x=1.0, linear_y=2.0, linear_z=3.0,
            angular_x=0.1, angular_y=0.2, angular_z=0.3,
        )
        assert result.success is True
        twist = result.data["twist"]
        assert twist["linear"]["x"] == 1.0
        assert twist["linear"]["y"] == 2.0
        assert twist["linear"]["z"] == 3.0
        assert twist["angular"]["x"] == 0.1
        assert twist["angular"]["y"] == 0.2
        assert twist["angular"]["z"] == 0.3


# ============================================================
# get_transform tests
# ============================================================


class TestGetTransform:
    """Tests for get_transform tool."""

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_transform_mock_mode(self, mock_use_real):
        """get_transform returns mock identity transform."""
        result = get_transform("map", "base_link")
        assert result.success is True
        assert result.data["target_frame"] == "map"
        assert result.data["source_frame"] == "base_link"
        assert "translation" in result.data
        assert "rotation_quaternion" in result.data
        assert "rotation_euler" in result.data

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_transform_mock_identity(self, mock_use_real):
        """get_transform mock returns identity (zero translation, identity rotation)."""
        result = get_transform("odom", "base_link")
        assert result.success is True
        trans = result.data["translation"]
        assert trans["x"] == 0.0
        assert trans["y"] == 0.0
        assert trans["z"] == 0.0
        rot = result.data["rotation_quaternion"]
        assert rot["w"] == 1.0

    def test_get_transform_missing_target(self):
        """get_transform returns error when target_frame is empty."""
        result = get_transform("", "base_link")
        assert result.success is False
        assert "MISSING_PARAMETER" in result.error_code

    def test_get_transform_missing_source(self):
        """get_transform returns error when source_frame is empty."""
        result = get_transform("map", "")
        assert result.success is False
        assert "MISSING_PARAMETER" in result.error_code


# ============================================================
# spawn_sdf tests
# ============================================================


class TestSpawnSdf:
    """Tests for spawn_sdf tool."""

    VALID_SDF = """<?xml version='1.0'?>
<sdf version='1.6'>
  <model name='test_model'>
    <static>true</static>
    <link name='link'>
      <visual name='visual'>
        <geometry><box><size>1 1 1</size></box></geometry>
      </visual>
    </link>
  </model>
</sdf>"""

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_mock_mode(self, mock_use_real):
        """spawn_sdf in mock mode returns success with entity info."""
        result = spawn_sdf("test_entity", self.VALID_SDF, x=1.0, y=2.0, z=0.5)
        assert result.success is True
        assert result.data["entity_name"] == "test_entity"
        assert result.data["position"]["x"] == 1.0
        assert result.data["position"]["y"] == 2.0
        assert result.data["position"]["z"] == 0.5
        assert result.data["sdf_length"] > 0

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_empty_xml(self, mock_use_real):
        """spawn_sdf returns error for empty SDF string."""
        result = spawn_sdf("test_entity", "")
        assert result.success is False
        assert "MISSING_PARAMETER" in result.error_code

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_whitespace_xml(self, mock_use_real):
        """spawn_sdf returns error for whitespace-only SDF string."""
        result = spawn_sdf("test_entity", "   \n  ")
        assert result.success is False
        assert "MISSING_PARAMETER" in result.error_code

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_invalid_xml(self, mock_use_real):
        """spawn_sdf returns error for non-XML string."""
        result = spawn_sdf("test_entity", "this is not xml")
        assert result.success is False
        assert "INVALID_PARAMETER" in result.error_code

    def test_spawn_sdf_invalid_entity_name(self):
        """spawn_sdf returns error for invalid entity name."""
        result = spawn_sdf("123invalid", self.VALID_SDF)
        assert result.success is False

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_with_orientation(self, mock_use_real):
        """spawn_sdf records orientation correctly."""
        import math
        result = spawn_sdf(
            "oriented_entity", self.VALID_SDF,
            x=0.0, y=0.0, z=0.0,
            roll=0.0, pitch=0.0, yaw=math.pi / 2,
        )
        assert result.success is True
        assert abs(result.data["orientation"]["yaw"] - math.pi / 2) < 0.001

    @patch("gazebo_mcp.tools.model_management.use_real_gazebo", return_value=False)
    def test_spawn_sdf_default_position(self, mock_use_real):
        """spawn_sdf defaults to origin position."""
        result = spawn_sdf("origin_entity", self.VALID_SDF)
        assert result.success is True
        assert result.data["position"]["x"] == 0.0
        assert result.data["position"]["y"] == 0.0
        assert result.data["position"]["z"] == 0.0


# ============================================================
# Topic categorization tests
# ============================================================


class TestTopicCategorization:
    """Tests for _categorize_topic helper."""

    def test_categorization(self):
        """_categorize_topic assigns correct categories."""
        from gazebo_mcp.tools.ros2_tools import _categorize_topic

        assert _categorize_topic("/scan", ["sensor_msgs/msg/LaserScan"]) == "sensor_lidar"
        assert _categorize_topic("/cmd_vel", ["geometry_msgs/msg/Twist"]) == "command"
        assert _categorize_topic("/odom", ["nav_msgs/msg/Odometry"]) == "odometry"
        assert _categorize_topic("/camera/image_raw", ["sensor_msgs/msg/Image"]) == "sensor_camera"
        assert _categorize_topic("/imu", ["sensor_msgs/msg/Imu"]) == "sensor_imu"
        assert _categorize_topic("/tf", ["tf2_msgs/msg/TFMessage"]) == "transform"
        assert _categorize_topic("/clock", ["rosgraph_msgs/msg/Clock"]) == "clock"
        assert _categorize_topic("/joint_states", ["sensor_msgs/msg/JointState"]) == "joint_states"
        assert _categorize_topic("/rosout", ["rcl_interfaces/msg/Log"]) == "system"
        assert _categorize_topic("/custom_topic", ["custom_msgs/msg/Custom"]) == "other"


# ============================================================
# get_joint_states tests
# ============================================================


class TestGetJointStates:
    """Tests for get_joint_states tool."""

    def setup_method(self):
        """Reset bridge state before each test."""
        from gazebo_mcp.tools import _bridge_helper
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_joint_states_mock_mode(self, mock_use_real):
        """get_joint_states returns mock data when Gazebo not running."""
        from gazebo_mcp.tools.ros2_tools import get_joint_states
        result = get_joint_states()

        assert result.success is True
        assert "joints" in result.data
        assert "count" in result.data
        assert result.data["count"] > 0
        assert "note" in result.data

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_joint_states_mock_joint_structure(self, mock_use_real):
        """Mock joints have required fields."""
        from gazebo_mcp.tools.ros2_tools import get_joint_states
        result = get_joint_states()

        joints = result.data["joints"]
        for joint in joints:
            assert "name" in joint
            assert "position" in joint
            assert "velocity" in joint
            assert "effort" in joint

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=False)
    def test_get_joint_states_custom_topic(self, mock_use_real):
        """get_joint_states accepts custom topic name."""
        from gazebo_mcp.tools.ros2_tools import get_joint_states
        result = get_joint_states(topic_name="/my_robot/joint_states")

        assert result.success is True
        assert result.data["topic"] == "/my_robot/joint_states"

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=True)
    def test_get_joint_states_real_mode_uses_bridge(self, mock_use_real):
        """get_joint_states calls bridge.get_joint_states in real mode."""
        from gazebo_mcp.tools.ros2_tools import get_joint_states
        from gazebo_mcp.tools import ros2_tools
        mock_bridge = Mock()
        mock_bridge.get_joint_states.return_value = {
            "joints": [{"name": "joint1", "position": 0.5, "velocity": 0.0, "effort": 0.0}],
            "topic": "/joint_states",
            "timestamp": "2026-04-06T00:00:00Z",
        }

        with patch.object(ros2_tools, 'get_bridge', return_value=mock_bridge):
            result = get_joint_states(topic_name="/joint_states", timeout=2.0)

        assert result.success is True
        assert len(result.data["joints"]) == 1
        assert result.data["joints"][0]["name"] == "joint1"

    @patch("gazebo_mcp.tools.ros2_tools.use_real_gazebo", return_value=True)
    def test_get_joint_states_real_mode_empty_response(self, mock_use_real):
        """get_joint_states handles empty joint list from bridge."""
        from gazebo_mcp.tools.ros2_tools import get_joint_states
        from gazebo_mcp.tools import ros2_tools
        mock_bridge = Mock()
        mock_bridge.get_joint_states.return_value = {
            "joints": [],
            "topic": "/joint_states",
            "timestamp": "2026-04-06T00:00:00Z",
        }

        with patch.object(ros2_tools, 'get_bridge', return_value=mock_bridge):
            result = get_joint_states()

        assert result.success is True
        assert result.data["count"] == 0
