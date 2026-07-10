# Gazebo MCP Server

> **ROS2 Model Context Protocol Server for Gazebo Simulation**

Enable AI assistants like Claude to control Gazebo simulations, spawn and manage models, query world and physics properties, drive robots, and gather sensor data through a standardized MCP interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue.svg)](https://docs.ros.org/en/humble/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-orange.svg)](https://gazebosim.org/)

## Features

The server exposes **27 MCP tools across 5 categories**. See [Available MCP Tools](#available-mcp-tools) for the full per-tool list.

### Model Management
- Spawn models from URDF/SDF files or XML strings
- List, delete, and query models in the simulation
- Set model pose and velocity (teleport / set velocity)
- Apply force and torque for physics testing

### Sensor Integration
- List sensors with filtering by model/type
- Read latest sensor data (camera, depth, RGBD, IMU, LiDAR, GPS, contact, force/torque, magnetometer, altimeter, sonar)
- Subscribe to a sensor topic and cache streamed data

### World Tools
- Validate and load world files; save the current world
- Query physics, gravity, and scene properties
- Update world properties and set the gravity vector (Earth, Moon, zero-g, custom)

### Simulation Control
- Pause, unpause, and reset the simulation
- Set simulation speed and query simulation time / performance metrics
- Get comprehensive simulation status and list active worlds

### ROS2 Tools
- List ROS2 topics and inspect topic info
- Publish velocity (twist) commands to drive a robot
- Look up TF transforms between coordinate frames
- Spawn models from SDF/URDF XML and read joint states

### Developer Experience & Debugging
- Add and clear visual debug markers; highlight models
- Generate RViz2 launch and visualization-panel instructions
- Record and play back simulations via rosbag (`ros2 bag` commands)
- Save and restore simulation snapshots for regression testing
- Profile performance and identify bottlenecks

> **Note:** Tools gracefully fall back to mock data when Gazebo is not running, so the server is usable for development and testing without a live simulator.

## Quick Start

### Prerequisites

- **ROS2**: Humble or Jazzy (LTS recommended)
- **Gazebo**: Modern Gazebo (Fortress, Garden, or Harmonic) - **Primary Support**
  - ⚠️ Classic Gazebo 11 is deprecated and will be removed in v2.0.0
- **Python**: 3.10 or higher
- **OS**: Ubuntu 22.04 or 24.04 (recommended)

### Installation

There are two ways to install: **pixi** (recommended — self-contained, no `apt`/system ROS2 needed) or a manual ROS2 + pip setup.

---

#### Option A — pixi (recommended)

[pixi](https://pixi.sh) pulls ROS2 Jazzy from [RoboStack](https://robostack.github.io/) and the Python deps from conda-forge into one reproducible, locked environment. No `/opt/ros`, no `apt`.

```bash
# Install pixi (if you don't have it)
curl -fsSL https://pixi.sh/install.sh | bash

# Clone and install
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp
pixi install            # server only
# pixi install -e dev   # + pytest/ruff/mypy
# pixi install -e sim   # + full gz simulator (ros_gz)
# pixi install -e full  # everything

# Run the server
pixi run serve
```

Environments:

| Command | Includes |
|---|---|
| `pixi install` | ROS2 Jazzy (rclpy + msgs) + MCP server |
| `pixi install -e dev` | + pytest, pytest-asyncio/cov/mock/timeout, ruff, mypy |
| `pixi install -e sim` | + `ros-jazzy-ros-gz` (full Gazebo simulator + bridge) |
| `pixi install -e full` | sim + dev |

Tasks: `pixi run serve` (stdio server), `pixi run server` (console script), `pixi run -e dev test`, `pixi run -e dev lint`.

The package is installed editable, so `gazebo_mcp` and the `gazebo-mcp-server` entry point are immediately on PATH inside the env. Backend defaults (`GAZEBO_BACKEND=modern`, `GAZEBO_WORLD_NAME=empty`, `PYTHONUNBUFFERED=1`) are set via pixi activation — override per shell as needed.

> Modern (`gz`) Gazebo is the default backend and is fully covered by RoboStack. The classic-Gazebo `gazebo_msgs` spawn/delete paths are not packaged by RoboStack; use Option B if you need classic Gazebo.

---

#### Option B — manual ROS2 + pip

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

# Note: Classic Gazebo (gazebo-ros-pkgs) is deprecated
# Only install if you need legacy support:
# sudo apt install ros-humble-gazebo-ros-pkgs
```

#### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp

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
```

**Actuation safety bounds (P5 hardening).** All actuation is clamped at a single
bridge-level chokepoint (identical across mock/modern/classic). Defaults and
overrides:

```bash
export GAZEBO_MAX_FORCE_N=1000          # force magnitude cap (N)
export GAZEBO_MAX_TORQUE_NM=500         # torque magnitude cap (N·m)
export GAZEBO_MAX_JOINT_VELOCITY=10     # vel-mode joint cap (rad/s or m/s)
export GAZEBO_MAX_JOINT_EFFORT=500      # force/effort-mode joint cap (N·m or N)
export GAZEBO_MAX_PERSISTENT_WRENCHES=8 # max simultaneous persistent wrenches
export GAZEBO_RATE_LIMIT_HZ=50          # per-entity rate cap (Hz); <=0 disables
export GAZEBO_STRICT_BOUNDS=0           # 0 = clamp (default); 1 = reject over-limit
```

By default over-limit commands are **clamped** (vectors scaled, direction
preserved); with `GAZEBO_STRICT_BOUNDS=1` they are **rejected** with
`ACTUATION_BOUNDS_EXCEEDED`. Persistent wrenches require an explicit clear before
a new one can take a slot. See [`docs/guides/p5-hardening.md`](docs/guides/p5-hardening.md)
for full details, plus the notify-then-poll sensor model, CPU-only physics,
image caps, and live-Gazebo acceptance requirements.

**Configuration Priority:**
1. Environment variables (highest)
2. Default values in code (lowest)

**Note:** Modern Gazebo is now the default backend. Classic Gazebo support is deprecated and will be removed in v2.0.0.

**For Claude Desktop Integration**, add to your `claude_desktop_config.json`:

If installed via **pixi (Option A)** — `pixi run` handles ROS2 sourcing and env activation, so no `PYTHONPATH`/sourcing needed:

```json
{
  "mcpServers": {
    "gazebo": {
      "command": "pixi",
      "args": ["run", "--manifest-path", "/path/to/gazebo-mcp/pixi.toml", "serve"]
    }
  }
}
```

If installed via **manual setup (Option B)**:

```json
{
  "mcpServers": {
    "gazebo": {
      "command": "python",
      "args": ["-m", "gazebo_mcp.server"],
      "cwd": "/path/to/gazebo_mcp_package",
      "env": {
        "PYTHONPATH": "/path/to/gazebo_mcp_package/src",
        "ROS_DOMAIN_ID": "0",
        "GAZEBO_BACKEND": "modern",
        "GAZEBO_WORLD_NAME": "default",
        "GAZEBO_TIMEOUT": "5.0"
      }
    }
  }
}
```

See `mcp/README.md` for detailed MCP server documentation.

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

# 4. List available sensors
await use_mcp_tool("gazebo_list_sensors", {
    "model_name": "my_robot"
})

# 5. Get sensor data
sensor_data = await use_mcp_tool("gazebo_get_sensor_data", {
    "sensor_name": "front_camera",
    "timeout": 5.0
})

# 6. Control simulation
await use_mcp_tool("gazebo_pause_simulation", {})
await use_mcp_tool("gazebo_unpause_simulation", {})

# 7. Get simulation status
status = await use_mcp_tool("gazebo_get_simulation_status", {})
```

## Practical Examples

The `examples/` directory contains **5 complete working examples** demonstrating real-world usage:

1. **[01_basic_connection.py](examples/01_basic_connection.py)** - MCP server basics, tool discovery, token efficiency
2. **[02_spawn_and_control.py](examples/02_spawn_and_control.py)** - Model spawning, state queries, lifecycle management
3. **[03_sensor_streaming.py](examples/03_sensor_streaming.py)** - Sensor discovery, data access, streaming
4. **[04_simulation_control.py](examples/04_simulation_control.py)** - Pause/resume, reset, time queries, world properties
5. **[05_complete_workflow.py](examples/05_complete_workflow.py)** - Full robot testing workflow (8 phases)

**All examples work without ROS2/Gazebo** using mock data. See **[examples/README.md](examples/README.md)** for detailed documentation.

```bash
# Run any example (no Gazebo required)
cd examples/
python 01_basic_connection.py
python 05_complete_workflow.py
```

## Available MCP Tools

**Total Tools**: 69 tools across 10 categories

See `mcp/README.md` for detailed tool documentation and examples.

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

### Developer Experience & Debugging (12 tools)

| Tool | Description |
|------|-------------|
| `gazebo_add_debug_marker` | Add a visual debug marker (line, arrow, point, text, bounding_box, trajectory, force_vector) |
| `gazebo_clear_debug_markers` | Remove a specific marker or clear all markers |
| `gazebo_highlight_model` | Highlight a model with a visual effect (glow, outline, transparency, color_overlay) |
| `gazebo_launch_rviz` | Generate the RViz2 launch command and recommended panel configuration |
| `gazebo_add_rviz_visualization` | Generate RViz2 display-panel instructions for a topic (point_cloud, marker, trajectory, map, laser_scan, image) |
| `gazebo_start_recording` | Start a rosbag recording session; returns the `ros2 bag record` command |
| `gazebo_stop_recording` | Stop the active recording session and report bag info |
| `gazebo_playback_recording` | Generate the `ros2 bag play` command for a recorded bag |
| `gazebo_save_snapshot` | Save a named snapshot of model poses/velocities and world state |
| `gazebo_restore_snapshot` | Restore a previously saved simulation snapshot |
| `gazebo_profile_simulation` | Profile real-time factor, physics step time, FPS, memory, sensor rates |
| `gazebo_identify_bottlenecks` | Return a ranked list of performance bottlenecks with suggestions |

> **Note:** RViz2 launch, rosbag record/play, and snapshot restoration require an external ROS2/Gazebo session — these tools return the exact CLI commands/instructions to run, and operate in mock mode when Gazebo is not available.

### Multi-Robot Coordination (6 tools)

| Tool | Description |
|------|-------------|
| `gazebo_spawn_robot_fleet` | Spawn a fleet with collision-free formation placement (line, grid, circle, random) |
| `gazebo_get_fleet_status` | Query per-robot position, velocity, battery, and task status |
| `gazebo_send_fleet_command` | Dispatch a command (move, stop, formation, sync, return_home) to the whole fleet or a subset |
| `gazebo_apply_swarm_behavior` | Apply a swarm behavior (flocking, coverage, formation_keeping, leader_follower, consensus) |
| `gazebo_visualize_robot_network` | Build comms-graph / task-allocation / formation-line / collision-zone visualization markers |
| `gazebo_enable_multi_robot_collision_avoidance` | Enable inter-robot collision avoidance (dynamic, social_force, velocity_obstacles, priority) |

### Advanced Sensors (8 tools)

| Tool | Description |
|------|-------------|
| `gazebo_fuse_sensor_data` | Fuse multiple sensors (lidar_camera, multi_lidar, imu_gps, camera_depth) |
| `gazebo_visualize_sensor_data` | Build sensor visualization markers (point_cloud, camera_frustum, imu_arrows, gps_path, contact_forces) |
| `gazebo_process_sensor_data` | Apply processing (voxel/statistical filter, image_blur, edge_detection, segmentation, imu_filter, ground_removal) |
| `gazebo_calibrate_sensor` | Calibrate a sensor (camera_intrinsics/extrinsics, lidar_offset, imu_bias, time_sync) |
| `gazebo_monitor_sensor_health` | Report data rate, latency, dropout, and quality score with alerts |
| `gazebo_record_sensor_stream` | Record sensor topics to a bag (none/lz4/zstd compression) |
| `gazebo_detect_objects_in_view` | Run object detection on a camera feed with confidence threshold |
| `gazebo_segment_camera_image` | Semantic or instance segmentation of a camera image |

### SLAM & Mapping (6 tools)

| Tool | Description |
|------|-------------|
| `gazebo_start_slam` | Start SLAM with a chosen backend (slam_toolbox, cartographer, rtabmap, orb_slam3) |
| `gazebo_save_slam_map` | Save the generated map (pgm_yaml or ros_map_server format) |
| `gazebo_load_slam_map` | Load a saved map for localization |
| `gazebo_localize_robot` | Localize in a known map (amcl, map_matching, icp) |
| `gazebo_get_localization_quality` | Report particle spread, match score, and ambiguity |
| `gazebo_detect_loop_closure` | Detect loop closures via visual bag-of-words |

### Navigation & Path Planning — Nav2 (10 tools)

| Tool | Description |
|------|-------------|
| `gazebo_initialize_nav2` | Initialize the Nav2 stack and lifecycle nodes for a robot |
| `gazebo_send_nav_goal` | Send a navigation goal (planner: DWB, TEB, RPP, MPPI) |
| `gazebo_cancel_nav_goal` | Cancel the current or a specific navigation goal |
| `gazebo_get_nav_status` | Query active goal, progress, distance remaining, obstacles |
| `gazebo_plan_path` | Plan a path without executing (A*, RRT, RRT*, DWB, TEB) |
| `gazebo_visualize_path` | Build visualization markers for a planned path |
| `gazebo_create_occupancy_map` | Generate an occupancy grid from the world |
| `gazebo_update_costmap` | Inject, clear, or inflate costmap regions |
| `gazebo_follow_waypoints` | Execute a multi-waypoint mission (sequence, loop, patrol) |
| `gazebo_plan_coverage_path` | Plan area coverage (boustrophedon, spiral, energy_efficient) |

> **Note:** Multi-robot, advanced-sensor, SLAM, and Nav2 tools integrate with external ROS2 stacks (Nav2, SLAM Toolbox, etc.) where available, and operate in deterministic mock mode when Gazebo/ROS2 is not running.

## Project Structure

```
ros2_gazebo_mcp/
├── src/gazebo_mcp/
│   ├── __init__.py
│   ├── bridge/
│   │   ├── __init__.py
│   │   ├── connection_manager.py    # ROS2 lifecycle management
│   │   └── gazebo_bridge_node.py    # Gazebo service interface
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── model_management.py      # Model spawn/delete/list/state
│   │   ├── sensor_tools.py          # Sensor data queries
│   │   ├── world_tools.py           # World loading/properties
│   │   └── simulation_tools.py      # Simulation control
│   └── utils/
│       ├── __init__.py
│       ├── validators.py            # Input validation
│       ├── converters.py            # ROS2 ↔ Python conversions
│       ├── geometry.py              # Quaternion math, transforms
│       ├── exceptions.py            # Custom exceptions
│       ├── logger.py                # Structured logging
│       ├── metrics.py               # Performance metrics collection
│       └── profiler.py              # Tool profiling decorator
├── mcp/
│   ├── server/
│   │   ├── server.py                # Main MCP server (stdio protocol)
│   │   └── adapters/
│   │       ├── __init__.py
│   │       ├── model_management_adapter.py
│   │       ├── sensor_tools_adapter.py
│   │       ├── world_tools_adapter.py
│   │       ├── simulation_tools_adapter.py
│   │       ├── ros2_tools_adapter.py
│   │       └── developer_tools_adapter.py
│   └── README.md                    # MCP server documentation
├── tests/
│   ├── conftest.py                  # Pytest configuration
│   ├── test_integration.py          # Integration tests (80+ tests)
│   ├── test_utils.py                # Unit tests
│   └── README.md                    # Test documentation
├── examples/
│   ├── 01_basic_connection.py       # Basic MCP usage
│   ├── 02_spawn_and_control.py      # Model management
│   ├── 03_sensor_streaming.py       # Sensor data access
│   ├── 04_simulation_control.py     # Simulation control
│   ├── 05_complete_workflow.py      # Full robot testing workflow
│   └── README.md                    # Examples documentation
├── docs/
│   ├── IMPLEMENTATION_PLAN.md       # Original implementation plan
│   ├── PHASE3_PROGRESS.md           # Phase 3 progress tracking
│   ├── PHASE4_PLAN.md               # Phase 4 enhancements plan
│   ├── DEPLOYMENT.md                # Production deployment guide
│   ├── METRICS.md                   # Performance monitoring guide
│   └── ARCHITECTURE.md              # System architecture
├── deployment/
│   ├── gazebo-mcp.service           # systemd service file
│   └── install.sh                   # Production installation script
├── scripts/
│   └── show_metrics.py              # Metrics display and export
├── .github/workflows/
│   ├── test.yml                     # CI/CD pipeline
│   └── pre-commit.yml               # Pre-commit checks
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Docker Compose configuration
├── .dockerignore                    # Docker ignore patterns
├── pyproject.toml                   # Python package configuration
├── package.xml                      # ROS2 package manifest
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── pytest.ini                       # Pytest configuration
└── README.md                        # This file
```

## Documentation

- **[API Reference](docs/api/_build/html/index.html)** - Complete API documentation (Sphinx)
- **[MCP Server Guide](mcp/README.md)** - Complete MCP server documentation
- **[Usage Examples](examples/README.md)** - 5 practical examples with detailed documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment, Docker, systemd, monitoring
- **[Performance Metrics](docs/METRICS.md)** - Monitoring, profiling, and metrics collection
- **[Test Documentation](tests/README.md)** - Test suite and running tests
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[Implementation Plan](docs/IMPLEMENTATION_PLAN.md)** - Original implementation plan
- **[Phase 3 Progress](docs/PHASE3_PROGRESS.md)** - Phase 3 completion summary
- **[Phase 4 Plan](docs/PHASE4_PLAN.md)** - Phase 4 enhancements and production features

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
- See `tests/README.md` for running tests

## Deployment

### Docker Deployment (Recommended for Production)

**Quick Start:**

```bash
# Start all services (Gazebo + MCP Server):
docker-compose up

# Run in background:
docker-compose up -d

# View logs:
docker-compose logs -f mcp_server

# Stop services:
docker-compose down
```

**Development Mode:**

```bash
# Start with development container:
docker-compose --profile development up dev

# Run examples:
docker-compose exec mcp_server python3 examples/01_basic_connection.py

# View metrics:
docker-compose exec mcp_server python3 scripts/show_metrics.py
```

**Monitoring Mode:**

```bash
# Start with metrics exporter:
docker-compose --profile monitoring up

# Metrics exported to: ./metrics/metrics.prom (Prometheus format)
```

See **[Deployment Guide](docs/DEPLOYMENT.md)** for comprehensive deployment documentation including:
- Production deployment with systemd
- Security best practices
- High availability setup
- Monitoring and observability
- Backup and recovery

### Production Deployment (systemd)

**Installation:**

```bash
cd deployment
sudo ./install.sh
```

**Service Management:**

```bash
# Start service:
sudo systemctl start gazebo-mcp

# Check status:
sudo systemctl status gazebo-mcp

# View logs:
sudo journalctl -u gazebo-mcp -f

# Stop service:
sudo systemctl stop gazebo-mcp
```

See **[Deployment Guide](docs/DEPLOYMENT.md)** for complete installation and configuration instructions.

## Development

### Running Tests

```bash
# Unit tests (no ROS2 required):
pytest tests/test_utils.py -v

# Integration tests (ROS2 required):
source /opt/ros/humble/setup.bash
pytest tests/test_integration.py -v --with-ros2

# Full integration tests (Gazebo required):
# Terminal 1:
ros2 launch gazebo_ros gazebo.launch.py

# Terminal 2:
pytest tests/test_integration.py -v --with-gazebo

# Run all tests:
pytest tests/ -v
```

See `tests/README.md` for detailed test documentation.

### Code Quality

```bash
# Type checking (recommended):
mypy src/gazebo_mcp/

# Linting:
ruff check src/ tests/

# Formatting:
black src/ tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

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
ros2 launch gazebo_ros gazebo.launch.py

# Terminal 2 - Run MCP server:
python -m gazebo_mcp.server
```

## Performance

**Token Efficiency:**
- Without ResultFilter: 50,000+ tokens (for 1000 models)
- With `response_format="summary"`: ~500 tokens (95% savings)
- With local filtering: ~2,000 tokens (95%+ savings)

**Response Times:**
- Model operations: < 100ms
- Sensor queries: < 200ms (depends on topic frequency)
- Simulation control: < 50ms
- World queries: < 100ms

**System Requirements:**
- CPU: Minimal overhead (< 5% CPU usage)
- Memory: ~100-200 MB (ROS2 + Python)
- Network: ROS2 local communication only

### Performance Monitoring

View real-time metrics:

```bash
# Show summary:
python3 scripts/show_metrics.py

# Show detailed metrics:
python3 scripts/show_metrics.py --detailed

# Export to Prometheus:
python3 scripts/show_metrics.py --export metrics.prom --format prometheus

# Export to JSON:
python3 scripts/show_metrics.py --export metrics.json --format json
```

See **[Performance Metrics Guide](docs/METRICS.md)** for complete documentation on:
- Automatic metrics collection
- Token efficiency tracking
- Prometheus integration
- Grafana dashboards
- Performance optimization

## Implementation Status

### ✅ Phase 1: Core Infrastructure (100% Complete)
- ROS2 Humble/Jazzy integration
- Gazebo Harmonic integration
- Connection management with auto-reconnect
- Utility functions (validators, converters, geometry)

### ✅ Phase 2: Tool Implementation (100% Complete)
- Model management (6 tools)
- Sensor tools (3 tools)
- World tools (5 tools)
- Simulation control (7 tools)
- ROS2 tools (6 tools)

### ✅ Phase 3: MCP Server & Testing (100% Complete)
- MCP server with stdio protocol
- 6 tool adapters with schemas
- 80+ tests (unit + integration)
- Comprehensive documentation

### ✅ Enhancement Area 7: Developer Experience & Debugging (100% Complete)
- Developer tools (12 tools): debug markers, model highlighting, RViz integration, rosbag record/playback, simulation snapshots, performance profiling
- 49 unit tests (mock-mode coverage), 244 unit tests passing total
- See `CAPABILITY_ENHANCEMENT_PLAN.md` Area 7 for the full capability map

### ✅ Phase 4: Production Enhancements (100% Complete)
- Complete `set_model_state()` implementation for teleporting models
- 5 working usage examples with detailed documentation
- Performance metrics and profiling system
- Docker deployment (Dockerfile + docker-compose)
- CI/CD pipeline (GitHub Actions)
- Production deployment guide (systemd service)
- Comprehensive deployment documentation

### 🔵 Future Enhancements
- Real-time sensor streaming improvements
- Advanced world generation tools
- Multi-robot coordination helpers
- Additional sensor types (thermal, radar)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://github.com/anthropics/mcp) by Anthropic
- [ROS2](https://docs.ros.org/en/humble/) by Open Robotics
- [Gazebo](https://gazebosim.org/) by Open Robotics
- [TurtleBot3](https://emanual.robotis.com/docs/en/platform/turtlebot3/) by ROBOTIS

## Support

- **Issues**: [GitHub Issues](https://github.com/kvgork/gazebo-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kvgork/gazebo-mcp/discussions)
- **Documentation**: [Wiki](https://github.com/kvgork/gazebo-mcp/wiki)

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

**Built with ❤️ for the robotics and AI community**
