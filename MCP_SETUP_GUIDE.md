# Gazebo MCP Server Setup for Claude Code

This guide will help you set up the Gazebo MCP server to work with Claude Code.

## ✅ What's Already Done

- [x] MCP configuration file created (`.mcp.json` in project root)
- [x] Python dependencies installed
- [x] Demo tests passing (14/14 tests)

## 📋 Prerequisites to Install

### 1. Install ROS2 Humble

```bash
# Add ROS2 repository
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository universe

# Add ROS2 GPG key
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add ROS2 repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble Desktop
sudo apt update
sudo apt install -y ros-humble-desktop

# Install Gazebo packages
sudo apt install -y ros-humble-gazebo-ros-pkgs ros-humble-ros-gz-bridge ros-humble-ros-gz-interfaces

# Install Gazebo Harmonic (Modern Gazebo)
sudo apt install -y gz-harmonic
```

### 2. Source ROS2 Environment

Add to your `~/.bashrc`:

```bash
source /opt/ros/humble/setup.bash
```

Then reload:

```bash
source ~/.bashrc
```

## 🚀 Using the MCP Server with Claude Code

### Step 1: Verify MCP Server is Detected

Since we're in the project directory where `.mcp.json` exists, Claude Code should automatically detect the Gazebo MCP server.

You can check with:

```bash
# List all MCP servers
claude mcp list
```

### Step 2: Check MCP Status in Claude Code

In your Claude Code conversation, type:

```
/mcp
```

This will show you the status of all MCP servers, including the Gazebo server.

### Step 3: Start Using Gazebo Tools

Once ROS2 is installed and a Gazebo simulation is running, you can use the MCP tools through Claude Code:

**Example queries you can ask me:**

- "List all models in the Gazebo simulation"
- "Spawn a box at position (1, 2, 0.5)"
- "Get the current state of the robot"
- "Pause the simulation"
- "List all available sensors"

## 🛠️ Available MCP Tools

Once the server is running, you'll have access to 18+ tools:

### Model Management (5 tools)
- `gazebo_list_models` - List all models in simulation
- `gazebo_spawn_model` - Spawn a new model
- `gazebo_delete_model` - Remove a model
- `gazebo_get_model_state` - Get model pose/velocity
- `gazebo_set_model_state` - Update model state

### Sensor Tools (3 tools)
- `gazebo_list_sensors` - List all sensors
- `gazebo_get_sensor_data` - Get sensor readings
- `gazebo_subscribe_sensor_stream` - Subscribe to sensor topic

### World Tools (4 tools)
- `gazebo_load_world` - Load world file
- `gazebo_save_world` - Save current world
- `gazebo_get_world_properties` - Query world settings
- `gazebo_set_world_property` - Update world properties

### Simulation Control (6 tools)
- `gazebo_pause_simulation` - Pause physics
- `gazebo_unpause_simulation` - Resume physics
- `gazebo_reset_simulation` - Reset to initial state
- `gazebo_set_simulation_speed` - Change speed multiplier
- `gazebo_get_simulation_time` - Get simulation time
- `gazebo_get_simulation_status` - Complete status check

## 🧪 Testing the Setup

### Option 1: Test with Mock Mode (No Gazebo Required)

The MCP server can run in mock mode for testing without a Gazebo simulation:

```bash
cd <path-to-ros2_gazebo_mcp>
source /opt/ros/humble/setup.bash
python3.10 -m mcp.server.server
```

It will return mock data but verify the server works.

### Option 2: Test with Actual Gazebo

**Terminal 1: Start Gazebo**
```bash
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf
```

**Terminal 2: Start ROS Bridge**
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

**Then use Claude Code**: The MCP server will automatically connect to the running simulation.

## 🐛 Troubleshooting

### MCP Server Not Showing Up

**Check 1**: Verify you're in the correct directory
```bash
cd <path-to-ros2_gazebo_mcp>
ls .mcp.json  # Should exist
```

**Check 2**: Restart Claude Code completely
```bash
# Exit Claude Code and restart
```

### ROS2 Import Errors

**Error**: `ModuleNotFoundError: No module named 'rclpy'`

**Solution**: Source ROS2 environment
```bash
source /opt/ros/humble/setup.bash
```

Make sure to restart Claude Code from a terminal that has ROS2 sourced.

### Gazebo Not Available

The MCP server will work in "mock mode" without Gazebo, returning simulated data. This is useful for:
- Testing the MCP integration
- Development without simulation
- Learning the API

To use real Gazebo, start it as shown in the testing section above.

## 📚 Additional Resources

- **Demo Files**: See `demos/` directory for working examples
- **Test Results**: See `demos/TEST_RESULTS.md` for validation
- **API Documentation**: See `docs/API.md` for tool details
- **MCP Documentation**: https://code.claude.com/docs/en/mcp

## 🎯 Quick Start Checklist

- [ ] Install ROS2 Humble
- [ ] Install Gazebo Harmonic
- [ ] Source ROS2 in `~/.bashrc`
- [ ] Restart Claude Code
- [ ] Type `/mcp` in Claude Code to verify
- [ ] Start Gazebo simulation (optional, for real testing)
- [ ] Ask me to list models or spawn objects!

## 🎉 You're Ready!

Once ROS2 is installed and Claude Code is restarted, you'll be able to control Gazebo simulations through natural language! Just ask me to perform any Gazebo operation and I'll use the MCP tools automatically.
