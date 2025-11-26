# Obstacle Course Challenge Demo

Advanced demonstration of robot navigation through a challenging obstacle course with multiple waypoints.

## Overview

This demo showcases advanced Gazebo MCP capabilities:
1. Complex world setup with custom SDF
2. Multi-model spawning (robot, obstacles, target)
3. Physics simulation
4. Waypoint-based navigation
5. State verification and error handling

## Prerequisites

- ROS2 Humble installed
- Modern Gazebo (Fortress/Garden/Harmonic)
- ros_gz_bridge package
- Python 3.10+

## Setup

### Automated Setup (Recommended)

Run the setup script to start Gazebo and ros_gz_bridge automatically:

```bash
cd demos/02_obstacle_course
./setup.sh
```

This will:
- Verify all dependencies
- Start Gazebo with obstacle course world
- Start ros_gz_bridge with required services
- Validate bridge connectivity

### Manual Setup

If you prefer manual setup:

1. Start Modern Gazebo with obstacle course world:
```bash
cd demos/02_obstacle_course
gz sim -r worlds/obstacle_course.sdf
```

2. In a new terminal, start ros_gz_bridge:
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/obstacle_course/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/obstacle_course/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/obstacle_course/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/obstacle_course/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/world/obstacle_course/state@ros_gz_interfaces/srv/GetWorldState" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
```

3. Wait 2-3 seconds for bridge to initialize

## Running the Demo

After setup is complete:

```bash
./obstacle_course_demo.py
```

Or using Python:
```bash
python3 obstacle_course_demo.py
```

## Expected Output

```
======================================================================
  Obstacle Course Challenge
======================================================================
Navigate robot through waypoints while avoiding obstacles

[Step 1/10] Validating environment...
  ✅ Validate environment (completed in 0.23s)

[Step 2/10] Initializing ROS2 and adapter...
  ✅ Initialize ROS2 and adapter (completed in 1.45s)

[Step 3/10] Spawning obstacles (walls)...
  ✅ Spawn obstacles (walls) (completed in 3.21s)

[Step 4/10] Spawning target zone...
  ✅ Spawn target zone (completed in 1.87s)

[Step 5/10] Spawning robot...
  ✅ Spawn robot (completed in 2.34s)

[Step 6/10] Verifying world state...
  ✅ Verify world state (completed in 1.12s)

[Step 7/10] Navigating to waypoint 1...
  ✅ Navigate to waypoint 1 (completed in 2.56s)

[Step 8/10] Navigating to waypoint 2...
  ✅ Navigate to waypoint 2 (completed in 3.12s)

[Step 9/10] Navigating to waypoint 3...
  ✅ Navigate to waypoint 3 (completed in 2.98s)

[Step 10/10] Reaching final target...
  ✅ Reach final target (completed in 2.45s)

======================================================================
  Demo Summary
======================================================================
Total Duration:    21.33s
Steps Completed:   10/10 ✅
Steps Failed:      0/10 ❌

🎉 Demo completed successfully!
======================================================================
```

## What This Demonstrates

### 1. Complex World Setup
- Custom SDF world file with ground plane, lighting, physics
- Grid reference for visualization
- Configurable physics parameters

### 2. Multi-Model Management
- **Robot**: Differential drive robot with wheels and caster
- **Obstacles**: Red wall barriers blocking direct paths
- **Target**: Green cylindrical target zone
- All models loaded from configuration

### 3. Physics Simulation
- Robot has mass, inertia, friction
- Wheels have revolute joints
- Caster has ball joint for smooth movement
- Collision detection active

### 4. Navigation System
- 4 waypoints defining path through course
- Distance calculation between positions
- State verification at each waypoint
- Arrival detection

### 5. Error Handling
- Environment validation before start
- World state verification
- Model existence checks
- Graceful cleanup on failure

## Course Layout

```
Start (0,0)
   ↓
Waypoint 1 (2,0)
   ↓
Waypoint 2 (4,0) → [Wall 1 blocks direct path]
   ↓
Waypoint 3 (4,2) → [Must navigate around]
   ↓
Target (6,2) → [Wall 2 blocks direct approach]
```

## Configuration

Edit `config.yaml` to customize:

### Robot Configuration
```yaml
robot:
  pose:
    position: [0.0, 0.0, 0.1]  # Starting position
  waypoints:
    - [2.0, 0.0]  # Waypoint 1
    - [4.0, 0.0]  # Waypoint 2
    - [4.0, 2.0]  # Waypoint 3
    - [6.0, 2.0]  # Final target
  max_velocity: 0.5  # m/s
```

### Obstacle Configuration
```yaml
wall_1:
  pose:
    position: [3.0, -1.0, 0.5]
  geometry:
    type: "box"
    size: [0.2, 4.0, 1.0]  # Thin tall wall
  color: [0.8, 0.2, 0.2, 1.0]  # Red
```

## Testing

Run unit tests:
```bash
pytest test_obstacle_course_demo.py -v
```

Or:
```bash
python3 test_obstacle_course_demo.py
```

Tests verify:
- Configuration validity
- File existence (world, robot model)
- Waypoint format
- Model definitions

## Troubleshooting

### "World file not found"
Check that `worlds/obstacle_course.sdf` exists:
```bash
ls worlds/obstacle_course.sdf
```

### "Robot model not found"
Check that `models/simple_robot.sdf` exists:
```bash
ls models/simple_robot.sdf
```

### "Gazebo not running"
Run the setup script:
```bash
./setup.sh
```

Or manually start Gazebo:
```bash
gz sim -r worlds/obstacle_course.sdf
```

### Service timeouts
- Verify bridge is running: `ps aux | grep ros_gz_bridge`
- Check services: `ros2 service list | grep /world/obstacle_course/`
- Increase timeout in config.yaml: `timeout: 60.0`

### Models don't spawn
- Check Gazebo logs: `/tmp/obstacle_course_gazebo.log`
- Check bridge logs: `/tmp/obstacle_course_bridge.log`
- Verify SDF syntax is valid

### Navigation fails
- Check robot spawned: Look in Gazebo GUI
- Verify waypoints are reachable
- Check for collision issues

## Advanced Customization

### Add More Obstacles
Edit `config.yaml`:
```yaml
models:
  wall_3:
    pose:
      position: [5.0, 3.0, 0.5]
    geometry:
      type: "box"
      size: [2.0, 0.2, 1.0]
    color: [0.8, 0.2, 0.2, 1.0]
    static: true
```

### Modify Robot Model
Edit `models/simple_robot.sdf` to change:
- Robot dimensions
- Wheel size and friction
- Mass and inertia
- Visual appearance

### Change Waypoints
Edit waypoint list in `config.yaml`:
```yaml
robot:
  waypoints:
    - [1.0, 1.0]
    - [2.0, 2.0]
    - [3.0, 1.0]
    - [4.0, 2.0]
    - [5.0, 2.0]  # Add more waypoints
```

### Adjust Physics
Edit `config.yaml` physics section:
```yaml
physics:
  gravity: [0.0, 0.0, -9.81]  # Standard Earth gravity
  max_step_size: 0.001  # 1ms timestep
  real_time_factor: 1.0  # Real-time speed
```

## Architecture

```
obstacle_course_demo.py
├── Uses: DemoExecutor (framework base)
├── Uses: DemoValidator (environment checks)
├── Uses: ConfigLoader (YAML config)
└── Uses: ModernGazeboAdapter (Gazebo operations)
    └── ros_gz_bridge → Modern Gazebo
        ├── World: obstacle_course.sdf
        ├── Robot: simple_robot.sdf
        └── Obstacles: Generated from config
```

## Cleanup

To stop Gazebo and bridge after demo:

If you used `setup.sh`:
```bash
# PIDs are saved
kill $(cat /tmp/obstacle_course_gazebo.pid)
kill $(cat /tmp/obstacle_course_bridge.pid)
```

Or force kill everything:
```bash
pkill -f 'gz sim'
pkill -f 'parameter_bridge'
```

## Next Steps

After completing this demo:
1. Add more complex obstacles
2. Implement actual velocity control (not teleportation)
3. Add collision detection logic
4. Implement path planning algorithms
5. Add sensor simulation (lidar, camera)
6. Create custom robot models

## Related Documentation

- `demos/framework/` - Demo framework implementation
- `demos/01_hello_world/` - Simpler introductory demo
- `ros2_gazebo_mcp/docs/DEPLOYMENT_GUIDE_MODERN_GAZEBO.md` - Gazebo setup
- `worlds/obstacle_course.sdf` - World definition
- `models/simple_robot.sdf` - Robot definition

## Performance Notes

- Typical completion time: 20-25 seconds
- 10 steps total
- 4 models spawned (robot + 2 walls + target)
- Physics running in real-time
- Bridge overhead: <10ms per operation

## Known Limitations

- Navigation uses teleportation (not physics-based movement)
- No collision avoidance logic
- No sensor feedback
- Simplified waypoint following

These limitations are intentional for demo purposes. Real robot navigation would require:
- Velocity commands to wheels
- PID control loops
- Sensor processing
- Path planning algorithms
- Collision detection and avoidance
