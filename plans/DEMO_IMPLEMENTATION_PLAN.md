# Demo Implementation Plan - Execution-Focused

**Created**: 2025-11-25
**Timeline**: 2-3 weeks
**Status**: Ready for implementation

---

## Executive Summary

Complete implementation of two demonstration scenarios for the Gazebo MCP server:
- **Demo 1**: Hello World (5 min, beginner audience) - 40% complete
- **Demo 2**: Obstacle Course (10 min, technical audience) - 0% complete

**Current State**: Modern Gazebo adapter fully functional (11/11 tests passing), demo scripts written, Demo 1 setup files ready.

**Deliverables**: Production-ready demos with execution scripts, tests, documentation, and unified launcher.

---

## Phase 1: Demo Framework (Days 1-3)

### Objective
Build reusable demo execution framework to avoid code duplication between demos.

### Tasks

#### 1.1: Create Base Framework Classes
**File**: `demos/framework/demo_executor.py`

```python
"""Base demo executor with step management and error handling."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Optional
import asyncio
import time


@dataclass
class DemoStep:
    """Represents a single demo step."""
    name: str
    active_name: str  # Present tense for display
    execute: Callable
    validate: Optional[Callable] = None
    timeout: float = 30.0
    critical: bool = True  # If False, failure is logged but demo continues


class DemoExecutor(ABC):
    """Base class for all demo implementations."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.steps: List[DemoStep] = []
        self.current_step = 0
        self.start_time = None
        self.results = {}

    def register_step(self, step: DemoStep):
        """Register a demo step."""
        self.steps.append(step)

    async def execute(self) -> bool:
        """Execute all registered steps."""
        self.start_time = time.time()
        print(f"\n{'='*60}")
        print(f"  {self.name}")
        print(f"{'='*60}\n")

        for i, step in enumerate(self.steps, 1):
            self.current_step = i
            success = await self._execute_step(step, i)

            if not success and step.critical:
                print(f"\n❌ Demo failed at step {i}/{len(self.steps)}")
                return False

        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"✅ Demo completed successfully in {elapsed:.1f}s")
        print(f"{'='*60}\n")
        return True

    async def _execute_step(self, step: DemoStep, step_num: int) -> bool:
        """Execute a single step with timing and error handling."""
        total = len(self.steps)
        print(f"[{step_num}/{total}] {step.active_name}...", end=" ", flush=True)

        step_start = time.time()
        try:
            result = await asyncio.wait_for(step.execute(), timeout=step.timeout)
            elapsed = time.time() - step_start

            if result:
                print(f"✓ ({elapsed:.1f}s)")
                self.results[step.name] = {"success": True, "time": elapsed}
                return True
            else:
                print(f"✗ ({elapsed:.1f}s)")
                self.results[step.name] = {"success": False, "time": elapsed}
                return False

        except asyncio.TimeoutError:
            print(f"✗ (timeout after {step.timeout}s)")
            self.results[step.name] = {"success": False, "error": "timeout"}
            return False
        except Exception as e:
            print(f"✗ (error: {str(e)})")
            self.results[step.name] = {"success": False, "error": str(e)}
            return False

    @abstractmethod
    async def setup(self):
        """Setup demo environment (implement in subclass)."""
        pass

    @abstractmethod
    async def teardown(self):
        """Cleanup after demo (implement in subclass)."""
        pass
```

#### 1.2: Create Validation Utilities
**File**: `demos/framework/demo_validator.py`

```python
"""Validation utilities for demo environment checks."""
import subprocess
import os
from typing import List, Tuple


class DemoValidator:
    """Environment validation for demos."""

    @staticmethod
    def check_command_exists(command: str) -> bool:
        """Check if a command is available."""
        return subprocess.run(
            ['which', command],
            capture_output=True
        ).returncode == 0

    @staticmethod
    def check_ros2_sourced() -> bool:
        """Check if ROS2 environment is sourced."""
        return 'ROS_DISTRO' in os.environ

    @staticmethod
    def check_gazebo_running() -> bool:
        """Check if Gazebo is running."""
        try:
            result = subprocess.run(
                ['gz', 'service', '-l'],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            return result.returncode == 0 and len(result.stdout) > 0
        except:
            return False

    @staticmethod
    def check_file_exists(path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(path)

    @staticmethod
    def validate_environment(checks: List[Tuple[str, callable]]) -> List[str]:
        """Run multiple validation checks, return list of failures."""
        failures = []
        for check_name, check_func in checks:
            if not check_func():
                failures.append(check_name)
        return failures
```

#### 1.3: Create Configuration Loader
**File**: `demos/framework/config_loader.py`

```python
"""Configuration loading utilities."""
import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Load and validate demo configurations."""

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    @staticmethod
    def merge_configs(base: Dict, override: Dict) -> Dict:
        """Merge override config into base config."""
        result = base.copy()
        result.update(override)
        return result

    @staticmethod
    def get_demo_config(demo_name: str, variant: str = None) -> Dict:
        """Load configuration for a specific demo."""
        demo_dir = Path(__file__).parent.parent / demo_name
        config_file = demo_dir / 'config.yaml'

        config = ConfigLoader.load_config(str(config_file))

        if variant and 'variations' in config and variant in config['variations']:
            config = ConfigLoader.merge_configs(
                config,
                config['variations'][variant]
            )

        return config
```

**Deliverables**:
- `demos/framework/` directory with 3 Python modules
- Framework ready for demo implementations

---

## Phase 2: Demo 1 - Hello World (Days 4-7)

### Objective
Complete Hello World demo implementation with all 5 steps functional.

### Tasks

#### 2.1: Implement Hello World Demo
**File**: `demos/01_hello_world/hello_world_demo.py`

```python
"""Hello World demo implementation."""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from demos.framework.demo_executor import DemoExecutor, DemoStep
from demos.framework.config_loader import ConfigLoader
from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose
import rclpy
from rclpy.node import Node


class HelloWorldDemo(DemoExecutor):
    """5-minute beginner-friendly demo."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path(__file__).parent / 'config.yaml')

        config = ConfigLoader.load_config(config_path)
        super().__init__("Hello World - First Robot", config)

        self.node = None
        self.adapter = None
        self.robot_name = "demo_robot"

        # Register demo steps
        self.register_step(DemoStep(
            name="verify_gazebo",
            active_name="Verifying Gazebo is running",
            execute=self.step_1_verify_gazebo,
            timeout=5.0
        ))

        self.register_step(DemoStep(
            name="spawn_robot",
            active_name="Spawning TurtleBot3 robot",
            execute=self.step_2_spawn_robot,
            timeout=10.0
        ))

        self.register_step(DemoStep(
            name="move_forward",
            active_name="Moving robot forward",
            execute=self.step_3_move_forward,
            timeout=15.0
        ))

        self.register_step(DemoStep(
            name="rotate_and_return",
            active_name="Rotating and returning to start",
            execute=self.step_4_rotate_return,
            timeout=15.0
        ))

        self.register_step(DemoStep(
            name="cleanup",
            active_name="Cleaning up",
            execute=self.step_5_cleanup,
            timeout=5.0,
            critical=False  # Cleanup failures shouldn't fail demo
        ))

    async def setup(self):
        """Initialize ROS2 node and adapter."""
        rclpy.init()
        self.node = Node('hello_world_demo_node')

        world_name = self.config.get('world', {}).get('name', 'default')
        timeout = self.config.get('demo', {}).get('timeout', 20.0)

        self.adapter = ModernGazeboAdapter(
            self.node,
            default_world=world_name,
            timeout=timeout
        )

    async def teardown(self):
        """Cleanup ROS2 resources."""
        if self.adapter:
            self.adapter.shutdown()
        if self.node:
            self.node.destroy_node()
        rclpy.shutdown()

    async def step_1_verify_gazebo(self) -> bool:
        """Verify Gazebo is running."""
        # Use adapter to check if Gazebo is responsive
        try:
            # Attempt to get world properties (will fail if Gazebo not running)
            world_info = await self.adapter.get_world_properties()
            return True
        except Exception:
            return False

    async def step_2_spawn_robot(self) -> bool:
        """Spawn TurtleBot3 robot at origin."""
        robot_config = self.config.get('robot', {})
        spawn_pos = robot_config.get('spawn_position', {})
        spawn_ori = robot_config.get('spawn_orientation', {})

        # Simple box robot SDF (TurtleBot3 requires full package, use simple model for demo)
        sdf_content = """
        <?xml version="1.0"?>
        <sdf version="1.8">
          <model name="demo_robot">
            <static>false</static>
            <link name="base_link">
              <pose>0 0 0.1 0 0 0</pose>
              <inertial>
                <mass>1.0</mass>
                <inertia>
                  <ixx>0.1</ixx>
                  <iyy>0.1</iyy>
                  <izz>0.1</izz>
                </inertia>
              </inertial>
              <visual name="visual">
                <geometry>
                  <box><size>0.3 0.3 0.2</size></box>
                </geometry>
                <material>
                  <ambient>0.0 0.5 1.0 1</ambient>
                  <diffuse>0.0 0.5 1.0 1</diffuse>
                </material>
              </visual>
              <collision name="collision">
                <geometry>
                  <box><size>0.3 0.3 0.2</size></box>
                </geometry>
              </collision>
            </link>
          </model>
        </sdf>
        """

        pose = EntityPose(
            position=(spawn_pos.get('x', 0.0), spawn_pos.get('y', 0.0), spawn_pos.get('z', 0.0)),
            orientation=(spawn_ori.get('roll', 0.0), spawn_ori.get('pitch', 0.0),
                        spawn_ori.get('yaw', 0.0), 1.0)
        )

        return await self.adapter.spawn_entity(
            name=self.robot_name,
            sdf=sdf_content,
            pose=pose
        )

    async def step_3_move_forward(self) -> bool:
        """Move robot forward 2 meters."""
        movements = self.config.get('movements', {})
        forward_dist = movements.get('part3_forward_distance', 2.0)

        # Get current pose
        current_state = await self.adapter.get_entity_state(self.robot_name)

        # Calculate new position (move forward in x direction)
        new_pose = EntityPose(
            position=(
                current_state.pose.position[0] + forward_dist,
                current_state.pose.position[1],
                current_state.pose.position[2]
            ),
            orientation=current_state.pose.orientation
        )

        return await self.adapter.set_entity_state(self.robot_name, pose=new_pose)

    async def step_4_rotate_return(self) -> bool:
        """Rotate 180 degrees and return to origin."""
        # Rotate 180 degrees
        import math
        current_state = await self.adapter.get_entity_state(self.robot_name)

        # Rotate 180 degrees (add pi to yaw)
        new_pose = EntityPose(
            position=current_state.pose.position,
            orientation=(0.0, 0.0, math.pi, 1.0)  # 180 degree rotation
        )

        success = await self.adapter.set_entity_state(self.robot_name, pose=new_pose)
        if not success:
            return False

        # Move back to origin
        await asyncio.sleep(1.0)  # Brief pause

        origin_pose = EntityPose(
            position=(0.0, 0.0, 0.0),
            orientation=(0.0, 0.0, 0.0, 1.0)
        )

        return await self.adapter.set_entity_state(self.robot_name, pose=origin_pose)

    async def step_5_cleanup(self) -> bool:
        """Remove spawned robot."""
        return await self.adapter.delete_entity(self.robot_name)


async def main():
    """Run Hello World demo."""
    demo = HelloWorldDemo()

    try:
        await demo.setup()
        success = await demo.execute()
        await demo.teardown()

        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

#### 2.2: Create Tests
**File**: `demos/01_hello_world/test_hello_world_demo.py`

```python
"""Tests for Hello World demo."""
import pytest
import asyncio
from pathlib import Path
from hello_world_demo import HelloWorldDemo


@pytest.mark.asyncio
async def test_demo_framework():
    """Test basic demo framework."""
    demo = HelloWorldDemo()
    assert demo.name == "Hello World - First Robot"
    assert len(demo.steps) == 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_demo_execution():
    """Integration test: full demo execution."""
    demo = HelloWorldDemo()

    await demo.setup()
    try:
        success = await demo.execute()
        assert success, "Demo should complete successfully"

        # Verify all steps completed
        assert len(demo.results) == 5
        assert all(result['success'] for result in demo.results.values())
    finally:
        await demo.teardown()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### 2.3: Update Documentation
**File**: `demos/01_hello_world/README.md`

Update with:
- Installation/setup instructions
- How to run the demo
- Expected output
- Troubleshooting common issues

**Deliverables**:
- Working Hello World demo
- Integration tests
- Updated documentation

---

## Phase 3: Demo 2 Setup (Days 8-10)

### Objective
Create all setup files and environment for Obstacle Course demo.

### Tasks

#### 3.1: Create setup.sh
**File**: `demos/02_obstacle_course/setup.sh`

```bash
#!/bin/bash
# Obstacle Course demo setup script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "Demo: Obstacle Course Challenge - Setup"
echo "========================================="

# Check ROS2
if [ -z "$ROS_DISTRO" ]; then
    source /opt/ros/humble/setup.bash
fi

# Check Gazebo
if ! command -v gz &> /dev/null; then
    echo -e "${RED}✗${NC} Gazebo not found"
    exit 1
fi
echo -e "${GREEN}✓${NC} Gazebo found"

# Check nav2 packages
if ! ros2 pkg list | grep -q "nav2"; then
    echo -e "${YELLOW}Installing nav2 packages...${NC}"
    sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup
fi
echo -e "${GREEN}✓${NC} Nav2 packages found"

# Create directories
mkdir -p logs worlds

# Generate quick test script
cat > quick_test.sh << 'EOF'
#!/bin/bash
source /opt/ros/humble/setup.bash
gz sim empty.sdf &
sleep 5
pkill -9 gz
echo "✓ Setup complete"
EOF
chmod +x quick_test.sh

echo -e "${GREEN}Setup complete!${NC}"
```

#### 3.2: Create config.yaml
**File**: `demos/02_obstacle_course/config.yaml`

```yaml
demo:
  name: "Obstacle Course Challenge"
  version: "1.0"
  duration_minutes: 10
  difficulty: "technical"

world:
  name: "obstacle_course"
  file: "worlds/obstacle_course.sdf"
  physics:
    gravity: 9.81
    step_size: 0.001

robot:
  model: "turtlebot3"
  variant: "waffle"
  spawn_position:
    x: 0.0
    y: 0.0
    z: 0.1

obstacles:
  count: 15
  types: ["box", "cylinder"]
  min_height: 0.2
  max_height: 1.0
  spacing: 1.5

navigation:
  use_nav2: true
  planner: "DWB"
  controller: "DWB"
  recovery_behaviors: true

sensors:
  lidar:
    enabled: true
    range: 12.0
    samples: 360
  camera:
    enabled: false

timing:
  step_timeout: 30.0
  navigation_timeout: 120.0

metrics:
  collect_path_data: true
  collect_sensor_data: true
  save_to_file: true
```

#### 3.3: Create/Validate World File
**File**: `demos/02_obstacle_course/worlds/obstacle_course.sdf`

Basic obstacle course world with 15 obstacles arranged in navigable pattern.

**Deliverables**:
- Complete setup scripts
- Configuration file
- World file validated and tested

---

## Phase 4: Demo 2 Implementation (Days 11-16)

### Objective
Implement full Obstacle Course demo with all 10 steps.

### Tasks

#### 4.1: Implement Obstacle Course Demo
**File**: `demos/02_obstacle_course/obstacle_course_demo.py`

Structure similar to Hello World but with 10 steps:
1. Launch world with obstacles
2. Spawn robot with sensors
3. Initialize sensor visualization
4. Demonstrate obstacle detection
5. Show path planning
6. Navigate to first waypoint
7. Handle dynamic obstacle
8. Demonstrate replanning
9. Complete course
10. Show metrics and cleanup

Key implementation points:
- Use Modern adapter for all Gazebo interactions
- Integrate nav2 for autonomous navigation
- Collect and display metrics
- Handle dynamic obstacle injection

#### 4.2: Create Tests
**File**: `demos/02_obstacle_course/test_obstacle_course_demo.py`

```python
"""Tests for Obstacle Course demo."""
import pytest
import asyncio
from obstacle_course_demo import ObstacleCourseDemo


@pytest.mark.asyncio
async def test_demo_initialization():
    """Test demo initializes correctly."""
    demo = ObstacleCourseDemo()
    assert len(demo.steps) == 10


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_demo():
    """Full integration test."""
    demo = ObstacleCourseDemo()

    await demo.setup()
    try:
        success = await demo.execute()
        assert success
    finally:
        await demo.teardown()
```

#### 4.3: Documentation
**File**: `demos/02_obstacle_course/README.md`

Technical documentation including:
- Setup instructions
- Nav2 configuration details
- World file structure
- Customization options
- Performance tuning

**Deliverables**:
- Working Obstacle Course demo
- Complete test suite
- Technical documentation

---

## Phase 5: Integration & Deployment (Days 17-20)

### Objective
Integrate both demos with unified launcher, polish UX, complete documentation.

### Tasks

#### 5.1: Create Unified Launcher
**File**: `demos/run_demo.py`

```python
"""Unified demo launcher."""
import argparse
import asyncio
import sys
from pathlib import Path

# Add demos to path
sys.path.insert(0, str(Path(__file__).parent))

from demos.hello_world.hello_world_demo import HelloWorldDemo
from demos.obstacle_course.obstacle_course_demo import ObstacleCourseDemo


async def run_demo(demo_name: str, config_override: str = None) -> int:
    """Run specified demo."""
    if demo_name == 'hello_world':
        demo = HelloWorldDemo(config_override)
    elif demo_name == 'obstacle_course':
        demo = ObstacleCourseDemo(config_override)
    else:
        print(f"Unknown demo: {demo_name}")
        return 1

    try:
        await demo.setup()
        success = await demo.execute()
        await demo.teardown()
        return 0 if success else 1
    except Exception as e:
        print(f"Demo failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Gazebo MCP Demo Launcher')
    parser.add_argument('demo', choices=['hello_world', 'obstacle_course', 'all'],
                       help='Demo to run')
    parser.add_argument('--config', help='Override config file')
    parser.add_argument('--list', action='store_true', help='List available demos')

    args = parser.parse_args()

    if args.list:
        print("Available demos:")
        print("  hello_world      - 5 min beginner demo")
        print("  obstacle_course  - 10 min technical demo")
        return 0

    if args.demo == 'all':
        print("Running all demos sequentially...\n")
        exit_code = asyncio.run(run_demo('hello_world', args.config))
        if exit_code == 0:
            exit_code = asyncio.run(run_demo('obstacle_course', args.config))
        return exit_code
    else:
        return asyncio.run(run_demo(args.demo, args.config))


if __name__ == '__main__':
    sys.exit(main())
```

#### 5.2: Master Documentation
**File**: `demos/README.md`

Comprehensive guide including:
- Overview of demo system
- Quick start instructions
- Demo catalog with audience mapping
- Installation requirements
- Troubleshooting guide
- Development guide for new demos

#### 5.3: CI Pipeline
**File**: `.github/workflows/demo-tests.yml`

```yaml
name: Demo Tests

on: [push, pull_request]

jobs:
  test-demos:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3

      - name: Install ROS2
        run: |
          sudo apt update
          sudo apt install -y ros-humble-ros-base

      - name: Install Gazebo
        run: |
          sudo apt install -y ignition-gazebo6

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run framework tests
        run: |
          pytest demos/framework/ -v

      - name: Run demo tests
        run: |
          pytest demos/ -v -m "not slow"
```

**Deliverables**:
- Unified launcher
- Master documentation
- CI pipeline
- Production-ready system

---

## Deliverables Summary

### Code Files
- `demos/framework/` - 3 Python modules (executor, validator, config)
- `demos/01_hello_world/hello_world_demo.py` - Demo 1 implementation
- `demos/01_hello_world/test_hello_world_demo.py` - Demo 1 tests
- `demos/02_obstacle_course/setup.sh` - Demo 2 setup
- `demos/02_obstacle_course/config.yaml` - Demo 2 config
- `demos/02_obstacle_course/obstacle_course_demo.py` - Demo 2 implementation
- `demos/02_obstacle_course/test_obstacle_course_demo.py` - Demo 2 tests
- `demos/02_obstacle_course/worlds/obstacle_course.sdf` - World file
- `demos/run_demo.py` - Unified launcher

### Documentation
- `demos/01_hello_world/README.md` - Demo 1 user guide
- `demos/02_obstacle_course/README.md` - Demo 2 technical guide
- `demos/README.md` - Master documentation
- `.github/workflows/demo-tests.yml` - CI configuration

### Tests
- Framework unit tests
- Demo integration tests
- CI pipeline tests

---

## Timeline

| Phase | Days | Parallel Work | Deliverables |
|-------|------|---------------|--------------|
| Phase 1 | 1-3 | Framework modules | 3 Python files |
| Phase 2 | 4-7 | Demo 1 implementation, tests, docs | 3 files |
| Phase 3 | 8-10 | Setup scripts, config, world | 3 files |
| Phase 4 | 11-16 | Demo 2 implementation, tests, docs | 3 files |
| Phase 5 | 17-20 | Integration, CI, master docs | 3 files |
| **Total** | **20 days** | | **18 files** |

**Parallel Opportunities**:
- Days 4-7: Demo 1 tests can be written parallel to implementation
- Days 8-10: Setup, config, and world creation can run parallel
- Days 11-16: Demo 2 steps 1-5 parallel with steps 6-10
- Days 17-20: Documentation parallel with CI setup

---

## Testing Strategy

### Unit Tests
- Framework classes (executor, validator, config loader)
- Individual demo steps
- Utility functions

### Integration Tests
- Full demo execution
- Modern adapter integration
- Error handling scenarios

### CI Tests
- All unit tests
- Fast integration tests (non-slow)
- Code quality checks

**Test Coverage Target**: >80%

---

## Key Integration Points

### Modern Gazebo Adapter
All demo steps use the Modern adapter methods:
- `spawn_entity()` - Robot and obstacle spawning
- `delete_entity()` - Cleanup
- `get_entity_state()` - State queries
- `set_entity_state()` - Pose manipulation
- `pause_simulation()` / `unpause_simulation()` - Demo control
- `get_world_properties()` - Environment validation

### Configuration Management
- YAML-based configuration
- Override support for variations
- Environment variable integration

### Error Handling
- Graceful degradation
- Clear error messages
- Step-level failure isolation
- Critical vs non-critical steps

---

## Success Criteria

### Technical
- [x] Modern adapter integrated (11/11 tests passing)
- [ ] Demo 1 executes all 5 steps reliably
- [ ] Demo 2 executes all 10 steps reliably
- [ ] All tests passing (unit + integration)
- [ ] CI pipeline green
- [ ] Code coverage >80%

### Performance
- [ ] Demo 1 completes in <6 minutes
- [ ] Demo 2 completes in <12 minutes
- [ ] No memory leaks
- [ ] Graceful error handling

### Documentation
- [ ] Installation instructions complete
- [ ] Usage examples for both demos
- [ ] Troubleshooting guide
- [ ] API documentation

---

## Next Steps

1. **Start Phase 1**: Create demo framework (3 days)
2. **Checkpoint**: Framework tested and ready
3. **Start Phase 2**: Implement Demo 1 (4 days)
4. **Checkpoint**: Demo 1 functional
5. **Continue through phases**

**Begin**: Create feature branch and start Phase 1, Task 1.1

```bash
cd /home/koen/workspaces/hackathon-git/ros2_gazebo_mcp
git checkout -b feature/demo-implementation
mkdir -p demos/framework
```

---

**Plan Status**: Ready for execution
**Last Updated**: 2025-11-25
**Est. Completion**: 2-3 weeks from start
