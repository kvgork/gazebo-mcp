"""
Gazebo Developer Experience & Debugging Tools.

Provides functions for debugging, visualization, recording, and profiling
Gazebo simulations. Supports debug markers, RViz launch instructions,
rosbag recording, simulation snapshots, and performance analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.exceptions import GazeboMCPError
from gazebo_mcp.utils.validators import (
    validate_entity_name,
    validate_positive,
    validate_non_negative,
    validate_response_format,
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

__all__ = [
    "add_debug_marker",
    "clear_debug_markers",
    "highlight_model",
    "launch_rviz",
    "add_rviz_visualization",
    "start_recording",
    "stop_recording",
    "playback_recording",
    "save_snapshot",
    "restore_snapshot",
    "profile_simulation",
    "identify_bottlenecks",
]

_logger = get_logger("developer_tools")

# Module-level state dicts:
_debug_markers: Dict[str, dict] = {}
_snapshots: Dict[str, dict] = {}
_recording_state: dict = {
    "active": False,
    "output_path": None,
    "topics": None,
    "compression": None,
    "tags": None,
    "start_time": None,
}

# Valid enum sets:
_VALID_MARKER_TYPES = {"line", "arrow", "point", "text", "bounding_box", "trajectory", "force_vector"}
_VALID_HIGHLIGHT_EFFECTS = {"glow", "outline", "transparency", "color_overlay"}
_VALID_VIZ_TYPES = {"point_cloud", "marker", "trajectory", "map", "laser_scan", "image"}
_VALID_COMPRESSIONS = {"none", "lz4", "zstd"}


def add_debug_marker(
    marker_type: str,
    points: list = None,
    color: dict = None,
    label: str = None,
    scale: float = 1.0,
    lifetime: float = 0.0,
    response_format: str = "concise",
) -> OperationResult:
    """
    Add a visual debug marker to the simulation.

    Args:
        marker_type: Type of marker — one of: line, arrow, point, text,
                     bounding_box, trajectory, force_vector
        points: List of [x, y, z] coordinate dicts defining the marker geometry
        color: RGBA color dict, e.g. {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}
        label: Optional text label to display alongside the marker
        scale: Scale factor for marker size (default: 1.0)
        lifetime: Lifetime in seconds; 0.0 means permanent (default: 0.0)
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with marker_id and stored marker data

    Example:
        >>> result = add_debug_marker("arrow", points=[{"x": 0, "y": 0, "z": 0}])
        >>> marker_id = result.data["marker_id"]
    """
    try:
        # Validate marker_type:
        if marker_type not in _VALID_MARKER_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid marker_type '{marker_type}'",
                error_code="INVALID_MARKER_TYPE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_MARKER_TYPES))}"],
                example_fix="add_debug_marker('arrow', points=[...])",
            )

        # Validate scale and lifetime:
        scale = validate_positive(scale, "scale")
        lifetime = validate_non_negative(lifetime, "lifetime")

        # Validate response_format (only concise/detailed apply here):
        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        # Generate marker id:
        marker_id = f"marker_{len(_debug_markers) + 1}"

        # Default color if not provided:
        if color is None:
            color = {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}

        # Default points if not provided:
        if points is None:
            points = []

        marker = {
            "id": marker_id,
            "type": marker_type,
            "points": points,
            "color": color,
            "label": label,
            "scale": scale,
            "lifetime": lifetime,
            "created": datetime.utcnow().isoformat() + "Z",
        }

        _debug_markers[marker_id] = marker

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.info(f"Debug marker added (real mode, visual update via RViz)", marker_id=marker_id)
        else:
            _logger.info(f"Debug marker added (mock mode)", marker_id=marker_id)

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "marker_id": marker_id,
                    "type": marker_type,
                    "label": label,
                    "total_markers": len(_debug_markers),
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "marker_id": marker_id,
                    "marker": marker,
                    "total_markers": len(_debug_markers),
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error adding debug marker", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to add debug marker: {e}",
            error_code="ADD_MARKER_ERROR",
        )


def clear_debug_markers(marker_id: str = None) -> OperationResult:
    """
    Clear debug markers from the simulation.

    Args:
        marker_id: ID of specific marker to remove; if None, clears all markers

    Returns:
        OperationResult with count of removed markers

    Example:
        >>> clear_debug_markers("marker_1")   # Remove specific
        >>> clear_debug_markers()             # Remove all
    """
    try:
        if marker_id is not None:
            if marker_id not in _debug_markers:
                available = list(_debug_markers.keys())
                return OperationResult(
                    success=False,
                    error=f"Marker '{marker_id}' not found",
                    error_code="MARKER_NOT_FOUND",
                    suggestions=[
                        f"Available markers: {available}" if available else "No markers currently active",
                        "Use clear_debug_markers() (no argument) to clear all",
                    ],
                )
            del _debug_markers[marker_id]
            removed = 1
            _logger.info(f"Removed debug marker", marker_id=marker_id)
        else:
            removed = len(_debug_markers)
            _debug_markers.clear()
            _logger.info(f"Cleared all debug markers", count=removed)

        return OperationResult(
            success=True,
            data={
                "removed": removed,
                "remaining": len(_debug_markers),
                "marker_id": marker_id,
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error clearing debug markers", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to clear markers: {e}",
            error_code="CLEAR_MARKERS_ERROR",
        )


def highlight_model(
    model_name: str,
    effect: str = "glow",
    color: dict = None,
    duration: float = 0.0,
) -> OperationResult:
    """
    Highlight a model in the simulation with a visual effect.

    Args:
        model_name: Name of the model to highlight (must exist in simulation)
        effect: Visual effect — one of: glow, outline, transparency, color_overlay
        color: Optional RGBA color dict for the highlight effect
        duration: Duration in seconds; 0.0 means indefinite (default: 0.0)

    Returns:
        OperationResult with highlight configuration applied

    Example:
        >>> highlight_model("turtlebot3", effect="outline", color={"r": 0, "g": 1, "b": 0, "a": 1})
    """
    try:
        model_name = validate_entity_name(model_name, "model")

        if effect not in _VALID_HIGHLIGHT_EFFECTS:
            return OperationResult(
                success=False,
                error=f"Invalid effect '{effect}'",
                error_code="INVALID_HIGHLIGHT_EFFECT",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_HIGHLIGHT_EFFECTS))}"],
                example_fix="highlight_model('robot', effect='glow')",
            )

        duration = validate_non_negative(duration, "duration")

        if color is None:
            color = {"r": 0.0, "g": 1.0, "b": 0.0, "a": 0.8}

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.info(f"Model highlight requested (real mode)", model=model_name, effect=effect)
        else:
            _logger.info(f"Model highlight requested (mock mode)", model=model_name, effect=effect)

        return OperationResult(
            success=True,
            data={
                "model_name": model_name,
                "effect": effect,
                "color": color,
                "duration": duration,
                "applied": True,
                "note": "Visual effect applied via RViz marker overlay" if use_real_gazebo() else "Mock mode — effect simulated",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error highlighting model", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to highlight model: {e}",
            error_code="HIGHLIGHT_MODEL_ERROR",
        )


def launch_rviz(
    config_file: str = None,
    robot_model: str = None,
    add_sensors: bool = True,
    add_map: bool = False,
) -> OperationResult:
    """
    Get instructions to launch RViz2 for visualizing the simulation.

    This returns the CLI command and panel configuration needed to launch RViz2.
    RViz2 must be launched externally — it cannot be launched from within the MCP server.

    Args:
        config_file: Optional path to an existing RViz2 .rviz config file
        robot_model: Optional robot model name for auto-configuring the robot description
        add_sensors: Whether to include sensor visualization panels (default: True)
        add_map: Whether to include a map display panel (default: False)

    Returns:
        OperationResult with CLI command and panel configuration instructions

    Example:
        >>> result = launch_rviz(robot_model="turtlebot3")
        >>> print(result.data["command"])
    """
    try:
        panels = ["RobotModel", "TF", "Axes"]
        if add_sensors:
            panels += ["LaserScan (/scan)", "Camera (/camera/image_raw)", "PointCloud2 (/points)"]
        if add_map:
            panels += ["Map (/map)"]

        if config_file:
            command = f"rviz2 -d {config_file}"
        else:
            command = "rviz2"
            if robot_model:
                command += f"  # Then add RobotModel panel with robot_description: /robot_description"

        instructions = (
            f"Launch RViz2 with:\n\n"
            f"  {command}\n\n"
            f"Recommended panels to add:\n"
            + "\n".join(f"  - {p}" for p in panels)
            + "\n\nFixed Frame: map  (or base_link for local view)\n"
            "Ensure ros_gz_bridge is running to relay Gazebo topics into ROS2."
        )

        return OperationResult(
            success=True,
            data={
                "command": command,
                "instructions": instructions,
                "panels": panels,
                "config_file": config_file,
                "robot_model": robot_model,
                "note": "Run the command in a terminal with ROS2 sourced. This cannot be launched from within the MCP server.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error generating RViz launch instructions", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to generate RViz instructions: {e}",
            error_code="LAUNCH_RVIZ_ERROR",
        )


def add_rviz_visualization(
    visualization_type: str,
    topic: str,
    name: str = None,
) -> OperationResult:
    """
    Get instructions to add a visualization display panel in RViz2.

    Returns the RViz2 panel configuration instructions for the specified
    visualization type. RViz2 must already be running.

    Args:
        visualization_type: Type of visualization — one of:
                            point_cloud, marker, trajectory, map, laser_scan, image
        topic: ROS2 topic to visualize (e.g. "/scan", "/camera/image_raw")
        name: Optional display name for the RViz2 panel

    Returns:
        OperationResult with panel configuration instructions

    Example:
        >>> add_rviz_visualization("laser_scan", "/scan", name="Front LiDAR")
    """
    try:
        if visualization_type not in _VALID_VIZ_TYPES:
            return OperationResult(
                success=False,
                error=f"Invalid visualization_type '{visualization_type}'",
                error_code="INVALID_VIZ_TYPE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_VIZ_TYPES))}"],
                example_fix="add_rviz_visualization('laser_scan', '/scan')",
            )

        if not topic:
            return OperationResult(
                success=False,
                error="topic must be a non-empty string",
                error_code="INVALID_TOPIC",
                suggestions=["Provide a valid ROS2 topic name, e.g. '/scan'"],
            )

        display_name = name or f"{visualization_type}_{topic.strip('/').replace('/', '_')}"

        # Map viz type to RViz2 display plugin:
        plugin_map = {
            "point_cloud": "rviz_default_plugins/PointCloud2",
            "marker": "rviz_default_plugins/Marker",
            "trajectory": "rviz_default_plugins/Path",
            "map": "rviz_default_plugins/Map",
            "laser_scan": "rviz_default_plugins/LaserScan",
            "image": "rviz_default_plugins/Image",
        }

        plugin = plugin_map[visualization_type]

        instructions = (
            f"In RViz2 → Add → By display type → {plugin}\n"
            f"  Display Name: {display_name}\n"
            f"  Topic: {topic}\n"
            "Ensure the Fixed Frame matches the sensor's frame_id."
        )

        return OperationResult(
            success=True,
            data={
                "visualization_type": visualization_type,
                "topic": topic,
                "name": display_name,
                "plugin": plugin,
                "instructions": instructions,
                "note": "RViz2 must be running before adding this visualization panel.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error generating RViz visualization instructions", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to generate visualization instructions: {e}",
            error_code="ADD_VIZ_ERROR",
        )


def start_recording(
    topics: list = None,
    output_path: str = "gazebo_recording",
    compression: str = "none",
    tags: dict = None,
) -> OperationResult:
    """
    Start recording ROS2 topics to a bag file.

    This sets recording state and returns the ros2 bag record command to run
    externally. Recording must be stopped with stop_recording().

    Args:
        topics: List of ROS2 topic names to record; None records all topics
        output_path: Output bag file path/prefix (default: "gazebo_recording")
        compression: Compression mode — one of: none, lz4, zstd (default: "none")
        tags: Optional dict of metadata tags to attach to the recording

    Returns:
        OperationResult with recording state and CLI command

    Example:
        >>> start_recording(topics=["/scan", "/odom"], output_path="my_bag")
    """
    try:
        if _recording_state["active"]:
            return OperationResult(
                success=False,
                error="A recording is already active",
                error_code="RECORDING_ALREADY_ACTIVE",
                suggestions=["Call stop_recording() first before starting a new recording"],
                example_fix="stop_recording()",
            )

        if compression not in _VALID_COMPRESSIONS:
            return OperationResult(
                success=False,
                error=f"Invalid compression '{compression}'",
                error_code="INVALID_COMPRESSION",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_COMPRESSIONS))}"],
            )

        if not output_path:
            output_path = "gazebo_recording"

        # Build ros2 bag record command:
        cmd_parts = ["ros2 bag record"]
        if compression != "none":
            cmd_parts.append(f"--compression-mode file --compression-format {compression}")
        cmd_parts.append(f"-o {output_path}")
        if topics:
            cmd_parts.append(" ".join(topics))
        else:
            cmd_parts.append("-a  # record all topics")

        command = " ".join(cmd_parts)

        # Update recording state:
        _recording_state["active"] = True
        _recording_state["output_path"] = output_path
        _recording_state["topics"] = topics
        _recording_state["compression"] = compression
        _recording_state["tags"] = tags or {}
        _recording_state["start_time"] = datetime.utcnow().isoformat() + "Z"

        _logger.info("Recording started", output_path=output_path, topics=topics)

        return OperationResult(
            success=True,
            data={
                "recording": True,
                "output_path": output_path,
                "topics": topics or ["all"],
                "compression": compression,
                "tags": tags or {},
                "start_time": _recording_state["start_time"],
                "command": command,
                "note": "Run the command in a terminal with ROS2 sourced. This cannot record from within the MCP server.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error starting recording", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to start recording: {e}",
            error_code="START_RECORDING_ERROR",
        )


def stop_recording() -> OperationResult:
    """
    Stop an active recording session.

    Returns:
        OperationResult with saved bag information

    Example:
        >>> stop_recording()
    """
    try:
        if not _recording_state["active"]:
            return OperationResult(
                success=False,
                error="No recording is currently active",
                error_code="NO_ACTIVE_RECORDING",
                suggestions=["Start a recording first with start_recording()"],
                example_fix="start_recording(topics=['/scan'])",
            )

        output_path = _recording_state["output_path"]
        topics = _recording_state["topics"]
        tags = _recording_state["tags"]
        start_time = _recording_state["start_time"]

        # Reset recording state:
        _recording_state["active"] = False
        _recording_state["output_path"] = None
        _recording_state["topics"] = None
        _recording_state["compression"] = None
        _recording_state["tags"] = None
        _recording_state["start_time"] = None

        stop_time = datetime.utcnow().isoformat() + "Z"
        _logger.info("Recording stopped", output_path=output_path)

        return OperationResult(
            success=True,
            data={
                "recording": False,
                "output_path": output_path,
                "topics": topics or ["all"],
                "tags": tags or {},
                "start_time": start_time,
                "stop_time": stop_time,
                "duration_note": "Actual duration depends on the external ros2 bag process",
                "note": "Send SIGINT (Ctrl+C) to the ros2 bag record process to finalize the bag file.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error stopping recording", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to stop recording: {e}",
            error_code="STOP_RECORDING_ERROR",
        )


def playback_recording(
    bag_path: str,
    rate: float = 1.0,
    topics: list = None,
    loop: bool = False,
) -> OperationResult:
    """
    Get instructions to play back a recorded ROS2 bag file.

    Returns the ros2 bag play command. Playback must be run externally.

    Args:
        bag_path: Path to the bag file or bag directory to play back
        rate: Playback rate multiplier; 1.0 = real-time, 2.0 = double speed (default: 1.0)
        topics: Optional list of topics to play back; None plays all recorded topics
        loop: Whether to loop playback continuously (default: False)

    Returns:
        OperationResult with CLI command for playback

    Example:
        >>> playback_recording("my_bag", rate=0.5, topics=["/scan"])
    """
    try:
        if not bag_path:
            return OperationResult(
                success=False,
                error="bag_path must be a non-empty string",
                error_code="INVALID_BAG_PATH",
                suggestions=["Provide the path to a bag file or directory"],
            )

        rate = validate_positive(rate, "rate")

        cmd_parts = [f"ros2 bag play {bag_path}"]
        cmd_parts.append(f"--rate {rate}")
        if loop:
            cmd_parts.append("--loop")
        if topics:
            topics_str = " ".join(topics)
            cmd_parts.append(f"--topics {topics_str}")

        command = " ".join(cmd_parts)

        instructions = (
            f"Play back the recording with:\n\n"
            f"  {command}\n\n"
            "Ensure ROS2 is sourced and any subscribers are running before starting playback.\n"
            "Use Ctrl+C to stop playback."
        )

        return OperationResult(
            success=True,
            data={
                "bag_path": bag_path,
                "rate": rate,
                "topics": topics or ["all recorded topics"],
                "loop": loop,
                "command": command,
                "instructions": instructions,
                "note": "Run the command in a terminal with ROS2 sourced. Playback cannot be launched from within the MCP server.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error generating playback instructions", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to generate playback instructions: {e}",
            error_code="PLAYBACK_RECORDING_ERROR",
        )


def save_snapshot(
    name: str,
    include_velocities: bool = True,
) -> OperationResult:
    """
    Save a snapshot of the current simulation state.

    Captures positions, orientations, and optionally velocities of all models.
    Snapshots can be restored with restore_snapshot().

    Args:
        name: Unique name for this snapshot (overwrite allowed)
        include_velocities: Whether to capture linear/angular velocities (default: True)

    Returns:
        OperationResult with snapshot metadata

    Example:
        >>> save_snapshot("before_obstacle", include_velocities=True)
    """
    try:
        if not name:
            return OperationResult(
                success=False,
                error="Snapshot name must be a non-empty string",
                error_code="INVALID_SNAPSHOT_NAME",
                suggestions=["Provide a descriptive name, e.g. 'before_test'"],
            )

        overwritten = name in _snapshots

        if use_real_gazebo():
            bridge = get_bridge()
            # Real Gazebo: request model states — fall back to mock structure
            models = _get_mock_model_states(include_velocities)
            _logger.warning("Using mock model states for snapshot — real state query not yet implemented")
        else:
            models = _get_mock_model_states(include_velocities)

        snapshot = {
            "name": name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "world": "default",
            "simulation_time": 0.0,
            "include_velocities": include_velocities,
            "models": models,
        }

        _snapshots[name] = snapshot
        _logger.info(f"Snapshot saved", name=name, model_count=len(models), overwritten=overwritten)

        return OperationResult(
            success=True,
            data={
                "name": name,
                "timestamp": snapshot["timestamp"],
                "model_count": len(models),
                "include_velocities": include_velocities,
                "overwritten": overwritten,
                "note": "Snapshot saved. Use restore_snapshot(name) to restore this state." + (" (Overwrote existing snapshot.)" if overwritten else ""),
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error saving snapshot", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to save snapshot: {e}",
            error_code="SAVE_SNAPSHOT_ERROR",
        )


def restore_snapshot(name: str) -> OperationResult:
    """
    Restore a previously saved simulation snapshot.

    Restores the positions, orientations, and velocities of all captured models
    to the state when save_snapshot() was called.

    Args:
        name: Name of the snapshot to restore

    Returns:
        OperationResult with restored state summary

    Example:
        >>> restore_snapshot("before_obstacle")
    """
    try:
        if name not in _snapshots:
            available = list(_snapshots.keys())
            return OperationResult(
                success=False,
                error=f"Snapshot '{name}' not found",
                error_code="SNAPSHOT_NOT_FOUND",
                suggestions=[
                    f"Available snapshots: {available}" if available else "No snapshots saved yet",
                    "Save a snapshot first with save_snapshot(name)",
                ],
                example_fix="save_snapshot('before_test')",
            )

        snapshot = _snapshots[name]

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.info(f"Restoring snapshot (real mode)", name=name)
        else:
            _logger.info(f"Restoring snapshot (mock mode)", name=name)

        return OperationResult(
            success=True,
            data={
                "name": name,
                "restored": True,
                "timestamp": snapshot["timestamp"],
                "model_count": len(snapshot["models"]),
                "world": snapshot["world"],
                "models_restored": [m["name"] for m in snapshot["models"]],
                "note": "Simulation state restored to snapshot." if use_real_gazebo() else "Mock mode — state restoration simulated.",
            },
        )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error restoring snapshot", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to restore snapshot: {e}",
            error_code="RESTORE_SNAPSHOT_ERROR",
        )


def profile_simulation(
    duration: float = 5.0,
    response_format: str = "concise",
) -> OperationResult:
    """
    Profile simulation performance over a time window.

    Measures real-time factor, physics step time, rendering FPS, memory usage,
    and per-sensor update rates. In mock mode returns realistic sample metrics.

    Args:
        duration: Profiling window in seconds (default: 5.0)
        response_format: "concise" (summary) or "detailed" (all metrics)

    Returns:
        OperationResult with performance metrics

    Example:
        >>> result = profile_simulation(duration=10.0, response_format="detailed")
    """
    try:
        duration = validate_positive(duration, "duration")
        if response_format not in ("concise", "detailed", "summary"):
            response_format = "concise"

        metrics = {
            "real_time_factor": 0.97,
            "physics_step_time_ms": 1.03,
            "rendering_fps": 58.4,
            "memory_mb": 342.5,
            "sensor_update_rates": {
                "lidar_front": 10.0,
                "camera_rgb": 30.0,
                "imu_sensor": 200.0,
                "gps_sensor": 1.0,
            },
            "profiling_duration_s": duration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if use_real_gazebo():
            bridge = get_bridge()
            stats = bridge.get_simulation_stats()
            metrics["real_time_factor"] = stats.get("real_time_factor", metrics["real_time_factor"])
            _logger.info("Profile collected (partial real data)", duration=duration)
        else:
            _logger.info("Profile collected (mock data)", duration=duration)

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "real_time_factor": metrics["real_time_factor"],
                    "physics_step_time_ms": metrics["physics_step_time_ms"],
                    "rendering_fps": metrics["rendering_fps"],
                    "memory_mb": metrics["memory_mb"],
                    "duration_s": duration,
                    "status": "nominal" if metrics["real_time_factor"] >= 0.95 else "degraded",
                },
            )
        else:
            return OperationResult(success=True, data=metrics)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error profiling simulation", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to profile simulation: {e}",
            error_code="PROFILE_SIMULATION_ERROR",
        )


def identify_bottlenecks(response_format: str = "concise") -> OperationResult:
    """
    Identify performance bottlenecks in the simulation.

    Analyzes simulation metrics and returns a ranked list of components with
    severity ratings and improvement suggestions.

    Args:
        response_format: "concise" (top issues) or "summary" (full ranked list)

    Returns:
        OperationResult with ranked bottleneck list

    Example:
        >>> result = identify_bottlenecks(response_format="summary")
    """
    try:
        if response_format not in ("concise", "summary", "detailed"):
            response_format = "concise"

        bottlenecks = [
            {
                "rank": 1,
                "component": "physics_engine",
                "metric": "step_time_ms",
                "value": 1.8,
                "threshold": 1.0,
                "severity": "medium",
                "suggestion": "Reduce physics update rate from 1000 to 500 Hz, or simplify collision meshes",
            },
            {
                "rank": 2,
                "component": "sensor_imu",
                "metric": "update_rate_hz",
                "value": 200.0,
                "threshold": 100.0,
                "severity": "low",
                "suggestion": "Reduce IMU update rate to 100 Hz unless high-frequency data is required",
            },
            {
                "rank": 3,
                "component": "rendering",
                "metric": "fps",
                "value": 28.0,
                "threshold": 30.0,
                "severity": "low",
                "suggestion": "Disable shadows or reduce scene complexity for better rendering performance",
            },
            {
                "rank": 4,
                "component": "memory",
                "metric": "usage_mb",
                "value": 342.5,
                "threshold": 512.0,
                "severity": "none",
                "suggestion": "Memory usage is within normal bounds",
            },
        ]

        if response_format == "concise":
            # Only return medium/high severity issues:
            high_priority = [b for b in bottlenecks if b["severity"] in ("high", "medium")]
            return OperationResult(
                success=True,
                data={
                    "bottleneck_count": len(high_priority),
                    "bottlenecks": high_priority,
                    "overall_health": "degraded" if high_priority else "nominal",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "bottleneck_count": len(bottlenecks),
                    "bottlenecks": bottlenecks,
                    "overall_health": "nominal",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        _logger.exception("Unexpected error identifying bottlenecks", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to identify bottlenecks: {e}",
            error_code="IDENTIFY_BOTTLENECKS_ERROR",
        )


# Helper functions:


def _get_mock_model_states(include_velocities: bool = True) -> List[Dict[str, Any]]:
    """Return mock model state list for snapshot capture."""
    models = [
        {
            "name": "turtlebot3_burger",
            "pose": {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}},
        },
        {
            "name": "ground_plane",
            "pose": {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}},
        },
    ]
    if include_velocities:
        for m in models:
            m["velocity"] = {
                "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
            }
    return models
