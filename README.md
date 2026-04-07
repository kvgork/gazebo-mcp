---
title: Gazebo MCP
emoji: 🐨
colorFrom: yellow
colorTo: purple
sdk: static
pinned: false
license: mit
short_description: A mcp server for Gazebo simulations
tags:
  - building-mcp-track-enterprise
  - building-mcp-track-customer
  - building-mcp-track-creative
  # - mcp-in-action-track-enterprise
  # - mcp-in-action-track-customer
---

# Gazebo MCP Server

Welcome to my submission for the hackathon!

I am always looking for new ways to work with robotics.

This led me to start experimenting with Claude Code where I have been creating agents and skills that help me move faster and learn new concepts.
With my own robotics project I am reaching a point where I want to try ideas in simulation and see how they behave before turning the robot on.

That is why I joined the MCP first birthday event on Hugging Face. My focus there is a ROS 2 Ignition Gazebo MCP server that can create simulation environments when needed. Once that is running well I plan to work toward an automation agent that uses the server to manage a full testing cycle.

Here are the goals guiding the project

- Learn Gazebo through real use
- Understand Claude code at a deeper level and see how it supports and works with agents, skills and mcp.
- Explore the limits and possibilities of agents, skills, and MCP servers(Most of the code is made using Claude)
- Study how AI can support automated testing inside simulation work

If you work with simulation or agent systems in robtoics I would love to hear what you learned along the way.

Current status: Spawning of objecets is done, now working on getting the turtlebot3 implementation in! Hopefully get that in before the deadline...

Main development has been done in a github repo, as I had some Claude Code Web token left!
(messy) Github repo: https://github.com/kvgork/gazebo-mcp

Demo: https://youtu.be/EheuCn7wfEM
Linkedin post: https://www.linkedin.com/posts/koen-van-gorkom_ros-gazebo-claude-activity-7399850098895101952-dTVb?utm_source=share&utm_medium=member_desktop&rcm=ACoAACTbTigBb1Kzy16TjXiTkuP13M5vyZVAQPc

> **ROS2 Model Context Protocol Server for Gazebo Simulation**

Enable AI assistants like Claude to control Gazebo simulations, spawn robots (TurtleBot3), manipulate environments, generate test worlds, and gather sensor data through a standardized MCP interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue.svg)](https://docs.ros.org/en/humble/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-orange.svg)](https://gazebosim.org/)

## Features

### Simulation Control
- Start, stop, pause, and reset Gazebo simulations
- Configure physics properties (gravity, timestep, etc.)
- Monitor simulation state

### [WIP] Robot Management (TurtleBot3 Focus)
- Spawn TurtleBot3 variants (Burger, Waffle, Waffle Pi)
- Control robot movement via velocity commands
- Access joint states and control
- Load custom robot models from URDF/SDF

### [WIP] Sensor Integration
- Access camera images (RGB, depth)
- Retrieve LiDAR point clouds
- Read IMU data (acceleration, gyroscope)
- Query GPS positions
- Monitor contact sensors

### Dynamic World Generation
- **Object Placement**: Add static and dynamic objects
  - Primitive shapes (boxes, spheres, cylinders)
  - Custom mesh models
  - Physics properties (mass, friction, collision)
- **[WIP] Terrain Modification**: Create diverse environments
  - Heightmap-based terrain
  - Surface types (grass, concrete, sand, gravel)
  - Procedural terrain generation
- **[WIP] Lighting Control**: Customize scene lighting
  - Ambient, directional, point, and spot lights
  - Day/night cycle simulation
  - Real-time lighting updates
- **Live World Updates**: Modify running simulations
  - Move objects dynamically
  - Apply forces and torques
  - Change appearances and properties

## Quick Start

### Prerequisites

- **ROS2**: Humble or Jazzy (LTS recommended)
- **Gazebo**: Modern Gazebo (Fortress, Garden, or Harmonic)
- **Python**: 3.10 or higher
- **OS**: Ubuntu 22.04 or 24.04 (recommended)

### Installation

#### 1. Install ROS2 and Gazebo

```bash
# Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop

# Install Modern Gazebo (Recommended)
# For ROS2 Humble - Gazebo Fortress or Garden:
sudo apt install ros-humble-ros-gz

# Or for specific Gazebo version:
sudo apt install gz-harmonic  # Gazebo Harmonic
sudo apt install gz-garden    # Gazebo Garden
sudo apt install gz-fortress  # Gazebo Fortress
```

#### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp/gazebo_mcp_package

# Source ROS2
source /opt/ros/humble/setup.bash

# Install Python dependencies
pip install -r requirements.txt

# Build the package (if using ROS2 workspace)
colcon build
source install/setup.bash
```

#### 3. Run the MCP Server

```bash
# Ensure ROS2 is sourced:
source /opt/ros/humble/setup.bash
source install/setup.bash  # If using colcon build

# Run the MCP server:
python -m gazebo_mcp.server
```

#### 4. Configuration (Optional)

Control Gazebo backend selection via environment variables:

```bash
# Use Modern Gazebo (Default - Recommended)
export GAZEBO_BACKEND=modern

# Use Classic Gazebo (Deprecated)
export GAZEBO_BACKEND=classic

# Auto-detect based on running services
export GAZEBO_BACKEND=auto

# Set default world name for multi-world support (Modern only)
export GAZEBO_WORLD_NAME=default

# Set service call timeout (seconds)
export GAZEBO_TIMEOUT=5.0

# Set Claude dependency path (if not in default locations)
export CLAUDE_ROOT=/path/to/claude
```

**For Claude Code Integration**, add to your MCP configuration:

```json
{
  "mcpServers": {
    "gazebo": {
      "command": "python",
      "args": ["-m", "gazebo_mcp.server"],
      "cwd": "<path_to_gazebo_mcp_package>",
      "env": {
        "PYTHONPATH": "<path_to_gazebo_mcp_package>/src",
        "ROS_DOMAIN_ID": "0",
        "GAZEBO_BACKEND": "modern",
        "GAZEBO_WORLD_NAME": "default",
        "GAZEBO_TIMEOUT": "5.0",
        "CLAUDE_ROOT": "/path/to/claude"
      }
    }
  }
}
```

See `gazebo_mcp_package/mcp/README.md` for detailed MCP server documentation.

### Usage Example

Once the MCP server is running, AI assistants can use it to control Gazebo:

```python
# Example: Claude controlling Gazebo via MCP

# 1. List all models in simulation
await use_mcp_tool("gazebo_list_models", {
    "response_format": "summary"
})

# 2. Spawn a model from file
await use_mcp_tool("gazebo_spawn_model", {
    "model_name": "my_robot",
    "model_file": "/path/to/robot.urdf",
    "pose": {
        "position": {"x": 0.0, "y": 0.0, "z": 0.5},
        "orientation": {"roll": 0, "pitch": 0, "yaw": 0}
    }
})

# 3. Get model state
state = await use_mcp_tool("gazebo_get_model_state", {
    "model_name": "my_robot"
})

# 4. Control simulation
await use_mcp_tool("gazebo_pause_simulation", {})
await use_mcp_tool("gazebo_unpause_simulation", {})
```

## Available MCP Tools

**Total Tools**: 27 tools across 5 categories

See `gazebo_mcp_package/mcp/README.md` for detailed tool documentation and examples.

### Model Management (6 tools)

| Tool | Description |
|------|-------------|
| `gazebo_list_models` | List all models in simulation with ResultFilter support |
| `gazebo_spawn_model` | Spawn model from URDF/SDF file or XML string |
| `gazebo_delete_model` | Remove model from simulation |
| `gazebo_get_model_state` | Query model pose and velocity |
| `gazebo_set_model_state` | Set model pose and/or velocity (teleport or set velocity) |
| `gazebo_apply_force` | Apply force/torque to a model for physics testing |

### Sensor Tools (3 tools)

| Tool | Description |
|------|-------------|
| `gazebo_list_sensors` | List all sensors with optional filtering by model/type |
| `gazebo_get_sensor_data` | Get latest sensor data (camera, lidar, IMU, GPS, etc.) |
| `gazebo_subscribe_sensor_stream` | Subscribe to sensor topic and cache data |

**Supported sensor types**: camera, depth_camera, rgbd_camera, imu, lidar, ray, gps, contact, force_torque, magnetometer, altimeter, sonar

### World Tools (5 tools)

| Tool | Description |
|------|-------------|
| `gazebo_load_world` | Validate world file and provide loading instructions |
| `gazebo_save_world` | Provide instructions for saving current world |
| `gazebo_get_world_properties` | Query physics settings, gravity, scene properties |
| `gazebo_set_world_property` | Provide instructions for updating world properties |
| `gazebo_set_gravity` | Set simulation gravity vector (Earth, Moon, zero-g, custom) |

### Simulation Control (7 tools)

| Tool | Description |
|------|-------------|
| `gazebo_pause_simulation` | Pause physics simulation |
| `gazebo_unpause_simulation` | Resume physics simulation |
| `gazebo_reset_simulation` | Reset simulation to initial state |
| `gazebo_set_simulation_speed` | Provide instructions for setting simulation speed |
| `gazebo_get_simulation_time` | Query simulation time and performance metrics |
| `gazebo_get_simulation_status` | Get comprehensive simulation status |
| `gazebo_list_worlds` | List all active Gazebo worlds |

### ROS2 Tools (6 tools)

| Tool | Description |
|------|-------------|
| `gazebo_list_topics` | List all active ROS2 topics with message types |
| `gazebo_get_topic_info` | Get detailed info about a specific ROS2 topic |
| `gazebo_publish_twist` | Publish velocity commands to drive a robot |
| `gazebo_get_transform` | Look up TF transform between two coordinate frames |
| `gazebo_spawn_sdf` | Spawn a model from complete SDF/URDF XML string |
| `gazebo_get_joint_states` | Read current joint positions and velocities from a robot |

## Key Features & Architecture

### Token Efficiency (95-99% Savings!)

This implementation uses the **ResultFilter pattern** for massive token savings:

```python
# ❌ Traditional approach - sends all 1000 models through model:
result = gazebo_list_models()  # 50,000+ tokens

# ✅ Our approach - filter locally in MCP server:
result = gazebo_list_models(response_format="summary")  # ~500 tokens (95% savings)

# Or get full data but filter client-side:
from skills.common.filters import ResultFilter
all_models = gazebo_list_models()["data"]["models"]
robots = ResultFilter.search(all_models, "robot", ["name"])
top_5 = ResultFilter.top_n_by_field(robots, "position.z", 5)
# Only 5 models sent to Claude instead of 1000! (95%+ savings)
```

### Graceful Fallback

Tools automatically fall back to mock data when Gazebo is not available:
- ✅ Development/testing without Gazebo running
- ✅ Clear indication in responses (`"note": "Mock mode - Gazebo not available"`)
- ✅ Same response format for consistent agent behavior

### Comprehensive Testing

- **80+ tests** covering all components
- **60+ unit tests** for validators, converters, geometry
- **20+ integration tests** for ROS2 and Gazebo integration
- **95%+ code coverage** for core utilities
- See `gazebo_mcp_package/tests/README.md` for running tests

## Documentation

All documentation is in the `gazebo_mcp_package/` directory:

- **[Main README](gazebo_mcp_package/README.md)** - Complete package documentation
- **[Installation Guide](gazebo_mcp_package/INSTALL_MCP.md)** - Detailed installation instructions
- **[Quick Install](gazebo_mcp_package/QUICK_INSTALL.md)** - Fast installation guide
- **[MCP Setup Guide](gazebo_mcp_package/MCP_SETUP_GUIDE.md)** - Claude Code integration
- **[MCP Server Guide](gazebo_mcp_package/mcp/README.md)** - Complete MCP server documentation
- **[Demo Guide](gazebo_mcp_package/demos/CONVERSATIONAL_DEMO_GUIDE.md)** - Interactive demos
- **[Manual Setup](gazebo_mcp_package/demos/MANUAL_SETUP_GUIDE.md)** - Step-by-step setup
- **[Troubleshooting](gazebo_mcp_package/demos/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Test Documentation](gazebo_mcp_package/tests/README.md)** - Test suite documentation

## Project Structure

```
gazebo-mcp/
├── gazebo_mcp_package/          # Main package directory
│   ├── src/gazebo_mcp/          # Source code
│   │   ├── bridge/              # ROS2 connection management
│   │   ├── tools/               # MCP tool implementations
│   │   └── utils/               # Utilities (validators, converters, etc.)
│   ├── mcp/                     # MCP server
│   │   └── server/              # Server implementation and adapters
│   ├── tests/                   # Test suite (80+ tests)
│   ├── demos/                   # Demo scripts and guides
│   ├── docs/                    # Documentation
│   ├── scripts/                 # Utility scripts
│   └── README.md                # Package documentation
└── README.md                    # This file
```

## Troubleshooting

### ROS2 Connection Issues

```bash
# Check ROS2 environment
echo $ROS_DISTRO  # Should show "humble" or "jazzy"

# Verify Gazebo installation
gz sim --version

# Check ROS2 topics
ros2 topic list
```

### MCP Server Not Starting

```bash
# Check Python version
python --version  # Should be 3.10+

# Verify dependencies
pip install -r requirements.txt

# Check ROS2 is sourced
source /opt/ros/humble/setup.bash

# Run server with logging
python -m gazebo_mcp.server 2>&1 | tee server.log
```

### "No module named rclpy" Error

```bash
# Source ROS2 before running MCP server:
source /opt/ros/humble/setup.bash

# Verify rclpy is available:
python -c "import rclpy; print('rclpy OK')"
```

### Gazebo Not Available

**This is expected!** The server gracefully falls back to mock data when Gazebo is not running. You'll see `"note": "Mock mode - Gazebo not available"` in responses.

To connect to real Gazebo:
```bash
# Terminal 1 - Start Gazebo:
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf

# Terminal 2 - Start bridge:
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"

# Terminal 3 - Run MCP server:
python -m gazebo_mcp.server
```

### 🔵 Future Enhancements
- Real-time sensor streaming improvements
- Advanced world generation tools
- Multi-robot coordination helpers
- Additional sensor types (thermal, radar)

## Development

### Running Tests

```bash
# Unit tests (no ROS2 required):
cd gazebo_mcp_package
pytest tests/test_utils.py -v

# Integration tests (ROS2 required):
source /opt/ros/humble/setup.bash
pytest tests/test_integration.py -v --with-ros2

# Run all tests:
pytest tests/ -v
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://github.com/anthropics/mcp) by Anthropic
- [ROS2](https://docs.ros.org/en/humble/) by Open Robotics
- [Gazebo](https://gazebosim.org/) by Open Robotics
- [TurtleBot3](https://emanual.robotis.com/docs/en/platform/turtlebot3/) by ROBOTIS

## Support

- **Issues**: [GitHub Issues](https://github.com/kvgork/gazebo-mcp/issues)
- **Documentation**: See `gazebo_mcp_package/README.md` for complete documentation

## Citation

If you use this project in your research, please cite:

```bibtex
@software{gazebo_mcp,
  title = {Gazebo MCP Server: ROS2 Model Context Protocol for Gazebo},
  author = {Gazebo MCP Team},
  year = {2024},
  url = {https://github.com/kvgork/gazebo-mcp}
}
```

---

**Built for the robotics and AI community**
