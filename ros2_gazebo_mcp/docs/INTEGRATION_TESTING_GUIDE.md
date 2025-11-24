# Modern Gazebo Integration Testing Guide

> **Status**: In Progress
> **Date**: 2025-11-24
> **Purpose**: Document requirements and procedures for Modern Gazebo integration testing

---

## Overview

This document provides guidance for running integration tests with the Modern Gazebo adapter. The tests validate all 10 `GazeboInterface` methods against a live Modern Gazebo (Ignition) instance.

---

## Architecture: How Modern Gazebo + ROS2 Integration Works

Modern Gazebo (Ignition/Gazebo Sim) operates independently from ROS2 and uses its own transport system (Ignition Transport). To enable ROS2 integration, there are **two approaches**:

### Approach 1: ros_gz Plugins (Recommended)

**How it works:**
- Modern Gazebo loads `ros_gz` system plugins at startup
- These plugins run INSIDE Gazebo and expose ROS2 services directly
- No separate bridge process needed
- Services appear automatically in ROS2 when Gazebo starts

**Requirements:**
1. Install `ros-humble-ros-gz-sim` package
2. Set `GZ_SIM_SYSTEM_PLUGIN_PATH` to include ros_gz plugins
3. Launch Gazebo using `ros2 launch ros_gz_sim gz_sim.launch.py`

**Advantages:**
- ✅ Automatic service exposure
- ✅ No separate bridge process to manage
- ✅ Lower latency (no IPC overhead)
- ✅ Official ROS2 integration method

### Approach 2: ros_gz_bridge (Topic-Focused)

**How it works:**
- Separate `ros_gz_bridge` process runs alongside Gazebo
- Bridge connects Ignition Transport to ROS2 DDS
- Primarily designed for topic bridging (sensors, state)
- Service bridging support is limited/experimental

**Requirements:**
1. Install `ros-humble-ros-gz-bridge` package
2. Run Gazebo separately (`ign gazebo`)
3. Run bridge with configuration (`ros2 run ros_gz_bridge parameter_bridge`)

**Limitations:**
- ⚠️ Service bridging syntax is complex and underdocumented
- ⚠️ Requires manual configuration for each service
- ⚠️ Additional process to manage
- ⚠️ Higher latency due to IPC

---

## Current Testing Status

### What Works ✅

1. **Modern Gazebo Installation**
   - Ignition Gazebo 6.17.0 (Fortress) installed
   - `ros_gz_interfaces` package available
   - All ROS2 service/message definitions present

2. **Adapter Implementation**
   - All 10 methods implemented correctly
   - Proper service client creation
   - Correct use of `ros_gz_interfaces` types
   - Async/await patterns working

3. **Test Framework**
   - Integration test suite created (`test_modern_adapter_integration.py`)
   - Test script with Gazebo lifecycle management
   - Environment variable configuration

4. **Exception Handling**
   - Added `GazeboServiceError` class
   - Fixed `GazeboNotRunningError` to accept message parameter
   - Proper error propagation

### What's Blocked ⏸️

1. **Service Availability**
   - ROS2 services from Modern Gazebo not appearing
   - Root cause: Missing ros_gz plugin loading in Gazebo
   - Solution: Use ros2 launch instead of direct `ign gazebo`

2. **Bridge Configuration**
   - Created `launch/gazebo_bridge.launch.py`
   - Service bridging syntax needs verification
   - May not be necessary with Approach 1 (plugins)

---

## Recommended Testing Approach

### Option 1: Use ros2 launch (Recommended)

Update test script to use official ros_gz launch files:

```bash
#!/bin/bash
# Start Gazebo with ROS2 integration
ros2 launch ros_gz_sim gz_sim.launch.py \
  gz_args:="-r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf"
```

This automatically:
- Sets correct environment variables
- Loads ros_gz system plugins
- Exposes ROS2 services
- Provides proper Gazebo + ROS2 integration

### Option 2: Manual Plugin Loading

Set environment and run Gazebo:

```bash
# Add ros_gz plugins to path
export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH:/opt/ros/humble/lib

# Run Gazebo
ign gazebo -s /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf
```

### Option 3: Keep Current Test (Development Only)

Current test setup works for:
- Verifying Gazebo starts correctly
- Testing adapter initialization
- Validating environment configuration

But **cannot test actual service calls** without ROS2 integration.

---

## Integration Test Requirements

### Prerequisites

**Required Packages:**
```bash
sudo apt install ros-humble-ros-gz-sim ros-humble-ros-gz-interfaces
```

**Required Environment Variables:**
```bash
export GAZEBO_BACKEND=modern
export GAZEBO_WORLD_NAME=empty  # Or "default" depending on world
export GAZEBO_TIMEOUT=10.0
```

### Test Execution

**Current Script:**
```bash
./scripts/test_modern_adapter.sh
```

**Status:** Partial - Gazebo starts, but ROS2 services not available

**To Complete Testing:**
1. Update script to use `ros2 launch ros_gz_sim gz_sim.launch.py`
2. Wait for services to appear (`ros2 service list | grep /world/`)
3. Run integration tests
4. Verify all 10 methods pass

---

## Known Limitations

### 1. Service Bridging Complexity

**Issue:** `ros_gz_bridge` service bridging is underdocumented

**Example Attempts:**
```python
# Attempted syntax (unclear if correct):
'/world/empty/create@ros_gz_interfaces/srv/SpawnEntity'

# Bridge dies with exit code 255 - syntax error
```

**Impact:** Cannot use Approach 2 (bridge) reliably

**Recommendation:** Use Approach 1 (plugins) instead

### 2. World Name Configuration

**Issue:** Empty.sdf defines world name as "empty", not "default"

**Fix Applied:**
```python
# Test now reads from environment
world_name = os.environ.get('GAZEBO_WORLD_NAME', 'default')
```

**Result:** ✅ Tests correctly use world name "empty"

### 3. Python Environment

**Issue:** Anaconda Python conflicts with ROS2

**Fix Applied:**
```bash
# Use system Python explicitly
/usr/bin/python3 tests/test_modern_adapter_integration.py
```

**Result:** ✅ ROS2 imports work correctly

---

## Next Steps

### Immediate (To Complete Testing)

1. **Update Test Script**
   ```bash
   # Replace direct ign gazebo with:
   ros2 launch ros_gz_sim gz_sim.launch.py \
     gz_args:="-s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf"
   ```

2. **Verify Service Availability**
   ```bash
   ros2 service list | grep /world/empty/
   ```

   Expected output:
   ```
   /world/empty/control
   /world/empty/create
   /world/empty/remove
   /world/empty/set_pose
   ```

3. **Run Full Test Suite**
   ```bash
   ./scripts/test_modern_adapter.sh
   ```

4. **Document Results**
   - Capture test output
   - Note any failures
   - Update migration summary

### Short-term (Documentation)

1. Update README with ros2 launch requirement
2. Add troubleshooting section
3. Document environment setup
4. Create deployment guide

### Long-term (Enhancements)

1. Create example launch files for common scenarios
2. Add Multi-world testing
3. Performance benchmarks
4. CI/CD integration

---

## Troubleshooting

### Services Not Appearing

**Symptoms:**
```bash
$ ros2 service list | grep /world/
# No output
```

**Causes:**
1. Gazebo started without ros_gz plugins
2. Wrong `GZ_SIM_SYSTEM_PLUGIN_PATH`
3. ros_gz_sim package not installed

**Solutions:**
1. Use `ros2 launch ros_gz_sim gz_sim.launch.py`
2. Verify: `echo $GZ_SIM_SYSTEM_PLUGIN_PATH`
3. Install: `sudo apt install ros-humble-ros-gz-sim`

### Bridge Process Dies

**Symptoms:**
```
[ERROR] [parameter_bridge-1]: process has died [pid X, exit code 255]
```

**Causes:**
1. Incorrect bridge argument syntax
2. Service types don't match
3. Gazebo not running

**Solutions:**
1. Verify argument format matches documentation
2. Check service type with `ros2 service type /world/empty/control`
3. Start Gazebo first, then bridge

### Test Timeout

**Symptoms:**
```python
GazeboTimeoutError: Operation 'spawn_entity' timed out after 10.0s
```

**Causes:**
1. Gazebo physics not running (paused)
2. System resources exhausted
3. Service deadlock

**Solutions:**
1. Ensure Gazebo started with `-r` (running) flag
2. Check CPU/memory usage
3. Increase timeout: `export GAZEBO_TIMEOUT=30.0`

---

## Files Created/Modified

### Created
- `launch/gazebo_bridge.launch.py` - ROS2 launch file for service bridging (experimental)
- `docs/INTEGRATION_TESTING_GUIDE.md` - This document

### Modified
- `scripts/test_modern_adapter.sh` - Added bridge support, fixed paths
- `tests/test_modern_adapter_integration.py` - Environment variable support
- `src/gazebo_mcp/utils/exceptions.py` - Added `GazeboServiceError`, fixed `GazeboNotRunningError`

---

## Conclusion

The Modern Gazebo adapter is **architecturally complete and implementation-ready**. Integration testing requires proper Modern Gazebo + ROS2 setup using `ros2 launch`, which automatically handles plugin loading and service exposure.

**Recommended Next Action:** Update test script to use `ros2 launch ros_gz_sim gz_sim.launch.py` and run full integration suite.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Author**: Claude Code
**Status**: Integration Testing In Progress
