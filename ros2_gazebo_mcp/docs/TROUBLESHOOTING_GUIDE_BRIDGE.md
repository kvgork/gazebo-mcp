# Troubleshooting Guide: Modern Gazebo Bridge Integration

> **Step-by-step solutions for common issues**

---

## Table of Contents

1. [Service Call Timeouts](#service-call-timeouts)
2. [Services Not Appearing](#services-not-appearing)
3. [Integration Test Failures](#integration-test-failures)
4. [World Name Issues](#world-name-issues)
5. [Version Compatibility](#version-compatibility)
6. [Performance Problems](#performance-problems)
7. [CI/CD Issues](#cicd-issues)

---

## Service Call Timeouts

### Symptom

```bash
$ ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld "{world_control: {pause: false}}"
waiting for service to become available...
[hangs or times out]
```

### Diagnostic Steps

1. **Verify service is listed**:
   ```bash
   ros2 service list | grep /world/empty/control
   ```
   - ✅ If listed: Bridge created the service endpoint
   - ❌ If not listed: Bridge not started or configuration error

2. **Check if Gazebo is running**:
   ```bash
   ps aux | grep "ign gazebo" | grep -v grep
   ```
   - ❌ If no output: Gazebo stopped or crashed
   - ✅ If running: Check next step

3. **Verify Gazebo services exist**:
   ```bash
   ign service -l | grep /world/empty/
   ```
   - ❌ If no output: Gazebo not fully started or world name wrong
   - ✅ If showing services: Bridge connection issue

4. **Check if bridge is running**:
   ```bash
   ps aux | grep parameter_bridge | grep -v grep
   ```
   - ❌ If no output: Bridge crashed or not started
   - ✅ If running: Check bridge logs

5. **Inspect bridge logs**:
   ```bash
   # If logging to file
   tail -20 /tmp/bridge.log

   # If running in foreground, check terminal output
   ```
   Look for:
   - Connection errors
   - Type conversion failures
   - Service creation messages

### Solutions

#### Solution A: Restart Everything

```bash
# Kill all processes
pkill -9 -f "ign.*gazebo"
pkill -9 -f "parameter_bridge"
pkill -9 ruby

# Wait a moment
sleep 2

# Start Gazebo
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf > /tmp/gazebo.log 2>&1 &

# Wait for Gazebo
sleep 10

# Start bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  > /tmp/bridge.log 2>&1 &

# Wait for services
sleep 5

# Verify
ros2 service list | grep /world/empty/
```

#### Solution B: Check World Name Mismatch

```bash
# Get actual world name from Gazebo
ACTUAL_WORLD=$(ign service -l | grep /world/ | head -1 | cut -d'/' -f3)
echo "Actual world name: $ACTUAL_WORLD"

# Restart bridge with correct name
pkill -9 -f "parameter_bridge"
ros2 run ros_gz_bridge parameter_bridge \
  "/world/${ACTUAL_WORLD}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${ACTUAL_WORLD}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${ACTUAL_WORLD}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${ACTUAL_WORLD}/set_pose@ros_gz_interfaces/srv/SetEntityPose" &
```

#### Solution C: Increase Timeout

```bash
# Use explicit timeout
timeout 20 ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"
```

In Python:
```python
client = node.create_client(ControlWorld, '/world/empty/control')

# Wait longer
if not client.wait_for_service(timeout_sec=20.0):
    raise RuntimeError("Service not available after 20 seconds")

# Longer call timeout
future = client.call_async(request)
rclpy.spin_until_future_complete(node, future, timeout_sec=20.0)
```

---

## Services Not Appearing

### Symptom

```bash
$ ros2 service list | grep /world/
[no output]
```

But Gazebo is running:
```bash
$ ps aux | grep "ign gazebo" | grep -v grep
koen    12345  ... ign gazebo ...
```

### Diagnostic Steps

1. **Check if bridge is running**:
   ```bash
   ps aux | grep parameter_bridge | grep -v grep
   ```

2. **Check bridge was started correctly**:
   ```bash
   # View recent commands
   history | grep parameter_bridge | tail -1
   ```

3. **Check for bridge startup errors**:
   ```bash
   cat /tmp/bridge.log
   ```

### Solutions

#### Solution A: Bridge Not Started

Start the bridge:
```bash
source /opt/ros/humble/setup.bash

ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" &

# Wait and verify
sleep 5
ros2 service list | grep /world/
```

#### Solution B: Wrong Syntax in Bridge Config

Common mistakes:

```bash
# ❌ Wrong: Missing package
/world/empty/control@ControlWorld

# ❌ Wrong: Missing srv/
/world/empty/control@ros_gz_interfaces/ControlWorld

# ❌ Wrong: Typo in type name
/world/empty/control@ros_gz_interfaces/srv/WorldControl

# ✅ Correct:
/world/empty/control@ros_gz_interfaces/srv/ControlWorld
```

Check syntax:
```bash
# Verify interface exists
ros2 interface list | grep -i controlworld
# Should show: ros_gz_interfaces/srv/ControlWorld

# Use exact name in bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld"
```

#### Solution C: ROS Environment Not Sourced

```bash
# Bridge won't work without ROS environment
source /opt/ros/humble/setup.bash

# Verify ROS is sourced
env | grep ROS
# Should show: ROS_DISTRO=humble, ROS_VERSION=2, etc.

# Then start bridge
ros2 run ros_gz_bridge parameter_bridge ...
```

---

## Integration Test Failures

### Symptom

```python
GazeboNotRunningError: Gazebo simulation is not running
```

Or:
```python
TimeoutError: Service call timed out after 10.0s
```

### Diagnostic Steps

1. **Check test script startup sequence**:
   ```python
   # Look for proper ordering
   start_gazebo()
   wait_for_gazebo()  # ← Must wait!
   start_bridge()
   wait_for_services()  # ← Must wait!
   run_tests()
   ```

2. **Check wait implementations**:
   ```python
   # Bad: Fixed sleep (may be too short)
   time.sleep(10)

   # Good: Poll with timeout
   for _ in range(30):
       if check_ready():
           break
       time.sleep(1)
   ```

3. **Check what test uses to detect Gazebo**:
   ```python
   # ❌ Wrong: Checking ROS2 (bridge layer)
   result = subprocess.run(['ros2', 'service', 'list'])

   # ✅ Correct: Checking Ignition Transport (Gazebo layer)
   result = subprocess.run(['ign', 'service', '-l'])
   ```

### Solutions

#### Solution A: Fix Test Startup Sequence

```python
import subprocess
import time

class TestModernAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start Gazebo and bridge once for all tests."""

        # 1. Start Gazebo
        cls.gazebo_process = subprocess.Popen([
            'ign', 'gazebo', '-s', '-r',
            '/usr/share/ignition/ignition-gazebo6/worlds/empty.sdf'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 2. Wait for Gazebo (Ignition Transport check!)
        for _ in range(30):
            result = subprocess.run(['ign', 'service', '-l'],
                                  capture_output=True, text=True)
            if '/world/empty/' in result.stdout:
                break
            time.sleep(1)
        else:
            raise TimeoutError("Gazebo failed to start")

        # 3. Start bridge
        cls.bridge_process = subprocess.Popen([
            'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
            '/world/empty/control@ros_gz_interfaces/srv/ControlWorld',
            '/world/empty/create@ros_gz_interfaces/srv/SpawnEntity',
            '/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity',
            '/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose',
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 4. Wait for ROS2 services
        for _ in range(15):
            result = subprocess.run(['ros2', 'service', 'list'],
                                  capture_output=True, text=True)
            if result.stdout.count('/world/empty/') >= 4:
                break
            time.sleep(1)
        else:
            raise TimeoutError("Bridge services failed to appear")

    @classmethod
    def tearDownClass(cls):
        """Clean up processes."""
        cls.bridge_process.terminate()
        cls.gazebo_process.terminate()
        time.sleep(1)
        subprocess.run(['pkill', '-9', '-f', 'ign.*gazebo'],
                      stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-9', '-f', 'parameter_bridge'],
                      stderr=subprocess.DEVNULL)
```

#### Solution B: Increase Timeouts

```python
# In adapter initialization
adapter = ModernGazeboAdapter(
    node,
    default_world='empty',
    timeout=20.0  # ← Increased from 10.0
)

# Or via environment
timeout = float(os.environ.get('GAZEBO_TIMEOUT', '20.0'))
adapter = ModernGazeboAdapter(node, timeout=timeout)
```

#### Solution C: Add Diagnostic Output

```python
def test_spawn_entity(self):
    """Test spawning with diagnostics."""

    # Add diagnostics on failure
    try:
        result = await self.adapter.spawn_entity(...)
        self.assertTrue(result)
    except Exception as e:
        # Print diagnostic info
        print("\n=== DIAGNOSTIC INFO ===")
        print("Gazebo process:", subprocess.run(['ps', 'aux'],
                                                capture_output=True,
                                                text=True).stdout)
        print("\nIgnition services:", subprocess.run(['ign', 'service', '-l'],
                                                     capture_output=True,
                                                     text=True).stdout)
        print("\nROS2 services:", subprocess.run(['ros2', 'service', 'list'],
                                                capture_output=True,
                                                text=True).stdout)
        raise
```

---

## World Name Issues

### Symptom

Services appear but don't work:
```bash
$ ros2 service list | grep /world/
/world/default/control  # ← Bridge created "default"
/world/default/create

$ ign service -l | grep /world/
/world/empty/control    # ← Gazebo has "empty"
/world/empty/create
```

Service calls fail:
```bash
$ ros2 service call /world/default/control ...
[timeout - no backend to handle this]
```

### Solutions

#### Solution A: Fix World Name in SDF

If you want world to be "default":

```xml
<!-- worlds/test.sdf -->
<?xml version="1.0"?>
<sdf version="1.8">
  <world name="default">  <!-- ← Change from "empty" to "default" -->
    ...
  </world>
</sdf>
```

#### Solution B: Fix Bridge Configuration

If you want to keep world as "empty":

```bash
# Stop wrong bridge
pkill -9 -f parameter_bridge

# Start with correct world name
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" &
```

#### Solution C: Use Environment Variables

Make everything configurable:

```bash
# Set world name
export GAZEBO_WORLD_NAME="empty"

# Use in bridge startup
ros2 run ros_gz_bridge parameter_bridge \
  "/world/${GAZEBO_WORLD_NAME}/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/${GAZEBO_WORLD_NAME}/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/${GAZEBO_WORLD_NAME}/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/${GAZEBO_WORLD_NAME}/set_pose@ros_gz_interfaces/srv/SetEntityPose" &
```

In Python tests:
```python
world_name = os.environ.get('GAZEBO_WORLD_NAME', 'default')
adapter = ModernGazeboAdapter(node, default_world=world_name)

# Use in all test methods
await adapter.spawn_entity(..., world=world_name)  # ← Not hardcoded
```

---

## Version Compatibility

### Symptom

Only control service works, but spawn/delete/set_pose don't:

```bash
$ ros2 service list | grep /world/
/world/empty/control  # ← Only this one appears
```

### Diagnostic Steps

1. **Check ros_gz_bridge version**:
   ```bash
   dpkg -l | grep ros-humble-ros-gz-bridge
   ```

2. **Check if version is too old**:
   - Need: 0.244.14 or newer (approximately March 2024)
   - Have: Check output from step 1

### Solutions

#### Solution A: Update Packages

```bash
# Update package lists
sudo apt update

# Upgrade ros_gz packages
sudo apt install --only-upgrade \
  ros-humble-ros-gz-bridge \
  ros-humble-ros-gz-interfaces \
  ros-humble-ros-gz-sim

# Verify new version
dpkg -l | grep ros-humble-ros-gz-bridge
```

#### Solution B: Build from Source

If packages are still too old:

```bash
# Create workspace
mkdir -p ~/ros_gz_ws/src
cd ~/ros_gz_ws/src

# Clone ros_gz
git clone https://github.com/gazebosim/ros_gz.git -b humble

# Install dependencies
cd ~/ros_gz_ws
rosdep install -r --from-paths src -i -y --rosdistro humble

# Build
source /opt/ros/humble/setup.bash
colcon build --packages-select ros_gz_bridge ros_gz_interfaces

# Source workspace
source ~/ros_gz_ws/install/setup.bash

# Now use bridge from source
ros2 run ros_gz_bridge parameter_bridge ...
```

---

## Performance Problems

### Symptom

Services work but are very slow:
- Service calls take 5-10 seconds
- Gazebo response is sluggish
- High CPU usage

### Solutions

#### Solution A: Reduce Gazebo Load

```bash
# Use simpler world
ign gazebo -s -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf

# Limit physics update rate
ign gazebo -s -r --physics-engine-real-time-factor 0.5 world.sdf

# Reduce rendering (if running with GUI)
ign gazebo --render-engine ogre world.sdf
```

#### Solution B: Optimize Bridge

```bash
# Only bridge services you need
# Don't include clock if not required
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity"
  # Removed others
```

#### Solution C: Check System Resources

```bash
# Check CPU usage
top -p $(pgrep -f "ign gazebo")

# Check memory
free -h

# Check if system is swapping
vmstat 1

# If system is overloaded, reduce concurrent tests
# or increase timeout values
```

---

## CI/CD Issues

### Symptom

Tests pass locally but fail in CI:
```
Error: Service call timed out after 10.0s
```

### Solutions

#### Solution A: Increase CI Timeouts

```yaml
# .github/workflows/test.yml
env:
  GAZEBO_TIMEOUT: "30"  # ← Double local timeout
  BRIDGE_TIMEOUT: "20"
```

In code:
```python
timeout = float(os.environ.get('GAZEBO_TIMEOUT', '15.0'))
if os.environ.get('CI'):
    timeout *= 1.5  # ← Extra buffer in CI
```

#### Solution B: Add Diagnostic Output

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    ./scripts/test_modern_adapter.sh
  env:
    DEBUG: "1"  # ← Enable diagnostics

- name: Upload logs on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: test-logs
    path: |
      /tmp/gazebo.log
      /tmp/bridge.log
```

#### Solution C: Isolate Test Runs

```yaml
# .github/workflows/test.yml
env:
  ROS_DOMAIN_ID: ${{ github.run_id }}  # ← Unique per run
```

This prevents:
- Cross-talk between parallel CI jobs
- Interference from previous runs
- Service name conflicts

---

## General Debugging Procedure

When you encounter any issue:

1. **Run diagnostic script**:
   ```bash
   ./scripts/diagnose.sh
   # Or copy script from QUICK_REFERENCE_BRIDGE.md
   ```

2. **Check in order**:
   - Is Gazebo running? (`ps aux | grep ign`)
   - Are Gazebo services visible? (`ign service -l`)
   - Is bridge running? (`ps aux | grep parameter_bridge`)
   - Are ROS2 services visible? (`ros2 service list`)
   - Do world names match? (compare above outputs)

3. **Check logs**:
   ```bash
   tail -20 /tmp/gazebo.log
   tail -20 /tmp/bridge.log
   ```

4. **Try manual service call**:
   ```bash
   timeout 10 ros2 service call /world/empty/control \
     ros_gz_interfaces/srv/ControlWorld \
     "{world_control: {pause: false}}"
   ```

5. **If still stuck, clean slate**:
   ```bash
   # Kill everything
   pkill -9 -f "ign.*gazebo"
   pkill -9 -f "parameter_bridge"
   pkill -9 ruby

   # Wait
   sleep 3

   # Start fresh with manual steps
   ign gazebo -s -r worlds/empty.sdf &
   sleep 12
   ros2 run ros_gz_bridge parameter_bridge ... &
   sleep 5
   ros2 service list | grep /world/
   ```

---

## Getting Help

If you're still stuck after trying these solutions:

1. **Gather information**:
   ```bash
   # Run diagnostic
   ./scripts/diagnose.sh > diagnostic.txt

   # Capture logs
   cp /tmp/gazebo.log gazebo_error.log
   cp /tmp/bridge.log bridge_error.log

   # Get versions
   ign gazebo --version > versions.txt
   dpkg -l | grep ros-humble-ros-gz >> versions.txt
   ```

2. **Include in issue report**:
   - What you're trying to do
   - Exact commands run
   - Output from diagnostic script
   - Log files
   - Version information

3. **Check existing issues**:
   - [gazebosim/ros_gz issues](https://github.com/gazebosim/ros_gz/issues)
   - Search for similar problems

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Related**: See `LESSONS_LEARNED_BRIDGE_INTEGRATION.md` for root causes
