"""
Basic unit tests for navigation tools (no ROS2/Nav2 required).

Tests code structure, schemas, and MCP integration without
requiring full Nav2 stack or Gazebo.
"""

import pytest
import sys
from pathlib import Path


class TestNavigationToolsStructure:
    """Test navigation tools module structure."""

    def test_navigation_tools_file_exists(self):
        """Test navigation_tools.py file exists."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        assert tools_path.exists(), "navigation_tools.py should exist"

    def test_navigation_tools_has_expected_functions(self):
        """Test navigation_tools.py contains expected function definitions."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        # Check function definitions exist
        assert "def spawn_turtlebot3(" in content
        assert "def send_nav2_goal(" in content
        assert "def get_navigation_status(" in content
        assert "def cancel_navigation(" in content
        assert "def set_initial_pose(" in content

    def test_navigation_tools_has_docstrings(self):
        """Test functions have docstrings."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        # Check docstrings exist
        assert '"""' in content or "'''" in content
        assert "Spawn TurtleBot3" in content
        assert "Send navigation goal" in content or "autonomous navigation" in content

    def test_navigation_tools_uses_operation_result(self):
        """Test functions return OperationResult."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        assert "OperationResult" in content
        assert "success_result" in content
        assert "error_result" in content


class TestMCPAdapterStructure:
    """Test MCP adapter structure."""

    def test_adapter_file_exists(self):
        """Test navigation_tools_adapter.py exists."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        assert adapter_path.exists(), "navigation_tools_adapter.py should exist"

    def test_adapter_has_get_tools(self):
        """Test adapter has get_tools function."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        assert "def get_tools()" in content
        assert "MCPTool" in content

    def test_adapter_defines_5_tools(self):
        """Test adapter defines 5 navigation tools."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        # Count tool definitions
        assert content.count("MCPTool(") >= 5

    def test_adapter_has_tool_names(self):
        """Test adapter defines all expected tool names."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        expected_tools = [
            "spawn_turtlebot3",
            "send_nav2_goal",
            "get_navigation_status",
            "cancel_navigation",
            "set_initial_pose"
        ]

        for tool in expected_tools:
            assert tool in content, f"Tool {tool} should be defined in adapter"

    def test_adapter_has_descriptions(self):
        """Test tools have descriptions for Claude."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        # Check for detailed descriptions
        assert "description=" in content
        assert "TurtleBot3" in content
        assert "Nav2" in content or "navigation" in content

    def test_adapter_has_parameter_schemas(self):
        """Test tools have parameter schemas."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        assert "parameters={" in content
        assert '"properties"' in content
        assert '"required"' in content


class TestMCPServerIntegration:
    """Test MCP server integration."""

    def test_adapter_imported_in_init(self):
        """Test navigation_tools_adapter imported in adapters/__init__.py."""
        init_path = Path("mcp/server/adapters/__init__.py")
        content = init_path.read_text()

        assert "navigation_tools_adapter" in content

    def test_adapter_in_all_exports(self):
        """Test navigation_tools_adapter in __all__."""
        init_path = Path("mcp/server/adapters/__init__.py")
        content = init_path.read_text()

        assert '"navigation_tools_adapter"' in content or "'navigation_tools_adapter'" in content

    def test_server_imports_adapter(self):
        """Test server.py imports navigation_tools_adapter."""
        server_path = Path("mcp/server/server.py")
        content = server_path.read_text()

        assert "navigation_tools_adapter" in content

    def test_server_registers_adapter(self):
        """Test server registers navigation_tools_adapter."""
        server_path = Path("mcp/server/server.py")
        content = server_path.read_text()

        # Should be in adapters list
        assert "navigation_tools_adapter" in content


class TestSetupScripts:
    """Test setup scripts exist and are executable."""

    def test_install_script_exists(self):
        """Test install_turtlebot3.sh exists."""
        script_path = Path("demos/02_obstacle_course/install_turtlebot3.sh")
        assert script_path.exists()

    def test_install_script_executable(self):
        """Test install_turtlebot3.sh is executable."""
        script_path = Path("demos/02_obstacle_course/install_turtlebot3.sh")
        import os
        assert os.access(script_path, os.X_OK), "Script should be executable"

    def test_install_script_content(self):
        """Test install script has expected content."""
        script_path = Path("demos/02_obstacle_course/install_turtlebot3.sh")
        content = script_path.read_text()

        assert "turtlebot3" in content.lower()
        assert "nav2" in content.lower()
        assert "apt install" in content

    def test_launch_nav2_script_exists(self):
        """Test launch_nav2.sh exists."""
        script_path = Path("demos/02_obstacle_course/launch_nav2.sh")
        assert script_path.exists()

    def test_launch_nav2_script_executable(self):
        """Test launch_nav2.sh is executable."""
        script_path = Path("demos/02_obstacle_course/launch_nav2.sh")
        import os
        assert os.access(script_path, os.X_OK), "Script should be executable"


class TestConfiguration:
    """Test configuration files."""

    def test_nav2_params_exists(self):
        """Test nav2_params.yaml exists."""
        config_path = Path("demos/02_obstacle_course/nav2_params.yaml")
        assert config_path.exists()

    def test_nav2_params_content(self):
        """Test nav2_params.yaml has expected content."""
        config_path = Path("demos/02_obstacle_course/nav2_params.yaml")
        content = config_path.read_text()

        # Check key Nav2 components
        assert "controller_server" in content
        assert "planner_server" in content
        assert "bt_navigator" in content or "behavior_server" in content

    def test_demo_config_updated(self):
        """Test demo config.yaml updated for Nav2."""
        config_path = Path("demos/02_obstacle_course/config.yaml")
        content = config_path.read_text()

        assert "turtlebot3" in content.lower()
        assert "nav2" in content.lower() or "navigation" in content.lower()

    def test_demo_config_has_waypoints(self):
        """Test demo config has waypoint definitions."""
        config_path = Path("demos/02_obstacle_course/config.yaml")
        content = config_path.read_text()

        assert "waypoint" in content.lower()
        # Should have multiple waypoints
        assert content.lower().count("waypoint") >= 3


class TestDocumentation:
    """Test documentation files."""

    def test_conversational_demo_exists(self):
        """Test CONVERSATIONAL_DEMO.md exists."""
        doc_path = Path("demos/02_obstacle_course/CONVERSATIONAL_DEMO.md")
        assert doc_path.exists()

    def test_conversational_demo_content(self):
        """Test CONVERSATIONAL_DEMO.md has expected content."""
        doc_path = Path("demos/02_obstacle_course/CONVERSATIONAL_DEMO.md")
        content = doc_path.read_text()

        # Should explain natural language usage
        assert "natural language" in content.lower() or "conversational" in content.lower()
        assert "claude" in content.lower()
        assert "spawn" in content.lower()
        assert "navigate" in content.lower()

    def test_conversational_demo_has_examples(self):
        """Test CONVERSATIONAL_DEMO.md has usage examples."""
        doc_path = Path("demos/02_obstacle_course/CONVERSATIONAL_DEMO.md")
        content = doc_path.read_text()

        # Should have example conversations
        assert "you say" in content.lower() or "you:" in content.lower()
        assert "example" in content.lower()

    def test_readme_updated(self):
        """Test README.md updated with v2.0 info."""
        readme_path = Path("demos/02_obstacle_course/README.md")
        content = readme_path.read_text()

        assert "v2" in content.lower() or "version 2" in content.lower()
        assert "nav2" in content.lower() or "autonomous" in content.lower()

    def test_implementation_complete_exists(self):
        """Test IMPLEMENTATION_COMPLETE.md exists."""
        doc_path = Path("demos/02_obstacle_course/IMPLEMENTATION_COMPLETE.md")
        assert doc_path.exists()


class TestCodeQuality:
    """Test code quality and patterns."""

    def test_navigation_tools_imports(self):
        """Test navigation_tools.py has proper imports."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        # Should import utilities
        assert "from gazebo_mcp.utils import" in content
        assert "OperationResult" in content

        # Should have type hints
        assert "from typing import" in content or "Tuple" in content or "Dict" in content

    def test_navigation_tools_error_handling(self):
        """Test navigation_tools.py has error handling."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        # Should have try/except blocks
        assert "try:" in content
        assert "except" in content

        # Should use error_result
        assert "error_result" in content

    def test_navigation_tools_logging(self):
        """Test navigation_tools.py has logging."""
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        content = tools_path.read_text()

        # Should use logger
        assert "logger" in content.lower() or "_logger" in content

    def test_adapter_follows_pattern(self):
        """Test adapter follows existing MCP adapter pattern."""
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")
        content = adapter_path.read_text()

        # Should follow dataclass pattern
        assert "@dataclass" in content or "class MCPTool" in content

        # Should have get_tools function
        assert "def get_tools()" in content
        assert "-> List[MCPTool]" in content or "List[MCPTool]" in content


class TestIntegrationReadiness:
    """Test implementation is ready for integration."""

    def test_all_files_created(self):
        """Test all expected files were created."""
        expected_files = [
            "src/gazebo_mcp/tools/navigation_tools.py",
            "mcp/server/adapters/navigation_tools_adapter.py",
            "demos/02_obstacle_course/install_turtlebot3.sh",
            "demos/02_obstacle_course/nav2_params.yaml",
            "demos/02_obstacle_course/launch_nav2.sh",
            "demos/02_obstacle_course/CONVERSATIONAL_DEMO.md",
            "demos/02_obstacle_course/IMPLEMENTATION_COMPLETE.md",
            "tests/integration/test_navigation_tools.py",
        ]

        for file_path in expected_files:
            assert Path(file_path).exists(), f"Expected file {file_path} should exist"

    def test_no_syntax_errors(self):
        """Test Python files have no syntax errors."""
        python_files = [
            "src/gazebo_mcp/tools/navigation_tools.py",
            "mcp/server/adapters/navigation_tools_adapter.py",
            "tests/integration/test_navigation_tools.py",
        ]

        import ast

        for file_path in python_files:
            content = Path(file_path).read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")

    def test_consistent_naming(self):
        """Test consistent naming across files."""
        # Tool names should be consistent
        tools_path = Path("src/gazebo_mcp/tools/navigation_tools.py")
        adapter_path = Path("mcp/server/adapters/navigation_tools_adapter.py")

        tools_content = tools_path.read_text()
        adapter_content = adapter_path.read_text()

        tool_names = [
            "spawn_turtlebot3",
            "send_nav2_goal",
            "get_navigation_status",
            "cancel_navigation",
            "set_initial_pose"
        ]

        for tool_name in tool_names:
            assert f"def {tool_name}(" in tools_content, f"Function {tool_name} should be defined"
            assert f'"{tool_name}"' in adapter_content or f"'{tool_name}'" in adapter_content, \
                f"Tool name {tool_name} should be in adapter"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
