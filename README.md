# 🤖 Gazebo MCP Server - AI-Powered Robot Simulation

> **MCP 1st Birthday Hackathon Submission**
> Bringing the power of Gazebo robotics simulation to AI assistants through the Model Context Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue.svg)](https://docs.ros.org/en/humble/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-orange.svg)](https://gazebosim.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-purple.svg)](https://github.com/anthropics/mcp)

## 🎯 What is Gazebo MCP?

**Gazebo MCP** is a Model Context Protocol server that bridges the gap between AI assistants (like Claude) and the Gazebo robotics simulator. It enables natural language control of complex robot simulations, making robotics research and development more accessible and intuitive.

Instead of writing complex code to test robots, you can simply ask Claude:
- *"Spawn a TurtleBot3 in an obstacle course and test its navigation"*
- *"Create a terrain with hills and test the robot's climbing ability"*
- *"Set up a day/night cycle and analyze how lighting affects the camera sensors"*

## ✨ Why This Matters

**Traditional robotics workflow:**
```bash
# Write launch files
# Configure YAML files
# Write Python/C++ code for tests
# Debug ROS2 nodes
# Manually verify sensors
```

**With Gazebo MCP:**
```
Just describe what you want to test in natural language.
Claude handles the rest through MCP tools.
```

This dramatically accelerates robotics development, testing, and education by removing the barrier between ideas and simulation.

## 🚀 Key Features

### 🎮 Complete Simulation Control
- **Start/Stop/Pause** Gazebo simulations with a single tool call
- **Dynamic Physics** configuration (gravity, timestep, real-time factor)
- **State Management** - Save, restore, and reset simulation states

### 🤖 Robot Management
- **TurtleBot3 Integration** - Spawn Burger, Waffle, or Waffle Pi variants
- **Custom Robots** - Load any URDF/SDF model
- **Multi-Robot** - Control multiple robots simultaneously
- **Real-time Control** - Send velocity and joint commands

### 🌍 Dynamic World Generation
- **Procedural Environments** - Generate test worlds on-demand
- **Object Placement** - Add boxes, spheres, cylinders, or custom meshes
- **Terrain Generation** - Create heightmaps and varied surface types
- **Obstacle Courses** - Automatically generate navigation challenges

### 💡 Advanced Lighting
- **Day/Night Cycles** - Simulate realistic lighting conditions
- **Multiple Light Types** - Ambient, directional, point, and spot lights
- **Real-time Updates** - Modify lighting during simulation

### 📡 Comprehensive Sensor Access
- **Camera** - RGB and depth images
- **LiDAR** - Point cloud data for navigation
- **IMU** - Acceleration and orientation
- **GPS** - Position tracking
- **Contact Sensors** - Collision detection

### ⚡ Live Simulation Updates
- **Real-time Modifications** - Change object properties during simulation
- **Force/Torque Application** - Test robot responses to disturbances
- **Dynamic Spawning** - Add/remove models while running

## 📺 Demo Video

> [!NOTE]
> Check out our [demo video](#) showing Claude controlling a TurtleBot3 through natural language!

## 🎬 Quick Start

### Prerequisites

- **ROS2** Humble or Jazzy
- **Gazebo** Harmonic or Garden
- **Python** 3.10+
- **Ubuntu** 22.04/24.04 (recommended)

### Installation

```bash
# 1. Install ROS2 and Gazebo
sudo apt update
sudo apt install ros-humble-desktop ros-humble-gazebo-ros-pkgs ros-humble-turtlebot3-*
sudo apt install gz-harmonic

# 2. Clone and setup
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp/ros2_gazebo_mcp
source /opt/ros/humble/setup.bash

# 3. Install Python dependencies
pip install -r requirements.txt
pip install -e .

# 4. Start the MCP server
gazebo-mcp-server
```

### Using with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "gazebo": {
      "command": "gazebo-mcp-server",
      "env": {
        "ROS_DOMAIN_ID": "0"
      }
    }
  }
}
```

Restart Claude Desktop, and you'll see the Gazebo MCP tools available!

## 💡 Usage Examples

### Example 1: Navigation Testing

**You ask Claude:**
> "Create a simple obstacle course and test TurtleBot3's navigation"

**Claude uses MCP tools:**
```python
# 1. Start simulation
await use_mcp_tool("start_simulation", {"world_name": "empty_world"})

# 2. Spawn robot
await use_mcp_tool("spawn_model", {
    "model_name": "robot_1",
    "model_type": "turtlebot3_burger",
    "x": 0.0, "y": 0.0, "z": 0.0
})

# 3. Create obstacles
await use_mcp_tool("create_obstacle_course", {
    "num_obstacles": 10,
    "area_size": 20.0,
    "obstacle_types": ["box", "cylinder"]
})

# 4. Move robot
await use_mcp_tool("send_velocity_command", {
    "model_name": "robot_1",
    "linear_x": 0.2,
    "angular_z": 0.0
})

# 5. Get LiDAR data
lidar = await use_mcp_tool("get_sensor_data", {
    "model_name": "robot_1",
    "sensor_type": "lidar"
})
```

### Example 2: Lighting Conditions Test

**You ask Claude:**
> "Test how the robot's camera performs at different times of day"

**Claude automates:**
- Spawns robot with camera
- Cycles through sunrise → noon → sunset → night
- Captures camera data at each time
- Analyzes image quality and brightness
- Reports findings

### Example 3: Multi-Terrain Testing

**You ask Claude:**
> "Create a world with different terrain types and test the robot on each"

**Claude sets up:**
- Heightmap terrain with hills
- Different surface materials (grass, sand, gravel)
- Tests robot mobility on each surface
- Measures performance metrics

## 🏗️ Architecture

```
┌─────────────────┐
│  Claude / AI    │
│   Assistant     │
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼────────┐
│  Gazebo MCP     │
│     Server      │
├─────────────────┤
│  • Tools        │
│  • Resources    │
│  • Prompts      │
└────────┬────────┘
         │ ROS2
         │
┌────────▼────────┐
│  ROS2 Bridge    │
│     Node        │
└────────┬────────┘
         │ Gazebo Transport
         │
┌────────▼────────┐
│    Gazebo       │
│   Simulation    │
└─────────────────┘
```

**Components:**
- **MCP Server** - Handles tool calls and manages resources
- **ROS2 Bridge** - Translates MCP to ROS2 messages
- **Gazebo Interface** - Direct communication with simulator
- **Tool Modules** - Organized by functionality (simulation, models, sensors, etc.)

## 🛠️ Available MCP Tools

We provide **30+ MCP tools** organized into categories:

| Category | Example Tools | Count |
|----------|---------------|-------|
| **Simulation Control** | `start_simulation`, `pause_simulation`, `reset_simulation` | 6 |
| **Model Management** | `spawn_model`, `delete_model`, `get_model_state` | 5 |
| **Robot Control** | `send_velocity_command`, `send_joint_command` | 3 |
| **Sensor Access** | `get_sensor_data`, `list_sensors`, `configure_sensor` | 3 |
| **World Generation** | `create_empty_world`, `create_obstacle_course` | 4 |
| **Terrain Tools** | `create_heightmap`, `set_surface_type` | 3 |
| **Lighting Tools** | `set_day_night_cycle`, `add_point_light` | 7 |
| **Live Updates** | `apply_force`, `modify_model_property` | 5 |

See the [full API documentation](ros2_gazebo_mcp/README.md) for details.

## 📚 Use Cases

### 🎓 Education
- **Learn ROS2/Gazebo** without complex setup
- **Interactive tutorials** guided by AI
- **Experiment safely** in simulation

### 🔬 Research
- **Rapid prototyping** of robot behaviors
- **Automated testing** of algorithms
- **Parameter sweeps** with AI assistance

### 🏭 Development
- **CI/CD integration** for robot testing
- **Regression testing** of navigation stacks
- **Performance benchmarking** across scenarios

### 🎮 Robotics Competitions
- **Quick scenario setup** for practice
- **Strategy testing** before hardware deployment
- **Team collaboration** with shared simulations

## 📁 Project Structure

```
gazebo-mcp/
├── ros2_gazebo_mcp/          # Main MCP server project
│   ├── src/gazebo_mcp/
│   │   ├── server.py         # MCP server implementation
│   │   ├── bridge/           # ROS2 bridge components
│   │   ├── tools/            # MCP tool implementations
│   │   └── utils/            # Utilities and helpers
│   ├── tests/                # Comprehensive test suite
│   ├── examples/             # Usage examples
│   ├── docs/                 # Documentation
│   ├── requirements.txt      # Python dependencies
│   └── pyproject.toml        # Package configuration
└── README.md                 # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=gazebo_mcp --cov-report=html

# Specific test categories
pytest tests/test_simulation_control.py
pytest tests/test_sensor_tools.py
```

## 🎯 Roadmap

- [x] **Phase 1**: Core MCP infrastructure and basic simulation control
- [x] **Phase 2**: Robot spawning and sensor integration
- [ ] **Phase 3**: Advanced world generation with AI assistance
- [ ] **Phase 4**: Multi-robot coordination and swarm simulation
- [ ] **Phase 5**: Recording/playback for reproducible tests
- [ ] **Phase 6**: Web dashboard for monitoring

## 🤝 Contributing

We welcome contributions! This project is part of the MCP 1st Birthday Hackathon, but we're building for the long term.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📖 Documentation

- **[Full Documentation](ros2_gazebo_mcp/README.md)** - Complete guide
- **[Architecture](ros2_gazebo_mcp/docs/ARCHITECTURE.md)** - System design
- **[API Reference](ros2_gazebo_mcp/docs/API.md)** - Tool documentation
- **[Examples](ros2_gazebo_mcp/examples/)** - Code samples

## 🏆 MCP Birthday Hackathon

This project is our submission to the [MCP 1st Birthday Hackathon](https://huggingface.co/MCP-1st-Birthday) (November 14-30, 2025).

**Why we built this:**
- **Bridge two powerful ecosystems** - AI and robotics
- **Lower barriers** to robotics development
- **Enable new workflows** that weren't possible before
- **Showcase MCP's versatility** in complex, real-time systems

## 🙏 Acknowledgments

- **[Anthropic](https://anthropic.com)** - For creating MCP and Claude
- **[HuggingFace](https://huggingface.co)** - For hosting the MCP Birthday Hackathon
- **[Open Robotics](https://openrobotics.org)** - For ROS2 and Gazebo
- **[ROBOTIS](https://robotis.com)** - For TurtleBot3

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact & Support

- **GitHub**: [kvgork/gazebo-mcp](https://github.com/kvgork/gazebo-mcp)
- **Issues**: [Report bugs or request features](https://github.com/kvgork/gazebo-mcp/issues)
- **Discussions**: [Join the conversation](https://github.com/kvgork/gazebo-mcp/discussions)

## 🌟 Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Built with ❤️ for the robotics, AI, and MCP communities**

*Making robot simulation accessible to everyone, one natural language command at a time.*
