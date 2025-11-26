# Troubleshooting Guide

Common issues and solutions for running Gazebo MCP demos.

## Python Version Issues

### Error: `ModuleNotFoundError: No module named 'rclpy._rclpy_pybind11'`

**Symptom:**
```
ModuleNotFoundError: No module named 'rclpy._rclpy_pybind11'
The C extension '/opt/ros/humble/lib/python3.10/site-packages/_rclpy_pybind11.cpython-311-x86_64-linux-gnu.so' isn't present
```

**Cause:** You're using anaconda Python 3.11, but ROS2 Humble requires system Python 3.10.

**Solution 1 - Use wrapper script (Recommended):**
```bash
./run_demo_ros2.sh
```

This automatically uses system Python 3.10 with ROS2 environment.

**Solution 2 - Use system Python directly:**
```bash
source /opt/ros/humble/setup.bash
/usr/bin/python3 ./run_demo.py --run 1
```

**Solution 3 - Create alias:**
```bash
alias run-demo='source /opt/ros/humble/setup.bash && /usr/bin/python3 ./run_demo.py'
```

Then use:
```bash
run-demo --run 1
```

---

## ROS2 Environment Issues

### Error: `ROS2 not found` or `ros2: command not found`

**Solution:**
```bash
source /opt/ros/humble/setup.bash
```

Add to your `~/.bashrc` for automatic sourcing:
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

---

## Gazebo Issues

### Error: `Gazebo is not running`

**Solution:**
Start Gazebo first:

**For Hello World:**
```bash
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf
```

**For Obstacle Course:**
```bash
cd 02_obstacle_course
./setup.sh  # Automated setup
```

### Error: `gz: command not found`

**Solution:**
Install Modern Gazebo:
```bash
sudo apt install ignition-gazebo6
```

Or for newer versions:
```bash
sudo apt install gz-garden  # or gz-harmonic
```

---

## Bridge Issues

### Error: Service timeouts

**Symptoms:**
```
GazeboTimeoutError: Gazebo operation 'spawn_entity' timed out after 30.0s
```

**Solution 1 - Wait for bridge warmup:**
After starting ros_gz_bridge, wait 5 seconds before running demo.

**Solution 2 - Check services are available:**
```bash
ros2 service list | grep /world/
```

Should show services like:
```
/world/empty/control
/world/empty/create
/world/empty/remove
/world/empty/set_pose
```

**Solution 3 - Restart bridge:**
```bash
pkill -f parameter_bridge
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

**Solution 4 - Increase timeout:**
Edit config.yaml:
```yaml
timeout: 60.0  # Increase from 30.0
```

### Error: `ros_gz_bridge package not found`

**Solution:**
```bash
sudo apt install ros-humble-ros-gz-bridge ros-humble-ros-gz-interfaces
```

---

## Import Errors

### Error: `ModuleNotFoundError: No module named 'framework'`

**Cause:** Running from wrong directory.

**Solution:**
```bash
cd demos
./run_demo_ros2.sh
```

### Error: `ImportError: attempted relative import with no known parent package`

**Cause:** Python path issues.

**Solution:**
Use the provided launcher scripts instead of importing directly:
```bash
# ✓ Correct
./run_demo_ros2.sh --run 1

# ✗ Wrong
python3 01_hello_world/hello_world_demo.py
```

---

## Permission Errors

### Error: `Permission denied: './run_demo.py'`

**Solution:**
```bash
chmod +x run_demo.py
chmod +x run_demo_ros2.sh
chmod +x 01_hello_world/hello_world_demo.py
chmod +x 02_obstacle_course/obstacle_course_demo.py
chmod +x 02_obstacle_course/setup.sh
```

Or use the fix script:
```bash
find . -name "*.py" -exec chmod +x {} \;
find . -name "*.sh" -exec chmod +x {} \;
```

---

## Configuration Errors

### Error: `Config validation failed`

**Solution:**
Check YAML syntax:
```bash
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

Common YAML issues:
- Incorrect indentation (use 2 spaces, not tabs)
- Missing colons after keys
- Incorrect list syntax

### Error: `Model configuration not found`

**Cause:** Model name in code doesn't match config.yaml.

**Solution:**
Check model names in config.yaml match what's being requested:
```yaml
models:
  hello_box:  # This exact name must be used in code
    pose: ...
```

---

## World/Model File Issues

### Error: `World file not found`

**Solution for Obstacle Course:**
```bash
ls 02_obstacle_course/worlds/obstacle_course.sdf
```

If missing, the file should be at:
`/home/koen/workspaces/hackathon-git/demos/02_obstacle_course/worlds/obstacle_course.sdf`

### Error: `Robot model not found`

**Solution:**
```bash
ls 02_obstacle_course/models/simple_robot.sdf
```

### Error: Invalid SDF syntax

**Solution:**
Validate SDF:
```bash
xmllint --noout path/to/file.sdf
```

---

## Demo-Specific Issues

### Hello World Demo

**Issue:** Box doesn't spawn

**Checklist:**
1. Is Gazebo running? `ps aux | grep "gz sim"`
2. Is bridge running? `ps aux | grep parameter_bridge`
3. Are services available? `ros2 service list | grep /world/empty/`
4. Did you wait 5 seconds after starting bridge?

### Obstacle Course Demo

**Issue:** Setup script fails

**Solution:**
Check logs:
```bash
cat /tmp/obstacle_course_gazebo.log
cat /tmp/obstacle_course_bridge.log
```

**Issue:** Robot doesn't appear

**Solution:**
Verify robot model exists:
```bash
xmllint --noout 02_obstacle_course/models/simple_robot.sdf
```

---

## Testing Issues

### Error: `pytest: command not found`

**Solution:**
```bash
pip install pytest pytest-asyncio
```

### Error: Tests fail with import errors

**Solution:**
Make sure you're in the demos directory:
```bash
cd /home/koen/workspaces/hackathon-git/demos
pytest -v
```

---

## Quick Diagnostics

Run the verification script:
```bash
./verify_implementation.sh
```

Expected output: 22/22 checks pass

If checks fail, the script will show which components need fixing.

---

## Getting More Help

### Check Logs

**Gazebo logs:**
```bash
tail -f /tmp/gazebo.log
tail -f /tmp/obstacle_course_gazebo.log
```

**Bridge logs:**
```bash
tail -f /tmp/bridge.log
tail -f /tmp/obstacle_course_bridge.log
```

**ROS2 logs:**
```bash
ros2 daemon log
```

### Verify Environment

```bash
# Check ROS2
echo $ROS_DISTRO  # Should be "humble"
ros2 --version

# Check Gazebo
gz sim --version

# Check Python
which python3
python3 --version

# Check packages
ros2 pkg list | grep ros_gz
```

### Test Individual Components

**Test framework only:**
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from framework import ConfigLoader
config = ConfigLoader.load_demo_config('01_hello_world/config.yaml')
print('Framework works!')
"
```

**Test ROS2 services:**
```bash
# List services
ros2 service list

# Call service manually
ros2 service call /world/empty/control ros_gz_interfaces/srv/ControlWorld \
  "{world_control: {pause: false}}"
```

---

## Common Solutions Summary

| Issue | Quick Fix |
|-------|-----------|
| Python version | Use `./run_demo_ros2.sh` |
| ROS2 not found | `source /opt/ros/humble/setup.bash` |
| Gazebo not running | `gz sim world.sdf` |
| Bridge timeout | Wait 5s after starting bridge |
| Permission denied | `chmod +x *.py *.sh` |
| Import errors | Run from `demos/` directory |
| Service unavailable | Restart bridge |

---

## Still Having Issues?

1. Run verification: `./verify_implementation.sh`
2. Check all logs in `/tmp/`
3. Verify environment: ROS2, Gazebo, Python versions
4. Review documentation: `README.md`, `QUICKSTART.md`
5. Check test results: `pytest -v`

---

**Last Updated**: 2025-11-25
**Status**: Covers all known issues
