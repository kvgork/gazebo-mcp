"""
Developer Tools MCP Adapter.

Exposes Gazebo developer experience and debugging tools as MCP tools:
- add_debug_marker: Add visual debug markers to the simulation
- clear_debug_markers: Remove debug markers
- highlight_model: Apply visual highlight effects to models
- launch_rviz: Get instructions to launch RViz2
- add_rviz_visualization: Get instructions to add RViz2 visualization panels
- start_recording: Start recording ROS2 topics to a bag file
- stop_recording: Stop an active recording
- playback_recording: Get instructions to play back a recording
- save_snapshot: Save simulation state snapshot
- restore_snapshot: Restore a saved snapshot
- profile_simulation: Profile simulation performance
- identify_bottlenecks: Identify simulation performance bottlenecks
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import developer_tools
from gz_mcp_server.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for developer experience and debugging operations."""
    return [
        MCPTool(
            name="gazebo_add_debug_marker",
            description=(
                "Add a visual debug marker to the Gazebo simulation.\n\n"
                "Supported marker types: line, arrow, point, text, bounding_box, trajectory, force_vector.\n\n"
                "Args:\n"
                "  marker_type: Type of marker to add (required)\n"
                "  points: List of {x, y, z} coordinate dicts defining geometry (optional)\n"
                "  color: RGBA color dict, e.g. {r: 1.0, g: 0.0, b: 0.0, a: 1.0} (optional)\n"
                "  label: Text label to display alongside the marker (optional)\n"
                "  scale: Scale factor for marker size, default 1.0 (optional)\n"
                "  lifetime: Lifetime in seconds; 0.0 = permanent (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Add arrow: gazebo_add_debug_marker(marker_type='arrow', points=[{x:0,y:0,z:0}])\n"
                "- Add text label: gazebo_add_debug_marker(marker_type='text', label='Goal', scale=2.0)\n"
                "- Add bounding box: gazebo_add_debug_marker(marker_type='bounding_box', color={r:0,g:1,b:0,a:0.5})"
            ),
            parameters={
                "properties": {
                    "marker_type": {
                        "type": "string",
                        "description": "Type of marker to add",
                        "enum": ["line", "arrow", "point", "text", "bounding_box", "trajectory", "force_vector"],
                    },
                    "points": {
                        "type": "array",
                        "description": "List of {x, y, z} coordinate dicts defining marker geometry",
                        "items": {"type": "object"},
                    },
                    "color": {
                        "type": "object",
                        "description": "RGBA color dict, e.g. {r: 1.0, g: 0.0, b: 0.0, a: 1.0}",
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional text label to display alongside the marker",
                    },
                    "scale": {
                        "type": "number",
                        "description": "Scale factor for marker size (default: 1.0)",
                        "default": 1.0,
                        "minimum": 0.001,
                    },
                    "lifetime": {
                        "type": "number",
                        "description": "Lifetime in seconds; 0.0 = permanent (default: 0.0)",
                        "default": 0.0,
                        "minimum": 0.0,
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["marker_type"],
            },
            handler=developer_tools.add_debug_marker,
        ),
        MCPTool(
            name="gazebo_clear_debug_markers",
            description=(
                "Remove debug markers from the simulation.\n\n"
                "If marker_id is provided, removes only that marker.\n"
                "If omitted, clears all active debug markers.\n\n"
                "Args:\n"
                "  marker_id: ID of specific marker to remove (optional)\n\n"
                "Examples:\n"
                "- Remove one: gazebo_clear_debug_markers(marker_id='marker_1')\n"
                "- Remove all: gazebo_clear_debug_markers()"
            ),
            parameters={
                "properties": {
                    "marker_id": {
                        "type": "string",
                        "description": "ID of specific marker to remove; omit to clear all",
                    },
                },
                "required": [],
            },
            handler=developer_tools.clear_debug_markers,
        ),
        MCPTool(
            name="gazebo_highlight_model",
            description=(
                "Apply a visual highlight effect to a model in the simulation.\n\n"
                "Supported effects: glow, outline, transparency, color_overlay.\n\n"
                "Args:\n"
                "  model_name: Name of the model to highlight (required)\n"
                "  effect: Visual effect type (default: 'glow')\n"
                "  color: RGBA color dict for the highlight (optional)\n"
                "  duration: Duration in seconds; 0.0 = indefinite (optional)\n\n"
                "Examples:\n"
                "- Glow: gazebo_highlight_model(model_name='turtlebot3', effect='glow')\n"
                "- Outline: gazebo_highlight_model(model_name='robot1', effect='outline', color={r:0,g:1,b:0,a:1})\n"
                "- Transparent: gazebo_highlight_model(model_name='obstacle', effect='transparency', duration=5.0)"
            ),
            parameters={
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of the model to highlight",
                    },
                    "effect": {
                        "type": "string",
                        "description": "Visual effect to apply (default: glow)",
                        "enum": ["glow", "outline", "transparency", "color_overlay"],
                        "default": "glow",
                    },
                    "color": {
                        "type": "object",
                        "description": "RGBA color dict for the highlight effect",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration in seconds; 0.0 = indefinite (default: 0.0)",
                        "default": 0.0,
                        "minimum": 0.0,
                    },
                },
                "required": ["model_name"],
            },
            handler=developer_tools.highlight_model,
        ),
        MCPTool(
            name="gazebo_launch_rviz",
            description=(
                "Get instructions and CLI command to launch RViz2 for visualizing the simulation.\n\n"
                "RViz2 must be launched externally in a terminal with ROS2 sourced.\n"
                "Returns the rviz2 command and recommended panel configuration.\n\n"
                "Args:\n"
                "  config_file: Path to existing .rviz config file (optional)\n"
                "  robot_model: Robot model name for auto-configuration (optional)\n"
                "  add_sensors: Include sensor visualization panels (default: True)\n"
                "  add_map: Include map display panel (default: False)\n\n"
                "Examples:\n"
                "- Basic launch: gazebo_launch_rviz()\n"
                "- With config: gazebo_launch_rviz(config_file='/path/to/config.rviz')\n"
                "- With robot: gazebo_launch_rviz(robot_model='turtlebot3', add_map=True)"
            ),
            parameters={
                "properties": {
                    "config_file": {
                        "type": "string",
                        "description": "Path to an existing RViz2 .rviz configuration file (optional)",
                    },
                    "robot_model": {
                        "type": "string",
                        "description": "Robot model name for panel auto-configuration (optional)",
                    },
                    "add_sensors": {
                        "type": "boolean",
                        "description": "Include sensor visualization panels (default: true)",
                        "default": True,
                    },
                    "add_map": {
                        "type": "boolean",
                        "description": "Include map display panel (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
            handler=developer_tools.launch_rviz,
        ),
        MCPTool(
            name="gazebo_add_rviz_visualization",
            description=(
                "Get instructions to add a visualization display panel in RViz2.\n\n"
                "Supported types: point_cloud, marker, trajectory, map, laser_scan, image.\n"
                "RViz2 must already be running.\n\n"
                "Args:\n"
                "  visualization_type: Type of visualization to add (required)\n"
                "  topic: ROS2 topic to visualize (required)\n"
                "  name: Optional display name for the panel (optional)\n\n"
                "Examples:\n"
                "- LiDAR: gazebo_add_rviz_visualization(visualization_type='laser_scan', topic='/scan')\n"
                "- Camera: gazebo_add_rviz_visualization(visualization_type='image', topic='/camera/image_raw')\n"
                "- Points: gazebo_add_rviz_visualization(visualization_type='point_cloud', topic='/points', name='LiDAR 3D')"
            ),
            parameters={
                "properties": {
                    "visualization_type": {
                        "type": "string",
                        "description": "Type of RViz2 visualization to add",
                        "enum": ["point_cloud", "marker", "trajectory", "map", "laser_scan", "image"],
                    },
                    "topic": {
                        "type": "string",
                        "description": "ROS2 topic to visualize (e.g. '/scan', '/camera/image_raw')",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional display name for the RViz2 panel",
                    },
                },
                "required": ["visualization_type", "topic"],
            },
            handler=developer_tools.add_rviz_visualization,
        ),
        MCPTool(
            name="gazebo_start_recording",
            description=(
                "Start recording ROS2 topics to a bag file.\n\n"
                "Sets recording state and returns the ros2 bag record command to run externally.\n"
                "Stop recording with gazebo_stop_recording.\n\n"
                "Args:\n"
                "  topics: List of topic names to record; None records all (optional)\n"
                "  output_path: Output bag path/prefix (default: 'gazebo_recording')\n"
                "  compression: Compression — none, lz4, or zstd (default: 'none')\n"
                "  tags: Metadata tags dict (optional)\n\n"
                "Examples:\n"
                "- All topics: gazebo_start_recording()\n"
                "- Selected: gazebo_start_recording(topics=['/scan', '/odom'], output_path='my_run')\n"
                "- Compressed: gazebo_start_recording(compression='lz4', output_path='compressed_run')"
            ),
            parameters={
                "properties": {
                    "topics": {
                        "type": "array",
                        "description": "List of ROS2 topic names to record; omit to record all",
                        "items": {"type": "string"},
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output bag file path or prefix (default: 'gazebo_recording')",
                        "default": "gazebo_recording",
                    },
                    "compression": {
                        "type": "string",
                        "description": "Compression mode (default: 'none')",
                        "enum": ["none", "lz4", "zstd"],
                        "default": "none",
                    },
                    "tags": {
                        "type": "object",
                        "description": "Optional metadata tags dict to attach to the recording",
                    },
                },
                "required": [],
            },
            handler=developer_tools.start_recording,
        ),
        MCPTool(
            name="gazebo_stop_recording",
            description=(
                "Stop an active recording session.\n\n"
                "Returns saved bag information including path, topics, and timestamps.\n"
                "Errors if no recording is currently active.\n\n"
                "Examples:\n"
                "- gazebo_stop_recording()"
            ),
            parameters={
                "properties": {},
                "required": [],
            },
            handler=developer_tools.stop_recording,
        ),
        MCPTool(
            name="gazebo_playback_recording",
            description=(
                "Get instructions and CLI command to play back a recorded ROS2 bag file.\n\n"
                "Playback must be run externally in a terminal with ROS2 sourced.\n\n"
                "Args:\n"
                "  bag_path: Path to the bag file or directory (required)\n"
                "  rate: Playback rate multiplier; 1.0 = real-time (default: 1.0)\n"
                "  topics: List of topics to play back; None plays all (optional)\n"
                "  loop: Whether to loop playback continuously (default: False)\n\n"
                "Examples:\n"
                "- Normal speed: gazebo_playback_recording(bag_path='my_bag')\n"
                "- Half speed: gazebo_playback_recording(bag_path='my_bag', rate=0.5)\n"
                "- Loop: gazebo_playback_recording(bag_path='my_bag', loop=True, topics=['/scan'])"
            ),
            parameters={
                "properties": {
                    "bag_path": {
                        "type": "string",
                        "description": "Path to the bag file or bag directory to play back",
                    },
                    "rate": {
                        "type": "number",
                        "description": "Playback rate multiplier; 1.0 = real-time (default: 1.0)",
                        "default": 1.0,
                        "minimum": 0.001,
                    },
                    "topics": {
                        "type": "array",
                        "description": "List of topics to play back; omit for all recorded topics",
                        "items": {"type": "string"},
                    },
                    "loop": {
                        "type": "boolean",
                        "description": "Whether to loop playback continuously (default: false)",
                        "default": False,
                    },
                },
                "required": ["bag_path"],
            },
            handler=developer_tools.playback_recording,
        ),
        MCPTool(
            name="gazebo_save_snapshot",
            description=(
                "Save a snapshot of the current simulation state.\n\n"
                "Captures poses and optionally velocities of all models.\n"
                "Restore later with gazebo_restore_snapshot.\n\n"
                "Args:\n"
                "  name: Unique snapshot name (required, overwrite allowed)\n"
                "  include_velocities: Capture linear/angular velocities (default: True)\n\n"
                "Examples:\n"
                "- Basic: gazebo_save_snapshot(name='before_test')\n"
                "- With velocities: gazebo_save_snapshot(name='mid_run', include_velocities=True)"
            ),
            parameters={
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique name for this snapshot (overwrite allowed)",
                    },
                    "include_velocities": {
                        "type": "boolean",
                        "description": "Whether to capture linear/angular velocities (default: true)",
                        "default": True,
                    },
                },
                "required": ["name"],
            },
            handler=developer_tools.save_snapshot,
        ),
        MCPTool(
            name="gazebo_restore_snapshot",
            description=(
                "Restore a previously saved simulation snapshot.\n\n"
                "Restores the positions, orientations, and velocities of all captured models.\n"
                "Errors with SNAPSHOT_NOT_FOUND if the name does not exist.\n\n"
                "Args:\n"
                "  name: Name of the snapshot to restore (required)\n\n"
                "Examples:\n"
                "- Restore: gazebo_restore_snapshot(name='before_test')"
            ),
            parameters={
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the snapshot to restore",
                    },
                },
                "required": ["name"],
            },
            handler=developer_tools.restore_snapshot,
        ),
        MCPTool(
            name="gazebo_profile_simulation",
            description=(
                "Profile simulation performance over a time window.\n\n"
                "Measures real-time factor, physics step time, rendering FPS,\n"
                "memory usage, and per-sensor update rates.\n\n"
                "Args:\n"
                "  duration: Profiling window in seconds (default: 5.0)\n"
                "  response_format: 'concise' (summary) or 'detailed' (all metrics)\n\n"
                "Examples:\n"
                "- Quick check: gazebo_profile_simulation()\n"
                "- Full profile: gazebo_profile_simulation(duration=10.0, response_format='detailed')"
            ),
            parameters={
                "properties": {
                    "duration": {
                        "type": "number",
                        "description": "Profiling window in seconds (default: 5.0)",
                        "default": 5.0,
                        "minimum": 0.001,
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' (summary) or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=developer_tools.profile_simulation,
        ),
        MCPTool(
            name="gazebo_identify_bottlenecks",
            description=(
                "Identify performance bottlenecks in the simulation.\n\n"
                "Analyzes simulation metrics and returns a ranked list of components\n"
                "with severity ratings and improvement suggestions.\n\n"
                "Args:\n"
                "  response_format: 'concise' (high-priority only) or 'summary' (full list)\n\n"
                "Examples:\n"
                "- Top issues: gazebo_identify_bottlenecks()\n"
                "- Full list: gazebo_identify_bottlenecks(response_format='summary')"
            ),
            parameters={
                "properties": {
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' (medium+ severity) or 'summary' (all)",
                        "enum": ["concise", "summary"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=developer_tools.identify_bottlenecks,
        ),
    ]
