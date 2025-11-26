#!/bin/bash
# Test Modern Gazebo adapter with automated Gazebo launch
#
# Usage:
#   ./scripts/test_modern_adapter.sh
#
# This script:
# 1. Starts Modern Gazebo (Ignition) in background
# 2. Waits for Gazebo to be ready
# 3. Runs integration tests
# 4. Cleans up

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Modern Gazebo Adapter Test Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ignition Gazebo is available
if ! command -v ign &> /dev/null; then
    echo -e "${RED}ERROR: Ignition Gazebo (ign) not found in PATH${NC}"
    echo "Please install Modern Gazebo:"
    echo "  sudo apt install ros-humble-ros-gz"
    exit 1
fi

# Check Gazebo version
echo -e "${GREEN}✓${NC} Found Ignition Gazebo:"
ign gazebo --version | head -1

# Set environment variables
export GAZEBO_BACKEND=modern
export GAZEBO_WORLD_NAME=empty
export GAZEBO_TIMEOUT=20.0

echo ""
echo "Environment:"
echo "  GAZEBO_BACKEND=$GAZEBO_BACKEND"
echo "  GAZEBO_WORLD_NAME=$GAZEBO_WORLD_NAME"
echo "  GAZEBO_TIMEOUT=$GAZEBO_TIMEOUT"
echo ""

# Start Gazebo (without ROS2 integration - bridge handles that)
echo "Starting Modern Gazebo..."
source /opt/ros/humble/setup.bash
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf > /tmp/gazebo_test.log 2>&1 &
GAZEBO_PID=$!

echo -e "${YELLOW}⏳${NC} Waiting for Gazebo to initialize (PID: $GAZEBO_PID)..."

# Wait for Gazebo to be ready (check Ignition Transport services)
MAX_WAIT=30
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ign service -l 2>/dev/null | grep -q "/world/empty/"; then
        echo -e "${GREEN}✓${NC} Gazebo is ready!"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}ERROR: Gazebo failed to start within ${MAX_WAIT}s${NC}"
    echo "Check logs: /tmp/gazebo_test.log"
    kill $GAZEBO_PID 2>/dev/null || true
    pkill -9 -f "ign.*gazebo" 2>/dev/null || true
    pkill -9 ruby 2>/dev/null || true
    exit 1
fi

# Start ros_gz_bridge to expose services to ROS2
echo ""
echo "Starting ros_gz_bridge to expose services to ROS2..."
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/${GAZEBO_WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${GAZEBO_WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${GAZEBO_WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${GAZEBO_WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock" \
  > /tmp/bridge_test.log 2>&1 &
BRIDGE_PID=$!

echo -e "${YELLOW}⏳${NC} Waiting for bridge to expose services (PID: $BRIDGE_PID)..."

# Wait for ROS2 services to appear
MAX_WAIT=15
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    SERVICE_COUNT=$(ros2 service list 2>/dev/null | grep -c "/world/${GAZEBO_WORLD_NAME}/" || echo "0")
    if [ "$SERVICE_COUNT" -ge 4 ]; then
        echo -e "${GREEN}✓${NC} Bridge is ready! Found $SERVICE_COUNT services"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}ERROR: Bridge failed to expose services within ${MAX_WAIT}s${NC}"
    echo "Check logs: /tmp/bridge_test.log"
    cat /tmp/bridge_test.log
    kill $BRIDGE_PID 2>/dev/null || true
    kill $GAZEBO_PID 2>/dev/null || true
    pkill -9 -f "ign.*gazebo" 2>/dev/null || true
    pkill -9 ruby 2>/dev/null || true
    exit 1
fi

# List available services for verification
echo "Available ROS2 services:"
ros2 service list | grep "/world/" | head -10
echo ""

# Warmup: Test if services are actually callable (not just visible)
echo -e "${YELLOW}⏳${NC} Warming up bridge connection..."
MAX_WARMUP_ATTEMPTS=5
WARMUP_SUCCESS=false

for i in $(seq 1 $MAX_WARMUP_ATTEMPTS); do
    if timeout 5 ros2 service call /world/${GAZEBO_WORLD_NAME}/control ros_gz_interfaces/srv/ControlWorld \
        "{world_control: {pause: false}}" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Bridge is warm and callable (attempt $i)"
        WARMUP_SUCCESS=true
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

if [ "$WARMUP_SUCCESS" = false ]; then
    echo -e "${YELLOW}WARNING: Bridge warmup test failed, but continuing anyway${NC}"
    echo "Tests may experience initial timeouts"
fi

# Run tests
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Running Integration Tests"
echo "════════════════════════════════════════════════════════════════"
echo ""

source /opt/ros/humble/setup.bash
/usr/bin/python3 tests/test_modern_adapter_integration.py
TEST_EXIT_CODE=$?

# Cleanup
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Cleanup"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "Stopping bridge (PID: $BRIDGE_PID)..."
kill $BRIDGE_PID 2>/dev/null || true

echo "Stopping Gazebo (PID: $GAZEBO_PID)..."
kill $GAZEBO_PID 2>/dev/null || true
sleep 2

# Force kill if still running
if ps -p $GAZEBO_PID > /dev/null 2>&1; then
    echo "Force killing Gazebo..."
    kill -9 $GAZEBO_PID 2>/dev/null || true
fi

if ps -p $BRIDGE_PID > /dev/null 2>&1; then
    echo "Force killing bridge..."
    kill -9 $BRIDGE_PID 2>/dev/null || true
fi

# Clean up any remaining gz/ruby/bridge processes
pkill -9 -f "ign.*gazebo" 2>/dev/null || true
pkill -9 -f "parameter_bridge" 2>/dev/null || true
pkill -9 ruby 2>/dev/null || true

echo -e "${GREEN}✓${NC} Cleanup complete"
echo ""

# Exit with test result
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${GREEN}  ✅ All tests passed!${NC}"
    echo "════════════════════════════════════════════════════════════════"
    exit 0
else
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${RED}  ❌ Tests failed (exit code: $TEST_EXIT_CODE)${NC}"
    echo "════════════════════════════════════════════════════════════════"
    exit $TEST_EXIT_CODE
fi
