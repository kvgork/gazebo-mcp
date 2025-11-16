"""
MCP Tool Adapters.

Adapters convert Gazebo tool functions to MCP tool definitions.
Each adapter module provides tools for a specific domain:

- model_management_adapter: Model spawn, delete, list, state
- sensor_tools_adapter: Sensor data queries and streaming
- world_tools_adapter: World loading, saving, properties
- simulation_tools_adapter: Physics control, pause, reset
"""

from . import model_management_adapter
from . import sensor_tools_adapter
from . import world_tools_adapter
from . import simulation_tools_adapter

__all__ = [
    "model_management_adapter",
    "sensor_tools_adapter",
    "world_tools_adapter",
    "simulation_tools_adapter",
]
