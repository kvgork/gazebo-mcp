# Conversational Demo Guide

How to run demos by **talking to Claude** through the MCP server (the right way!).

## Overview

Instead of running bash commands, you interact with the Gazebo MCP server by asking Claude to do things in natural language. Claude calls the appropriate MCP tools automatically.

## Prerequisites

1. **Start the MCP Server** (one time setup):
```bash
cd <path-to-ros2_gazebo_mcp>/demos
./start_mcp_server.sh
```

Or manually:
```bash
cd <path-to-ros2_gazebo_mcp>
source /opt/ros/humble/setup.bash
/usr/bin/python3 -m gazebo_mcp.server
```

**IMPORTANT:** Must use `/usr/bin/python3` (system Python 3.10), NOT `python` (anaconda Python 3.11)!

2. **Start Gazebo** (in separate terminal):
```bash
source /opt/ros/humble/setup.bash
ign gazebo -r /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf
```

**Note:** Using `ign gazebo` (Ignition Fortress), not `gz sim`. Your system has Ignition Gazebo 6.17.0 installed.

3. **Start ros_gz_bridge** (in separate terminal):
```bash
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
  "/world/empty/control@ros_gz_interfaces/srv/ControlWorld" \
  "/world/empty/create@ros_gz_interfaces/srv/SpawnEntity" \
  "/world/empty/remove@ros_gz_interfaces/srv/DeleteEntity" \
  "/world/empty/set_pose@ros_gz_interfaces/srv/SetEntityPose"
```

## Conversational Demo - Just Talk to Claude!

Once the MCP server, Gazebo, and bridge are running, you can just **ask Claude** to do things:

### Example 1: Spawn a Model

**You say:**
> "Spawn a green box at position (2, 0, 0.5)"

**Claude will:**
1. Call the `spawn_model` MCP tool
2. Generate appropriate SDF
3. Place it at the specified position
4. Respond: "✅ Spawned green box at (2, 0, 0.5)"

---

### Example 2: List Models

**You say:**
> "What models are in the simulation?"

**Claude will:**
1. Call the `list_models` MCP tool
2. Return the list
3. Respond: "Found 3 models: ground_plane, test_box, sun"

---

### Example 3: Move a Model

**You say:**
> "Move the box to position (5, 2, 1)"

**Claude will:**
1. Call the `set_model_pose` MCP tool with new coordinates
2. Update the model position
3. Respond: "✅ Moved box to (5, 2, 1)"

---

### Example 4: Get Model State

**You say:**
> "Where is the box right now?"

**Claude will:**
1. Call the `get_model_state` MCP tool
2. Return current pose
3. Respond: "The box is at position (5, 2, 1) with orientation (0, 0, 0, 1)"

---

### Example 5: Delete a Model

**You say:**
> "Remove the box from the simulation"

**Claude will:**
1. Call the `delete_model` MCP tool
2. Remove the model
3. Respond: "✅ Deleted box from simulation"

---

### Example 6: Control Simulation

**You say:**
> "Pause the simulation"

**Claude will:**
1. Call the `pause_simulation` MCP tool
2. Pause the physics
3. Respond: "✅ Simulation paused"

**You say:**
> "Resume the simulation"

**Claude will:**
1. Call the `unpause_simulation` MCP tool
2. Resume physics
3. Respond: "✅ Simulation resumed"

---

### Example 7: Run Complete Demo

**You say:**
> "Run the hello world demo - spawn a box, move it around, then delete it"

**Claude will:**
1. Call `spawn_model` to create a box
2. Call `set_model_pose` to move it
3. Wait a moment
4. Call `set_model_pose` again to move it somewhere else
5. Call `delete_model` to remove it
6. Respond with step-by-step progress

---

## Available MCP Tools

When the MCP server is running, Claude has access to these tools:

### Model Management
- `spawn_model` - Create new models in simulation
- `delete_model` - Remove models
- `list_models` - List all models in world
- `get_model_state` - Get model position/orientation
- `set_model_pose` - Move/rotate models

### World Control
- `get_world_properties` - Get world info
- `reset_world` - Reset simulation to initial state
- `reset_simulation` - Full simulation reset

### Simulation Control
- `pause_simulation` - Pause physics
- `unpause_simulation` - Resume physics
- `get_simulation_time` - Get current sim time

### Sensor Data
- `get_camera_image` - Get camera feed
- `get_lidar_scan` - Get lidar data
- `get_imu_data` - Get IMU readings

## Natural Language Examples

Here are more examples of how you can talk to Claude:

### Spawning Objects

> "Create a red sphere at coordinates x=1, y=2, z=0.5"

> "Spawn a cube with 2m sides colored blue"

> "Add a robot model called turtlebot3 at the origin"

### Moving Things

> "Slide the box 3 meters to the right"

> "Rotate the sphere 90 degrees around the z-axis"

> "Move the robot to waypoint (5, 3, 0)"

### Querying State

> "How many models are loaded?"

> "What's the current position of the turtlebot?"

> "Is the simulation paused?"

### Complex Operations

> "Create an obstacle course with 3 walls and a target zone"

> "Spawn a robot, move it to (2,0), then move it to (4,2), then delete it"

> "Set up a simple scene with a ground plane and 5 random objects"

### Sensor Queries

> "What does the robot's camera see?"

> "Get the latest lidar scan"

> "Show me the IMU acceleration readings"

## How It Works

```
You (Natural Language)
    ↓
Claude (Understanding)
    ↓
MCP Server (Tool Selection)
    ↓
Gazebo Adapter (ROS2 Bridge)
    ↓
Gazebo Simulation (Action)
    ↓
Result back to Claude
    ↓
Claude (Natural Response)
    ↓
You (See result in simulation!)
```

## Token Efficiency

The MCP server uses the ResultFilter pattern for 98.7% token savings:

**You say:**
> "List all models, but only show me the ones with 'robot' in the name"

**Behind the scenes:**
```python
# Claude generates this code (executed locally by MCP server):
from gazebo_mcp.tools import list_models
from skills.common.filters import ResultFilter

# Get all models (could be 1000s):
all_models = list_models(response_format="full")

# Filter locally (98.7% token savings!):
robots = ResultFilter.search(all_models, "robot", ["name"])

# Return only filtered results to Claude:
return robots  # Only 5 models instead of 1000!
```

**Claude responds:**
> "Found 5 robot models: robot_1, robot_2, turtlebot3_burger, turtlebot3_waffle, pr2"

Only the 5 filtered results are sent to Claude, not all 1000 models!

## Troubleshooting

### "MCP server not responding"

**Check if server is running:**
```bash
ps aux | grep "mcp.server.server"
```

**Restart if needed:**
```bash
cd <path-to-ros2_gazebo_mcp>/demos
./start_mcp_server.sh
```

### "Tool not found"

**List available tools:**

You say:
> "What MCP tools are available?"

Claude will list all registered tools.

### "Gazebo not connected"

Make sure:
1. Gazebo is running: `ps aux | grep "gz sim"`
2. Bridge is running: `ps aux | grep "parameter_bridge"`
3. Services available: `ros2 service list | grep /world/`

## Comparison

### ❌ Old Way (Manual Commands):
```bash
ros2 service call /world/empty/create ros_gz_interfaces/srv/SpawnEntity "{entity_factory: ...long xml..."
```

### ✅ New Way (Natural Language):
> "Spawn a green box at (2, 0, 0.5)"

Much better! 🎉

## Demo Scripts via Conversation

Want to run the full Hello World demo conversationally?

**You say:**
> "I want to run a demo. First spawn a green box at position (2, 0, 0.5), then move it to (3, 1, 0.5), wait a second, then delete it. Show me progress after each step."

**Claude will:**
1. ✅ Spawning green box at (2, 0, 0.5)...
2. ✅ Spawned successfully
3. ✅ Moving box to (3, 1, 0.5)...
4. ✅ Moved successfully
5. ⏳ Waiting 1 second...
6. ✅ Deleting box...
7. ✅ Deleted successfully
8. 🎉 Demo complete!

## Demo 2: Obstacle Course (Conversational)

Once Gazebo and bridge are running, you can run the entire obstacle course just by talking!

### Complete Demo as Single Request

**You say:**
> "Run the complete obstacle course demo: spawn a robot at the origin, create 3 red obstacles at (2,0,0.5), (4,2,0.5), and (3,-1,0.5), place a green target at (8,0,0.5), then navigate the robot through waypoints (2,-1.5), (5,1), (6,-0.5), (7,0), and finally to the target at (8,0). Show progress after each step."

**Claude will:**
1. ✅ Spawning 3 obstacles...
2. ✅ Spawning target...
3. ✅ Spawning robot...
4. ✅ Navigating to waypoint 1 (2, -1.5)...
5. ✅ Navigating to waypoint 2 (5, 1)...
6. ✅ Navigating to waypoint 3 (6, -0.5)...
7. ✅ Navigating to waypoint 4 (7, 0)...
8. ✅ Reaching target at (8, 0)...
9. 🎉 Obstacle course complete!

---

### Step-by-Step Commands

Or break it down into smaller requests:

**Setup Phase:**
> "Set up an obstacle course with a robot, 3 obstacles, and a target zone. Place the robot at the origin, obstacles at (2,0,0.5), (4,2,0.5), and (3,-1,0.5), and the target at (8,0,0.5)."

**Navigation Phase:**
> "Navigate the robot through waypoint (2, -1.5) to avoid the first obstacle"
> "Move the robot to waypoint (5, 1)"
> "Navigate to waypoint (6, -0.5)"
> "Move to the final waypoint at (7, 0)"

**Goal Phase:**
> "Move the robot to the target position at (8, 0)"

**Verification:**
> "List all models in the simulation"
> "Where is the robot right now?"

**Cleanup:**
> "Clean up the obstacle course - delete all models except the ground plane and sun"

---

## Next Steps

1. **Start Gazebo + bridge** (2 terminals)
2. **Just talk to Claude!** - No more manual commands needed

The demos in `01_hello_world/` and `02_obstacle_course/` show the Python SDK way, but the **MCP way is much better** - just have a conversation!

---

**Remember:** The whole point of MCP is that you don't need to run commands or write code. Just tell Claude what you want, and it figures out which tools to call! 🚀
