"""
MCP Tool Adapters.

Adapters convert Gazebo tool functions to MCP tool definitions.
Each adapter module provides tools for a specific domain:

- model_management_adapter: Model spawn, delete, list, state
- sensor_tools_adapter: Sensor data queries and streaming
- world_tools_adapter: World loading, saving, properties
- simulation_tools_adapter: Physics control, pause, reset
- ros2_tools_adapter: ROS2 topic discovery, velocity publishing, TF, SDF spawn
- developer_tools_adapter: Debug markers, RViz, recording, snapshots, profiling
- multi_robot_tools_adapter: Fleet spawning, swarm behaviors, coordination
- advanced_sensor_tools_adapter: Sensor fusion, visualization, calibration
- slam_tools_adapter: SLAM mapping, localization, loop closure
- nav2_tools_adapter: Nav2 navigation, path planning, costmaps, waypoints
"""

from . import model_management_adapter
from . import sensor_tools_adapter
from . import world_tools_adapter
from . import simulation_tools_adapter
from . import ros2_tools_adapter
from . import developer_tools_adapter
from . import multi_robot_tools_adapter
from . import advanced_sensor_tools_adapter
from . import slam_tools_adapter
from . import nav2_tools_adapter

__all__ = [
    "model_management_adapter",
    "sensor_tools_adapter",
    "world_tools_adapter",
    "simulation_tools_adapter",
    "ros2_tools_adapter",
    "developer_tools_adapter",
    "multi_robot_tools_adapter",
    "advanced_sensor_tools_adapter",
    "slam_tools_adapter",
    "nav2_tools_adapter",
]
