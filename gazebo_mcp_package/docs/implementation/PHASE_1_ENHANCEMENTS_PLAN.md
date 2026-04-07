# Phase 1: Foundation Enhancements - Detailed Implementation Plan

**Status:** 🚀 In Progress
**Duration:** 4 weeks (Weeks 1-4)
**Started:** 2025-12-29
**Priority:** 🔴 HIGH

---

## Overview

Phase 1 implements high-priority, high-impact features that unlock major new use cases:
- **Multi-robot coordination** (Week 1-2)
- **Advanced sensor capabilities** (Week 1-2)
- **Nav2 integration** (Week 3-4)
- **Developer tools** (Week 3-4)

**Total New Tools:** 33 tools across 4 enhancement areas

---

## Week 1-2: Multi-Robot & Advanced Sensors

### Multi-Robot Coordination (6 new tools)

#### Task 1.1: Multi-Robot Spawning
**File:** `src/gazebo_mcp/tools/multi_robot_tools.py` (NEW)
**Estimated:** 2 days

**Tool: `spawn_robot_fleet`**
```python
def spawn_robot_fleet(
    robot_model: str,
    count: int,
    formation: str = "grid",  # grid, line, circle, random
    spacing: float = 2.0,
    namespace_prefix: str = "robot",
    start_position: Optional[Dict[str, float]] = None,
    robot_params: Optional[Dict[str, Any]] = None
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Create `multi_robot_tools.py` module
2. [ ] Implement formation algorithms:
   - [ ] Grid formation (rows x cols)
   - [ ] Line formation (straight line)
   - [ ] Circle formation (radius-based)
   - [ ] Random formation (collision-free placement)
3. [ ] Add collision detection for placement
4. [ ] Implement namespace management
5. [ ] Add progress tracking for batch spawn
6. [ ] Write unit tests (5+ tests)
7. [ ] Create integration test with 10 robots
8. [ ] Add to MCP adapter

**Success Criteria:**
- [ ] Spawn 10 robots in grid formation successfully
- [ ] All robots have unique namespaces
- [ ] No collisions between spawned robots
- [ ] Formation spacing is accurate within 0.1m

---

#### Task 1.2: Fleet Status Monitoring
**Estimated:** 1 day

**Tool: `get_fleet_status`**
```python
def get_fleet_status(
    namespace_pattern: Optional[str] = None,  # "robot*"
    include_sensors: bool = False,
    include_battery: bool = False,
    response_format: str = "summary"
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Implement robot discovery by namespace pattern
2. [ ] Query state for each robot (parallel)
3. [ ] Aggregate fleet statistics
4. [ ] Add battery simulation (optional)
5. [ ] Implement ResultFilter for token efficiency
6. [ ] Write unit tests (3+ tests)
7. [ ] Add to MCP adapter

**Returns:**
```python
{
    "fleet_size": 10,
    "robots": [
        {
            "name": "robot_0",
            "namespace": "/robot_0",
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "velocity": {"linear": 0.0, "angular": 0.0},
            "battery": 95.5,  # Optional
            "status": "idle"
        },
        # ... more robots
    ],
    "summary": {
        "active": 10,
        "idle": 8,
        "moving": 2,
        "errors": 0
    }
}
```

---

#### Task 1.3: Fleet Command
**Estimated:** 1.5 days

**Tool: `send_fleet_command`**
```python
def send_fleet_command(
    command_type: str,  # velocity, goal, formation
    targets: Optional[List[str]] = None,  # None = all
    command_data: Dict[str, Any] = {},
    synchronized: bool = False
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Implement robot selection/filtering
2. [ ] Add command types:
   - [ ] Velocity command (Twist)
   - [ ] Goal command (PoseStamped)
   - [ ] Formation command (relative positions)
3. [ ] Add synchronized execution option
4. [ ] Implement error handling for individual failures
5. [ ] Write unit tests (4+ tests)
6. [ ] Add to MCP adapter

---

#### Task 1.4: Collision Avoidance
**Estimated:** 2 days

**Tool: `enable_multi_robot_collision_avoidance`**
```python
def enable_multi_robot_collision_avoidance(
    robot_namespaces: List[str],
    method: str = "velocity_obstacle",  # velocity_obstacle, social_force
    safety_distance: float = 0.5,
    max_deceleration: float = 1.0
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Implement velocity obstacle algorithm
2. [ ] Add social force model (optional)
3. [ ] Create collision prediction system
4. [ ] Implement velocity adjustment
5. [ ] Add monitoring and metrics
6. [ ] Write unit tests (5+ tests)
7. [ ] Create multi-robot demo
8. [ ] Add to MCP adapter

**Note:** This is a complex feature. Start with basic velocity obstacles.

---

#### Task 1.5: Swarm Behaviors (DEFERRED to Phase 2)
**Reason:** Complex, lower priority than core coordination

---

### Advanced Sensor Capabilities (8 new tools)

#### Task 2.1: Sensor Fusion
**File:** `src/gazebo_mcp/tools/sensor_fusion_tools.py` (NEW)
**Estimated:** 2 days

**Tool: `fuse_sensor_data`**
```python
def fuse_sensor_data(
    fusion_type: str,  # lidar_camera, multi_lidar, imu_gps
    sensor_sources: Dict[str, str],  # {"lidar": "/robot/scan", "camera": "/robot/camera"}
    output_format: str = "pointcloud2",
    color_mapping: Optional[str] = None
) -> OperationResult
```

**Fusion Types:**
1. **lidar_camera:** Colorize point cloud with camera
2. **multi_lidar:** Merge multiple LiDAR scans
3. **imu_gps:** Combine IMU and GPS for better pose

**Implementation Steps:**
1. [ ] Create `sensor_fusion_tools.py` module
2. [ ] Implement LiDAR + Camera fusion:
   - [ ] Get camera calibration
   - [ ] Project 3D points to 2D image
   - [ ] Sample RGB values
   - [ ] Create colored point cloud
3. [ ] Implement multi-LiDAR fusion:
   - [ ] Transform scans to common frame
   - [ ] Merge point clouds
   - [ ] Remove duplicates
4. [ ] Implement IMU + GPS fusion (Kalman filter)
5. [ ] Write unit tests (6+ tests)
6. [ ] Add to MCP adapter

**Success Criteria:**
- [ ] LiDAR + Camera produces colored point cloud
- [ ] Multi-LiDAR creates 360° coverage
- [ ] IMU + GPS improves localization accuracy

---

#### Task 2.2: Sensor Visualization
**Estimated:** 2 days

**Tool: `visualize_sensor_data`**
```python
def visualize_sensor_data(
    sensor_topic: str,
    visualization_type: str,  # pointcloud, camera_frustum, imu_arrow, trajectory
    duration: float = 0.0,  # 0 = permanent
    color: Optional[Dict[str, float]] = None,
    scale: float = 1.0
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Implement RViz marker publishing
2. [ ] Add visualization types:
   - [ ] Point cloud display
   - [ ] Camera frustum (field of view)
   - [ ] IMU orientation arrow
   - [ ] GPS trajectory path
   - [ ] LiDAR range circles
3. [ ] Add color and scale options
4. [ ] Implement duration-based cleanup
5. [ ] Write unit tests (5+ tests)
6. [ ] Add to MCP adapter

---

#### Task 2.3: Real-Time Sensor Monitoring
**Estimated:** 1.5 days

**Tool: `monitor_sensor_health`**
```python
def monitor_sensor_health(
    sensor_topics: List[str],
    duration: float = 10.0,
    alert_thresholds: Optional[Dict[str, Any]] = None
) -> OperationResult
```

**Metrics:**
- Data rate (Hz)
- Latency (ms)
- Dropout detection
- Quality metrics (SNR, variance)

**Implementation Steps:**
1. [ ] Implement topic rate monitoring
2. [ ] Add latency calculation
3. [ ] Detect data dropouts
4. [ ] Calculate quality metrics
5. [ ] Generate alerts for threshold violations
6. [ ] Write unit tests (4+ tests)
7. [ ] Add to MCP adapter

**Returns:**
```python
{
    "sensors": [
        {
            "topic": "/robot/scan",
            "type": "LaserScan",
            "rate_hz": 10.2,
            "latency_ms": 12.5,
            "dropouts": 0,
            "quality": "good",
            "alerts": []
        }
    ],
    "overall_health": "good"
}
```

---

#### Task 2.4: Sensor Data Processing
**Estimated:** 2 days

**Tool: `process_sensor_data`**
```python
def process_sensor_data(
    sensor_topic: str,
    processing_type: str,  # voxel_filter, statistical_filter, ground_removal, etc.
    parameters: Dict[str, Any]
) -> OperationResult
```

**Processing Types:**
1. **Point Cloud:**
   - Voxel grid filter
   - Statistical outlier removal
   - Ground plane removal
   - Radius outlier removal

2. **Image:**
   - Gaussian blur
   - Edge detection (Canny)
   - Color space conversion
   - ROI extraction

3. **IMU:**
   - Complementary filter
   - Bias compensation
   - Noise filtering

**Implementation Steps:**
1. [ ] Implement point cloud filters (PCL-based)
2. [ ] Implement image processing (OpenCV)
3. [ ] Implement IMU filters
4. [ ] Add parameter validation
5. [ ] Write unit tests (6+ tests)
6. [ ] Add to MCP adapter

---

#### Task 2.5: Sensor Recording
**Estimated:** 1 day

**Tool: `record_sensor_stream`**
```python
def record_sensor_stream(
    topics: List[str],
    output_path: str,
    duration: Optional[float] = None,  # None = until stopped
    compression: str = "lz4",
    max_bag_size_mb: int = 1024
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Use rosbag2 Python API
2. [ ] Implement topic selection
3. [ ] Add compression options
4. [ ] Implement file rotation
5. [ ] Add metadata tagging
6. [ ] Write unit tests (3+ tests)
7. [ ] Add to MCP adapter

---

## Week 3-4: Nav2 Integration & Developer Tools

### Nav2 Integration (10 new tools)

#### Task 3.1: Nav2 Initialization
**File:** `src/gazebo_mcp/tools/nav2_tools.py` (NEW)
**Estimated:** 2 days

**Tool: `initialize_nav2`**
```python
def initialize_nav2(
    robot_namespace: str,
    map_file: Optional[str] = None,  # None = SLAM mode
    planner: str = "dwb",  # dwb, teb, smac
    controller: str = "dwb",
    behavior_tree: Optional[str] = None,
    autostart: bool = True
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Create `nav2_tools.py` module
2. [ ] Check Nav2 installation
3. [ ] Generate Nav2 config files
4. [ ] Launch Nav2 nodes via ROS2 API
5. [ ] Wait for lifecycle nodes to activate
6. [ ] Verify all components ready
7. [ ] Write unit tests (4+ tests)
8. [ ] Add to MCP adapter

**Success Criteria:**
- [ ] Nav2 initializes in <10 seconds
- [ ] All lifecycle nodes in ACTIVE state
- [ ] Map loaded successfully (if provided)
- [ ] Costmaps configured correctly

---

#### Task 3.2: Navigation Goals
**Estimated:** 1.5 days

**Tool: `send_nav_goal`**
```python
def send_nav_goal(
    robot_namespace: str,
    goal_pose: Dict[str, Any],  # {position: {x, y}, orientation: {yaw}}
    planner_id: Optional[str] = None,
    behavior_tree: Optional[str] = None,
    timeout: float = 300.0
) -> OperationResult
```

**Tool: `cancel_nav_goal`**
**Tool: `get_nav_status`**

**Implementation Steps:**
1. [ ] Implement Nav2 action client
2. [ ] Send navigation goals
3. [ ] Track goal progress
4. [ ] Handle goal cancellation
5. [ ] Query navigation status
6. [ ] Write unit tests (5+ tests)
7. [ ] Add to MCP adapter

---

#### Task 3.3: Path Planning
**Estimated:** 2 days

**Tool: `plan_path`**
```python
def plan_path(
    robot_namespace: str,
    start_pose: Dict[str, Any],
    goal_pose: Dict[str, Any],
    planner_id: str = "GridBased",
    use_current_pose: bool = True
) -> OperationResult
```

**Tool: `visualize_path`**

**Implementation Steps:**
1. [ ] Implement path planning service client
2. [ ] Support multiple planners:
   - [ ] GridBased (NavFn, A*)
   - [ ] SmacPlanner2D
   - [ ] ThetaStar
3. [ ] Calculate path metrics (length, cost)
4. [ ] Visualize path with markers
5. [ ] Write unit tests (4+ tests)
6. [ ] Add to MCP adapter

---

#### Task 3.4: Costmap Management
**Estimated:** 1.5 days

**Tool: `get_costmap`**
**Tool: `update_costmap`**
**Tool: `clear_costmap`**

**Implementation Steps:**
1. [ ] Subscribe to costmap topics
2. [ ] Implement costmap clearing service
3. [ ] Add dynamic obstacle injection
4. [ ] Query costmap data
5. [ ] Write unit tests (4+ tests)
6. [ ] Add to MCP adapter

---

### Developer Tools (9 new tools)

#### Task 4.1: Debug Markers
**File:** `src/gazebo_mcp/tools/debug_tools.py` (NEW)
**Estimated:** 2 days

**Tool: `add_debug_marker`**
```python
def add_debug_marker(
    marker_type: str,  # line, arrow, point, text, sphere, box
    position: Dict[str, float],
    properties: Dict[str, Any],
    namespace: str = "debug",
    duration: float = 0.0,  # 0 = permanent
    marker_id: Optional[int] = None
) -> OperationResult
```

**Tool: `clear_debug_markers`**
**Tool: `list_debug_markers`**

**Implementation Steps:**
1. [ ] Create `debug_tools.py` module
2. [ ] Implement RViz marker publishing
3. [ ] Support marker types:
   - [ ] Lines and arrows
   - [ ] Points and spheres
   - [ ] Text labels
   - [ ] Boxes and cylinders
4. [ ] Add namespace management
5. [ ] Implement marker lifetime
6. [ ] Add marker clearing
7. [ ] Write unit tests (6+ tests)
8. [ ] Add to MCP adapter

---

#### Task 4.2: Model Highlighting
**Estimated:** 1 day

**Tool: `highlight_model`**
```python
def highlight_model(
    model_name: str,
    effect: str = "outline",  # outline, glow, color, transparent
    color: Optional[Dict[str, float]] = None,
    duration: float = 5.0
) -> OperationResult
```

**Implementation Steps:**
1. [ ] Implement visual plugin control
2. [ ] Add highlight effects
3. [ ] Manage highlight duration
4. [ ] Write unit tests (3+ tests)
5. [ ] Add to MCP adapter

---

#### Task 4.3: RViz Integration
**Estimated:** 1.5 days

**Tool: `launch_rviz`**
```python
def launch_rviz(
    robot_namespace: str,
    config_type: str = "auto",  # auto, navigation, slam, sensors
    config_file: Optional[str] = None,
    display_options: Optional[List[str]] = None
) -> OperationResult
```

**Tool: `add_rviz_visualization`**

**Implementation Steps:**
1. [ ] Generate RViz config files
2. [ ] Launch RViz via subprocess
3. [ ] Auto-configure for robot
4. [ ] Add visualization layers
5. [ ] Write unit tests (3+ tests)
6. [ ] Add to MCP adapter

---

#### Task 4.4: Recording & Playback
**Estimated:** 2 days

**Tool: `start_recording`**
**Tool: `stop_recording`**
**Tool: `playback_recording`**

**Implementation Steps:**
1. [ ] Implement rosbag2 recording
2. [ ] Add topic filtering
3. [ ] Implement compression
4. [ ] Add file rotation
5. [ ] Implement playback control
6. [ ] Add playback speed control
7. [ ] Write unit tests (5+ tests)
8. [ ] Add to MCP adapter

---

#### Task 4.5: Simulation Snapshots
**Estimated:** 1.5 days

**Tool: `save_snapshot`**
**Tool: `restore_snapshot`**

**Implementation Steps:**
1. [ ] Capture complete simulation state
2. [ ] Serialize to JSON/pickle
3. [ ] Restore all model states
4. [ ] Restore simulation time
5. [ ] Write unit tests (4+ tests)
6. [ ] Add to MCP adapter

---

## Testing Strategy

### Unit Tests
- Minimum 3 tests per tool
- Mock Gazebo/ROS2 when appropriate
- Test error handling
- Test edge cases

**Target:** 100+ new unit tests

### Integration Tests
- Test with real Gazebo simulation
- Multi-robot scenarios (5-10 robots)
- Nav2 full workflow tests
- Sensor fusion with real data

**Target:** 20+ integration tests

### End-to-End Tests
- Complete workflows (spawn → navigate → record)
- Multi-robot coordination
- Nav2 mission execution

**Target:** 5+ E2E tests

---

## Documentation Requirements

### Tool Documentation
- [ ] API reference for all new tools
- [ ] Parameter descriptions
- [ ] Return value formats
- [ ] Example usage for each tool

### Tutorials
- [ ] Multi-robot coordination tutorial
- [ ] Nav2 integration guide
- [ ] Sensor fusion walkthrough
- [ ] Debug tools usage guide

### Examples
- [ ] Multi-robot patrol example
- [ ] Nav2 waypoint mission
- [ ] Sensor fusion demo
- [ ] Recording and playback demo

**Target:** 4 comprehensive tutorials + 4 working examples

---

## File Structure

```
src/gazebo_mcp/tools/
├── multi_robot_tools.py        # NEW - Multi-robot coordination (6 tools)
├── sensor_fusion_tools.py      # NEW - Sensor fusion and processing (5 tools)
├── nav2_tools.py               # NEW - Nav2 integration (10 tools)
├── debug_tools.py              # NEW - Developer debugging tools (9 tools)
├── model_management.py         # EXISTING - Enhanced with highlights
├── sensor_tools.py             # EXISTING - Enhanced with monitoring
└── ...

mcp/server/adapters/
├── multi_robot_adapter.py      # NEW
├── sensor_fusion_adapter.py    # NEW
├── nav2_adapter.py             # NEW
├── debug_tools_adapter.py      # NEW
└── ...

tests/unit/
├── test_multi_robot_tools.py   # NEW - 15+ tests
├── test_sensor_fusion.py       # NEW - 20+ tests
├── test_nav2_tools.py          # NEW - 25+ tests
├── test_debug_tools.py         # NEW - 20+ tests
└── ...

tests/integration/
├── test_multi_robot_scenarios.py  # NEW
├── test_nav2_workflows.py         # NEW
└── ...

examples/
├── 09_multi_robot_patrol.py       # NEW
├── 10_nav2_waypoint_mission.py    # NEW
├── 11_sensor_fusion_demo.py       # NEW
├── 12_debug_and_record.py         # NEW
└── ...

docs/tutorials/
├── MULTI_ROBOT_COORDINATION.md    # NEW
├── NAV2_INTEGRATION.md            # NEW
├── SENSOR_FUSION_GUIDE.md         # NEW
├── DEBUGGING_TOOLS.md             # NEW
└── ...
```

---

## Dependencies

### Required ROS2 Packages
```bash
# Nav2
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup

# SLAM (for Phase 1 testing)
sudo apt install ros-humble-slam-toolbox

# RViz
sudo apt install ros-humble-rviz2

# Rosbag2
sudo apt install ros-humble-rosbag2

# TurtleBot3 (for testing)
sudo apt install ros-humble-turtlebot3*
```

### Python Dependencies
```bash
pip install numpy scipy scikit-learn opencv-python
```

---

## Success Criteria

### Week 1-2 Completion
- [ ] All 14 multi-robot and sensor tools implemented
- [ ] 40+ unit tests passing
- [ ] Multi-robot demo working (10 robots)
- [ ] Sensor fusion produces colored point clouds
- [ ] Documentation for Week 1-2 tools complete

### Week 3-4 Completion
- [ ] All 19 Nav2 and debug tools implemented
- [ ] 60+ unit tests passing
- [ ] Nav2 autonomous navigation working
- [ ] Debug markers and RViz integration working
- [ ] Recording/playback functional
- [ ] Documentation for Week 3-4 tools complete

### Phase 1 Complete
- [ ] 33 new tools implemented and tested
- [ ] 100+ unit tests passing (total: 540+)
- [ ] 20+ integration tests passing
- [ ] 4 tutorials written
- [ ] 4 working examples
- [ ] All documentation complete
- [ ] Backward compatibility maintained (100%)

---

## Risk Mitigation

### Risk: Nav2 Integration Complexity
**Mitigation:**
- Start with basic goal sending
- Add advanced features incrementally
- Use Nav2 examples as reference
- Test with TurtleBot3 first

### Risk: Multi-Robot Performance
**Mitigation:**
- Implement efficient namespace handling
- Use parallel queries where possible
- Add caching for fleet status
- Monitor performance with metrics

### Risk: Sensor Fusion Accuracy
**Mitigation:**
- Start with simple LiDAR+Camera fusion
- Use well-tested calibration methods
- Validate with ground truth data
- Add quality metrics

---

## Daily Progress Tracking

### Week 1
- [ ] Day 1: Multi-robot spawning (Task 1.1)
- [ ] Day 2: Multi-robot spawning complete + tests
- [ ] Day 3: Fleet status monitoring (Task 1.2)
- [ ] Day 4: Fleet command (Task 1.3)
- [ ] Day 5: Sensor fusion tool (Task 2.1 started)

### Week 2
- [ ] Day 6: Sensor fusion complete + tests
- [ ] Day 7: Sensor visualization (Task 2.2)
- [ ] Day 8: Sensor visualization complete
- [ ] Day 9: Sensor monitoring (Task 2.3) + processing (Task 2.4 started)
- [ ] Day 10: Sensor processing complete, Week 1-2 review

### Week 3
- [ ] Day 11: Nav2 initialization (Task 3.1)
- [ ] Day 12: Nav2 initialization complete + tests
- [ ] Day 13: Navigation goals (Task 3.2)
- [ ] Day 14: Path planning (Task 3.3)
- [ ] Day 15: Path planning complete

### Week 4
- [ ] Day 16: Debug markers (Task 4.1)
- [ ] Day 17: Debug markers complete + RViz integration (Task 4.3)
- [ ] Day 18: Recording & playback (Task 4.4)
- [ ] Day 19: Recording & playback complete
- [ ] Day 20: Final testing, documentation, Phase 1 review

---

## Next Steps (After This Document)

1. **Immediate:**
   - [ ] Create first new file: `multi_robot_tools.py`
   - [ ] Implement `spawn_robot_fleet` function
   - [ ] Write first unit test
   - [ ] Add to MCP adapter

2. **This Week:**
   - [ ] Complete Tasks 1.1, 1.2, 1.3 (Multi-robot core)
   - [ ] Start Task 2.1 (Sensor fusion)
   - [ ] Daily progress updates

3. **Continuous:**
   - [ ] Update this document with progress
   - [ ] Track issues and blockers
   - [ ] Update roadmap based on learnings

---

**Status:** 🚀 Ready to Begin Implementation
**Last Updated:** 2025-12-29
**Next Review:** End of Week 1
