# Lessons Learned: Modern Gazebo Bridge Integration

> **Project**: ROS2 Gazebo MCP Server - Modern Gazebo Migration
> **Date**: 2025-11-24
> **Context**: Integration testing and ros_gz_bridge configuration

---

## Table of Contents

1. [Critical Discoveries](#critical-discoveries)
2. [Architecture Understanding](#architecture-understanding)
3. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
4. [Testing Best Practices](#testing-best-practices)
5. [Development Workflow](#development-workflow)
6. [Debugging Techniques](#debugging-techniques)
7. [Future Development Guidelines](#future-development-guidelines)

---

## Critical Discoveries

### 1. Two Separate Transport Systems

**Discovery**: Modern Gazebo and ROS2 use completely separate communication systems.

**Implications**:
- Gazebo services exist in **Ignition Transport**, not ROS2 DDS
- Services do NOT automatically appear in ROS2
- An explicit bridge (ros_gz_bridge) is REQUIRED

**How to Verify**:
```bash
# Check Gazebo services (Ignition Transport)
ign service -l | grep /world/

# Check ROS2 services (DDS)
ros2 service list | grep /world/

# Without bridge: first command shows services, second shows nothing
# With bridge: both commands show services
```

**Lesson**: Always verify which transport system you're checking. Don't assume ROS2 visibility means Gazebo visibility.

---

### 2. Bridge Service Syntax

**Discovery**: Service bridging syntax is simple but must be exact.

**Correct Format**: `/service/path@ros_interface_type`

**Examples**:
```bash
# Services
/world/empty/control@ros_gz_interfaces/srv/ControlWorld
/world/empty/create@ros_gz_interfaces/srv/SpawnEntity
/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity
/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose

# Topics (note the different syntax)
/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
```

**Common Mistakes**:
- ❌ `/world/empty/control` (missing type specification)
- ❌ `/world/empty/control@ControlWorld` (missing package)
- ❌ `/world/empty/control@ros_gz_interfaces/ControlWorld` (missing srv/)
- ✅ `/world/empty/control@ros_gz_interfaces/srv/ControlWorld` (correct!)

**Lesson**: Use the full ROS2 interface path including `srv/` or `msg/` prefix.

---

### 3. Service Bridging Version Requirements

**Discovery**: Service bridging for SpawnEntity/DeleteEntity/SetEntityPose was added in March 2024.

**Details**:
- GitHub Issue: [gazebosim/ros_gz#711](https://github.com/gazebosim/ros_gz/issues/711)
- Backport PR: #380
- Required: ros-humble-ros-gz-bridge >= 0.244.14 (approximately)
- Our version: 0.244.20 (October 2024) ✅

**How to Check Your Version**:
```bash
dpkg -l | grep ros-humble-ros-gz-bridge
```

**Lesson**: If using Ubuntu apt packages, ensure you have updates from mid-2024 or later. Older versions may only support ControlWorld service.

---

### 4. World Name Must Match Exactly

**Discovery**: Service paths include the world name, which must match the SDF file.

**Example**:
```xml
<!-- worlds/empty.sdf -->
<world name="empty">  <!-- This name matters! -->
  ...
</world>
```

**Bridge Configuration Must Match**:
```bash
# If world is named "empty"
/world/empty/control@...   # ✅ Correct

# If world is named "default"
/world/default/control@...  # ✅ Correct

# Mismatch
/world/empty/control@...    # ❌ Wrong if world is "default"
```

**In Test Code**:
```python
# ❌ Bad: Hardcoded world name
await adapter.spawn_entity(..., world="default")

# ✅ Good: Use environment variable
world_name = os.environ.get('GAZEBO_WORLD_NAME', 'default')
await adapter.spawn_entity(..., world=world_name)
```

**Lesson**: Make world names configurable. Never hardcode them in tests or scripts.

---

### 5. Service Startup Timing

**Discovery**: Services don't appear instantly - there's a warmup period.

**Timeline**:
1. Gazebo starts: 8-10 seconds (can check with `ign service -l`)
2. Bridge starts: 2-3 seconds
3. ROS2 services appear: 1-2 seconds after bridge
4. **Total: 12-15 seconds minimum**

**Test Script Pattern**:
```bash
# Start Gazebo
ign gazebo -s -r world.sdf &
GAZEBO_PID=$!

# Wait for Gazebo (check Ignition Transport)
MAX_WAIT=30
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ign service -l 2>/dev/null | grep -q "/world/empty/"; then
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Start bridge
ros2 run ros_gz_bridge parameter_bridge ... &
BRIDGE_PID=$!

# Wait for ROS2 services
MAX_WAIT=15
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    COUNT=$(ros2 service list | grep -c "/world/" || echo "0")
    if [ "$COUNT" -ge 4 ]; then
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done
```

**Lesson**: Always wait for services before attempting calls. Use polling loops with timeouts.

---

## Architecture Understanding

### Transport Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                         │
│              (MCP Server, Python Scripts, etc.)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │   ROS2 Client   │
                  │  Service Calls  │
                  └────────┬────────┘
                           │
                           ▼
           ╔═══════════════════════════════════╗
           ║         ROS2 DDS Layer            ║
           ║    /world/empty/control (ROS2)    ║
           ║    ros_gz_interfaces/srv/...      ║
           ╚═══════════════╤═══════════════════╝
                           │
                           ▼
                  ┌────────────────┐
                  │ ros_gz_bridge  │
                  │ parameter_bridge│
                  └────────┬───────┘
                           │
                           ▼
           ╔═══════════════════════════════════╗
           ║     Ignition Transport Layer      ║
           ║   /world/empty/control (Gazebo)   ║
           ║      gz.msgs.WorldControl         ║
           ╚═══════════════╤═══════════════════╝
                           │
                           ▼
                  ┌────────────────┐
                  │ Modern Gazebo  │
                  │  (Simulation)  │
                  └────────────────┘
```

**Key Points**:
1. **Two separate message formats**: ros_gz_interfaces vs gz.msgs
2. **Bridge translates**: Between ROS2 types and Gazebo types
3. **Service discovery**: Happens at both layers independently
4. **No automatic passthrough**: Every service must be explicitly bridged

---

### Service Call Flow

**Successful Service Call Sequence**:

```
1. User Code:
   ros2 service call /world/empty/control ...

2. ROS2 Layer:
   - Looks up service in ROS2 service registry
   - Creates ros_gz_interfaces/srv/ControlWorld message
   - Sends request via DDS

3. ros_gz_bridge:
   - Receives ROS2 request
   - Converts ros_gz_interfaces → gz.msgs format
   - Calls Gazebo service via Ignition Transport

4. Gazebo:
   - Receives gz.msgs.WorldControl message
   - Executes simulation command (pause/unpause/etc.)
   - Returns gz.msgs.Boolean response

5. ros_gz_bridge:
   - Receives gz.msgs.Boolean
   - Converts → ros_gz_interfaces/srv/ControlWorld response
   - Returns to ROS2

6. User Code:
   - Receives response: success=True/False
```

**Lesson**: Understand the full stack. Debugging requires checking each layer.

---

## Common Pitfalls & Solutions

### Pitfall 1: "Service Not Available" Despite ros2 service list Showing It

**Symptom**:
```bash
$ ros2 service list | grep control
/world/empty/control

$ ros2 service call /world/empty/control ...
waiting for service to become available...
[timeout]
```

**Root Causes**:
1. **Bridge not running** - Services appear but aren't backed by bridge
2. **Gazebo not running** - Bridge can't reach backend
3. **World name mismatch** - Service exists but for wrong world

**Diagnosis Steps**:
```bash
# 1. Is Gazebo running?
ps aux | grep "ign gazebo" | grep -v grep
# OR
ign service -l | grep /world/

# 2. Is bridge running?
ps aux | grep parameter_bridge | grep -v grep

# 3. Check bridge logs
# (if logging to file, cat the log file)

# 4. Verify world name matches
ign service -l | grep /world/  # Shows actual world name
ros2 service list | grep /world/  # Should match
```

**Solutions**:
- Ensure Gazebo is running before bridge
- Ensure bridge is running before service calls
- Match world names in bridge config and SDF file
- Wait 15+ seconds after starting both

---

### Pitfall 2: Tests Fail with "Gazebo Not Running"

**Symptom**:
```python
GazeboNotRunningError: Gazebo simulation is not running
```

**Root Causes**:
1. **Testing wrong transport layer** - Checking ROS2 services with `ign service`
2. **Insufficient wait time** - Services not ready yet
3. **Premature cleanup** - Gazebo killed before tests run

**Solution Pattern**:
```python
# In test setup
def setUp(self):
    # Start Gazebo
    subprocess.Popen(['ign', 'gazebo', '-s', '-r', 'world.sdf'])

    # Wait for Gazebo (Ignition Transport check)
    for _ in range(30):
        result = subprocess.run(['ign', 'service', '-l'],
                              capture_output=True, text=True)
        if '/world/empty/' in result.stdout:
            break
        time.sleep(1)

    # Start bridge
    subprocess.Popen(['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge', ...])

    # Wait for ROS2 services
    for _ in range(15):
        result = subprocess.run(['ros2', 'service', 'list'],
                              capture_output=True, text=True)
        if result.stdout.count('/world/empty/') >= 4:
            break
        time.sleep(1)
```

---

### Pitfall 3: Timeout Errors in CI/CD

**Symptom**: Tests pass locally but fail in CI with timeouts.

**Root Causes**:
1. **CI machines slower** - 10-second timeout insufficient
2. **Parallel tests** - Resource contention
3. **Cold start** - First Gazebo launch takes longer

**Solutions**:
```python
# Make timeouts configurable
TIMEOUT = int(os.environ.get('GAZEBO_TIMEOUT', '20'))

# Add extra wait in CI
if os.environ.get('CI'):
    TIMEOUT *= 2

# Increase adapter timeout
adapter = ModernGazeboAdapter(node, timeout=TIMEOUT)
```

```bash
# In CI config (.github/workflows/test.yml)
env:
  GAZEBO_TIMEOUT: "30"
  ROS_DOMAIN_ID: "${{ github.run_id }}"  # Isolate tests
```

---

### Pitfall 4: Service Call Field Name Errors

**Symptom**:
```
Failed to populate field: 'SpawnEntity_Request' object has no attribute 'name'
```

**Root Cause**: Interface uses nested structure.

**Wrong**:
```python
# ❌ Flat structure
ros2 service call /world/empty/create ros_gz_interfaces/srv/SpawnEntity \
  "{name: 'box', sdf: '...'}"
```

**Correct**:
```python
# ✅ Nested under entity_factory
ros2 service call /world/empty/create ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {name: 'box', sdf: '...'}}"
```

**How to Discover Correct Structure**:
```bash
# Check interface definition
ros2 interface show ros_gz_interfaces/srv/SpawnEntity

# Output shows:
# ros_gz_interfaces/EntityFactory entity_factory  # <-- This is the field name!
#   string name
#   string sdf
#   ...
```

**Lesson**: Always check `ros2 interface show` for correct message structure.

---

## Testing Best Practices

### 1. Separate Lifecycle Management

**Pattern**: Manage Gazebo, bridge, and tests as separate lifecycle stages.

```bash
#!/bin/bash
# test_integration.sh

# Stage 1: Start Gazebo
start_gazebo() {
    ign gazebo -s -r worlds/test.sdf > /tmp/gazebo.log 2>&1 &
    GAZEBO_PID=$!
    wait_for_gazebo
}

# Stage 2: Start Bridge
start_bridge() {
    ros2 run ros_gz_bridge parameter_bridge ... > /tmp/bridge.log 2>&1 &
    BRIDGE_PID=$!
    wait_for_services
}

# Stage 3: Run Tests
run_tests() {
    python3 tests/test_integration.py
}

# Stage 4: Cleanup
cleanup() {
    kill $BRIDGE_PID $GAZEBO_PID 2>/dev/null
    pkill -9 -f "ign.*gazebo"
    pkill -9 -f "parameter_bridge"
}

# Execute with error handling
trap cleanup EXIT
start_gazebo || exit 1
start_bridge || exit 1
run_tests
```

**Benefits**:
- Clear separation of concerns
- Easy to debug which stage fails
- Proper cleanup even on failure
- Logs separated by component

---

### 2. Environment-Based Configuration

**Pattern**: Use environment variables for all configurable values.

```python
# config.py
import os

class GazeboTestConfig:
    """Test configuration from environment."""

    WORLD_NAME = os.environ.get('GAZEBO_WORLD_NAME', 'default')
    BACKEND = os.environ.get('GAZEBO_BACKEND', 'modern')
    TIMEOUT = float(os.environ.get('GAZEBO_TIMEOUT', '15.0'))

    # CI-specific adjustments
    if os.environ.get('CI'):
        TIMEOUT *= 2

    @classmethod
    def get_world_services(cls):
        """Get service paths for current world."""
        return [
            f"/world/{cls.WORLD_NAME}/control",
            f"/world/{cls.WORLD_NAME}/create",
            f"/world/{cls.WORLD_NAME}/remove",
            f"/world/{cls.WORLD_NAME}/set_pose",
        ]
```

**Usage in Tests**:
```python
class TestModernAdapter(unittest.TestCase):
    def setUp(self):
        self.config = GazeboTestConfig()
        self.adapter = ModernGazeboAdapter(
            node,
            default_world=self.config.WORLD_NAME,
            timeout=self.config.TIMEOUT
        )
```

---

### 3. Diagnostic Output

**Pattern**: Log detailed diagnostic information for debugging.

```python
def diagnose_gazebo_state():
    """Print diagnostic information about Gazebo state."""
    print("\n" + "="*60)
    print("GAZEBO DIAGNOSTIC INFORMATION")
    print("="*60)

    # Check Ignition Transport
    print("\n1. Ignition Transport Services:")
    result = subprocess.run(['ign', 'service', '-l'],
                          capture_output=True, text=True)
    ign_services = [s for s in result.stdout.split('\n') if '/world/' in s]
    print(f"   Found {len(ign_services)} services:")
    for svc in ign_services[:10]:
        print(f"     - {svc}")

    # Check ROS2 Services
    print("\n2. ROS2 Services:")
    result = subprocess.run(['ros2', 'service', 'list'],
                          capture_output=True, text=True)
    ros2_services = [s for s in result.stdout.split('\n') if '/world/' in s]
    print(f"   Found {len(ros2_services)} services:")
    for svc in ros2_services:
        print(f"     - {svc}")

    # Check Processes
    print("\n3. Running Processes:")
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'gazebo' in line.lower() or 'bridge' in line.lower():
            print(f"   {line}")

    # Environment
    print("\n4. Environment:")
    print(f"   GAZEBO_WORLD_NAME: {os.environ.get('GAZEBO_WORLD_NAME', 'not set')}")
    print(f"   GAZEBO_BACKEND: {os.environ.get('GAZEBO_BACKEND', 'not set')}")
    print(f"   ROS_DOMAIN_ID: {os.environ.get('ROS_DOMAIN_ID', 'not set')}")

    print("="*60 + "\n")
```

**Usage**:
```python
def setUp(self):
    start_gazebo_and_bridge()

    # Add diagnostic output
    if os.environ.get('DEBUG'):
        diagnose_gazebo_state()
```

---

### 4. Test Isolation

**Pattern**: Ensure tests don't interfere with each other.

```python
class TestModernAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start Gazebo once for all tests."""
        cls.gazebo_process = start_gazebo()
        cls.bridge_process = start_bridge()
        wait_for_services()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.bridge_process.terminate()
        cls.gazebo_process.terminate()
        cleanup_processes()

    def setUp(self):
        """Reset world state before each test."""
        # Reset simulation
        self.adapter.reset_world(world=self.config.WORLD_NAME)

        # Remove any test entities
        entities = self.adapter.list_entities(world=self.config.WORLD_NAME)
        for entity in entities:
            if entity.startswith('test_'):
                self.adapter.delete_entity(entity, world=self.config.WORLD_NAME)

    def test_spawn_entity(self):
        """Test spawning - world is clean from setUp."""
        ...
```

---

## Debugging Techniques

### Technique 1: Two-Terminal Debug

**Setup**: Use two terminals to observe both transport layers simultaneously.

**Terminal 1: Monitor Ignition Transport**
```bash
# Continuous monitoring
watch -n 1 'ign service -l | grep /world/'

# Or one-shot
while true; do
    clear
    echo "=== Ignition Transport Services ==="
    ign service -l | grep /world/
    echo ""
    echo "=== Gazebo Process ==="
    ps aux | grep "ign gazebo" | grep -v grep
    sleep 2
done
```

**Terminal 2: Monitor ROS2**
```bash
# Continuous monitoring
watch -n 1 'ros2 service list | grep /world/'

# Or detailed
while true; do
    clear
    echo "=== ROS2 Services ==="
    ros2 service list | grep /world/
    echo ""
    echo "=== Bridge Process ==="
    ps aux | grep parameter_bridge | grep -v grep
    sleep 2
done
```

---

### Technique 2: Incremental Service Testing

**Pattern**: Test services one at a time, starting with simplest.

```bash
# Step 1: Test control service (simplest - no parameters)
echo "Testing control service..."
timeout 5 ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

if [ $? -eq 0 ]; then
    echo "✅ Control service works"
else
    echo "❌ Control service failed - fix before proceeding"
    exit 1
fi

# Step 2: Test spawn service (complex - SDF parameter)
echo "Testing spawn service..."
timeout 5 ros2 service call /world/empty/create \
  ros_gz_interfaces/srv/SpawnEntity \
  "{entity_factory: {name: 'test', sdf: '...'}}"

if [ $? -eq 0 ]; then
    echo "✅ Spawn service works"
else
    echo "❌ Spawn service failed"
    exit 1
fi

# Continue with other services...
```

---

### Technique 3: Bridge Log Analysis

**Pattern**: Enable verbose bridge logging and analyze.

```bash
# Start bridge with debug output
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  --ros-args --log-level DEBUG \
  > /tmp/bridge_debug.log 2>&1 &

# Monitor logs
tail -f /tmp/bridge_debug.log

# Look for:
# - "Creating service bridge" messages
# - Type conversion errors
# - Connection establishment
# - Service call traces
```

**Common Log Messages**:
```
# Good signs:
[INFO] Creating ROS->GZ service bridge
[INFO] Service /world/empty/control is now available

# Warning signs:
[WARN] Failed to create service bridge
[ERROR] Type conversion failed
[ERROR] Service not found in Gazebo
```

---

### Technique 4: Interface Inspection

**Pattern**: Verify message structures before calling.

```bash
# Check service interface
ros2 interface show ros_gz_interfaces/srv/SpawnEntity

# Check message interface
ros2 interface show ros_gz_interfaces/msg/EntityFactory

# Generate example message (Python)
python3 << EOF
from ros_gz_interfaces.srv import SpawnEntity
from ros_gz_interfaces.msg import EntityFactory

# Create message
req = SpawnEntity.Request()
req.entity_factory.name = "test"
req.entity_factory.sdf = "<sdf>...</sdf>"

# Print structure
print(req)
EOF
```

---

## Development Workflow

### Recommended Development Sequence

**Phase 1: Environment Setup**
1. ✅ Verify Modern Gazebo installed
2. ✅ Verify ros_gz packages installed
3. ✅ Check versions (bridge >= 0.244.14)
4. ✅ Test basic Gazebo launch

**Phase 2: Manual Bridge Testing**
1. ✅ Start Gazebo manually
2. ✅ Verify Ignition services: `ign service -l`
3. ✅ Start bridge manually with one service
4. ✅ Verify ROS2 service appears: `ros2 service list`
5. ✅ Call service manually: `ros2 service call ...`
6. ✅ Add more services incrementally

**Phase 3: Script Automation**
1. ✅ Create shell script to start Gazebo
2. ✅ Add bridge startup with all services
3. ✅ Add waiting/polling logic
4. ✅ Test script multiple times
5. ✅ Add cleanup logic

**Phase 4: Test Integration**
1. ✅ Update test scripts to use new workflow
2. ✅ Fix hardcoded values (world names, etc.)
3. ✅ Add environment variable support
4. ✅ Run tests locally
5. ✅ Test in CI environment

**Phase 5: Documentation**
1. ✅ Document bridge requirements
2. ✅ Create setup guides
3. ✅ Document common issues
4. ✅ Add troubleshooting section

---

### Code Review Checklist

When reviewing Modern Gazebo integration code:

**Bridge Configuration**
- [ ] All required services included
- [ ] Syntax correct: `/path@package/srv/Type`
- [ ] World name configurable (not hardcoded)
- [ ] Clock topic included if needed

**Timing and Sequencing**
- [ ] Gazebo started before bridge
- [ ] Wait loops for service availability
- [ ] Timeouts configurable and sufficient (15-20s minimum)
- [ ] Proper error handling for timeouts

**World Name Handling**
- [ ] World name from environment variable
- [ ] Used consistently across scripts/tests
- [ ] Matches actual SDF world name

**Process Management**
- [ ] Process IDs captured
- [ ] Cleanup on success
- [ ] Cleanup on failure (trap/finally)
- [ ] All child processes killed

**Testing**
- [ ] Tests use environment config
- [ ] Diagnostic output available
- [ ] Test isolation (setUp/tearDown)
- [ ] Works in CI environment

---

## Future Development Guidelines

### Adding New Services

**Process**:
1. Identify Gazebo service name: `ign service -l`
2. Check if ROS interface exists: `ros2 interface list | grep ...`
3. Add to bridge configuration
4. Test manually before automation
5. Update documentation

**Example**: Adding /world/default/light service
```bash
# 1. Check Gazebo
$ ign service -l | grep light
/world/default/light/config

# 2. Check ROS interface
$ ros2 interface list | grep -i light
ros_gz_interfaces/srv/Light  # Found it!

# 3. Check interface structure
$ ros2 interface show ros_gz_interfaces/srv/Light

# 4. Add to bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/default/light/config@ros_gz_interfaces/srv/Light"

# 5. Test
ros2 service call /world/default/light/config ros_gz_interfaces/srv/Light "{...}"
```

---

### Supporting Multiple Gazebo Versions

**Pattern**: Version detection and conditional behavior.

```python
def get_gazebo_version():
    """Detect Modern Gazebo version."""
    result = subprocess.run(['ign', 'gazebo', '--version'],
                          capture_output=True, text=True)
    # Parse: "Gazebo Sim, version 6.17.0"
    match = re.search(r'version (\d+)\.(\d+)\.(\d+)', result.stdout)
    if match:
        return tuple(map(int, match.groups()))
    return (0, 0, 0)

def get_required_services(version):
    """Get service list based on Gazebo version."""
    base_services = [
        "/world/{world}/control@ros_gz_interfaces/srv/ControlWorld",
    ]

    # SpawnEntity added in Gazebo 6+
    if version >= (6, 0, 0):
        base_services.extend([
            "/world/{world}/create@ros_gz_interfaces/srv/SpawnEntity",
            "/world/{world}/remove@ros_gz_interfaces/srv/DeleteEntity",
            "/world/{world}/set_pose@ros_gz_interfaces/srv/SetEntityPose",
        ])

    return base_services
```

---

### Multi-World Support

**Pattern**: Maintain separate bridges for multiple worlds.

```python
class MultiWorldBridgeManager:
    """Manage bridges for multiple Gazebo worlds."""

    def __init__(self):
        self.bridges = {}

    def start_bridge_for_world(self, world_name):
        """Start bridge for specific world."""
        services = [
            f"/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld",
            f"/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity",
            f"/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity",
            f"/world/{world_name}/set_pose@ros_gz_interfaces/srv/SetEntityPose",
        ]

        process = subprocess.Popen([
            'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
            *services
        ])

        self.bridges[world_name] = process
        return process

    def stop_all_bridges(self):
        """Stop all bridges."""
        for bridge in self.bridges.values():
            bridge.terminate()
        self.bridges.clear()
```

---

### CI/CD Integration

**GitHub Actions Example**:
```yaml
name: Modern Gazebo Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-22.04

    env:
      GAZEBO_BACKEND: modern
      GAZEBO_TIMEOUT: "30"
      ROS_DOMAIN_ID: ${{ github.run_id }}

    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          sudo apt update
          sudo apt install -y \
            ros-humble-ros-gz-bridge \
            ros-humble-ros-gz-interfaces \
            ignition-gazebo6

      - name: Run integration tests
        run: |
          source /opt/ros/humble/setup.bash
          ./scripts/test_modern_adapter.sh

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs
          path: /tmp/*.log
```

---

## Quick Reference

### Essential Commands

```bash
# Check Gazebo running
ps aux | grep "ign gazebo" | grep -v grep
ign service -l | grep /world/

# Check bridge running
ps aux | grep parameter_bridge | grep -v grep

# Check services available
ros2 service list | grep /world/

# Test service call
ros2 service call /world/empty/control \
  ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"

# Check versions
dpkg -l | grep ros-humble-ros-gz-bridge
ign gazebo --version

# Kill everything
pkill -9 -f "ign.*gazebo"
pkill -9 -f "parameter_bridge"
pkill -9 ruby
```

---

### Common Error Messages and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "waiting for service to become available..." | Bridge not running or Gazebo stopped | Check both processes running, wait longer |
| "GazeboNotRunningError" | Checking wrong transport layer | Use `ign service -l` not `ros2 service list` |
| "Service call timed out" | Service not bridged or wrong world name | Check bridge config matches world name |
| "Failed to populate field" | Wrong message structure | Check `ros2 interface show` for correct fields |
| "No /world/ services found" | Bridge not started or crashed | Check bridge logs, restart bridge |

---

## Conclusion

The Modern Gazebo bridge integration requires understanding two separate transport systems, proper timing/sequencing, and careful configuration management. Follow these lessons to avoid common pitfalls and build robust integrations.

**Key Takeaways**:
1. ✅ Modern Gazebo ≠ ROS2 - explicit bridge required
2. ✅ Wait for services - 15+ seconds startup time
3. ✅ Make everything configurable - no hardcoded values
4. ✅ Test incrementally - start simple, add complexity
5. ✅ Monitor both layers - Ignition Transport and ROS2

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Related Documents**:
- `BRIDGE_INTEGRATION_SUCCESS.md` - Manual testing results
- `ARCHITECTURE_DECISION_MODERN_GAZEBO.md` - Architecture analysis
- `INTEGRATION_TESTING_GUIDE.md` - User setup guide
