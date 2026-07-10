#!/usr/bin/env bash
# Wrapper: source ROS2 Jazzy + venv, then exec gazebo-mcp server (stdio).
set -e
source /opt/ros/jazzy/setup.bash
source /home/koen/workspaces/gazebo-mcp/.venv/bin/activate
export PYTHONUNBUFFERED=1
export GAZEBO_BACKEND="${GAZEBO_BACKEND:-modern}"
export GAZEBO_WORLD_NAME="${GAZEBO_WORLD_NAME:-empty}"
cd /home/koen/workspaces/gazebo-mcp
exec python -m gazebo_mcp.server
