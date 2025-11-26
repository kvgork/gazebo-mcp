#!/bin/bash
#
# Gazebo MCP Server - Global Uninstallation Script
#
# This script removes the globally configured Gazebo MCP server
#
# Usage: ./uninstall_mcp_global.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  Gazebo MCP Server - Uninstallation${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Check if Claude CLI exists
if ! command -v claude &> /dev/null; then
    echo -e "${RED}✗ Claude CLI not found${NC}"
    echo "Cannot uninstall - Claude CLI is not available"
    exit 1
fi

# Check if gazebo MCP server is registered
if ! claude mcp list 2>/dev/null | grep -q "gazebo"; then
    echo -e "${YELLOW}⚠ Gazebo MCP server not found in registered servers${NC}"
    echo "Nothing to uninstall."
    exit 0
fi

echo -e "${YELLOW}Removing Gazebo MCP server...${NC}"

# Remove the MCP server
if claude mcp remove gazebo; then
    echo -e "${GREEN}✓ MCP server unregistered${NC}"
else
    echo -e "${RED}✗ Failed to unregister MCP server${NC}"
    exit 1
fi

# Remove wrapper script if it exists
WRAPPER_SCRIPT="$HOME/.local/bin/gazebo-mcp-server"
if [ -f "$WRAPPER_SCRIPT" ]; then
    rm "$WRAPPER_SCRIPT"
    echo -e "${GREEN}✓ Removed wrapper script${NC}"
fi

# Remove project-level .mcp.json if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.mcp.json" ]; then
    read -p "Remove project-level .mcp.json? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$SCRIPT_DIR/.mcp.json"
        echo -e "${GREEN}✓ Removed .mcp.json${NC}"
    fi
fi

echo ""
echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}  ✓ Uninstallation Complete${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo -e "${YELLOW}Note:${NC}"
echo "- Python packages (mcp, dependencies) were not removed"
echo "- ROS2 installation was not affected"
echo "- To reinstall, run: ./install_mcp_global.sh"
echo ""
echo "You may need to restart Claude Code for changes to take effect."
echo ""
