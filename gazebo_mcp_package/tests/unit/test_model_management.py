"""
Unit tests for model_management module.

Tests all 5 model management functions:
- list_models
- spawn_model
- delete_model
- get_model_state
- set_model_state
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import model_management
from gazebo_mcp.tools import _bridge_helper
from gazebo_mcp.utils.exceptions import (
    InvalidParameterError,
    ROS2NotConnectedError,
    GazeboMCPError,
    ModelNotFoundError
)


class TestListModels:
    """Tests for list_models()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_list_models_mock_mode_summary(self):
        """Test listing models in mock mode with summary format."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.list_models(response_format="summary")

        assert result.success is True
        assert "count" in result.data
        assert "types" in result.data
        assert "states" in result.data
        assert isinstance(result.data["count"], int)

    def test_list_models_mock_mode_concise(self):
        """Test listing models in mock mode with concise format."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.list_models(response_format="concise")

        assert result.success is True
        assert "models" in result.data
        assert isinstance(result.data["models"], list)
        # Check first model has required fields:
        if len(result.data["models"]) > 0:
            model = result.data["models"][0]
            assert "name" in model
            assert "type" in model
            assert "state" in model

    def test_list_models_mock_mode_filtered(self):
        """Test listing models in mock mode with filtered format."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.list_models(response_format="filtered")

        assert result.success is True
        assert "models" in result.data
        assert isinstance(result.data["models"], list)
        # Filtered format includes full data:
        if len(result.data["models"]) > 0:
            model = result.data["models"][0]
            assert "name" in model
            assert "position" in model
            assert "velocity" in model

    def test_list_models_real_mode_success(self):
        """Test listing models in real mode with successful retrieval."""
        mock_bridge = Mock()
        mock_model_state = Mock()
        mock_model_state.name = "test_robot"
        mock_model_state.state = "active"
        mock_model_state.pose = {
            "position": {"x": 1.0, "y": 2.0, "z": 0.5},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }
        mock_model_state.twist = {
            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0}
        }
        mock_bridge.get_model_list.return_value = [mock_model_state]

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.list_models(response_format="concise")

        assert result.success is True
        assert len(result.data["models"]) == 1
        assert result.data["models"][0]["name"] == "test_robot"

    def test_list_models_empty_simulation(self):
        """Test listing models when simulation is empty."""
        mock_bridge = Mock()
        mock_bridge.get_model_list.return_value = []

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.list_models(response_format="summary")

        assert result.success is True
        assert result.data["count"] == 0

    def test_list_models_gazebo_error(self):
        """Test list models when GazeboMCPError occurs."""
        mock_bridge = Mock()
        mock_bridge.get_model_list.side_effect = GazeboMCPError(
            "Failed to retrieve models",
            error_code="RETRIEVAL_ERROR"
        )

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.list_models()

        assert result.success is False
        assert result.error_code == "RETRIEVAL_ERROR"


class TestSpawnModel:
    """Tests for spawn_model()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_spawn_model_mock_mode_defaults(self):
        """Test spawning model in mock mode with default parameters."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.spawn_model("test_robot")

        assert result.success is True
        assert result.data["model_name"] == "test_robot"
        assert result.data["position"]["x"] == 0.0
        assert result.data["position"]["y"] == 0.0
        assert result.data["position"]["z"] == 0.0
        assert "note" in result.data
        assert "Mock spawn" in result.data["note"]

    def test_spawn_model_mock_mode_custom_position(self):
        """Test spawning model with custom position."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.spawn_model(
                "test_robot",
                x=1.5,
                y=2.5,
                z=0.5
            )

        assert result.success is True
        assert result.data["position"]["x"] == 1.5
        assert result.data["position"]["y"] == 2.5
        assert result.data["position"]["z"] == 0.5

    def test_spawn_model_mock_mode_custom_orientation(self):
        """Test spawning model with custom orientation."""
        import math
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.spawn_model(
                "test_robot",
                roll=0.1,
                pitch=0.2,
                yaw=math.pi / 2
            )

        assert result.success is True
        assert abs(result.data["orientation"]["roll"] - 0.1) < 0.001
        assert abs(result.data["orientation"]["pitch"] - 0.2) < 0.001
        assert abs(result.data["orientation"]["yaw"] - math.pi / 2) < 0.001

    def test_spawn_model_with_namespace(self):
        """Test spawning model with custom namespace."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.spawn_model(
                "test_robot",
                namespace="robot_1"
            )

        assert result.success is True
        assert result.data["namespace"] == "robot_1"
        assert result.data["entity_name"] == "robot_1"

    def test_spawn_model_real_mode_success(self):
        """Test spawning model in real mode."""
        mock_bridge = Mock()
        mock_bridge.spawn_entity.return_value = True

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.spawn_model(
                    "test_robot",
                    x=1.0,
                    y=2.0,
                    z=0.5
                )

        assert result.success is True
        assert result.data["model_name"] == "test_robot"
        mock_bridge.spawn_entity.assert_called_once()

    def test_spawn_model_invalid_name(self):
        """Test spawning model with invalid name."""
        result = model_management.spawn_model("")

        assert result.success is False

    def test_spawn_model_invalid_position(self):
        """Test spawning model with invalid position."""
        result = model_management.spawn_model(
            "test_robot",
            x=float('nan')
        )

        assert result.success is False

    def test_spawn_model_gazebo_error(self):
        """Test spawn when GazeboMCPError occurs."""
        mock_bridge = Mock()
        mock_bridge.spawn_entity.side_effect = GazeboMCPError(
            "Spawn service unavailable",
            error_code="SERVICE_ERROR"
        )

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.spawn_model("test_robot")

        assert result.success is False
        assert result.error_code == "SERVICE_ERROR"


class TestDeleteModel:
    """Tests for delete_model()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_delete_model_mock_mode(self):
        """Test deleting model in mock mode."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.delete_model("test_robot")

        assert result.success is True
        assert result.data["model_name"] == "test_robot"
        assert "note" in result.data
        assert "Mock deletion" in result.data["note"]

    def test_delete_model_real_mode_success(self):
        """Test deleting model in real mode."""
        mock_bridge = Mock()
        mock_bridge.delete_entity.return_value = True

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.delete_model("test_robot")

        assert result.success is True
        assert result.data["model_name"] == "test_robot"
        mock_bridge.delete_entity.assert_called_once()

    def test_delete_model_real_mode_failure(self):
        """Test deleting model when bridge fails."""
        mock_bridge = Mock()
        mock_bridge.delete_entity.return_value = False

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.delete_model("test_robot")

        assert result.success is False
        assert result.error_code == "DELETE_FAILED"

    def test_delete_model_invalid_name(self):
        """Test deleting model with invalid name."""
        result = model_management.delete_model("")

        assert result.success is False

    def test_delete_model_not_found(self):
        """Test deleting non-existent model."""
        mock_bridge = Mock()
        mock_bridge.delete_entity.side_effect = ModelNotFoundError("test_robot")

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.delete_model("test_robot")

        assert result.success is False


class TestGetModelState:
    """Tests for get_model_state()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_get_model_state_mock_mode_concise(self):
        """Test getting model state in mock mode with concise format."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.get_model_state("test_robot", response_format="concise")

        assert result.success is True
        assert result.data["name"] == "test_robot"
        assert "position" in result.data
        assert "orientation" in result.data
        assert "note" in result.data

    def test_get_model_state_mock_mode_detailed(self):
        """Test getting model state in mock mode with detailed format."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.get_model_state("test_robot", response_format="detailed")

        assert result.success is True
        assert "velocity" in result.data
        # Detailed format includes same fields as concise in mock mode

    def test_get_model_state_real_mode_success(self):
        """Test getting model state in real mode."""
        mock_bridge = Mock()
        mock_model_state = Mock()
        mock_model_state.name = "test_robot"
        mock_model_state.pose = {
            "position": {"x": 1.0, "y": 2.0, "z": 0.5},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }
        mock_model_state.twist = {
            "linear": {"x": 0.1, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.2}
        }
        mock_bridge.get_model_state.return_value = mock_model_state

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.get_model_state("test_robot")

        assert result.success is True
        assert result.data["name"] == "test_robot"
        mock_bridge.get_model_state.assert_called_once()

    def test_get_model_state_invalid_name(self):
        """Test getting state with invalid model name."""
        result = model_management.get_model_state("")

        assert result.success is False

    def test_get_model_state_not_found(self):
        """Test getting state of non-existent model."""
        mock_bridge = Mock()
        mock_bridge.get_model_state.side_effect = ModelNotFoundError("test_robot")

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.get_model_state("test_robot")

        assert result.success is False


class TestSetModelState:
    """Tests for set_model_state()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_set_model_state_mock_mode_pose_only(self):
        """Test setting model state in mock mode with pose only."""
        pose = {
            "position": {"x": 2.0, "y": 3.0, "z": 1.0},
            "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 1.57}
        }

        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.set_model_state("test_robot", pose=pose)

        assert result.success is True
        assert result.data["model"] == "test_robot"
        assert "note" in result.data

    def test_set_model_state_mock_mode_twist_only(self):
        """Test setting model state with twist only."""
        twist = {
            "linear": {"x": 0.5, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.3}
        }

        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.set_model_state("test_robot", twist=twist)

        assert result.success is True

    def test_set_model_state_mock_mode_both(self):
        """Test setting both pose and twist."""
        pose = {
            "position": {"x": 1.0, "y": 1.0, "z": 0.5}
        }
        twist = {
            "linear": {"x": 0.2, "y": 0.0, "z": 0.0}
        }

        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.set_model_state(
                "test_robot",
                pose=pose,
                twist=twist
            )

        assert result.success is True

    def test_set_model_state_real_mode_success(self):
        """Test setting model state in real mode."""
        mock_bridge = Mock()
        mock_bridge.set_entity_state.return_value = True

        pose = {
            "position": {"x": 2.0, "y": 3.0, "z": 1.0}
        }

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.set_model_state("test_robot", pose=pose)

        assert result.success is True
        mock_bridge.set_entity_state.assert_called_once()

    def test_set_model_state_no_pose_no_twist(self):
        """Test setting state with neither pose nor twist."""
        result = model_management.set_model_state("test_robot")

        assert result.success is False
        assert "pose" in result.error.lower() or "twist" in result.error.lower()

    def test_set_model_state_invalid_name(self):
        """Test setting state with invalid model name."""
        pose = {"position": {"x": 1.0, "y": 1.0, "z": 0.5}}
        result = model_management.set_model_state("", pose=pose)

        assert result.success is False

    def test_set_model_state_invalid_pose(self):
        """Test setting state with invalid pose values."""
        pose = {
            "position": {"x": float('inf'), "y": 0.0, "z": 0.0}
        }

        result = model_management.set_model_state("test_robot", pose=pose)

        assert result.success is False

    def test_set_model_state_quaternion_orientation(self):
        """Test setting state with quaternion orientation."""
        pose = {
            "position": {"x": 1.0, "y": 1.0, "z": 0.5},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.707, "w": 0.707}
        }

        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.set_model_state("test_robot", pose=pose)

        assert result.success is True

    def test_set_model_state_gazebo_error(self):
        """Test setting state when GazeboMCPError occurs."""
        mock_bridge = Mock()
        mock_bridge.set_entity_state.side_effect = GazeboMCPError(
            "State service unavailable",
            error_code="SERVICE_ERROR"
        )

        pose = {"position": {"x": 1.0, "y": 1.0, "z": 0.5}}

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.set_model_state("test_robot", pose=pose)

        assert result.success is False
        assert result.error_code == "SERVICE_ERROR"


class TestBridgeConnection:
    """Tests for get_bridge() and use_real_gazebo() helpers in _bridge_helper."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_use_real_gazebo_success(self):
        """Test use_real_gazebo returns True when bridge available."""
        with patch.object(_bridge_helper, 'get_bridge', return_value=Mock()):
            result = _bridge_helper.use_real_gazebo()

        assert result is True

    def test_use_real_gazebo_failure(self):
        """Test use_real_gazebo returns False when bridge unavailable."""
        with patch.object(_bridge_helper, 'get_bridge', side_effect=ROS2NotConnectedError("Not connected")):
            result = _bridge_helper.use_real_gazebo()

        assert result is False

    def test_get_bridge_creates_singleton(self):
        """Test get_bridge creates and reuses singleton bridge."""
        mock_conn_mgr = Mock()
        mock_node = Mock()
        mock_conn_mgr.get_node.return_value = mock_node

        with patch('gazebo_mcp.tools._bridge_helper.ConnectionManager', return_value=mock_conn_mgr):
            with patch('gazebo_mcp.tools._bridge_helper.GazeboBridgeNode') as MockBridge:
                mock_bridge = Mock()
                MockBridge.return_value = mock_bridge

                # First call creates bridge:
                bridge1 = _bridge_helper.get_bridge()

                # Second call reuses bridge:
                bridge2 = _bridge_helper.get_bridge()

                assert bridge1 is bridge2
                MockBridge.assert_called_once()

    def test_get_bridge_connection_failure(self):
        """Test get_bridge raises ROS2NotConnectedError on failure."""
        with patch('gazebo_mcp.tools._bridge_helper.ConnectionManager', side_effect=RuntimeError("Connection failed")):
            with pytest.raises(ROS2NotConnectedError) as exc_info:
                _bridge_helper.get_bridge()

            assert "Failed to connect to ROS2/Gazebo" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration-style tests for common workflows."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_spawn_then_get_state(self):
        """Test spawning a model then getting its state."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            # Spawn:
            result1 = model_management.spawn_model(
                "test_robot",
                x=1.0,
                y=2.0,
                z=0.5
            )
            assert result1.success is True

            # Get state:
            result2 = model_management.get_model_state("test_robot")
            assert result2.success is True

    def test_spawn_move_delete(self):
        """Test complete lifecycle: spawn, move, delete."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            # Spawn:
            result1 = model_management.spawn_model("test_robot")
            assert result1.success is True

            # Move:
            result2 = model_management.set_model_state(
                "test_robot",
                pose={"position": {"x": 5.0, "y": 5.0, "z": 0.5}}
            )
            assert result2.success is True

            # Delete:
            result3 = model_management.delete_model("test_robot")
            assert result3.success is True

    def test_list_after_spawn(self):
        """Test listing models returns spawned models."""
        mock_bridge = Mock()
        mock_bridge.spawn_entity.return_value = True

        mock_model_state = Mock()
        mock_model_state.name = "test_robot"
        mock_model_state.state = "active"
        mock_model_state.pose = {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }
        mock_model_state.twist = {
            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0}
        }
        mock_bridge.get_model_list.return_value = [mock_model_state]

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                # Spawn:
                model_management.spawn_model("test_robot")

                # List should show the spawned model:
                result = model_management.list_models(response_format="concise")
                assert result.success is True
                assert len(result.data["models"]) == 1
                assert result.data["models"][0]["name"] == "test_robot"


class TestApplyForce:
    """Tests for apply_force()."""

    def setup_method(self):
        """Reset module state before each test."""
        _bridge_helper._connection_manager = None
        _bridge_helper._bridge_node = None

    def test_apply_force_mock_mode_force_only(self):
        """Test apply_force with force vector in mock mode."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.apply_force(
                "robot1", force={"x": 10.0, "y": 0.0, "z": 0.0}
            )

        assert result.success is True
        assert result.data["applied"] is False
        assert result.data["force"]["x"] == 10.0
        assert result.data["torque"] == {"x": 0.0, "y": 0.0, "z": 0.0}
        assert "note" in result.data

    def test_apply_force_mock_mode_torque_only(self):
        """Test apply_force with torque vector only in mock mode."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.apply_force(
                "robot1", torque={"x": 0.0, "y": 0.0, "z": 5.0}
            )

        assert result.success is True
        assert result.data["torque"]["z"] == 5.0
        assert result.data["force"] == {"x": 0.0, "y": 0.0, "z": 0.0}

    def test_apply_force_no_force_or_torque_returns_error(self):
        """Test apply_force fails when neither force nor torque provided."""
        result = model_management.apply_force("robot1")

        assert result.success is False
        assert result.error_code == "MISSING_PARAMETER"
        assert len(result.suggestions) > 0

    def test_apply_force_default_duration(self):
        """Test apply_force uses default 0.1s duration."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.apply_force(
                "robot1", force={"x": 5.0, "y": 0.0, "z": 0.0}
            )

        assert result.data["duration_sec"] == 0.1

    def test_apply_force_custom_duration_clamped(self):
        """Test apply_force clamps duration to minimum 0.001s."""
        with patch.object(model_management, 'use_real_gazebo', return_value=False):
            result = model_management.apply_force(
                "robot1",
                force={"x": 1.0, "y": 0.0, "z": 0.0},
                duration=0.0,
            )

        assert result.success is True
        assert result.data["duration_sec"] == 0.001

    def test_apply_force_real_mode_success(self):
        """Test apply_force calls bridge.apply_wrench in real mode."""
        mock_bridge = Mock()
        mock_bridge.apply_wrench.return_value = True

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.apply_force(
                    "robot1",
                    force={"x": 10.0, "y": 0.0, "z": 0.0},
                    torque={"x": 0.0, "y": 0.0, "z": 2.0},
                    duration=0.5,
                )

        assert result.success is True
        assert result.data["applied"] is True
        mock_bridge.apply_wrench.assert_called_once_with(
            model_name="robot1",
            force=(10.0, 0.0, 0.0),
            torque=(0.0, 0.0, 2.0),
            duration=0.5,
            world="default",
        )

    def test_apply_force_real_mode_failure(self):
        """Test apply_force handles bridge failure."""
        mock_bridge = Mock()
        mock_bridge.apply_wrench.return_value = False

        with patch.object(model_management, 'use_real_gazebo', return_value=True):
            with patch.object(model_management, 'get_bridge', return_value=mock_bridge):
                result = model_management.apply_force(
                    "robot1", force={"x": 10.0, "y": 0.0, "z": 0.0}
                )

        assert result.success is False
        assert result.error_code == "APPLY_WRENCH_FAILED"
        assert len(result.suggestions) > 0

    def test_apply_force_handles_exception(self):
        """Test apply_force handles unexpected exceptions."""
        with patch.object(model_management, 'use_real_gazebo', side_effect=RuntimeError("unexpected")):
            result = model_management.apply_force(
                "robot1", force={"x": 1.0, "y": 0.0, "z": 0.0}
            )

        assert result.success is False
        assert result.error_code == "APPLY_FORCE_ERROR"
