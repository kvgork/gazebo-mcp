"""
Gazebo Multi-Robot Coordination Tools.

Provides functions for spawning and coordinating fleets of robots in Gazebo:
fleet spawning with collision-free formations, fleet status queries, fleet-wide
commands, swarm behaviors, network visualization, and multi-robot collision
avoidance. All tools operate deterministically in mock mode so they work
without a running Gazebo instance.
"""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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
    "spawn_robot_fleet",
    "get_fleet_status",
    "send_fleet_command",
    "apply_swarm_behavior",
    "visualize_robot_network",
    "enable_multi_robot_collision_avoidance",
]

_logger = get_logger("multi_robot_tools")

# Module-level state:
_fleets: Dict[str, dict] = {}

# Valid enum sets:
_VALID_FORMATIONS = {"line", "grid", "circle", "random"}
_VALID_COMMANDS = {"move", "stop", "formation", "sync", "return_home"}
_VALID_BEHAVIORS = {"flocking", "coverage", "formation_keeping", "leader_follower", "consensus"}
_VALID_VISUALIZATIONS = {"comms_graph", "task_allocation", "formation_lines", "collision_zones"}
_VALID_CA_METHODS = {"dynamic", "social_force", "velocity_obstacles", "priority"}


def _coerce_response_format(response_format: str) -> str:
    """Coerce response_format to 'concise' or 'detailed' (default 'concise')."""
    if response_format not in ("concise", "detailed"):
        return "concise"
    return response_format


def _now() -> str:
    """Return a timezone-aware ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _compute_formation_poses(
    count: int, formation: str, spacing: float, origin: dict
) -> List[Dict[str, float]]:
    """
    Compute deterministic, collision-free poses for a fleet.

    Args:
        count: Number of robots (>0)
        formation: One of line, grid, circle, random
        spacing: Minimum spacing between robots (>0)
        origin: Origin dict {x, y, z}

    Returns:
        List of pose dicts {x, y, z, yaw}, one per robot.
    """
    ox = origin.get("x", 0.0)
    oy = origin.get("y", 0.0)
    oz = origin.get("z", 0.0)

    poses: List[Dict[str, float]] = []

    if formation == "line":
        # Robots along +x at fixed spacing.
        for i in range(count):
            poses.append({"x": ox + i * spacing, "y": oy, "z": oz, "yaw": 0.0})

    elif formation == "grid":
        # ceil(sqrt(count)) rows/cols grid.
        cols = math.ceil(math.sqrt(count))
        for i in range(count):
            row = i // cols
            col = i % cols
            poses.append(
                {"x": ox + col * spacing, "y": oy + row * spacing, "z": oz, "yaw": 0.0}
            )

    elif formation == "circle":
        # Radius large enough to keep arc-spacing >= spacing.
        radius = max(spacing, count * spacing / (2.0 * math.pi))
        for i in range(count):
            angle = 2.0 * math.pi * i / count if count > 0 else 0.0
            poses.append(
                {
                    "x": ox + radius * math.cos(angle),
                    "y": oy + radius * math.sin(angle),
                    "z": oz,
                    # Face outward from circle center.
                    "yaw": angle,
                }
            )

    elif formation == "random":
        # Deterministic spread by index (no RNG): lay robots on an expanding
        # spiral so they never overlap.
        for i in range(count):
            ring = int(math.isqrt(i)) if i > 0 else 0
            angle = i * 2.399963229728653  # golden angle in radians
            r = spacing * (ring + 1)
            poses.append(
                {
                    "x": ox + r * math.cos(angle),
                    "y": oy + r * math.sin(angle),
                    "z": oz,
                    "yaw": angle,
                }
            )

    return poses


def spawn_robot_fleet(
    robot_type: str,
    count: int,
    formation: str = "grid",
    spacing: float = 2.0,
    namespace_prefix: str = "robot",
    origin: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Spawn a fleet of robots in a collision-free formation.

    Computes deterministic poses for each robot according to the chosen
    formation so that robots never overlap. Stores the fleet in module state.

    Args:
        robot_type: Robot model/type to spawn (e.g. "turtlebot3_burger")
        count: Number of robots to spawn (must be a positive integer)
        formation: Formation layout — one of: line, grid, circle, random
        spacing: Minimum spacing between robots in meters (must be > 0)
        namespace_prefix: Prefix for per-robot namespaces (default "robot")
        origin: Origin dict {x, y, z} for the formation (default {0,0,0})
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with fleet_id, count, formation, and robot list.

    Example:
        >>> result = spawn_robot_fleet("turtlebot3_burger", 4, formation="grid")
        >>> fleet_id = result.data["fleet_id"]
    """
    try:
        robot_type = validate_entity_name(robot_type, "robot_type")

        if formation not in _VALID_FORMATIONS:
            return OperationResult(
                success=False,
                error=f"Invalid formation '{formation}'",
                error_code="INVALID_FORMATION",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_FORMATIONS))}"],
                example_fix="spawn_robot_fleet('turtlebot3', 4, formation='grid')",
            )

        # count must be a positive integer (reject floats/bools).
        if isinstance(count, bool) or not isinstance(count, int):
            return OperationResult(
                success=False,
                error=f"count must be a positive integer, got {count!r}",
                error_code="INVALID_COUNT",
                suggestions=["Provide a positive integer count, e.g. count=4"],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )
        count = int(validate_positive(count, "count"))

        spacing = validate_positive(spacing, "spacing")

        if not namespace_prefix:
            namespace_prefix = "robot"

        if origin is None:
            origin = {"x": 0.0, "y": 0.0, "z": 0.0}

        response_format = _coerce_response_format(response_format)

        poses = _compute_formation_poses(count, formation, spacing, origin)

        robots = []
        for i, pose in enumerate(poses):
            name = f"{namespace_prefix}_{i + 1}"
            robots.append(
                {
                    "name": name,
                    "namespace": f"/{name}",
                    "pose": pose,
                }
            )

        fleet_id = f"fleet_{len(_fleets) + 1}"

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode fleet spawn not yet implemented; using deterministic mock poses",
                fleet_id=fleet_id,
            )
        else:
            _logger.info("Fleet spawned (mock mode)", fleet_id=fleet_id, count=count)

        fleet = {
            "id": fleet_id,
            "robot_type": robot_type,
            "count": count,
            "formation": formation,
            "robots": robots,
            "created": _now(),
        }
        _fleets[fleet_id] = fleet

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "fleet_id": fleet_id,
                    "count": count,
                    "formation": formation,
                    "robots": [{"name": r["name"], "pose": r["pose"]} for r in robots],
                },
            )
        return OperationResult(
            success=True,
            data={
                "fleet_id": fleet_id,
                "robot_type": robot_type,
                "count": count,
                "formation": formation,
                "spacing": spacing,
                "origin": origin,
                "robots": robots,
                "created": fleet["created"],
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
        _logger.exception("Unexpected error spawning robot fleet", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to spawn robot fleet: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check robot_type, count, and formation parameters"],
        )


def _mock_robot_status(name: str, index: int) -> Dict[str, Any]:
    """Build a deterministic per-robot status payload."""
    return {
        "name": name,
        "position": {"x": float(index), "y": 0.0, "z": 0.0},
        "velocity": {
            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "battery_pct": max(0.0, 100.0 - index * 5.0),
        "task_status": "idle",
    }


def get_fleet_status(
    fleet_id: str = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Get the status of one fleet or all fleets.

    Args:
        fleet_id: Fleet ID to query; if None, returns status of all fleets.
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with per-robot status (position, velocity, battery,
        task_status). Unknown fleet_id returns FLEET_NOT_FOUND.

    Example:
        >>> get_fleet_status("fleet_1")
        >>> get_fleet_status()   # all fleets
    """
    try:
        response_format = _coerce_response_format(response_format)

        if fleet_id is not None and fleet_id not in _fleets:
            return OperationResult(
                success=False,
                error=f"Fleet '{fleet_id}' not found",
                error_code="FLEET_NOT_FOUND",
                suggestions=[
                    f"Available fleets: {list(_fleets.keys())}"
                    if _fleets
                    else "No fleets spawned yet",
                    "Spawn a fleet first with spawn_robot_fleet(...)",
                ],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )

        target_ids = [fleet_id] if fleet_id is not None else list(_fleets.keys())

        fleets_status = []
        for fid in target_ids:
            fleet = _fleets[fid]
            robot_statuses = [
                _mock_robot_status(r["name"], i)
                for i, r in enumerate(fleet["robots"])
            ]
            fleets_status.append(
                {
                    "fleet_id": fid,
                    "robot_type": fleet["robot_type"],
                    "count": fleet["count"],
                    "formation": fleet["formation"],
                    "robots": robot_statuses,
                }
            )

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning("Real-mode fleet status not implemented; returning mock status")
        else:
            _logger.info("Fleet status collected (mock mode)", fleet_count=len(fleets_status))

        return OperationResult(
            success=True,
            data={
                "fleet_id": fleet_id,
                "fleet_count": len(fleets_status),
                "fleets": fleets_status,
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
        _logger.exception("Unexpected error getting fleet status", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get fleet status: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Verify the fleet_id or spawn a fleet first"],
        )


def _resolve_targets(fleet_id: str, targets: list) -> List[str]:
    """Resolve dispatch target robot names within a fleet (None = whole fleet)."""
    fleet = _fleets[fleet_id]
    all_names = [r["name"] for r in fleet["robots"]]
    if targets is None:
        return all_names
    return [name for name in all_names if name in set(targets)]


def _pick_fleet_id(fleet_id: str) -> Optional[str]:
    """Pick the fleet to act on: explicit id, else the only/first fleet."""
    if fleet_id is not None:
        return fleet_id
    if _fleets:
        return next(iter(_fleets))
    return None


def send_fleet_command(
    command: str,
    fleet_id: str = None,
    targets: list = None,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Send a command to a fleet (or a subset of its robots).

    Args:
        command: Command — one of: move, stop, formation, sync, return_home
        fleet_id: Fleet to command; if None, uses the first available fleet.
        targets: Subset of robot names to command; None broadcasts to the fleet.
        params: Optional command parameters dict.
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with command, fleet_id, dispatched_to names, and count.

    Example:
        >>> send_fleet_command("move", fleet_id="fleet_1", params={"goal": [5, 0]})
    """
    try:
        response_format = _coerce_response_format(response_format)

        if command not in _VALID_COMMANDS:
            return OperationResult(
                success=False,
                error=f"Invalid command '{command}'",
                error_code="INVALID_COMMAND",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_COMMANDS))}"],
                example_fix="send_fleet_command('move', fleet_id='fleet_1')",
            )

        resolved_id = _pick_fleet_id(fleet_id)
        if resolved_id is None or resolved_id not in _fleets:
            return OperationResult(
                success=False,
                error=f"Fleet '{fleet_id}' not found"
                if fleet_id is not None
                else "No fleets available to command",
                error_code="FLEET_NOT_FOUND",
                suggestions=[
                    f"Available fleets: {list(_fleets.keys())}"
                    if _fleets
                    else "Spawn a fleet first with spawn_robot_fleet(...)"
                ],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )

        dispatched_to = _resolve_targets(resolved_id, targets)
        params = params or {}

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning("Real-mode fleet command not implemented; simulating dispatch")
        else:
            _logger.info(
                "Fleet command dispatched (mock mode)",
                command=command,
                fleet_id=resolved_id,
                count=len(dispatched_to),
            )

        data = {
            "command": command,
            "fleet_id": resolved_id,
            "dispatched_to": dispatched_to,
            "count": len(dispatched_to),
        }
        if response_format == "detailed":
            data["targets_requested"] = targets
            data["params"] = params
            data["broadcast"] = targets is None

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
        _logger.exception("Unexpected error sending fleet command", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to send fleet command: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Verify the command, fleet_id, and targets"],
        )


def apply_swarm_behavior(
    behavior: str,
    fleet_id: str = None,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Apply a swarm behavior to a fleet.

    Args:
        behavior: Behavior — one of: flocking, coverage, formation_keeping,
                  leader_follower, consensus
        fleet_id: Fleet to apply to; if None, uses the first available fleet.
        params: Optional behavior parameters dict.
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with behavior, fleet_id, applied_to names, and params.

    Example:
        >>> apply_swarm_behavior("flocking", fleet_id="fleet_1")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if behavior not in _VALID_BEHAVIORS:
            return OperationResult(
                success=False,
                error=f"Invalid behavior '{behavior}'",
                error_code="INVALID_BEHAVIOR",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_BEHAVIORS))}"],
                example_fix="apply_swarm_behavior('flocking', fleet_id='fleet_1')",
            )

        resolved_id = _pick_fleet_id(fleet_id)
        if resolved_id is None or resolved_id not in _fleets:
            return OperationResult(
                success=False,
                error=f"Fleet '{fleet_id}' not found"
                if fleet_id is not None
                else "No fleets available for swarm behavior",
                error_code="FLEET_NOT_FOUND",
                suggestions=[
                    f"Available fleets: {list(_fleets.keys())}"
                    if _fleets
                    else "Spawn a fleet first with spawn_robot_fleet(...)"
                ],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )

        applied_to = [r["name"] for r in _fleets[resolved_id]["robots"]]
        params = params or {}

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning("Real-mode swarm behavior not implemented; simulating application")
        else:
            _logger.info(
                "Swarm behavior applied (mock mode)", behavior=behavior, fleet_id=resolved_id
            )

        data = {
            "behavior": behavior,
            "fleet_id": resolved_id,
            "applied_to": applied_to,
            "parameters": params,
        }
        if response_format == "detailed":
            data["robot_count"] = len(applied_to)
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
        _logger.exception("Unexpected error applying swarm behavior", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to apply swarm behavior: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Verify the behavior and fleet_id"],
        )


def visualize_robot_network(
    fleet_id: str = None,
    show: list = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Generate visualization markers for a multi-robot network.

    Returns instruction-style guidance plus a mock marker payload for the
    requested visualization layers. RViz2 must be running to render markers.

    Args:
        fleet_id: Fleet to visualize; if None, uses the first available fleet.
        show: Subset of {comms_graph, task_allocation, formation_lines,
              collision_zones}; defaults to all four.
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with fleet_id, visualizations list, and markers payload.

    Example:
        >>> visualize_robot_network("fleet_1", show=["comms_graph"])
    """
    try:
        response_format = _coerce_response_format(response_format)

        if show is None:
            show = sorted(_VALID_VISUALIZATIONS)

        invalid = [v for v in show if v not in _VALID_VISUALIZATIONS]
        if invalid:
            return OperationResult(
                success=False,
                error=f"Invalid visualization(s): {invalid}",
                error_code="INVALID_VISUALIZATION",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_VISUALIZATIONS))}"],
                example_fix="visualize_robot_network('fleet_1', show=['comms_graph'])",
            )

        resolved_id = _pick_fleet_id(fleet_id)
        if resolved_id is None or resolved_id not in _fleets:
            return OperationResult(
                success=False,
                error=f"Fleet '{fleet_id}' not found"
                if fleet_id is not None
                else "No fleets available to visualize",
                error_code="FLEET_NOT_FOUND",
                suggestions=[
                    f"Available fleets: {list(_fleets.keys())}"
                    if _fleets
                    else "Spawn a fleet first with spawn_robot_fleet(...)"
                ],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )

        robots = _fleets[resolved_id]["robots"]
        names = [r["name"] for r in robots]

        # Build a deterministic mock marker payload per requested layer.
        markers: Dict[str, Any] = {}
        for layer in show:
            if layer == "comms_graph":
                edges = [
                    [names[i], names[i + 1]] for i in range(len(names) - 1)
                ]
                markers[layer] = {"type": "LINE_LIST", "edges": edges, "nodes": names}
            elif layer == "task_allocation":
                markers[layer] = {
                    "type": "TEXT_VIEW_FACING",
                    "labels": {n: "idle" for n in names},
                }
            elif layer == "formation_lines":
                markers[layer] = {
                    "type": "LINE_STRIP",
                    "points": [r["pose"] for r in robots],
                }
            elif layer == "collision_zones":
                markers[layer] = {
                    "type": "CYLINDER",
                    "zones": [{"name": n, "radius": 0.5} for n in names],
                }

        instructions = (
            "Publish these markers to the /visualization_marker_array topic and "
            "add a MarkerArray display in RViz2 to render the robot network."
        )

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning("Real-mode network visualization not implemented; returning mock markers")
        else:
            _logger.info(
                "Network visualization generated (mock mode)",
                fleet_id=resolved_id,
                layers=show,
            )

        data = {
            "fleet_id": resolved_id,
            "visualizations": list(show),
            "markers": markers,
            "instructions": instructions,
        }
        if response_format == "detailed":
            data["robot_count"] = len(names)
            data["note"] = "RViz2 must be running to render the marker array."

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
        _logger.exception("Unexpected error visualizing robot network", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to visualize robot network: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Verify the fleet_id and show layers"],
        )


def enable_multi_robot_collision_avoidance(
    fleet_id: str = None,
    method: str = "velocity_obstacles",
    enabled: bool = True,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Enable or disable multi-robot collision avoidance for a fleet.

    Args:
        fleet_id: Fleet to configure; if None, uses the first available fleet.
        method: Avoidance method — one of: dynamic, social_force,
                velocity_obstacles, priority (default "velocity_obstacles")
        enabled: Whether avoidance is enabled (default True)
        params: Optional method parameters dict.
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with fleet_id, method, enabled flag, and parameters.

    Example:
        >>> enable_multi_robot_collision_avoidance("fleet_1", method="priority")
    """
    try:
        response_format = _coerce_response_format(response_format)

        if method not in _VALID_CA_METHODS:
            return OperationResult(
                success=False,
                error=f"Invalid method '{method}'",
                error_code="INVALID_CA_METHOD",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_CA_METHODS))}"],
                example_fix="enable_multi_robot_collision_avoidance('fleet_1', method='velocity_obstacles')",
            )

        resolved_id = _pick_fleet_id(fleet_id)
        if resolved_id is None or resolved_id not in _fleets:
            return OperationResult(
                success=False,
                error=f"Fleet '{fleet_id}' not found"
                if fleet_id is not None
                else "No fleets available to configure",
                error_code="FLEET_NOT_FOUND",
                suggestions=[
                    f"Available fleets: {list(_fleets.keys())}"
                    if _fleets
                    else "Spawn a fleet first with spawn_robot_fleet(...)"
                ],
                example_fix="spawn_robot_fleet('turtlebot3', 4)",
            )

        params = params or {}

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning("Real-mode collision avoidance not implemented; simulating config")
        else:
            _logger.info(
                "Collision avoidance configured (mock mode)",
                fleet_id=resolved_id,
                method=method,
                enabled=enabled,
            )

        data = {
            "fleet_id": resolved_id,
            "method": method,
            "enabled": enabled,
            "parameters": params,
        }
        if response_format == "detailed":
            data["robot_count"] = len(_fleets[resolved_id]["robots"])
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
        _logger.exception("Unexpected error enabling collision avoidance", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to enable collision avoidance: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Verify the fleet_id and method"],
        )
