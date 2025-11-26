# Quick Start Guide

Get up and running with Gazebo MCP demos in 5 minutes!

## Prerequisites Check

```bash
# Check ROS2
ros2 --version

# Check Gazebo
gz sim --version

# Check ros_gz_bridge
ros2 pkg list | grep ros_gz_bridge
```

If any command fails, see [full setup instructions](README.md#system-requirements).

## Option 1: Hello World (10 seconds)

Simple demo, great for first-time users.

### Setup (3 commands)

```bash
# Terminal 1: Start Gazebo
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf

# Terminal 2: Start bridge
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"

# Wait 3 seconds for bridge warmup

# Terminal 3: Run demo
cd demos
./run_demo.py --run 1
```

### Expected Output

```
======================================================================
  Hello World Demo
======================================================================
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

🎉 Demo completed successfully!
```

## Option 2: Obstacle Course (25 seconds)

Advanced demo with robot navigation.

### Setup (2 commands)

```bash
# Terminal 1: Automated setup
cd demos/02_obstacle_course
./setup.sh

# Wait for "Environment is ready!" message

# Terminal 2 (or same terminal): Run demo
./obstacle_course_demo.py
```

### Expected Output

```
======================================================================
  Obstacle Course Challenge
======================================================================
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
...
[Step 10/10] Reaching final target...
  ✅ Reach final target (completed in 2.45s)

🎉 Demo completed successfully!
```

## Troubleshooting

### "Command not found: ros2"

```bash
source /opt/ros/humble/setup.bash
```

### "Gazebo not running"

Start Gazebo first (see setup steps above).

### Service timeouts

Wait 5 seconds after starting bridge before running demo.

### Still stuck?

```bash
# Run verification
cd demos
./verify_implementation.sh

# Check detailed README
cat README.md
```

## Next Steps

- Read full documentation: [demos/README.md](README.md)
- Try customizing configs: `01_hello_world/config.yaml`
- Create your own demo: Follow [framework guide](README.md#creating-new-demos)

---

**Total Time**: 5 minutes to first demo ⚡
