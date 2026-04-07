# Demos Index

Complete index of all demo files and documentation.

## 📚 Documentation (Start Here)

| Document | Purpose | Audience |
|----------|---------|----------|
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute quick start | All users (start here!) |
| **[README.md](README.md)** | Complete guide & reference | All users |
| **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** | Implementation details | Developers |
| **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** | Deployment status & metrics | DevOps/Management |
| **[INDEX.md](INDEX.md)** | This file | Navigation |

## 🚀 Quick Actions

```bash
# Run interactive launcher
./run_demo.py

# Run specific demo
./run_demo.py --run 1    # Hello World
./run_demo.py --run 2    # Obstacle Course

# Verify installation
./verify_implementation.sh

# List all demos
./run_demo.py --list

# Get setup help
./run_demo.py --setup 1
```

## 📁 Directory Structure

```
demos/
├── 📘 Documentation
│   ├── QUICKSTART.md              # Quick start (5 min)
│   ├── README.md                  # Complete guide
│   ├── IMPLEMENTATION_COMPLETE.md # Implementation details
│   ├── DEPLOYMENT_STATUS.md       # Status & metrics
│   └── INDEX.md                   # This file
│
├── 🎯 Demos
│   ├── 01_hello_world/            # Demo 1: Hello World
│   │   ├── hello_world_demo.py    # Main demo (268 lines)
│   │   ├── config.yaml            # Configuration
│   │   ├── test_hello_world_demo.py # Unit tests
│   │   └── README.md              # Demo documentation
│   │
│   └── 02_obstacle_course/        # Demo 2: Obstacle Course
│       ├── obstacle_course_demo.py # Main demo (545 lines)
│       ├── config.yaml            # Configuration
│       ├── setup.sh               # Automated setup
│       ├── test_obstacle_course_demo.py # Unit tests
│       ├── README.md              # Demo documentation
│       ├── worlds/
│       │   └── obstacle_course.sdf # Gazebo world
│       └── models/
│           └── simple_robot.sdf   # Robot model
│
├── 🔧 Framework
│   └── framework/                 # Reusable framework
│       ├── __init__.py            # Package exports
│       ├── demo_executor.py       # Base executor (210 lines)
│       ├── demo_validator.py      # Validation (271 lines)
│       └── config_loader.py       # Config management (227 lines)
│
├── 🛠️ Tools
│   ├── run_demo.py                # Unified launcher (236 lines)
│   └── verify_implementation.sh   # Verification script
│
└── ⚙️ CI/CD
    └── .github/workflows/
        └── demo-tests.yml         # Automated testing

Total: 22 files, ~4,800 lines of code
```

## 🎮 Demo Quick Reference

### Demo 1: Hello World

**Duration**: ~10 seconds
**Difficulty**: Beginner
**Steps**: 5

**What it does**:
1. Validates environment
2. Spawns a box
3. Moves the box
4. Deletes the box

**Quick start**:
```bash
# Setup (3 commands)
gz sim /usr/share/gz/gz-sim8/worlds/empty.sdf  # Terminal 1
ros2 run ros_gz_bridge parameter_bridge ...    # Terminal 2
./run_demo.py --run 1                          # Terminal 3
```

**Documentation**: [01_hello_world/README.md](01_hello_world/README.md)

---

### Demo 2: Obstacle Course

**Duration**: ~25 seconds
**Difficulty**: Intermediate
**Steps**: 10

**What it does**:
1. Validates environment
2. Spawns obstacles (walls)
3. Spawns target zone
4. Spawns robot
5. Navigates through 4 waypoints

**Quick start**:
```bash
# Setup (2 commands)
cd 02_obstacle_course
./setup.sh                    # Terminal 1 (automated!)
./obstacle_course_demo.py     # Terminal 2
```

**Documentation**: [02_obstacle_course/README.md](02_obstacle_course/README.md)

## 🧪 Testing

### Run All Tests

```bash
pytest -v
```

### Run Demo-Specific Tests

```bash
# Hello World
pytest 01_hello_world/test_hello_world_demo.py -v

# Obstacle Course
pytest 02_obstacle_course/test_obstacle_course_demo.py -v
```

### Verification

```bash
./verify_implementation.sh
```

**Expected**: 22/22 checks pass ✅

## 📦 Framework API

### DemoExecutor

Base class for all demos.

```python
from framework import DemoExecutor

class MyDemo(DemoExecutor):
    def __init__(self, config_path):
        super().__init__("My Demo", "Description")
        self.register_step(
            name="Step name",
            active_name="Doing step",
            execute=self._step_1,
            timeout=30.0
        )

    async def _step_1(self):
        return {"success": True}

    async def setup(self):
        pass

    async def teardown(self):
        pass
```

### DemoValidator

Environment validation utilities.

```python
from framework import DemoValidator

# Check command exists
result = DemoValidator.check_command_exists("ros2")

# Check ROS2 package
result = DemoValidator.check_ros2_package("ros_gz_bridge")

# Check file exists
result = DemoValidator.check_file_exists("/path/to/file.sdf")

# Validate full environment
checks = [
    ("ROS2", lambda: DemoValidator.check_command_exists("ros2")),
    ("Gazebo", lambda: DemoValidator.check_gazebo_process()),
]
all_passed, results = DemoValidator.validate_demo_environment(checks)
```

### ConfigLoader

YAML configuration management.

```python
from framework import ConfigLoader

# Load config
config = ConfigLoader.load_demo_config("config.yaml")

# Get model config
model_config = ConfigLoader.get_model_config(config, "robot")

# Get pose
pose = ConfigLoader.get_model_pose(config, "robot")

# Validate
is_valid, errors = ConfigLoader.validate_config(config)
```

## 🎯 Common Tasks

### Run a Demo

```bash
./run_demo.py --run 1
```

### List Available Demos

```bash
./run_demo.py --list
```

### Get Setup Help

```bash
./run_demo.py --setup 2
```

### Verify Installation

```bash
./verify_implementation.sh
```

### Run Tests

```bash
pytest -v
```

### Create New Demo

1. Copy demo structure
2. Extend DemoExecutor
3. Create config.yaml
4. Write tests
5. Update run_demo.py
6. Document in README

See [README.md#creating-new-demos](README.md#creating-new-demos)

## 🔍 Troubleshooting

### Quick Fixes

| Issue | Solution |
|-------|----------|
| "ROS2 not found" | `source /opt/ros/humble/setup.bash` |
| "Gazebo not running" | Start Gazebo first |
| Service timeouts | Wait 5s after bridge starts |
| Import errors | Check Python path, source ROS2 |

### Debug Mode

```bash
export DEMO_DEBUG=1
./run_demo.py --run 1
```

### Get Help

1. Check [QUICKSTART.md](QUICKSTART.md)
2. Read demo-specific README
3. Run verification script
4. Check [full README](README.md)

## 📊 Statistics

| Metric | Value |
|--------|-------|
| Total files | 22 |
| Total lines | ~4,800 |
| Demos | 2 |
| Documentation | 5 files |
| Test files | 2 |
| Framework modules | 3 |
| CI/CD jobs | 3 |
| Verification checks | 22 |

## ✅ Status

- **Implementation**: ✅ Complete
- **Testing**: ✅ 22/22 checks pass
- **Documentation**: ✅ Comprehensive
- **Deployment**: ✅ Production ready
- **Quality**: ✅ High

## 🚦 Next Steps

1. **New User**:
   - Read [QUICKSTART.md](QUICKSTART.md)
   - Run Hello World demo
   - Try Obstacle Course

2. **Developer**:
   - Read [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)
   - Study framework code
   - Create new demo

3. **DevOps**:
   - Review [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)
   - Check CI/CD pipeline
   - Plan deployment

## 📞 Support

- **Documentation**: Start with [QUICKSTART.md](QUICKSTART.md)
- **Issues**: Check troubleshooting sections
- **Questions**: Review [README.md](README.md)

---

**Last Updated**: 2025-11-25
**Version**: 1.0.0
**Status**: Production Ready ✅
