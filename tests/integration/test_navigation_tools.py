"""
Integration tests for Nav2 navigation tools.

Tests the integration of navigation tools with MCP server,
Nav2 action servers, and Gazebo simulation.
"""

import pytest
import asyncio
from pathlib import Path

# Import navigation tools
from gazebo_mcp.tools import navigation_tools
from gazebo_mcp.utils import OperationResult


class TestNavigationToolsBasic:
    """Basic tests that don't require Gazebo or Nav2."""

    def test_navigation_tools_import(self):
        """Test that navigation tools module can be imported."""
        assert hasattr(navigation_tools, 'spawn_turtlebot3')
        assert hasattr(navigation_tools, 'send_nav2_goal')
        assert hasattr(navigation_tools, 'get_navigation_status')
        assert hasattr(navigation_tools, 'cancel_navigation')
        assert hasattr(navigation_tools, 'set_initial_pose')

    def test_spawn_turtlebot3_signature(self):
        """Test spawn_turtlebot3 function signature."""
        import inspect
        sig = inspect.signature(navigation_tools.spawn_turtlebot3)
        params = sig.parameters

        assert 'name' in params
        assert 'variant' in params
        assert 'position' in params
        assert 'orientation' in params
        assert 'world' in params

        # Check defaults
        assert params['variant'].default == 'burger'
        assert params['position'].default == (0.0, 0.0, 0.01)

    def test_send_nav2_goal_signature(self):
        """Test send_nav2_goal function signature."""
        import inspect
        sig = inspect.signature(navigation_tools.send_nav2_goal)
        params = sig.parameters

        assert 'robot_name' in params
        assert 'goal_position' in params
        assert 'goal_orientation' in params
        assert 'timeout' in params
        assert 'wait_for_result' in params

        # Check defaults
        assert params['timeout'].default == 120.0
        assert params['wait_for_result'].default == True


@pytest.mark.integration
@pytest.mark.requires_ros2
class TestNavigationToolsWithROS2:
    """Tests that require ROS2 but not full Nav2 stack."""

    def test_spawn_turtlebot3_validation(self):
        """Test parameter validation in spawn_turtlebot3."""
        # Invalid variant
        result = navigation_tools.spawn_turtlebot3(
            name="test_robot",
            variant="invalid_variant"
        )
        assert not result.success
        assert "variant" in result.message.lower()

    def test_navigation_status_robot_not_found(self):
        """Test get_navigation_status with non-existent robot."""
        result = navigation_tools.get_navigation_status("nonexistent_robot")
        assert not result.success
        assert "not found" in result.message.lower()


@pytest.mark.integration
@pytest.mark.requires_gazebo
@pytest.mark.requires_nav2
@pytest.mark.slow
class TestNavigationToolsFullStack:
    """Full integration tests with Gazebo and Nav2."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup
        yield
        # Teardown - cleanup any spawned robots
        # (Implementation depends on available cleanup utilities)

    def test_spawn_turtlebot3_burger(self):
        """Test spawning TurtleBot3 burger."""
        result = navigation_tools.spawn_turtlebot3(
            name="test_burger",
            variant="burger",
            position=(0.0, 0.0, 0.01)
        )

        assert result.success, f"Failed to spawn: {result.message}"
        assert result.data is not None
        assert result.data["robot_name"] == "test_burger"
        assert result.data["variant"] == "burger"
        assert result.data["nav2_ready"] == True
        assert "lidar" in result.data["sensors"]

    def test_set_initial_pose(self):
        """Test setting initial pose."""
        # First spawn robot
        spawn_result = navigation_tools.spawn_turtlebot3(
            name="test_pose_robot",
            variant="burger"
        )
        assert spawn_result.success

        # Set initial pose
        result = navigation_tools.set_initial_pose(
            robot_name="test_pose_robot",
            position=(0.0, 0.0),
            orientation=0.0
        )

        assert result.success
        assert result.data is not None
        assert result.data["robot_name"] == "test_pose_robot"

    def test_send_nav2_goal_simple(self):
        """Test sending a simple navigation goal."""
        # Spawn robot
        spawn_result = navigation_tools.spawn_turtlebot3(
            name="test_nav_robot",
            variant="burger"
        )
        assert spawn_result.success

        # Set initial pose
        pose_result = navigation_tools.set_initial_pose(
            robot_name="test_nav_robot",
            position=(0.0, 0.0),
            orientation=0.0
        )
        assert pose_result.success

        # Send navigation goal
        result = navigation_tools.send_nav2_goal(
            robot_name="test_nav_robot",
            goal_position=(2.0, 0.0),
            goal_orientation=0.0,
            timeout=120.0,
            wait_for_result=True
        )

        # Check result
        assert result.success, f"Navigation failed: {result.message}"
        assert result.data is not None
        assert result.data["status"] == "succeeded"
        assert "elapsed_time" in result.data
        assert "distance_traveled" in result.data

    def test_navigation_status_tracking(self):
        """Test navigation status tracking."""
        # Spawn and setup robot
        spawn_result = navigation_tools.spawn_turtlebot3(
            name="test_status_robot",
            variant="burger"
        )
        assert spawn_result.success

        # Check initial status
        status = navigation_tools.get_navigation_status("test_status_robot")
        assert status.success
        assert status.data["state"] == "idle"

        # Send goal without waiting
        nav_result = navigation_tools.send_nav2_goal(
            robot_name="test_status_robot",
            goal_position=(1.0, 0.0),
            wait_for_result=False
        )
        assert nav_result.success

        # Check status while navigating
        status = navigation_tools.get_navigation_status("test_status_robot")
        assert status.success
        # State should be navigating or completed

    def test_cancel_navigation(self):
        """Test canceling navigation."""
        # Spawn robot
        spawn_result = navigation_tools.spawn_turtlebot3(
            name="test_cancel_robot",
            variant="burger"
        )
        assert spawn_result.success

        # Set initial pose
        navigation_tools.set_initial_pose(
            robot_name="test_cancel_robot",
            position=(0.0, 0.0)
        )

        # Send long navigation goal without waiting
        navigation_tools.send_nav2_goal(
            robot_name="test_cancel_robot",
            goal_position=(10.0, 10.0),
            wait_for_result=False
        )

        # Cancel it
        result = navigation_tools.cancel_navigation("test_cancel_robot")
        assert result.success

    def test_multiple_waypoints(self):
        """Test navigating through multiple waypoints."""
        robot_name = "test_multi_robot"

        # Spawn
        spawn_result = navigation_tools.spawn_turtlebot3(
            name=robot_name,
            variant="burger"
        )
        assert spawn_result.success

        # Set initial pose
        navigation_tools.set_initial_pose(
            robot_name=robot_name,
            position=(0.0, 0.0)
        )

        # Navigate through waypoints
        waypoints = [
            (2.0, 0.0),
            (4.0, 0.0),
            (4.0, 2.0),
        ]

        for i, (x, y) in enumerate(waypoints, 1):
            result = navigation_tools.send_nav2_goal(
                robot_name=robot_name,
                goal_position=(x, y),
                timeout=120.0,
                wait_for_result=True
            )
            assert result.success, f"Failed at waypoint {i}: {result.message}"

        # Verify final status
        status = navigation_tools.get_navigation_status(robot_name)
        assert status.success
        assert status.data["state"] in ["succeeded", "idle"]


@pytest.mark.integration
class TestMCPNavigationAdapter:
    """Test MCP adapter for navigation tools."""

    def test_navigation_adapter_import(self):
        """Test that navigation adapter can be imported."""
        from mcp.server.adapters import navigation_tools_adapter

        assert hasattr(navigation_tools_adapter, 'get_tools')
        assert hasattr(navigation_tools_adapter, 'get_tool_names')

    def test_navigation_adapter_tools(self):
        """Test navigation adapter returns correct tools."""
        from mcp.server.adapters import navigation_tools_adapter

        tools = navigation_tools_adapter.get_tools()
        tool_names = [tool.name for tool in tools]

        assert "spawn_turtlebot3" in tool_names
        assert "send_nav2_goal" in tool_names
        assert "get_navigation_status" in tool_names
        assert "cancel_navigation" in tool_names
        assert "set_initial_pose" in tool_names

        # Verify count
        assert len(tools) == 5

    def test_navigation_tool_schemas(self):
        """Test that tool schemas are properly formed."""
        from mcp.server.adapters import navigation_tools_adapter

        tools = navigation_tools_adapter.get_tools()

        for tool in tools:
            # Check required fields
            assert tool.name
            assert tool.description
            assert tool.parameters
            assert tool.handler

            # Check parameters structure
            assert "properties" in tool.parameters
            assert "required" in tool.parameters

    def test_spawn_turtlebot3_schema(self):
        """Test spawn_turtlebot3 tool schema."""
        from mcp.server.adapters import navigation_tools_adapter

        tools = navigation_tools_adapter.get_tools()
        spawn_tool = next(t for t in tools if t.name == "spawn_turtlebot3")

        props = spawn_tool.parameters["properties"]

        # Check required parameters
        assert "name" in props
        assert "variant" in props
        assert "position" in props

        # Check variant enum
        assert "enum" in props["variant"]
        assert "burger" in props["variant"]["enum"]
        assert "waffle" in props["variant"]["enum"]


@pytest.mark.integration
class TestMCPServerRegistration:
    """Test that navigation tools are registered in MCP server."""

    def test_navigation_tools_registered(self):
        """Test navigation tools are registered in MCP server."""
        from mcp.server.server import GazeboMCPServer

        server = GazeboMCPServer()
        tool_names = list(server.tools.keys())

        # Check navigation tools are present
        assert "spawn_turtlebot3" in tool_names
        assert "send_nav2_goal" in tool_names
        assert "get_navigation_status" in tool_names
        assert "cancel_navigation" in tool_names
        assert "set_initial_pose" in tool_names

        # Verify they're callable
        for tool_name in ["spawn_turtlebot3", "send_nav2_goal"]:
            tool = server.tools[tool_name]
            assert callable(tool.handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
