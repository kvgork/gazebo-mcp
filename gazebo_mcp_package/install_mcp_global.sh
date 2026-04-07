#!/bin/bash
#
# Gazebo MCP Server - Global Installation Script
#
# This script installs and configures the Gazebo MCP server globally
# so it's available in all Claude Code sessions.
#
# Usage: ./install_mcp_global.sh [--with-ros2]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
INSTALL_ROS2=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-ros2)
            INSTALL_ROS2=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--with-ros2]"
            echo ""
            echo "Options:"
            echo "  --with-ros2    Also install ROS2 Humble and Gazebo Harmonic"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  Gazebo MCP Server - Global Installation${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

# Check Python 3.10+
if ! command -v python3.10 &> /dev/null; then
    if ! command -v python3.11 &> /dev/null; then
        echo -e "${RED}✗ Python 3.10+ not found${NC}"
        echo "Please install Python 3.10 or later:"
        echo "  sudo apt install python3.10"
        exit 1
    else
        PYTHON_CMD="python3.11"
    fi
else
    PYTHON_CMD="python3.10"
fi
echo -e "${GREEN}✓ Python found: $PYTHON_CMD${NC}"

# Check Claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}✗ Claude CLI not found${NC}"
    echo "Claude Code CLI is required but not found in PATH."
    echo "Please ensure Claude Code is properly installed."
    exit 1
fi
echo -e "${GREEN}✓ Claude CLI found${NC}"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/src/gazebo_mcp/server.py" ]; then
    echo -e "${RED}✗ Gazebo MCP source files not found${NC}"
    echo "Please run this script from the ros2_gazebo_mcp directory"
    exit 1
fi
echo -e "${GREEN}✓ Project structure verified${NC}"

echo ""

# Step 2: Install ROS2 (optional)
if [ "$INSTALL_ROS2" = true ]; then
    echo -e "${YELLOW}[2/6] Installing ROS2 Humble and Gazebo Harmonic...${NC}"

    # Check if already installed
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        echo -e "${GREEN}✓ ROS2 Humble already installed${NC}"
    else
        echo "Installing ROS2 Humble..."

        # Add ROS2 repository
        sudo apt update
        sudo apt install -y software-properties-common curl
        sudo add-apt-repository universe -y

        # Add ROS2 GPG key
        sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
            -o /usr/share/keyrings/ros-archive-keyring.gpg

        # Add ROS2 repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
            sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

        # Install ROS2
        sudo apt update
        sudo apt install -y ros-humble-desktop \
            ros-humble-gazebo-ros-pkgs \
            ros-humble-ros-gz-bridge \
            ros-humble-ros-gz-interfaces

        echo -e "${GREEN}✓ ROS2 Humble installed${NC}"
    fi

    # Install Gazebo Harmonic
    if command -v gz &> /dev/null; then
        echo -e "${GREEN}✓ Gazebo Harmonic already installed${NC}"
    else
        echo "Installing Gazebo Harmonic..."
        sudo apt install -y gz-harmonic
        echo -e "${GREEN}✓ Gazebo Harmonic installed${NC}"
    fi

    # Add ROS2 sourcing to bashrc if not already there
    if ! grep -q "source /opt/ros/humble/setup.bash" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# ROS2 Humble environment" >> ~/.bashrc
        echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
        echo -e "${GREEN}✓ Added ROS2 to ~/.bashrc${NC}"
    else
        echo -e "${GREEN}✓ ROS2 already in ~/.bashrc${NC}"
    fi
else
    echo -e "${YELLOW}[2/6] Skipping ROS2 installation (use --with-ros2 to install)${NC}"

    # Check if ROS2 is available
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        echo -e "${GREEN}✓ ROS2 Humble detected${NC}"
    else
        echo -e "${YELLOW}⚠ ROS2 not found - MCP server will run in mock mode${NC}"
        echo "  To install ROS2, run: $0 --with-ros2"
    fi
fi

echo ""

# Step 3: Install Python dependencies
echo -e "${YELLOW}[3/6] Installing Python dependencies...${NC}"

cd "$PROJECT_ROOT"

# Install requirements
$PYTHON_CMD -m pip install --user -r requirements.txt

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Step 4: Build the package (if using colcon)
echo -e "${YELLOW}[4/6] Checking package installation...${NC}"

# Try to install the package
$PYTHON_CMD -m pip install --user "$PROJECT_ROOT"

echo -e "${GREEN}✓ Package installation complete${NC}"
echo ""

# Step 5: Register MCP server globally
echo -e "${YELLOW}[5/6] Registering Gazebo MCP server globally...${NC}"

# Remove existing configuration if present
claude mcp remove gazebo 2>/dev/null || true

# Build the command
MCP_COMMAND="$PYTHON_CMD"
MCP_ARGS="-m mcp.server.server"

# Determine if ROS2 is available
if [ -f "/opt/ros/humble/setup.bash" ]; then
    ROS2_AVAILABLE="true"
    echo "ROS2 detected - configuring for full functionality"
else
    ROS2_AVAILABLE="false"
    echo "ROS2 not detected - configuring for mock mode"
fi

# Create temporary wrapper script for proper environment setup
WRAPPER_SCRIPT="$HOME/.local/bin/gazebo-mcp-server"
mkdir -p "$HOME/.local/bin"

cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
# Gazebo MCP Server Wrapper
# Automatically sources ROS2 environment if available

# Source ROS2 if available
if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi

# Set Python path
export PYTHONPATH="PROJECT_ROOT_PLACEHOLDER/src:PROJECT_ROOT_PLACEHOLDER:$PYTHONPATH"

# Execute the MCP server
exec PYTHON_CMD_PLACEHOLDER -m mcp.server.server "$@"
WRAPPER_EOF

# Replace placeholders
sed -i "s|PROJECT_ROOT_PLACEHOLDER|$PROJECT_ROOT|g" "$WRAPPER_SCRIPT"
sed -i "s|PYTHON_CMD_PLACEHOLDER|$PYTHON_CMD|g" "$WRAPPER_SCRIPT"

# Make executable
chmod +x "$WRAPPER_SCRIPT"

# Add MCP server using Claude CLI with the wrapper
claude mcp add --transport stdio gazebo -- "$WRAPPER_SCRIPT"

echo -e "${GREEN}✓ Gazebo MCP server registered globally${NC}"
echo "  Command: $WRAPPER_SCRIPT"
echo ""

# Step 6: Verify installation
echo -e "${YELLOW}[6/6] Verifying installation...${NC}"

# Check if MCP server is in the list
if claude mcp list | grep -q "gazebo"; then
    echo -e "${GREEN}✓ MCP server registered successfully${NC}"
else
    echo -e "${RED}✗ MCP server not found in list${NC}"
    echo "Something went wrong. Please check the output above."
    exit 1
fi

echo ""
echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}  ✓ Installation Complete!${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Restart Claude Code (completely exit and reopen)"
echo ""
echo "2. In Claude Code, check MCP status:"
echo "   Type: /mcp"
echo ""
echo "3. Start using Gazebo MCP tools:"
echo "   - \"List all models in the simulation\""
echo "   - \"Spawn a box at position (1, 2, 0.5)\""
echo "   - \"Get simulation status\""
echo ""

if [ "$INSTALL_ROS2" = true ]; then
    echo -e "${YELLOW}Important:${NC}"
    echo "You need to restart your terminal or run:"
    echo "  source ~/.bashrc"
    echo "for ROS2 environment to be available."
    echo ""
fi

echo -e "${YELLOW}Testing:${NC}"
echo ""
echo "To test the MCP server manually:"
echo "  $WRAPPER_SCRIPT"
echo ""
echo "To verify in Claude Code:"
echo "  claude mcp list"
echo "  claude mcp get gazebo"
echo ""

echo -e "${BLUE}Available MCP Tools:${NC}"
echo "  - Model Management (5 tools)"
echo "  - Sensor Access (3 tools)"
echo "  - World Control (4 tools)"
echo "  - Simulation Control (6 tools)"
echo ""
echo "See MCP_SETUP_GUIDE.md for detailed documentation."
echo ""
echo -e "${GREEN}Happy robot simulating! 🤖${NC}"
