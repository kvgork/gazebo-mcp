#!/bin/bash
# Gazebo MCP Environment Verification Script
# Run this before starting implementation to verify your environment is ready

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════╗"
echo "║   Gazebo MCP Environment Verification                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Track overall status
ERRORS=0
WARNINGS=0

# Check 1: ROS2 Environment
echo "1. Checking ROS2 Environment..."
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${RED}❌ ROS2 not sourced${NC}"
    echo "   Run: source /opt/ros/humble/setup.bash"
    echo "   Add to ~/.bashrc for permanent setup"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ ROS2 $ROS_DISTRO sourced${NC}"

    # Check ROS2 version
    if command -v ros2 &> /dev/null; then
        ROS_VERSION=$(ros2 --version 2>&1 | head -n1)
        echo "   Version: $ROS_VERSION"
    fi
fi
echo ""

# Check 2: Gazebo Installation
echo "2. Checking Gazebo Installation..."
if ! command -v gz &> /dev/null; then
    echo -e "${RED}❌ Gazebo not installed${NC}"
    echo "   Install: sudo apt install gz-harmonic"
    ERRORS=$((ERRORS + 1))
else
    GZ_VERSION=$(gz sim --version 2>&1 | head -n1)
    echo -e "${GREEN}✅ Gazebo installed${NC}"
    echo "   $GZ_VERSION"
fi
echo ""

# Check 3: TurtleBot3 Packages
echo "3. Checking TurtleBot3 Packages..."
if [ ! -z "$ROS_DISTRO" ] && command -v ros2 &> /dev/null; then
    if ros2 pkg list 2>/dev/null | grep -q turtlebot3_gazebo; then
        echo -e "${GREEN}✅ TurtleBot3 Gazebo packages installed${NC}"
        TB3_VERSION=$(ros2 pkg xml turtlebot3_gazebo | grep version | sed 's/.*>\(.*\)<.*/\1/')
        echo "   Version: $TB3_VERSION"
    else
        echo -e "${YELLOW}⚠️  TurtleBot3 packages not found${NC}"
        echo "   Install: sudo apt install ros-$ROS_DISTRO-turtlebot3-*"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Cannot check (ROS2 not available)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check 4: Python Environment
echo "4. Checking Python Environment..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not installed${NC}"
    ERRORS=$((ERRORS + 1))
else
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"

    # Check Python version >= 3.10
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PYTHON_MINOR" -lt 10 ]; then
        echo -e "${RED}❌ Python 3.10+ required, found 3.$PYTHON_MINOR${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# Check 5: Python Dependencies
echo "5. Checking Python Dependencies..."
if [ -f "requirements.txt" ]; then
    if command -v pip &> /dev/null; then
        # Check if packages can be imported
        python3 -c "import mcp" 2>/dev/null && MCP_OK=1 || MCP_OK=0
        python3 -c "import pydantic" 2>/dev/null && PYDANTIC_OK=1 || PYDANTIC_OK=0
        python3 -c "import yaml" 2>/dev/null && YAML_OK=1 || YAML_OK=0

        if [ $MCP_OK -eq 1 ] && [ $PYDANTIC_OK -eq 1 ] && [ $YAML_OK -eq 1 ]; then
            echo -e "${GREEN}✅ Core dependencies installed${NC}"
        else
            echo -e "${YELLOW}⚠️  Some dependencies missing${NC}"
            echo "   Install: pip install -r requirements.txt"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo -e "${RED}❌ pip not installed${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check 6: Project Structure
echo "6. Checking Project Structure..."
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Not in project root (pyproject.toml not found)${NC}"
    ERRORS=$((ERRORS + 1))
elif [ ! -d "src/gazebo_mcp" ]; then
    echo -e "${RED}❌ Source directory missing (src/gazebo_mcp not found)${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ Project structure correct${NC}"

    # Count implementation files
    if [ -d "docs/implementation" ]; then
        PHASE_COUNT=$(ls -1 docs/implementation/PHASE_*.md 2>/dev/null | wc -l)
        echo "   Phase documents: $PHASE_COUNT"
    fi
fi
echo ""

# Check 7: Development Tools
echo "7. Checking Development Tools..."
DEV_TOOLS_OK=1

if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️  pytest not installed${NC}"
    DEV_TOOLS_OK=0
fi

if ! command -v black &> /dev/null; then
    echo -e "${YELLOW}⚠️  black not installed${NC}"
    DEV_TOOLS_OK=0
fi

if ! command -v ruff &> /dev/null; then
    echo -e "${YELLOW}⚠️  ruff not installed${NC}"
    DEV_TOOLS_OK=0
fi

if [ $DEV_TOOLS_OK -eq 1 ]; then
    echo -e "${GREEN}✅ Development tools installed${NC}"
else
    echo "   Install: pip install -r requirements-dev.txt"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Check 8: Git Repository
echo "8. Checking Git Repository..."
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Not a git repository${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    BRANCH=$(git branch --show-current)
    echo -e "${GREEN}✅ Git repository${NC}"
    echo "   Current branch: $BRANCH"

    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        echo "   Working directory clean"
    else
        echo -e "${YELLOW}   ⚠️  Uncommitted changes present${NC}"
    fi
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════"
echo "                    SUMMARY"
echo "═══════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Environment is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review: docs/implementation/IMPLEMENTATION_PLAN.md"
    echo "2. Start: docs/implementation/PHASE_2_INFRASTRUCTURE.md"
    echo "3. Run tests: pytest tests/ -v"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found.${NC}"
    echo "Environment is usable but some features may not work."
    echo ""
    echo "Recommended: Install missing optional dependencies"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) and $WARNINGS warning(s) found.${NC}"
    echo "Please fix errors before proceeding."
    echo ""
    echo "Common fixes:"
    echo "• Source ROS2: source /opt/ros/humble/setup.bash"
    echo "• Install Gazebo: sudo apt install gz-harmonic"
    echo "• Install TurtleBot3: sudo apt install ros-humble-turtlebot3-*"
    echo "• Install Python deps: pip install -r requirements.txt"
    exit 1
fi
