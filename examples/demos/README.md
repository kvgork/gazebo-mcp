# ROS2 Gazebo MCP Server - Demonstrations

This directory contains comprehensive demonstrations showcasing the capabilities of the ROS2 Gazebo MCP Server.

---

## 📁 Contents

### Interactive Demonstrations
- **[interactive_demo.py](interactive_demo.py)** - Menu-driven interface for exploring all features

### Complete Scenarios
- **[01_complete_navigation_demo.py](01_complete_navigation_demo.py)** - End-to-end navigation setup workflow
- **[06_world_generation_showcase.py](06_world_generation_showcase.py)** - Comprehensive world generation features

### World Files
- **[worlds/](worlds/)** - Generated world files from demonstrations

---

## 🚀 Quick Start

### Run the Interactive Demo

The easiest way to explore features:

```bash
python3 interactive_demo.py
```

This provides a menu-driven interface where you can:
- Create worlds with various features
- Spawn and manage models
- Monitor sensors
- Run complete scenarios
- Get help and explanations

**Perfect for:** First-time users, exploration, learning

---

## 📋 Demonstration Index

### 1. Complete Navigation Demo

**File:** `01_complete_navigation_demo.py`
**Duration:** ~5 minutes
**Complexity:** ⭐⭐ Moderate

**What it demonstrates:**
- World generation with obstacle course
- TurtleBot3 spawning
- Sensor configuration
- Robot state monitoring
- Model management

**Run it:**
```bash
python3 01_complete_navigation_demo.py
```

**Expected output:**
- Navigation world with maze obstacles
- Spawned TurtleBot3 robot
- Sensor status reports
- Model list
- Exported world file

**Use case:** Complete workflow from world creation to robot deployment

---

### 6. World Generation Showcase

**File:** `06_world_generation_showcase.py`
**Duration:** ~3-5 minutes
**Complexity:** ⭐⭐⭐ Advanced

**What it demonstrates:**
- All obstacle patterns (maze, grid, circular)
- Advanced lighting (volumetric, shadows)
- Animation system (3 types)
- Trigger zones (3 shapes)
- Environmental effects (fog, wind)
- Reproducible benchmark worlds

**Run it:**
```bash
# Basic showcase (no file export)
python3 06_world_generation_showcase.py

# Export all generated worlds
python3 06_world_generation_showcase.py --export-all
```

**Expected output:**
- Demonstration of all world generation features
- Summary of capabilities
- Optional: Exported world files

**Use case:** Comprehensive feature overview, learning advanced capabilities

---

### Interactive Demo

**File:** `interactive_demo.py`
**Duration:** User-paced
**Complexity:** ⭐ Beginner-friendly

**What it demonstrates:**
- All features through menu interface
- Step-by-step guidance
- Custom parameter selection
- Real-time feedback

**Run it:**
```bash
python3 interactive_demo.py
```

**Features:**
1. **World Generation Menu**
   - Simple worlds
   - Obstacle courses
   - Advanced features
   - World export

2. **Model Management Menu**
   - Model spawning
   - State monitoring
   - Model deletion
   - Model listing

3. **Sensor Monitoring Menu**
   - Camera reading (placeholder)
   - Lidar scanning (placeholder)
   - IMU data (placeholder)

4. **Complete Scenarios**
   - Pre-configured workflows
   - Automated setup
   - Guided execution

5. **Help System**
   - Feature explanations
   - Usage guidance
   - Documentation links

**Use case:** Learning, exploration, custom workflows

---

## 🎯 Demonstration Objectives

### For New Users
- **Start with:** `interactive_demo.py`
- **Then try:** `01_complete_navigation_demo.py`
- **Finally:** `06_world_generation_showcase.py`

### For Developers
- **Integration examples:** `01_complete_navigation_demo.py`
- **API usage patterns:** All demonstrations
- **Feature reference:** `06_world_generation_showcase.py`

### For Decision Makers
- **Capability overview:** `06_world_generation_showcase.py`
- **Complete workflow:** `01_complete_navigation_demo.py`
- **Ease of use:** `interactive_demo.py`

---

## 📊 Feature Coverage

| Feature | Demo 1 | Demo 6 | Interactive |
|---------|:------:|:------:|:-----------:|
| **World Generation** |
| Basic world creation | ✅ | ✅ | ✅ |
| Obstacle patterns | ✅ | ✅ | ✅ |
| Lighting | ✅ | ✅ | ✅ |
| Fog effects | ❌ | ✅ | ✅ |
| Wind system | ❌ | ✅ | ✅ |
| Animations | ❌ | ✅ | ✅ |
| Trigger zones | ❌ | ✅ | ✅ |
| **Model Management** |
| Model spawning | ✅ | ❌ | ✅ |
| State monitoring | ✅ | ❌ | ✅ |
| Model deletion | ❌ | ❌ | ✅ |
| Model listing | ✅ | ❌ | ✅ |
| **Sensors** |
| Camera | ✅ | ❌ | ℹ️ |
| Lidar | ✅ | ❌ | ℹ️ |
| IMU | ✅ | ❌ | ℹ️ |

**Legend:**
- ✅ Fully demonstrated
- ℹ️ Menu available (requires setup)
- ❌ Not included

---

## 🛠️ Requirements

### Minimum Requirements
- Python 3.8+
- ROS2 Gazebo MCP Server installed

### For Full Functionality
- Gazebo simulator (for visualization)
- ROS2 (for robot control)
- TurtleBot3 models (for robot demonstrations)

### Python Dependencies
All required dependencies are in `requirements.txt`:
```bash
pip install -r ../../requirements.txt
```

---

## 📖 Usage Patterns

### Pattern 1: Quick Feature Test

Want to quickly test a specific feature?

```python
from gazebo_mcp.tools.world_generation import WorldGenerator

gen = WorldGenerator()
gen.create_world(name="test_world", description="Quick test")
gen.add_ground_plane(size=(10.0, 10.0))
# Add your feature here
sdf = gen.export_world()
```

### Pattern 2: Complete Workflow

Need a complete setup?

1. Run `01_complete_navigation_demo.py`
2. Modify for your use case
3. Export world
4. Use in your application

### Pattern 3: Interactive Exploration

Not sure what you need?

1. Run `interactive_demo.py`
2. Explore features interactively
3. Note what you used
4. Implement in your code

---

## 🎓 Learning Path

### Beginner
1. **Start:** Read `docs/tutorials/GETTING_STARTED.md`
2. **Practice:** Run `interactive_demo.py`
3. **Explore:** Try `01_complete_navigation_demo.py`

### Intermediate
1. **Study:** Analyze demo source code
2. **Modify:** Customize parameters in demos
3. **Create:** Build your own demonstration

### Advanced
1. **Deep dive:** `06_world_generation_showcase.py`
2. **Integrate:** Use in your applications
3. **Extend:** Create custom features

---

## 💡 Tips and Best Practices

### World Generation
```python
# ✅ Good: Clear, descriptive names
gen.create_world(name="navigation_course", description="Obstacle course for testing")

# ❌ Avoid: Generic names
gen.create_world(name="world1", description="test")
```

### Model Spawning
```python
# ✅ Good: Check result status
result = spawn_model(...)
if result.success:
    # Proceed
else:
    # Handle error: result.error

# ❌ Avoid: Ignoring errors
spawn_model(...)  # What if it fails?
```

### Resource Management
```python
# ✅ Good: Export worlds for reuse
sdf = gen.export_world()
Path("my_world.sdf").write_text(sdf)

# ✅ Good: Delete models when done
delete_model(model_name="test_robot")
```

---

## 🔧 Customization

### Modify Demo Parameters

All demonstrations use clear variable names. Example:

```python
# In 01_complete_navigation_demo.py

# Change obstacle count
num_obstacles=15  # Change to 20, 30, etc.

# Change difficulty
difficulty="medium"  # Change to "low" or "high"

# Change pattern
pattern="maze"  # Change to "grid", "circular"
```

### Create Your Own Demo

Template:

```python
#!/usr/bin/env python3
"""My Custom Demo"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.world_generation import WorldGenerator
# Import other tools as needed

def main():
    # Your demo code here
    print("Running my custom demo...")

    # Create world
    gen = WorldGenerator()
    gen.create_world(name="custom", description="My custom world")

    # Add features
    # ...

    # Export
    sdf = gen.export_world()
    Path("custom_world.sdf").write_text(sdf)

    print("✅ Demo complete!")

if __name__ == "__main__":
    main()
```

---

## 📊 Performance Notes

### Demo 1: Complete Navigation
- **Runtime:** ~2-5 seconds (without Gazebo)
- **Memory:** < 100 MB
- **Output:** ~2-5 KB world file

### Demo 6: World Generation Showcase
- **Runtime:** ~3-8 seconds
- **Memory:** < 150 MB
- **Output:** 10-15 world files (~20-50 KB each) with `--export-all`

### Interactive Demo
- **Runtime:** User-paced
- **Memory:** < 100 MB
- **Output:** Varies based on user actions

---

## 🆘 Troubleshooting

### Problem: "ModuleNotFoundError"

```bash
# Solution: Add project to Python path
cd /path/to/ros2_gazebo_mcp
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 examples/demos/interactive_demo.py
```

### Problem: "Failed to spawn model"

**Causes:**
- Gazebo not running
- Wrong model name
- Model already exists

**Solutions:**
1. Start Gazebo first
2. Check model type spelling
3. Use unique model names

### Problem: Demo runs but no output files

**Cause:** Wrong working directory

**Solution:**
```bash
# Run from project root
cd ros2_gazebo_mcp
python3 examples/demos/01_complete_navigation_demo.py
```

---

## 📝 Contributing

Want to add a demonstration?

1. **Create your demo script** in `examples/demos/`
2. **Follow naming convention:** `NN_description_demo.py`
3. **Include docstring** with description and usage
4. **Update this README** with your demo details
5. **Add to feature coverage table**
6. **Test thoroughly**

---

## 📚 Related Documentation

- **Getting Started Tutorial:** `docs/tutorials/GETTING_STARTED.md`
- **API Reference:** `docs/API_REFERENCE.md`
- **Other Examples:** `examples/` (root examples directory)
- **Advanced Tutorials:** `docs/tutorials/`
- **Implementation Plan:** `docs/PHASE7_IMPLEMENTATION_PLAN.md`

---

## ✅ Demonstration Checklist

Use this checklist when running demonstrations:

- [ ] Python environment activated
- [ ] Project dependencies installed
- [ ] In correct directory (project root)
- [ ] Gazebo installed (if visualizing)
- [ ] Sufficient disk space for world exports
- [ ] Read demonstration description
- [ ] Understood expected output

---

## 🎉 Success Criteria

You'll know the demonstrations are working when:

✅ **Demo 1:** Creates world, spawns robot, exports world file
✅ **Demo 6:** Shows all features, optionally exports 10+ worlds
✅ **Interactive:** Menu appears, options work, provides feedback

---

**Questions? Issues?**
- Check troubleshooting section above
- Review `docs/tutorials/GETTING_STARTED.md`
- Examine source code (well-commented)
- Consult `docs/API_REFERENCE.md`

**Ready to explore?** Start with `interactive_demo.py`! 🚀
