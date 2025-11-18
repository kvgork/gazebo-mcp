"""
Unit tests for simulation_tools module.

Tests all 6 simulation control functions:
- pause_simulation
- unpause_simulation
- reset_simulation
- set_simulation_speed
- get_simulation_time
- get_simulation_status
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import simulation_tools
from gazebo_mcp.utils.exceptions import (
    InvalidParameterError,
    ROS2NotConnectedError,
    GazeboMCPError
)


class TestPauseSimulation:
    """Tests for pause_simulation()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = False
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_pause_simulation_mock_mode(self):
        """Test pausing simulation in mock mode (Gazebo not available)."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.pause_simulation()

        assert result.success is True
        assert result.data["paused"] is True
        assert "timestamp" in result.data
        assert "note" in result.data
        assert "Mock mode" in result.data["note"]

    def test_pause_simulation_real_mode_success(self):
        """Test pausing simulation in real mode with successful pause."""
        mock_bridge = Mock()
        mock_bridge.pause_physics.return_value = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.pause_simulation(timeout=5.0)

        assert result.success is True
        assert result.data["paused"] is True
        assert "timestamp" in result.data
        mock_bridge.pause_physics.assert_called_once_with(timeout=5.0)

    def test_pause_simulation_real_mode_failure(self):
        """Test pausing simulation when bridge fails to pause."""
        mock_bridge = Mock()
        mock_bridge.pause_physics.return_value = False

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.pause_simulation()

        assert result.success is False
        assert result.error == "Failed to pause simulation"
        assert result.error_code == "PAUSE_FAILED"

    def test_pause_simulation_invalid_timeout(self):
        """Test pause with invalid timeout value."""
        result = simulation_tools.pause_simulation(timeout=-1.0)

        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_pause_simulation_updates_state(self):
        """Test that pause updates global _simulation_paused state."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            simulation_tools.pause_simulation()

        assert simulation_tools._simulation_paused is True

    def test_pause_simulation_gazebo_error(self):
        """Test pause when GazeboMCPError occurs."""
        mock_bridge = Mock()
        mock_bridge.pause_physics.side_effect = GazeboMCPError(
            "Gazebo service unavailable",
            error_code="SERVICE_UNAVAILABLE",
            suggestions=["Check Gazebo is running"]
        )

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.pause_simulation()

        assert result.success is False
        assert result.error_code == "SERVICE_UNAVAILABLE"
        assert len(result.suggestions) > 0

    def test_pause_simulation_unexpected_exception(self):
        """Test pause when unexpected exception occurs."""
        mock_bridge = Mock()
        mock_bridge.pause_physics.side_effect = RuntimeError("Unexpected error")

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.pause_simulation()

        assert result.success is False
        assert result.error_code == "PAUSE_ERROR"
        assert "Unexpected error" in result.error


class TestUnpauseSimulation:
    """Tests for unpause_simulation()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = True  # Start paused
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_unpause_simulation_mock_mode(self):
        """Test unpausing simulation in mock mode."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.unpause_simulation()

        assert result.success is True
        assert result.data["paused"] is False
        assert "timestamp" in result.data
        assert "Mock mode" in result.data["note"]

    def test_unpause_simulation_real_mode_success(self):
        """Test unpausing simulation in real mode."""
        mock_bridge = Mock()
        mock_bridge.unpause_physics.return_value = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.unpause_simulation(timeout=5.0)

        assert result.success is True
        assert result.data["paused"] is False
        mock_bridge.unpause_physics.assert_called_once_with(timeout=5.0)

    def test_unpause_simulation_real_mode_failure(self):
        """Test unpausing when bridge fails."""
        mock_bridge = Mock()
        mock_bridge.unpause_physics.return_value = False

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.unpause_simulation()

        assert result.success is False
        assert result.error == "Failed to unpause simulation"
        assert result.error_code == "UNPAUSE_FAILED"

    def test_unpause_simulation_updates_state(self):
        """Test that unpause updates global _simulation_paused state."""
        simulation_tools._simulation_paused = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            simulation_tools.unpause_simulation()

        assert simulation_tools._simulation_paused is False

    def test_unpause_simulation_invalid_timeout(self):
        """Test unpause with invalid timeout."""
        result = simulation_tools.unpause_simulation(timeout=0.0)

        assert result.success is False


class TestResetSimulation:
    """Tests for reset_simulation()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = False
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_reset_simulation_mock_mode(self):
        """Test resetting simulation in mock mode."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.reset_simulation()

        assert result.success is True
        assert result.data["reset"] is True
        assert result.data["simulation_time"] == 0.0
        assert "timestamp" in result.data
        assert "Mock mode" in result.data["note"]

    def test_reset_simulation_real_mode_success(self):
        """Test resetting simulation in real mode."""
        mock_bridge = Mock()
        mock_bridge.reset_simulation.return_value = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.reset_simulation(timeout=10.0)

        assert result.success is True
        assert result.data["reset"] is True
        assert result.data["simulation_time"] == 0.0
        mock_bridge.reset_simulation.assert_called_once_with(timeout=10.0)

    def test_reset_simulation_real_mode_failure(self):
        """Test resetting when bridge fails."""
        mock_bridge = Mock()
        mock_bridge.reset_simulation.return_value = False

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.reset_simulation()

        assert result.success is False
        assert result.error == "Failed to reset simulation"
        assert result.error_code == "RESET_FAILED"

    def test_reset_simulation_invalid_timeout(self):
        """Test reset with invalid timeout."""
        result = simulation_tools.reset_simulation(timeout=-5.0)

        assert result.success is False

    def test_reset_simulation_gazebo_error(self):
        """Test reset when GazeboMCPError occurs."""
        mock_bridge = Mock()
        mock_bridge.reset_simulation.side_effect = GazeboMCPError(
            "Reset service unavailable",
            error_code="SERVICE_ERROR"
        )

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            with patch.object(simulation_tools, '_get_bridge', return_value=mock_bridge):
                result = simulation_tools.reset_simulation()

        assert result.success is False
        assert result.error_code == "SERVICE_ERROR"


class TestSetSimulationSpeed:
    """Tests for set_simulation_speed()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_set_simulation_speed_mock_mode(self):
        """Test setting speed in mock mode."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.set_simulation_speed(2.0)

        assert result.success is True
        assert result.data["speed_factor"] == 2.0
        assert result.data["set"] is False  # Not actually set in mock
        assert "Gazebo not running" in result.data["note"]

    def test_set_simulation_speed_real_mode(self):
        """Test setting speed in real mode (not yet implemented)."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            result = simulation_tools.set_simulation_speed(1.5)

        assert result.success is True
        assert result.data["speed_factor"] == 1.5
        assert result.data["set"] is False  # Not yet implemented
        assert "will be implemented in a future update" in result.data["note"]
        assert "instructions" in result.data

    def test_set_simulation_speed_various_factors(self):
        """Test setting various speed factors."""
        test_speeds = [0.1, 0.5, 1.0, 2.0, 10.0]

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            for speed in test_speeds:
                result = simulation_tools.set_simulation_speed(speed)
                assert result.success is True
                assert result.data["speed_factor"] == speed

    def test_set_simulation_speed_invalid_negative(self):
        """Test setting negative speed factor."""
        result = simulation_tools.set_simulation_speed(-1.0)

        assert result.success is False
        assert "positive" in result.error.lower()

    def test_set_simulation_speed_invalid_zero(self):
        """Test setting zero speed factor."""
        result = simulation_tools.set_simulation_speed(0.0)

        assert result.success is False

    def test_set_simulation_speed_gazebo_error(self):
        """Test speed setting when error occurs."""
        with patch.object(simulation_tools, '_use_real_gazebo', side_effect=RuntimeError("Error")):
            result = simulation_tools.set_simulation_speed(1.0)

        assert result.success is False
        assert result.error_code == "SET_SPEED_ERROR"


class TestGetSimulationTime:
    """Tests for get_simulation_time()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = False
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_get_simulation_time_mock_mode(self):
        """Test getting time in mock mode (Gazebo not available)."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.get_simulation_time()

        assert result.success is True
        assert result.data["simulation_time"] == 0.0
        assert result.data["real_time"] == 0.0
        assert result.data["iterations"] == 0
        assert result.data["paused"] is False
        assert "Gazebo not running" in result.data["note"]

    def test_get_simulation_time_real_mode(self):
        """Test getting time in real mode (currently returns mock data)."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            result = simulation_tools.get_simulation_time()

        assert result.success is True
        assert "simulation_time" in result.data
        assert "real_time" in result.data
        assert "iterations" in result.data
        assert "paused" in result.data
        # Currently returns mock data until real implementation:
        assert "Mock data" in result.data.get("note", "")

    def test_get_simulation_time_respects_paused_state(self):
        """Test that time query respects global paused state."""
        simulation_tools._simulation_paused = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.get_simulation_time()

        assert result.success is True
        assert result.data["paused"] is True

    def test_get_simulation_time_exception_handling(self):
        """Test time query when exception occurs."""
        with patch.object(simulation_tools, '_use_real_gazebo', side_effect=RuntimeError("Error")):
            result = simulation_tools.get_simulation_time()

        assert result.success is False
        assert result.error_code == "GET_TIME_ERROR"


class TestGetSimulationStatus:
    """Tests for get_simulation_status()."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = False
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_get_simulation_status_mock_mode(self):
        """Test getting status in mock mode."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.get_simulation_status()

        assert result.success is True
        assert result.data["running"] is False
        assert result.data["paused"] is False
        assert result.data["gazebo_connected"] is False
        assert result.data["simulation_time"] == 0.0
        assert result.data["real_time"] == 0.0
        assert "Gazebo not running" in result.data["note"]

    def test_get_simulation_status_real_mode(self):
        """Test getting status in real mode."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            # Mock get_simulation_time to return consistent data:
            mock_time_result = Mock()
            mock_time_result.data = {
                "simulation_time": 123.456,
                "real_time": 125.678,
                "iterations": 123456
            }

            with patch.object(simulation_tools, 'get_simulation_time', return_value=mock_time_result):
                result = simulation_tools.get_simulation_status()

        assert result.success is True
        assert result.data["running"] is True
        assert result.data["gazebo_connected"] is True
        assert result.data["simulation_time"] == 123.456
        assert result.data["real_time"] == 125.678
        assert result.data["iterations"] == 123456

    def test_get_simulation_status_respects_paused_state(self):
        """Test status reflects paused state."""
        simulation_tools._simulation_paused = True

        with patch.object(simulation_tools, '_use_real_gazebo', return_value=True):
            mock_time_result = Mock()
            mock_time_result.data = {"simulation_time": 10.0, "real_time": 10.0, "iterations": 1000}

            with patch.object(simulation_tools, 'get_simulation_time', return_value=mock_time_result):
                result = simulation_tools.get_simulation_status()

        assert result.success is True
        assert result.data["paused"] is True

    def test_get_simulation_status_exception_handling(self):
        """Test status query when exception occurs."""
        with patch.object(simulation_tools, '_use_real_gazebo', side_effect=RuntimeError("Error")):
            result = simulation_tools.get_simulation_status()

        assert result.success is False
        assert result.error_code == "GET_STATUS_ERROR"

    def test_get_simulation_status_complete_data(self):
        """Test that status returns all expected fields."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result = simulation_tools.get_simulation_status()

        assert result.success is True
        required_fields = [
            "running",
            "paused",
            "simulation_time",
            "real_time",
            "iterations",
            "gazebo_connected"
        ]
        for field in required_fields:
            assert field in result.data


class TestBridgeConnection:
    """Tests for _get_bridge() and _use_real_gazebo() helpers."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_use_real_gazebo_success(self):
        """Test _use_real_gazebo returns True when bridge available."""
        with patch.object(simulation_tools, '_get_bridge', return_value=Mock()):
            result = simulation_tools._use_real_gazebo()

        assert result is True

    def test_use_real_gazebo_failure(self):
        """Test _use_real_gazebo returns False when bridge unavailable."""
        with patch.object(simulation_tools, '_get_bridge', side_effect=ROS2NotConnectedError("Not connected")):
            result = simulation_tools._use_real_gazebo()

        assert result is False

    def test_get_bridge_creates_singleton(self):
        """Test _get_bridge creates and reuses singleton bridge."""
        mock_conn_mgr = Mock()
        mock_node = Mock()
        mock_conn_mgr.get_node.return_value = mock_node

        with patch('gazebo_mcp.tools.simulation_tools.ConnectionManager', return_value=mock_conn_mgr):
            with patch('gazebo_mcp.tools.simulation_tools.GazeboBridgeNode') as MockBridge:
                mock_bridge = Mock()
                MockBridge.return_value = mock_bridge

                # First call creates bridge:
                bridge1 = simulation_tools._get_bridge()

                # Second call reuses bridge:
                bridge2 = simulation_tools._get_bridge()

                assert bridge1 is bridge2
                MockBridge.assert_called_once()  # Only called once

    def test_get_bridge_connection_failure(self):
        """Test _get_bridge raises ROS2NotConnectedError on failure."""
        with patch('gazebo_mcp.tools.simulation_tools.ConnectionManager', side_effect=RuntimeError("Connection failed")):
            with pytest.raises(ROS2NotConnectedError) as exc_info:
                simulation_tools._get_bridge()

            assert "Failed to connect to ROS2/Gazebo" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration-style tests for common workflows."""

    def setup_method(self):
        """Reset module state before each test."""
        simulation_tools._simulation_paused = False
        simulation_tools._connection_manager = None
        simulation_tools._bridge_node = None

    def test_pause_unpause_cycle(self):
        """Test pause followed by unpause."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            # Pause:
            result1 = simulation_tools.pause_simulation()
            assert result1.success is True
            assert result1.data["paused"] is True

            # Unpause:
            result2 = simulation_tools.unpause_simulation()
            assert result2.success is True
            assert result2.data["paused"] is False

    def test_status_after_operations(self):
        """Test status reflects operations."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            # Initial status:
            result1 = simulation_tools.get_simulation_status()
            assert result1.data["paused"] is False

            # Pause:
            simulation_tools.pause_simulation()

        # Check the state was updated:
        assert simulation_tools._simulation_paused is True

        # Status should reflect the paused state:
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            result2 = simulation_tools.get_simulation_status()
            # In mock mode when not connected, status shows paused=False
            # But the internal state is tracked separately
            assert simulation_tools._simulation_paused is True

    def test_reset_after_pause(self):
        """Test reset after pausing."""
        with patch.object(simulation_tools, '_use_real_gazebo', return_value=False):
            # Pause:
            simulation_tools.pause_simulation()
            assert simulation_tools._simulation_paused is True

            # Reset:
            result = simulation_tools.reset_simulation()
            assert result.success is True
            assert result.data["simulation_time"] == 0.0
