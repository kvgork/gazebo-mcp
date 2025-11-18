# API Reference

Complete reference for all Gazebo MCP Server tools.

## Table of Contents

- [Simulation Control Tools](#simulation-control-tools)
- [Model Management Tools](#model-management-tools)
- [Sensor Integration Tools](#sensor-integration-tools)
- [World Management Tools](#world-management-tools)
- [Response Format](#response-format)
- [Error Handling](#error-handling)

---

## Overview

The Gazebo MCP Server provides **17 tools** across 4 categories:

| Category | Tools | Purpose |
|----------|-------|---------|
| **Simulation Control** | 6 tools | Control simulation state and timing |
| **Model Management** | 5 tools | Spawn, delete, and manipulate models |
| **Sensor Integration** | 3 tools | Access sensor data from robots |
| **World Management** | 3 tools | Load, save, and configure worlds |

All tools return an `OperationResult` with consistent structure.

---

## Simulation Control Tools

### `pause_simulation()`

Pause the simulation (freeze time).

**Parameters:** None

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'paused': True,
        'simulation_time': 10.5  # Time when paused
    }
)
```

**Example:**
```python
from gazebo_mcp.tools import simulation_tools

result = simulation_tools.pause_simulation()
if result.success:
    print("Simulation paused")
```

**Use Cases:**
- Capture exact simulation state
- Prepare for batch operations
- Debugging robot behavior

---

### `unpause_simulation()`

Resume the simulation.

**Parameters:** None

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'paused': False,
        'simulation_time': 10.5
    }
)
```

**Example:**
```python
result = simulation_tools.unpause_simulation()
if result.success:
    print("Simulation resumed")
```

---

### `reset_simulation()`

Reset simulation to initial state (time = 0, models reset).

**Parameters:** None

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'reset_time': True,
        'reset_models': True,
        'simulation_time': 0.0
    }
)
```

**Example:**
```python
result = simulation_tools.reset_simulation()
if result.success:
    print("Simulation reset to t=0")
```

**Warning:** This resets ALL models to their spawn positions!

---

### `get_simulation_status()`

Get current simulation state.

**Parameters:** None

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'paused': False,
        'simulation_time': 25.3,
        'real_time': 25.1,
        'real_time_factor': 1.008,
        'iterations': 25300
    }
)
```

**Example:**
```python
result = simulation_tools.get_simulation_status()
if result.success:
    print(f"Time: {result.data['simulation_time']:.2f}s")
    print(f"Paused: {result.data['paused']}")
```

---

### `get_simulation_time()`

Get current simulation time.

**Parameters:** None

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'simulation_time': 42.7,  # Seconds
        'real_time': 42.5
    }
)
```

**Example:**
```python
result = simulation_tools.get_simulation_time()
time = result.data['simulation_time']
print(f"Simulation time: {time:.2f}s")
```

---

### `set_simulation_speed(speed_factor)`

Set simulation speed multiplier.

**Parameters:**
- `speed_factor` (float): Speed multiplier (0.1 to 10.0)
  - `1.0` = Real-time
  - `2.0` = 2x speed
  - `0.5` = Half speed

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'speed_factor': 2.0,
        'previous_speed': 1.0
    }
)
```

**Example:**
```python
# Run simulation at 5x speed
result = simulation_tools.set_simulation_speed(5.0)
if result.success:
    print("Simulation running at 5x speed")
```

**Use Cases:**
- Fast-forward through initialization
- Slow-motion for debugging
- Batch testing at high speed

---

## Model Management Tools

### `spawn_model(model_name, model_type, x, y, z, roll, pitch, yaw)`

Spawn a robot or object in the simulation.

**Parameters:**
- `model_name` (str, required): Unique identifier for this model instance
- `model_type` (str): Type of model (default: "turtlebot3_burger")
  - Options: "turtlebot3_burger", "turtlebot3_waffle", "turtlebot3_waffle_pi"
  - Or custom model URIs
- `x`, `y`, `z` (float): Position in meters (default: 0, 0, 0)
- `roll`, `pitch`, `yaw` (float): Orientation in radians (default: 0, 0, 0)

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'model_name': 'my_robot',
        'model_type': 'turtlebot3_burger',
        'position': {'x': 1.0, 'y': 2.0, 'z': 0.01},
        'orientation': {'roll': 0.0, 'pitch': 0.0, 'yaw': 1.57}
    }
)
```

**Example:**
```python
from gazebo_mcp.tools import model_management

# Spawn TurtleBot3 at origin
result = model_management.spawn_model(
    model_name="robot1",
    model_type="turtlebot3_burger",
    x=0.0, y=0.0, z=0.01,
    roll=0.0, pitch=0.0, yaw=0.0
)

if result.success:
    print(f"Spawned {result.data['model_name']}")
```

**Advanced:**
```python
# Spawn at specific position with rotation
result = model_management.spawn_model(
    model_name="robot2",
    model_type="turtlebot3_waffle",
    x=5.0, y=3.0, z=0.01,
    yaw=1.57  # 90 degrees rotation
)
```

**Common Errors:**
- `MODEL_ALREADY_EXISTS`: Model with this name exists
- `MODEL_TYPE_INVALID`: Unknown model type
- `SPAWN_FAILED`: Collision or invalid position

---

### `delete_model(model_name)`

Remove a model from the simulation.

**Parameters:**
- `model_name` (str, required): Name of model to delete

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'model_name': 'robot1',
        'deleted': True
    }
)
```

**Example:**
```python
result = model_management.delete_model("robot1")
if result.success:
    print("Model deleted")
```

**Errors:**
- `MODEL_NOT_FOUND`: Model doesn't exist

---

### `list_models(response_format)`

List all models in the simulation.

**Parameters:**
- `response_format` (str): Output format (default: "summary")
  - `"summary"`: Model names and basic info only
  - `"filtered"`: Return full data for local filtering
  - `"full"`: All details (high token usage)

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'models': [
            {
                'name': 'robot1',
                'type': 'turtlebot3_burger',
                'position': {'x': 0.0, 'y': 0.0, 'z': 0.01}
            },
            {
                'name': 'robot2',
                'type': 'turtlebot3_waffle',
                'position': {'x': 5.0, 'y': 3.0, 'z': 0.01}
            }
        ],
        'count': 2
    }
)
```

**Example:**
```python
# Summary (recommended)
result = model_management.list_models(response_format="summary")
print(f"Total models: {result.data['count']}")
for model in result.data['models']:
    print(f"  - {model['name']}: {model['type']}")
```

**Token Efficiency:**
- `summary`: ~50 tokens per model
- `full`: ~500 tokens per model
- Use `filtered` with ResultFilter for 98% token savings

---

### `get_model_state(model_name)`

Get current state of a model (position, velocity).

**Parameters:**
- `model_name` (str, required): Model to query

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'model_name': 'robot1',
        'pose': {
            'position': {'x': 1.5, 'y': 2.3, 'z': 0.01},
            'orientation': {'roll': 0.0, 'pitch': 0.0, 'yaw': 1.2}
        },
        'twist': {
            'linear': {'x': 0.1, 'y': 0.0, 'z': 0.0},
            'angular': {'x': 0.0, 'y': 0.0, 'z': 0.05}
        }
    }
)
```

**Example:**
```python
result = model_management.get_model_state("robot1")
if result.success:
    pos = result.data['pose']['position']
    print(f"Robot at ({pos['x']:.2f}, {pos['y']:.2f})")
```

---

### `set_model_state(model_name, x, y, z, roll, pitch, yaw)`

Set model position and orientation (teleport).

**Parameters:**
- `model_name` (str, required): Model to move
- `x`, `y`, `z` (float, required): New position
- `roll`, `pitch`, `yaw` (float): New orientation (default: 0, 0, 0)

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'model_name': 'robot1',
        'position': {'x': 5.0, 'y': 0.0, 'z': 0.01},
        'orientation': {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
    }
)
```

**Example:**
```python
# Teleport robot to new position
result = model_management.set_model_state(
    model_name="robot1",
    x=10.0, y=5.0, z=0.01,
    yaw=3.14  # 180 degree rotation
)
```

**Note:** This instantly moves the model (no physics simulation).

---

## Sensor Integration Tools

### `list_sensors(model_name, response_format)`

List all sensors on a model.

**Parameters:**
- `model_name` (str, required): Model to query
- `response_format` (str): Output format (default: "summary")

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'model_name': 'robot1',
        'sensors': [
            {
                'name': 'scan',
                'type': 'lidar',
                'topic': '/robot1/scan',
                'frame_id': 'base_scan'
            },
            {
                'name': 'camera',
                'type': 'camera',
                'topic': '/robot1/camera/image_raw',
                'frame_id': 'camera_rgb_optical_frame'
            }
        ],
        'count': 2
    }
)
```

**Example:**
```python
from gazebo_mcp.tools import sensor_tools

result = sensor_tools.list_sensors("robot1", response_format="summary")
if result.success:
    for sensor in result.data['sensors']:
        print(f"{sensor['name']}: {sensor['type']}")
```

---

### `get_sensor_data(model_name, sensor_type, timeout)`

Read sensor data from a model.

**Parameters:**
- `model_name` (str, required): Model with sensor
- `sensor_type` (str, required): Type of sensor
  - Options: "camera", "lidar", "imu", "gps"
- `timeout` (float): Max wait time in seconds (default: 2.0)

**Returns - LiDAR:**
```python
OperationResult(
    success=True,
    data={
        'sensor_data': {
            'type': 'lidar',
            'ranges': [inf, 2.5, 1.8, ...],  # 360 readings
            'angle_min': -3.14,
            'angle_max': 3.14,
            'range_min': 0.12,
            'range_max': 3.5
        }
    }
)
```

**Returns - Camera:**
```python
OperationResult(
    success=True,
    data={
        'sensor_data': {
            'type': 'camera',
            'width': 640,
            'height': 480,
            'encoding': 'rgb8',
            'data': b'...'  # Binary image data
        }
    }
)
```

**Returns - IMU:**
```python
OperationResult(
    success=True,
    data={
        'sensor_data': {
            'type': 'imu',
            'orientation': {'roll': 0.01, 'pitch': -0.02, 'yaw': 1.57},
            'angular_velocity': {'x': 0.0, 'y': 0.0, 'z': 0.1},
            'linear_acceleration': {'x': 0.0, 'y': 0.0, 'z': 9.81}
        }
    }
)
```

**Example:**
```python
# Read LiDAR
result = sensor_tools.get_sensor_data(
    model_name="robot1",
    sensor_type="lidar",
    timeout=2.0
)

if result.success:
    ranges = result.data['sensor_data']['ranges']
    min_dist = min(r for r in ranges if r != float('inf'))
    print(f"Closest obstacle: {min_dist:.2f}m")
```

**See also:** [SENSOR_DATA_FORMATS.md](SENSOR_DATA_FORMATS.md) for complete format details.

---

### `subscribe_sensor_stream(model_name, sensor_type, callback, duration)`

Subscribe to continuous sensor updates (streaming).

**Parameters:**
- `model_name` (str, required): Model with sensor
- `sensor_type` (str, required): Sensor type
- `callback` (callable, required): Function called for each message
- `duration` (float): Subscription duration in seconds (default: 10.0)

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'subscribed': True,
        'topic': '/robot1/scan',
        'duration': 10.0,
        'messages_received': 100  # After completion
    }
)
```

**Example:**
```python
def handle_lidar(data):
    ranges = data['ranges']
    print(f"Min distance: {min(ranges):.2f}m")

result = sensor_tools.subscribe_sensor_stream(
    model_name="robot1",
    sensor_type="lidar",
    callback=handle_lidar,
    duration=5.0  # Stream for 5 seconds
)
```

**Note:** This is async - callback runs for each message.

---

## World Management Tools

### `load_world(world_file_path)`

Load a Gazebo world from SDF file.

**Parameters:**
- `world_file_path` (str, required): Path to .sdf world file

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'file_path': '/path/to/world.sdf',
        'instructions': 'Restart Gazebo with: gz sim /path/to/world.sdf'
    }
)
```

**Example:**
```python
from gazebo_mcp.tools import world_tools

result = world_tools.load_world("/path/to/my_world.sdf")
if result.success:
    print(result.data['instructions'])
```

**Note:** Requires restarting Gazebo with the world file.

---

### `save_world(file_path, overwrite)`

Save current world state to SDF file.

**Parameters:**
- `file_path` (str, required): Output path for .sdf file
- `overwrite` (bool): Overwrite if exists (default: False)

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'file_path': 'worlds/my_saved_world.sdf',
        'model_count': 5,
        'file_size_kb': 156
    }
)
```

**Example:**
```python
result = world_tools.save_world(
    file_path="worlds/test_scenario.sdf",
    overwrite=True
)
if result.success:
    print(f"Saved world with {result.data['model_count']} models")
```

---

### `get_world_properties(response_format)`

Get current world configuration.

**Parameters:**
- `response_format` (str): Output format (default: "summary")

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'properties': {
            'sim_time': 42.5,
            'paused': False,
            'model_count': 3,
            'gravity': {'x': 0.0, 'y': 0.0, 'z': -9.81}
        }
    }
)
```

**Example:**
```python
result = world_tools.get_world_properties(response_format="summary")
if result.success:
    props = result.data['properties']
    print(f"Models: {props['model_count']}")
    print(f"Time: {props['sim_time']:.2f}s")
```

---

### `set_world_property(property_name, value)`

Modify world property.

**Parameters:**
- `property_name` (str, required): Property to set
  - Options: "gravity", "magnetic_field", etc.
- `value` (any, required): New value

**Returns:**
```python
OperationResult(
    success=True,
    data={
        'property': 'gravity',
        'value': [0.0, 0.0, -9.81],
        'previous_value': [0.0, 0.0, -9.81]
    }
)
```

**Example:**
```python
# Set lunar gravity
result = world_tools.set_world_property(
    property_name="gravity",
    value=[0.0, 0.0, -1.62]  # Moon: 1.62 m/s²
)

# Set Mars gravity
result = world_tools.set_world_property(
    property_name="gravity",
    value=[0.0, 0.0, -3.71]  # Mars: 3.71 m/s²
)
```

---

## Response Format

All tools return an `OperationResult` object:

```python
@dataclass
class OperationResult:
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    error_code: Optional[str]
    suggestions: List[str]
    timestamp: str
```

**Access pattern:**
```python
result = model_management.spawn_model(...)

if result.success:
    # Access data
    model_name = result.data['model_name']
    position = result.data['position']
else:
    # Handle error
    print(f"Error: {result.error}")
    print(f"Code: {result.error_code}")
    for suggestion in result.suggestions:
        print(f"  - {suggestion}")
```

---

## Error Handling

### Common Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `ROS2_NOT_CONNECTED` | ROS2 connection failed | ROS2 not sourced, daemon not running |
| `GAZEBO_NOT_RUNNING` | Gazebo not available | Gazebo not started or crashed |
| `MODEL_NOT_FOUND` | Model doesn't exist | Wrong name or model deleted |
| `MODEL_ALREADY_EXISTS` | Duplicate model name | Name collision |
| `SENSOR_NOT_FOUND` | Sensor unavailable | Wrong sensor type or not on model |
| `TIMEOUT` | Operation timed out | Gazebo slow or frozen |
| `INVALID_PARAMETER` | Bad input | Check parameter types/ranges |

### Error Handling Pattern

```python
result = model_management.spawn_model("robot1", ...)

if not result.success:
    if result.error_code == "MODEL_ALREADY_EXISTS":
        # Try different name
        result = model_management.spawn_model("robot2", ...)

    elif result.error_code == "GAZEBO_NOT_RUNNING":
        # Start Gazebo or use mock mode
        print("Start Gazebo with: gz sim")

    else:
        # Generic error handling
        print(f"Error: {result.error}")
        for suggestion in result.suggestions:
            print(f"Try: {suggestion}")
```

---

## Best Practices

### 1. Check Success Before Accessing Data

```python
# ✅ Good
result = model_management.get_model_state("robot1")
if result.success:
    position = result.data['pose']['position']

# ❌ Bad
result = model_management.get_model_state("robot1")
position = result.data['pose']['position']  # May crash if failed
```

### 2. Use Summary Format for Lists

```python
# ✅ Good - Low token usage
result = model_management.list_models(response_format="summary")

# ❌ Bad - High token usage
result = model_management.list_models(response_format="full")
```

### 3. Handle Mock Mode Gracefully

```python
result = model_management.spawn_model("robot1", ...)
if result.success:
    if result.data.get('mock_data'):
        print("Running in mock mode - for testing only")
    else:
        print("Connected to real Gazebo")
```

### 4. Clean Up Resources

```python
# Spawn robots
for i in range(5):
    model_management.spawn_model(f"robot_{i}", ...)

# Do work...

# Clean up
for i in range(5):
    model_management.delete_model(f"robot_{i}")
```

---

## Advanced Usage

### Batch Operations

```python
# Spawn multiple robots efficiently
robots = []
for i in range(10):
    result = model_management.spawn_model(
        model_name=f"robot_{i}",
        x=i * 2.0, y=0.0, z=0.01
    )
    if result.success:
        robots.append(result.data['model_name'])

print(f"Spawned {len(robots)} robots")
```

### Sensor Monitoring Loop

```python
import time

# Monitor LiDAR for obstacles
while True:
    result = sensor_tools.get_sensor_data("robot1", "lidar")

    if result.success:
        ranges = result.data['sensor_data']['ranges']
        min_dist = min(r for r in ranges if r != float('inf'))

        if min_dist < 0.5:
            print(f"⚠️ Obstacle at {min_dist:.2f}m!")

    time.sleep(0.1)  # 10 Hz
```

---

## Next Steps

- **Sensor Data Formats**: [SENSOR_DATA_FORMATS.md](SENSOR_DATA_FORMATS.md)
- **TurtleBot3 Guide**: [../guides/TURTLEBOT3_GUIDE.md](../guides/TURTLEBOT3_GUIDE.md)
- **Examples**: Browse `examples/` directory
- **Source Code**: `src/gazebo_mcp/tools/`
