"""
Simulation Tools MCP Adapter.

Exposes Gazebo simulation control tools as MCP tools:
- pause_simulation: Pause physics simulation
- unpause_simulation: Resume physics simulation
- reset_simulation: Reset to initial state
- set_simulation_speed: Control simulation speed
- get_simulation_time: Query simulation time
- get_simulation_status: Get overall simulation status
- list_worlds: List all active Gazebo worlds
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import simulation_tools
from gazebo_mcp.utils import OperationResult
from gazebo_mcp.mcp_protocol.server.mcp_tool import MCPTool


def pause_simulation_wrapper(timeout: float = 5.0) -> OperationResult:
    """Wrapper for pause_simulation."""
    return simulation_tools.pause_simulation(timeout=timeout, world=None)


def unpause_simulation_wrapper(timeout: float = 5.0) -> OperationResult:
    """Wrapper for unpause_simulation."""
    return simulation_tools.unpause_simulation(timeout=timeout, world=None)


def reset_simulation_wrapper(timeout: float = 10.0) -> OperationResult:
    """Wrapper for reset_simulation."""
    return simulation_tools.reset_simulation(timeout=timeout, world=None)


def get_tools() -> List[MCPTool]:
    """Get MCP tools for simulation control."""
    return [
        MCPTool(
            name="gazebo_pause_simulation",
            description=(
                "Pause Gazebo physics simulation.\n\n"
                "Stops physics updates while keeping visualization running.\n\n"
                "Args:\n"
                "  timeout: Service call timeout in seconds (default: 5.0)\n\n"
                "Example: gazebo_pause_simulation()"
            ),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 5.0)",
                        "default": 5.0,
                    }
                },
                "required": [],
            },
            handler=pause_simulation_wrapper,
        ),
        MCPTool(
            name="gazebo_unpause_simulation",
            description=(
                "Resume Gazebo physics simulation.\n\n"
                "Resumes physics updates after pause.\n\n"
                "Args:\n"
                "  timeout: Service call timeout in seconds (default: 5.0)\n\n"
                "Example: gazebo_unpause_simulation()"
            ),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 5.0)",
                        "default": 5.0,
                    }
                },
                "required": [],
            },
            handler=unpause_simulation_wrapper,
        ),
        MCPTool(
            name="gazebo_reset_simulation",
            description=(
                "Reset Gazebo simulation to initial state.\n\n"
                "Resets all model poses, simulation time, and physics state.\n\n"
                "Args:\n"
                "  timeout: Service call timeout in seconds (default: 10.0)\n\n"
                "Example: gazebo_reset_simulation()"
            ),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 10.0)",
                        "default": 10.0,
                    }
                },
                "required": [],
            },
            handler=reset_simulation_wrapper,
        ),
        MCPTool(
            name="gazebo_set_simulation_speed",
            description=(
                "Set simulation speed multiplier.\n\n"
                "1.0 = real-time, < 1.0 = slower, > 1.0 = faster.\n"
                "Provides instructions for manual setting.\n\n"
                "Args:\n"
                "  speed_factor: Speed multiplier (required)\n\n"
                "Examples:\n"
                "- Half speed: gazebo_set_simulation_speed(0.5)\n"
                "- Double speed: gazebo_set_simulation_speed(2.0)"
            ),
            parameters={
                "properties": {
                    "speed_factor": {
                        "type": "number",
                        "description": "Speed multiplier (> 0)",
                        "minimum": 0.001,
                        "maximum": 100.0,
                    }
                },
                "required": ["speed_factor"],
            },
            handler=simulation_tools.set_simulation_speed,
        ),
        MCPTool(
            name="gazebo_get_simulation_time",
            description=(
                "Get current simulation time and metrics.\n\n"
                "Returns simulation_time, real_time, paused status, and iterations.\n\n"
                "Example: gazebo_get_simulation_time()"
            ),
            parameters={
                "properties": {},
                "required": [],
            },
            handler=simulation_tools.get_simulation_time,
        ),
        MCPTool(
            name="gazebo_get_simulation_status",
            description=(
                "Get overall simulation status.\n\n"
                "Returns running state, paused status, simulation time, "
                "and Gazebo connection status.\n\n"
                "Example: gazebo_get_simulation_status()"
            ),
            parameters={
                "properties": {},
                "required": [],
            },
            handler=simulation_tools.get_simulation_status,
        ),
        MCPTool(
            name="gazebo_list_worlds",
            description=(
                "List all active Gazebo worlds.\n\n"
                "Discovers running worlds by inspecting the gz/ign service graph.\n"
                "Returns ['default'] when Gazebo is not running.\n\n"
                "Example: gazebo_list_worlds()"
            ),
            parameters={
                "properties": {},
                "required": [],
            },
            handler=simulation_tools.list_worlds,
        ),
    ]
