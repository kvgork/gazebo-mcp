# Gazebo MCP Server - Usage Examples

This directory contains practical examples demonstrating how to use the Gazebo MCP server for simulation control, robot testing, and sensor data access.

## Quick Start

All examples work **without** ROS2 or Gazebo installed. They will use mock data to demonstrate the MCP server functionality. For real simulation control, follow the [Prerequisites](#prerequisites) section below.

### Run Examples

```bash
# Navigate to examples directory
cd examples/

# Run any example (works without Gazebo)
python 01_basic_connection.py
python 02_spawn_and_control.py
python 03_sensor_streaming.py
python 04_simulation_control.py
python 05_complete_workflow.py
```

All examples include:
- ✅ Detailed console output with progress indicators
- ✅ Educational comments explaining each step
- ✅ Graceful fallback to mock data when Gazebo unavailable
- ✅ Clear indication of mock vs. real mode
- ✅ Token efficiency demonstrations

---

## Example Overview

### 01. Basic Connection (`01_basic_connection.py`)

**Complexity**: Beginner
**Duration**: ~30 seconds
**Lines**: ~220 lines

**What it demonstrates:**
- Creating an MCP server instance
- Listing all 17 available tools
- Categorizing tools by function
- Getting simulation status
- Listing models with different response formats
- Token efficiency comparison (summary vs. filtered)

**Key Concepts:**
- MCP server initialization
- Tool discovery and categorization
- Progressive disclosure pattern
- ResultFilter for token efficiency

**Output Highlights:**
```
Available tools: 17
  Model Management (4 tools)
  Sensor Tools (3 tools)
  World Tools (4 tools)
  Simulation Control (6 tools)

Token savings: ~95% with summary format
  Summary format: 500 tokens
  Filtered format: 50,000+ tokens
```

**When to use:**
- Learning MCP server basics
- Exploring available functionality
- Understanding token efficiency
- Testing server setup

---

### 02. Spawn and Control (`02_spawn_and_control.py`)

**Complexity**: Intermediate
**Duration**: ~45 seconds
**Lines**: ~280 lines

**What it demonstrates:**
- Creating SDF model definitions
- Spawning models at specific positions
- Querying model state (pose, velocity)
- Listing all models
- Deleting models from simulation
- Model lifecycle management

**Key Concepts:**
- SDF/URDF model creation
- Model spawning workflow
- State queries
- Cleanup procedures

**Output Highlights:**
```
✓ Box spawned successfully!
  Model name: red_box
  Position: (2.00, 1.00, 0.50)

✓ Got model state
  Position: x: 2.000, y: 1.000, z: 0.500
  Orientation: roll: 0.000, pitch: 0.000, yaw: 0.000
  Linear Velocity: vx: 0.000 m/s

✓ Model deleted successfully!
```

**When to use:**
- Testing model spawning
- Creating custom models
- Managing model lifecycle
- Verifying spawning behavior

---

### 03. Sensor Streaming (`03_sensor_streaming.py`)

**Complexity**: Intermediate
**Duration**: ~60 seconds
**Lines**: ~340 lines

**What it demonstrates:**
- Listing all available sensors
- Filtering sensors by type (camera, lidar, IMU, GPS)
- Getting sensor data readings
- Subscribing to sensor streams
- Processing different sensor types
- Handling sensor data formats

**Key Concepts:**
- Sensor discovery
- Type-specific data formats
- Streaming vs. one-time queries
- Data processing patterns

**Supported Sensor Types:**
- Vision: camera, depth_camera, rgbd_camera
- Range: lidar, ray (laser), sonar
- Motion: imu, gps, altimeter, magnetometer
- Contact: contact, force_torque

**Output Highlights:**
```
✓ Found 8 sensors
  Sensors by type:
    • camera: 2
    • lidar: 1
    • imu: 1

✓ Got camera data
  Width: 640 px
  Height: 480 px
  Encoding: rgb8

✓ Got lidar data
  Num Ranges: 360
  Min Distance: 0.12 m
  Max Distance: 9.87 m
```

**When to use:**
- Working with robot sensors
- Testing sensor configurations
- Validating sensor data
- Developing sensor processing

---

### 04. Simulation Control (`04_simulation_control.py`)

**Complexity**: Intermediate
**Duration**: ~45 seconds
**Lines**: ~320 lines

**What it demonstrates:**
- Getting simulation status
- Pausing and unpausing simulation
- Resetting simulation to initial state
- Querying simulation time and performance
- Setting simulation speed (faster/slower than real-time)
- Getting world properties (physics, scene)

**Key Concepts:**
- Simulation lifecycle control
- Time management
- Speed control for testing
- Performance monitoring

**Output Highlights:**
```
Simulation State:
  Running: True
  Paused: False
  Simulation Time: 45.23 s
  Real Time: 22.61 s
  Real-time Factor: 2.00x

✓ Paused
✓ Unpaused
✓ Reset (time: 45.23s → 0.00s)

Physics Properties:
  Gravity: -9.81 m/s² (z-axis)
  Update Rate: 1000 Hz
```

**When to use:**
- Automated testing workflows
- Debugging simulations
- Performance testing
- Batch simulation runs

---

### 05. Complete Workflow (`05_complete_workflow.py`)

**Complexity**: Advanced
**Duration**: ~90 seconds
**Lines**: ~480 lines

**What it demonstrates:**
- Complete end-to-end robot testing workflow
- 8 phases from initialization to cleanup
- Real-world testing scenario
- Integration of all previous examples
- Best practices for automated testing

**Workflow Phases:**
1. **Initialization**: Create server, check status
2. **Environment Setup**: Verify world properties
3. **Robot Deployment**: Spawn robot with sensors
4. **Sensor Verification**: Discover and validate sensors
5. **Simulation Execution**: Run for specified time
6. **Data Collection**: Query all sensor data
7. **State Verification**: Check final robot state
8. **Cleanup**: Pause, delete, verify

**Output Highlights:**
```
Phase 1: Initialization
  ✓ MCP server created
  ℹ Gazebo connected: False
  ℹ Running in MOCK mode

Phase 3: Robot Deployment
  ✓ Robot spawned successfully
  ℹ Position: (0.00, 0.00, 0.50)

Phase 4: Sensor Verification
  ✓ Found 2 sensors on robot
    ℹ imu_sensor (imu)
    ℹ lidar (ray)

Phase 6: Data Collection
  ✓ Collected data from 2/2 sensors
    ✓ imu_sensor: ✓ Data received
    ✓ lidar: ✓ Data received

Phase 8: Cleanup
  ✓ Simulation paused
  ✓ Robot deleted
  ✓ Cleanup complete
```

**When to use:**
- Production testing workflows
- Integration testing
- CI/CD pipelines
- Learning complete workflows

---

## Prerequisites

### For Mock Mode (No Installation Required)

All examples work without ROS2 or Gazebo. They will return mock data and clearly indicate they're running in mock mode.

**Perfect for:**
- Learning the MCP API
- Understanding tool functionality
- Developing MCP clients
- Testing without simulation overhead

### For Real Simulation (Optional)

To connect to actual Gazebo simulations:

#### 1. Install ROS2 Humble or Jazzy

**Ubuntu 22.04 (Recommended):**
```bash
# Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop
sudo apt install ros-humble-gazebo-ros-pkgs

# Source ROS2
source /opt/ros/humble/setup.bash
```

#### 2. Install Project Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Build the project (if using colcon)
cd /path/to/ros2_gazebo_mcp
colcon build
source install/setup.bash
```

#### 3. Start Gazebo

**Option A: Empty World**
```bash
ros2 launch gazebo_ros gazebo.launch.py
```

**Option B: With TurtleBot3**
```bash
# Install TurtleBot3 packages
sudo apt install ros-humble-turtlebot3*

# Set model
export TURTLEBOT3_MODEL=burger

# Launch
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

#### 4. Verify Connection

```bash
# Check ROS2 topics
ros2 topic list

# Check Gazebo services
ros2 service list | grep gazebo

# Should see services like:
#   /gazebo/spawn_entity
#   /gazebo/delete_entity
#   /gazebo/pause_physics
```

#### 5. Run Examples with Real Gazebo

```bash
# Terminal 1: Start Gazebo (if not already running)
ros2 launch gazebo_ros gazebo.launch.py

# Terminal 2: Run examples
cd examples/
python 01_basic_connection.py
```

The examples will automatically detect Gazebo and use real data instead of mock data.

---

## Learning Path

### Beginner Track

1. **Start here**: `01_basic_connection.py`
   - Understand MCP server basics
   - Learn tool discovery
   - See token efficiency in action

2. **Model basics**: `02_spawn_and_control.py`
   - Create simple models
   - Spawn and delete
   - Query state

3. **Explore sensors**: `03_sensor_streaming.py`
   - Discover sensors
   - Get sensor data
   - Understand sensor types

### Intermediate Track

4. **Control simulation**: `04_simulation_control.py`
   - Pause/unpause
   - Reset simulation
   - Adjust speed
   - Query time

5. **Complete workflow**: `05_complete_workflow.py`
   - Full testing scenario
   - Best practices
   - Production patterns

### Advanced Topics

After completing the examples, explore:

- **Custom robots**: Modify examples to use your robot URDF/SDF
- **Complex scenarios**: Create multi-robot simulations
- **Automated testing**: Integrate with pytest
- **CI/CD**: Run examples in GitHub Actions
- **Performance testing**: Use speed control for batch runs

---

## Tips and Best Practices

### Token Efficiency

Always use `response_format="summary"` when you don't need full details:

```python
# ❌ Inefficient (50,000+ tokens for 1000 models)
result = server.call_tool("gazebo_list_models", {
    "response_format": "filtered"
})

# ✅ Efficient (~500 tokens)
result = server.call_tool("gazebo_list_models", {
    "response_format": "summary"
})
```

### Error Handling

Check the `success` field in responses:

```python
content = json.loads(result["content"][0]["text"])
if content["success"]:
    data = content["data"]
    # Process data
else:
    print(f"Error: {content['error']}")
    # Check suggestions
    for suggestion in content.get("suggestions", []):
        print(f"  - {suggestion}")
```

### Resource Cleanup

Always clean up spawned models:

```python
# Spawn model
server.call_tool("gazebo_spawn_model", {...})

try:
    # Your testing code
    pass
finally:
    # Always delete, even on error
    server.call_tool("gazebo_delete_model", {"model_name": "test_model"})
```

### Simulation Timing

Pause simulation for inspection:

```python
# Pause
server.call_tool("gazebo_pause_simulation", {})

# Inspect state
state = server.call_tool("gazebo_get_model_state", {"model_name": "robot"})

# Resume
server.call_tool("gazebo_unpause_simulation", {})
```

---

## Common Issues

### "Gazebo not connected" Message

**This is normal!** Examples work in mock mode without Gazebo.

**To use real Gazebo:**
1. Start Gazebo: `ros2 launch gazebo_ros gazebo.launch.py`
2. Verify: `ros2 service list | grep gazebo`
3. Re-run example

### Import Errors

```python
ModuleNotFoundError: No module named 'mcp.server.server'
```

**Solution:**
```bash
# Ensure you're in the project root
cd /path/to/ros2_gazebo_mcp

# Add to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/src

# Or run from examples/ directory (examples handle this automatically)
cd examples/
python 01_basic_connection.py
```

### ROS2 Not Sourced

```bash
# Source ROS2 before running
source /opt/ros/humble/setup.bash
source install/setup.bash  # if using colcon
```

---

## Example Output Comparison

### Mock Mode (No Gazebo)

```
ℹ Note: Gazebo not connected
  The server is working in MOCK mode
  To connect to real Gazebo:
    1. Source ROS2: source /opt/ros/humble/setup.bash
    2. Start Gazebo: ros2 launch gazebo_ros gazebo.launch.py
    3. Re-run this script
```

### Real Gazebo Mode

```
✓ Gazebo connected: True
✓ Simulation running: True
✓ Found 15 models in simulation
✓ Real sensor data collected
```

---

## Next Steps

After completing these examples:

1. **Explore the MCP server code**:
   - `mcp/server/server.py` - Main server implementation
   - `mcp/server/adapters/` - Tool adapters
   - `src/gazebo_mcp/tools/` - Core tool implementations

2. **Read the documentation**:
   - `mcp/README.md` - Complete MCP server guide
   - `docs/ARCHITECTURE.md` - System architecture
   - `docs/PHASE4_PLAN.md` - Advanced features roadmap

3. **Build your own applications**:
   - Integrate MCP server with your robot
   - Create custom testing workflows
   - Develop automation scripts

4. **Contribute**:
   - Report issues
   - Suggest improvements
   - Add new examples

---

## Additional Resources

- **[Main README](../README.md)** - Project overview
- **[MCP Server Guide](../mcp/README.md)** - Complete MCP documentation
- **[Architecture](../docs/ARCHITECTURE.md)** - System design
- **[Testing Guide](../tests/README.md)** - Running tests
- **[Phase 4 Plan](../docs/PHASE4_PLAN.md)** - Future enhancements

---

## Questions or Issues?

- Check the troubleshooting section in `mcp/README.md`
- Review test documentation in `tests/README.md`
- Examine working code in these examples
- Consult architecture documentation

---

**Happy simulating! 🤖**

All examples are designed to be educational, demonstrating real-world patterns and best practices for working with the Gazebo MCP server.
