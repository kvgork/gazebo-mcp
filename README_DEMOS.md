# Demos Location

The Gazebo MCP demonstration suite has been moved to the `demos/` directory within this project.

## Quick Start

```bash
cd demos
./run_demo_ros2.sh
```

## Documentation

All demo documentation is located in the demos folder:

- **[demos/QUICKSTART.md](demos/QUICKSTART.md)** - 5-minute quick start
- **[demos/README.md](demos/README.md)** - Complete documentation
- **[demos/INDEX.md](demos/INDEX.md)** - Navigation guide
- **[demos/TROUBLESHOOTING.md](demos/TROUBLESHOOTING.md)** - Issue resolution

## Available Demos

### Demo 1: Hello World
**Location**: `demos/01_hello_world/`
**Duration**: ~10 seconds
**Difficulty**: Beginner

Simple demonstration of basic Gazebo MCP operations.

### Demo 2: Obstacle Course
**Location**: `demos/02_obstacle_course/`
**Duration**: ~25 seconds
**Difficulty**: Intermediate

Advanced robot navigation through obstacle course.

## Running Demos

### Option 1: Interactive Launcher (Recommended)

```bash
cd demos
./run_demo_ros2.sh
```

### Option 2: Direct Execution

```bash
cd demos
./run_demo_ros2.sh --run 1  # Hello World
./run_demo_ros2.sh --run 2  # Obstacle Course
```

### Option 3: Individual Demo

```bash
cd demos/01_hello_world
source /opt/ros/humble/setup.bash
/usr/bin/python3 hello_world_demo.py
```

## Prerequisites

- ROS2 Humble
- Modern Gazebo (Fortress/Garden/Harmonic)
- ros_gz_bridge package
- System Python 3.10

See [demos/README.md](demos/README.md#system-requirements) for complete setup instructions.

## Troubleshooting

If you encounter issues:

1. Use the ROS2 wrapper script: `./run_demo_ros2.sh`
2. Check [demos/TROUBLESHOOTING.md](demos/TROUBLESHOOTING.md)
3. Run verification: `cd demos && ./verify_implementation.sh`
4. Review [demos/README.md](demos/README.md)

## Structure

```
ros2_gazebo_mcp/
├── demos/                    # Demo suite (NEW)
│   ├── framework/           # Reusable framework
│   ├── 01_hello_world/      # Demo 1
│   ├── 02_obstacle_course/  # Demo 2
│   ├── run_demo.py          # Python launcher
│   ├── run_demo_ros2.sh     # ROS2 wrapper
│   └── README.md            # Complete guide
│
├── src/                     # MCP server source
├── docs/                    # Documentation
└── tests/                   # Tests
```

## Integration with MCP Server

The demos use the Modern Gazebo adapter from the MCP server:

```python
from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
```

Make sure to build the MCP server first:

```bash
cd ros2_gazebo_mcp
colcon build
source install/setup.bash
```

## Status

✅ **Production Ready**
- 24/24 tests passing
- Complete documentation
- CI/CD configured
- All files validated

For more details, see [demos/DEPLOYMENT_STATUS.md](demos/DEPLOYMENT_STATUS.md)

---

**Quick Links**:
- [Quick Start](demos/QUICKSTART.md)
- [Full Documentation](demos/README.md)
- [Troubleshooting](demos/TROUBLESHOOTING.md)
- [Test Results](demos/TEST_RESULTS.md)
