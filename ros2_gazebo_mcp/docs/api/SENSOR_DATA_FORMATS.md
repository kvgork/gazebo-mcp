# Sensor Data Formats

Complete reference for all sensor data structures returned by the Gazebo MCP Server.

## Table of Contents

- [Overview](#overview)
- [LiDAR / Laser Scanner](#lidar--laser-scanner)
- [Camera (RGB)](#camera-rgb)
- [IMU (Inertial Measurement Unit)](#imu-inertial-measurement-unit)
- [GPS / GNSS](#gps--gnss)
- [Common Patterns](#common-patterns)
- [Processing Examples](#processing-examples)

---

## Overview

All sensor data is returned through the `get_sensor_data()` function with a consistent structure:

```python
OperationResult(
    success=True,
    data={
        'sensor_data': {
            'type': 'sensor_type',
            # ... sensor-specific fields ...
        },
        'timestamp': '2024-11-17T10:30:45.123Z',
        'model_name': 'robot_name'
    }
)
```

---

## LiDAR / Laser Scanner

### Data Structure

```python
{
    'type': 'lidar',
    'ranges': [2.5, 2.4, 2.3, ...],  # List of 360 floats
    'intensities': [100, 95, 90, ...],  # Optional: Signal strength
    'angle_min': -3.14159,  # Radians
    'angle_max': 3.14159,   # Radians
    'angle_increment': 0.0174533,  # ~1 degree in radians
    'time_increment': 0.0,  # Time between measurements
    'scan_time': 0.2,  # Total scan time in seconds
    'range_min': 0.12,  # Minimum detectable range (m)
    'range_max': 3.5,   # Maximum detectable range (m)
    'frame_id': 'base_scan'
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `ranges` | List[float] | Distance measurements in meters. `inf` = no obstacle detected |
| `intensities` | List[float] | Optional: Reflection intensity (0-255) |
| `angle_min` | float | Start angle of scan (radians) |
| `angle_max` | float | End angle of scan (radians) |
| `angle_increment` | float | Angular distance between measurements |
| `range_min` | float | Minimum valid range (meters) |
| `range_max` | float | Maximum valid range (meters) |

### TurtleBot3 Specifications

**LDS-01 (Burger):**
- 360 readings (1° resolution)
- Range: 0.12m to 3.5m
- Update rate: 5 Hz

**LDS-02 (Waffle/Waffle Pi):**
- 360 readings (1° resolution)
- Range: 0.12m to 3.5m
- Update rate: 5 Hz

### Example Usage

```python
from gazebo_mcp.tools import sensor_tools

result = sensor_tools.get_sensor_data("my_robot", "lidar")

if result.success:
    lidar = result.data['sensor_data']

    # Get distance measurements
    ranges = lidar['ranges']

    # Check specific directions (0° = front)
    front = ranges[0]
    left = ranges[90]
    back = ranges[180]
    right = ranges[270]

    print(f"Front: {front:.2f}m")
    print(f"Left: {left:.2f}m")
    print(f"Back: {back:.2f}m")
    print(f"Right: {right:.2f}m")

    # Find closest obstacle
    valid_ranges = [r for r in ranges if r != float('inf')]
    if valid_ranges:
        min_distance = min(valid_ranges)
        min_index = ranges.index(min_distance)
        angle = lidar['angle_min'] + min_index * lidar['angle_increment']
        print(f"Closest obstacle: {min_distance:.2f}m at {angle:.2f} rad")
```

### Processing Tips

**Converting to Cartesian Coordinates:**
```python
import math

def lidar_to_cartesian(lidar_data):
    """Convert LiDAR polar coordinates to Cartesian (x, y)."""
    points = []
    ranges = lidar_data['ranges']
    angle_min = lidar_data['angle_min']
    angle_increment = lidar_data['angle_increment']

    for i, distance in enumerate(ranges):
        if distance != float('inf'):
            angle = angle_min + i * angle_increment
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            points.append((x, y))

    return points
```

**Filtering Noise:**
```python
def filter_lidar_noise(ranges, min_range=0.12, max_range=3.5):
    """Remove invalid and out-of-range measurements."""
    filtered = []
    for r in ranges:
        if r != float('inf') and min_range <= r <= max_range:
            filtered.append(r)
        else:
            filtered.append(None)
    return filtered
```

---

## Camera (RGB)

### Data Structure

```python
{
    'type': 'camera',
    'width': 640,  # Image width in pixels
    'height': 480,  # Image height in pixels
    'encoding': 'rgb8',  # Color encoding format
    'step': 1920,  # Row length in bytes (width * channels)
    'data': b'\xff\xd8\xff...',  # Binary image data
    'frame_id': 'camera_rgb_optical_frame'
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `width` | int | Image width in pixels |
| `height` | int | Image height in pixels |
| `encoding` | str | Pixel format (rgb8, bgr8, rgba8, etc.) |
| `step` | int | Bytes per row (width × bytes_per_pixel) |
| `data` | bytes | Raw image data (binary) |

### Encoding Formats

| Format | Channels | Bytes/Pixel | Description |
|--------|----------|-------------|-------------|
| `rgb8` | 3 | 3 | Red-Green-Blue, 8-bit per channel |
| `bgr8` | 3 | 3 | Blue-Green-Red (OpenCV default) |
| `rgba8` | 4 | 4 | RGB + Alpha (transparency) |
| `mono8` | 1 | 1 | Grayscale, 8-bit |

### TurtleBot3 Specifications

**RealSense D435 (Waffle):**
- Resolution: 640×480 (default)
- Frame rate: 30 FPS
- RGB + Depth support

**Pi Camera v2 (Waffle Pi):**
- Resolution: 640×480
- Frame rate: 30 FPS
- RGB only

### Example Usage

```python
result = sensor_tools.get_sensor_data("waffle_bot", "camera")

if result.success:
    camera = result.data['sensor_data']

    width = camera['width']
    height = camera['height']
    encoding = camera['encoding']
    image_data = camera['data']

    print(f"Image: {width}x{height}, {encoding}")
    print(f"Size: {len(image_data) / 1024:.1f} KB")
```

### Processing with OpenCV

```python
import cv2
import numpy as np

result = sensor_tools.get_sensor_data("waffle_bot", "camera")

if result.success:
    camera = result.data['sensor_data']

    # Convert binary data to numpy array
    img_array = np.frombuffer(camera['data'], dtype=np.uint8)

    # Reshape to image dimensions
    if camera['encoding'] == 'rgb8':
        img = img_array.reshape((camera['height'], camera['width'], 3))

        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Display or process
        cv2.imshow('Robot Camera', img_bgr)
        cv2.waitKey(1)

        # Save image
        cv2.imwrite('robot_view.jpg', img_bgr)
```

### Processing with PIL/Pillow

```python
from PIL import Image
import io

result = sensor_tools.get_sensor_data("waffle_bot", "camera")

if result.success:
    camera = result.data['sensor_data']

    # Convert to PIL Image
    if camera['encoding'] == 'rgb8':
        img = Image.frombytes(
            'RGB',
            (camera['width'], camera['height']),
            camera['data']
        )

        # Display or save
        img.show()
        img.save('robot_view.png')
```

---

## IMU (Inertial Measurement Unit)

### Data Structure

```python
{
    'type': 'imu',
    'orientation': {
        'x': 0.0,  # Quaternion x
        'y': 0.0,  # Quaternion y
        'z': 0.0,  # Quaternion z
        'w': 1.0,  # Quaternion w
        'roll': 0.0,   # Roll in radians
        'pitch': 0.0,  # Pitch in radians
        'yaw': 0.0     # Yaw in radians
    },
    'orientation_covariance': [0.0, ...],  # 9 values
    'angular_velocity': {
        'x': 0.0,  # rad/s
        'y': 0.0,  # rad/s
        'z': 0.0   # rad/s (rotation rate)
    },
    'angular_velocity_covariance': [0.0, ...],  # 9 values
    'linear_acceleration': {
        'x': 0.0,  # m/s²
        'y': 0.0,  # m/s²
        'z': 9.81  # m/s² (includes gravity)
    },
    'linear_acceleration_covariance': [0.0, ...],  # 9 values
    'frame_id': 'imu_link'
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `orientation` | dict | Robot orientation (quaternion + Euler) |
| `angular_velocity` | dict | Rotation rates (rad/s) |
| `linear_acceleration` | dict | Acceleration (m/s²) including gravity |
| `*_covariance` | list | Uncertainty matrix (3×3 flattened) |

### Euler Angles

- **Roll:** Rotation around X-axis (tilt left/right)
- **Pitch:** Rotation around Y-axis (tilt forward/back)
- **Yaw:** Rotation around Z-axis (heading/compass direction)

### Example Usage

```python
result = sensor_tools.get_sensor_data("my_robot", "imu")

if result.success:
    imu = result.data['sensor_data']

    # Get orientation
    ori = imu['orientation']
    print(f"Heading: {ori['yaw']:.2f} rad ({ori['yaw'] * 57.3:.1f}°)")
    print(f"Tilt: Roll={ori['roll']:.2f}, Pitch={ori['pitch']:.2f}")

    # Get angular velocity (rotation speed)
    ang_vel = imu['angular_velocity']
    print(f"Turning rate: {ang_vel['z']:.2f} rad/s")

    # Get linear acceleration
    lin_acc = imu['linear_acceleration']
    print(f"Acceleration: X={lin_acc['x']:.2f}, Y={lin_acc['y']:.2f}")
    print(f"Gravity component: {lin_acc['z']:.2f} m/s²")
```

### Processing Tips

**Detecting Rotation:**
```python
def is_rotating(imu_data, threshold=0.05):
    """Check if robot is rotating."""
    ang_vel = imu_data['angular_velocity']
    rotation_rate = abs(ang_vel['z'])
    return rotation_rate > threshold
```

**Calculating Heading Change:**
```python
def heading_change(yaw_prev, yaw_current):
    """Calculate change in heading (handles wraparound)."""
    import math
    diff = yaw_current - yaw_prev

    # Normalize to [-π, π]
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi

    return diff
```

**Removing Gravity:**
```python
def remove_gravity(imu_data):
    """Remove gravity from linear acceleration."""
    acc = imu_data['linear_acceleration'].copy()
    ori = imu_data['orientation']

    # Gravity is usually in Z direction
    # (More complex with non-zero roll/pitch)
    acc['z'] -= 9.81

    return acc
```

---

## GPS / GNSS

### Data Structure

```python
{
    'type': 'gps',
    'latitude': 37.422, # Degrees
    'longitude': -122.084,  # Degrees
    'altitude': 15.5,  # Meters above sea level
    'position_covariance': [1.0, 0.0, 0.0, ...],  # 9 values
    'position_covariance_type': 1,  # Covariance type indicator
    'status': {
        'status': 0,  # Fix status
        'service': 1  # GPS service type
    },
    'frame_id': 'gps_link'
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `latitude` | float | Latitude in degrees (-90 to 90) |
| `longitude` | float | Longitude in degrees (-180 to 180) |
| `altitude` | float | Altitude in meters (above sea level) |
| `position_covariance` | list | Position uncertainty (3×3 matrix) |
| `status` | dict | Fix quality and satellite info |

### Status Values

**Fix Status:**
- `-1`: No fix
- `0`: Fix
- `1`: SBAS fix
- `2`: GBAS fix

### Example Usage

```python
result = sensor_tools.get_sensor_data("my_robot", "gps")

if result.success:
    gps = result.data['sensor_data']

    lat = gps['latitude']
    lon = gps['longitude']
    alt = gps['altitude']

    print(f"Position: {lat:.6f}°, {lon:.6f}°")
    print(f"Altitude: {alt:.1f}m")

    # Check fix quality
    status = gps['status']['status']
    if status >= 0:
        print("✓ GPS fix acquired")
    else:
        print("⚠ No GPS fix")
```

### Processing Tips

**Calculate Distance Between Points:**
```python
import math

def gps_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters using Haversine formula."""
    R = 6371000  # Earth radius in meters

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c
```

---

## Common Patterns

### Error Handling

```python
result = sensor_tools.get_sensor_data("robot", "lidar", timeout=2.0)

if not result.success:
    if result.error_code == "SENSOR_NOT_FOUND":
        print("Sensor not available on this robot")
    elif result.error_code == "TIMEOUT":
        print("Sensor data not received in time")
    else:
        print(f"Error: {result.error}")
else:
    sensor_data = result.data['sensor_data']
    # Process data...
```

### Continuous Monitoring

```python
import time

while True:
    result = sensor_tools.get_sensor_data("robot", "lidar")

    if result.success:
        process_lidar(result.data['sensor_data'])

    time.sleep(0.1)  # 10 Hz update rate
```

### Multi-Sensor Fusion

```python
# Read multiple sensors
lidar_result = sensor_tools.get_sensor_data("robot", "lidar")
imu_result = sensor_tools.get_sensor_data("robot", "imu")
camera_result = sensor_tools.get_sensor_data("robot", "camera")

if all([lidar_result.success, imu_result.success, camera_result.success]):
    # Combine sensor data for enhanced perception
    lidar = lidar_result.data['sensor_data']
    imu = imu_result.data['sensor_data']
    camera = camera_result.data['sensor_data']

    # Fusion logic...
```

---

## Processing Examples

### Obstacle Detection (LiDAR)

```python
def detect_obstacles(robot_name, safe_distance=0.5):
    """Detect obstacles within safe distance."""
    result = sensor_tools.get_sensor_data(robot_name, "lidar")

    if not result.success:
        return []

    ranges = result.data['sensor_data']['ranges']
    angle_min = result.data['sensor_data']['angle_min']
    angle_inc = result.data['sensor_data']['angle_increment']

    obstacles = []
    for i, distance in enumerate(ranges):
        if distance < safe_distance and distance != float('inf'):
            angle = angle_min + i * angle_inc
            obstacles.append({
                'distance': distance,
                'angle': angle,
                'direction': 'front' if -0.5 < angle < 0.5 else 'side'
            })

    return obstacles
```

### Edge Detection (Camera)

```python
import cv2
import numpy as np

def detect_edges(robot_name):
    """Detect edges in camera image."""
    result = sensor_tools.get_sensor_data(robot_name, "camera")

    if not result.success:
        return None

    camera = result.data['sensor_data']
    img_array = np.frombuffer(camera['data'], dtype=np.uint8)
    img = img_array.reshape((camera['height'], camera['width'], 3))

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Detect edges
    edges = cv2.Canny(gray, 50, 150)

    return edges
```

### Motion Detection (IMU)

```python
def detect_motion(robot_name, prev_orientation=None):
    """Detect if robot has moved or rotated."""
    result = sensor_tools.get_sensor_data(robot_name, "imu")

    if not result.success:
        return False, None

    current_ori = result.data['sensor_data']['orientation']

    if prev_orientation is None:
        return False, current_ori

    # Check if orientation changed
    yaw_change = abs(current_ori['yaw'] - prev_orientation['yaw'])

    moved = yaw_change > 0.01  # 0.01 radian threshold

    return moved, current_ori
```

---

## Next Steps

- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md) - Tool documentation
- **TurtleBot3 Guide**: [../guides/TURTLEBOT3_GUIDE.md](../guides/TURTLEBOT3_GUIDE.md) - Robot specifics
- **Examples**: `examples/03_sensor_reading.py` - Working code
- **Source Code**: `src/gazebo_mcp/tools/sensor_tools.py` - Implementation

---

**Happy sensor processing!** 📡
