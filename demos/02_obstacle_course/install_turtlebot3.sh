#!/bin/bash
# Install TurtleBot3 packages and Nav2 dependencies
# Part of Demo 2: Obstacle Course with Nav2

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "  TurtleBot3 + Nav2 Installation"
echo "========================================"
echo

# Check if running as sudo
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}✗${NC} Please run this script as regular user (will prompt for sudo when needed)"
   exit 1
fi

# Check ROS2 distro
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}⚠${NC} ROS_DISTRO not set, sourcing /opt/ros/humble/setup.bash"
    source /opt/ros/humble/setup.bash
fi

echo -e "${BLUE}ROS2 Distro:${NC} $ROS_DISTRO"
echo

# Update package list
echo -e "${BLUE}[1/5]${NC} Updating package list..."
sudo apt update -qq

# Install TurtleBot3 packages
echo -e "${BLUE}[2/5]${NC} Installing TurtleBot3 packages..."
sudo apt install -y \
    ros-${ROS_DISTRO}-turtlebot3 \
    ros-${ROS_DISTRO}-turtlebot3-gazebo \
    ros-${ROS_DISTRO}-turtlebot3-simulations \
    ros-${ROS_DISTRO}-turtlebot3-msgs \
    ros-${ROS_DISTRO}-turtlebot3-description \
    ros-${ROS_DISTRO}-turtlebot3-teleop \
    ros-${ROS_DISTRO}-turtlebot3-bringup

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} TurtleBot3 packages installed"
else
    echo -e "${RED}✗${NC} Failed to install TurtleBot3 packages"
    exit 1
fi

# Install Nav2
echo -e "${BLUE}[3/5]${NC} Installing Nav2 navigation stack..."
sudo apt install -y \
    ros-${ROS_DISTRO}-navigation2 \
    ros-${ROS_DISTRO}-nav2-bringup \
    ros-${ROS_DISTRO}-nav2-common \
    ros-${ROS_DISTRO}-nav2-msgs \
    ros-${ROS_DISTRO}-slam-toolbox

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Nav2 installed"
else
    echo -e "${RED}✗${NC} Failed to install Nav2"
    exit 1
fi

# Install ros_gz_bridge if not present
echo -e "${BLUE}[4/5]${NC} Checking ros_gz_bridge..."
if ! dpkg -l | grep -q "ros-${ROS_DISTRO}-ros-gz-bridge"; then
    echo "Installing ros_gz_bridge..."
    sudo apt install -y ros-${ROS_DISTRO}-ros-gz-bridge
    echo -e "${GREEN}✓${NC} ros_gz_bridge installed"
else
    echo -e "${GREEN}✓${NC} ros_gz_bridge already installed"
fi

# Set TurtleBot3 model environment variable
echo -e "${BLUE}[5/5]${NC} Setting up environment..."

# Add to bashrc if not already there
if ! grep -q "TURTLEBOT3_MODEL" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# TurtleBot3 Model (for Gazebo MCP Demo 2)" >> ~/.bashrc
    echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
    echo -e "${GREEN}✓${NC} Added TURTLEBOT3_MODEL to ~/.bashrc"
else
    echo -e "${GREEN}✓${NC} TURTLEBOT3_MODEL already in ~/.bashrc"
fi

# Set for current session
export TURTLEBOT3_MODEL=burger

echo
echo "========================================"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo "========================================"
echo
echo "Installed packages:"
echo "  • TurtleBot3 (burger/waffle/waffle_pi)"
echo "  • Nav2 navigation stack"
echo "  • SLAM Toolbox"
echo "  • ros_gz_bridge"
echo
echo "Environment:"
echo "  • TURTLEBOT3_MODEL=burger (added to ~/.bashrc)"
echo
echo "Next steps:"
echo "  1. Source your bashrc: source ~/.bashrc"
echo "  2. Run setup script: ./setup.sh"
echo "  3. Follow CONVERSATIONAL_DEMO.md guide"
echo
echo -e "${BLUE}Tip:${NC} For current session, TURTLEBOT3_MODEL is already set to 'burger'"
echo
