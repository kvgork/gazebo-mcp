# TurtleBot3 Guide

Complete guide to using TurtleBot3 robots with the Gazebo MCP Server.

## Table of Contents

- [TurtleBot3 Overview](#turtlebot3-overview)
- [Model Variants](#model-variants)
- [Spawning TurtleBot3](#spawning-turtlebot3)
- [Controlling Movement](#controlling-movement)
- [Reading Sensors](#reading-sensors)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

---

## TurtleBot3 Overview

TurtleBot3 is a compact, affordable mobile robot platform designed for education and research.

**Key Features:**
- Differential drive (two-wheel) locomotion
- 360-degree LiDAR scanner
- IMU (Inertial Measurement Unit)
- Optional camera (Waffle/Waffle Pi)
- ROS2 native support
- Gazebo simulation ready

**Use Cases:**
- SLAM (Simultaneous Localization and Mapping)
- Autonomous navigation
- Sensor fusion research
- Multi-robot coordination
- Education and learning

---

## Model Variants

The Gazebo MCP Server supports all three TurtleBot3 variants:

### TurtleBot3 Burger

**Model Type:** `"turtlebot3_burger"`

**Specifications:**
- **Size:** 138mm × 178mm × 192mm
- **Weight:** ~1kg
- **Max Speed:** 0.22 m/s linear, 2.84 rad/s angular
- **Sensors:**
  - LDS-01 LiDAR (360°, 3.5m range)
  - 9-axis IMU
  - Cliff detection sensor

**Best For:**
- Basic navigation
- Learning SLAM
- Budget-friendly testing
- Indoor environments

**Example:**
```python
result = model_management.spawn_model(
    model_name="burger_bot",
    model_type="turtlebot3_burger",
    x=0.0, y=0.0, z=0.01
)
```

---

### TurtleBot3 Waffle

**Model Type:** `"turtlebot3_waffle"`

**Specifications:**
- **Size:** 281mm × 306mm × 141mm
- **Weight:** ~1.8kg
- **Max Speed:** 0.26 m/s linear, 1.82 rad/s angular
- **Sensors:**
  - LDS-02 LiDAR (360°, 3.5m range)
  - 9-axis IMU
  - Intel RealSense D435 camera (RGB-D)
  - Cliff detection sensor

**Best For:**
- Vision-based navigation
- Object detection/recognition
- Advanced SLAM with RGB-D
- Research applications

**Example:**
```python
result = model_management.spawn_model(
    model_name="waffle_bot",
    model_type="turtlebot3_waffle",
    x=0.0, y=0.0, z=0.01
)
```

---

### TurtleBot3 Waffle Pi

**Model Type:** `"turtlebot3_waffle_pi"`

**Specifications:**
- **Size:** 281mm × 306mm × 141mm
- **Weight:** ~1.8kg
- **Max Speed:** 0.26 m/s linear, 1.82 rad/s angular
- **Sensors:**
  - LDS-02 LiDAR (360°, 3.5m range)
  - 9-axis IMU
  - Raspberry Pi Camera Module v2
  - Cliff detection sensor

**Best For:**
- Camera-based vision
- Image processing research
- Educational projects
- Raspberry Pi integration

**Example:**
```python
result = model_management.spawn_model(
    model_name="waffle_pi_bot",
    model_type="turtlebot3_waffle_pi",
    x=0.0, y=0.0, z=0.01
)
```

---

## Spawning TurtleBot3

### Basic Spawning

```python
from gazebo_mcp.tools import model_management

# Spawn at origin
result = model_management.spawn_model(
    model_name="my_robot",
    model_type="turtlebot3_burger",
    x=0.0, y=0.0, z=0.01  # Slightly above ground
)

if result.success:
    print(f"✓ Spawned {result.data['model_type']}")
else:
    print(f"✗ Error: {result.error}")
```

### Spawning at Specific Location

```python
# Spawn robot at coordinates with orientation
result = model_management.spawn_model(
    model_name="robot_1",
    model_type="turtlebot3_burger",
    x=5.0,      # 5 meters in X
    y=3.0,      # 3 meters in Y
    z=0.01,     # Just above ground
    roll=0.0,   # No roll
    pitch=0.0,  # No pitch
    yaw=1.57    # Face East (90 degrees)
)
```

### Spawning Multiple Robots

```python
# Create a fleet of robots
robots = []
for i in range(5):
    result = model_management.spawn_model(
        model_name=f"robot_{i}",
        model_type="turtlebot3_burger",
        x=i * 2.0,  # Space 2m apart
        y=0.0,
        z=0.01
    )
    if result.success:
        robots.append(f"robot_{i}")

print(f"Spawned {len(robots)} robots")
```

---

## Controlling Movement

TurtleBot3 uses differential drive - control with linear and angular velocities.

### Understanding Velocity Commands

**Linear Velocity (m/s):**
- **Forward:** Positive X velocity
- **Backward:** Negative X velocity
- **Range:** -0.22 to 0.22 m/s (Burger)

**Angular Velocity (rad/s):**
- **Turn Left:** Positive Z velocity
- **Turn Right:** Negative Z velocity
- **Range:** -2.84 to 2.84 rad/s (Burger)

### Teleportation (Instant Movement)

```python
# Move robot instantly to new position
result = model_management.set_model_state(
    model_name="my_robot",
    x=10.0,
    y=5.0,
    z=0.01,
    yaw=3.14  # Face opposite direction
)
```

**Use Cases:**
- Reset robot position
- Test specific scenarios
- Skip navigation phases
- Positioning for experiments

### Movement Patterns

#### Drive Straight

```python
# Position robot, check state, move it
# (Note: Actual velocity control requires ROS2 cmd_vel topics)

# Get current position
start = model_management.get_model_state("my_robot")

# Teleport 2m forward
if start.success:
    pos = start.data['pose']['position']
    result = model_management.set_model_state(
        model_name="my_robot",
        x=pos['x'] + 2.0,  # Move 2m in X
        y=pos['y'],
        z=0.01
    )
```

#### Turn in Place

```python
# Rotate robot 90 degrees
result = model_management.get_model_state("my_robot")
if result.success:
    pos = result.data['pose']['position']
    ori = result.data['pose']['orientation']

    # Add 90 degrees (π/2 radians)
    new_yaw = ori['yaw'] + 1.57

    model_management.set_model_state(
        model_name="my_robot",
        x=pos['x'],
        y=pos['y'],
        z=0.01,
        yaw=new_yaw
    )
```

#### Square Pattern

```python
import time

# Drive in a square (using teleportation)
square_points = [
    (0, 0, 0),      # Start
    (2, 0, 1.57),   # Move right, face up
    (2, 2, 3.14),   # Move up, face left
    (0, 2, -1.57),  # Move left, face down
    (0, 0, 0)       # Return to start
]

for i, (x, y, yaw) in enumerate(square_points):
    print(f"Moving to point {i+1}/5...")
    model_management.set_model_state(
        model_name="my_robot",
        x=x, y=y, z=0.01, yaw=yaw
    )
    time.sleep(1)  # Pause at each point
```

---

## Reading Sensors

### LiDAR Scanner

TurtleBot3 includes a 360-degree LiDAR scanner.

**Specifications:**
- **Range:** 0.12m to 3.5m
- **Readings:** 360 measurements (1° resolution)
- **Update Rate:** 5 Hz
- **Topic:** `/robot_name/scan`

**Reading LiDAR Data:**

```python
from gazebo_mcp.tools import sensor_tools

result = sensor_tools.get_sensor_data(
    model_name="my_robot",
    sensor_type="lidar",
    timeout=2.0
)

if result.success:
    sensor_data = result.data['sensor_data']
    ranges = sensor_data['ranges']

    # Find closest obstacle
    valid_ranges = [r for r in ranges if r != float('inf')]
    if valid_ranges:
        min_dist = min(valid_ranges)
        print(f"Closest obstacle: {min_dist:.2f}m")

    # Check front, left, right, back
    front = ranges[0]      # 0° (front)
    left = ranges[90]      # 90° (left)
    back = ranges[180]     # 180° (back)
    right = ranges[270]    # 270° (right)

    print(f"Front: {front:.2f}m")
    print(f"Left: {left:.2f}m")
    print(f"Right: {right:.2f}m")
    print(f"Back: {back:.2f}m")
```

**Obstacle Detection:**

```python
def check_obstacles(robot_name, safe_distance=0.5):
    """Check if obstacles are too close."""
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="lidar"
    )

    if not result.success:
        return False, "Sensor unavailable"

    ranges = result.data['sensor_data']['ranges']
    valid_ranges = [r for r in ranges if r != float('inf')]

    if valid_ranges:
        min_dist = min(valid_ranges)
        if min_dist < safe_distance:
            return False, f"Obstacle at {min_dist:.2f}m"

    return True, "Path clear"

# Usage
safe, msg = check_obstacles("my_robot", safe_distance=0.5)
print(msg)
```

---

### IMU (Inertial Measurement Unit)

Provides orientation, angular velocity, and linear acceleration.

**Reading IMU Data:**

```python
result = sensor_tools.get_sensor_data(
    model_name="my_robot",
    sensor_type="imu",
    timeout=2.0
)

if result.success:
    imu = result.data['sensor_data']

    # Orientation (Roll, Pitch, Yaw)
    ori = imu['orientation']
    print(f"Heading: {ori['yaw']:.2f} rad ({ori['yaw']*57.3:.1f}°)")
    print(f"Tilt: pitch={ori['pitch']:.2f}, roll={ori['roll']:.2f}")

    # Angular velocity
    ang_vel = imu['angular_velocity']
    print(f"Rotation rate: {ang_vel['z']:.2f} rad/s")

    # Linear acceleration
    lin_acc = imu['linear_acceleration']
    print(f"Acceleration: x={lin_acc['x']:.2f} m/s²")
```

**Detecting Movement:**

```python
def is_robot_moving(robot_name, threshold=0.01):
    """Check if robot is moving."""
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="imu"
    )

    if result.success:
        imu = result.data['sensor_data']

        # Check linear acceleration (excluding gravity)
        acc = imu['linear_acceleration']
        magnitude = (acc['x']**2 + acc['y']**2)**0.5

        return magnitude > threshold

    return False
```

---

### Camera (Waffle/Waffle Pi only)

**Reading Camera Images:**

```python
result = sensor_tools.get_sensor_data(
    model_name="waffle_bot",
    sensor_type="camera",
    timeout=2.0
)

if result.success:
    camera = result.data['sensor_data']

    print(f"Image size: {camera['width']}x{camera['height']}")
    print(f"Encoding: {camera['encoding']}")

    # Image data is in camera['data'] (binary)
    image_bytes = camera['data']
    print(f"Image size: {len(image_bytes) / 1024:.1f} KB")

    # Process with OpenCV (example)
    # import cv2
    # import numpy as np
    # img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    # img = img_array.reshape((camera['height'], camera['width'], 3))
```

---

## Common Workflows

### Workflow 1: Obstacle Avoidance

```python
from gazebo_mcp.tools import model_management, sensor_tools
import time

robot_name = "my_robot"

# Spawn robot
model_management.spawn_model(
    model_name=robot_name,
    model_type="turtlebot3_burger",
    x=0.0, y=0.0, z=0.01
)

# Simple obstacle avoidance loop
while True:
    # Read LiDAR
    result = sensor_tools.get_sensor_data(
        model_name=robot_name,
        sensor_type="lidar"
    )

    if result.success:
        ranges = result.data['sensor_data']['ranges']
        front_distance = min(ranges[0:30] + ranges[330:360])

        if front_distance < 0.5:
            print("⚠️ Obstacle detected! Taking action...")
            # Logic to avoid obstacle
        else:
            print("✓ Path clear")

    time.sleep(0.5)
```

### Workflow 2: SLAM Preparation

```python
# Spawn robot in empty world
model_management.spawn_model(
    model_name="slam_robot",
    model_type="turtlebot3_burger",
    x=0.0, y=0.0, z=0.01
)

# Verify LiDAR is working
result = sensor_tools.list_sensors("slam_robot")
if result.success:
    sensors = result.data['sensors']
    lidar_found = any(s['type'] == 'lidar' for s in sensors)
    print(f"LiDAR ready: {lidar_found}")

# Read initial scan
result = sensor_tools.get_sensor_data("slam_robot", "lidar")
if result.success:
    print("✓ Ready for SLAM!")
    print(f"  Scan range: {result.data['sensor_data']['range_max']}m")
```

### Workflow 3: Multi-Robot Coordination

```python
# Spawn robot fleet in formation
formation = [
    (0, 0),    # Leader
    (-1, -1),  # Left rear
    (-1, 1),   # Right rear
    (-2, -1),  # Left far
    (-2, 1)    # Right far
]

robots = []
for i, (x, y) in enumerate(formation):
    result = model_management.spawn_model(
        model_name=f"fleet_{i}",
        model_type="turtlebot3_burger",
        x=x, y=y, z=0.01
    )
    if result.success:
        robots.append(f"fleet_{i}")

print(f"Fleet of {len(robots)} robots ready")

# Query each robot's position
for robot in robots:
    result = model_management.get_model_state(robot)
    if result.success:
        pos = result.data['pose']['position']
        print(f"{robot}: ({pos['x']:.1f}, {pos['y']:.1f})")
```

---

## Troubleshooting

### Robot Doesn't Appear

**Problem:** `spawn_model()` succeeds but robot not visible in Gazebo.

**Solutions:**
1. Check Gazebo is fully started (wait 10 seconds)
2. Verify model path:
   ```bash
   export GAZEBO_MODEL_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models:$GAZEBO_MODEL_PATH
   ```
3. Install TurtleBot3 models:
   ```bash
   sudo apt install ros-humble-turtlebot3-gazebo
   ```
4. Check spawn height (z=0.01, not z=0)

---

### LiDAR Returns All "inf"

**Problem:** All LiDAR readings are infinity.

**Solutions:**
1. Robot is in empty space (no obstacles in range)
2. Add test obstacles to world
3. Check LiDAR max range (3.5m for TurtleBot3)
4. Verify Gazebo physics is running (not paused)

---

### IMU Shows No Movement

**Problem:** IMU readings are all zero despite robot moving.

**Solutions:**
1. Check robot is actually moving (use `get_model_state`)
2. Verify IMU sensor exists: `list_sensors("robot_name")`
3. Wait for sensor to initialize (first reading may be zero)
4. Check gravity is enabled in world (for acceleration)

---

### Model Already Exists Error

**Problem:** `MODEL_ALREADY_EXISTS` when spawning.

**Solutions:**
```python
# Delete existing model first
model_management.delete_model("my_robot")

# Then spawn
model_management.spawn_model("my_robot", "turtlebot3_burger", ...)
```

Or use unique names:
```python
import uuid
unique_name = f"robot_{uuid.uuid4().hex[:8]}"
model_management.spawn_model(unique_name, ...)
```

---

### Camera Not Available

**Problem:** Camera sensor not found on Burger model.

**Solution:** Use Waffle or Waffle Pi models:
```python
# ❌ Burger has no camera
model_management.spawn_model("robot", "turtlebot3_burger", ...)

# ✅ Waffle has camera
model_management.spawn_model("robot", "turtlebot3_waffle", ...)
```

---

## Model Comparison

| Feature | Burger | Waffle | Waffle Pi |
|---------|--------|--------|-----------|
| **Size** | Compact | Large | Large |
| **Speed** | 0.22 m/s | 0.26 m/s | 0.26 m/s |
| **LiDAR** | LDS-01 ✓ | LDS-02 ✓ | LDS-02 ✓ |
| **IMU** | ✓ | ✓ | ✓ |
| **Camera** | ✗ | RealSense ✓ | Pi Camera ✓ |
| **RGB-D** | ✗ | ✓ | ✗ |
| **Best For** | Learning | Research | Education |
| **Cost** | Low | High | Medium |

---

## Next Steps

- **API Reference**: [API_REFERENCE.md](../api/API_REFERENCE.md) - All tool details
- **Sensor Formats**: [SENSOR_DATA_FORMATS.md](../api/SENSOR_DATA_FORMATS.md) - Data structures
- **Examples**: `examples/` directory - Working code
- **ROS2 Nav2**: Integrate with navigation stack
- **SLAM**: Set up mapping and localization

---

## Additional Resources

- **TurtleBot3 Manual**: https://emanual.robotis.com/docs/en/platform/turtlebot3/
- **ROS2 Tutorials**: https://docs.ros.org/en/humble/Tutorials.html
- **Gazebo Sim**: https://gazebosim.org/docs
- **Example Code**: `examples/02_turtlebot3_spawn.py`

**Happy robot simulating!** 🤖
