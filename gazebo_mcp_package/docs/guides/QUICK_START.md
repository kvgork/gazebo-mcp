# Quick Start Guide

Get up and running with the Gazebo MCP Server in 10 minutes.

## Prerequisites

Before starting, ensure you have completed the [Installation Guide](INSTALLATION.md).

You should have:
- ✅ ROS2 Humble installed
- ✅ Gazebo Harmonic installed
- ✅ Gazebo MCP Server cloned and installed
- ✅ ROS2 environment sourced: `source /opt/ros/humble/setup.bash`

---

## Your First Simulation (5 minutes)

### Step 1: Start Gazebo

Open a terminal and start Gazebo:

```bash
gz sim
```

You should see the Gazebo window open with an empty world.

**Tip**: Leave this terminal running. Open a new terminal for the next steps.

---

### Step 2: Source ROS2

In your new terminal:

```bash
source /opt/ros/humble/setup.bash
```

---

### Step 3: Navigate to Project

```bash
cd ~/workspaces/gazebo-mcp/ros2_gazebo_mcp
```

---

### Step 4: Run Your First Example

```bash
python3 examples/01_basic_simulation.py
```

**Expected Output**:
```
============================================================
Example 1: Basic Simulation Control
============================================================

Step 1: Getting simulation status...
✓ Simulation status retrieved
  - Paused: False
  - Time: 0.00
  - Mode: REAL (Connected to Gazebo)

Step 2: Listing models in simulation...
✓ Models retrieved
  - Total models: 0
  - Model names: []
...
```

✅ **Success!** The MCP server is connected to Gazebo and working.

---

## Spawn Your First Robot (5 minutes)

### Step 1: Run TurtleBot3 Example

```bash
python3 examples/02_turtlebot3_spawn.py
```

**Watch Gazebo**: You should see a TurtleBot3 robot appear in the simulation!

**Expected Output**:
```
============================================================
Example 2: TurtleBot3 Spawn and Control
============================================================

Step 1: Spawning TurtleBot3 Burger...
✓ TurtleBot3 'my_turtlebot3' spawned
  - Position: (0.00, 0.00, 0.01)
  - Model type: turtlebot3_burger
  - Mode: REAL

Step 2: Getting robot state...
✓ Robot state retrieved
  - Position: (0.00, 0.00, 0.01)
  - Orientation: (0.00, 0.00, 0.00) rad

Step 3: Moving robot to position (2.0, 1.5, 0.01)...
✓ Robot moved to new position
  - New position: (2.00, 1.50, 0.01)
...
```

**In Gazebo**: The robot should teleport to the new position!

---

## Read Sensor Data (Optional)

### Step 1: Run Sensor Example

```bash
python3 examples/03_sensor_reading.py
```

**Expected Output**:
```
============================================================
Example 3: Reading Sensor Data
============================================================

Step 1: Ensuring robot is spawned...
✓ Robot 'my_turtlebot3' ready

Step 2: Listing sensors on robot...
✓ Found 1 sensor(s)
  - scan: lidar
    Topic: /my_turtlebot3/scan

Step 3: Reading LiDAR sensor data...
✓ LiDAR data retrieved
  - Type: lidar
  - Range min: 0.12 m
  - Range max: 3.50 m
  - Number of readings: 360
  - Sample readings: [inf, inf, inf, inf, inf]
  - Min distance: 0.50 m
  - Max distance: inf
...
```

---

## Understanding the Examples

### Example 1: Basic Simulation Control

**What it does:**
- Connects to Gazebo
- Queries simulation status
- Pauses and unpauses simulation
- Gets simulation time

**Key functions used:**
- `simulation_tools.get_simulation_status()`
- `simulation_tools.pause_simulation()`
- `simulation_tools.unpause_simulation()`
- `model_management.list_models()`

---

### Example 2: TurtleBot3 Spawn and Control

**What it does:**
- Spawns a TurtleBot3 Burger robot
- Queries robot position
- Moves robot to new position
- Deletes robot

**Key functions used:**
- `model_management.spawn_model()`
- `model_management.get_model_state()`
- `model_management.set_model_state()`
- `model_management.delete_model()`

---

### Example 3: Reading Sensor Data

**What it does:**
- Lists available sensors on robot
- Reads LiDAR scan data
- Reads camera images (if available)
- Reads IMU data (if available)

**Key functions used:**
- `sensor_tools.list_sensors()`
- `sensor_tools.get_sensor_data()`

---

### Example 4: World Manipulation

**What it does:**
- Queries world properties
- Modifies gravity
- Changes simulation speed
- Saves and loads worlds

**Key functions used:**
- `world_tools.get_world_properties()`
- `world_tools.set_world_property()`
- `simulation_tools.set_simulation_speed()`
- `world_tools.save_world()`

---

## Mock Mode (No Gazebo Required)

All examples work in **mock mode** when Gazebo is not running:

```bash
# Stop Gazebo if running
pkill -9 gz

# Run examples - they still work!
python3 examples/01_basic_simulation.py
```

**Output will show:**
```
  - Mode: MOCK (Gazebo not running)
```

**Use cases for mock mode:**
- Learning the API without Gazebo
- Testing on systems without Gazebo
- CI/CD pipelines
- Quick prototyping

---

## Common Workflows

### Workflow 1: Quick Robot Test

```bash
# 1. Start Gazebo
gz sim &

# 2. Spawn robot
python3 examples/02_turtlebot3_spawn.py

# 3. Test sensors
python3 examples/03_sensor_reading.py
```

### Workflow 2: Custom Script

Create `my_script.py`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import model_management, simulation_tools

# Spawn 5 robots
for i in range(5):
    result = model_management.spawn_model(
        model_name=f"robot_{i}",
        model_type="turtlebot3_burger",
        x=i * 2.0,  # Space them out
        y=0.0,
        z=0.01
    )
    print(f"Robot {i}: {'✓' if result.success else '✗'}")

# List all models
result = model_management.list_models(response_format="summary")
if result.success:
    print(f"\nTotal robots: {len(result.data['models'])}")
```

Run it:
```bash
python3 my_script.py
```

---

## Next Steps

### Learn More

1. **TurtleBot3 Guide**: [TURTLEBOT3_GUIDE.md](TURTLEBOT3_GUIDE.md)
   - All TurtleBot3 variants
   - Sensor configurations
   - Navigation basics

2. **API Reference**: [API_REFERENCE.md](../api/API_REFERENCE.md)
   - Complete tool documentation
   - All parameters and return values
   - Advanced usage

3. **Sensor Data Formats**: [SENSOR_DATA_FORMATS.md](../api/SENSOR_DATA_FORMATS.md)
   - Camera, LiDAR, IMU, GPS formats
   - Data processing examples

### Try Advanced Features

1. **Multiple Robots**: Spawn and control robot fleets
2. **Custom Worlds**: Create obstacle courses and test environments
3. **Sensor Fusion**: Combine LiDAR, camera, and IMU data
4. **Navigation**: Integrate with ROS2 Nav2 stack

---

## Troubleshooting Quick Fixes

### "Mode: MOCK" when Gazebo is running

**Solution**:
```bash
# Ensure Gazebo is fully started (wait 10 seconds after launching)
gz sim &
sleep 10

# Then run examples
python3 examples/02_turtlebot3_spawn.py
```

### "rclpy module not found"

**Solution**:
```bash
# Source ROS2 in current terminal
source /opt/ros/humble/setup.bash

# Add to ~/.bashrc for automatic sourcing
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

### Robot doesn't appear in Gazebo

**Solution**:
```bash
# Check if model spawned successfully (look for errors in output)
# Ensure TurtleBot3 models are installed:
sudo apt install ros-humble-turtlebot3-gazebo

# Set model path
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH
```

### Examples are slow

**Solution**:
```bash
# Run Gazebo in headless mode (no GUI)
gz sim -s &

# Or reduce Gazebo graphics quality in GUI: View → Visualization
```

---

## Summary

You've learned how to:

✅ Start Gazebo and connect the MCP server
✅ Spawn and control a TurtleBot3 robot
✅ Read sensor data from robots
✅ Use mock mode for testing
✅ Write custom scripts with the MCP tools

**Time to explore:** Check out the other examples and API documentation!

---

## Getting Help

- **Documentation**: Browse `docs/` directory
- **Examples**: Study `examples/` directory
- **Issues**: https://github.com/kvgork/gazebo-mcp/issues
- **ROS Answers**: https://answers.ros.org
- **Gazebo Forums**: https://community.gazebosim.org

**Happy simulating!** 🤖
