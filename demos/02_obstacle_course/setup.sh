#!/bin/bash
# Obstacle Course Demo Setup Script

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Obstacle Course Demo Setup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD_FILE="${SCRIPT_DIR}/worlds/obstacle_course.sdf"

# Check dependencies
echo "Checking dependencies..."

# Check ROS2
if ! command -v ros2 &> /dev/null; then
    echo -e "${RED}ERROR: ROS2 not found${NC}"
    echo "Please install ROS2 Humble"
    exit 1
fi
echo -e "${GREEN}✓${NC} ROS2 found"

# Check Gazebo
if ! command -v gz &> /dev/null; then
    echo -e "${RED}ERROR: Gazebo (gz) not found${NC}"
    echo "Please install Modern Gazebo"
    exit 1
fi
echo -e "${GREEN}✓${NC} Gazebo found"

# Check ros_gz_bridge
source /opt/ros/humble/setup.bash
if ! ros2 pkg list | grep -q "ros_gz_bridge"; then
    echo -e "${RED}ERROR: ros_gz_bridge not found${NC}"
    echo "Please install: sudo apt install ros-humble-ros-gz-bridge"
    exit 1
fi
echo -e "${GREEN}✓${NC} ros_gz_bridge found"

echo ""
echo "Dependencies satisfied!"
echo ""

# Check if Gazebo is already running
if pgrep -f "gz sim" > /dev/null; then
    echo -e "${YELLOW}WARNING: Gazebo is already running${NC}"
    echo "Please stop existing Gazebo instance first:"
    echo "  pkill -f 'gz sim'"
    exit 1
fi

# Set environment
export GAZEBO_WORLD_NAME="obstacle_course"
export GAZEBO_BACKEND="modern"
export GAZEBO_TIMEOUT="45.0"

echo "Environment:"
echo "  GAZEBO_WORLD_NAME=$GAZEBO_WORLD_NAME"
echo "  GAZEBO_BACKEND=$GAZEBO_BACKEND"
echo "  GAZEBO_TIMEOUT=$GAZEBO_TIMEOUT"
echo ""

# Check world file exists
if [ ! -f "$WORLD_FILE" ]; then
    echo -e "${RED}ERROR: World file not found: $WORLD_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} World file found: $WORLD_FILE"
echo ""

# Start Gazebo
echo "Starting Gazebo with obstacle course world..."
gz sim -r "$WORLD_FILE" > /tmp/obstacle_course_gazebo.log 2>&1 &
GAZEBO_PID=$!
echo "Gazebo PID: $GAZEBO_PID"

# Wait for Gazebo
echo -e "${YELLOW}⏳${NC} Waiting for Gazebo to initialize..."
MAX_WAIT=30
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if gz service -l 2>/dev/null | grep -q "/world/$GAZEBO_WORLD_NAME/"; then
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
    echo "Check logs: /tmp/obstacle_course_gazebo.log"
    kill $GAZEBO_PID 2>/dev/null || true
    exit 1
fi

# Start ros_gz_bridge
echo ""
echo "Starting ros_gz_bridge..."
ros2 run ros_gz_bridge parameter_bridge \
  "/world/${GAZEBO_WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${GAZEBO_WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${GAZEBO_WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${GAZEBO_WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/world/${GAZEBO_WORLD_NAME}/state@ros_gz_interfaces/srv/GetWorldState" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock" \
  > /tmp/obstacle_course_bridge.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge PID: $BRIDGE_PID"

# Wait for bridge
echo -e "${YELLOW}⏳${NC} Waiting for bridge to expose services..."
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
    echo -e "${RED}ERROR: Bridge failed within ${MAX_WAIT}s${NC}"
    echo "Check logs: /tmp/obstacle_course_bridge.log"
    kill $BRIDGE_PID 2>/dev/null || true
    kill $GAZEBO_PID 2>/dev/null || true
    exit 1
fi

# Warmup test
echo ""
echo "Testing bridge connection..."
if timeout 5 ros2 service call "/world/$GAZEBO_WORLD_NAME/control" ros_gz_interfaces/srv/ControlWorld \
    "{world_control: {pause: false}}" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Bridge is functional!"
else
    echo -e "${YELLOW}WARNING: Bridge warmup test failed${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo "Gazebo PID:  $GAZEBO_PID"
echo "Bridge PID:  $BRIDGE_PID"
echo ""
echo "Available services:"
ros2 service list | grep "/world/" | head -10
echo ""
echo "To run the demo:"
echo "  python3 obstacle_course_demo.py"
echo ""
echo "To stop:"
echo "  kill $GAZEBO_PID $BRIDGE_PID"
echo "  # or"
echo "  pkill -f 'gz sim'"
echo "  pkill -f 'parameter_bridge'"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Save PIDs for cleanup script
echo "$GAZEBO_PID" > /tmp/obstacle_course_gazebo.pid
echo "$BRIDGE_PID" > /tmp/obstacle_course_bridge.pid

echo "Environment is ready! You can now run the demo."
