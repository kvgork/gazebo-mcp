ROS2 Gazebo MCP Server - API Documentation
===========================================

Welcome to the ROS2 Gazebo MCP Server API documentation. This server provides a Model Context Protocol (MCP) interface for controlling Gazebo simulations and robots.

Overview
--------

The ROS2 Gazebo MCP Server enables:

* **World Generation**: Create custom simulation worlds with obstacles, terrain, and environmental effects
* **Model Management**: Spawn, control, and monitor robot models in simulation
* **Sensor Integration**: Read data from cameras, lidars, IMUs, GPS, and other sensors
* **Simulation Control**: Pause, play, reset, and configure simulation parameters
* **ROS2 Bridge**: Seamless integration with ROS2 ecosystem

Quick Start
-----------

.. code-block:: python

   from gazebo_mcp.server import GazeboMCPServer

   # Start the server
   server = GazeboMCPServer()
   await server.start()

For detailed tutorials and examples, see the main project documentation.

API Reference
-------------

.. toctree::
   :maxdepth: 4
   :caption: API Modules:

   modules
   gazebo_mcp

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

