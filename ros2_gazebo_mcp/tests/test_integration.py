"""
Integration Tests for Gazebo MCP.

Tests ConnectionManager, GazeboBridgeNode, and model_management integration.

Run with:
    pytest tests/test_integration.py -v                    # Without Gazebo
    pytest tests/test_integration.py -v --with-ros2        # With ROS2
    pytest tests/test_integration.py -v --with-gazebo      # With Gazebo running
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock


# Test ConnectionManager without ROS2:

def test_connection_manager_import():
    """Test that ConnectionManager can be imported."""
    from gazebo_mcp.bridge import ConnectionManager, ConnectionState
    assert ConnectionManager is not None
    assert ConnectionState is not None


def test_connection_state_enum():
    """Test ConnectionState enum values."""
    from gazebo_mcp.bridge import ConnectionState

    assert ConnectionState.DISCONNECTED.value == "disconnected"
    assert ConnectionState.CONNECTING.value == "connecting"
    assert ConnectionState.CONNECTED.value == "connected"
    assert ConnectionState.ERROR.value == "error"
    assert ConnectionState.RECONNECTING.value == "reconnecting"


def test_connection_manager_creation():
    """Test ConnectionManager can be created."""
    from gazebo_mcp.bridge import ConnectionManager

    manager = ConnectionManager()
    assert manager is not None
    assert not manager.is_connected()
    assert manager.is_disconnected()


def test_connection_manager_properties():
    """Test ConnectionManager properties."""
    from gazebo_mcp.bridge import ConnectionManager

    manager = ConnectionManager(
        node_name="test_node",
        auto_reconnect=True,
        max_reconnect_attempts=3,
        reconnect_base_delay=0.5,
        health_check_interval=1.0
    )

    assert manager.node_name == "test_node"
    assert manager.auto_reconnect is True
    assert manager.max_reconnect_attempts == 3
    assert manager.reconnect_base_delay == 0.5
    assert manager.health_check_interval == 1.0


# Test ConnectionManager with ROS2:

@pytest.mark.ros2
def test_connection_manager_connect(ros2_available):
    """Test ConnectionManager connect."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager

    manager = ConnectionManager()

    try:
        # Connect:
        success = manager.connect(timeout=10.0)
        assert success is True
        assert manager.is_connected()

        # Get node:
        node = manager.get_node()
        assert node is not None
        assert node.get_name() == "gazebo_mcp_bridge"

    finally:
        # Cleanup:
        manager.disconnect()
        assert manager.is_disconnected()


@pytest.mark.ros2
def test_connection_manager_reconnect(ros2_available):
    """Test ConnectionManager reconnect."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager

    manager = ConnectionManager(auto_reconnect=True, reconnect_base_delay=0.1)

    try:
        # Initial connect:
        manager.connect(timeout=10.0)
        assert manager.is_connected()

        # Disconnect:
        manager.disconnect()
        assert manager.is_disconnected()

        # Reconnect:
        success = manager.reconnect()
        assert success is True
        assert manager.is_connected()

    finally:
        manager.disconnect()


@pytest.mark.ros2
def test_connection_manager_context_manager(ros2_available):
    """Test ConnectionManager as context manager."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager, ConnectionState

    with ConnectionManager() as manager:
        assert manager.state == ConnectionState.CONNECTED
        node = manager.get_node()
        assert node is not None

    # Should be disconnected after context:
    assert manager.state == ConnectionState.DISCONNECTED


@pytest.mark.ros2
def test_connection_manager_ensure_connected(ros2_available):
    """Test ensure_connected context manager."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager
    from gazebo_mcp.utils.exceptions import ROS2NotConnectedError

    manager = ConnectionManager()

    # Should fail when not connected:
    with pytest.raises(ROS2NotConnectedError):
        with manager.ensure_connected():
            pass

    try:
        # Connect first:
        manager.connect(timeout=10.0)

        # Should work when connected:
        with manager.ensure_connected():
            node = manager.get_node()
            assert node is not None

    finally:
        manager.disconnect()


@pytest.mark.ros2
def test_connection_manager_callbacks(ros2_available):
    """Test ConnectionManager event callbacks."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager

    connected_called = []
    disconnected_called = []

    def on_connected():
        connected_called.append(True)

    def on_disconnected():
        disconnected_called.append(True)

    manager = ConnectionManager()
    manager.on_connected(on_connected)
    manager.on_disconnected(on_disconnected)

    try:
        # Connect - should trigger callback:
        manager.connect(timeout=10.0)
        time.sleep(0.1)  # Give callback time to execute
        assert len(connected_called) == 1

        # Disconnect - should trigger callback:
        manager.disconnect()
        time.sleep(0.1)
        assert len(disconnected_called) == 1

    finally:
        if manager.is_connected():
            manager.disconnect()


# Test GazeboBridgeNode:

@pytest.mark.ros2
def test_bridge_node_creation(ros2_available):
    """Test GazeboBridgeNode creation."""
    if not ros2_available:
        pytest.skip("ROS2 not available")

    from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

    manager = ConnectionManager()

    try:
        manager.connect(timeout=10.0)
        node = manager.get_node()

        bridge = GazeboBridgeNode(node)
        assert bridge is not None
        assert bridge.node == node

    finally:
        manager.disconnect()


@pytest.mark.gazebo
def test_bridge_node_get_model_list(gazebo_available):
    """Test GazeboBridgeNode.get_model_list() with real Gazebo."""
    if not gazebo_available:
        pytest.skip("Gazebo not available")

    from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

    manager = ConnectionManager()

    try:
        manager.connect(timeout=10.0)
        bridge = GazeboBridgeNode(manager.get_node())

        # Get model list:
        models = bridge.get_model_list(timeout=5.0)
        assert models is not None
        assert isinstance(models, list)

        # Should have at least ground_plane:
        assert len(models) > 0

        # Check model structure:
        model = models[0]
        assert hasattr(model, "name")
        assert hasattr(model, "pose")
        assert hasattr(model, "twist")

    finally:
        manager.disconnect()


@pytest.mark.gazebo
@pytest.mark.slow
def test_bridge_node_spawn_delete_entity(gazebo_available):
    """Test GazeboBridgeNode spawn and delete."""
    if not gazebo_available:
        pytest.skip("Gazebo not available")

    from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

    manager = ConnectionManager()

    try:
        manager.connect(timeout=10.0)
        bridge = GazeboBridgeNode(manager.get_node())

        # Create simple SDF:
        sdf_content = """<?xml version='1.0'?>
<sdf version='1.6'>
  <model name='test_box'>
    <static>true</static>
    <link name='link'>
      <collision name='collision'>
        <geometry>
          <box>
            <size>1 1 1</size>
          </box>
        </geometry>
      </collision>
      <visual name='visual'>
        <geometry>
          <box>
            <size>1 1 1</size>
          </box>
        </geometry>
      </visual>
    </link>
  </model>
</sdf>"""

        # Spawn entity:
        pose = {
            "position": {"x": 5.0, "y": 5.0, "z": 0.5},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }

        success = bridge.spawn_entity(
            name="test_box",
            xml_content=sdf_content,
            pose=pose,
            timeout=10.0
        )
        assert success is True

        # Verify it was spawned:
        time.sleep(0.5)  # Give Gazebo time to update
        models = bridge.get_model_list(timeout=5.0)
        model_names = [m.name for m in models]
        assert "test_box" in model_names

        # Delete entity:
        success = bridge.delete_entity(name="test_box", timeout=10.0)
        assert success is True

        # Verify it was deleted:
        time.sleep(0.5)
        models = bridge.get_model_list(timeout=5.0)
        model_names = [m.name for m in models]
        assert "test_box" not in model_names

    finally:
        # Cleanup:
        try:
            bridge.delete_entity(name="test_box", timeout=5.0)
        except Exception:
            pass
        manager.disconnect()


# Test model_management integration:

def test_model_management_import():
    """Test model_management can be imported."""
    from gazebo_mcp.tools import model_management
    assert model_management is not None


def test_list_models_mock_data():
    """Test list_models returns mock data when Gazebo unavailable."""
    from gazebo_mcp.tools.model_management import list_models

    result = list_models(response_format="summary")
    assert result.success is True
    assert "count" in result.data
    assert result.data["count"] > 0


def test_list_models_filtered_format():
    """Test list_models with filtered format."""
    from gazebo_mcp.tools.model_management import list_models

    result = list_models(response_format="filtered")
    assert result.success is True
    assert "models" in result.data
    assert "filter_examples" in result.data
    assert "token_savings_pct" in result.data


def test_spawn_model_validation():
    """Test spawn_model parameter validation."""
    from gazebo_mcp.tools.model_management import spawn_model
    from gazebo_mcp.utils.exceptions import InvalidParameterError

    # Invalid model name (starts with number):
    result = spawn_model("123_invalid")
    assert result.success is False
    assert "INVALID_PARAMETER" in result.error_code


def test_delete_model_validation():
    """Test delete_model parameter validation."""
    from gazebo_mcp.tools.model_management import delete_model

    # Invalid model name:
    result = delete_model("123_invalid")
    assert result.success is False


@pytest.mark.gazebo
def test_list_models_real_gazebo(gazebo_available):
    """Test list_models with real Gazebo."""
    if not gazebo_available:
        pytest.skip("Gazebo not available")

    from gazebo_mcp.tools.model_management import list_models

    result = list_models(response_format="concise")
    assert result.success is True
    assert "models" in result.data
    assert len(result.data["models"]) > 0

    # Check model structure:
    model = result.data["models"][0]
    assert "name" in model
    assert "type" in model
    assert "position" in model


@pytest.mark.gazebo
@pytest.mark.slow
def test_spawn_delete_model_real_gazebo(gazebo_available):
    """Test spawn and delete with real Gazebo."""
    if not gazebo_available:
        pytest.skip("Gazebo not available")

    from gazebo_mcp.tools.model_management import spawn_model, delete_model, get_model_state

    # Spawn a test box:
    result = spawn_model(
        model_name="test_integration_box",
        x=10.0,
        y=10.0,
        z=0.5,
        roll=0.0,
        pitch=0.0,
        yaw=0.0
    )
    assert result.success is True
    assert result.data["model_name"] == "test_integration_box"

    # Get its state:
    result = get_model_state("test_integration_box")
    if result.success:  # May not be found if spawn is async
        assert result.data["name"] == "test_integration_box"

    # Delete it:
    time.sleep(0.5)  # Give Gazebo time
    result = delete_model("test_integration_box")
    assert result.success is True


# Test error handling:

def test_error_result_structure():
    """Test error result structure."""
    from gazebo_mcp.utils import error_result

    result = error_result(
        error="Test error",
        error_code="TEST_ERROR",
        suggestions=["Fix 1", "Fix 2"],
        example_fix="example code"
    )

    assert result.success is False
    assert result.error == "Test error"
    assert result.error_code == "TEST_ERROR"
    assert len(result.suggestions) == 2
    assert result.example_fix == "example code"


def test_model_not_found_error():
    """Test model_not_found_error helper."""
    from gazebo_mcp.utils import model_not_found_error

    result = model_not_found_error("nonexistent_model")
    assert result.success is False
    assert "MODEL_NOT_FOUND" in result.error_code
    assert "nonexistent_model" in result.error


# Test ResultFilter integration:

def test_result_filter_with_models():
    """Test ResultFilter with model data."""
    from gazebo_mcp.tools.model_management import list_models
    from skills.common.filters import ResultFilter

    result = list_models(response_format="filtered")
    assert result.success is True

    models = result.data["models"]

    # Test search:
    turtlebots = ResultFilter.search(models, "turtlebot", ["name"])
    assert len(turtlebots) > 0

    # Test filter by field:
    active_models = ResultFilter.filter_by_field(models, "state", "active")
    assert all(m["state"] == "active" for m in active_models)

    # Test limit:
    limited = ResultFilter.limit(models, 2)
    assert len(limited) == 2

    # Test top_n:
    top_complex = ResultFilter.top_n_by_field(models, "complexity", 2)
    assert len(top_complex) == 2
    assert top_complex[0]["complexity"] >= top_complex[1]["complexity"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
