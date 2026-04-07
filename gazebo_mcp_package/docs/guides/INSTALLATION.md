# Installation Guide

Complete step-by-step installation guide for the Gazebo MCP Server.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Install](#quick-install)
- [Detailed Installation](#detailed-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Operating System
- **Ubuntu 22.04 LTS** (Recommended)
- **Ubuntu 24.04 LTS** (Supported)
- Other Linux distributions (may require additional setup)

### Software Requirements
- **ROS2**: Humble or Jazzy (Humble recommended)
- **Gazebo**: Harmonic or Garden
- **Python**: 3.10 or higher
- **Git**: For cloning the repository

### Hardware Requirements
- **CPU**: Quad-core processor or better
- **RAM**: 8GB minimum (16GB recommended)
- **GPU**: Recommended for Gazebo visualization
- **Disk**: 10GB free space

---

## Quick Install

For experienced users who want to get started quickly:

```bash
# 1. Install ROS2 Humble
sudo apt update
sudo apt install ros-humble-desktop

# 2. Install Gazebo Harmonic
sudo apt install gz-harmonic

# 3. Install Gazebo-ROS2 bridge
sudo apt install ros-humble-gazebo-ros-pkgs

# 4. Clone and setup
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp/ros2_gazebo_mcp

# 5. Source ROS2
source /opt/ros/humble/setup.bash

# 6. Install Python dependencies
pip install -e .

# 7. Test installation
python3 examples/01_basic_simulation.py
```

---

## Detailed Installation

### Step 1: Install ROS2 Humble

#### 1.1 Add ROS2 Repository

```bash
# Ensure universe repository is enabled
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository universe

# Add ROS2 GPG key
sudo apt update
sudo apt install curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

#### 1.2 Install ROS2 Packages

```bash
# Update package index
sudo apt update

# Install ROS2 Desktop (includes RViz, demos, tutorials)
sudo apt install ros-humble-desktop

# Install development tools (optional but recommended)
sudo apt install ros-dev-tools
```

#### 1.3 Setup Environment

Add to your `~/.bashrc`:

```bash
# ROS2 environment setup
source /opt/ros/humble/setup.bash

# Optional: Auto-source in new terminals
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

Reload your shell:

```bash
source ~/.bashrc
```

#### 1.4 Verify ROS2 Installation

```bash
# Check ROS2 version
ros2 --version
# Expected: ros2 cli version: 0.18.x

# Test with demo
ros2 run demo_nodes_cpp talker
# Should see: [INFO] [talker]: Publishing: 'Hello World: 1'
# Press Ctrl+C to stop
```

---

### Step 2: Install Gazebo Harmonic

#### 2.1 Add Gazebo Repository

```bash
# Add Gazebo GPG key
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg

# Add repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
```

#### 2.2 Install Gazebo

```bash
# Update package index
sudo apt update

# Install Gazebo Harmonic
sudo apt install gz-harmonic
```

#### 2.3 Verify Gazebo Installation

```bash
# Check Gazebo version
gz sim --version
# Expected: Gazebo Sim, version 8.x.x

# Test Gazebo (launches GUI)
gz sim
# Should open Gazebo window. Close it after verification.
```

---

### Step 3: Install Gazebo-ROS2 Bridge

```bash
# Install ros2-gazebo packages
sudo apt install ros-humble-gazebo-ros-pkgs

# Install additional useful packages
sudo apt install ros-humble-gazebo-ros2-control
sudo apt install ros-humble-ros-gz-bridge
```

---

### Step 4: Install TurtleBot3 (Optional but Recommended)

```bash
# Install TurtleBot3 packages
sudo apt install ros-humble-turtlebot3*

# Set default TurtleBot3 model
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

---

### Step 5: Clone and Setup Gazebo MCP Server

#### 5.1 Clone Repository

```bash
# Navigate to your workspace
cd ~/workspaces  # Or your preferred location

# Clone the repository
git clone https://github.com/kvgork/gazebo-mcp.git
cd gazebo-mcp/ros2_gazebo_mcp
```

#### 5.2 Install Python Dependencies

```bash
# Ensure ROS2 is sourced
source /opt/ros/humble/setup.bash

# Install in development mode
pip install -e .

# Or install specific dependencies
pip install -r requirements.txt
```

#### 5.3 Optional: Build with Colcon (Advanced)

If you want to use ROS2's build system:

```bash
# From the ros2_gazebo_mcp directory
cd ..  # Go to workspace root
colcon build
source install/setup.bash
```

---

## Verification

### Verify Complete Installation

Run the comprehensive verification script:

```bash
# From ros2_gazebo_mcp directory
./scripts/verify_installation.sh
```

Or manually verify each component:

#### 1. Verify ROS2

```bash
ros2 --version
ros2 topic list
```

#### 2. Verify Gazebo

```bash
gz sim --version
```

#### 3. Verify Python Environment

```bash
python3 -c "import sys; sys.path.insert(0, 'src'); from gazebo_mcp.tools import model_management; print('✓ Import successful')"
```

#### 4. Test Examples

```bash
# Test basic simulation (works without Gazebo)
python3 examples/01_basic_simulation.py

# Test with Gazebo running
gz sim &
python3 examples/02_turtlebot3_spawn.py
```

Expected output:
```
============================================================
Example 2: TurtleBot3 Spawn and Control
============================================================

Step 1: Spawning TurtleBot3 Burger...
✓ TurtleBot3 'my_turtlebot3' spawned
  - Position: (0.00, 0.00, 0.01)
  - Model type: turtlebot3_burger
...
```

---

## Troubleshooting

### Common Issues

#### Issue: "rclpy module not found"

**Cause**: ROS2 not sourced or not installed correctly.

**Solution**:
```bash
# Ensure ROS2 is sourced
source /opt/ros/humble/setup.bash

# Verify installation
ros2 --version

# If not installed, reinstall ROS2
sudo apt install ros-humble-desktop
```

#### Issue: "gz: command not found"

**Cause**: Gazebo not installed or not in PATH.

**Solution**:
```bash
# Install Gazebo
sudo apt install gz-harmonic

# Verify installation
which gz
gz sim --version
```

#### Issue: "Cannot import gazebo_mcp"

**Cause**: Python path not set correctly.

**Solution**:
```bash
# From ros2_gazebo_mcp directory
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

#### Issue: Examples run but show "Mode: MOCK"

**Cause**: Gazebo not running or ROS2 bridge not connected.

**Solution**:
```bash
# Start Gazebo first
gz sim &

# Wait 5 seconds for startup

# Then run examples
python3 examples/02_turtlebot3_spawn.py
```

#### Issue: "TurtleBot3 model not found"

**Cause**: TurtleBot3 models not installed.

**Solution**:
```bash
# Install TurtleBot3 packages
sudo apt install ros-humble-turtlebot3-gazebo

# Set model path
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH

# Add to ~/.bashrc for persistence
echo 'export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH' >> ~/.bashrc
```

#### Issue: Gazebo crashes or freezes

**Cause**: Insufficient resources or graphics driver issues.

**Solution**:
```bash
# Run Gazebo headless (no GUI)
gz sim -s

# Or reduce graphics quality in Gazebo settings
# View → Visualization → Reduce quality settings
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: Look in `logs/gazebo_mcp.log` for detailed error messages
2. **GitHub Issues**: Search or create an issue at https://github.com/kvgork/gazebo-mcp/issues
3. **ROS Answers**: For ROS2-specific questions: https://answers.ros.org
4. **Gazebo Forums**: For Gazebo issues: https://community.gazebosim.org

---

## Next Steps

After successful installation:

1. **Quick Start**: Read [QUICK_START.md](QUICK_START.md) for your first workflow
2. **Examples**: Try all examples in the `examples/` directory
3. **TurtleBot3 Guide**: Read [TURTLEBOT3_GUIDE.md](TURTLEBOT3_GUIDE.md) for robot-specific info
4. **API Reference**: Explore [API_REFERENCE.md](../api/API_REFERENCE.md) for all available tools

---

## Advanced Setup

### Docker Installation

For containerized deployment, see [Docker Setup](DOCKER_SETUP.md).

### Multi-Version ROS2

To support multiple ROS2 distributions:

```bash
# Install additional ROS2 versions
sudo apt install ros-jazzy-desktop

# Switch between versions
source /opt/ros/humble/setup.bash  # For Humble
source /opt/ros/jazzy/setup.bash   # For Jazzy
```

### Development Setup

For contributors and developers:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

---

## Uninstallation

To remove the Gazebo MCP Server:

```bash
# Uninstall Python package
pip uninstall gazebo-mcp

# Remove cloned repository
cd ~/workspaces
rm -rf gazebo-mcp

# Optional: Remove ROS2 and Gazebo
sudo apt remove ros-humble-* gz-harmonic
sudo apt autoremove
```

---

**Installation complete!** 🎉

Continue to [QUICK_START.md](QUICK_START.md) to start using the Gazebo MCP Server.
