# Quick Reference: Modern Gazebo Bridge Integration

> **Quick lookup guide for common tasks and commands**

---

## Table of Contents

1. [Essential Commands](#essential-commands)
2. [Common Workflows](#common-workflows)
3. [Debugging Checklist](#debugging-checklist)
4. [Error Messages](#error-messages)
5. [Code Snippets](#code-snippets)

---

## Essential Commands

### Check Running Processes

```bash
# Check if Gazebo is running
ps aux | grep "ign gazebo" | grep -v grep

# Check if bridge is running
ps aux | grep parameter_bridge | grep -v grep

# Check all related processes
ps aux | grep -E "(gazebo|bridge|ruby)" | grep -v grep

# Kill all processes
pkill -9 -f "ign.*gazebo" && pkill -9 -f "parameter_bridge" && pkill -9 ruby
```

---

### Check Services

```bash
# Gazebo services (Ignition Transport)
ign service -l | grep /world/

# ROS2 services (DDS)
ros2 service list | grep /world/

# Count ROS2 services
ros2 service list | grep -c /world/

# Expected: 4 services (control, create, remove, set_pose)
```

---

### Start Gazebo

```bash
# Basic start
ign gazebo worlds/empty.sdf

# Headless with autostart
ign gazebo -s -r worlds/empty.sdf

# With verbose logging
ign gazebo -s -r --verbose 4 worlds/empty.sdf

# Background with logging
ign gazebo -s -r worlds/empty.sdf > /tmp/gazebo.log 2>&1 &
GAZEBO_PID=$!
```

---

### Start Bridge

```bash
# Single service
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld"

# All services
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"

# Background with logging
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
```

---

### Test Services

```bash
# Test control service
ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# Test spawn service
ros2 service call /world/empty/create \
  ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {
    name: 'test_box',
    sdf: '<?xml version=\"1.0\"?><sdf version=\"1.8\"><model name=\"test_box\"><static>true</static><link name=\"link\"><visual name=\"visual\"><geometry><box><size>1 1 1</size></box></geometry></visual></link></model></sdf>'
  }}"

# Test with timeout (recommended)
timeout 10 ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"
```

---

### Check Interface Definitions

```bash
# List all ros_gz_interfaces
ros2 interface list | grep ros_gz_interfaces

# Show service structure
ros2 interface show ros_gz_interfaces/srv/ControlWorld
ros2 interface show ros_gz_interfaces/srv/SpawnEntity
ros2 interface show ros_gz_interfaces/srv/DeleteEntity
ros2 interface show ros_gz_interfaces/srv/SetEntityPose

# Show message structure
ros2 interface show ros_gz_interfaces/msg/EntityFactory
```

---

### Check Versions

```bash
# Gazebo version
ign gazebo --version

# Bridge version
dpkg -l | grep ros-humble-ros-gz-bridge

# All ros_gz packages
dpkg -l | grep ros-humble-ros-gz
```

---

## Common Workflows

### Workflow 1: Complete Startup Sequence

```bash
#!/bin/bash
# complete_startup.sh

set -e

# 1. Start Gazebo
echo "Starting Gazebo..."
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf > /tmp/gazebo.log 2>&1 &
GAZEBO_PID=$!
echo "Gazebo PID: $GAZEBO_PID"

# 2. Wait for Gazebo
echo "Waiting for Gazebo..."
for i in {1..30}; do
    if ign service -l 2>/dev/null | grep -q "/world/empty/"; then
        echo "✓ Gazebo ready"
        break
    fi
    sleep 1
done

# 3. Start bridge
echo "Starting bridge..."
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge PID: $BRIDGE_PID"

# 4. Wait for services
echo "Waiting for ROS2 services..."
for i in {1..15}; do
    COUNT=$(ros2 service list 2>/dev/null | grep -c "/world/empty/" || echo "0")
    if [ "$COUNT" -ge 4 ]; then
        echo "✓ Services ready (found $COUNT)"
        break
    fi
    sleep 1
done

# 5. Verify
echo ""
echo "Services available:"
ros2 service list | grep /world/empty/

echo ""
echo "Ready! PIDs: Gazebo=$GAZEBO_PID Bridge=$BRIDGE_PID"
echo ""
echo "To cleanup:"
echo "  kill $BRIDGE_PID $GAZEBO_PID"
echo "  pkill -9 -f 'ign.*gazebo' && pkill -9 -f 'parameter_bridge'"
```

---

### Workflow 2: Quick Test

```bash
#!/bin/bash
# quick_test.sh

# Start everything
./complete_startup.sh

# Wait a bit
sleep 2

# Test control service
echo "Testing control service..."
timeout 5 ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}" && echo "✓ PASS" || echo "✗ FAIL"

# Test spawn service
echo "Testing spawn service..."
timeout 5 ros2 service call /world/empty/create \
  ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {name: 'test', sdf: '<?xml version=\"1.0\"?><sdf version=\"1.8\"><model name=\"test\"><static>true</static><link name=\"link\"><visual name=\"visual\"><geometry><box><size>0.5 0.5 0.5</size></box></geometry></visual></link></model></sdf>'}}" && echo "✓ PASS" || echo "✗ FAIL"

# Cleanup
echo ""
echo "Cleaning up..."
pkill -9 -f "ign.*gazebo"
pkill -9 -f "parameter_bridge"
pkill -9 ruby
```

---

### Workflow 3: Monitor Services

```bash
#!/bin/bash
# monitor_services.sh

# Continuous monitoring
watch -n 1 '
echo "=== Gazebo Services (Ignition Transport) ==="
ign service -l 2>/dev/null | grep /world/ | head -10
echo ""
echo "=== ROS2 Services (DDS) ==="
ros2 service list 2>/dev/null | grep /world/
echo ""
echo "=== Processes ==="
ps aux | grep -E "(ign gazebo|parameter_bridge)" | grep -v grep | awk "{print \$2, \$11, \$12, \$13}"
'
```

---

## Debugging Checklist

### When Services Don't Work

Run through this checklist in order:

```bash
# 1. Is Gazebo running?
ps aux | grep "ign gazebo" | grep -v grep
# If not: Start Gazebo

# 2. Can Gazebo services be seen?
ign service -l | grep /world/
# If not: Wait longer or restart Gazebo

# 3. Is bridge running?
ps aux | grep parameter_bridge | grep -v grep
# If not: Start bridge

# 4. Are ROS2 services visible?
ros2 service list | grep /world/
# If not: Check bridge configuration and logs

# 5. Do world names match?
echo "Gazebo world:"
ign service -l | grep /world/ | head -1 | cut -d'/' -f3
echo "ROS2 services:"
ros2 service list | grep /world/ | head -1 | cut -d'/' -f3
# If different: Fix world name in bridge config

# 6. Can you call the service?
timeout 5 ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"
# If timeout: Check bridge logs, restart bridge
```

---

### Diagnostic Script

```bash
#!/bin/bash
# diagnose.sh - Full diagnostic output

echo "=========================================="
echo "GAZEBO BRIDGE DIAGNOSTIC"
echo "=========================================="
echo ""

echo "1. GAZEBO PROCESS"
echo "------------------"
ps aux | grep "ign gazebo" | grep -v grep || echo "  ✗ Not running"
echo ""

echo "2. BRIDGE PROCESS"
echo "------------------"
ps aux | grep "parameter_bridge" | grep -v grep || echo "  ✗ Not running"
echo ""

echo "3. IGNITION TRANSPORT SERVICES"
echo "--------------------------------"
ign service -l 2>/dev/null | grep /world/ || echo "  ✗ No services"
echo ""

echo "4. ROS2 SERVICES"
echo "----------------"
ros2 service list 2>/dev/null | grep /world/ || echo "  ✗ No services"
echo ""

echo "5. VERSIONS"
echo "-----------"
echo "Gazebo: $(ign gazebo --version 2>&1 | head -1)"
echo "Bridge: $(dpkg -l 2>/dev/null | grep ros-humble-ros-gz-bridge | awk '{print $3}')"
echo ""

echo "6. ENVIRONMENT"
echo "--------------"
echo "GAZEBO_WORLD_NAME: ${GAZEBO_WORLD_NAME:-not set}"
echo "GAZEBO_BACKEND: ${GAZEBO_BACKEND:-not set}"
echo "ROS_DOMAIN_ID: ${ROS_DOMAIN_ID:-not set}"
echo ""

echo "7. RECENT LOGS"
echo "--------------"
if [ -f /tmp/gazebo.log ]; then
    echo "Gazebo log (last 5 lines):"
    tail -5 /tmp/gazebo.log
else
    echo "  No Gazebo log at /tmp/gazebo.log"
fi
echo ""
if [ -f /tmp/bridge.log ]; then
    echo "Bridge log (last 5 lines):"
    tail -5 /tmp/bridge.log
else
    echo "  No bridge log at /tmp/bridge.log"
fi
echo ""

echo "=========================================="
```

---

## Error Messages

### "waiting for service to become available..."

**Cause**: Service exists in `ros2 service list` but bridge isn't functioning.

**Solutions**:
```bash
# Check if bridge is actually running
ps aux | grep parameter_bridge | grep -v grep

# Check if Gazebo is running
ps aux | grep "ign gazebo" | grep -v grep

# Restart bridge
pkill -9 -f parameter_bridge
ros2 run ros_gz_bridge parameter_bridge [services...]

# Check bridge logs
tail -f /tmp/bridge.log
```

---

### "GazeboNotRunningError"

**Cause**: Code checking wrong transport layer or Gazebo not started.

**Solutions**:
```bash
# For Gazebo detection, use Ignition Transport
ign service -l | grep /world/
# NOT ros2 service list

# Verify Gazebo process
ps aux | grep "ign gazebo" | grep -v grep

# Check Gazebo logs
tail -f /tmp/gazebo.log
```

---

### "Failed to populate field: object has no attribute 'name'"

**Cause**: Wrong message structure in service call.

**Solutions**:
```bash
# Check correct interface structure
ros2 interface show ros_gz_interfaces/srv/SpawnEntity

# For SpawnEntity, use entity_factory wrapper:
ros2 service call /world/empty/create \
  ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {name: 'box', sdf: '...'}}"
#  ^^^^^^^^^^^^^^^ Required wrapper!
```

---

### "No /world/ services found"

**Cause**: Bridge not started or world name mismatch.

**Solutions**:
```bash
# Check what Gazebo actually calls the world
ign service -l | grep /world/ | head -1
# Extract world name: /world/NAME/...

# Update bridge to match
ros2 run ros_gz_bridge parameter_bridge \
  "/world/ACTUAL_NAME/control@..."
```

---

## Code Snippets

### Python: Complete Setup

```python
import subprocess
import time
import os

def setup_gazebo_with_bridge(world_name='empty'):
    """Start Gazebo and bridge, wait for services."""

    # Start Gazebo
    gazebo_process = subprocess.Popen([
        'ign', 'gazebo', '-s', '-r',
        f'/usr/share/ignition/ignition-gazebo6/worlds/{world_name}.sdf'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"Started Gazebo (PID: {gazebo_process.pid})")

    # Wait for Gazebo services
    for _ in range(30):
        result = subprocess.run(['ign', 'service', '-l'],
                              capture_output=True, text=True)
        if f'/world/{world_name}/' in result.stdout:
            print("✓ Gazebo ready")
            break
        time.sleep(1)
    else:
        raise TimeoutError("Gazebo failed to start")

    # Start bridge
    services = [
        f"/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld",
        f"/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity",
        f"/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity",
        f"/world/{world_name}/set_pose@ros_gz_interfaces/srv/SetEntityPose",
    ]

    bridge_process = subprocess.Popen([
        'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
        *services
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"Started bridge (PID: {bridge_process.pid})")

    # Wait for ROS2 services
    for _ in range(15):
        result = subprocess.run(['ros2', 'service', 'list'],
                              capture_output=True, text=True)
        count = result.stdout.count(f'/world/{world_name}/')
        if count >= 4:
            print(f"✓ Services ready (found {count})")
            break
        time.sleep(1)
    else:
        raise TimeoutError("Bridge services failed to appear")

    return gazebo_process, bridge_process

def cleanup(gazebo_process, bridge_process):
    """Clean up processes."""
    bridge_process.terminate()
    gazebo_process.terminate()
    subprocess.run(['pkill', '-9', '-f', 'ign.*gazebo'],
                  stderr=subprocess.DEVNULL)
    subprocess.run(['pkill', '-9', '-f', 'parameter_bridge'],
                  stderr=subprocess.DEVNULL)
```

---

### Python: Test Service Call

```python
import rclpy
from rclpy.node import Node
from ros_gz_interfaces.srv import ControlWorld
from ros_gz_interfaces.msg import WorldControl

def test_control_service(world_name='empty'):
    """Test control service call."""

    rclpy.init()
    node = Node('test_node')

    # Create client
    client = node.create_client(
        ControlWorld,
        f'/world/{world_name}/control'
    )

    # Wait for service
    if not client.wait_for_service(timeout_sec=10.0):
        raise RuntimeError("Service not available")

    # Create request
    request = ControlWorld.Request()
    request.world_control.pause = False

    # Call service
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)

    # Get result
    if future.done():
        result = future.result()
        print(f"Success: {result.success}")
        return result.success
    else:
        raise RuntimeError("Service call timed out")

    # Cleanup
    node.destroy_node()
    rclpy.shutdown()
```

---

### Bash: Environment Configuration

```bash
# config.sh - Source this before running scripts

# World configuration
export GAZEBO_WORLD_NAME="empty"
export GAZEBO_BACKEND="modern"

# Timeouts (in seconds)
export GAZEBO_STARTUP_TIMEOUT=30
export BRIDGE_STARTUP_TIMEOUT=15
export SERVICE_CALL_TIMEOUT=10

# Paths
export GAZEBO_WORLD_PATH="/usr/share/ignition/ignition-gazebo6/worlds"
export LOG_DIR="/tmp"

# ROS configuration
export ROS_DOMAIN_ID="${CI_JOB_ID:-0}"  # Isolate in CI

# Debug
export GAZEBO_VERBOSE="${DEBUG:+4}"  # Verbose if DEBUG set

# Helper function
start_with_config() {
    echo "Starting with configuration:"
    echo "  World: $GAZEBO_WORLD_NAME"
    echo "  Backend: $GAZEBO_BACKEND"
    echo "  Timeouts: Gazebo=$GAZEBO_STARTUP_TIMEOUT Bridge=$BRIDGE_STARTUP_TIMEOUT"

    ign gazebo -s -r \
        ${GAZEBO_VERBOSE:+--verbose $GAZEBO_VERBOSE} \
        "$GAZEBO_WORLD_PATH/${GAZEBO_WORLD_NAME}.sdf" \
        > "$LOG_DIR/gazebo.log" 2>&1 &
}
```

---

## Summary

**Most Common Commands**:
```bash
# Start everything
ign gazebo -s -r worlds/empty.sdf &
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" &

# Wait 15 seconds

# Test
ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# Cleanup
pkill -9 -f "ign.*gazebo" && pkill -9 -f "parameter_bridge"
```

**Remember**:
- Wait 15+ seconds after starting everything
- World names must match everywhere
- Use `ign service -l` to check Gazebo, `ros2 service list` for ROS2
- Check both processes are running before debugging

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**See Also**: `LESSONS_LEARNED_BRIDGE_INTEGRATION.md` for detailed explanations
