# Gazebo MCP Server

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

### Robot Management (TurtleBot3 Focus)
- Spawn TurtleBot3 variants (Burger, Waffle, Waffle Pi)
- Control robot movement via velocity commands
- Access joint states and control
- Load custom robot models from URDF/SDF

### Sensor Integration
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
- **Terrain Modification**: Create diverse environments
  - Heightmap-based terrain
  - Surface types (grass, concrete, sand, gravel)
  - Procedural terrain generation
- **Lighting Control**: Customize scene lighting
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
- **Gazebo**: Harmonic or Garden
- **Python**: 3.10 or higher
- **OS**: Ubuntu 22.04 or 24.04 (recommended)

### Installation

#### 1. Install ROS2 and Gazebo

```bash
# Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop

# Install Gazebo Harmonic
sudo apt install gz-harmonic

# Install Gazebo ROS2 packages
sudo apt install ros-humble-gazebo-ros-pkgs

# Install TurtleBot3 packages
sudo apt install ros-humble-turtlebot3-*
```

#### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/gazebo-mcp.git
cd gazebo-mcp

# Source ROS2
source /opt/ros/humble/setup.bash

# Install Python dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

#### 3. Run the MCP Server

```bash
# Start the Gazebo MCP server
gazebo-mcp-server

# Or run directly
python -m gazebo_mcp.server
```

### Usage Example

Once the MCP server is running, AI assistants can use it to control Gazebo:

```python
# Example: Claude controlling Gazebo via MCP

# 1. Start a simulation with empty world
await use_mcp_tool("start_simulation", {
    "world_name": "empty_world"
})

# 2. Spawn a TurtleBot3 Burger
await use_mcp_tool("spawn_model", {
    "model_name": "robot_1",
    "model_type": "turtlebot3_burger",
    "x": 0.0,
    "y": 0.0,
    "z": 0.0
})

# 3. Create an obstacle course
await use_mcp_tool("create_obstacle_course", {
    "num_obstacles": 10,
    "area_size": 20.0,
    "obstacle_types": ["box", "cylinder"]
})

# 4. Set day/night cycle
await use_mcp_tool("set_day_night_cycle", {
    "cycle_duration": 60,  # seconds
    "start_time": "sunrise"
})

# 5. Send velocity command to robot
await use_mcp_tool("send_velocity_command", {
    "model_name": "robot_1",
    "linear_x": 0.2,
    "angular_z": 0.5
})

# 6. Get LiDAR data
sensor_data = await use_mcp_tool("get_sensor_data", {
    "model_name": "robot_1",
    "sensor_type": "lidar"
})
```

## Available MCP Tools

### Simulation Control
| Tool | Description |
|------|-------------|
| `start_simulation` | Launch Gazebo with specified world |
| `stop_simulation` | Shutdown Gazebo gracefully |
| `pause_simulation` | Pause physics simulation |
| `unpause_simulation` | Resume physics simulation |
| `reset_simulation` | Reset world to initial state |
| `set_physics_properties` | Configure gravity, timestep, etc. |

### Model Management
| Tool | Description |
|------|-------------|
| `spawn_model` | Spawn robot/object from URDF/SDF |
| `delete_model` | Remove model from simulation |
| `list_models` | Get all active models |
| `get_model_state` | Query model pose and velocity |
| `set_model_state` | Set model pose and velocity |

### Robot Control
| Tool | Description |
|------|-------------|
| `send_velocity_command` | Send cmd_vel to robot |
| `send_joint_command` | Control individual joints |
| `get_joint_states` | Read joint positions/velocities |

### Sensor Access
| Tool | Description |
|------|-------------|
| `list_sensors` | Query available sensors |
| `get_sensor_data` | Read sensor data (camera, lidar, IMU) |
| `configure_sensor` | Modify sensor parameters |

### World Generation
| Tool | Description |
|------|-------------|
| `create_empty_world` | Generate basic world template |
| `load_world` | Load existing .world file |
| `save_world` | Export current world state |
| `place_static_object` | Add static obstacles |
| `place_dynamic_object` | Add physics objects |
| `create_obstacle_course` | Generate random obstacle layouts |

### Terrain Tools
| Tool | Description |
|------|-------------|
| `set_ground_plane` | Configure ground surface |
| `create_heightmap` | Generate terrain from heightmap |
| `set_surface_type` | Configure terrain materials |

### Lighting Tools
| Tool | Description |
|------|-------------|
| `set_ambient_light` | Configure ambient lighting |
| `add_directional_light` | Add sun/directional light |
| `add_point_light` | Add point light source |
| `add_spot_light` | Add spotlight |
| `set_day_night_cycle` | Animate lighting over time |
| `remove_light` | Delete light source |
| `list_lights` | Get all light sources |

### Live Updates
| Tool | Description |
|------|-------------|
| `modify_model_property` | Update model params on-the-fly |
| `apply_force` | Apply forces to objects |
| `apply_torque` | Apply torques to objects |
| `set_wind` | Configure wind forces |
| `update_light_realtime` | Change lighting dynamically |

## Project Structure

```
gazebo-mcp/
├── src/gazebo_mcp/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── bridge/
│   │   ├── __init__.py
│   │   ├── gazebo_bridge_node.py   # ROS2 bridge
│   │   └── connection_manager.py    # Connection lifecycle
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── simulation_control.py
│   │   ├── model_management.py
│   │   ├── sensor_tools.py
│   │   ├── world_generation.py
│   │   ├── lighting_tools.py
│   │   ├── terrain_tools.py
│   │   └── live_update_tools.py
│   └── utils/
│       ├── __init__.py
│       ├── validators.py
│       ├── converters.py
│       ├── geometry.py
│       ├── sdf_generator.py
│       └── world_template.py
├── config/                    # Configuration files
├── launch/                    # ROS2 launch files
├── worlds/                    # Gazebo world files
├── models/                    # Custom model definitions
├── tests/                     # Test suite
├── examples/                  # Example scripts
├── docs/                      # Documentation
│   └── ARCHITECTURE.md
├── pyproject.toml
├── package.xml
├── requirements.txt
└── README.md
```

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and component details
- [API Reference](docs/API.md) - Complete tool documentation
- [Development Guide](docs/DEVELOPMENT.md) - Contributing and development setup
- [Examples](examples/) - Working code examples

## Example Scenarios

### 1. TurtleBot3 Navigation Test

```python
# Setup environment
await start_simulation("turtlebot3_world")
await spawn_model("robot_1", "turtlebot3_burger", x=0, y=0)

# Create obstacles
await create_obstacle_course(num_obstacles=5, area_size=10)

# Command robot to move
await send_velocity_command("robot_1", linear_x=0.2, angular_z=0.0)

# Monitor sensors
lidar_data = await get_sensor_data("robot_1", "lidar")
camera_image = await get_sensor_data("robot_1", "camera")
```

### 2. Multi-Terrain Testing

```python
# Create world with heightmap terrain
await create_empty_world("terrain_test")
await create_heightmap("terrain.png", scale=1.0, elevation_range=5.0)

# Set different surface types
await set_surface_type(region="north", material="grass")
await set_surface_type(region="south", material="sand")

# Spawn robot and test
await spawn_model("robot_1", "turtlebot3_waffle", x=0, y=0, z=1.0)
```

### 3. Day/Night Sensor Testing

```python
# Setup
await start_simulation("empty_world")
await spawn_model("robot_1", "turtlebot3_burger")

# Test at different times
for time in ["sunrise", "noon", "sunset", "night"]:
    await set_day_night_cycle(start_time=time, cycle_duration=0)
    camera_data = await get_sensor_data("robot_1", "camera")
    # Analyze camera performance at different lighting
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gazebo_mcp --cov-report=html

# Run specific test
pytest tests/test_simulation_control.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

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

# Run with debug logging
gazebo-mcp-server --log-level DEBUG
```

### TurtleBot3 Models Not Found

```bash
# Install TurtleBot3 packages
sudo apt install ros-humble-turtlebot3-*

# Set TurtleBot3 model
export TURTLEBOT3_MODEL=burger
```

## Performance

- **Tool Latency**: < 100ms for cached operations
- **Spawn Model**: ~ 500ms (depends on model complexity)
- **Sensor Data**: ~ 50ms (one message latency)
- **World Generation**: 1-5s (depends on complexity)

## Roadmap

- [ ] Phase 1: Core infrastructure and basic tools ✅ (In Progress)
- [ ] Phase 2: Advanced world generation
- [ ] Phase 3: Multi-robot coordination
- [ ] Phase 4: Recording and playback
- [ ] Phase 5: AI-assisted world generation
- [ ] Phase 6: Web dashboard for monitoring

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://github.com/anthropics/mcp) by Anthropic
- [ROS2](https://docs.ros.org/en/humble/) by Open Robotics
- [Gazebo](https://gazebosim.org/) by Open Robotics
- [TurtleBot3](https://emanual.robotis.com/docs/en/platform/turtlebot3/) by ROBOTIS

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/gazebo-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/gazebo-mcp/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/gazebo-mcp/wiki)

## Citation

If you use this project in your research, please cite:

```bibtex
@software{gazebo_mcp,
  title = {Gazebo MCP Server: ROS2 Model Context Protocol for Gazebo},
  author = {Gazebo MCP Team},
  year = {2024},
  url = {https://github.com/yourusername/gazebo-mcp}
}
```

---

**Built with ❤️ for the robotics and AI community**
