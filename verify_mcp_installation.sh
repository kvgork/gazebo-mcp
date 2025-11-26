#!/bin/bash
#
# Gazebo MCP Server - Installation Verification Script
#
# This script verifies that the Gazebo MCP server is properly installed
# and configured for use with Claude Code.
#
# Usage: ./verify_mcp_installation.sh
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERRORS=0
WARNINGS=0

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  Gazebo MCP Server - Installation Verification${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARNINGS++))
}

# Check 1: Python version
echo -e "${BLUE}[1/10] Checking Python...${NC}"
if command -v python3.10 &> /dev/null; then
    PYTHON_VERSION=$(python3.10 --version)
    check_pass "Python 3.10+ found: $PYTHON_VERSION"
    PYTHON_CMD="python3.10"
elif command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version)
    check_pass "Python 3.11+ found: $PYTHON_VERSION"
    PYTHON_CMD="python3.11"
else
    check_fail "Python 3.10+ not found"
    PYTHON_CMD="python3"
fi
echo ""

# Check 2: Claude CLI
echo -e "${BLUE}[2/10] Checking Claude CLI...${NC}"
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "version unknown")
    check_pass "Claude CLI found: $CLAUDE_VERSION"
else
    check_fail "Claude CLI not found - required for MCP"
fi
echo ""

# Check 3: Project structure
echo -e "${BLUE}[3/10] Checking project files...${NC}"
if [ -f "$SCRIPT_DIR/src/gazebo_mcp/server.py" ]; then
    check_pass "Server source files found"
else
    check_fail "Server source files missing"
fi

if [ -f "$SCRIPT_DIR/mcp/server/server.py" ]; then
    check_pass "MCP server implementation found"
else
    check_fail "MCP server implementation missing"
fi

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    check_pass "requirements.txt found"
else
    check_fail "requirements.txt missing"
fi
echo ""

# Check 4: Python dependencies
echo -e "${BLUE}[4/10] Checking Python dependencies...${NC}"
REQUIRED_PACKAGES=("mcp" "pydantic" "pyyaml" "numpy" "pillow" "aiohttp")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if $PYTHON_CMD -c "import $package" 2>/dev/null; then
        check_pass "$package installed"
    else
        check_fail "$package not installed"
    fi
done
echo ""

# Check 5: ROS2 installation
echo -e "${BLUE}[5/10] Checking ROS2...${NC}"
if [ -f "/opt/ros/humble/setup.bash" ]; then
    check_pass "ROS2 Humble found"

    # Check if sourced
    if [ -n "$ROS_DISTRO" ]; then
        check_pass "ROS2 environment active: $ROS_DISTRO"
    else
        check_warn "ROS2 not sourced (run: source /opt/ros/humble/setup.bash)"
    fi
else
    check_warn "ROS2 not installed - MCP will run in mock mode"
    echo "  To install: ./install_mcp_global.sh --with-ros2"
fi
echo ""

# Check 6: Gazebo installation
echo -e "${BLUE}[6/10] Checking Gazebo...${NC}"
if command -v gz &> /dev/null; then
    GZ_VERSION=$(gz sim --version 2>&1 | head -1 || echo "unknown")
    check_pass "Gazebo found: $GZ_VERSION"
else
    check_warn "Gazebo not installed - required for real simulations"
    echo "  To install: ./install_mcp_global.sh --with-ros2"
fi
echo ""

# Check 7: MCP server registration
echo -e "${BLUE}[7/10] Checking MCP server registration...${NC}"
if command -v claude &> /dev/null; then
    if claude mcp list 2>/dev/null | grep -q "gazebo"; then
        check_pass "Gazebo MCP server registered globally"

        # Get details
        echo ""
        echo "Server details:"
        claude mcp get gazebo 2>/dev/null || echo "  (details unavailable)"
    else
        check_fail "Gazebo MCP server not registered"
        echo "  Run: ./install_mcp_global.sh"
    fi
else
    check_fail "Cannot check - Claude CLI not available"
fi
echo ""

# Check 8: Wrapper script
echo -e "${BLUE}[8/10] Checking wrapper script...${NC}"
WRAPPER_SCRIPT="$HOME/.local/bin/gazebo-mcp-server"
if [ -f "$WRAPPER_SCRIPT" ]; then
    check_pass "Wrapper script exists"
    if [ -x "$WRAPPER_SCRIPT" ]; then
        check_pass "Wrapper script is executable"
    else
        check_fail "Wrapper script not executable"
    fi
else
    check_warn "Wrapper script not found (expected at $WRAPPER_SCRIPT)"
fi
echo ""

# Check 9: Configuration files
echo -e "${BLUE}[9/10] Checking configuration files...${NC}"
if [ -f "$SCRIPT_DIR/.mcp.json" ]; then
    check_pass "Project-level .mcp.json found"

    # Validate JSON
    if command -v jq &> /dev/null; then
        if jq empty "$SCRIPT_DIR/.mcp.json" 2>/dev/null; then
            check_pass "JSON syntax valid"
        else
            check_fail "JSON syntax invalid"
        fi
    fi
else
    check_warn "No project-level .mcp.json (using global only)"
fi
echo ""

# Check 10: Test MCP server
echo -e "${BLUE}[10/10] Testing MCP server...${NC}"
if [ -f "$WRAPPER_SCRIPT" ] && [ -x "$WRAPPER_SCRIPT" ]; then
    echo "Attempting to start server (will timeout after 3 seconds)..."

    # Try to run the server with timeout
    if timeout 3s "$WRAPPER_SCRIPT" 2>&1 | head -5; then
        check_warn "Server started (killed after timeout - this is expected)"
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            check_pass "Server starts successfully (timeout expected)"
        else
            check_fail "Server failed to start (exit code: $EXIT_CODE)"
        fi
    fi
else
    check_warn "Cannot test - wrapper script not available"
fi
echo ""

# Summary
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  Verification Summary${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your Gazebo MCP server is properly installed and configured."
    echo ""
    echo "Next steps:"
    echo "1. Restart Claude Code if it's currently running"
    echo "2. Type /mcp in Claude Code to verify"
    echo "3. Start asking Claude to control Gazebo!"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo "Installation is functional but with some limitations."
    echo "The MCP server will work in mock mode without ROS2/Gazebo."
    echo ""
    echo "To install missing components: ./install_mcp_global.sh --with-ros2"
else
    echo -e "${RED}✗ ${ERRORS} error(s) and ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo "Please fix the errors above before using the MCP server."
    echo ""
    echo "To install: ./install_mcp_global.sh"
    echo "For help: ./install_mcp_global.sh --help"
fi

echo ""
echo -e "${BLUE}Additional Resources:${NC}"
echo "  - Setup Guide: cat MCP_SETUP_GUIDE.md"
echo "  - Demo Tests: cd demos && pytest -v"
echo "  - MCP Docs: https://code.claude.com/docs/en/mcp"
echo ""

exit $ERRORS
