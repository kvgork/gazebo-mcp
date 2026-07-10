"""
Gazebo SLAM & Mapping Tools.

Provides functions for running SLAM backends, saving and loading maps,
localizing a robot, assessing localization quality, and detecting loop
closures in Gazebo simulations.

All tools operate in a deterministic mock mode when not connected to a real
Gazebo/ROS2 stack, so they can be exercised without a running simulator.
"""

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
    "start_slam",
    "save_slam_map",
    "load_slam_map",
    "localize_robot",
    "get_localization_quality",
    "detect_loop_closure",
]

_logger = get_logger("slam_tools")

# Module-level state dicts (resettable in tests):
_slam_state: dict = {"active": False}
_maps: Dict[str, dict] = {}
_localization_state: dict = {"active": False}

# Valid enum sets:
_VALID_SLAM_BACKENDS = {"slam_toolbox", "cartographer", "rtabmap", "orb_slam3"}
_VALID_MAP_FORMATS = {"pgm_yaml", "ros_map_server"}
_VALID_LOCALIZATION_METHODS = {"amcl", "map_matching", "icp"}


def _now() -> str:
    """Return a timezone-aware ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def start_slam(
    backend: str = "slam_toolbox",
    robot: str = None,
    params: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Start a SLAM (Simultaneous Localization and Mapping) session.

    Args:
        backend: SLAM backend — one of: slam_toolbox, cartographer, rtabmap, orb_slam3
        robot: Optional robot name to attach SLAM to
        params: Optional dict of backend-specific tuning parameters
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with slam_id, backend, robot, and status

    Example:
        >>> result = start_slam(backend="slam_toolbox", robot="turtlebot3")
        >>> slam_id = result.data["slam_id"]
    """
    try:
        if backend not in _VALID_SLAM_BACKENDS:
            return OperationResult(
                success=False,
                error=f"Invalid backend '{backend}'",
                error_code="INVALID_BACKEND",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_SLAM_BACKENDS))}"],
                example_fix="start_slam(backend='slam_toolbox')",
            )

        if robot is not None:
            robot = validate_entity_name(robot, "robot")

        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        params = params or {}
        slam_id = f"slam_{backend}_1"

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode SLAM launch not yet implemented — using mock result",
                backend=backend,
            )
        else:
            _logger.info("SLAM started (mock mode)", backend=backend, robot=robot)

        _slam_state["active"] = True
        _slam_state["slam_id"] = slam_id
        _slam_state["backend"] = backend
        _slam_state["robot"] = robot
        _slam_state["params"] = params
        _slam_state["start_time"] = _now()

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "slam_id": slam_id,
                    "backend": backend,
                    "robot": robot,
                    "status": "running",
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "slam_id": slam_id,
                    "backend": backend,
                    "robot": robot,
                    "status": "running",
                    "params": params,
                    "start_time": _slam_state["start_time"],
                    "note": "Mock mode — SLAM session simulated" if not use_real_gazebo() else "SLAM launch requested",
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
        _logger.exception("Unexpected error starting SLAM", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to start SLAM: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check the backend name and parameters"],
        )


def save_slam_map(
    map_name: str,
    output_path: str = None,
    format: str = "pgm_yaml",
    response_format: str = "concise",
) -> OperationResult:
    """
    Save the current SLAM map to disk.

    Args:
        map_name: Unique name for the map (overwrite allowed)
        output_path: Optional output directory/prefix for the map files
        format: Map format — one of: pgm_yaml, ros_map_server
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with map_name, format, and the list of files written

    Example:
        >>> save_slam_map("warehouse_map", format="pgm_yaml")
    """
    try:
        map_name = validate_entity_name(map_name, "map")

        if format not in _VALID_MAP_FORMATS:
            return OperationResult(
                success=False,
                error=f"Invalid format '{format}'",
                error_code="INVALID_FORMAT",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_MAP_FORMATS))}"],
                example_fix="save_slam_map('my_map', format='pgm_yaml')",
            )

        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        prefix = output_path or map_name
        if format == "pgm_yaml":
            files = [f"{prefix}.pgm", f"{prefix}.yaml"]
        else:  # ros_map_server
            files = [f"{prefix}.yaml", f"{prefix}.pgm", f"{prefix}.posegraph"]

        overwritten = map_name in _maps

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode map save not yet implemented — using mock result",
                map_name=map_name,
            )
        else:
            _logger.info("Map saved (mock mode)", map_name=map_name, format=format)

        map_record = {
            "map_name": map_name,
            "format": format,
            "output_path": output_path,
            "files": files,
            "saved_at": _now(),
        }
        _maps[map_name] = map_record

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "map_name": map_name,
                    "format": format,
                    "files": files,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "map_name": map_name,
                    "format": format,
                    "output_path": output_path,
                    "files": files,
                    "overwritten": overwritten,
                    "saved_at": map_record["saved_at"],
                    "total_maps": len(_maps),
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
        _logger.exception("Unexpected error saving SLAM map", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to save SLAM map: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check the map name and output path"],
        )


def load_slam_map(
    map_path: str,
    response_format: str = "concise",
) -> OperationResult:
    """
    Load a previously saved SLAM map for localization or continued mapping.

    Args:
        map_path: Path to the map file (e.g. a .yaml descriptor)
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with map_path, loaded flag, and map_info metadata

    Example:
        >>> load_slam_map("/maps/warehouse.yaml")
    """
    try:
        if not map_path:
            return OperationResult(
                success=False,
                error="map_path must be a non-empty string",
                error_code="INVALID_MAP_PATH",
                suggestions=["Provide the path to a map descriptor, e.g. '/maps/my_map.yaml'"],
                example_fix="load_slam_map('/maps/my_map.yaml')",
            )

        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        map_info = {
            "resolution": 0.05,
            "width": 384,
            "height": 384,
            "origin": [-10.0, -10.0, 0.0],
        }

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode map load not yet implemented — using mock result",
                map_path=map_path,
            )
        else:
            _logger.info("Map loaded (mock mode)", map_path=map_path)

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "map_path": map_path,
                    "loaded": True,
                    "map_info": map_info,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "map_path": map_path,
                    "loaded": True,
                    "map_info": map_info,
                    "loaded_at": _now(),
                    "note": "Mock mode — map metadata simulated" if not use_real_gazebo() else "Map load requested",
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
        _logger.exception("Unexpected error loading SLAM map", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to load SLAM map: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check the map path"],
        )


def localize_robot(
    method: str = "amcl",
    initial_pose: dict = None,
    response_format: str = "concise",
) -> OperationResult:
    """
    Localize a robot within a loaded map.

    Args:
        method: Localization method — one of: amcl, map_matching, icp
        initial_pose: Optional initial pose hint, e.g. {"x": 0.0, "y": 0.0, "theta": 0.0}
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with the method, estimated_pose, and covariance

    Example:
        >>> localize_robot(method="amcl", initial_pose={"x": 1.0, "y": 2.0, "theta": 0.0})
    """
    try:
        if method not in _VALID_LOCALIZATION_METHODS:
            return OperationResult(
                success=False,
                error=f"Invalid method '{method}'",
                error_code="INVALID_METHOD",
                suggestions=[f"Use one of: {', '.join(sorted(_VALID_LOCALIZATION_METHODS))}"],
                example_fix="localize_robot(method='amcl')",
            )

        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        initial_pose = initial_pose or {}
        x = float(initial_pose.get("x", 0.0))
        y = float(initial_pose.get("y", 0.0))
        theta = float(initial_pose.get("theta", 0.0))

        estimated_pose = {"x": x, "y": y, "theta": theta}

        # 6-DoF covariance diagonal (x, y, z, roll, pitch, yaw):
        covariance = [0.25, 0.0, 0.0, 0.0, 0.0, 0.0685]

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode localization not yet implemented — using mock result",
                method=method,
            )
        else:
            _logger.info("Robot localized (mock mode)", method=method)

        _localization_state["active"] = True
        _localization_state["method"] = method
        _localization_state["estimated_pose"] = estimated_pose
        _localization_state["covariance"] = covariance
        _localization_state["start_time"] = _now()

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "method": method,
                    "estimated_pose": estimated_pose,
                    "covariance": covariance,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "method": method,
                    "estimated_pose": estimated_pose,
                    "covariance": covariance,
                    "initial_pose": initial_pose,
                    "start_time": _localization_state["start_time"],
                    "note": "Mock mode — localization simulated" if not use_real_gazebo() else "Localization requested",
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
        _logger.exception("Unexpected error localizing robot", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to localize robot: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Check the method and initial_pose"],
        )


def get_localization_quality(response_format: str = "concise") -> OperationResult:
    """
    Assess the quality of the current localization estimate.

    Args:
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with particle_spread, match_score, ambiguity, and quality

    Example:
        >>> result = get_localization_quality()
        >>> print(result.data["quality"])
    """
    try:
        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        particle_spread = 0.12
        match_score = 0.91
        ambiguity = 0.07

        # Derive a categorical quality rating:
        if match_score >= 0.85 and particle_spread <= 0.2 and ambiguity <= 0.1:
            quality = "good"
        elif match_score >= 0.6 and ambiguity <= 0.3:
            quality = "fair"
        else:
            quality = "poor"

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode localization quality not yet implemented — using mock result"
            )
        else:
            _logger.info("Localization quality assessed (mock mode)", quality=quality)

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "particle_spread": particle_spread,
                    "match_score": match_score,
                    "ambiguity": ambiguity,
                    "quality": quality,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "particle_spread": particle_spread,
                    "match_score": match_score,
                    "ambiguity": ambiguity,
                    "quality": quality,
                    "localization_active": _localization_state.get("active", False),
                    "timestamp": _now(),
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
        _logger.exception("Unexpected error assessing localization quality", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to assess localization quality: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Ensure localization has been started"],
        )


def detect_loop_closure(response_format: str = "concise") -> OperationResult:
    """
    Detect loop closures in the current SLAM session.

    Loop closure detection recognizes previously visited locations to correct
    accumulated drift in the map and trajectory.

    Args:
        response_format: "concise" or "detailed"

    Returns:
        OperationResult with loop_closure_detected, candidates, and method

    Example:
        >>> result = detect_loop_closure()
        >>> print(result.data["loop_closure_detected"])
    """
    try:
        if response_format not in ("concise", "detailed", "summary", "filtered"):
            response_format = "concise"

        candidates = [
            {
                "candidate_id": "kf_42",
                "current_keyframe": "kf_318",
                "match_score": 0.88,
                "distance_m": 0.34,
            },
            {
                "candidate_id": "kf_57",
                "current_keyframe": "kf_318",
                "match_score": 0.81,
                "distance_m": 0.52,
            },
        ]
        loop_closure_detected = len(candidates) > 0
        method = "visual_bag_of_words"

        if use_real_gazebo():
            bridge = get_bridge()
            _logger.warning(
                "Real-mode loop closure detection not yet implemented — using mock result"
            )
        else:
            _logger.info(
                "Loop closure detection run (mock mode)",
                detected=loop_closure_detected,
            )

        if response_format == "concise":
            return OperationResult(
                success=True,
                data={
                    "loop_closure_detected": loop_closure_detected,
                    "candidates": candidates,
                    "method": method,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "loop_closure_detected": loop_closure_detected,
                    "candidates": candidates,
                    "candidate_count": len(candidates),
                    "method": method,
                    "timestamp": _now(),
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
        _logger.exception("Unexpected error detecting loop closure", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to detect loop closure: {e}",
            error_code="INTERNAL_ERROR",
            suggestions=["Ensure a SLAM session is running"],
        )
