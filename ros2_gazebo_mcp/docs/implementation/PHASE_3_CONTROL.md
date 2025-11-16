# Phase 3: Gazebo Connection & Control Tools

**Status**: 🔵 Not Started
**Estimated Duration**: 5-7 days
**Prerequisites**: Phase 2 Complete

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

## Success Criteria

Phase 3 is complete when:

- [ ] All 30 tasks implemented
- [ ] TurtleBot3 can be spawned and controlled
- [ ] Sensor data can be read from all sensor types
- [ ] Simulation can be controlled (pause, reset, etc.)
- [ ] All tests pass (>80% coverage)
- [ ] Integration tests with real Gazebo pass
- [ ] Documentation complete

---

## Next Phase

Proceed to **Phase 4: World Generation & Manipulation**

---

**Estimated Completion**: 5-7 days
**Priority**: HIGH
