#!/bin/bash
# Phase 2 Verification Script
# Run this to verify Phase 2 is complete before proceeding to Phase 3

set -e  # Exit on first error

echo "=== Phase 2 Verification ==="
echo ""

echo "1. Running tests with coverage..."
pytest tests/ -v --cov=gazebo_mcp --cov-report=term-missing --cov-fail-under=80

echo ""
echo "2. Type checking with mypy..."
mypy src/gazebo_mcp --strict

echo ""
echo "3. Linting with ruff..."
ruff check src/ tests/

echo ""
echo "4. Checking code formatting..."
black src/ tests/ --check

echo ""
echo "=== All Automated Checks Passed! ✅ ==="
echo ""
echo "Next Steps:"
echo "1. Manually verify server starts: python -m gazebo_mcp.server"
echo "2. Check ROS2 connection: ros2 node list"
echo "3. Test health check with MCP client"
echo "4. If all pass, proceed to Phase 3"
echo ""
