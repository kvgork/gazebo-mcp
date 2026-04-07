# Manual Demo Setup Guide

Step-by-step instructions to run demos manually from separate terminals.

## Prerequisites Check

First, verify you have everything installed:

```bash
# Check ROS2
ros2 --version

# Check Gazebo (try both commands)
gz sim --version
# OR
ign gazebo --version

# Check ros_gz_bridge
ros2 pkg list | grep ros_gz_bridge
```

If anything is missing, see [Installation](#installation) section below.

---

## Hello World Demo - Manual Setup

### Step 1: Terminal 1 - Start Gazebo

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# Start Gazebo with empty world
gz sim -r /usr/share/gz/gz-sim8/worlds/empty.sdf
```

**Alternative paths to try if above doesn't work:**
```bash
# Try Garden
gz sim -r /usr/share/gz/worlds/empty.sdf

# Try Fortress
ign gazebo -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf

# Or use a minimal inline world
gz sim -r -s
```

**What to expect:**
- Gazebo window opens (or runs headless with `-s`)
- Status messages in terminal
- No errors

**Leave this terminal running!**

---

### Step 2: Terminal 2 - Start ros_gz_bridge

Open a **new terminal**:

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# Start the bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
```

**Important:**
- Make sure world name matches! If Gazebo loaded a different world name, update `/world/empty/` to match
- To find the world name, look in Gazebo terminal output or in the .sdf file

**What to expect:**
- Bridge starts and shows service mappings
- No errors
- Terminal stays running with periodic output

**Wait 5 seconds** for bridge to fully initialize before proceeding!

**Leave this terminal running!**

---

### Step 3: Terminal 3 - Verify Services (Optional)

Open a **new terminal** to verify everything is working:

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# List services - should see /world/empty/... services
ros2 service list | grep /world/

# Expected output:
# /world/empty/control
# /world/empty/create
# /world/empty/remove
# /world/empty/set_pose
```

**Test a service call:**
```bash
# Test pause/unpause
ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# Should return:
# response:
#   ros_gz_interfaces.srv.ControlWorld_Response(success=True)
```

If this works, you're ready to run the demo!

---

### Step 4: Terminal 4 - Run Hello World Demo

Open a **new terminal**:

```bash
# Navigate to demos
cd <path_to_gazebo_mcp_package>/demos

# Source ROS2
source /opt/ros/humble/setup.bash

# Run with system Python 3.10
/usr/bin/python3 01_hello_world/hello_world_demo.py
```

**What to expect:**
```
======================================================================
  Demo Configuration
======================================================================
Demo Name:     Hello World
Description:   Simple demonstration of basic Gazebo MCP operations
Gazebo World:  empty
Timeout:       30.0s
Models:        1
...
======================================================================

======================================================================
  Hello World Demo
======================================================================
Demonstrates basic Gazebo MCP operations: spawn, move, delete

[Step 1/5] Validating environment...
  ✅ Validate environment (completed in 0.15s)

[Step 2/5] Initializing ROS2 and adapter...
  ✅ Initialize ROS2 and adapter (completed in 1.23s)

[Step 3/5] Spawning box model...
  ✅ Spawn box model (completed in 2.45s)

[Step 4/5] Moving box to new position...
  ✅ Move box to new position (completed in 1.87s)

[Step 5/5] Deleting box model...
  ✅ Delete box model (completed in 1.34s)

======================================================================
  Demo Summary
======================================================================
Total Duration:    7.04s
Steps Completed:   5/5 ✅
Steps Failed:      0/5 ❌

🎉 Demo completed successfully!
======================================================================
```

**In Gazebo window** (if visible):
- You'll see a green box appear
- Box moves to a new position
- Box disappears

---

## Obstacle Course Demo - Manual Setup

### Step 1: Use Automated Setup Script

The Obstacle Course has its own setup script that starts both Gazebo and bridge:

```bash
cd <path_to_gazebo_mcp_package>/demos/02_obstacle_course
./setup.sh
```

This script will:
1. Check dependencies
2. Start Gazebo with obstacle course world
3. Start ros_gz_bridge with correct services
4. Verify everything is ready

**Wait for the message:**
```
════════════════════════════════════════════════════════════════
  Setup Complete!
════════════════════════════════════════════════════════════════
```

**Leave this terminal running!**

---

### Step 2: Run Obstacle Course Demo

Open a **new terminal**:

```bash
cd <path_to_gazebo_mcp_package>/demos/02_obstacle_course

# Source ROS2
source /opt/ros/humble/setup.bash

# Run demo
/usr/bin/python3 obstacle_course_demo.py
```

**What to expect:**
- 10 steps execute
- Robot, obstacles, and target spawn
- Robot navigates through waypoints
- ~25 seconds total duration

---

## Troubleshooting

### Issue: "gz: command not found"

**Try these in order:**

1. **Check if Ignition Gazebo is installed:**
```bash
ign gazebo --version
```
If this works, use `ign gazebo` instead of `gz sim`.

2. **Install Gazebo:**
```bash
# For Garden
sudo apt install gz-garden

# For Fortress (older)
sudo apt install ignition-gazebo6

# For Harmonic (newer)
sudo apt install gz-harmonic
```

3. **Find Gazebo worlds:**
```bash
# Find world files
find /usr/share -name "empty.sdf" 2>/dev/null

# Common locations:
# /usr/share/gz/gz-sim8/worlds/empty.sdf (Garden/Harmonic)
# /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf (Fortress)
```

---

### Issue: "Service not available" or timeouts

**Solutions:**

1. **Wait longer after starting bridge** (10 seconds instead of 5)

2. **Check if services exist:**
```bash
ros2 service list | grep /world/
```

3. **Verify Gazebo world name:**
```bash
# In Gazebo terminal, look for output like:
# [Msg] Loading world [empty]
```
Use this name in bridge command.

4. **Restart bridge with correct world name:**
```bash
# If world is named "default" instead of "empty":
ros2 run ros_gz_bridge parameter_bridge \
  "/world/default/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/default/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/default/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/default/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

---

### Issue: "ModuleNotFoundError: rclpy"

**Cause:** Using anaconda Python instead of system Python

**Solution:** Always use `/usr/bin/python3`:
```bash
/usr/bin/python3 hello_world_demo.py
```

NOT:
```bash
python3 hello_world_demo.py  # ❌ Uses anaconda
```

---

### Issue: Bridge shows errors

**Check bridge logs:**
```bash
# If using setup.sh
cat /tmp/bridge_test.log

# Or for obstacle course
cat /tmp/obstacle_course_bridge.log
```

**Common fixes:**
- Ensure Gazebo is fully started before bridge
- Verify world name matches in Gazebo and bridge
- Check ROS2 domain ID matches (usually not needed)

---

## Quick Reference

### Start Gazebo (Terminal 1)
```bash
source /opt/ros/humble/setup.bash
gz sim -r /usr/share/gz/gz-sim8/worlds/empty.sdf
```

### Start Bridge (Terminal 2)
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

### Run Demo (Terminal 3)
```bash
cd ros2_gazebo_mcp/demos
source /opt/ros/humble/setup.bash
/usr/bin/python3 01_hello_world/hello_world_demo.py
```

---

## Installation

If you're missing components:

### Install ROS2 Humble
```bash
# Add ROS2 repository
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository universe

# Add ROS2 key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2
sudo apt update
sudo apt install ros-humble-ros-base
```

### Install Gazebo
```bash
# Install Gazebo Garden (recommended)
sudo apt install gz-garden

# OR Fortress (older but stable)
sudo apt install ignition-gazebo6
```

### Install ros_gz packages
```bash
sudo apt install \
  ros-humble-ros-gz-bridge \
  ros-humble-ros-gz-interfaces
```

### Verify Installation
```bash
source /opt/ros/humble/setup.bash
ros2 --version
gz sim --version
ros2 pkg list | grep ros_gz_bridge
```

---

## Terminal Summary

You need **3-4 terminals** running simultaneously:

| Terminal | Purpose | Command | Keep Running? |
|----------|---------|---------|---------------|
| 1 | Gazebo | `gz sim -r /path/to/empty.sdf` | ✅ Yes |
| 2 | Bridge | `ros2 run ros_gz_bridge parameter_bridge ...` | ✅ Yes |
| 3 | Verify (optional) | `ros2 service list` | ❌ No (one-time) |
| 4 | Demo | `/usr/bin/python3 hello_world_demo.py` | ❌ No (runs once) |

---

## Tips

1. **Always source ROS2 first** in each new terminal:
   ```bash
   source /opt/ros/humble/setup.bash
   ```

2. **Use system Python**, not anaconda:
   ```bash
   /usr/bin/python3 script.py
   ```

3. **Wait for bridge warmup** (5-10 seconds) before running demo

4. **Check world names match** between Gazebo and bridge

5. **Keep terminals organized** - label them or use tmux/screen

---

Good luck! If you encounter issues, check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.
