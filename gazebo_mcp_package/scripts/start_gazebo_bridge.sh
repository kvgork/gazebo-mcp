#!/bin/bash
# Start Gazebo with complete service bridge
# This script bridges all required Modern Gazebo services to ROS2

set -e

# Get world name from environment or use default
WORLD_NAME=${GAZEBO_WORLD_NAME:-"empty"}

echo "Starting ros_gz_bridge for world: $WORLD_NAME"

# Bridge all required services
# Format: /world/WORLD/SERVICE@ros_gz_interfaces/srv/TYPE
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/${WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
