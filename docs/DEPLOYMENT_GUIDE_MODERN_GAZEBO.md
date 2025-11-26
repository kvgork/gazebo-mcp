# Modern Gazebo Bridge Deployment Guide

> **Version**: 1.5.1
> **Date**: 2025-11-25
> **Status**: Production Ready
> **Test Coverage**: 11/11 integration tests passing (100%)

---

## Overview

This guide provides step-by-step instructions for deploying the Modern Gazebo adapter with ros_gz_bridge for the Gazebo MCP server.

### What You'll Get

- ✅ Full Modern Gazebo (Fortress/Garden/Harmonic) support
- ✅ ROS2 service integration via ros_gz_bridge
- ✅ 11 adapter methods fully functional
- ✅ Automated bridge startup and monitoring
- ✅ Production-ready configuration

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 22.04 (Jammy) or later
- **ROS2**: Humble or later
- **Gazebo**: Modern Gazebo (Fortress/Garden/Harmonic)
- **Python**: 3.10+

### Required Packages

```bash
# ROS2 Humble
sudo apt update
sudo apt install -y \
    ros-humble-ros-base \
    ros-humble-ros-gz-bridge \
    ros-humble-ros-gz-interfaces

# Modern Gazebo (if not already installed)
sudo apt install -y \
    ignition-gazebo6 \
    libignition-gazebo6-dev

# Python dependencies
pip install rclpy
```

### Verify Installation

```bash
# Check ROS2
ros2 --version
# Should show: ros2 doctor version X.X.X

# Check Gazebo
ign gazebo --version
# Should show: Gazebo Sim, version 6.X.X or later

# Check ros_gz_bridge
ros2 pkg list | grep ros_gz_bridge
# Should show: ros_gz_bridge

# Check ros_gz_interfaces
ros2 interface list | grep ros_gz_interfaces
# Should show multiple ros_gz_interfaces types
```

---

## Quick Start

### 1. Start Modern Gazebo

```bash
# Option A: With empty world (for testing)
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf

# Option B: With your custom world
ign gazebo -s -r /path/to/your/world.sdf

# Option C: GUI mode (for visualization)
ign gazebo /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf
```

**Flags:**
- `-s`: Server mode (no GUI)
- `-r`: Run simulation immediately

### 2. Start ros_gz_bridge

In a **new terminal**, start the bridge to expose Gazebo services to ROS2:

```bash
# Source ROS2
source /opt/ros/humble/setup.bash

# Start bridge with all required services
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
```

**Important**: Replace `empty` with your actual world name from the SDF file.

### 3. Verify Services

Wait 2-3 seconds, then verify services are available:

```bash
# List ROS2 services
ros2 service list | grep /world/

# Expected output:
# /world/empty/control
# /world/empty/create
# /world/empty/remove
# /world/empty/set_pose
```

### 4. Test Service Call (Optional)

```bash
# Test pause/unpause control
ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# Expected response:
# response:
# ros_gz_interfaces.srv.ControlWorld_Response(success=True)
```

### 5. Use MCP Server

The MCP server can now interact with Modern Gazebo via ROS2 services!

```python
from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
import rclpy
from rclpy.node import Node

# Initialize ROS2
rclpy.init()
node = Node('gazebo_mcp_node')

# Create adapter
adapter = ModernGazeboAdapter(
    node=node,
    default_world='empty',  # Match your world name
    timeout=20.0            # Generous timeout for initialization
)

# Now you can use all 11 adapter methods!
# spawn_entity, delete_entity, pause_simulation, etc.
```

---

## Production Deployment

### Automated Startup Script

Create a startup script for production use:

```bash
#!/bin/bash
# File: start_modern_gazebo_mcp.sh

set -e

# Configuration
WORLD_FILE="${GAZEBO_WORLD_FILE:-/usr/share/ignition/ignition-gazebo6/worlds/empty.sdf}"
WORLD_NAME="${GAZEBO_WORLD_NAME:-empty}"
BRIDGE_SERVICES=(
    "/world/${WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld"
    "/world/${WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity"
    "/world/${WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity"
    "/world/${WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose"
    "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
)

echo "Starting Modern Gazebo MCP system..."
echo "World: $WORLD_NAME"
echo "World file: $WORLD_FILE"

# Source ROS2
source /opt/ros/humble/setup.bash

# Start Gazebo in background
echo "Starting Gazebo..."
ign gazebo -s -r "$WORLD_FILE" > /tmp/gazebo.log 2>&1 &
GAZEBO_PID=$!
echo "Gazebo PID: $GAZEBO_PID"

# Wait for Gazebo to be ready
echo "Waiting for Gazebo to initialize..."
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if ign service -l 2>/dev/null | grep -q "/world/$WORLD_NAME/"; then
        echo "✓ Gazebo is ready!"
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ $elapsed -ge $timeout ]; then
    echo "ERROR: Gazebo failed to start within ${timeout}s"
    kill $GAZEBO_PID 2>/dev/null || true
    exit 1
fi

# Start bridge
echo "Starting ros_gz_bridge..."
ros2 run ros_gz_bridge parameter_bridge "${BRIDGE_SERVICES[@]}" > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
echo "Bridge PID: $BRIDGE_PID"

# Wait for services to be available
echo "Waiting for ROS2 services..."
timeout=15
elapsed=0
while [ $elapsed -lt $timeout ]; do
    service_count=$(ros2 service list 2>/dev/null | grep -c "/world/$WORLD_NAME/" || echo "0")
    if [ "$service_count" -ge 4 ]; then
        echo "✓ Bridge is ready! Found $service_count services"
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ $elapsed -ge $timeout ]; then
    echo "WARNING: Bridge services took longer than expected"
fi

# Warmup test
echo "Testing bridge connection..."
if timeout 5 ros2 service call "/world/$WORLD_NAME/control" ros_gz_interfaces/srv/ControlWorld \
    "{world_control: {pause: false}}" >/dev/null 2>&1; then
    echo "✓ Bridge is warm and functional!"
else
    echo "WARNING: Bridge warmup test failed, but services may still work"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Modern Gazebo MCP System Ready"
echo "════════════════════════════════════════════════════════════════"
echo "Gazebo PID: $GAZEBO_PID"
echo "Bridge PID: $BRIDGE_PID"
echo ""
echo "Available services:"
ros2 service list | grep "/world/" | head -10
echo ""
echo "To stop:"
echo "  kill $GAZEBO_PID $BRIDGE_PID"
echo "════════════════════════════════════════════════════════════════"

# Keep script running (optional)
# wait $GAZEBO_PID $BRIDGE_PID
```

**Usage:**

```bash
chmod +x start_modern_gazebo_mcp.sh

# Start with default empty world
./start_modern_gazebo_mcp.sh

# Start with custom world
GAZEBO_WORLD_FILE=/path/to/custom.sdf GAZEBO_WORLD_NAME=my_world ./start_modern_gazebo_mcp.sh
```

### Systemd Service (Optional)

For production servers, create a systemd service:

```ini
# File: /etc/systemd/system/gazebo-mcp.service
[Unit]
Description=Modern Gazebo MCP Service
After=network.target

[Service]
Type=forking
User=your_user
WorkingDirectory=/path/to/ros2_gazebo_mcp
Environment="GAZEBO_WORLD_NAME=empty"
ExecStart=/path/to/start_modern_gazebo_mcp.sh
ExecStop=/usr/bin/killall -SIGTERM ign ros2
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable gazebo-mcp
sudo systemctl start gazebo-mcp
sudo systemctl status gazebo-mcp
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GAZEBO_BACKEND` | `modern` | Backend type (must be 'modern') |
| `GAZEBO_WORLD_NAME` | `default` | World name from SDF file |
| `GAZEBO_TIMEOUT` | `20.0` | Service call timeout (seconds) |

### Adapter Configuration

```python
# Recommended settings
adapter = ModernGazeboAdapter(
    node=node,
    default_world='your_world_name',
    timeout=20.0  # Generous for bridge initialization
)
```

### Bridge Service List

**Required services** for full adapter functionality:

1. **ControlWorld** (`/world/{world}/control`) - Pause/unpause/reset simulation
2. **SpawnEntity** (`/world/{world}/create`) - Spawn models
3. **DeleteEntity** (`/world/{world}/remove`) - Delete models
4. **SetEntityPose** (`/world/{world}/set_pose`) - Move models

**Optional** (recommended):

5. **Clock** (`/clock`) - Simulation time synchronization

---

## Troubleshooting

### Issue: Services Don't Appear

**Symptoms:**
```bash
ros2 service list | grep /world/
# (empty output)
```

**Solutions:**

1. **Check Gazebo is running:**
   ```bash
   ign service -l | grep /world/
   # Should show Gazebo services
   ```

2. **Check bridge process:**
   ```bash
   ps aux | grep ros_gz_bridge
   # Should show running process
   ```

3. **Check bridge logs:**
   ```bash
   tail -f /tmp/bridge.log
   # Look for errors
   ```

4. **Verify world name matches:**
   - Bridge command uses `/world/WORLDNAME/...`
   - World name must match the `<world name="...">` in your SDF file

### Issue: Services Time Out

**Symptoms:**
```python
GazeboTimeoutError: Gazebo operation 'spawn_entity (world=empty)' timed out after 20.0s
```

**Solutions:**

1. **Increase timeout:**
   ```python
   adapter = ModernGazeboAdapter(node, timeout=30.0)
   ```

2. **Check bridge is warm:**
   ```bash
   # Test a simple service call first
   ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
     "{world_control: {pause: false}}"
   ```

3. **Verify ROS2 discovery:**
   ```bash
   # Check if service exists
   ros2 service type /world/empty/create
   # Should show: ros_gz_interfaces/srv/SpawnEntity
   ```

### Issue: "Service Not Available" Error

**Symptoms:**
```
GazeboNotRunningError: Service for spawn_entity not available. Is Modern Gazebo running?
```

**Solutions:**

1. **Wait for bridge warmup** (2-5 seconds after bridge starts)
2. **Check ROS2 domain ID** matches between bridge and client
3. **Verify packages installed:**
   ```bash
   dpkg -l | grep ros-humble-ros-gz
   # Should show ros-gz-bridge and ros-gz-interfaces
   ```

### Issue: Wrong World Name

**Symptoms:**
```
Services appear but calls fail with "world not found"
```

**Solutions:**

1. **Extract world name from SDF:**
   ```bash
   grep '<world name=' /path/to/world.sdf
   # Use this exact name in bridge and adapter
   ```

2. **Update bridge services:**
   ```bash
   # If world name is "my_world"
   ros2 run ros_gz_bridge parameter_bridge \
     "/world/my_world/control@ros_gz_interfaces/srv/ControlWorld" \
     # ... etc
   ```

3. **Update adapter:**
   ```python
   adapter = ModernGazeboAdapter(node, default_world='my_world')
   ```

### Issue: Bridge Crashes

**Symptoms:**
Bridge process terminates unexpectedly

**Solutions:**

1. **Check Gazebo is running first** (bridge needs Gazebo)
2. **Check service syntax:**
   ```bash
   # Correct format
   "/world/NAME/control@ros_gz_interfaces/srv/ControlWorld"

   # Wrong (missing @type)
   "/world/NAME/control"
   ```

3. **Check ROS2 environment:**
   ```bash
   source /opt/ros/humble/setup.bash
   env | grep ROS
   ```

---

## Performance Tuning

### Bridge Overhead

Typical latency: **<10ms** per service call

**Measured Performance:**
- Spawn entity: ~50-100ms (includes bridge + Gazebo processing)
- Delete entity: ~50-100ms
- Pause/unpause: ~10-20ms
- Set pose: ~20-50ms

### Optimization Tips

1. **Reduce bridge services** to only what you need
2. **Use local ROS_DOMAIN_ID** (avoid network discovery overhead)
3. **Increase timeout** for complex operations (spawning large models)
4. **Reuse adapter instances** (don't recreate for each operation)

---

## Testing

### Run Integration Tests

```bash
# From project root
./scripts/test_modern_adapter.sh
```

**Expected output:**
```
════════════════════════════════════════════════════════════════
  Test Summary
════════════════════════════════════════════════════════════════
Total Tests:  11
Passed:       11 ✅
Failed:       0 ❌

[SUCCESS] 🎉 All tests passed! Modern Gazebo adapter is fully functional.
```

### Manual Service Tests

```bash
# Test each service individually

# 1. Spawn a box
ros2 service call /world/empty/create ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {name: 'test_box', sdf: '<?xml version=\"1.0\"?><sdf version=\"1.8\"><model name=\"test_box\"><static>true</static><link name=\"link\"><visual name=\"visual\"><geometry><box><size>1 1 1</size></box></geometry></visual></link></model></sdf>'}}"

# 2. Pause simulation
ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: true}}"

# 3. Unpause simulation
ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# 4. Delete the box
ros2 service call /world/empty/remove ros_gz_interfaces/srv/DeleteEntity \
  "{entity: {name: 'test_box'}}"
```

---

## Migration from Classic Gazebo

If you're migrating from Classic Gazebo (gazebo_ros):

### Key Differences

| Aspect | Classic Gazebo | Modern Gazebo |
|--------|----------------|---------------|
| Package | `gazebo_ros` | `ros_gz_bridge` |
| Interfaces | `gazebo_msgs` | `ros_gz_interfaces` |
| Service paths | `/gazebo/*` | `/world/{world}/*` |
| Field names | `.xml`, `.initial_pose` | `.sdf`, `.pose` |
| Multi-world | No | Yes (world parameter required) |

### Migration Checklist

- [ ] Install `ros_gz_bridge` and `ros_gz_interfaces`
- [ ] Update service paths from `/gazebo/*` to `/world/{name}/*`
- [ ] Update adapter from `ClassicGazeboAdapter` to `ModernGazeboAdapter`
- [ ] Change field names (`.xml` → `.sdf`, etc.)
- [ ] Add world name parameter to all operations
- [ ] Update tests and scripts
- [ ] Verify bridge configuration

---

## Support & Resources

### Documentation
- [BRIDGE_INTEGRATION_SUCCESS.md](BRIDGE_INTEGRATION_SUCCESS.md) - Integration success summary
- [TROUBLESHOOTING_GUIDE_BRIDGE.md](TROUBLESHOOTING_GUIDE_BRIDGE.md) - Detailed troubleshooting
- [QUICK_REFERENCE_BRIDGE.md](QUICK_REFERENCE_BRIDGE.md) - Quick command reference

### Official Resources
- [ros_gz Documentation](https://docs.ros.org/en/rolling/p/ros_gz_bridge/)
- [Modern Gazebo Documentation](https://gazebosim.org/docs)
- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)

### Common Issues
See [TROUBLESHOOTING_GUIDE_BRIDGE.md](TROUBLESHOOTING_GUIDE_BRIDGE.md) for detailed solutions

---

## Changelog

### v1.5.1 (2025-11-25)
- ✅ Fixed critical ROS2 callback spinning issue
- ✅ Added service client lifecycle management
- ✅ Implemented bridge warmup health checks
- ✅ All 11 integration tests passing
- ✅ Production-ready deployment scripts

### v1.5.0 (2025-11-24)
- ✅ Initial Modern Gazebo adapter implementation
- ✅ Bridge configuration validated
- ✅ Basic integration tests

---

**Status**: ✅ Production Ready
**Test Coverage**: 11/11 tests passing (100%)
**Last Updated**: 2025-11-25
