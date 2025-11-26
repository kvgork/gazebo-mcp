# Hello World Demo

Simple demonstration of basic Gazebo MCP operations.

## Overview

This demo demonstrates the fundamental operations of the Gazebo MCP system:
1. Environment validation
2. ROS2 initialization
3. Spawning a model
4. Moving a model
5. Deleting a model

## Prerequisites

- ROS2 Humble installed
- Modern Gazebo (Fortress/Garden/Harmonic)
- ros_gz_bridge package
- Gazebo running with ros_gz_bridge

## Setup

1. Start Modern Gazebo:
```bash
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf
```

2. In a new terminal, start ros_gz_bridge:
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose" \
  "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
```

3. Wait 2-3 seconds for bridge to initialize

## Running the Demo

```bash
cd demos/01_hello_world
./hello_world_demo.py
```

Or using Python:
```bash
python3 hello_world_demo.py
```

## Expected Output

```
======================================================================
  Hello World Demo
======================================================================
Demonstrates basic Gazebo MCP operations: spawn, move, delete

[Step 1/5] Validating environment...
  ✅ Validate environment (completed in 0.15s)

[Step 2/5] Initializing ROS2 and adapter...
  ✅ Initialize ROS2 and adapter (completed in 1.23s)

[Step 3/5] Spawning box model...
  ✅ Spawn box model (completed in 2.45s)

[Step 4/5] Moving box to new position...
  ✅ Move box to new position (completed in 1.87s)

[Step 5/5] Deleting box model...
  ✅ Delete box model (completed in 1.34s)

======================================================================
  Demo Summary
======================================================================
Total Duration:    7.04s
Steps Completed:   5/5 ✅
Steps Failed:      0/5 ❌

🎉 Demo completed successfully!
======================================================================
```

## What This Demonstrates

### 1. Environment Validation
- Checks for required commands (ros2, gz)
- Verifies ROS2 packages are installed
- Confirms Gazebo is running

### 2. ROS2 Integration
- Initializes ROS2 node
- Creates Modern Gazebo adapter
- Connects to Gazebo services via ros_gz_bridge

### 3. Model Spawning
- Generates simple box SDF inline
- Spawns box at configured position
- Validates spawn success

### 4. Model Manipulation
- Moves box to new position
- Updates entity state in simulation
- Demonstrates set_entity_state operation

### 5. Model Cleanup
- Deletes spawned model
- Cleans up resources
- Demonstrates delete_entity operation

## Configuration

Edit `config.yaml` to customize:

```yaml
models:
  hello_box:
    pose:
      position: [2.0, 0.0, 0.5]  # Initial spawn position
      orientation: [0.0, 0.0, 0.0, 1.0]
    new_position: [3.0, 1.0, 0.5]  # Position to move to
```

## Testing

Run unit tests:
```bash
pytest test_hello_world_demo.py -v
```

Or:
```bash
python3 test_hello_world_demo.py
```

## Troubleshooting

### "Gazebo is not running"
Start Gazebo first (see Setup step 1)

### "ros_gz_bridge package not found"
Install with:
```bash
sudo apt install ros-humble-ros-gz-bridge
```

### Service timeouts
- Verify bridge is running
- Wait a few seconds after starting bridge
- Check services are visible:
```bash
ros2 service list | grep /world/empty/
```

### "Model already exists"
If previous run didn't cleanup:
```bash
ros2 service call /world/empty/remove ros_gz_interfaces/srv/DeleteEntity \
  "{entity: {name: 'hello_box'}}"
```

## Architecture

```
hello_world_demo.py
├── Uses: DemoExecutor (framework base class)
├── Uses: DemoValidator (environment checks)
├── Uses: ConfigLoader (YAML config)
└── Uses: ModernGazeboAdapter (Gazebo operations)
    └── ros_gz_bridge → Modern Gazebo
```

## Next Steps

After completing this demo, try:
1. **Obstacle Course Demo** - More complex scenario with multiple models
2. Modify config.yaml to spawn different positions
3. Add more models to the demo
4. Experiment with different SDF geometries

## Related Documentation

- `demos/framework/` - Demo framework implementation
- `demos/02_obstacle_course/` - Advanced demo
- `ros2_gazebo_mcp/docs/DEPLOYMENT_GUIDE_MODERN_GAZEBO.md` - Gazebo setup
