#!/bin/bash
# Launch Nav2 for Obstacle Course Demo
# Part of Demo 2: Obstacle Course with TurtleBot3

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "  Nav2 Launch for Obstacle Course"
echo "========================================"
echo

# Source ROS2
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}⚠${NC} Sourcing ROS2 Humble..."
    source /opt/ros/humble/setup.bash
fi

# Set TurtleBot3 model
export TURTLEBOT3_MODEL=burger
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:/opt/ros/humble/share/turtlebot3_gazebo/models

echo -e "${GREEN}✓${NC} ROS2 Distro: $ROS_DISTRO"
echo -e "${GREEN}✓${NC} TurtleBot3 Model: $TURTLEBOT3_MODEL"
echo

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if params file exists
PARAMS_FILE="$SCRIPT_DIR/nav2_params.yaml"
if [ ! -f "$PARAMS_FILE" ]; then
    echo -e "${RED}✗${NC} Nav2 params file not found: $PARAMS_FILE"
    echo "Please create nav2_params.yaml first"
    exit 1
fi

echo -e "${GREEN}✓${NC} Nav2 params: $PARAMS_FILE"
echo

# Check if Gazebo is running
if ! pgrep -x "gz" > /dev/null && ! pgrep -x "ruby" > /dev/null; then
    echo -e "${YELLOW}⚠${NC} Gazebo doesn't appear to be running"
    echo "  Start Gazebo first with: gz sim -r worlds/obstacle_course_nav2.sdf"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if ros_gz_bridge is running
if ! pgrep -f "parameter_bridge" > /dev/null; then
    echo -e "${YELLOW}⚠${NC} ros_gz_bridge doesn't appear to be running"
    echo "  Start bridge with ./setup.sh or manually"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}Starting Nav2 Stack...${NC}"
echo

# Launch Nav2
# Note: We use bringup_launch.py which includes:
# - controller_server
# - planner_server
# - recoveries_server
# - bt_navigator
# - waypoint_follower
# - velocity_smoother

ros2 launch nav2_bringup bringup_launch.py \
    use_sim_time:=True \
    params_file:=$PARAMS_FILE \
    autostart:=True

# Note: This blocks until Ctrl+C
# In separate terminal, you can check with:
#   ros2 node list | grep nav2
#   ros2 topic list | grep nav
