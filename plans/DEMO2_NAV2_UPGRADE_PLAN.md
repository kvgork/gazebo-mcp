# Demo 2: Obstacle Course - Nav2 Upgrade Implementation Plan

**Created**: 2025-01-27
**Status**: Ready for Implementation
**Goal**: Transform Demo 2 from script-based teleportation to natural language MCP-driven autonomous navigation

---

## Executive Summary

Upgrade Demo 2 (Obstacle Course) with two major improvements:

1. **Natural Language Control**: Replace Python script execution with MCP tool-based conversational interface (like Demo 1)
2. **Real Autonomous Navigation**: Replace teleportation with actual TurtleBot3 + Nav2 autonomous navigation

**Timeline**: 3-5 days
**Complexity**: Medium-High (Nav2 integration + MCP tool development)

---

## Current State Analysis

### What Works ✅
- Demo framework (DemoExecutor, DemoValidator, ConfigLoader)
- Modern Gazebo adapter (11/11 tests passing)
- MCP server with model management tools
- Obstacle course world generation
- Script-based demo execution (10 steps)
- TurtleBot3 configuration exists (`config/ros2_config.yaml`)

### What Needs Updating ❌
1. **Demo 2 uses Python scripts** - Need to expose as MCP tools
2. **Robot is teleported** (line 369-381 in `obstacle_course_demo.py`) - Need Nav2 integration
3. **No navigation MCP tools** - Need to create tools for Nav2 goal setting
4. **Simple robot model** - Need real TurtleBot3 with sensors

---

## Phase 1: Nav2 Integration & MCP Tools (Days 1-2)

### Objective
Create MCP tools for Nav2 navigation and TurtleBot3 spawning.

### Tasks

#### 1.1: Create Nav2 Tools Module
**File**: `src/gazebo_mcp/tools/navigation_tools.py`

**Tools to implement**:
```python
@mcp_tool
def spawn_turtlebot3(
    name: str = "turtlebot3",
    variant: str = "burger",  # burger, waffle, waffle_pi
    position: tuple = (0.0, 0.0, 0.01),
    orientation: tuple = (0.0, 0.0, 0.0),
    world: str = "default"
) -> OperationResult:
    """
    Spawn TurtleBot3 robot with proper sensors and configuration.

    Uses TurtleBot3 models from config/ros2_config.yaml.
    Automatically configures:
    - LiDAR sensor
    - IMU
    - Odometry
    - Differential drive controller

    Args:
        name: Robot instance name
        variant: TurtleBot3 variant (burger/waffle/waffle_pi)
        position: (x, y, z) spawn position
        orientation: (roll, pitch, yaw) in radians
        world: Gazebo world name

    Returns:
        OperationResult with spawn status

    Example:
        >>> spawn_turtlebot3("my_robot", "burger", (0, 0, 0.01))
    """
    pass


@mcp_tool
def send_nav2_goal(
    robot_name: str,
    goal_position: tuple,  # (x, y)
    goal_orientation: float = 0.0,  # yaw in radians
    timeout: float = 120.0,
    wait_for_result: bool = True
) -> OperationResult:
    """
    Send navigation goal to Nav2 action server.

    Uses ROS2 action client to send NavigateToPose goal.
    Monitors navigation progress and reports success/failure.

    Args:
        robot_name: Name of robot to navigate
        goal_position: Target (x, y) coordinates
        goal_orientation: Target yaw orientation in radians
        timeout: Maximum time to wait for navigation (seconds)
        wait_for_result: Block until navigation completes

    Returns:
        OperationResult with navigation status and path metrics

    Example:
        >>> send_nav2_goal("turtlebot3", (5.0, 3.0), 1.57)
    """
    pass


@mcp_tool
def get_navigation_status(
    robot_name: str
) -> OperationResult:
    """
    Get current Nav2 navigation status.

    Returns:
        - Current robot pose
        - Goal pose (if navigating)
        - Remaining distance
        - Navigation state (idle/navigating/succeeded/failed)
        - Path length
        - Time elapsed

    Example:
        >>> get_navigation_status("turtlebot3")
    """
    pass


@mcp_tool
def cancel_navigation(
    robot_name: str
) -> OperationResult:
    """
    Cancel ongoing navigation goal.

    Sends cancel request to Nav2 action server and stops robot.

    Example:
        >>> cancel_navigation("turtlebot3")
    """
    pass


@mcp_tool
def set_initial_pose(
    robot_name: str,
    position: tuple,  # (x, y)
    orientation: float = 0.0  # yaw in radians
) -> OperationResult:
    """
    Set initial pose for AMCL localization.

    Publishes to /initialpose topic to initialize AMCL.
    Required before navigation if using AMCL.

    Example:
        >>> set_initial_pose("turtlebot3", (0, 0), 0)
    """
    pass
```

**Implementation approach**:
- Use `rclpy.action` for Nav2 action client
- Create `NavigateToPose` goal messages
- Monitor action feedback for progress
- Return structured OperationResult with metrics

#### 1.2: Create Nav2 Adapter
**File**: `src/gazebo_mcp/bridge/adapters/nav2_adapter.py`

```python
class Nav2Adapter:
    """Adapter for Nav2 navigation stack integration."""

    def __init__(self, node: Node):
        self.node = node
        self.action_clients = {}  # robot_name -> action_client
        self.goal_handles = {}    # robot_name -> goal_handle
        self.navigation_state = {}  # robot_name -> state

    def create_navigation_client(self, robot_name: str):
        """Create Nav2 action client for robot."""
        pass

    async def send_goal(self, robot_name: str, goal: NavigateToPose.Goal):
        """Send navigation goal via action server."""
        pass

    async def wait_for_result(self, robot_name: str, timeout: float):
        """Wait for navigation to complete."""
        pass

    def get_feedback(self, robot_name: str) -> dict:
        """Get current navigation feedback."""
        pass
```

#### 1.3: Create MCP Adapter for Nav Tools
**File**: `mcp/server/adapters/navigation_tools_adapter.py`

```python
"""
Nav2 Navigation Tools MCP Adapter.

Exposes Nav2 navigation tools as MCP tools:
- spawn_turtlebot3: Spawn TurtleBot3 with sensors
- send_nav2_goal: Send navigation goal
- get_navigation_status: Check navigation progress
- cancel_navigation: Stop navigation
- set_initial_pose: Initialize AMCL localization
"""

def get_tools() -> List[MCPTool]:
    """Get MCP tools for Nav2 navigation."""
    return [
        MCPTool(
            name="spawn_turtlebot3",
            description="Spawn TurtleBot3 robot with proper sensors and configuration",
            parameters={
                "properties": {
                    "name": {"type": "string", "description": "Robot instance name"},
                    "variant": {
                        "type": "string",
                        "enum": ["burger", "waffle", "waffle_pi"],
                        "description": "TurtleBot3 variant"
                    },
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Spawn position [x, y, z]"
                    }
                },
                "required": ["name"]
            },
            handler=spawn_turtlebot3
        ),
        # ... other tools
    ]
```

#### 1.4: Update MCP Server Registration
**File**: `mcp/server/server.py`

Add navigation_tools_adapter to the registered adapters:

```python
from mcp.server.adapters import (
    model_management_adapter,
    sensor_tools_adapter,
    world_tools_adapter,
    simulation_tools_adapter,
    navigation_tools_adapter,  # NEW
)

def _register_tools(self):
    """Register all tools from adapters."""
    adapters = [
        model_management_adapter,
        sensor_tools_adapter,
        world_tools_adapter,
        simulation_tools_adapter,
        navigation_tools_adapter,  # NEW
    ]
```

**Deliverables**:
- `navigation_tools.py` with 5 MCP tools
- `nav2_adapter.py` for Nav2 integration
- `navigation_tools_adapter.py` for MCP exposure
- Updated MCP server registration
- Unit tests for each tool

**Skills/Agents to use**:
- `/skills:ros:py-node-template` - Generate ROS node boilerplate
- `/skills:ros:ros-msg-gen` - Generate ROS message definitions if needed
- `/skills:verification:verify-ros-node` - Validate implementation

---

## Phase 2: TurtleBot3 Model & Nav2 Setup (Days 2-3)

### Objective
Set up TurtleBot3 models and Nav2 launch files for obstacle course demo.

### Tasks

#### 2.1: Install TurtleBot3 Packages
**Script**: `demos/02_obstacle_course/install_turtlebot3.sh`

```bash
#!/bin/bash
# Install TurtleBot3 packages and dependencies

set -e

echo "Installing TurtleBot3 packages..."

# Install TurtleBot3 packages
sudo apt update
sudo apt install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-gazebo \
    ros-humble-turtlebot3-simulations \
    ros-humble-turtlebot3-msgs \
    ros-humble-turtlebot3-description

# Install Nav2
sudo apt install -y \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-slam-toolbox

# Set TurtleBot3 model environment
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc

echo "✓ TurtleBot3 installation complete!"
```

#### 2.2: Create Nav2 Configuration
**File**: `demos/02_obstacle_course/nav2_params.yaml`

```yaml
# Nav2 parameters for obstacle course demo
bt_navigator:
  ros__parameters:
    use_sim_time: True
    global_frame: odom
    robot_base_frame: base_footprint
    transform_timeout: 0.1
    default_nav_to_pose_bt_xml: ""
    default_nav_through_poses_bt_xml: ""
    plugin_lib_names:
      - nav2_compute_path_to_pose_action_bt_node
      - nav2_follow_path_action_bt_node
      - nav2_back_up_action_bt_node
      - nav2_spin_action_bt_node
      - nav2_wait_action_bt_node

controller_server:
  ros__parameters:
    use_sim_time: True
    controller_frequency: 20.0
    min_x_velocity_threshold: 0.001
    min_y_velocity_threshold: 0.5
    min_theta_velocity_threshold: 0.001
    progress_checker_plugin: "progress_checker"
    goal_checker_plugins: ["goal_checker"]
    controller_plugins: ["FollowPath"]

    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"
      required_movement_radius: 0.5
      movement_time_allowance: 10.0

    goal_checker:
      plugin: "nav2_controller::SimpleGoalChecker"
      xy_goal_tolerance: 0.25
      yaw_goal_tolerance: 0.25
      stateful: True

    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"
      min_vel_x: 0.0
      min_vel_y: 0.0
      max_vel_x: 0.22
      max_vel_y: 0.0
      max_vel_theta: 2.75
      min_speed_xy: 0.0
      max_speed_xy: 0.22
      min_speed_theta: 0.0
      acc_lim_x: 2.5
      acc_lim_y: 0.0
      acc_lim_theta: 3.2
      decel_lim_x: -2.5
      decel_lim_y: 0.0
      decel_lim_theta: -3.2

planner_server:
  ros__parameters:
    use_sim_time: True
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_navfn_planner/NavfnPlanner"
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

#### 2.3: Create Nav2 Launch File
**File**: `demos/02_obstacle_course/launch_nav2.sh`

```bash
#!/bin/bash
# Launch Nav2 for obstacle course demo

source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger

# Start Nav2
ros2 launch nav2_bringup bringup_launch.py \
    use_sim_time:=True \
    params_file:=$(pwd)/nav2_params.yaml \
    map:=$(pwd)/maps/obstacle_course.yaml
```

#### 2.4: Update Obstacle Course World
**File**: `demos/02_obstacle_course/worlds/obstacle_course_nav2.sdf`

Enhance the world file with:
- Ground plane with proper materials
- Static obstacles visible to LiDAR
- Goal markers
- Lighting optimized for camera sensors

**Skills/Agents to use**:
- `/skills:robot:urdf-builder` - Validate TurtleBot3 model
- `/agents:ros:ros-launch-mgr` - Create launch files
- `/skills:ros:yaml-config` - Create/validate Nav2 params

---

## Phase 3: Update Demo 2 for Natural Language Control (Days 3-4)

### Objective
Refactor Demo 2 to use MCP tools instead of direct Python API calls.

### Tasks

#### 3.1: Create Conversational Demo Script
**File**: `demos/02_obstacle_course/CONVERSATIONAL_DEMO.md`

```markdown
# Obstacle Course Demo - Natural Language Guide

## Prerequisites

1. Start MCP server:
   ```bash
   cd <path-to-ros2_gazebo_mcp>
   python3 -m mcp.server.server
   ```

2. Start Gazebo with obstacle course:
   ```bash
   cd demos/02_obstacle_course
   gz sim -r worlds/obstacle_course_nav2.sdf
   ```

3. Start ros_gz_bridge:
   ```bash
   ./setup.sh
   ```

4. Start Nav2:
   ```bash
   ./launch_nav2.sh
   ```

## Running the Demo Conversationally

Once all services are running, **just talk to Claude**:

### Step 1: Spawn TurtleBot3

**You say:**
> "Spawn a TurtleBot3 burger robot at the origin"

**Claude will:**
- Call `spawn_turtlebot3` MCP tool
- Spawn robot with LiDAR and sensors
- Initialize localization
- Respond: "✅ TurtleBot3 burger spawned at (0, 0, 0.01)"

---

### Step 2: Set Initial Pose

**You say:**
> "Set the robot's initial pose at (0, 0) facing forward"

**Claude will:**
- Call `set_initial_pose` MCP tool
- Initialize AMCL localization
- Respond: "✅ Initial pose set for localization"

---

### Step 3: Navigate to First Waypoint

**You say:**
> "Navigate the robot to position (2, 0)"

**Claude will:**
- Call `send_nav2_goal` MCP tool
- Send goal to Nav2
- Monitor navigation progress
- Report when arrived
- Respond: "✅ Robot reached (2, 0) - 2.1m in 8.4s"

---

### Step 4: Navigate to Second Waypoint

**You say:**
> "Now go to (4, 0)"

**Claude will:**
- Send next navigation goal
- Continue monitoring
- Respond: "✅ Robot reached (4, 0) - 2.0m in 7.9s"

---

### Step 5: Navigate Around Obstacle

**You say:**
> "Navigate to (4, 2) - watch out for the wall"

**Claude will:**
- Send goal
- Nav2 will plan path around obstacle
- Respond: "✅ Robot reached (4, 2) - avoided obstacle - 2.3m in 9.2s"

---

### Step 6: Reach Final Target

**You say:**
> "Go to the final target at (6, 2)"

**Claude will:**
- Send final goal
- Complete navigation
- Show summary statistics
- Respond: "🎉 Demo complete! Total distance: 8.4m, Total time: 33.6s"

---

### Bonus: Check Status Anytime

**You say:**
> "Where is the robot now?"

**Claude will:**
- Call `get_navigation_status` MCP tool
- Return current pose and navigation state

**You say:**
> "Cancel navigation"

**Claude will:**
- Call `cancel_navigation` MCP tool
- Stop the robot immediately

## What Changed from Script Version?

### Before (Script):
```python
await self.adapter.set_entity_state(
    name='simple_robot',
    pose=new_pose  # Teleport!
)
```

### After (MCP + Natural Language):
**You:** "Navigate robot to (2, 0)"
**Claude:** Calls `send_nav2_goal("turtlebot3", (2.0, 0.0))`
**Result:** Robot actually drives there using Nav2!

## Architecture

```
You (Natural Language)
    ↓
Claude (MCP Tool Selection)
    ↓
MCP Server (navigation_tools.py)
    ↓
Nav2 Action Server
    ↓
TurtleBot3 Controller
    ↓
Robot moves autonomously!
```
```

#### 3.2: Update Demo 2 Configuration
**File**: `demos/02_obstacle_course/config.yaml`

```yaml
demo:
  name: "Obstacle Course Challenge - Nav2"
  version: "2.0"
  duration_minutes: 15
  difficulty: "intermediate"
  type: "conversational"  # NEW: Changed from "scripted"

robot:
  type: "turtlebot3"  # NEW: Changed from simple_robot
  variant: "burger"
  spawn_position: [0.0, 0.0, 0.01]
  spawn_orientation: [0.0, 0.0, 0.0]

  # Navigation waypoints
  waypoints:
    - name: "waypoint_1"
      position: [2.0, 0.0]
      tolerance: 0.25
    - name: "waypoint_2"
      position: [4.0, 0.0]
      tolerance: 0.25
    - name: "waypoint_3"
      position: [4.0, 2.0]
      tolerance: 0.25
    - name: "final_target"
      position: [6.0, 2.0]
      tolerance: 0.3

navigation:
  use_nav2: true  # NEW
  nav2_params: "nav2_params.yaml"
  timeout_per_goal: 120.0
  planner: "NavFn"
  controller: "DWB"

obstacles:
  # Keep existing obstacle config
  models:
    wall_1:
      pose:
        position: [3.0, -1.0, 0.5]
      geometry:
        type: "box"
        size: [0.2, 4.0, 1.0]
      color: [0.8, 0.2, 0.2, 1.0]
      static: true
    # ... other obstacles
```

#### 3.3: Create Optional Scripted Wrapper
**File**: `demos/02_obstacle_course/run_scripted_demo.py`

For users who still want automated execution (e.g., in CI), create wrapper that calls MCP tools programmatically:

```python
#!/usr/bin/env python3
"""
Scripted wrapper for obstacle course demo.
Calls MCP tools programmatically for automated testing.
"""

import asyncio
from mcp.client import MCPClient

async def run_demo():
    """Run demo by calling MCP tools."""
    client = MCPClient()
    await client.connect()

    print("Step 1: Spawning TurtleBot3...")
    result = await client.call_tool(
        "spawn_turtlebot3",
        name="turtlebot3",
        variant="burger",
        position=[0.0, 0.0, 0.01]
    )
    print(f"✓ {result.message}")

    print("Step 2: Setting initial pose...")
    result = await client.call_tool(
        "set_initial_pose",
        robot_name="turtlebot3",
        position=[0.0, 0.0],
        orientation=0.0
    )
    print(f"✓ {result.message}")

    waypoints = [
        (2.0, 0.0),
        (4.0, 0.0),
        (4.0, 2.0),
        (6.0, 2.0)
    ]

    for i, (x, y) in enumerate(waypoints, 1):
        print(f"Step {i+2}: Navigating to ({x}, {y})...")
        result = await client.call_tool(
            "send_nav2_goal",
            robot_name="turtlebot3",
            goal_position=[x, y],
            timeout=120.0,
            wait_for_result=True
        )
        print(f"✓ {result.message}")

    print("\n🎉 Demo completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_demo())
```

**Deliverables**:
- CONVERSATIONAL_DEMO.md guide
- Updated config.yaml
- Optional scripted wrapper
- Updated README.md

---

## Phase 4: Testing & Documentation (Days 4-5)

### Objective
Test full workflow and create comprehensive documentation.

### Tasks

#### 4.1: Create Integration Tests
**File**: `tests/integration/test_demo2_nav2.py`

```python
"""Integration tests for Demo 2 with Nav2."""

import pytest
from mcp.client import MCPClient

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_gazebo
@pytest.mark.requires_nav2
async def test_full_obstacle_course_demo():
    """Test complete obstacle course demo with Nav2."""
    client = MCPClient()
    await client.connect()

    # Spawn TurtleBot3
    result = await client.call_tool(
        "spawn_turtlebot3",
        name="test_robot",
        variant="burger",
        position=[0, 0, 0.01]
    )
    assert result.success

    # Set initial pose
    result = await client.call_tool(
        "set_initial_pose",
        robot_name="test_robot",
        position=[0, 0],
        orientation=0
    )
    assert result.success

    # Navigate to waypoint
    result = await client.call_tool(
        "send_nav2_goal",
        robot_name="test_robot",
        goal_position=[2, 0],
        timeout=120.0,
        wait_for_result=True
    )
    assert result.success
    assert result.data["final_distance"] < 0.3  # Within tolerance


@pytest.mark.asyncio
@pytest.mark.unit
async def test_navigation_tools_available():
    """Test that navigation tools are registered."""
    client = MCPClient()
    await client.connect()

    tools = await client.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "spawn_turtlebot3" in tool_names
    assert "send_nav2_goal" in tool_names
    assert "get_navigation_status" in tool_names
    assert "cancel_navigation" in tool_names
```

#### 4.2: Update Main Documentation
**File**: `demos/02_obstacle_course/README.md`

Add sections:
- **Conversational Mode** - How to run with natural language
- **Scripted Mode** - How to run automated version
- **Nav2 Architecture** - Diagram showing components
- **Troubleshooting Nav2** - Common issues
- **Performance Comparison** - Teleport vs autonomous navigation

#### 4.3: Create Video Script (Optional)
**File**: `demos/02_obstacle_course/VIDEO_SCRIPT.md`

Script for recording demo:
1. Show MCP server starting
2. Show Gazebo with obstacle course
3. Talk to Claude in natural language
4. Show robot autonomously navigating
5. Highlight path planning around obstacles
6. Show completion statistics

#### 4.4: Update Master Demo Documentation
**File**: `demos/README.md`

Update with:
- Demo 2 now supports conversational mode
- Nav2 integration details
- Comparison of scripted vs conversational modes

**Skills/Agents to use**:
- `/skills:verification:verify-integration` - Run integration tests
- `/skills:analysis:code-pattern-detect` - Check for anti-patterns
- `/agents:documentation:arch-diagram` - Create architecture diagrams

---

## Implementation Sequence

### Day 1: Nav2 Tools Foundation
1. ✅ Create `navigation_tools.py` skeleton
2. ✅ Implement `spawn_turtlebot3` tool
3. ✅ Create Nav2 adapter basics
4. ✅ Test TurtleBot3 spawning

### Day 2: Navigation Core
1. ✅ Implement `send_nav2_goal` tool
2. ✅ Implement action client integration
3. ✅ Test single goal navigation
4. ✅ Implement `get_navigation_status`

### Day 3: MCP Integration
1. ✅ Create MCP adapter for nav tools
2. ✅ Register in MCP server
3. ✅ Test tools via MCP protocol
4. ✅ Update Demo 2 config

### Day 4: Demo & Documentation
1. ✅ Create CONVERSATIONAL_DEMO.md
2. ✅ Test full conversational workflow
3. ✅ Create scripted wrapper
4. ✅ Update README

### Day 5: Testing & Polish
1. ✅ Write integration tests
2. ✅ Test error scenarios
3. ✅ Performance validation
4. ✅ Final documentation review

---

## Success Criteria

### Technical Requirements
- [ ] TurtleBot3 spawns with proper sensors
- [ ] Nav2 action client connects successfully
- [ ] Robot navigates autonomously (no teleportation)
- [ ] Obstacle avoidance works correctly
- [ ] All 4 waypoints reached via autonomous navigation
- [ ] Navigation metrics collected (distance, time, path length)
- [ ] MCP tools return structured OperationResults

### User Experience
- [ ] Can run demo by talking to Claude in natural language
- [ ] Clear feedback on navigation progress
- [ ] Can check status and cancel navigation
- [ ] Optional scripted mode still works
- [ ] Documentation is clear and complete

### Performance
- [ ] Demo completes in <5 minutes
- [ ] No navigation failures on standard course
- [ ] Path planning completes in <5 seconds
- [ ] Robot reaches goals within tolerance (0.25m)

---

## Architecture Diagrams

### Before (Teleportation):
```
Python Script
    ↓
DemoExecutor
    ↓
ModernGazeboAdapter.set_entity_state()
    ↓
ros_gz_bridge
    ↓
Gazebo (teleport robot)
```

### After (Nav2 + Conversational):
```
Natural Language ("Go to waypoint 2")
    ↓
Claude (understands intent)
    ↓
MCP Server
    ↓
send_nav2_goal() tool
    ↓
Nav2Adapter
    ↓
Nav2 Action Server
    ↓
Path Planner → Controller
    ↓
TurtleBot3 (autonomous driving)
    ↓
Gazebo (physics simulation)
```

---

## Dependencies

### System Packages
```bash
ros-humble-turtlebot3
ros-humble-turtlebot3-gazebo
ros-humble-navigation2
ros-humble-nav2-bringup
ros-humble-slam-toolbox
```

### Python Packages
```bash
rclpy
action-msgs
nav2-msgs
geometry-msgs
```

### Existing Components
- ✅ Modern Gazebo adapter
- ✅ MCP server framework
- ✅ TurtleBot3 config (`config/ros2_config.yaml`)
- ✅ Demo framework (DemoExecutor)

---

## Risk Mitigation

### Risk: Nav2 fails to find path
**Mitigation**:
- Validate obstacle course is navigable
- Test with known-good Nav2 params
- Provide fallback to simple planner

### Risk: TurtleBot3 model not found
**Mitigation**:
- Check `GAZEBO_MODEL_PATH` includes TurtleBot3
- Provide model files in demo directory
- Add validation in setup script

### Risk: Action client timeout
**Mitigation**:
- Increase timeouts for complex navigation
- Add progress monitoring
- Provide cancel option

### Risk: Users confused by two modes (conversational vs scripted)
**Mitigation**:
- Clear documentation of both modes
- Default to conversational mode
- Mark scripted mode as "legacy" or "CI only"

---

## Testing Strategy

### Unit Tests
- Each navigation tool independently
- Mock Nav2 action server
- Test parameter validation
- Test error handling

### Integration Tests
- Full navigation workflow
- Multi-waypoint navigation
- Obstacle avoidance
- Cancel and retry scenarios

### Manual Testing
- Conversational mode with Claude
- Different robot variants
- Different obstacle configurations
- Edge cases (unreachable goals, etc.)

---

## Future Enhancements (Not in this Plan)

1. **SLAM Integration**: Map building with slam_toolbox
2. **Multi-Robot**: Coordinate multiple TurtleBot3s
3. **Dynamic Obstacles**: Moving obstacles during navigation
4. **Cost Maps**: Custom cost map configuration
5. **Recovery Behaviors**: Custom recovery behaviors for failures
6. **Sensor Visualization**: Live LiDAR scan visualization
7. **Path Visualization**: Show planned vs actual path

---

## References

- [TurtleBot3 Simulation](https://emanual.robotis.com/docs/en/platform/turtlebot3/simulation/)
- [TurtleBot3 SLAM](https://emanual.robotis.com/docs/en/platform/turtlebot3/slam_simulation/)
- [TurtleBot3 Navigation](https://emanual.robotis.com/docs/en/platform/turtlebot3/nav_simulation/)
- [Nav2 Documentation](https://navigation.ros.org/)
- [MCP Specification](https://modelcontextprotocol.io/)
- Current: `demos/CONVERSATIONAL_DEMO_GUIDE.md`
- Current: `config/ros2_config.yaml`

---

**Plan Status**: Ready for Implementation
**Estimated Completion**: 3-5 days
**Blocking Issues**: None
**Dependencies**: All satisfied

**Next Step**: Begin Phase 1, Task 1.1 - Create `navigation_tools.py`
