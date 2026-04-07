# Gazebo MCP Server - Installation Guide

Complete guide for installing and configuring the Gazebo MCP server to work with Claude Code.

## 🚀 Quick Start (Recommended)

### One-Command Installation

```bash
cd <path_to_gazebo_mcp_package>
./install_mcp_global.sh --with-ros2
```

This will:
- ✅ Install ROS2 Humble and Gazebo Harmonic
- ✅ Install all Python dependencies
- ✅ Register the MCP server globally with Claude Code
- ✅ Create wrapper scripts for easy use
- ✅ Configure environment variables

**After installation:**
1. Restart your terminal (for ROS2 environment)
2. Restart Claude Code completely
3. Type `/mcp` in Claude Code to verify
4. Start using Gazebo tools!

## 📋 Installation Options

### Option 1: Full Installation (with ROS2)

Install everything including ROS2 and Gazebo:

```bash
./install_mcp_global.sh --with-ros2
```

**Use this if:**
- You want full Gazebo simulation capabilities
- You plan to control real Gazebo simulations
- You're setting up a new system

### Option 2: MCP Only (without ROS2)

Install just the MCP server without ROS2:

```bash
./install_mcp_global.sh
```

**Use this if:**
- ROS2 is already installed
- You only want to test the MCP integration
- You want mock mode for development

### Option 3: Manual Installation

If you prefer manual control, follow the detailed steps in `MCP_SETUP_GUIDE.md`.

## 🔍 Verification

After installation, verify everything is working:

```bash
./verify_mcp_installation.sh
```

This checks:
- ✓ Python version and dependencies
- ✓ Claude CLI availability
- ✓ Project structure
- ✓ ROS2 installation
- ✓ Gazebo installation
- ✓ MCP server registration
- ✓ Configuration files
- ✓ Server startup test

**Expected output:**
```
✓ All checks passed!

Your Gazebo MCP server is properly installed and configured.
```

## 📦 What Gets Installed

### Python Packages (via pip)
- `mcp` (v1.22.0+) - Model Context Protocol SDK
- `pydantic` - Data validation
- `pyyaml` - YAML parsing
- `numpy` - Numerical operations
- `pillow` - Image processing
- `aiohttp` - Async HTTP client

### ROS2 Packages (via apt, if --with-ros2 used)
- `ros-humble-desktop` - ROS2 core
- `ros-humble-gazebo-ros-pkgs` - Gazebo integration
- `ros-humble-ros-gz-bridge` - Modern Gazebo bridge
- `ros-humble-ros-gz-interfaces` - Interface definitions
- `gz-harmonic` - Modern Gazebo simulator

### Files Created
- `~/.local/bin/gazebo-mcp-server` - Wrapper script
- `~/.bashrc` - Updated with ROS2 sourcing (if needed)
- `.mcp.json` - Project-level configuration
- MCP server registration in Claude Code settings

## 🎮 Using the MCP Server

### In Claude Code

Once installed and Claude Code is restarted:

1. **Check status:**
   ```
   /mcp
   ```

2. **List available servers:**
   ```bash
   claude mcp list
   ```

3. **Get server details:**
   ```bash
   claude mcp get gazebo
   ```

4. **Start asking Claude naturally:**
   - "List all models in the Gazebo simulation"
   - "Spawn a TurtleBot3 burger robot at position (1, 2, 0)"
   - "Get the current simulation status"
   - "Pause the simulation"

### Available Tools

Once registered, you'll have 18+ MCP tools:

#### Model Management (5 tools)
- `gazebo_list_models` - List all simulation models
- `gazebo_spawn_model` - Spawn new models
- `gazebo_delete_model` - Remove models
- `gazebo_get_model_state` - Query model state
- `gazebo_set_model_state` - Update model state

#### Sensor Tools (3 tools)
- `gazebo_list_sensors` - List available sensors
- `gazebo_get_sensor_data` - Get sensor readings
- `gazebo_subscribe_sensor_stream` - Subscribe to sensor data

#### World Control (4 tools)
- `gazebo_load_world` - Load world files
- `gazebo_save_world` - Save current world
- `gazebo_get_world_properties` - Query world settings
- `gazebo_set_world_property` - Modify world properties

#### Simulation Control (6 tools)
- `gazebo_pause_simulation` - Pause physics
- `gazebo_unpause_simulation` - Resume physics
- `gazebo_reset_simulation` - Reset simulation
- `gazebo_set_simulation_speed` - Change speed
- `gazebo_get_simulation_time` - Get time info
- `gazebo_get_simulation_status` - Complete status

## 🧪 Testing the Installation

### 1. Verify Installation

```bash
./verify_mcp_installation.sh
```

### 2. Test MCP Server Manually

```bash
~/.local/bin/gazebo-mcp-server
```

The server runs via stdio (JSON-RPC). Press Ctrl+C to stop.

### 3. Run Demo Tests

```bash
cd demos
pytest -v
```

Expected: All 14 unit tests pass.

### 4. Test with Real Gazebo

**Terminal 1: Start Gazebo**
```bash
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf
```

**Terminal 2: Start Bridge**
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

**Terminal 3: Use Claude Code**
Ask me to list models or spawn objects!

## 🗑️ Uninstallation

To remove the globally configured MCP server:

```bash
./uninstall_mcp_global.sh
```

This removes:
- MCP server registration from Claude Code
- Wrapper script (`~/.local/bin/gazebo-mcp-server`)
- Optionally: project-level `.mcp.json`

**Note:** Python packages and ROS2 are NOT removed.

## 🔧 Troubleshooting

### MCP Server Not Appearing

**Symptoms:** `/mcp` command doesn't show gazebo server

**Solutions:**
1. Verify installation: `./verify_mcp_installation.sh`
2. Check registration: `claude mcp list`
3. Restart Claude Code completely
4. Re-run installation: `./install_mcp_global.sh`

### ROS2 Import Errors

**Error:** `ModuleNotFoundError: No module named 'rclpy'`

**Solutions:**
1. Source ROS2: `source /opt/ros/humble/setup.bash`
2. Add to bashrc: `echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc`
3. Restart terminal
4. Restart Claude Code from terminal with ROS2 sourced

### Server Starts But No Data

**Symptoms:** Server runs but returns mock data

**Causes:**
- Gazebo not running
- ROS2 bridge not running
- Wrong world name

**Solutions:**
1. Start Gazebo simulation
2. Start ros_gz_bridge (see testing section)
3. Wait 3-5 seconds for bridge warmup
4. Verify services: `ros2 service list | grep /world/`

### Python Version Issues

**Error:** `Python 3.10+ not found`

**Solutions:**
```bash
# Install Python 3.10
sudo apt install python3.10

# Or use Python 3.11
sudo apt install python3.11
```

### Permission Errors

**Error:** `Permission denied` when running scripts

**Solution:**
```bash
chmod +x install_mcp_global.sh
chmod +x uninstall_mcp_global.sh
chmod +x verify_mcp_installation.sh
```

## 🎯 Configuration Scopes

The MCP server can be configured at different levels:

### Global (User-level)
- Registered via: `claude mcp add --transport stdio gazebo -- <command>`
- Available in all projects
- Default behavior of `install_mcp_global.sh`

### Project-level
- File: `.mcp.json` in project root
- Only available in this project
- Useful for version control

### System-wide (Enterprise)
- Linux: `/etc/claude-code/managed-mcp.json`
- Managed by administrators
- Read-only for users

## 📚 Additional Resources

### Documentation
- **Setup Guide:** `MCP_SETUP_GUIDE.md` - Detailed manual setup
- **Test Results:** `demos/TEST_RESULTS.md` - Validation results
- **API Reference:** `docs/API.md` - Tool documentation
- **Official MCP Docs:** https://code.claude.com/docs/en/mcp

### Example Usage
- **Demo 1:** `demos/01_hello_world/` - Basic operations
- **Demo 2:** `demos/02_obstacle_course/` - Advanced navigation
- **Examples:** `examples/` - Code samples

### Support
- **Issues:** Check `verify_mcp_installation.sh` output
- **Logs:** Check Claude Code logs
- **Community:** GitHub issues for this project

## 🚦 Quick Reference

### Installation Commands

```bash
# Full installation (recommended)
./install_mcp_global.sh --with-ros2

# MCP only
./install_mcp_global.sh

# Verify
./verify_mcp_installation.sh

# Uninstall
./uninstall_mcp_global.sh
```

### Claude Code Commands

```bash
# List MCP servers
claude mcp list

# Get server details
claude mcp get gazebo

# Remove server
claude mcp remove gazebo

# Check status in Claude Code
/mcp
```

### Manual Testing

```bash
# Test server directly
~/.local/bin/gazebo-mcp-server

# Run unit tests
cd demos && pytest -v

# Run demo
cd demos && ./run_demo.py --run 1
```

## ✨ Features

Once installed, you can:

- 🎮 **Control Gazebo simulations** through natural language
- 🤖 **Spawn and manage robots** (TurtleBot3, custom models)
- 🌍 **Create and modify worlds** on the fly
- 📡 **Access sensor data** (camera, lidar, IMU, GPS)
- ⚡ **Real-time control** of physics and objects
- 🧪 **Test scenarios** without writing code
- 📊 **Monitor simulations** and get status updates

## 🎉 You're Ready!

After running the installation script and restarting Claude Code:

1. ✅ All tools are available globally
2. ✅ Works in any project directory
3. ✅ Automatically connects to Gazebo when running
4. ✅ Falls back to mock mode when Gazebo unavailable
5. ✅ Full natural language interface

Just start asking Claude to control your robot simulations! 🤖🚀
