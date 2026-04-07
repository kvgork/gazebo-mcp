#!/bin/bash
# Test single service bridge

set -e

# Source ROS2
source /opt/ros/humble/setup.bash

# Start Gazebo
echo "Starting Gazebo..."
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf > /tmp/gz_test.log 2>&1 &
GZ_PID=$!
echo "Gazebo PID: $GZ_PID"

sleep 10

# Start bridge
echo "Starting bridge..."
ros2 run ros_gz_bridge parameter_bridge "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" > /tmp/bridge_single.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge PID: $BRIDGE_PID"

sleep 5

# Check services
echo "Checking ROS2 services..."
ros2 service list | grep world || echo "No /world/ services found"

echo ""
echo "Bridge log:"
cat /tmp/bridge_single.log

# Cleanup
echo ""
echo "Cleaning up..."
kill -9 $BRIDGE_PID $GZ_PID 2>/dev/null || true
pkill -9 -f "ign.*gazebo" 2>/dev/null || true
pkill -9 ruby 2>/dev/null || true
