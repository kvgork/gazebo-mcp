"""
Simulation Tools MCP Adapter.

Exposes Gazebo simulation control tools as MCP tools:
- pause_simulation: Pause physics simulation
- unpause_simulation: Resume physics simulation
- reset_simulation: Reset to initial state
- set_simulation_speed: Control simulation speed
- get_simulation_time: Query simulation time
- get_simulation_status: Get overall simulation status

Useful for controlling simulation flow, debugging, and testing.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import simulation_tools
from gazebo_mcp.utils import OperationResult


# Wrapper functions to use "empty" world
def pause_simulation_wrapper(timeout: float = 5.0) -> OperationResult:
    """Wrapper for pause_simulation that uses the empty world."""
    return simulation_tools.pause_simulation(timeout=timeout, world="empty")


def unpause_simulation_wrapper(timeout: float = 5.0) -> OperationResult:
    """Wrapper for unpause_simulation that uses the empty world."""
    return simulation_tools.unpause_simulation(timeout=timeout, world="empty")


def reset_simulation_wrapper(timeout: float = 10.0) -> OperationResult:
    """Wrapper for reset_simulation that uses the empty world."""
    return simulation_tools.reset_simulation(timeout=timeout, world="empty")


class MCPTool:
    """MCP tool definition (imported from server.py context)."""

    def __init__(self, name, description, parameters, handler):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", [])
            }
        }


def get_tools() -> List[MCPTool]:
    """
    Get MCP tools for simulation control.

    Returns:
        List of MCPTool instances
    """
    return [
        # Pause simulation tool:
        MCPTool(
            name="gazebo_pause_simulation",
            description="""
Pause Gazebo physics simulation.

Stops physics updates while keeping visualization running.
Useful for inspecting state, debugging, or preparing next step.

Args:
    timeout: Service call timeout in seconds (default: 5.0, optional)

Returns pause status with timestamp.

Examples:
- gazebo_pause_simulation()
- gazebo_pause_simulation(timeout=10.0)
            """.strip(),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 5.0)",
                        "default": 5.0,
                        "minimum": 0.1,
                        "maximum": 60.0
                    }
                },
                "required": []
            },
            handler=pause_simulation_wrapper
        ),

        # Unpause simulation tool:
        MCPTool(
            name="gazebo_unpause_simulation",
            description="""
Unpause (resume) Gazebo physics simulation.

Resumes physics updates after pause.

Args:
    timeout: Service call timeout in seconds (default: 5.0, optional)

Returns unpause status with timestamp.

Examples:
- gazebo_unpause_simulation()
- gazebo_unpause_simulation(timeout=10.0)
            """.strip(),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 5.0)",
                        "default": 5.0,
                        "minimum": 0.1,
                        "maximum": 60.0
                    }
                },
                "required": []
            },
            handler=unpause_simulation_wrapper
        ),

        # Reset simulation tool:
        MCPTool(
            name="gazebo_reset_simulation",
            description="""
Reset Gazebo simulation to initial state.

Resets:
- All model poses to initial positions
- Simulation time to 0
- Physics state (velocities, forces, etc.)

Args:
    timeout: Service call timeout in seconds (default: 10.0, optional)

Returns reset status with new simulation time (should be 0.0).

Examples:
- gazebo_reset_simulation()
- gazebo_reset_simulation(timeout=15.0)
            """.strip(),
            parameters={
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Service call timeout in seconds (default: 10.0)",
                        "default": 10.0,
                        "minimum": 0.1,
                        "maximum": 60.0
                    }
                },
                "required": []
            },
            handler=reset_simulation_wrapper
        ),

        # Set simulation speed tool:
        MCPTool(
            name="gazebo_set_simulation_speed",
            description="""
Set simulation speed multiplier.

Speed factor controls how fast simulation runs relative to real-time:
- 1.0 = real-time (default)
- < 1.0 = slower than real-time (e.g., 0.5 = half speed)
- > 1.0 = faster than real-time (e.g., 2.0 = double speed)

Note: Actual speed may be limited by system performance.
Speed setting via MCP will be implemented in a future update.
Currently provides instructions for manual setting.

Args:
    speed_factor: Speed multiplier (required)

Returns speed setting status and instructions.

Examples:
- gazebo_set_simulation_speed(0.5)   # Half speed
- gazebo_set_simulation_speed(1.0)   # Real-time
- gazebo_set_simulation_speed(2.0)   # Double speed
            """.strip(),
            parameters={
                "properties": {
                    "speed_factor": {
                        "type": "number",
                        "description": "Speed multiplier (> 0)",
                        "minimum": 0.001,
                        "maximum": 100.0
                    }
                },
                "required": ["speed_factor"]
            },
            handler=simulation_tools.set_simulation_speed
        ),

        # Get simulation time tool:
        MCPTool(
            name="gazebo_get_simulation_time",
            description="""
Get current simulation time and related metrics.

Returns:
- simulation_time: Simulated time elapsed (seconds)
- real_time: Real wall-clock time elapsed (seconds)
- paused: Whether simulation is paused
- iterations: Number of physics iterations
- real_time_factor: Actual speed (sim_time / real_time)

Useful for monitoring simulation progress and performance.

Example:
- gazebo_get_simulation_time()
            """.strip(),
            parameters={
                "properties": {},
                "required": []
            },
            handler=simulation_tools.get_simulation_time
        ),

        # Get simulation status tool:
        MCPTool(
            name="gazebo_get_simulation_status",
            description="""
Get overall simulation status.

Returns comprehensive status including:
- running: Whether Gazebo is running
- paused: Whether physics is paused
- simulation_time: Simulated time elapsed
- real_time: Real time elapsed
- iterations: Physics iterations
- gazebo_connected: Whether ROS2 connection is active

Useful for health checks and monitoring.

Example:
- gazebo_get_simulation_status()
            """.strip(),
            parameters={
                "properties": {},
                "required": []
            },
            handler=simulation_tools.get_simulation_status
        ),
    ]
