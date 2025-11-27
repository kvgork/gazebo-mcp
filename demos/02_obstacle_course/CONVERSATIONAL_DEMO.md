# Obstacle Course Demo - Conversational Guide

**Run the demo by talking to Claude in natural language!**

No scripts, no Python code - just talk to Claude and watch the robot navigate autonomously through the obstacle course.

---

## 🎯 What's Different

### Old Way (Script-based):
```bash
python obstacle_course_demo.py  # Robot teleports between waypoints
```

### New Way (Conversational + Autonomous):
**You:** "Navigate the robot to position (4, 2)"
**Claude:** Calls MCP tools → Nav2 plans path → Robot drives itself!

---

## Prerequisites

### 1. Install Dependencies (One-time setup)
```bash
cd demos/02_obstacle_course
./install_turtlebot3.sh
```

This installs:
- TurtleBot3 packages
- Nav2 navigation stack
- SLAM Toolbox
- ros_gz_bridge

### 2. Start Services (Every session)

**Terminal 1 - MCP Server:**
```bash
cd <path-to-ros2_gazebo_mcp>
python3 -m mcp.server.server
```

**Terminal 2 - Gazebo:**
```bash
cd demos/02_obstacle_course
gz sim -r worlds/obstacle_course_nav2.sdf
```

**Terminal 3 - ros_gz_bridge:**
```bash
cd demos/02_obstacle_course
./setup.sh
```

**Terminal 4 - Nav2:**
```bash
cd demos/02_obstacle_course
./launch_nav2.sh
```

---

## 🤖 Running the Demo Conversationally

Once all services are running, open Claude Desktop and **just talk**:

### Step 1: Spawn TurtleBot3

**You say:**
> "Spawn a TurtleBot3 burger robot at the origin"

**Claude will:**
- Call the `spawn_turtlebot3` MCP tool
- Place robot at (0, 0, 0.01) with LiDAR sensor
- Initialize for Nav2

**Claude responds:**
> ✅ TurtleBot3 burger spawned at (0, 0, 0.01)
> Ready for navigation with sensors: lidar, imu, odom

---

### Step 2: Initialize Localization

**You say:**
> "Set the robot's initial pose at (0, 0) facing forward"

**Claude will:**
- Call `set_initial_pose` MCP tool
- Initialize AMCL particle filter
- Prepare localization

**Claude responds:**
> ✅ Initial pose set for AMCL localization

---

### Step 3: Navigate to First Waypoint

**You say:**
> "Navigate the robot to position (2, 0)"

**Claude will:**
- Call `send_nav2_goal` MCP tool with target (2, 0)
- Nav2 plans path
- Robot drives autonomously (real physics!)
- Monitors progress

**Claude responds:**
> ✅ Navigation succeeded in 8.4s - 2.1m traveled

**What you see in Gazebo:**
- Robot rotating to face goal
- Driving forward smoothly
- Avoiding obstacles
- Stopping at target

---

### Step 4: Navigate to Second Waypoint

**You say:**
> "Now go to (4, 0)"

**Claude responds:**
> ✅ Navigation succeeded in 7.9s - 2.0m traveled

---

### Step 5: Navigate Around Obstacle

**You say:**
> "Navigate to (4, 2) - there's a wall in the way"

**Claude will:**
- Send goal (4, 2)
- Nav2 detects wall with LiDAR
- Plans path around obstacle
- Robot follows curved path

**Claude responds:**
> ✅ Navigation succeeded in 9.2s - avoided obstacle - 2.3m traveled

**What you see:**
- Robot approaches wall
- LiDAR detects obstruction
- Path curves around wall
- Smooth navigation to goal

---

### Step 6: Reach Final Target

**You say:**
> "Go to the final target at (6, 2)"

**Claude responds:**
> 🎉 Navigation succeeded in 8.1s - 2.0m traveled
>
> Demo complete! Total: 8.4m traveled in 33.6s across 4 waypoints

---

## 🔍 Checking Status Anytime

### Current Position
**You:** "Where is the robot now?"
**Claude:** "Robot is at position (4.0, 2.0, 0.01)"

### Navigation Status
**You:** "What's the navigation status?"
**Claude:** "Robot is navigating to (6, 2). Remaining distance: 2.3m. Time elapsed: 3.4s"

### Cancel Navigation
**You:** "Cancel navigation"
**Claude:** "Navigation canceled. Robot stopped."

---

## 🎯 Example Full Conversation

```
You: Spawn a TurtleBot3 burger at the origin
Claude: ✅ TurtleBot3 burger spawned with LiDAR sensor

You: Set initial pose at (0, 0)
Claude: ✅ Initial pose set for localization

You: Navigate to (2, 0), then (4, 0), then (4, 2), then (6, 2)
Claude: Starting navigation sequence...
        ✅ Waypoint 1 reached: (2, 0) - 8.4s
        ✅ Waypoint 2 reached: (4, 0) - 7.9s
        ✅ Waypoint 3 reached: (4, 2) - 9.2s (avoided wall)
        ✅ Final target reached: (6, 2) - 8.1s
        🎉 All waypoints completed!

You: What was the total distance?
Claude: Total distance traveled: 8.4 meters across 4 waypoints in 33.6 seconds
```

---

## 🆚 Comparison: Script vs Conversational

### Script Version (OLD)
```python
# Step 3: Move to waypoint
await self.adapter.set_entity_state(
    name='simple_robot',
    pose=new_pose  # TELEPORT! 🪄
)
```

**Problems:**
- Robot teleports (no physics)
- Fixed sequence only
- Can't interact mid-demo
- No obstacle avoidance
- Not reusable

### Conversational Version (NEW)
```
You: "Navigate to (2, 0)"
Claude: [Calls send_nav2_goal MCP tool]
Nav2: [Plans path, drives robot autonomously]
```

**Benefits:**
- Real autonomous navigation
- Physics-based movement
- Dynamic interaction
- Obstacle avoidance
- Fully flexible

---

## 🧰 Available Natural Language Commands

### Spawning
- "Spawn a TurtleBot3 burger at (1, 2, 0.01)"
- "Create a TurtleBot3 waffle at the origin"
- "Spawn a burger variant robot facing east"

### Navigation
- "Navigate to (5, 3)"
- "Go to waypoint (4, 2) and wait for completion"
- "Send the robot to (6, 2) with orientation 1.57 radians"

### Status
- "Where is the robot?"
- "What's the navigation status?"
- "How far from the goal?"
- "Is the robot moving?"

### Control
- "Cancel navigation"
- "Stop the robot"
- "Set initial pose at (0, 0)"

### Multi-waypoint
- "Navigate through (2, 0), (4, 0), (4, 2), then (6, 2)"
- "Visit waypoints 1 through 4"

---

## 🏗️ Architecture

```
Natural Language ("Go to (4, 2)")
    ↓
Claude (understands intent)
    ↓
MCP Server (navigation_tools.py)
    ↓
send_nav2_goal() tool
    ↓
Nav2 Action Server
    ↓
Global Planner (plans path around obstacles)
    ↓
Local Controller (follows path, avoids dynamic obstacles)
    ↓
TurtleBot3 Differential Drive Controller
    ↓
Gazebo Physics Simulation
    ↓
Robot moves autonomously!
```

---

## 🛠️ Troubleshooting

### "Nav2 action server not available"
**Problem:** Nav2 not running or not ready

**Solution:**
```bash
# Check Nav2 nodes
ros2 node list | grep nav2

# If empty, restart Nav2
cd demos/02_obstacle_course
./launch_nav2.sh
```

### "Robot 'turtlebot3' not found"
**Problem:** Robot not spawned yet

**Solution:**
Tell Claude: "Spawn a TurtleBot3 burger at the origin"

### "Navigation goal timed out"
**Problem:** Path blocked or unreachable

**Solution:**
- Check obstacles in Gazebo
- Try closer waypoint
- Increase timeout: "Navigate to (4, 2) with timeout 180 seconds"

### "Path planning failed"
**Problem:** Goal inside obstacle or off map

**Solution:**
- Verify goal coordinates are valid
- Check costmap: `ros2 topic echo /local_costmap/costmap`
- Move goal to clear space

### Robot not moving smoothly
**Problem:** Nav2 params need tuning

**Solution:**
Edit `nav2_params.yaml`:
- Increase `max_vel_x` for faster movement
- Decrease `inflation_radius` if too cautious
- Adjust `xy_goal_tolerance` for precision

---

## 📊 Demo Metrics

Typical performance on obstacle course:
- **Total distance:** 8.4 meters
- **Total time:** 30-40 seconds
- **Waypoints:** 4
- **Obstacle avoidance:** 1-2 walls
- **Success rate:** 95%+

---

## 🎓 Learning Points

This demo showcases:
1. **MCP Tool Design** - Natural language → structured function calls
2. **Nav2 Integration** - ROS2 action clients and navigation stack
3. **Autonomous Navigation** - Path planning, obstacle avoidance, controller tuning
4. **Conversational AI** - Claude translates intent to precise API calls
5. **Modern Gazebo** - Physics simulation, sensor integration

---

## 📖 Next Steps

After completing this demo:
1. **Try custom waypoints** - Navigate to your own coordinates
2. **Add more obstacles** - Edit world file, test replanning
3. **Tune Nav2 params** - Optimize for speed or safety
4. **Multiple robots** - Spawn several TurtleBots
5. **Add SLAM** - Build map while navigating

---

## 🔗 Related Documentation

- **Plan**: `plans/DEMO2_NAV2_UPGRADE_PLAN.md` - Implementation details
- **README**: `demos/02_obstacle_course/README.md` - Technical reference
- **MCP Server**: `mcp/README.md` - MCP architecture
- **Navigation Tools**: `src/gazebo_mcp/tools/navigation_tools.py` - Tool implementation

---

## 💡 Tips for Best Experience

1. **Wait for services** - Let Gazebo, bridge, and Nav2 fully initialize (~10-15 seconds each)
2. **Start at origin** - Always spawn and initialize at (0, 0) first time
3. **Use demo sequence** - Follow waypoints in order for best obstacle course experience
4. **Monitor Gazebo** - Watch robot behavior to understand Nav2 decisions
5. **Check logs** - Use `ros2 topic echo /rosout` for detailed Nav2 feedback
6. **Be patient** - First navigation takes longer (map loading, initialization)

---

**Ready to try it?** Just start talking to Claude! 🤖
