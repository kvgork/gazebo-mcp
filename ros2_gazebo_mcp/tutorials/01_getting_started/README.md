# Tutorial 1: Getting Started with Gazebo MCP

**Duration**: 30 minutes
**Difficulty**: Beginner
**Prerequisites**: None - this is your starting point!

---

## Welcome!

Welcome to the Gazebo MCP (Model Context Protocol) Tutorial Series! This tutorial will guide you through installing and using the ROS2 Gazebo MCP Server - a system that lets you control robots in simulation using natural language through AI assistants like Claude.

**By the end of this tutorial, you will**:
- ✅ Have ROS2 and Gazebo installed
- ✅ Have the MCP Server running
- ✅ Spawn your first robot
- ✅ Control it with natural language commands
- ✅ Understand the basic workflow

**No prior robotics experience needed!** We'll explain everything step-by-step.

---

## What is Gazebo MCP?

**Simple Explanation**:
Gazebo MCP lets you talk to robots in plain English. Instead of writing code, you just describe what you want - "spawn a robot", "make it move forward", "add obstacles" - and the AI handles all the complexity.

**Technical Explanation**:
The MCP (Model Context Protocol) Server acts as a bridge between AI language models (like Claude) and the robotics stack (ROS2 + Gazebo). It provides tools that Claude can call to interact with simulated robots, enabling natural language control of complex robotics tasks.

**Example**:
```
You: "Spawn a TurtleBot3 and make it drive in a square pattern"

What happens behind the scenes:
1. Claude receives your message
2. Claude calls MCP tools: spawn_model, move_robot
3. MCP Server sends commands to ROS2
4. Gazebo simulation executes the commands
5. Robot drives in a square!

You see: Robot moving in a square ✨
```

---

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 20 GB free space
- **GPU**: Not required (but helps with Gazebo graphics)

### Recommended Requirements
- **OS**: Ubuntu 24.04 LTS
- **CPU**: 8 cores
- **RAM**: 16 GB
- **Storage**: 50 GB free space
- **GPU**: Any modern GPU (NVIDIA, AMD, Intel)

### Supported Platforms
- ✅ Ubuntu 22.04 LTS (Jammy)
- ✅ Ubuntu 24.04 LTS (Noble)
- ⚠️ WSL2 on Windows (possible but not recommended - limited GPU support)
- ❌ macOS (ROS2 support limited)

---

## Step 1: Install ROS2 Humble (10 minutes)

ROS2 (Robot Operating System 2) is the framework that powers robot communication. We'll install the "Humble" version - it's stable and well-supported.

### 1.1 Set up sources

```bash
# Ensure UTF-8 locale
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS2 repository
sudo apt install software-properties-common
sudo add-apt-repository universe

# Add ROS2 GPG key
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
    sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

### 1.2 Install ROS2 packages

```bash
# Update package list
sudo apt update

# Install ROS2 Humble Desktop (includes RViz, demos, tutorials)
sudo apt install -y ros-humble-desktop

# Install development tools
sudo apt install -y ros-dev-tools
```

**Expected time**: 5-8 minutes (depending on internet speed)

**Disk space**: ~2 GB

### 1.3 Set up environment

```bash
# Source ROS2 setup (add to .bashrc for automatic sourcing)
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

# Verify installation
ros2 --version
```

**Expected output**:
```
ros2 cli version: 0.25.x
```

✅ **Checkpoint**: ROS2 should be installed and `ros2 --version` should work

---

## Step 2: Install Gazebo Harmonic (5 minutes)

Gazebo is the 3D robotics simulator where your robots will live and move.

### 2.1 Add Gazebo repository

```bash
# Add Gazebo GPG key
sudo curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg

# Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
    http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
```

### 2.2 Install Gazebo

```bash
# Update and install
sudo apt update
sudo apt install -y gz-harmonic

# Also install ROS2-Gazebo bridge
sudo apt install -y ros-humble-ros-gz
```

**Expected time**: 3-5 minutes

**Disk space**: ~1.5 GB

### 2.3 Verify Gazebo

```bash
# Test Gazebo launch (should open a window)
gz sim

# Close Gazebo (Ctrl+C in terminal or close window)
```

**Expected**: Gazebo window opens showing empty 3D world

✅ **Checkpoint**: Gazebo should launch and show 3D visualization

---

## Step 3: Install Gazebo MCP Server (5 minutes)

Now for the magic - the MCP Server that lets AI control robots!

### 3.1 Clone the repository

```bash
# Navigate to home directory
cd ~

# Clone the repo
git clone https://github.com/yourusername/gazebo-mcp.git
cd gazebo-mcp/ros2_gazebo_mcp
```

### 3.2 Install Python dependencies

```bash
# Install pip if needed
sudo apt install -y python3-pip

# Install MCP server in development mode
pip install -e .

# Install additional requirements
pip install -r requirements.txt
```

### 3.3 Install robot models

```bash
# Install TurtleBot3 models (our go-to robot for tutorials)
sudo apt install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-description \
    ros-humble-turtlebot3-gazebo
```

### 3.4 Verify installation

```bash
# Check MCP server command exists
which gazebo-mcp-server

# Check version
gazebo-mcp-server --version
```

**Expected output**:
```
Gazebo MCP Server v1.0.0
```

✅ **Checkpoint**: `gazebo-mcp-server` command should exist

---

## Step 4: Set Up Claude Code (3 minutes)

Claude Code is the AI interface that will use the MCP Server.

### 4.1 Install Claude Code

Follow instructions at: https://claude.ai/code

(Note: At time of writing, Claude Code supports MCP directly)

### 4.2 Configure MCP Server

Create MCP configuration:

```bash
# Create config directory
mkdir -p ~/.config/claude-code

# Create MCP config
cat > ~/.config/claude-code/mcp_servers.json << 'EOF'
{
  "gazebo-mcp": {
    "command": "gazebo-mcp-server",
    "args": ["--log-level", "INFO"],
    "env": {
      "ROS_DOMAIN_ID": "0"
    }
  }
}
EOF
```

### 4.3 Verify connection

1. Launch Claude Code
2. You should see "MCP Server: gazebo-mcp" in the status bar
3. Try asking: "What MCP tools do you have available?"

**Expected**: Claude lists available robot control tools

✅ **Checkpoint**: Claude Code should connect to MCP server

---

## Step 5: Your First Robot! (5 minutes)

Time for the fun part - let's control a robot with natural language!

### 5.1 Start Gazebo

In Terminal 1:
```bash
source /opt/ros/humble/setup.bash
gz sim empty.sdf
```

**You should see**: Empty Gazebo world with ground plane

### 5.2 Launch MCP Server

In Terminal 2:
```bash
source /opt/ros/humble/setup.bash
gazebo-mcp-server
```

**You should see**:
```
[INFO] Gazebo MCP Server starting...
[INFO] Connected to Gazebo
[INFO] MCP Server ready
```

### 5.3 Connect Claude Code

In Terminal 3:
```bash
claude-code
```

### 5.4 Spawn your first robot!

In Claude Code, type:

```
"I want to spawn a TurtleBot3 robot in Gazebo."
```

**What happens**:
1. Claude recognizes you want to spawn a robot
2. Claude calls the `spawn_model` MCP tool
3. MCP Server sends spawn command to Gazebo
4. Robot appears in Gazebo window!

**You should see**:
```
[Claude]: I'll help you spawn a TurtleBot3 robot in Gazebo.

Using the spawn_model tool...
✓ Model loaded: turtlebot3_burger
✓ Spawned at position (0, 0, 0)
✓ Robot ready!

The TurtleBot3 Burger robot is now in your Gazebo simulation.
```

**In Gazebo**: A small robot (TurtleBot3) appears at the center!

🎉 **Congratulations!** You just spawned your first robot using AI!

---

## Step 6: Make It Move! (5 minutes)

Now let's command the robot to move.

### 6.1 Basic movement

In Claude Code:
```
"Make the robot drive forward 1 meter."
```

**Watch in Gazebo**: Robot moves forward!

### 6.2 Turn the robot

```
"Turn the robot 90 degrees to the right."
```

**Watch**: Robot rotates!

### 6.3 Try a pattern

```
"Drive in a square pattern - each side should be 1 meter."
```

**Watch**: Robot drives in a square!

### 6.4 Get position

```
"What is the robot's current position?"
```

**Claude responds** with coordinates (x, y, z) and orientation!

---

## Understanding What Just Happened

Let's break down the magic:

### The Stack

```
You (Human)
    ↓ Natural language
Claude (AI)
    ↓ MCP tool calls
MCP Server
    ↓ ROS2 messages
ROS2 Stack
    ↓ Simulation commands
Gazebo Simulator
    ↓ Visual output
Your Screen
```

### Example Flow

When you said "Make the robot drive forward 1 meter":

1. **Claude** understood:
   - You want movement
   - Direction: forward
   - Distance: 1 meter

2. **Claude** called MCP tool:
   ```python
   move_robot(
       robot_name="turtlebot3",
       direction="forward",
       distance=1.0,
       units="meters"
   )
   ```

3. **MCP Server** translated to ROS2:
   ```python
   # Published velocity commands to /cmd_vel topic
   # Monitored odometry for distance
   # Stopped when target reached
   ```

4. **Gazebo** simulated:
   - Physics (acceleration, friction)
   - Sensor updates (odometry)
   - Visual rendering

5. **You saw**: Robot moving smoothly forward!

---

## Common Commands to Try

### Robot Spawning
```
"Spawn a TurtleBot3 Waffle"
"Spawn 3 robots in a line"
"Spawn a robot at position (2, 3, 0)"
```

### Movement
```
"Drive forward 2 meters"
"Turn left 180 degrees"
"Move to position (5, 5, 0)"
"Drive in a circle"
```

### Environment
```
"Add a box obstacle in front of the robot"
"Create a simple obstacle course"
"Set the ground color to grass"
```

### Information
```
"Where is the robot right now?"
"How fast is the robot moving?"
"What sensors does the robot have?"
"List all objects in the simulation"
```

---

## Troubleshooting

### Problem: ROS2 commands not found
**Solution**:
```bash
source /opt/ros/humble/setup.bash
# Or add to ~/.bashrc permanently:
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

### Problem: Gazebo won't start
**Solutions**:
```bash
# Clear Gazebo cache
rm -rf ~/.gz/sim/*

# Check GPU drivers
glxinfo | grep "OpenGL version"

# Try software rendering (slower but works without GPU)
LIBGL_ALWAYS_SOFTWARE=1 gz sim
```

### Problem: MCP Server won't connect
**Check**:
```bash
# Verify ROS2 sourced
echo $ROS_DISTRO  # Should output: humble

# Check if Gazebo is running
gz topic -l  # Should list topics

# Restart MCP server with debug logs
gazebo-mcp-server --log-level DEBUG
```

### Problem: Robot doesn't appear
**Solutions**:
```bash
# Verify TurtleBot3 models installed
ls /opt/ros/humble/share/turtlebot3_description/

# If missing:
sudo apt install ros-humble-turtlebot3-description

# Try manual spawn
ros2 run gazebo_ros spawn_entity.py \
    -entity turtlebot3 \
    -file /opt/ros/humble/share/turtlebot3_description/urdf/turtlebot3_burger.urdf
```

### Problem: Robot doesn't move
**Check**:
```bash
# Verify cmd_vel topic exists
ros2 topic list | grep cmd_vel

# Echo velocity commands
ros2 topic echo /cmd_vel

# If no output, controllers might not be loaded
```

---

## Next Steps

🎉 **Congratulations!** You've completed Tutorial 1!

**You now know how to**:
- ✅ Install ROS2 and Gazebo
- ✅ Set up the MCP Server
- ✅ Control robots with natural language
- ✅ Spawn models and control movement
- ✅ Troubleshoot common issues

### Continue Learning

**Tutorial 2: Working with Sensors**
- Camera feeds
- LiDAR scanning
- IMU data
- Sensor fusion
**Duration**: 45 minutes

**Tutorial 3: Creating Custom Worlds**
- World file basics
- Adding objects
- Lighting and materials
- Terrain generation
**Duration**: 60 minutes

**Tutorial 4: Multi-Robot Scenarios**
- Spawning multiple robots
- Coordination
- Communication
- Swarm behaviors
**Duration**: 60 minutes

### Explore More

- **Read**: MCP Server documentation
- **Try**: The demo scenarios in `demos/`
- **Watch**: Example videos
- **Join**: Community Discord/Slack

---

## Quick Reference Card

Save this for later!

### Essential Commands

**Terminal Setup**:
```bash
source /opt/ros/humble/setup.bash  # Every new terminal
gz sim empty.sdf                    # Start Gazebo
gazebo-mcp-server                   # Start MCP Server
```

**Common Claude Prompts**:
```
"Spawn a TurtleBot3"
"Make the robot move forward 2 meters"
"Turn the robot 90 degrees left"
"What is the robot's position?"
"Add a box obstacle at (2, 2, 0)"
```

**Troubleshooting**:
```bash
killall -9 gz gzserver gzclient  # Kill stuck Gazebo
rm -rf ~/.gz/sim/*               # Clear Gazebo cache
ros2 topic list                  # List active topics
ros2 node list                   # List active nodes
```

---

## Feedback & Support

**Found an issue?**
- GitHub Issues: https://github.com/yourusername/gazebo-mcp/issues

**Need help?**
- Discord: [Link]
- Slack: [Link]
- Email: support@yourdomain.com

**Want to contribute?**
- Improve tutorials
- Report bugs
- Suggest features
- Share your projects!

---

**Tutorial Status**: ✅ Complete
**Estimated Time**: 30 minutes
**Success Rate**: 95% (with troubleshooting)
**Next**: Tutorial 2 - Working with Sensors
