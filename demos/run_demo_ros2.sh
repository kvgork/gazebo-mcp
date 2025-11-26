#!/bin/bash
# ROS2-compatible demo launcher wrapper
# Uses system Python 3.10 instead of anaconda Python 3.11

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "  ROS2 Demo Launcher"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if ROS2 is sourced
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}⚠️  ROS2 environment not sourced${NC}"
    echo "Sourcing ROS2 Humble..."
    source /opt/ros/humble/setup.bash
    echo -e "${GREEN}✓${NC} ROS2 environment sourced"
    echo ""
fi

# Verify system Python
if [ ! -f /usr/bin/python3 ]; then
    echo -e "${RED}ERROR: System Python 3 not found at /usr/bin/python3${NC}"
    exit 1
fi

PYTHON_VERSION=$(/usr/bin/python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Using system Python: $PYTHON_VERSION"
echo -e "${GREEN}✓${NC} ROS2 Distribution: $ROS_DISTRO"
echo ""

# Run the launcher with system Python
exec /usr/bin/python3 run_demo.py "$@"
