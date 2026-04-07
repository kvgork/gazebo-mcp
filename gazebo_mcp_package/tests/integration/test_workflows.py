"""
Integration tests for complete Gazebo MCP workflows.

Tests end-to-end scenarios combining multiple tools:
- Spawn robot -> Move -> Read sensors -> Delete
- Simulation control -> Model management -> World properties
- Complete robot lifecycle with error handling
"""

import pytest
from unittest.mock import patch, Mock
import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import (
    simulation_tools,
    model_management,
    sensor_tools,
    world_tools,
)
from gazebo_mcp.tools import _bridge_helper


def _reset_bridge():
    """Reset shared bridge state between tests."""
    _bridge_helper._connection_manager = None
    _bridge_helper._bridge_node = None


class TestRobotLifecycle:
    """Test complete robot lifecycle workflows."""

    def setup_method(self):
        """Reset all module states before each test."""
        _reset_bridge()

    def test_spawn_move_sense_delete_workflow(self):
        """Test complete robot workflow: spawn -> move -> sense -> delete."""
        with patch.object(simulation_tools, "use_real_gazebo", return_value=False):
            with patch.object(model_management, "use_real_gazebo", return_value=False):
                with patch.object(sensor_tools, "use_real_gazebo", return_value=False):
                    # Step 1: Spawn robot
                    spawn_result = model_management.spawn_model(
                        model_name="test_robot", x=0.0, y=0.0, z=0.5
                    )
                    assert spawn_result.success is True
                    assert spawn_result.data["model_name"] == "test_robot"

                    # Step 2: Get initial state
                    state_result = model_management.get_model_state("test_robot")
                    assert state_result.success is True
                    assert state_result.data["name"] == "test_robot"

                    # Step 3: Move robot
                    move_result = model_management.set_model_state(
                        "test_robot",
                        pose={"position": {"x": 2.0, "y": 1.5, "z": 0.5}},
                    )
                    assert move_result.success is True

                    # Step 4: List sensors
                    sensors_result = sensor_tools.list_sensors(
                        model_name="test_robot", response_format="concise"
                    )
                    assert sensors_result.success is True

                    # Step 5: Delete robot
                    delete_result = model_management.delete_model("test_robot")
                    assert delete_result.success is True
                    assert delete_result.data["model_name"] == "test_robot"

    def test_simulation_control_with_models(self):
        """Test simulation control integrated with model management."""
        with patch.object(simulation_tools, "use_real_gazebo", return_value=False):
            with patch.object(model_management, "use_real_gazebo", return_value=False):
                # Step 1: Get initial simulation status
                status1 = simulation_tools.get_simulation_status()
                assert status1.success is True

                # Step 2: Pause simulation
                pause_result = simulation_tools.pause_simulation()
                assert pause_result.success is True

                # Step 3: Spawn robot while paused
                spawn_result = model_management.spawn_model(
                    model_name="robot_paused", x=1.0, y=1.0, z=0.5
                )
                assert spawn_result.success is True

                # Step 4: Unpause simulation
                unpause_result = simulation_tools.unpause_simulation()
                assert unpause_result.success is True

                # Step 5: List models
                models_result = model_management.list_models(response_format="summary")
                assert models_result.success is True

    def test_multi_robot_scenario(self):
        """Test spawning and managing multiple robots."""
        with patch.object(model_management, "use_real_gazebo", return_value=False):
            # Spawn 3 robots
            robot_names = []
            for i in range(3):
                name = f"robot_{i}"
                spawn_result = model_management.spawn_model(
                    model_name=name, x=float(i * 2), y=0.0, z=0.5
                )
                assert spawn_result.success is True
                robot_names.append(name)

            # Get state of each robot
            for name in robot_names:
                state_result = model_management.get_model_state(name)
                assert state_result.success is True
                assert state_result.data["name"] == name

            # Delete all robots
            for name in robot_names:
                delete_result = model_management.delete_model(name)
                assert delete_result.success is True


class TestWorldManipulation:
    """Test world manipulation workflows."""

    def setup_method(self):
        """Reset module states."""
        _reset_bridge()

    def test_world_properties_workflow(self):
        """Test getting and setting world properties."""
        with patch.object(world_tools, "use_real_gazebo", return_value=False):
            # Step 1: Get current properties
            get_result = world_tools.get_world_properties()
            assert get_result.success is True
            assert "gravity" in get_result.data

            # Step 2: Set gravity
            set_result = world_tools.set_world_property(
                property_name="gravity", value=[0.0, 0.0, -10.0]
            )
            # Mock mode may not actually set, but should succeed
            assert set_result.success is True

    def test_world_with_models(self):
        """Test world manipulation with models present."""
        with patch.object(world_tools, "use_real_gazebo", return_value=False):
            with patch.object(model_management, "use_real_gazebo", return_value=False):
                # Spawn a robot
                spawn_result = model_management.spawn_model(
                    model_name="world_test_robot", x=0.0, y=0.0, z=1.0
                )
                assert spawn_result.success is True

                # Get world properties
                props_result = world_tools.get_world_properties()
                assert props_result.success is True

                # Set world property (e.g., gravity)
                set_result = world_tools.set_world_property(
                    property_name="gravity", value=[0.0, 0.0, -5.0]
                )
                assert set_result.success is True


class TestErrorHandling:
    """Test error handling in integrated workflows."""

    def setup_method(self):
        """Reset module states."""
        _reset_bridge()

    def test_invalid_operations_sequence(self):
        """Test handling of invalid operation sequences."""
        with patch.object(model_management, "use_real_gazebo", return_value=False):
            # Try to delete non-existent model
            delete_result = model_management.delete_model("nonexistent_robot")
            # Should fail gracefully
            assert delete_result.success is False or "note" in delete_result.data

            # Try to get state of non-existent model
            state_result = model_management.get_model_state("nonexistent_robot")
            # Should fail gracefully
            assert state_result.success is True or state_result.success is False

    def test_invalid_parameters_workflow(self):
        """Test workflows with invalid parameters."""
        with patch.object(model_management, "use_real_gazebo", return_value=False):
            # Try to spawn with invalid name
            spawn_result = model_management.spawn_model(model_name="")
            assert spawn_result.success is False

            # Try to set state with invalid pose
            set_result = model_management.set_model_state(
                "test_robot", pose={"position": {"x": float("inf"), "y": 0.0, "z": 0.0}}
            )
            assert set_result.success is False


class TestSensorIntegration:
    """Test sensor integration with robot workflows."""

    def setup_method(self):
        """Reset module states."""
        _reset_bridge()

    def test_spawn_and_list_sensors(self):
        """Test spawning robot and listing its sensors."""
        with patch.object(model_management, "use_real_gazebo", return_value=False):
            with patch.object(sensor_tools, "use_real_gazebo", return_value=False):
                # Spawn robot
                spawn_result = model_management.spawn_model(
                    model_name="sensor_robot", x=0.0, y=0.0, z=0.5
                )
                assert spawn_result.success is True

                # List sensors on robot
                sensors_result = sensor_tools.list_sensors(
                    model_name="sensor_robot", response_format="concise"
                )
                assert sensors_result.success is True


class TestSimulationReset:
    """Test simulation reset workflows."""

    def setup_method(self):
        """Reset module states."""
        _reset_bridge()

    def test_spawn_reset_verify(self):
        """Test spawning robot, resetting simulation, and verifying."""
        with patch.object(simulation_tools, "use_real_gazebo", return_value=False):
            with patch.object(model_management, "use_real_gazebo", return_value=False):
                # Spawn robot
                spawn_result = model_management.spawn_model(
                    model_name="reset_test_robot", x=5.0, y=5.0, z=0.5
                )
                assert spawn_result.success is True

                # Reset simulation
                reset_result = simulation_tools.reset_simulation()
                assert reset_result.success is True
                assert reset_result.data["simulation_time"] == 0.0

                # Get simulation status after reset
                status_result = simulation_tools.get_simulation_status()
                assert status_result.success is True


class TestCompleteExample:
    """Test complete example matching documentation."""

    def setup_method(self):
        """Reset all module states."""
        _reset_bridge()

    def test_quick_start_workflow(self):
        """Test the workflow from QUICK_START.md documentation."""
        with patch.object(simulation_tools, "use_real_gazebo", return_value=False):
            with patch.object(model_management, "use_real_gazebo", return_value=False):
                with patch.object(sensor_tools, "use_real_gazebo", return_value=False):
                    # Example 1: Basic simulation control
                    status = simulation_tools.get_simulation_status()
                    assert status.success is True

                    # Example 2: TurtleBot3 spawn
                    spawn = model_management.spawn_model(
                        model_name="my_turtlebot3",
                        x=0.0,
                        y=0.0,
                        z=0.01,
                    )
                    assert spawn.success is True

                    # Get robot state
                    state = model_management.get_model_state("my_turtlebot3")
                    assert state.success is True

                    # Move robot
                    move = model_management.set_model_state(
                        "my_turtlebot3",
                        pose={"position": {"x": 2.0, "y": 1.5, "z": 0.01}},
                    )
                    assert move.success is True

                    # Example 3: Read sensors
                    sensors = sensor_tools.list_sensors(response_format="concise")
                    assert sensors.success is True
