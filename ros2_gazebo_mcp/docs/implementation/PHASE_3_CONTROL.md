# Phase 3: Gazebo Connection & Control Tools

**Status**: ✅ COMPLETE (Implementation Date: 2024-11-16)
**Estimated Duration**: 5-7 days
**Prerequisites**: Phase 2 Complete

---

## Quick Reference

**What you'll build**: MCP tools for Gazebo simulation control, model management, sensor access, and robot control

**Tasks**: 30 across 4 modules
- Module 3.1: Simulation Control (6 tools)
- Module 3.2: Model Management (8 tools)
- Module 3.3: Sensor Integration (8 tools)
- Module 3.4: Robot Control (6 tools)

**Success criteria**: Can spawn TurtleBot3, read all sensor types, control movement, manage simulation lifecycle

**Verification**:
```bash
./verify_phase3.sh  # Automated verification
pytest tests/integration/test_turtlebot3_spawn.py  # Integration test
```

**Key deliverables**:
- ✅ Full simulation control (start, stop, pause, reset)
- ✅ TurtleBot3 spawning and management
- ✅ Multi-sensor data access (camera, lidar, IMU, GPS)
- ✅ Robot velocity and joint control
- ✅ Integration tests with real Gazebo

---

## Learning Objectives

By completing this phase, you will understand:

1. **Gazebo Process Management**
   - How to launch and manage Gazebo subprocess
   - Graceful shutdown and cleanup
   - Port and resource management

2. **ROS2 Service Interaction**
   - How to discover and call Gazebo services
   - Service timeout and retry handling
   - Service availability waiting

3. **Sensor Data Processing**
   - How to subscribe to ROS2 sensor topics
   - Message type handling (Image, LaserScan, Imu)
   - Data format conversion and validation

4. **Model Lifecycle Management**
   - How to spawn models from SDF/URDF
   - Model state querying and setting
   - TurtleBot3 model integration

5. **Real-time Robot Control**
   - How to publish velocity commands
   - Joint control and state management
   - Safety limits and validation

---

## Core Principles for This Phase

### 1. Gather → Act → Verify → Repeat

**Gather Context**:
- Read module documentation completely
- Review Gazebo and ROS2 service APIs
- Check existing sensor message formats
- Study TurtleBot3 model structure

**Act (Implement)**:
- Write tests FIRST for each tool
- Implement tool with full type hints
- Add comprehensive error handling
- Document sensor data formats

**Verify (Critical)**:
- Unit tests pass for each tool
- Integration tests with real Gazebo pass
- Type checking passes (mypy --strict)
- Manual testing with TurtleBot3

**Repeat**:
- Iterate on failing tests
- Refine error messages
- Optimize performance
- Commit when green

### 2. Write Tests First (TDD)

```python
# ALWAYS start with the test
def test_spawn_turtlebot3():
    """Test TurtleBot3 spawning"""
    result = await spawn_model(
        model_name="test_robot",
        model_type="turtlebot3_burger",
        x=0.0, y=0.0, z=0.1
    )
    assert result['success'] == True
    assert result['model_name'] == "test_robot"

# THEN implement
async def spawn_model(...):
    # Implementation
```

### 3. Handle Gazebo-Specific Errors

Common issues to handle:
- Gazebo not running → Clear error with instructions
- Service timeout → Retry with exponential backoff
- Model already exists → Descriptive error
- Invalid SDF → Validation before spawning
- Sensor topic not available → Wait or fail gracefully

### 4. Validate All Inputs

```python
# Example validation
def validate_spawn_parameters(model_name: str, x: float, y: float, z: float):
    """Validate spawn parameters"""
    if not model_name or not model_name.strip():
        raise ValidationError("model_name cannot be empty")

    if not (-100 <= x <= 100 and -100 <= y <= 100):
        raise ValidationError(
            f"Position out of bounds: x={x}, y={y}. "
            f"Valid range: -100 to 100 meters"
        )

    if z < 0:
        raise ValidationError(f"Height z={z} cannot be negative")
```

### 5. Provide Actionable Errors

```python
# ❌ Bad
raise Exception("Failed to spawn")

# ✅ Good
raise ModelSpawnError(
    f"Failed to spawn model '{model_name}'. "
    f"Gazebo service '/spawn_entity' not available. "
    f"Ensure Gazebo is running with: gz sim -s"
)
```

---

## Overview

Implement MCP tools for controlling Gazebo simulations, managing models (especially TurtleBot3), accessing sensors, and controlling robots.

## Objectives

1. Create simulation control tools (start, stop, pause, reset)
2. Implement model management (spawn, delete, list, state)
3. Build sensor integration (camera, lidar, IMU, GPS)
4. Create robot controllers (velocity, joint control)
5. Add TurtleBot3-specific features

---

## Module 3.1: Simulation Control Tools

**File**: `src/gazebo_mcp/tools/simulation_control.py`

### Tasks (0/6)

- [ ] **Tool**: `start_simulation` - Launch Gazebo with world file
- [ ] **Tool**: `stop_simulation` - Gracefully shutdown Gazebo
- [ ] **Tool**: `pause_simulation` - Pause physics
- [ ] **Tool**: `unpause_simulation` - Resume physics
- [ ] **Tool**: `reset_simulation` - Reset world to initial state
- [ ] **Tool**: `set_physics_properties` - Configure gravity, timestep, etc.

### Implementation Example

```python
@mcp_tool(
    name="start_simulation",
    description="Launch Gazebo simulation with specified world"
)
async def start_simulation(
    world_name: str = "empty_world",
    gui: bool = True,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Start Gazebo simulation.

    Args:
        world_name: Name of world file (without .world extension)
        gui: Launch with GUI
        verbose: Enable verbose output

    Returns:
        Success status and process info
    """
    # Implementation
    pass
```

---

## Module 3.2: Model Management Tools

**File**: `src/gazebo_mcp/tools/model_management.py`

### Tasks (0/8)

- [ ] **Tool**: `spawn_model` - Spawn model from SDF/URDF
- [ ] **Tool**: `delete_model` - Remove model from simulation
- [ ] **Tool**: `list_models` - Get all active models
- [ ] **Tool**: `get_model_state` - Query model pose and velocity
- [ ] **Tool**: `set_model_state` - Set model pose and velocity
- [ ] **Helper**: Load TurtleBot3 SDF templates
- [ ] **Helper**: Validate SDF/URDF before spawning
- [ ] **Helper**: Generate unique model names

### TurtleBot3 Models

Support for:
- `turtlebot3_burger` - Basic model with LiDAR
- `turtlebot3_waffle` - Larger with camera
- `turtlebot3_waffle_pi` - Waffle with Raspberry Pi camera

### Implementation Example

```python
@mcp_tool(
    name="spawn_model",
    description="Spawn a robot or object model in Gazebo"
)
async def spawn_model(
    model_name: str,
    model_type: str = "turtlebot3_burger",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    yaw: float = 0.0
) -> Dict[str, Any]:
    """
    Spawn model in simulation.

    Args:
        model_name: Unique name for model instance
        model_type: Type of model (turtlebot3_burger, etc.)
        x, y, z: Initial position
        yaw: Initial orientation (radians)

    Returns:
        Success status and model info
    """
    # Load model SDF
    sdf_xml = load_model_sdf(model_type)

    # Spawn via bridge
    result = await bridge.spawn_entity(
        name=model_name,
        xml=sdf_xml,
        initial_pose={'x': x, 'y': y, 'z': z, 'yaw': yaw}
    )

    return result
```

---

## Module 3.3: Sensor Integration Tools

**File**: `src/gazebo_mcp/tools/sensor_tools.py`

### Tasks (0/8)

- [ ] **Tool**: `list_sensors` - Query available sensors on model
- [ ] **Tool**: `get_sensor_data` - Read sensor data
- [ ] **Tool**: `configure_sensor` - Modify sensor parameters
- [ ] **Parser**: Camera image data (RGB, depth)
- [ ] **Parser**: LiDAR point clouds
- [ ] **Parser**: IMU data (accel, gyro)
- [ ] **Parser**: GPS data
- [ ] **Parser**: Contact sensor data

### Sensor Types

1. **Camera**
   - RGB images
   - Depth images
   - Image encoding/compression

2. **LiDAR**
   - Point cloud data
   - Range arrays
   - Intensity values

3. **IMU**
   - Linear acceleration
   - Angular velocity
   - Orientation

4. **GPS**
   - Latitude, longitude, altitude
   - Fix status

### Implementation Example

```python
@mcp_tool(
    name="get_sensor_data",
    description="Get data from robot sensor"
)
async def get_sensor_data(
    model_name: str,
    sensor_type: str,
    timeout: float = 1.0
) -> Dict[str, Any]:
    """
    Read sensor data from model.

    Args:
        model_name: Name of model with sensor
        sensor_type: Type of sensor (camera, lidar, imu, gps)
        timeout: Max time to wait for data

    Returns:
        Sensor data dictionary
    """
    topic_name = f"/{model_name}/{sensor_type}"

    # Subscribe and wait for message
    data = await bridge.get_latest_message(topic_name, timeout)

    # Parse based on sensor type
    if sensor_type == "camera":
        return parse_camera_data(data)
    elif sensor_type == "lidar":
        return parse_lidar_data(data)
    # ...

    return parsed_data
```

---

## Module 3.4: Robot Control Tools

**File**: `src/gazebo_mcp/tools/robot_control.py`

### Tasks (0/6)

- [ ] **Tool**: `send_velocity_command` - Send cmd_vel
- [ ] **Tool**: `send_joint_command` - Control joints
- [ ] **Tool**: `get_joint_states` - Read joint positions/velocities
- [ ] **Tool**: `set_controller_parameters` - Configure PID gains
- [ ] **Helper**: Create Twist messages
- [ ] **Helper**: Validate velocity limits

### Implementation Example

```python
@mcp_tool(
    name="send_velocity_command",
    description="Send velocity command to robot"
)
async def send_velocity_command(
    model_name: str,
    linear_x: float = 0.0,
    linear_y: float = 0.0,
    linear_z: float = 0.0,
    angular_x: float = 0.0,
    angular_y: float = 0.0,
    angular_z: float = 0.0
) -> Dict[str, Any]:
    """
    Send velocity command to robot.

    Args:
        model_name: Name of robot model
        linear_x/y/z: Linear velocities (m/s)
        angular_x/y/z: Angular velocities (rad/s)

    Returns:
        Success status
    """
    # Create Twist message
    from geometry_msgs.msg import Twist
    cmd = Twist()
    cmd.linear.x = linear_x
    cmd.linear.y = linear_y
    cmd.linear.z = linear_z
    cmd.angular.x = angular_x
    cmd.angular.y = angular_y
    cmd.angular.z = angular_z

    # Publish to robot's cmd_vel topic
    topic = f"/{model_name}/cmd_vel"
    bridge.publish_velocity(topic, cmd)

    return {'success': True, 'model': model_name}
```

---

## Additional Utilities

### SDF Generator
**File**: `src/gazebo_mcp/utils/sdf_generator.py`

- [ ] Generate SDF for primitive shapes (box, sphere, cylinder)
- [ ] Generate SDF for TurtleBot3 models
- [ ] Template system for model generation
- [ ] Validation of generated SDF

### Model Templates
**Directory**: `config/models/`

- [ ] `turtlebot3_burger.yaml` - TurtleBot3 Burger config
- [ ] `turtlebot3_waffle.yaml` - TurtleBot3 Waffle config
- [ ] `primitives.yaml` - Primitive shape templates

---

## Testing Requirements

### Unit Tests
- [ ] Test each tool with valid inputs
- [ ] Test validation and error handling
- [ ] Test SDF generation
- [ ] Test sensor data parsers
- [ ] Test message conversions

### Integration Tests
- [ ] Test spawning TurtleBot3 in real Gazebo
- [ ] Test sending velocity commands
- [ ] Test reading sensor data
- [ ] Test pause/unpause simulation
- [ ] Test model state queries

### Test Files
- `tests/test_simulation_control.py`
- `tests/test_model_management.py`
- `tests/test_sensor_tools.py`
- `tests/test_robot_control.py`

---

## Documentation

- [ ] Document each tool in API reference
- [ ] Add usage examples for each tool
- [ ] Create TurtleBot3 setup guide
- [ ] Document sensor data formats
- [ ] Add troubleshooting section

---

## Subprocess Management Details

### Gazebo Launcher Implementation

**Critical for Module 3.1**: Managing Gazebo as a subprocess

```python
import subprocess
import signal
import os
import time
from typing import Optional

class GazeboLauncher:
    """Manage Gazebo process lifecycle"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False

    def launch(
        self,
        world_file: Optional[str] = None,
        gui: bool = True,
        verbose: bool = False
    ) -> None:
        """
        Launch Gazebo with specified world file.

        Args:
            world_file: Path to .world file (None for empty world)
            gui: Launch with GUI
            verbose: Enable verbose logging
        """
        if self.is_running:
            raise GazeboError("Gazebo is already running")

        # Build command
        cmd = ['gz', 'sim']

        if not gui:
            cmd.append('--headless')

        if verbose:
            cmd.append('--verbose')

        if world_file:
            cmd.append(world_file)

        # Launch with process group for clean shutdown
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )

        # Wait for Gazebo to be ready (check for ROS2 topics)
        self._wait_for_ready(timeout=10.0)
        self.is_running = True

    def _wait_for_ready(self, timeout: float = 10.0) -> None:
        """Wait for Gazebo services to be available"""
        import rclpy
        from rclpy.node import Node

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            # Check if Gazebo services are available
            # This is a simplified check - actual implementation should verify
            # specific services like /spawn_entity
            if self._check_services_available():
                return
            time.sleep(0.5)

        raise TimeoutError(
            f"Gazebo did not become ready within {timeout} seconds. "
            f"Check Gazebo logs for errors."
        )

    def shutdown(self, timeout: float = 10.0) -> None:
        """
        Gracefully shutdown Gazebo.

        Args:
            timeout: Max time to wait for shutdown (seconds)
        """
        if not self.is_running or not self.process:
            return

        try:
            # Send SIGINT for graceful shutdown
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)

            # Wait for process to exit
            self.process.wait(timeout=timeout)

        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown failed
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait(timeout=5.0)

        finally:
            self.is_running = False
            self.process = None

    def is_alive(self) -> bool:
        """Check if Gazebo process is still running"""
        if not self.process:
            return False
        return self.process.poll() is None
```

### Service Discovery and Waiting

**Pattern for waiting on Gazebo services**:

```python
async def wait_for_service(
    node: Node,
    service_name: str,
    timeout: float = 10.0
) -> bool:
    """
    Wait for ROS2 service to become available.

    Args:
        node: ROS2 node instance
        service_name: Service name (e.g., '/spawn_entity')
        timeout: Maximum wait time

    Returns:
        True if service available, False if timeout
    """
    from rclpy.client import Client
    from gazebo_msgs.srv import SpawnEntity

    client = node.create_client(SpawnEntity, service_name)

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if client.service_is_ready():
            return True
        await asyncio.sleep(0.1)

    return False
```

---

## Sensor Data Format Reference

### Camera (RGB)
**Topic**: `/{robot_name}/camera/image_raw`
**Type**: `sensor_msgs/msg/Image`

```python
{
    'width': 640,
    'height': 480,
    'encoding': 'rgb8',  # or 'bgr8'
    'data': bytes,  # width × height × 3 bytes
}
```

### LiDAR (LaserScan)
**Topic**: `/{robot_name}/scan`
**Type**: `sensor_msgs/msg/LaserScan`

```python
{
    'angle_min': -3.14,  # radians
    'angle_max': 3.14,
    'angle_increment': 0.0175,  # ~1 degree
    'range_min': 0.12,  # meters
    'range_max': 3.5,
    'ranges': [1.2, 1.3, ...],  # array of distances
    'intensities': [0.8, 0.9, ...]  # optional
}
```

### IMU
**Topic**: `/{robot_name}/imu`
**Type**: `sensor_msgs/msg/Imu`

```python
{
    'orientation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
    'angular_velocity': {'x': 0.0, 'y': 0.0, 'z': 0.0},  # rad/s
    'linear_acceleration': {'x': 0.0, 'y': 0.0, 'z': 9.8}  # m/s²
}
```

### GPS
**Topic**: `/{robot_name}/gps`
**Type**: `sensor_msgs/msg/NavSatFix`

```python
{
    'latitude': 37.7749,  # degrees
    'longitude': -122.4194,
    'altitude': 100.0,  # meters
    'status': 0  # 0=no fix, 1=fix, 2=SBAS fix
}
```

---

## Success Criteria

### Automated Verification ✅

Run verification script:
```bash
./verify_phase3.sh
```

This checks:
- [ ] All 30 tasks implemented with tests
- [ ] >80% code coverage for phase 3 modules
- [ ] Type checking passes (mypy --strict)
- [ ] Linting passes (ruff, black)
- [ ] No critical security issues

### Manual Verification Checklist ✅

**Simulation Control**:
- [ ] Can start Gazebo with empty world
- [ ] Can pause and unpause simulation
- [ ] Can reset simulation to initial state
- [ ] Can stop Gazebo gracefully
- [ ] Can configure physics properties

**Model Management**:
- [ ] Can spawn TurtleBot3 Burger at specified position
- [ ] Can spawn TurtleBot3 Waffle with camera
- [ ] Can query list of active models
- [ ] Can get model state (position, velocity)
- [ ] Can set model state programmatically
- [ ] Can delete spawned models

**Sensor Access**:
- [ ] Can read camera RGB images
- [ ] Can read LiDAR scan data
- [ ] Can read IMU data (accel, gyro, orientation)
- [ ] Can read GPS coordinates
- [ ] All sensor data formats are correct
- [ ] Sensor timeout handling works

**Robot Control**:
- [ ] Can send linear velocity commands
- [ ] Can send angular velocity commands
- [ ] Can control individual joints
- [ ] Can read joint states
- [ ] Velocity limits are enforced

### Integration Tests ✅

Run with real Gazebo:
```bash
# Start Gazebo first
gz sim -s &

# Run integration tests
pytest tests/integration/test_turtlebot3_spawn.py -v
pytest tests/integration/test_sensor_access.py -v
```

Must pass:
- [ ] `test_spawn_and_control_turtlebot3` - Full workflow
- [ ] `test_read_all_sensors` - All sensor types
- [ ] `test_pause_and_reset` - Simulation control
- [ ] `test_multiple_models` - Multi-robot scenario

### Code Quality Standards ✅

**CRITICAL**: All code must meet these standards:

- [ ] **Type Hints**: Every function fully typed
  ```python
  def spawn_model(model_name: str, x: float) -> Dict[str, Any]:
  ```

- [ ] **Docstrings**: All public functions documented
  ```python
  """
  Spawn model in Gazebo.

  Args:
      model_name: Unique identifier for model

  Returns:
      Success status and model info
  """
  ```

- [ ] **Error Handling**: All failures handled gracefully
- [ ] **Tests**: >80% coverage, TDD approach
- [ ] **Validation**: All inputs validated
- [ ] **Logging**: Appropriate log levels used

### Documentation ✅

- [ ] All tools documented in API reference
- [ ] Sensor data formats documented
- [ ] TurtleBot3 usage examples added
- [ ] Subprocess management guide complete
- [ ] Troubleshooting section updated

### Performance Targets ✅

| Operation | Target | Actual |
|-----------|--------|--------|
| Spawn model | < 500ms | ___ |
| Get sensor data | < 50ms | ___ |
| Send velocity cmd | < 100ms | ___ |
| Service call | < 200ms | ___ |

---

## Next Phase

Once all success criteria are met, proceed to:
**Phase 4: World Generation & Manipulation**

---

## Best Practices Summary

**DO** ✅:
- Write tests before implementation
- Validate all inputs thoroughly
- Handle Gazebo process lifecycle carefully
- Wait for services before calling
- Provide actionable error messages
- Document sensor data formats
- Test with real Gazebo regularly

**DON'T** ❌:
- Skip subprocess cleanup
- Ignore service timeouts
- Assume Gazebo is always running
- Use generic error messages
- Hardcode topic names
- Skip integration tests
- Leave zombie processes

---

**Estimated Completion**: 5-7 days
**Priority**: HIGH
