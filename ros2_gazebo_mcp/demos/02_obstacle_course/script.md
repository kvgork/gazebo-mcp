# Demo 7.1.2: Obstacle Course Challenge

**Duration**: 10 minutes
**Audience**: Technical users, researchers, robotics engineers
**Wow Factor**: 4/5
**Difficulty**: Intermediate

---

## Overview

This demo showcases autonomous navigation through a procedurally-generated obstacle course. It demonstrates the MCP server's world generation capabilities, sensor integration (LiDAR), and autonomous planning algorithms.

**Key Message**: "AI can generate complex environments and solve navigation challenges autonomously."

---

## Prerequisites

### Hardware
- GPU recommended (for better Gazebo performance)
- 16GB RAM (for nav2 stack)
- Ubuntu 22.04 or 24.04

### Software
- ROS2 Humble with Nav2
- Gazebo Harmonic
- MCP Server with Phase 4 tools
- TurtleBot3 packages

### Additional Packages
```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup \
                 ros-humble-turtlebot3 ros-humble-turtlebot3-gazebo
```

---

## Setup (Pre-Demo)

### Terminal 1: Gazebo
```bash
source /opt/ros/humble/setup.bash
gz sim empty.sdf
```

### Terminal 2: MCP Server
```bash
source /opt/ros/humble/setup.bash
gazebo-mcp-server --log-level INFO --enable-phase4
```

### Terminal 3: Nav2 (Optional - for autonomous navigation)
```bash
source /opt/ros/humble/setup.bash
# Will be started during demo via Claude
```

### Terminal 4: Claude Code
```bash
claude-code
```

### Pre-Check (5 min before)
```
[To Claude] "Can you verify Gazebo is running and Phase 4 tools are available?"
```

Expected: "Yes, Gazebo is running. Phase 4 world generation tools are loaded."

---

## Demo Script (10 minutes)

### Part 1: Introduction & World Generation (3 minutes)

**[Face audience]**

> "Good afternoon. Today I'm going to show you something that combines procedural world generation with autonomous robotics.
>
> Here's the challenge: Can AI create a difficult obstacle course AND solve it autonomously? Let's find out.
>
> Watch as I describe what I want in plain English, and Claude handles all the complexity..."

**[Turn to screen]**

**[To Claude]**
```
"Create a challenging obstacle course with 15 obstacles of varying heights.
Make it solvable but difficult - think navigation challenge for a small robot.
Use a variety of shapes and sizes."
```

**Expected Response**:
```
I'll create a challenging obstacle course using the Phase 4 world generation tools.

Creating obstacle course...
✓ Spawning 15 obstacles with varying heights (0.2m to 1.0m)
✓ Using mixed shapes: boxes, cylinders, and complex forms
✓ Placing obstacles in navigable pattern (maze-like)
✓ Ensuring solvable paths exist
✓ Course dimensions: 10m x 10m

Obstacle course generation complete!
Course difficulty: HARD (narrow passages, multiple route options)
```

**[Narrate while obstacles appear]**

> "Notice several things happening here. First, Claude understood 'challenging' - it's placing obstacles strategically, not randomly.
>
> Second, it's using varying heights - some obstacles a robot could see over, others it must navigate around.
>
> Third, it's generating a solvable course - there ARE paths through, they're just difficult to find.
>
> This is procedural generation with intelligence."

**Visual Check**:
- ✓ 15 obstacles visible in Gazebo
- ✓ Varying heights (check tall and short obstacles)
- ✓ Mixed shapes (boxes, cylinders)
- ✓ Pattern looks navigable but challenging
- ✓ No obstacles completely blocking all paths

**Recovery**: If generation fails → Use pre-generated world file (see Recovery Plan)

---

### Part 2: Robot Deployment (2 minutes)

**[To Claude]**
```
"Spawn a TurtleBot3 Waffle at the start position of the course.
Equip it with LiDAR for obstacle detection.
Also, adjust the camera view to show the entire course from above."
```

**Expected Response**:
```
Deploying TurtleBot3 Waffle with sensors...

✓ Spawning TurtleBot3 Waffle model
✓ Position: Start of obstacle course (edge of course area)
✓ LiDAR sensor active (360° scanning, 12m range)
✓ Camera view adjusted to top-down perspective
✓ Course fully visible

Robot ready for navigation challenge.
```

**[Point to screen]**

> "Now we have a bird's-eye view. You can see the robot - there at the start - and the full course ahead.
>
> The robot is equipped with a LiDAR sensor - you'll see it scanning as green rays in the simulation. This gives the robot a 360-degree view of obstacles around it.
>
> Watch the LiDAR visualization - it's constantly scanning..."

**[If LiDAR visualization visible]**
> "See those rays? That's the robot sensing its environment in real-time."

**Visual Check**:
- ✓ Robot spawned at course start
- ✓ Camera shows full course (top-down view)
- ✓ LiDAR visualization visible (green scanning rays)
- ✓ Robot at correct orientation (facing into course)
- ✓ No collisions with obstacles

**Recovery**: If robot spawns inside obstacle → Teleport to clear position

---

### Part 3: Autonomous Navigation (4 minutes)

**[To Claude]**
```
"Navigate the robot through this obstacle course to reach the opposite side.
Use the LiDAR to avoid obstacles.
Show me real-time sensor data and the navigation path being planned."
```

**Expected Response**:
```
Initiating autonomous navigation...

✓ Loading Nav2 navigation stack
✓ Creating map from LiDAR scans
✓ Planning path through obstacle course
✓ Starting autonomous navigation

Navigation active - watch the robot find its way...
[Real-time updates as robot moves]
```

**[Narrate during navigation - this is key engagement!]**

> "Now the interesting part begins. The robot is doing several things simultaneously:
>
> **[As robot starts moving]**
> First, it's building a map of the environment using only its LiDAR sensor. It's never seen this course before - it's discovering obstacles in real-time.
>
> **[As robot approaches first obstacle]**
> Watch here - the robot detects this obstacle and calculates a path around it. This isn't pre-programmed - it's dynamic planning.
>
> **[If robot pauses to replan]**
> See how it paused? It detected a potential collision and is recalculating. This is autonomous decision-making in action.
>
> **[As robot navigates tight passage]**
> This is a tight squeeze. The robot knows its own dimensions and is calculating whether it can fit. This is sophisticated spatial reasoning.
>
> **[If robot takes unexpected route]**
> Interesting - it chose a different path than I would have. This shows it's truly autonomous, making its own decisions based on sensor data."

**Key Moments to Highlight**:
- Robot scanning obstacles
- Path planning visualization (if visible)
- Successful obstacle avoidance
- Navigation through tight spaces
- Course completion

**Visual Check**:
- ✓ Robot moving autonomously
- ✓ LiDAR scanning visible
- ✓ Robot avoiding obstacles successfully
- ✓ No collisions (minor bumps OK, stuck is NOT OK)
- ✓ Making progress toward goal

**Recovery Plans**:
- If robot gets stuck → [To Claude] "The robot seems stuck. Can you teleport it past this obstacle and continue?"
- If navigation fails to start → Use teleoperation fallback
- If crashes → Emergency recovery (see below)

---

### Part 4: Analysis & Metrics (1 minute)

**[Once robot reaches end or after 3-4 minutes of navigation]**

**[To Claude]**
```
"Give me statistics on this navigation run:
time taken, distance traveled, closest approach to any obstacle,
and number of obstacles successfully avoided."
```

**Expected Response**:
```
Navigation Statistics:

Time Elapsed: 47.3 seconds
Total Distance: 12.4 meters
Straight-line Distance: 9.2 meters
Path Efficiency: 74% (actual vs optimal path)

Obstacle Encounters:
- Obstacles Detected: 15/15 (100%)
- Closest Approach: 0.15m (safe clearance)
- Collisions: 0
- Re-planning Events: 3

Sensor Performance:
- LiDAR Scans: 473 scans processed
- Map Updates: 89
- Average Processing Time: 12ms per scan

Result: ✓ SUCCESS - Course completed safely
```

**[To audience]**

> "Look at these numbers. The robot:
> - Detected all 15 obstacles it encountered
> - Maintained safe clearance (15cm minimum)
> - Zero collisions
> - Completed the course in under a minute
>
> And here's the kicker - this was a completely novel environment. The robot had never seen this specific obstacle course before. It was generated moments ago and solved autonomously.
>
> This demonstrates the power of combining AI-driven world generation with autonomous robotics."

---

### Closing (30 seconds)

**[Face audience]**

> "So in 10 minutes we:
> 1. Generated a complex, challenging environment procedurally
> 2. Deployed a robot with realistic sensors
> 3. Solved a navigation challenge autonomously
> 4. Analyzed performance metrics
>
> All driven by natural language commands to Claude.
>
> This is the future of robotics research and development - rapid iteration, AI-assisted development, autonomous validation."

**[Open for questions]**

---

## Demo Variations

### Difficulty Levels

**Easy Mode** (for less technical audiences):
```
[To Claude] "Create an easy obstacle course with 5 obstacles and wide spacing."
```

**Hard Mode** (for impressive demos):
```
[To Claude] "Create an expert-level maze with 25 obstacles and very narrow passages.
Make it as challenging as possible while still solvable."
```

**Timed Challenge**:
```
[To Claude] "Create a course and challenge: the robot must complete it in under 60 seconds."
```

### Interactive Variations

**Audience Participation**:
> "What kind of obstacle course should I create? Give me suggestions!"
> [Take 2-3 suggestions, combine them]

**Live Modifications**:
```
[To Claude] "While the robot is navigating, add 3 more obstacles to make it harder."
```
(Demonstrates dynamic world modification)

**Multiple Robots**:
```
[To Claude] "Spawn 3 more robots and have them all race through the course."
```

---

## Key Talking Points

### For Technical Audiences

- **SLAM (Simultaneous Localization and Mapping)**: Robot builds map while navigating
- **Nav2 Stack**: Industry-standard navigation framework
- **Cost Maps**: How robot represents obstacles and free space
- **Path Planning**: DWB (Dynamic Window Approach) for local planning
- **Sensor Fusion**: Combining LiDAR data with odometry

### For Research Audiences

- **Reproducibility**: Course can be regenerated with same seed
- **Benchmarking**: Standardized courses for algorithm comparison
- **Parameterization**: Difficulty levels, obstacle density, passage width
- **Metrics**: Quantitative evaluation of navigation performance
- **Generalization**: Robot navigates never-before-seen environments

### For Non-Technical Audiences

- **Autonomous**: Robot makes its own decisions
- **Adaptive**: Adjusts to changing environments
- **Intelligent**: Uses sensors like we use eyes
- **Safe**: Maintains clearance, avoids collisions
- **Fast**: Efficient path finding

---

## Success Criteria

**Minimum Success** (Demo still effective):
- ✅ Obstacle course generates
- ✅ Robot spawns correctly
- ✅ Robot navigates at least 50% of course
- ✅ Audience sees autonomous behavior

**Full Success** (Ideal execution):
- ✅ Course generates perfectly
- ✅ Robot completes full course
- ✅ Zero collisions
- ✅ Metrics displayed
- ✅ Under 10 minutes total

**Exceptional** (Bonus):
- ✅ Everything above
- ✅ Live course modification during navigation
- ✅ Multiple robots racing
- ✅ Audience participation incorporated
- ✅ Spectacular obstacle avoidance moments

---

## Recovery Plan

### Course Generation Fails

**Immediate**:
```bash
# Load pre-generated world
gz sim worlds/obstacle_course_preset.sdf
```

**Explanation**: "Let me load a pre-generated course we prepared..."

**Prevention**: Have `obstacle_course_preset.sdf` ready in `demos/02_obstacle_course/worlds/`

### Robot Won't Spawn

**Immediate**:
```
[To Claude] "Let's try spawning a TurtleBot3 Burger instead."
```

If still fails:
```bash
# Manual spawn
ros2 run gazebo_ros spawn_entity.py -entity turtlebot3 \
    -file /opt/ros/humble/share/turtlebot3_description/urdf/turtlebot3_waffle.urdf \
    -x 0 -y 0 -z 0.1
```

### Navigation Won't Start

**Option 1** - Simplified navigation:
```
[To Claude] "Use simple teleoperation to navigate through the course."
```

**Option 2** - Demonstration mode:
```
[To Claude] "Show me the path the robot would take, then teleport it along that path."
```

**Option 3** - Backup video:
"Let me show you a recording from our test run..."

### Robot Gets Stuck

**Immediate**:
```
[To Claude] "The robot encountered a tricky situation.
Teleport it forward 1 meter and resume navigation."
```

**Narrate**: "In development, we can quick-reset positions. In production, the robot would have additional recovery behaviors."

### Complete Failure

1. Stay calm and confident
2. Switch to explaining the concept with the static scene
3. Show backup video
4. Offer live demo after presentation

---

## Files

```
demos/02_obstacle_course/
├── script.md                      # This file
├── setup.sh                       # Automated setup
├── config.yaml                    # Configuration
├── timing_guide.md                # Detailed timing breakdown
├── variations.md                  # Additional demo variations
├── troubleshooting.md             # Detailed troubleshooting
├── worlds/
│   ├── obstacle_course_easy.sdf   # Pre-generated easy course
│   ├── obstacle_course_medium.sdf # Pre-generated medium course
│   └── obstacle_course_hard.sdf   # Pre-generated hard course
├── videos/
│   └── backup_navigation.mp4      # Backup video
└── analysis/
    ├── metrics_template.yaml      # Metrics collection template
    └── performance_analysis.py    # Post-demo analysis script
```

---

## Practice Checklist

Before delivering:
- [ ] Run demo 3+ times end-to-end
- [ ] Record backup video of successful run
- [ ] Test on presentation hardware
- [ ] Generate pre-made obstacle courses (easy/medium/hard)
- [ ] Verify Nav2 stack installed and working
- [ ] Time each section (should total <10 min)
- [ ] Prepare answers to common questions
- [ ] Test recovery procedures
- [ ] Have emergency scripts ready
- [ ] Review narration points

---

**Demo Status**: Advanced difficulty - practice recommended
**Technical Requirements**: Medium-High (requires Nav2)
**Wow Factor**: High (autonomous navigation impresses audiences)
**Recommended For**: Technical demos, research presentations, capability showcases
