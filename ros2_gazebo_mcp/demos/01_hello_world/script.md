# Demo 7.1.1: "Hello World" - First Robot

**Duration**: 5 minutes
**Audience**: First-time users, executives, decision-makers
**Wow Factor**: 2/5
**Difficulty**: Beginner

---

## Overview

This demo showcases the absolute basics of the Gazebo MCP Server - AI controlling a robot in Gazebo through natural language. It's designed to be simple, reliable, and impressive even to non-technical audiences.

**Key Message**: "You can control robots with plain English - no coding required."

---

## Prerequisites

### Hardware
- Computer with GPU (recommended)
- Minimum 8GB RAM
- Ubuntu 22.04 or 24.04

### Software
- ROS2 Humble installed
- Gazebo Harmonic installed
- MCP Server installed and configured
- Claude Code or compatible MCP client

### Pre-Demo Setup (15 minutes before demo)
1. Test all systems - run through demo once
2. Have backup video ready
3. Clear Gazebo world
4. Position screen for audience visibility
5. Close unnecessary applications

---

## Setup (Pre-Demo)

### Terminal 1: Gazebo
```bash
source /opt/ros/humble/setup.bash
gz sim empty.sdf
```

**Expected**: Empty Gazebo world loads, shows ground plane

### Terminal 2: MCP Server
```bash
source /opt/ros/humble/setup.bash
cd /path/to/gazebo-mcp/ros2_gazebo_mcp
gazebo-mcp-server --log-level INFO
```

**Expected**: Server starts, shows "MCP Server Ready" message

### Terminal 3: Claude Code
```bash
claude-code
```

**Expected**: Claude Code interface appears, MCP tools loaded

### Pre-Check
Quick test before audience arrives:
```
[To Claude] "Can you see the Gazebo simulator?"
```
Expected: "Yes, I can see Gazebo is running with an empty world."

---

## Demo Script (5 minutes)

### Part 1: Introduction (1 minute)

**[Face audience, Gazebo visible on screen]**

> "Good morning everyone. Today I'm going to show you something that seemed impossible just a few years ago - controlling a robot simulation using nothing but natural language.
>
> Behind me you can see Gazebo, a professional-grade robotics simulator used by companies like Boston Dynamics and research labs worldwide. And here [point to Claude Code] is Claude, an AI assistant.
>
> Watch what happens when I simply ask Claude to help me with robotics..."

**[Turn to screen, keep talking so audience hears]**

---

### Part 2: Spawn Robot (1.5 minutes)

**[Type/Say to Claude]**
```
"Please start a Gazebo simulation and spawn a TurtleBot3 robot at the center of the world."
```

**Expected Response**:
```
I'll help you spawn a TurtleBot3 robot in Gazebo.

Using the spawn_model tool to create a TurtleBot3 Burger robot...
✓ Robot spawned successfully at position (0, 0, 0)
```

**[Point to screen as robot appears]**

> "Notice a few things here. First, I didn't write any code. Second, Claude understood 'TurtleBot3' - it knows robotics terminology. Third, the robot appeared exactly where I asked - at the center."

**Visual Check**:
- ✓ Robot visible in Gazebo
- ✓ Robot at origin (0, 0, 0)
- ✓ Robot properly oriented

**[If robot doesn't appear - see Recovery Plan below]**

---

### Part 3: Basic Control (2 minutes)

**[To Claude]**
```
"Make the robot drive forward 2 meters, then turn around and come back to the start."
```

**Expected Response**:
```
I'll command the robot to move forward 2 meters, rotate 180 degrees,
and return to the starting position.

Executing movement commands...
✓ Moving forward 2 meters
✓ Rotating 180 degrees
✓ Returning to start position
✓ Robot back at origin
```

**[Narrate while robot moves]**

> "Watch the robot now. It's receiving commands through ROS2 - the Robot Operating System - but I never had to touch ROS2 directly. Claude handles all the complexity.
>
> The robot uses sensors to track its position, motors to move, and control algorithms to execute the path. All of this orchestrated by simple conversation."

**Visual Check**:
- ✓ Robot moves forward smoothly
- ✓ Robot stops at ~2 meters
- ✓ Robot rotates 180°
- ✓ Robot returns to origin
- ✓ No collisions or errors

---

### Part 4: Add Complexity (1.5 minutes)

**[To Claude]**
```
"Now add some obstacles around the robot and have it navigate around them back to the origin."
```

**Expected Response**:
```
I'll create obstacles around the robot and command it to navigate
autonomously back to the origin while avoiding them.

Spawning obstacles...
✓ Created 4 obstacles in a pattern around the robot
✓ Enabling autonomous navigation
✓ Robot navigating around obstacles
✓ Reached origin successfully
```

**[Point out key moments]**

> "This is where it gets impressive. Claude didn't just add obstacles randomly - it placed them strategically to create a challenge.
>
> Now the robot has to plan its own path. Watch as it uses its LiDAR sensor to detect obstacles and navigate around them. This is autonomous robotics in action."

**Visual Check**:
- ✓ 3-5 obstacles spawn around robot
- ✓ Obstacles don't block path completely
- ✓ Robot pauses to scan (LiDAR working)
- ✓ Robot navigates around obstacles
- ✓ Robot reaches origin

---

### Closing (30 seconds)

**[Turn back to audience]**

> "So what just happened? In under 5 minutes, we:
> - Spawned a professional robot model
> - Commanded precise movements
> - Created a dynamic environment
> - Enabled autonomous navigation
>
> All through natural language. No coding. No robotics expertise required.
>
> This is the future of robotics development - accessible, intuitive, and powerful."

**[Pause for questions]**

---

## Key Talking Points

**During Demo**:
- ✅ "Natural language control - no coding required"
- ✅ "AI understands robotics concepts natively"
- ✅ "Professional-grade simulation - same tools as Boston Dynamics"
- ✅ "Accessible to non-experts, powerful for professionals"

**For Technical Audiences**:
- Works with ROS2 and Gazebo - industry standards
- MCP (Model Context Protocol) for AI-robot communication
- Supports complex robots, sensors, physics
- Extensible for custom applications

**For Executives**:
- Lowers barrier to entry for robotics development
- Faster prototyping and iteration
- Reduces training time for new team members
- Accelerates research and development

---

## Recovery Plan

### If robot doesn't spawn:
**Immediate**:
1. [To Claude] "Let me try that again - please spawn a TurtleBot3."
2. If still fails: Switch to pre-recorded video
3. Narrate: "Occasionally we have network delays. Let me show you a recording..."

**Root Causes**:
- Model files not found → Check `turtlebot3_description` package installed
- Gazebo not responding → Restart Gazebo before demo
- MCP connection lost → Restart MCP server

### If robot doesn't move:
**Immediate**:
1. Check robot is selected in Gazebo (should have focus)
2. [To Claude] "The robot seems paused. Can you reset and try again?"
3. If fails: Use fallback simple command
4. Last resort: Pre-recorded video

**Root Causes**:
- No ROS2 controller loaded → Spawn robot with `--wait-for-controller`
- Physics paused → Check Gazebo play button
- Velocity commands not reaching robot → Check topic `cmd_vel`

### If obstacles block robot completely:
**Immediate**:
1. [To Claude] "These obstacles are too dense. Please remove a few to make a path."
2. Narrate: "Sometimes we need to adjust the difficulty..."
3. Continue when path clears

**Prevention**:
- Test obstacle generation before demo
- Have Claude use "solvable" parameter
- Manually verify path exists

### If navigation fails (robot stuck):
**Immediate**:
1. [To Claude] "The robot seems stuck. Let's teleport it to the goal."
2. Narrate: "In development, we can quickly reset positions..."
3. Demonstrate goal achievement

### Technical Failure (Complete):
**If all else fails**:
1. Stay calm, smile
2. "Let me show you the video from our test run this morning..."
3. Play backup video
4. Narrate over video
5. Offer to demonstrate offline after session

---

## Success Criteria

**Minimum Success** (Demo still effective if you achieve this):
- ✅ Robot spawns
- ✅ Robot moves at least once
- ✅ Audience sees natural language control

**Full Success** (Ideal execution):
- ✅ Robot spawns perfectly
- ✅ All movements execute smoothly
- ✅ Obstacles create and robot navigates
- ✅ No technical glitches
- ✅ Under 5 minutes total time

**Exceptional** (Bonus points):
- ✅ Everything above
- ✅ Take audience suggestion: "Can it draw a circle?"
- ✅ Show sensor data visualization
- ✅ Demonstrate recovery from failure gracefully

---

## Post-Demo

### Immediate
1. Thank audience for attention
2. Offer to answer questions
3. Share contact info / documentation

### Follow-Up Materials
- Share GitHub repository: `https://github.com/yourusername/gazebo-mcp`
- Documentation: Point to Tutorial 7.2.1 "Getting Started"
- Video recording of demo (if recorded)
- Email for questions

### Debrief
Document what worked and what didn't:
- Technical issues encountered
- Audience reaction and engagement
- Questions asked (for FAQ)
- Timing (too fast/slow?)

---

## Variations

### For Technical Audience
Add these elements:
- Show MCP tool calls in terminal
- Explain ROS2 topics: `gz topic -l`
- Demonstrate sensor data: "Show me LiDAR readings"
- Quick code peek: Show Python MCP tool

### For Quick Demo (3 minutes)
Skip Part 4 (obstacles), go straight to closing

### For Extended Demo (10 minutes)
Add:
- Part 5: Sensor visualization "Show camera feed"
- Part 6: Multiple robots "Spawn 3 more robots"
- Part 7: Custom world "Create a warehouse environment"

### For Live Q&A
Common questions and prep:
- "Can it work with real robots?" → Yes, same MCP tools
- "What languages?" → Python, C++, any language with MCP
- "Cost?" → Open source, free to use
- "Learning curve?" → See Tutorial series

---

## Files Included

```
demos/01_hello_world/
├── script.md                   # This file
├── setup.sh                    # Automated setup script
├── config.yaml                 # Demo configuration
├── backup_video.mp4           # Fallback video (create during practice)
├── troubleshooting.md         # Detailed troubleshooting
└── slides/                    # Optional presentation slides
    ├── intro.pdf
    └── demo_outline.pdf
```

---

## Practice Checklist

Before delivering this demo:
- [ ] Run through demo 3 times successfully
- [ ] Record backup video
- [ ] Test on actual presentation hardware
- [ ] Verify internet connection (if needed)
- [ ] Have troubleshooting guide printed
- [ ] Know recovery procedures by heart
- [ ] Time yourself (should be under 5 min)
- [ ] Test with a friend as audience
- [ ] Prepare for common questions
- [ ] Have water nearby (you'll be talking!)

---

**Demo Status**: Ready for delivery
**Last Tested**: [Date]
**Success Rate**: [After practice runs]
**Recommended For**: First-time demos, introductory presentations, executive briefings
