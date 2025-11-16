# Troubleshooting Guide

Common issues and solutions for the Gazebo MCP Server.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [ROS2 Environment Issues](#ros2-environment-issues)
3. [Gazebo Issues](#gazebo-issues)
4. [Connection Issues](#connection-issues)
5. [Testing Issues](#testing-issues)
6. [Performance Issues](#performance-issues)
7. [Getting Help](#getting-help)

---

## Installation Issues

### Python Version Too Old

**Symptom**: `SyntaxError` or feature not available
```
SyntaxError: invalid syntax
```

**Solution**: Python 3.10+ required
```bash
python3 --version  # Check version
sudo apt install python3.10  # Install if needed
```

### Pip Dependencies Fail to Install

**Symptom**: `error: could not build wheel`

**Solution**: Install build dependencies
```bash
sudo apt install python3-dev python3-pip
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### MCP SDK Not Found

**Symptom**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**: Install MCP SDK
```bash
pip install mcp>=0.1.0
```

**Note**: MCP SDK may need to be installed from source during development:
```bash
git clone https://github.com/anthropics/mcp-sdk-python
cd mcp-sdk-python
pip install -e .
```

---

## ROS2 Environment Issues

### ROS2 Not Sourced

**Symptom**: `ROS_DISTRO` environment variable not set
```bash
echo $ROS_DISTRO
# (empty)
```

**Solution**: Source ROS2 setup
```bash
source /opt/ros/humble/setup.bash

# Add to ~/.bashrc for automatic sourcing
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

### ROS2 Package Not Found

**Symptom**: `Package 'gazebo_msgs' not found`

**Solution**: Install ROS2 Gazebo packages
```bash
sudo apt update
sudo apt install ros-humble-gazebo-ros-pkgs
```

### ROS2 Daemon Issues

**Symptom**: `DaemonNotRunningError` or timeout connecting

**Solution**: Restart ROS2 daemon
```bash
ros2 daemon stop
ros2 daemon start

# Verify it's running
ros2 daemon status
```

### Multiple ROS Versions Conflict

**Symptom**: Mixed ROS1/ROS2 errors

**Solution**: Clean environment and source only ROS2
```bash
# Start new shell or:
unset ROS_DISTRO
unset AMENT_PREFIX_PATH
source /opt/ros/humble/setup.bash
```

---

## Gazebo Issues

### Gazebo Not Found

**Symptom**: `gazebo: command not found` or `gz: command not found`

**Solution**: Install Gazebo
```bash
# For Gazebo Harmonic
sudo apt install gz-harmonic

# Verify installation
gz sim --version
```

### Gazebo Won't Start

**Symptom**: Gazebo crashes immediately or hangs

**Possible Causes**:
1. Graphics driver issues
2. Display not available
3. Port already in use

**Solutions**:

**Check graphics**:
```bash
# Test with verbose output
gz sim --verbose

# Try headless mode (no GUI)
gz sim -s --headless
```

**Check display**:
```bash
echo $DISPLAY
# Should show :0 or similar

# If empty, set it:
export DISPLAY=:0
```

**Check ports**:
```bash
# Check if port 11345 (Gazebo) is in use
sudo lsof -i :11345

# Kill if needed
killall gz
```

### TurtleBot3 Model Not Found

**Symptom**: `Model not found: turtlebot3_burger`

**Solution**: Install TurtleBot3 packages and set model path
```bash
# Install packages
sudo apt install ros-humble-turtlebot3-*

# Set environment variables
export TURTLEBOT3_MODEL=burger
export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH

# Add to ~/.bashrc
echo 'export TURTLEBOT3_MODEL=burger' >> ~/.bashrc
echo 'export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH' >> ~/.bashrc
```

### World File Not Found

**Symptom**: `Unable to find file: empty_world.world`

**Solution**: Use correct world file paths
```bash
# List available worlds
ls /opt/ros/humble/share/turtlebot3_gazebo/worlds/

# Use full path in code
world_path = "/opt/ros/humble/share/turtlebot3_gazebo/worlds/empty_world.world"
```

---

## Connection Issues

### MCP Server Won't Start

**Symptom**: Server exits immediately or won't initialize

**Debug steps**:
```bash
# Run with verbose logging
python -m gazebo_mcp.server --log-level DEBUG

# Check for errors in logs
tail -f logs/gazebo_mcp.log
```

**Common causes**:
- ROS2 not sourced → Source ROS2
- Port already in use → Check with `lsof -i :8080`
- Config file errors → Validate YAML syntax

### ROS2 Node Won't Connect

**Symptom**: `Failed to initialize ROS2 node`

**Solution**: Verify ROS2 is working
```bash
# Test ROS2
ros2 topic list

# Check node can be created
python3 -c "import rclpy; rclpy.init(); print('OK'); rclpy.shutdown()"

# Restart daemon if needed
ros2 daemon stop && ros2 daemon start
```

### Service Call Timeout

**Symptom**: `TimeoutError: Service /gazebo/spawn_entity not available`

**Solution**: Ensure Gazebo is running and services are available
```bash
# Check if Gazebo is running
ps aux | grep gazebo

# List available services
ros2 service list | grep gazebo

# Test service manually
ros2 service call /gazebo/spawn_entity gazebo_msgs/srv/SpawnEntity
```

### Connection Drops Randomly

**Symptom**: Connection works then fails intermittently

**Possible causes**:
1. Network issues (if using DDS)
2. Resource exhaustion
3. ROS2 daemon crashes

**Solutions**:
```bash
# Check system resources
top  # Look for high CPU/memory

# Check ROS2 daemon
ros2 daemon status

# Increase timeout values in config
# config/server_config.yaml
timeouts:
  service_call: 30.0  # Increase from 10.0
  connection: 10.0    # Increase from 5.0
```

---

## Testing Issues

### Tests Hang

**Symptom**: `pytest` runs but never completes

**Solution**: Add timeout
```bash
# Install pytest-timeout
pip install pytest-timeout

# Run with timeout
pytest --timeout=300  # 5 minutes
```

### Integration Tests Fail

**Symptom**: Tests fail with "Gazebo not available"

**Solutions**:

**Skip integration tests**:
```bash
pytest -m "not integration"
```

**Ensure Gazebo is running for integration tests**:
```python
# In tests/conftest.py
@pytest.fixture(scope="session")
def gazebo_instance():
    """Start Gazebo for integration tests"""
    # Check if Gazebo is already running
    if not is_gazebo_running():
        # Start Gazebo
        proc = subprocess.Popen(['gz', 'sim', '-s'])
        time.sleep(5)  # Wait for startup
        yield proc
        proc.terminate()
    else:
        yield None
```

### Mock Issues

**Symptom**: Mocks not working as expected

**Solution**: Use pytest-mock properly
```python
# Install
pip install pytest-mock

# Use mocker fixture
def test_with_mock(mocker):
    mock_bridge = mocker.patch('gazebo_mcp.bridge.GazeboBridgeNode')
    # ... test code
```

### Coverage Too Low

**Symptom**: Coverage below 80% requirement

**Solution**: Identify uncovered code
```bash
# Generate detailed coverage report
pytest --cov=gazebo_mcp --cov-report=html

# Open in browser
firefox htmlcov/index.html

# Focus on uncovered lines
pytest --cov=gazebo_mcp --cov-report=term-missing
```

---

## Performance Issues

### High Latency

**Symptom**: Tool calls take >1 second

**Debug**:
```python
import time

start = time.time()
result = await tool_call()
print(f"Duration: {time.time() - start:.2f}s")
```

**Common causes**:
- Network latency (DDS)
- Unoptimized queries
- Large data transfers

**Solutions**:
- Use caching for repeated queries
- Implement pagination
- Filter data before returning
- Use efficient QoS settings

### Memory Leaks

**Symptom**: Memory usage grows over time

**Debug**:
```python
# Install memory profiler
pip install memory-profiler

# Profile code
from memory_profiler import profile

@profile
def my_function():
    # ... code
```

**Common causes**:
- Unclosed ROS2 connections
- Cached data not cleaned
- Circular references

**Solutions**:
- Use context managers for connections
- Implement cache eviction
- Use weak references where appropriate

### CPU Usage High

**Symptom**: 100% CPU usage

**Common causes**:
- Busy waiting in loops
- No rate limiting
- Too many threads

**Solutions**:
```python
# Add rate limiting
import time
time.sleep(0.01)  # Don't spin at 100%

# Use async/await properly
await asyncio.sleep(0.1)

# Limit concurrent operations
semaphore = asyncio.Semaphore(5)
```

---

## Getting Help

### Before Asking for Help

1. **Run `verify_setup.sh`** - Check environment
2. **Check logs** - Look for error messages
3. **Search issues** - Check if already reported
4. **Minimal reproduction** - Isolate the problem

### Information to Provide

When reporting issues, include:

1. **Environment**:
   ```bash
   # Run this and include output
   echo "OS: $(lsb_release -d)"
   echo "ROS2: $ROS_DISTRO"
   gz sim --version
   python3 --version
   pip list | grep -E "mcp|pydantic|rclpy"
   ```

2. **Error message**: Full traceback
3. **Steps to reproduce**: Minimal example
4. **Expected vs actual**: What should happen vs what happens

### Resources

- **Documentation**: `/docs`
- **Examples**: `/examples`
- **Tests**: `/tests` (show expected usage)
- **Architecture**: `/docs/ARCHITECTURE.md`
- **Implementation Plan**: `/docs/implementation/IMPLEMENTATION_PLAN.md`

### Quick Diagnostic Commands

```bash
# Full environment check
./verify_setup.sh

# Check ROS2
echo $ROS_DISTRO
ros2 topic list
ros2 service list

# Check Gazebo
gz sim --version
gz topic list

# Check Python environment
python3 --version
pip list | grep mcp

# Check project
pytest tests/ -v --tb=short

# Check type hints
mypy src/gazebo_mcp --strict

# Check code style
ruff check src/
black src/ --check
```

---

## Common Error Messages

### `ImportError: cannot import name 'X' from 'mcp'`
→ MCP SDK version mismatch or not installed
→ Solution: `pip install --upgrade mcp`

### `rclpy._rclpy_pybind11.RCLError: failed to initialize`
→ ROS2 already initialized or not shut down properly
→ Solution: Restart Python process or call `rclpy.shutdown()`

### `FileNotFoundError: [Errno 2] No such file or directory: 'gazebo'`
→ Gazebo not in PATH
→ Solution: Install Gazebo or add to PATH

### `TypeError: __init__() missing required positional argument: 'node'`
→ Dependency injection issue
→ Solution: Pass required arguments to class constructor

### `asyncio.TimeoutError`
→ Operation took too long
→ Solution: Increase timeout or check if service is available

---

**Last Updated**: 2024-11-16
**Need more help?** Check `/docs/` or review test files for usage examples
