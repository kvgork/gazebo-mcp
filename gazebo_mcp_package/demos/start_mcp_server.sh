#!/bin/bash
# MCP Server Startup Script
# Automatically builds workspace and uses correct Python version

set -e

echo "========================================================================"
echo "  Starting Gazebo MCP Server"
echo "========================================================================"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Source ROS2 environment
echo "Sourcing ROS2 Humble environment..."
source /opt/ros/humble/setup.bash

# Check if workspace is built
if [ ! -f "install/setup.bash" ]; then
    echo ""
    echo "Workspace not built. Building now..."
    echo ""
    colcon build --symlink-install
    echo ""
    echo "✅ Build complete!"
fi

# Source local workspace
echo "Sourcing local workspace..."
source install/setup.bash

# Add src to PYTHONPATH so Python can find the modules
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

echo ""
echo "Starting MCP server with system Python 3.10..."
echo "Server location: src/gazebo_mcp/server.py"
echo "PYTHONPATH: $PYTHONPATH"
echo ""
echo "========================================================================"
echo ""

# Use system Python 3.10 explicitly and run the server directly
exec /usr/bin/python3 src/gazebo_mcp/server.py
