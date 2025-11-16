# Gazebo MCP - MCP Hackathon Project

This repository contains projects developed for the MCP Hackathon.

## Projects

### 🤖 [ROS2 Gazebo MCP Server](ros2_gazebo_mcp/)

A comprehensive Model Context Protocol (MCP) server that enables AI assistants like Claude to control Gazebo simulations through ROS2.

**Features:**
- Full Gazebo simulation control (start, stop, pause, reset)
- TurtleBot3 robot management (spawn, control, sensors)
- Dynamic world generation (objects, terrain, lighting)
- Live world updates during simulation
- Real-time sensor data access (camera, LiDAR, IMU, GPS)

**Quick Start:**
```bash
cd ros2_gazebo_mcp
pip install -r requirements.txt
pip install -e .
gazebo-mcp-server
```

See the [ROS2 Gazebo MCP documentation](ros2_gazebo_mcp/README.md) for detailed installation and usage instructions.

---

## Repository Structure

```
gazebo-mcp/
├── ros2_gazebo_mcp/          # ROS2 Gazebo MCP Server project
│   ├── src/                   # Source code
│   ├── docs/                  # Documentation
│   ├── tests/                 # Test suite
│   ├── examples/              # Example scripts
│   └── README.md              # Project documentation
└── claude/                    # Claude Code learning system (submodule)
```

## Development

This project is actively being developed. See individual project READMEs for:
- Installation instructions
- Usage examples
- API documentation
- Contributing guidelines

## License

MIT License - see individual project LICENSE files for details.
