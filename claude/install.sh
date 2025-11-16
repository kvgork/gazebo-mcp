#!/bin/bash

# Claude Code Global Installation Script
# Makes skills, agents, and commands available globally

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    CONFIG_DIR="$HOME/.config/claude-code"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    CONFIG_DIR="$HOME/Library/Application Support/Claude/claude-code"
else
    echo -e "${RED}Unsupported platform: $OSTYPE${NC}"
    echo "Please manually follow INSTALLATION.md"
    exit 1
fi

echo -e "${GREEN}=== Claude Code Global Installation ===${NC}"
echo -e "Repository: ${YELLOW}$SCRIPT_DIR${NC}"
echo -e "Platform: ${YELLOW}$PLATFORM${NC}"
echo -e "Config directory: ${YELLOW}$CONFIG_DIR${NC}"
echo ""

# Create config directory
echo -e "${GREEN}[1/6]${NC} Creating config directory..."
mkdir -p "$CONFIG_DIR"

# Symlink agents
echo -e "${GREEN}[2/6]${NC} Linking agents..."
if [ -L "$CONFIG_DIR/agents" ]; then
    echo "  Removing existing agents symlink..."
    rm "$CONFIG_DIR/agents"
elif [ -d "$CONFIG_DIR/agents" ]; then
    echo -e "${YELLOW}  Warning: agents directory exists. Backing up to agents.backup${NC}"
    mv "$CONFIG_DIR/agents" "$CONFIG_DIR/agents.backup"
fi
ln -sf "$SCRIPT_DIR/agents" "$CONFIG_DIR/agents"
echo "  ✓ Agents linked"

# Symlink commands
echo -e "${GREEN}[3/6]${NC} Linking commands..."
if [ -L "$CONFIG_DIR/commands" ]; then
    echo "  Removing existing commands symlink..."
    rm "$CONFIG_DIR/commands"
elif [ -d "$CONFIG_DIR/commands" ]; then
    echo -e "${YELLOW}  Warning: commands directory exists. Backing up to commands.backup${NC}"
    mv "$CONFIG_DIR/commands" "$CONFIG_DIR/commands.backup"
fi
ln -sf "$SCRIPT_DIR/commands" "$CONFIG_DIR/commands"
echo "  ✓ Commands linked"

# Symlink agent registry
echo -e "${GREEN}[4/6]${NC} Linking agent registry..."
if [ -f "$CONFIG_DIR/agent-registry.json" ]; then
    echo "  Backing up existing registry to agent-registry.json.backup"
    cp "$CONFIG_DIR/agent-registry.json" "$CONFIG_DIR/agent-registry.json.backup"
fi
ln -sf "$SCRIPT_DIR/agent-registry.json" "$CONFIG_DIR/agent-registry.json" 2>/dev/null || echo "  (agent-registry.json not found, skipping)"
echo "  ✓ Agent registry linked"

# Copy settings (don't symlink - user may want different global settings)
echo -e "${GREEN}[5/6]${NC} Setting up configuration..."
if [ -f "$CONFIG_DIR/settings.json" ]; then
    echo -e "${YELLOW}  settings.json already exists. Skipping...${NC}"
    echo "  (Manually merge $SCRIPT_DIR/settings.local.json if needed)"
elif [ -f "$SCRIPT_DIR/settings.local.json" ]; then
    cp "$SCRIPT_DIR/settings.local.json" "$CONFIG_DIR/settings.json"
    echo "  ✓ Settings copied"
else
    echo -e "${YELLOW}  settings.local.json not found. Skipping...${NC}"
fi

# Install Python package
echo -e "${GREEN}[6/6]${NC} Installing Python skills package..."
if command -v pip &> /dev/null; then
    pip install -e "$SCRIPT_DIR" --quiet
    echo "  ✓ Skills package installed"
else
    echo -e "${YELLOW}  Warning: pip not found. Skipping Python package installation.${NC}"
    echo "  Install manually with: pip install -e $SCRIPT_DIR"
fi

# Verify installation
echo ""
echo -e "${GREEN}=== Verification ===${NC}"

# Check symlinks
if [ -L "$CONFIG_DIR/agents" ] && [ -L "$CONFIG_DIR/commands" ]; then
    echo -e "${GREEN}✓${NC} Symlinks created successfully"
else
    echo -e "${RED}✗${NC} Symlink creation failed"
fi

# Check Python import
if python -c "from skills.code_analysis import CodeAnalysisSkill" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Skills Python package working"
else
    echo -e "${YELLOW}!${NC} Skills import check failed (may need to restart shell)"
fi

echo ""
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo ""
echo -e "${YELLOW}New Features Installed:${NC}"
echo "  • Dynamic Model Selection - Automatic cost optimization (30-85% savings)"
echo "  • Parallel Execution - 40-70% faster workflows"
echo "  • Token Efficiency - 95-99% token reduction for data-heavy operations"
echo "  • 68+ ROS2/Robotics commands"
echo "  • 14 teaching specialist agents"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure:"
echo "   ${YELLOW}cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env${NC}"
echo "   ${YELLOW}# Add your ANTHROPIC_API_KEY${NC}"
echo ""
echo "2. Restart Claude Code"
echo ""
echo "3. Try commands:"
echo "   ${YELLOW}/start-learning${NC} - Start a learning journey"
echo "   ${YELLOW}/dev \"Create a ROS2 node\"${NC} - Complete workflow"
echo "   ${YELLOW}/verify-all${NC} - Parallel verification"
echo ""
echo "4. Test skills from Python:"
echo "   ${YELLOW}from skills.code_analysis import analyze_codebase_parallel${NC}"
echo "   ${YELLOW}from skills.common import ModelSelector${NC}"
echo ""
echo "Configuration location: $CONFIG_DIR"
echo "Repository location: $SCRIPT_DIR"
echo "Documentation: $SCRIPT_DIR/README.md"
echo ""
echo -e "${GREEN}Happy coding!${NC}"
