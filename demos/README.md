# Gazebo MCP Demonstrations

Complete demonstration suite for the Gazebo Model Context Protocol (MCP) server, showcasing robot simulation and control capabilities.

## Overview

This collection of demos demonstrates the full capabilities of the Gazebo MCP system, from basic operations to advanced robot navigation. Each demo is self-contained with complete setup, execution, and testing infrastructure.

## Quick Start

### Unified Launcher

The easiest way to run demos:

```bash
cd demos
./run_demo.py
```

This launches an interactive menu where you can select and run any demo.

### Direct Execution

Run a specific demo directly:

```bash
# Demo 1: Hello World
./run_demo.py --run 1

# Demo 2: Obstacle Course
./run_demo.py --run 2
```

### List Available Demos

```bash
./run_demo.py --list
```

### Get Setup Instructions

```bash
./run_demo.py --setup 1  # Hello World setup
./run_demo.py --setup 2  # Obstacle Course setup
```

## Available Demos

### 1. Hello World (`01_hello_world/`)

**Difficulty**: Beginner
**Duration**: ~10 seconds
**Prerequisites**: Modern Gazebo, ros_gz_bridge

Simple demonstration of basic Gazebo MCP operations:
- Environment validation
- ROS2 initialization
- Model spawning (box)
- Model manipulation (move)
- Model deletion

Perfect for:
- First-time users
- Understanding basic MCP operations
- Verifying system setup
- Learning the demo framework

[**Full Documentation →**](01_hello_world/README.md)

### 2. Obstacle Course Challenge (`02_obstacle_course/`)

**Difficulty**: Intermediate
**Duration**: ~25 seconds
**Prerequisites**: Modern Gazebo, ros_gz_bridge, custom world

Advanced robot navigation through obstacle course:
- Custom world with physics simulation
- Multi-model spawning (robot, obstacles, target)
- Differential drive robot with wheels
- Waypoint-based navigation
- Collision environment

Perfect for:
- Understanding complex scenarios
- Multi-model management
- Robot navigation concepts
- Physics simulation
- Real-world use cases

[**Full Documentation →**](02_obstacle_course/README.md)

## Demo Framework

All demos are built on a common framework that provides:

- **DemoExecutor**: Base class with step management, timeouts, error handling
- **DemoValidator**: Environment validation (commands, packages, files)
- **ConfigLoader**: YAML configuration parsing and validation
- **Step System**: Structured execution with progress tracking
- **Error Handling**: Graceful failures with cleanup

### Framework Components

```
framework/
├── __init__.py              # Package exports
├── demo_executor.py         # Base executor class
├── demo_validator.py        # Validation utilities
└── config_loader.py         # Config management
```

See [Framework Documentation](framework/) for details.

## System Requirements

### Required Software

- **Operating System**: Ubuntu 22.04 or later
- **ROS2**: Humble or later
- **Gazebo**: Modern Gazebo (Fortress/Garden/Harmonic)
- **Python**: 3.10+

### Required ROS2 Packages

```bash
sudo apt install -y \
    ros-humble-ros-base \
    ros-humble-ros-gz-bridge \
    ros-humble-ros-gz-interfaces
```

### Python Dependencies

```bash
pip install rclpy pyyaml
```

### Verify Installation

```bash
# Check ROS2
ros2 --version

# Check Gazebo
gz sim --version

# Check ros_gz_bridge
ros2 pkg list | grep ros_gz_bridge

# Check Python
python3 --version  # Should be 3.10+
```

## Setup Instructions

### Common Setup (All Demos)

1. **Source ROS2 environment**:
```bash
source /opt/ros/humble/setup.bash
```

2. **Build the MCP server** (if not already built):
```bash
cd ros2_gazebo_mcp
colcon build
source install/setup.bash
```

### Demo-Specific Setup

Each demo has specific setup requirements:

#### Hello World Demo

Requires empty Gazebo world:

```bash
# Terminal 1: Start Gazebo
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf

# Terminal 2: Start bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"

# Terminal 3: Run demo
cd demos
./run_demo.py --run 1
```

#### Obstacle Course Demo

Has automated setup script:

```bash
cd demos/02_obstacle_course
./setup.sh  # Starts Gazebo + bridge automatically

# Then run demo (same terminal or new one)
./obstacle_course_demo.py
```

## Running Tests

Each demo includes unit tests.

### Run All Tests

```bash
# From demos directory
pytest -v

# Or with coverage
pytest --cov=framework --cov=01_hello_world --cov=02_obstacle_course
```

### Run Demo-Specific Tests

```bash
# Hello World tests
cd 01_hello_world
pytest test_hello_world_demo.py -v

# Obstacle Course tests
cd 02_obstacle_course
pytest test_obstacle_course_demo.py -v
```

### Run Framework Tests

```bash
cd framework
pytest -v
```

## CI/CD Integration

Demos are integrated with GitHub Actions for automated testing.

### Workflow File

See `.github/workflows/demo-tests.yml` for CI configuration.

### What Gets Tested

- ✅ Configuration validation
- ✅ File existence checks
- ✅ Framework unit tests
- ✅ Demo-specific unit tests
- ⚠️ Full demo execution (requires Gazebo - manual testing)

### Running CI Locally

```bash
# Install act (GitHub Actions local runner)
# https://github.com/nektos/act

# Run all workflows
act

# Run specific workflow
act -j test-demos
```

## Troubleshooting

### Common Issues

#### "ROS2 not found"

**Solution**:
```bash
source /opt/ros/humble/setup.bash
# Add to ~/.bashrc for persistence
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

#### "Gazebo not running"

**Symptoms**: Demo fails at validation step

**Solution**:
```bash
# Check if Gazebo is running
ps aux | grep "gz sim"

# Start Gazebo if not running
gz sim /path/to/world.sdf
```

#### "ros_gz_bridge package not found"

**Solution**:
```bash
sudo apt install ros-humble-ros-gz-bridge ros-humble-ros-gz-interfaces
```

#### Service timeouts

**Symptoms**: Operations timeout after 30-45 seconds

**Solutions**:
1. Wait for bridge warmup (5 seconds after starting)
2. Verify services exist: `ros2 service list | grep /world/`
3. Increase timeout in config.yaml
4. Check bridge logs for errors

#### Configuration errors

**Symptoms**: "Config validation failed"

**Solution**: Check YAML syntax:
```bash
# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Debug Mode

Enable verbose logging:

```bash
# Set environment variable
export DEMO_DEBUG=1

# Run demo
./run_demo.py --run 1
```

### Getting Help

1. Check demo-specific README files
2. Review [Deployment Guide](../ros2_gazebo_mcp/docs/DEPLOYMENT_GUIDE_MODERN_GAZEBO.md)
3. Check [Troubleshooting Guide](../ros2_gazebo_mcp/docs/TROUBLESHOOTING_GUIDE_BRIDGE.md)
4. Open an issue on GitHub

## Development

### Creating New Demos

1. **Create demo directory**:
```bash
mkdir demos/03_my_demo
cd demos/03_my_demo
```

2. **Create configuration**:
```yaml
# config.yaml
demo_name: "My Demo"
description: "Demo description"
gazebo_world: "my_world"
timeout: 30.0

models:
  my_model:
    pose:
      position: [0, 0, 0]
      orientation: [0, 0, 0, 1]
```

3. **Implement demo**:
```python
# my_demo.py
from framework import DemoExecutor

class MyDemo(DemoExecutor):
    def __init__(self, config_path):
        super().__init__("My Demo", "Demo description")
        self.config = ConfigLoader.load_demo_config(config_path)
        self._register_steps()

    def _register_steps(self):
        self.register_step(
            name="Step 1",
            active_name="Executing step 1",
            execute=self._step_1,
            timeout=30.0
        )

    async def _step_1(self):
        # Implementation
        return {"success": True}

    async def setup(self):
        pass

    async def teardown(self):
        pass
```

4. **Create tests**:
```python
# test_my_demo.py
def test_config_loads():
    config = ConfigLoader.load_demo_config("config.yaml")
    assert config.demo_name == "My Demo"
```

5. **Update launcher**:
Add your demo to `run_demo.py` in the `list_available_demos()` function.

### Demo Best Practices

- ✅ Use DemoExecutor as base class
- ✅ Load configuration from YAML
- ✅ Validate environment before execution
- ✅ Implement proper cleanup in teardown()
- ✅ Use timeouts for all operations
- ✅ Mark critical vs non-critical steps
- ✅ Provide clear progress messages
- ✅ Include comprehensive tests
- ✅ Document setup requirements

## Architecture

```
demos/
├── run_demo.py              # Unified launcher
├── README.md                # This file
│
├── framework/               # Shared demo framework
│   ├── demo_executor.py
│   ├── demo_validator.py
│   └── config_loader.py
│
├── 01_hello_world/          # Demo 1: Hello World
│   ├── hello_world_demo.py
│   ├── config.yaml
│   ├── test_hello_world_demo.py
│   └── README.md
│
└── 02_obstacle_course/      # Demo 2: Obstacle Course
    ├── obstacle_course_demo.py
    ├── config.yaml
    ├── setup.sh
    ├── worlds/
    │   └── obstacle_course.sdf
    ├── models/
    │   └── simple_robot.sdf
    ├── test_obstacle_course_demo.py
    └── README.md
```

## Performance

### Execution Times

| Demo | Typical Duration | Steps | Models |
|------|-----------------|-------|--------|
| Hello World | ~10 seconds | 5 | 1 |
| Obstacle Course | ~25 seconds | 10 | 4 |

### Resource Usage

- **Memory**: ~200MB (Gazebo) + ~50MB (bridge) + ~20MB (demo)
- **CPU**: Varies with physics complexity
- **Disk**: <10MB for all demos

## Roadmap

### Planned Demos

- **Demo 3**: Sensor Integration (camera, lidar)
- **Demo 4**: Multi-Robot Coordination
- **Demo 5**: Manipulation (arm + gripper)
- **Demo 6**: SLAM Navigation

### Framework Enhancements

- Parallel step execution
- Step retry logic
- Demo recording/playback
- Performance profiling
- Web-based visualization

## Contributing

Contributions welcome! To add a demo:

1. Fork the repository
2. Create demo following structure above
3. Add tests (aim for >80% coverage)
4. Update run_demo.py
5. Document in README
6. Submit pull request

## License

See [LICENSE](../LICENSE) file in root directory.

## Related Documentation

- [Gazebo MCP Server](../ros2_gazebo_mcp/README.md)
- [Modern Gazebo Deployment](../ros2_gazebo_mcp/docs/DEPLOYMENT_GUIDE_MODERN_GAZEBO.md)
- [Bridge Integration](../ros2_gazebo_mcp/docs/BRIDGE_INTEGRATION_SUCCESS.md)
- [Troubleshooting](../ros2_gazebo_mcp/docs/TROUBLESHOOTING_GUIDE_BRIDGE.md)

---

**Last Updated**: 2025-11-25
**Version**: 1.0.0
**Status**: Production Ready
