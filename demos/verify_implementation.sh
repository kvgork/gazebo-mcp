#!/bin/bash
# Verification script for demo implementation
set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Demo Implementation Verification"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        FAIL=$((FAIL + 1))
    fi
}

check_executable() {
    if [ -x "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 (executable)"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} $1 (not executable)"
        FAIL=$((FAIL + 1))
    fi
}

echo "Checking framework files..."
check_file "framework/__init__.py"
check_file "framework/demo_executor.py"
check_file "framework/demo_validator.py"
check_file "framework/config_loader.py"
echo ""

echo "Checking Hello World demo..."
check_file "01_hello_world/config.yaml"
check_file "01_hello_world/README.md"
check_file "01_hello_world/test_hello_world_demo.py"
check_executable "01_hello_world/hello_world_demo.py"
echo ""

echo "Checking Obstacle Course demo..."
check_file "02_obstacle_course/config.yaml"
check_file "02_obstacle_course/README.md"
check_file "02_obstacle_course/test_obstacle_course_demo.py"
check_file "02_obstacle_course/worlds/obstacle_course.sdf"
check_file "02_obstacle_course/models/simple_robot.sdf"
check_executable "02_obstacle_course/setup.sh"
check_executable "02_obstacle_course/obstacle_course_demo.py"
echo ""

echo "Checking integration files..."
check_file "README.md"
check_file "IMPLEMENTATION_COMPLETE.md"
check_executable "run_demo.py"
echo ""

echo "Checking CI/CD..."
check_file "../.github/workflows/demo-tests.yml"
echo ""

echo "Validating Python syntax..."
python3 -m py_compile framework/*.py
python3 -m py_compile 01_hello_world/*.py
python3 -m py_compile 02_obstacle_course/*.py
python3 -m py_compile run_demo.py
echo -e "${GREEN}✓${NC} All Python files compile successfully"
PASS=$((PASS + 1))
echo ""

echo "Validating YAML syntax..."
python3 -c "import yaml; yaml.safe_load(open('01_hello_world/config.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('02_obstacle_course/config.yaml'))"
echo -e "${GREEN}✓${NC} All YAML files valid"
PASS=$((PASS + 1))
echo ""

echo "Validating configurations..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from framework import ConfigLoader

# Hello World
config = ConfigLoader.load_demo_config('01_hello_world/config.yaml')
valid, errors = ConfigLoader.validate_config(config)
if not valid:
    print(f"Hello World config invalid: {errors}")
    sys.exit(1)
print("✓ Hello World config valid")

# Obstacle Course
config = ConfigLoader.load_demo_config('02_obstacle_course/config.yaml')
valid, errors = ConfigLoader.validate_config(config)
if not valid:
    print(f"Obstacle Course config invalid: {errors}")
    sys.exit(1)
print("✓ Obstacle Course config valid")
EOF
PASS=$((PASS + 1))
echo ""

echo "Counting lines of code..."
FRAMEWORK_LINES=$(find framework -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
HELLO_LINES=$(find 01_hello_world -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
OBSTACLE_LINES=$(find 02_obstacle_course -name "*.py" -o -name "*.sh" | xargs wc -l | tail -1 | awk '{print $1}')
INTEGRATION_LINES=$(wc -l run_demo.py | awk '{print $1}')
TOTAL_CODE=$((FRAMEWORK_LINES + HELLO_LINES + OBSTACLE_LINES + INTEGRATION_LINES))

echo "  Framework:        $FRAMEWORK_LINES lines"
echo "  Hello World:      $HELLO_LINES lines"
echo "  Obstacle Course:  $OBSTACLE_LINES lines"
echo "  Integration:      $INTEGRATION_LINES lines"
echo "  ─────────────────────────────"
echo "  Total:            $TOTAL_CODE lines"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  Verification Results"
echo "════════════════════════════════════════════════════════════════"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Implementation is complete.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start Gazebo and ros_gz_bridge"
    echo "  2. Run: ./run_demo.py --run 1"
    echo "  3. Try: ./run_demo.py --run 2"
    exit 0
else
    echo -e "${RED}⚠️  Some checks failed. Please review errors above.${NC}"
    exit 1
fi
