#!/bin/bash
# Start ros_gz_bridge for complete ROS2 ↔ Ignition Gazebo integration.
#
# Bridges:
#   - World services (spawn, delete, control, set_pose)
#   - Clock
#   - Diff-drive robot topics (cmd_vel, odometry)
#   - Sensor topics (lidar/scan, IMU, joint states)
#
# Usage:
#   ./start_gazebo_bridge.sh [--world WORLD_NAME]
#   GAZEBO_WORLD_NAME=my_world ./start_gazebo_bridge.sh

set -e

# Parse --world argument or fall back to env var, then auto-detect
WORLD_NAME="${GAZEBO_WORLD_NAME:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --world)
            WORLD_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--world WORLD_NAME]"
            exit 1
            ;;
    esac
done

# Auto-detect world name if not set
if [ -z "$WORLD_NAME" ]; then
    for CLI in gz ign; do
        if command -v "$CLI" &>/dev/null; then
            DETECTED=$(${CLI} service --list 2>/dev/null | grep -oP '/world/\K[^/]+(?=/control$)' | head -1)
            if [ -n "$DETECTED" ]; then
                WORLD_NAME="$DETECTED"
                echo "Auto-detected Gazebo world: '$WORLD_NAME'"
                break
            fi
        fi
    done
fi

# Final fallback
WORLD_NAME="${WORLD_NAME:-default}"

echo "Starting ros_gz_bridge for world: $WORLD_NAME"

source /opt/ros/humble/setup.bash

# Source workspace if available
if [ -f "$(dirname "$0")/../../install/setup.bash" ]; then
    source "$(dirname "$0")/../../install/setup.bash"
fi

# Relay model TF to /tf so TF2 listeners can find robot frames.
# Uses custom tf_relay.py since topic_tools may not be installed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/tf_relay.py" --model turtlebot3 &
RELAY_PID=$!
trap "kill $RELAY_PID 2>/dev/null" EXIT

exec ros2 run ros_gz_bridge parameter_bridge \
  "/world/${WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock" \
  "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist" \
  "/model/turtlebot3/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist" \
  "/model/turtlebot3/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry" \
  "/model/turtlebot3/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V" \
  "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan" \
  "/imu@sensor_msgs/msg/Imu[gz.msgs.IMU" \
  "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model"
