# Getting Started with ROS2 Gazebo MCP Server

**Estimated Time:** 15-20 minutes
**Difficulty:** Beginner
**Prerequisites:** Python 3.8+, ROS2 installed (optional for basic usage)

---

## 🎯 What You'll Learn

By the end of this tutorial, you'll be able to:
- ✅ Verify your MCP server installation
- ✅ Create your first simulation world
- ✅ Spawn a robot model
- ✅ Read sensor data
- ✅ Export worlds for use in Gazebo

---

## 📋 Step 1: Verify Installation

First, let's make sure everything is installed correctly.

### Check Python Installation

```bash
python3 --version
# Should show Python 3.8 or higher
```

### Verify MCP Server Installation

```bash
cd ros2_gazebo_mcp
python3 -c "from gazebo_mcp.tools.world_generation import WorldGenerator; print('✅ Installation OK!')"
```

If you see `✅ Installation OK!`, you're ready to go!

**Troubleshooting:**
- If you get `ModuleNotFoundError`, make sure you're in the project directory
- Check that `src/` directory exists with `gazebo_mcp/` inside it

---

## 📋 Step 2: Create Your First World

Let's create a simple world with a ground plane and some lighting.

### Create a Python Script

Create a file called `my_first_world.py`:

```python
#!/usr/bin/env python3
"""My First World - Getting Started Tutorial"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.world_generation import WorldGenerator

def main():
    # Create world generator
    print("Creating world generator...")
    generator = WorldGenerator()

    # Create world
    print("Creating world...")
    result = generator.create_world(
        name="my_first_world",
        description="My first simulation world"
    )
    print(f"✅ World created: {result['name']}")

    # Add ground plane
    print("Adding ground plane...")
    generator.add_ground_plane(
        size=(20.0, 20.0),  # 20m x 20m
        material="concrete"
    )
    print("✅ Ground plane added")

    # Add sun light
    print("Adding sun light...")
    generator.add_light(
        name="sun",
        light_type="directional",
        pose={
            "position": [0, 0, 10],
            "orientation": [0, 0, 0]
        },
        intensity=1.0,
        cast_shadows=True
    )
    print("✅ Sun light added")

    # Export world
    print("Exporting world...")
    sdf_content = generator.export_world()

    output_path = Path("my_first_world.sdf")
    output_path.write_text(sdf_content)
    print(f"✅ World exported to: {output_path.absolute()}")
    print(f"   File size: {len(sdf_content)} bytes")

    print("\n🎉 Success! Your first world is ready!")
    print(f"\nTo view it in Gazebo:")
    print(f"  gazebo {output_path.absolute()}")

if __name__ == "__main__":
    main()
```

### Run the Script

```bash
python3 my_first_world.py
```

**Expected Output:**
```
Creating world generator...
Creating world...
✅ World created: my_first_world
Adding ground plane...
✅ Ground plane added
Adding sun light...
✅ Sun light added
Exporting world...
✅ World exported to: /path/to/my_first_world.sdf
   File size: 1234 bytes

🎉 Success! Your first world is ready!
```

**What Just Happened?**
- Created a `WorldGenerator` object
- Created a world with name and description
- Added a 20m x 20m concrete ground plane
- Added directional sun lighting with shadows
- Exported the world to an SDF file

---

## 📋 Step 3: Add Some Obstacles

Let's make our world more interesting by adding obstacles.

### Add Obstacles to Your Script

Add this code before the export section:

```python
    # Add obstacles
    print("Adding obstacle course...")
    result = generator.add_obstacle_course(
        pattern="grid",
        difficulty="low",
        num_obstacles=8,
        area_size=(10.0, 10.0),
        center=(0.0, 0.0)
    )
    print(f"✅ Added {result['obstacles_added']} obstacles")
```

### Run Again

```bash
python3 my_first_world.py
```

Now your world has 8 obstacles arranged in a grid pattern!

**Pattern Options:**
- `"grid"` - Structured grid layout
- `"maze"` - Maze-like pattern
- `"circular"` - Circular arrangement
- `"random"` - Random placement

**Difficulty Levels:**
- `"low"` - Easy navigation
- `"medium"` - Moderate challenge
- `"high"` - Difficult navigation

---

## 📋 Step 4: Spawn a Robot Model

Now let's add a robot to our world.

### Create Robot Spawning Script

Create `spawn_robot.py`:

```python
#!/usr/bin/env python3
"""Spawn Robot - Getting Started Tutorial"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.model_management import spawn_model, get_model_state

def main():
    print("Spawning TurtleBot3...")

    # Spawn robot
    result = spawn_model(
        model_name="my_robot",
        model_type="turtlebot3_burger",
        pose={
            "position": [0.0, 0.0, 0.1],  # x, y, z
            "orientation": [0, 0, 0]      # roll, pitch, yaw
        },
        is_static=False  # Robot can move
    )

    if result.success:
        print("✅ Robot spawned successfully!")
        print(f"   Name: my_robot")
        print(f"   Type: turtlebot3_burger")
        print(f"   Position: (0.0, 0.0, 0.1)")

        # Get robot state
        print("\nGetting robot state...")
        state_result = get_model_state(model_name="my_robot")

        if state_result.success:
            print("✅ Robot state retrieved")
            # You can access position, orientation, velocity, etc.

    else:
        print(f"❌ Failed to spawn robot: {result.error}")
        print("\n💡 Tip: Make sure Gazebo is running with your world loaded")

if __name__ == "__main__":
    main()
```

### Run the Script

**Important:** You need Gazebo running with your world loaded first!

```bash
# Terminal 1: Start Gazebo with your world
gazebo my_first_world.sdf

# Terminal 2: Spawn the robot
python3 spawn_robot.py
```

**Available Robot Models:**
- `turtlebot3_burger` - Small, nimble robot
- `turtlebot3_waffle` - Larger robot with more sensors
- Also supports: `box`, `sphere`, `cylinder` for simple objects

---

## 📋 Step 5: Monitor Sensors

Let's read data from the robot's sensors.

### Create Sensor Monitoring Script

Create `monitor_sensors.py`:

```python
#!/usr/bin/env python3
"""Monitor Sensors - Getting Started Tutorial"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.sensor_tools import (
    get_camera_image,
    get_lidar_scan,
    get_imu_data
)

def main():
    robot_name = "my_robot"

    print("Monitoring robot sensors...")
    print("-" * 60)

    # Get camera data
    print("\n📷 Camera:")
    try:
        result = get_camera_image(
            model_name=robot_name,
            camera_name="camera",
            response_format="summary"
        )

        if result.success:
            data = result.data
            print(f"   Status: Active")
            print(f"   Image size: {data.get('width')}x{data.get('height')}")
            print(f"   Format: {data.get('encoding')}")
        else:
            print(f"   Status: {result.error}")
    except Exception as e:
        print(f"   Status: Not available ({e})")

    # Get lidar data
    print("\n📡 Lidar:")
    try:
        result = get_lidar_scan(
            model_name=robot_name,
            lidar_name="lidar",
            response_format="summary"
        )

        if result.success:
            data = result.data
            print(f"   Status: Active")
            print(f"   Ranges: {data.get('range_count')}")
            print(f"   Min range: {data.get('range_min')} m")
            print(f"   Max range: {data.get('range_max')} m")
        else:
            print(f"   Status: {result.error}")
    except Exception as e:
        print(f"   Status: Not available ({e})")

    # Get IMU data
    print("\n🧭 IMU:")
    try:
        result = get_imu_data(
            model_name=robot_name,
            imu_name="imu",
            response_format="summary"
        )

        if result.success:
            print(f"   Status: Active")
            print(f"   Orientation: Available")
            print(f"   Angular velocity: Available")
            print(f"   Linear acceleration: Available")
        else:
            print(f"   Status: {result.error}")
    except Exception as e:
        print(f"   Status: Not available ({e})")

    print("\n" + "-" * 60)
    print("✅ Sensor monitoring complete!")

if __name__ == "__main__":
    main()
```

### Run Sensor Monitoring

```bash
# With Gazebo running and robot spawned:
python3 monitor_sensors.py
```

**Note:** Sensors become active once the simulation is running. If you get "Not available", make sure:
1. Gazebo is running
2. The robot is spawned
3. The simulation is not paused

---

## 📋 Step 6: Try the Interactive Demo

Want to explore more features? Try our interactive demo!

```bash
cd examples/demos
python3 interactive_demo.py
```

This menu-driven demo lets you:
- Create worlds with different features
- Spawn and manage models
- Monitor sensors interactively
- Run complete scenarios

---

## 🎯 Next Steps

Congratulations! You've learned the basics. Here's what to try next:

### 1. Explore More Examples

```bash
cd examples
ls *.py
```

Try these examples:
- `01_basic_operations.py` - More MCP operations
- `02_model_spawning.py` - Advanced model spawning
- `03_sensor_monitoring.py` - Comprehensive sensor usage
- `demos/06_world_generation_showcase.py` - All world generation features

### 2. Advanced Tutorials

Check out more advanced tutorials:
- `docs/tutorials/NAVIGATION_SCENARIOS.md` - Building navigation worlds
- `docs/tutorials/ADVANCED_WORLD_GENERATION.md` - Complex world features
- `docs/tutorials/MULTI_ROBOT.md` - Multiple robot coordination

### 3. Explore Advanced Features

Try adding:
- **Fog effects:** `generator.add_fog(...)`
- **Wind simulation:** `generator.add_wind(...)`
- **Animated obstacles:** `generator.add_animated_obstacle(...)`
- **Trigger zones:** `generator.add_trigger_zone(...)`

See `docs/API_REFERENCE.md` for complete API documentation.

### 4. Run Complete Demos

```bash
cd examples/demos
python3 01_complete_navigation_demo.py
```

---

## 🆘 Troubleshooting

### Problem: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure you're in the project directory
cd ros2_gazebo_mcp

# Verify src/ exists
ls src/gazebo_mcp/

# Try installing in development mode
pip install -e .
```

### Problem: "Failed to spawn robot"

**Possible causes:**
1. Gazebo not running
2. World not loaded
3. Model name conflict

**Solution:**
```bash
# Make sure Gazebo is running
gazebo my_first_world.sdf

# Try a different model name
# Or delete existing model first
```

### Problem: "Sensors not available"

**Solution:**
- Ensure simulation is running (not paused)
- Wait a few seconds after spawning for sensors to initialize
- Check that robot model includes sensors (use turtlebot3_burger or turtlebot3_waffle)

### Problem: "ROS2 not found"

**Note:** ROS2 is optional for basic world generation and MCP operations. You only need ROS2 for:
- Controlling robots
- Advanced sensor integration
- Real-time simulation control

Basic MCP functionality works without ROS2.

---

## 📚 Additional Resources

- **API Documentation:** `docs/API_REFERENCE.md`
- **Complete Examples:** `examples/`
- **Deployment Guide:** `docs/DEPLOYMENT.md`
- **Performance Tuning:** `docs/METRICS.md`

---

## ✅ Tutorial Complete!

You now know how to:
- ✅ Create simulation worlds
- ✅ Add obstacles and features
- ✅ Spawn robot models
- ✅ Monitor sensors
- ✅ Export worlds for Gazebo

**Ready for more?** Check out the other tutorials in `docs/tutorials/`!

---

**Need Help?**
- Check the troubleshooting section above
- Review example scripts in `examples/`
- Consult API documentation in `docs/`

Happy simulating! 🚀
