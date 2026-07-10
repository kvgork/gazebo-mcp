"""
Gazebo Navigation & Path Planning (Nav2) Tools.

Provides functions for initializing Nav2, sending and managing navigation
goals, planning paths, building occupancy maps and costmaps, following
waypoint missions, and planning coverage paths. All tools operate in a
deterministic mock mode so they are useful without a live Gazebo/Nav2 stack.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.exceptions import GazeboMCPError
from gazebo_mcp.utils.validators import (
    validate_entity_name,
    validate_positive,
    validate_non_negative,
    validate_response_format,
    validate_position,
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo

__all__ = [
    "initialize_nav2",
    "send_nav_goal",
    "cancel_nav_goal",
    "get_nav_status",
    "plan_path",
    "visualize_path",
    "create_occupancy_map",
    "update_costmap",
    "follow_waypoints",
    "plan_coverage_path",
]

_logger = get_logger("nav2_tools")

# Module-level state dicts:
_nav2_state: dict = {"active": False}
_nav_goals: Dict[str, dict] = {}
_paths: Dict[str, dict] = {}
_costmaps: dict = {}

# Valid enum sets:
_VALID_GOAL_PLANNERS = {"DWB", "TEB", "RPP", "MPPI"}
_VALID_PATH_PLANNERS = {"A*", "RRT", "RRT*", "DWB", "TEB"}
_VALID_COSTMAP_ACTIONS = {"inject", "clear", "inflate"}
_VALID_WAYPOINT_MODES = {"sequence", "loop", "patrol"}
_VALID_COVERAGE_ALGORITHMS = {"boustrophedon", "spiral", "energy_efficient"}


def _now() -> str:
    """Return a timezone-aware UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _coerce_response_format(response_format: str) -> str:
    """Coerce unknown response_format values to 'concise'."""
    if response_format not in ("concise", "detailed", "summary", "filtered"):
        return "concise"
    return response_format


def initialize_nav2(
    robot: str = None,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Initialize the Nav2 navigation stack.

    Activates the navigation lifecycle and reports the lifecycle nodes that
    would be brought up. In mock mode this simply flips the internal state to
    active and returns a deterministic node list.

    Args:
        robot: Optional robot/namespace name to initialize Nav2 for
        params: Optional dict of Nav2 parameter overrides
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with robot, status, and lifecycle_nodes

    Example:
        >>> initialize_nav2(robot="turtlebot3")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if robot is not None:
            robot = validate_entity_name(robot, "robot")

        lifecycle_nodes = [
            "controller_server",
            "planner_server",
            "behavior_server",
            "bt_navigator",
            "waypoint_follower",
            "smoother_server",
            "velocity_smoother",
        ]

        _nav2_state["active"] = True
        _nav2_state["robot"] = robot
        _nav2_state["params"] = params or {}
        _nav2_state["initialized_at"] = _now()

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real Nav2 bring-up not implemented; returning mock lifecycle state",
                robot=robot,
            )
        else:
            _logger.info("Nav2 initialized (mock mode)", robot=robot)

        data = {
            "robot": robot,
            "status": "active",
            "lifecycle_nodes": lifecycle_nodes,
        }
        if response_format == "detailed":
            data["params"] = params or {}
            data["initialized_at"] = _nav2_state["initialized_at"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error initializing Nav2", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the robot name and params, then retry"],
        )


def send_nav_goal(
    x: float,
    y: float,
    theta: float = 0.0,
    planner: str = "DWB",
    behavior_tree: str = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Send a navigation goal to the Nav2 stack.

    Args:
        x: Target X coordinate in the map frame
        y: Target Y coordinate in the map frame
        theta: Target yaw orientation in radians (default: 0.0)
        planner: Controller/planner plugin — one of: DWB, TEB, RPP, MPPI
        behavior_tree: Optional path to a custom behavior tree XML
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with goal_id, target, planner, status, and eta_s

    Example:
        >>> send_nav_goal(2.0, 3.0, theta=1.57, planner="TEB")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if planner not in _VALID_GOAL_PLANNERS:
            return OperationResult(
                success=False,
                error=f"Invalid planner '{planner}'",
                error_code="INVALID_PLANNER",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_GOAL_PLANNERS))}"],
                example_fix="send_nav_goal(1.0, 2.0, planner='DWB')",
            )

        # Validate x, y numeric (z fixed at 0 for ground navigation):
        x, y, _z = validate_position(x, y, 0.0)
        theta = float(theta)

        goal_id = f"goal_{len(_nav_goals) + 1}"
        distance = math.sqrt(x * x + y * y)
        eta_s = round(distance / 0.5, 2)  # assume 0.5 m/s nominal speed

        goal = {
            "goal_id": goal_id,
            "target": {"x": x, "y": y, "theta": theta},
            "planner": planner,
            "behavior_tree": behavior_tree,
            "status": "accepted",
            "eta_s": eta_s,
            "created": _now(),
        }
        _nav_goals[goal_id] = goal
        _nav2_state["active_goal"] = goal_id

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real Nav2 goal dispatch not implemented; returning mock acceptance",
                goal_id=goal_id,
            )
        else:
            _logger.info("Nav goal accepted (mock mode)", goal_id=goal_id)

        data = {
            "goal_id": goal_id,
            "target": {"x": x, "y": y, "theta": theta},
            "planner": planner,
            "status": "accepted",
            "eta_s": eta_s,
        }
        if response_format == "detailed":
            data["behavior_tree"] = behavior_tree
            data["distance_m"] = round(distance, 3)
            data["created"] = goal["created"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error sending nav goal", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check x, y, and planner, then retry"],
        )


def cancel_nav_goal(
    goal_id: str = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Cancel an active navigation goal.

    Args:
        goal_id: ID of the goal to cancel; if None, cancels the current goal
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with cancelled goal identifier and status

    Example:
        >>> cancel_nav_goal()              # Cancel current goal
        >>> cancel_nav_goal("goal_1")      # Cancel specific goal
    """
    try:
        response_format = _coerce_response_format(response_format)

        cancelled = goal_id if goal_id is not None else "current"

        if goal_id is not None and goal_id in _nav_goals:
            _nav_goals[goal_id]["status"] = "cancelled"

        if _nav2_state.get("active_goal") == goal_id or goal_id is None:
            _nav2_state["active_goal"] = None

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real Nav2 goal cancel not implemented; returning mock cancellation",
                goal_id=cancelled,
            )
        else:
            _logger.info("Nav goal cancelled (mock mode)", goal_id=cancelled)

        data = {
            "cancelled": cancelled,
            "status": "cancelled",
        }
        if response_format == "detailed":
            data["known_goal"] = goal_id in _nav_goals if goal_id is not None else False

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error cancelling nav goal", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Retry the cancellation"],
        )


def get_nav_status(response_format: str = "concise") -> OperationResult:
    """
    Get the current navigation status.

    Args:
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with active_goal, progress_pct, distance_remaining_m,
        and obstacles_detected

    Example:
        >>> get_nav_status()
    """
    try:
        response_format = _coerce_response_format(response_format)

        active_goal = _nav2_state.get("active_goal")

        if active_goal:
            progress_pct = 42.0
            distance_remaining_m = 3.5
            obstacles_detected = 1
        else:
            progress_pct = 0.0
            distance_remaining_m = 0.0
            obstacles_detected = 0

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real Nav2 status query not implemented; returning mock status"
            )
        else:
            _logger.info("Nav status queried (mock mode)", active_goal=active_goal)

        data = {
            "active_goal": active_goal,
            "progress_pct": progress_pct,
            "distance_remaining_m": distance_remaining_m,
            "obstacles_detected": obstacles_detected,
        }
        if response_format == "detailed":
            data["nav2_active"] = _nav2_state.get("active", False)
            data["total_goals"] = len(_nav_goals)
            data["timestamp"] = _now()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error getting nav status", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Retry the status query"],
        )


def plan_path(
    start: dict,
    goal: dict,
    planner: str = "A*",
    response_format: str = "concise",
) -> OperationResult:
    """
    Plan a path from a start pose to a goal pose.

    Args:
        start: Start position dict with at least 'x' and 'y' keys
        goal: Goal position dict with at least 'x' and 'y' keys
        planner: Global planner — one of: A*, RRT, RRT*, DWB, TEB
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with path_id, planner, waypoints, length_m, cost,
        and est_time_s

    Example:
        >>> plan_path({"x": 0, "y": 0}, {"x": 5, "y": 3}, planner="RRT*")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if planner not in _VALID_PATH_PLANNERS:
            return OperationResult(
                success=False,
                error=f"Invalid planner '{planner}'",
                error_code="INVALID_PLANNER",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_PATH_PLANNERS))}"],
                example_fix="plan_path({'x':0,'y':0}, {'x':5,'y':5}, planner='A*')",
            )

        if not isinstance(start, dict) or "x" not in start or "y" not in start:
            return OperationResult(
                success=False,
                error="start must be a dict with 'x' and 'y' keys",
                error_code="INVALID_START",
                suggestions=["Provide start={'x': 0.0, 'y': 0.0}"],
                example_fix="plan_path({'x':0,'y':0}, {'x':5,'y':5})",
            )
        if not isinstance(goal, dict) or "x" not in goal or "y" not in goal:
            return OperationResult(
                success=False,
                error="goal must be a dict with 'x' and 'y' keys",
                error_code="INVALID_GOAL",
                suggestions=["Provide goal={'x': 5.0, 'y': 3.0}"],
                example_fix="plan_path({'x':0,'y':0}, {'x':5,'y':5})",
            )

        sx, sy = float(start["x"]), float(start["y"])
        gx, gy = float(goal["x"]), float(goal["y"])

        # Build a deterministic straight-line waypoint set:
        num_segments = 4
        waypoints = []
        for i in range(num_segments + 1):
            frac = i / num_segments
            waypoints.append(
                {"x": round(sx + (gx - sx) * frac, 3), "y": round(sy + (gy - sy) * frac, 3)}
            )

        length_m = round(math.sqrt((gx - sx) ** 2 + (gy - sy) ** 2), 3)
        cost = round(length_m * 1.1, 3)
        est_time_s = round(length_m / 0.5, 2)

        path_id = f"path_{len(_paths) + 1}"
        path = {
            "path_id": path_id,
            "planner": planner,
            "start": {"x": sx, "y": sy},
            "goal": {"x": gx, "y": gy},
            "waypoints": waypoints,
            "length_m": length_m,
            "cost": cost,
            "est_time_s": est_time_s,
            "created": _now(),
        }
        _paths[path_id] = path

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real Nav2 path planning not implemented; returning mock path",
                path_id=path_id,
            )
        else:
            _logger.info("Path planned (mock mode)", path_id=path_id)

        data = {
            "path_id": path_id,
            "planner": planner,
            "waypoints": waypoints,
            "length_m": length_m,
            "cost": cost,
            "est_time_s": est_time_s,
        }
        if response_format == "detailed":
            data["start"] = {"x": sx, "y": sy}
            data["goal"] = {"x": gx, "y": gy}
            data["waypoint_count"] = len(waypoints)
            data["created"] = path["created"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error planning path", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check start/goal dicts and planner, then retry"],
        )


def visualize_path(
    path_id: str = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Get instructions and mock markers to visualize a planned path in RViz2.

    Args:
        path_id: ID of a previously planned path; if None, visualizes the most
                 recently planned path
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with path_id and markers

    Example:
        >>> visualize_path("path_1")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if path_id is None:
            if not _paths:
                return OperationResult(
                    success=False,
                    error="No paths have been planned yet",
                    error_code="PATH_NOT_FOUND",
                    suggestions=["Plan a path first with plan_path(start, goal)"],
                    example_fix="plan_path({'x':0,'y':0}, {'x':5,'y':5})",
                )
            path_id = list(_paths.keys())[-1]

        if path_id not in _paths:
            available = list(_paths.keys())
            return OperationResult(
                success=False,
                error=f"Path '{path_id}' not found",
                error_code="PATH_NOT_FOUND",
                suggestions=[
                    f"Available paths: {available}" if available else "No paths planned yet",
                    "Plan a path first with plan_path(start, goal)",
                ],
                example_fix="plan_path({'x':0,'y':0}, {'x':5,'y':5})",
            )

        path = _paths[path_id]
        waypoints = path["waypoints"]

        markers = {
            "line_strip": {
                "ns": "nav2_path",
                "color": {"r": 0.0, "g": 0.8, "b": 1.0, "a": 1.0},
                "points": waypoints,
            },
            "start_marker": {"type": "sphere", "position": waypoints[0] if waypoints else None},
            "goal_marker": {"type": "sphere", "position": waypoints[-1] if waypoints else None},
            "topic": "/plan_markers",
        }

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real path marker publishing not implemented; returning mock markers",
                path_id=path_id,
            )
        else:
            _logger.info("Path visualization prepared (mock mode)", path_id=path_id)

        data = {
            "path_id": path_id,
            "markers": markers,
            "instructions": (
                f"Add a Path display in RViz2 on topic /plan and a MarkerArray "
                f"display on {markers['topic']} to view path '{path_id}'."
            ),
        }
        if response_format == "detailed":
            data["waypoint_count"] = len(waypoints)
            data["length_m"] = path["length_m"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error visualizing path", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the path_id and retry"],
        )


def create_occupancy_map(
    resolution: float = 0.05,
    world: str = "default",
    response_format: str = "concise",
) -> OperationResult:
    """
    Create an occupancy grid map of the simulation world.

    Args:
        resolution: Map resolution in meters/cell; must be > 0 (default: 0.05)
        world: Name of the world to map (default: "default")
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with resolution, width, height, origin, and
        occupancy_summary

    Example:
        >>> create_occupancy_map(resolution=0.1, world="warehouse")
    """
    try:
        response_format = _coerce_response_format(response_format)

        resolution = validate_positive(resolution, "resolution")

        # Deterministic mock map: 20m x 20m area.
        area_m = 20.0
        width = int(area_m / resolution)
        height = int(area_m / resolution)
        total_cells = width * height

        occupied = int(total_cells * 0.08)
        unknown = int(total_cells * 0.12)
        free = total_cells - occupied - unknown

        origin = {"x": -area_m / 2.0, "y": -area_m / 2.0, "theta": 0.0}

        _costmaps["occupancy_map"] = {
            "resolution": resolution,
            "world": world,
            "width": width,
            "height": height,
            "origin": origin,
            "created": _now(),
        }

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real occupancy map generation not implemented; returning mock map",
                world=world,
            )
        else:
            _logger.info("Occupancy map created (mock mode)", world=world)

        data = {
            "resolution": resolution,
            "width": width,
            "height": height,
            "origin": origin,
            "occupancy_summary": {
                "free": free,
                "occupied": occupied,
                "unknown": unknown,
            },
        }
        if response_format == "detailed":
            data["world"] = world
            data["total_cells"] = total_cells
            data["created"] = _costmaps["occupancy_map"]["created"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error creating occupancy map", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the resolution (> 0) and retry"],
        )


def update_costmap(
    updates: list,
    response_format: str = "concise",
) -> OperationResult:
    """
    Apply a batch of updates to the navigation costmap.

    Args:
        updates: Non-empty list of update dicts, each with an 'action' key of
                 'inject', 'clear', or 'inflate' plus action-specific fields
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with applied updates and count

    Example:
        >>> update_costmap([{"action": "inject", "x": 1.0, "y": 2.0, "radius": 0.5}])
    """
    try:
        response_format = _coerce_response_format(response_format)

        if not isinstance(updates, list) or len(updates) == 0:
            return OperationResult(
                success=False,
                error="updates must be a non-empty list",
                error_code="INVALID_UPDATES",
                suggestions=["Provide at least one update dict with an 'action' key"],
                example_fix="update_costmap([{'action': 'inject', 'x': 1.0, 'y': 2.0}])",
            )

        applied = []
        for idx, upd in enumerate(updates):
            if not isinstance(upd, dict) or "action" not in upd:
                return OperationResult(
                    success=False,
                    error=f"Update at index {idx} must be a dict with an 'action' key",
                    error_code="INVALID_UPDATE_ENTRY",
                    suggestions=[f"Use one of: {', '.join(sorted(_VALID_COSTMAP_ACTIONS))}"],
                    example_fix="update_costmap([{'action': 'clear'}])",
                )
            action = upd["action"]
            if action not in _VALID_COSTMAP_ACTIONS:
                return OperationResult(
                    success=False,
                    error=f"Invalid costmap action '{action}' at index {idx}",
                    error_code="INVALID_COSTMAP_ACTION",
                    suggestions=[f"Use one of: {', '.join(sorted(_VALID_COSTMAP_ACTIONS))}"],
                    example_fix="update_costmap([{'action': 'inflate', 'radius': 0.3}])",
                )
            applied.append({"action": action, "params": {k: v for k, v in upd.items() if k != "action"}})

        _costmaps.setdefault("applied_updates", []).extend(applied)

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real costmap update not implemented; recorded mock updates",
                count=len(applied),
            )
        else:
            _logger.info("Costmap updated (mock mode)", count=len(applied))

        data = {
            "applied": applied,
            "count": len(applied),
        }
        if response_format == "detailed":
            data["total_applied"] = len(_costmaps.get("applied_updates", []))
            data["timestamp"] = _now()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error updating costmap", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the updates list and retry"],
        )


def follow_waypoints(
    waypoints: list,
    mode: str = "sequence",
    response_format: str = "concise",
) -> OperationResult:
    """
    Start a waypoint-following mission.

    Args:
        waypoints: Non-empty list of waypoint dicts (each with 'x' and 'y')
        mode: Mission mode — one of: sequence, loop, patrol
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with mission_id, waypoint_count, mode, and status

    Example:
        >>> follow_waypoints([{"x": 1, "y": 1}, {"x": 2, "y": 2}], mode="loop")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if mode not in _VALID_WAYPOINT_MODES:
            return OperationResult(
                success=False,
                error=f"Invalid mode '{mode}'",
                error_code="INVALID_MODE",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_WAYPOINT_MODES))}"],
                example_fix="follow_waypoints([{'x':1,'y':1}], mode='sequence')",
            )

        if not isinstance(waypoints, list) or len(waypoints) == 0:
            return OperationResult(
                success=False,
                error="waypoints must be a non-empty list",
                error_code="INVALID_WAYPOINTS",
                suggestions=["Provide at least one waypoint dict, e.g. {'x': 1.0, 'y': 1.0}"],
                example_fix="follow_waypoints([{'x':1,'y':1}, {'x':2,'y':2}])",
            )

        mission_id = f"mission_{len(_nav_goals) + len(_paths) + 1}"
        mission = {
            "mission_id": mission_id,
            "waypoints": waypoints,
            "mode": mode,
            "status": "executing",
            "created": _now(),
        }
        _nav2_state.setdefault("missions", {})[mission_id] = mission

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real waypoint follower not implemented; returning mock mission",
                mission_id=mission_id,
            )
        else:
            _logger.info("Waypoint mission started (mock mode)", mission_id=mission_id)

        data = {
            "mission_id": mission_id,
            "waypoint_count": len(waypoints),
            "mode": mode,
            "status": "executing",
        }
        if response_format == "detailed":
            data["waypoints"] = waypoints
            data["created"] = mission["created"]

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error following waypoints", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the waypoints list and mode, then retry"],
        )


def plan_coverage_path(
    area: dict,
    algorithm: str = "boustrophedon",
    response_format: str = "concise",
) -> OperationResult:
    """
    Plan a coverage path over an area (e.g. for sweeping or inspection).

    Args:
        area: Dict describing the area to cover (e.g. bounds or polygon)
        algorithm: Coverage algorithm — one of: boustrophedon, spiral,
                   energy_efficient
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with algorithm, waypoints, coverage_pct, and
        path_length_m

    Example:
        >>> plan_coverage_path({"min_x": 0, "min_y": 0, "max_x": 5, "max_y": 5})
    """
    try:
        response_format = _coerce_response_format(response_format)

        if algorithm not in _VALID_COVERAGE_ALGORITHMS:
            return OperationResult(
                success=False,
                error=f"Invalid algorithm '{algorithm}'",
                error_code="INVALID_ALGORITHM",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_COVERAGE_ALGORITHMS))}"],
                example_fix="plan_coverage_path({'min_x':0,'min_y':0,'max_x':5,'max_y':5})",
            )

        if not isinstance(area, dict) or len(area) == 0:
            return OperationResult(
                success=False,
                error="area must be a non-empty dict describing the region to cover",
                error_code="INVALID_AREA",
                suggestions=["Provide area bounds, e.g. {'min_x':0,'min_y':0,'max_x':5,'max_y':5}"],
                example_fix="plan_coverage_path({'min_x':0,'min_y':0,'max_x':5,'max_y':5})",
            )

        min_x = float(area.get("min_x", 0.0))
        min_y = float(area.get("min_y", 0.0))
        max_x = float(area.get("max_x", min_x + 5.0))
        max_y = float(area.get("max_y", min_y + 5.0))
        spacing = float(area.get("spacing", 1.0)) or 1.0

        # Deterministic boustrophedon-style sweep:
        waypoints = []
        rows = max(int((max_y - min_y) / spacing) + 1, 1)
        for r in range(rows):
            y = round(min_y + r * spacing, 3)
            if r % 2 == 0:
                waypoints.append({"x": round(min_x, 3), "y": y})
                waypoints.append({"x": round(max_x, 3), "y": y})
            else:
                waypoints.append({"x": round(max_x, 3), "y": y})
                waypoints.append({"x": round(min_x, 3), "y": y})

        path_length_m = 0.0
        for i in range(1, len(waypoints)):
            dx = waypoints[i]["x"] - waypoints[i - 1]["x"]
            dy = waypoints[i]["y"] - waypoints[i - 1]["y"]
            path_length_m += math.sqrt(dx * dx + dy * dy)
        path_length_m = round(path_length_m, 3)

        coverage_pct = 95.0

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real coverage planning not implemented; returning mock coverage path",
                algorithm=algorithm,
            )
        else:
            _logger.info("Coverage path planned (mock mode)", algorithm=algorithm)

        data = {
            "algorithm": algorithm,
            "waypoints": waypoints,
            "coverage_pct": coverage_pct,
            "path_length_m": path_length_m,
        }
        if response_format == "detailed":
            data["area"] = area
            data["waypoint_count"] = len(waypoints)
            data["timestamp"] = _now()

        return OperationResult(success=True, data=data)

    except GazeboMCPError as e:
        return OperationResult(
            success=False,
            error=e.message,
            error_code=e.error_code,
            suggestions=e.suggestions,
            example_fix=e.example_fix,
        )
    except Exception as e:
        _logger.exception("Unexpected error planning coverage path", error=str(e))
        return OperationResult(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            suggestions=["Check the area dict and algorithm, then retry"],
        )
