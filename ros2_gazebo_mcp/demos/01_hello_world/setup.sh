#!/bin/bash
# Demo 7.1.1: Hello World - Setup Script
# Automates pre-demo setup and verification

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Demo 7.1.1: Hello World - Setup"
echo "========================================="
echo ""

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# 1. Check ROS2 Installation
echo "Checking prerequisites..."
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}Sourcing ROS2...${NC}"
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        source /opt/ros/humble/setup.bash
        print_status $? "ROS2 Humble sourced"
    else
        print_status 1 "ROS2 not found. Please install ROS2 Humble."
        exit 1
    fi
else
    print_status 0 "ROS2 $ROS_DISTRO detected"
fi

# 2. Check Gazebo
if command_exists gz; then
    GZ_VERSION=$(gz sim --version 2>&1 | head -n1)
    print_status 0 "Gazebo found: $GZ_VERSION"
else
    print_status 1 "Gazebo not found. Please install Gazebo Harmonic."
    exit 1
fi

# 3. Check TurtleBot3 models
echo ""
echo "Checking robot models..."
TURTLEBOT3_MODEL_PATH="/opt/ros/humble/share/turtlebot3_description"
if [ -d "$TURTLEBOT3_MODEL_PATH" ]; then
    print_status 0 "TurtleBot3 models found"
else
    echo -e "${YELLOW}Installing TurtleBot3 models...${NC}"
    sudo apt update
    sudo apt install -y ros-humble-turtlebot3 ros-humble-turtlebot3-description
    print_status $? "TurtleBot3 installed"
fi

# 4. Check MCP Server
echo ""
echo "Checking MCP Server..."
if command_exists gazebo-mcp-server; then
    print_status 0 "MCP Server found"
else
    print_status 1 "MCP Server not found. Please install from repo."
    echo "  Run: pip install -e /path/to/gazebo-mcp/ros2_gazebo_mcp"
    exit 1
fi

# 5. Test Gazebo Launch
echo ""
echo "Testing Gazebo launch..."
echo -e "${YELLOW}Starting Gazebo (will close in 5 seconds)...${NC}"

# Start Gazebo in background
gz sim empty.sdf &
GZ_PID=$!
sleep 5

# Check if Gazebo is running
if ps -p $GZ_PID > /dev/null; then
    print_status 0 "Gazebo launches successfully"
    kill $GZ_PID
    wait $GZ_PID 2>/dev/null
else
    print_status 1 "Gazebo failed to launch"
    exit 1
fi

# 6. Create demo workspace
echo ""
echo "Setting up demo workspace..."
DEMO_DIR="$(dirname "$0")"
cd "$DEMO_DIR"

# Create required directories
mkdir -p logs
mkdir -p slides
print_status 0 "Workspace created"

# 7. Generate quick test script
cat > quick_test.sh << 'EOF'
#!/bin/bash
# Quick test before demo
echo "Running quick test..."

# Start Gazebo
source /opt/ros/humble/setup.bash
gz sim empty.sdf &
GZ_PID=$!
sleep 3

# Check Gazebo is running
if ! ps -p $GZ_PID > /dev/null; then
    echo "❌ Gazebo failed to start"
    exit 1
fi

echo "✅ Gazebo running (PID: $GZ_PID)"
echo ""
echo "Quick Test Checklist:"
echo "  1. Gazebo window visible? [y/n]"
echo "  2. Ground plane visible? [y/n]"
echo "  3. No error messages? [y/n]"
echo ""
echo "Press Enter to stop Gazebo..."
read
kill $GZ_PID
echo "Test complete."
EOF
chmod +x quick_test.sh
print_status 0 "Quick test script created"

# 8. Create MCP server launch script
cat > start_mcp_server.sh << 'EOF'
#!/bin/bash
# Start MCP Server for Demo
source /opt/ros/humble/setup.bash
cd "$(dirname "$0")"

echo "Starting MCP Server..."
echo "Log file: logs/mcp_server.log"

# Start with logging
gazebo-mcp-server --log-level INFO 2>&1 | tee logs/mcp_server.log
EOF
chmod +x start_mcp_server.sh
print_status 0 "MCP server launcher created"

# 9. Create emergency recovery script
cat > emergency_recovery.sh << 'EOF'
#!/bin/bash
# Emergency Recovery - Use if demo fails
echo "🚨 Emergency Recovery Mode"

echo "Killing all Gazebo processes..."
killall -9 gz 2>/dev/null
killall -9 gzserver 2>/dev/null
killall -9 gzclient 2>/dev/null

echo "Killing MCP server..."
killall -9 gazebo-mcp-server 2>/dev/null

sleep 2

echo "Restarting Gazebo..."
source /opt/ros/humble/setup.bash
gz sim empty.sdf &

echo ""
echo "Recovery complete. Wait 5 seconds, then restart MCP server."
echo "Run: ./start_mcp_server.sh"
EOF
chmod +x emergency_recovery.sh
print_status 0 "Emergency recovery script created"

# 10. Create pre-demo checklist
cat > PRE_DEMO_CHECKLIST.md << 'EOF'
# Pre-Demo Checklist - Hello World Demo

Run through this checklist 15 minutes before demo:

## 15 Minutes Before
- [ ] Close all unnecessary applications
- [ ] Clear browser tabs (reduce lag)
- [ ] Disable notifications (Do Not Disturb)
- [ ] Check internet connection (if needed)
- [ ] Increase screen brightness for visibility
- [ ] Test audio (if presenting remotely)

## 10 Minutes Before
- [ ] Run `./quick_test.sh` - verify Gazebo works
- [ ] Start Gazebo: `gz sim empty.sdf`
- [ ] Start MCP Server: `./start_mcp_server.sh`
- [ ] Test one spawn command with Claude
- [ ] Verify robot appears and moves
- [ ] Have backup video ready to play

## 5 Minutes Before
- [ ] Position Gazebo window for audience visibility
- [ ] Position Claude Code window for visibility
- [ ] Have emergency_recovery.sh ready in terminal
- [ ] Take a deep breath - you've got this! 🚀
- [ ] Have water nearby

## During Demo
- [ ] Speak clearly and slowly
- [ ] Point to screen when referencing
- [ ] Pause after each command for effect
- [ ] If failure occurs: stay calm, use recovery plan

## After Demo
- [ ] Save logs: `cp logs/* ~/demo_logs_$(date +%Y%m%d)/`
- [ ] Note what worked well
- [ ] Note what could improve
- [ ] Answer questions
- [ ] Share follow-up materials
EOF
print_status 0 "Pre-demo checklist created"

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Review: cat PRE_DEMO_CHECKLIST.md"
echo "  2. Practice: Review script.md"
echo "  3. Test: ./quick_test.sh"
echo "  4. Before demo: Follow PRE_DEMO_CHECKLIST.md"
echo ""
echo "Emergency scripts available:"
echo "  - emergency_recovery.sh (if things go wrong)"
echo "  - start_mcp_server.sh (clean MCP start)"
echo ""
echo -e "${GREEN}Ready to deliver an amazing demo!${NC} 🎉"
echo ""
