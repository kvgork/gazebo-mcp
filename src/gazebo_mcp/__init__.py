"""
Gazebo MCP Server - ROS2 Model Context Protocol Server for Gazebo Simulation

This package provides an MCP server that enables AI assistants to control
and manipulate Gazebo simulations through ROS2 interfaces.

Features:
- Simulation control (start, stop, pause, reset)
- Model management (spawn, delete, control TurtleBot3)
- Sensor data access (camera, lidar, IMU, GPS)
- World generation and manipulation
- Dynamic lighting and terrain control
- Real-time world updates
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("gazebo-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__license__ = "MIT"
