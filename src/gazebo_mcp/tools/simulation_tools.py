"""
Gazebo Simulation Control Tools.

Provides functions for controlling simulation physics, time, and state:
- Pause/unpause physics
- Reset simulation
- Control simulation speed
- Get simulation time
"""

import subprocess
import re
from typing import Optional, List
from datetime import datetime

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.exceptions import GazeboMCPError
from gazebo_mcp.utils.validators import validate_positive, validate_timeout
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.tools._bridge_helper import get_bridge, use_real_gazebo, _detect_world_name

__all__ = [
    "pause_simulation",
    "unpause_simulation",
    "reset_simulation",
    "set_simulation_speed",
    "get_simulation_time",
    "get_simulation_status",
    "list_worlds",
]

_logger = get_logger("simulation_tools")

# Simulation state tracking:
_simulation_paused = False


def pause_simulation(
    timeout: float = 5.0,
    world: Optional[str] = None
) -> OperationResult:
    """
    Pause Gazebo physics simulation.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        timeout: Service call timeout (seconds)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with pause status

    Example:
        >>> result = pause_simulation()
        >>> if result.success:
        ...     print("Simulation paused")
    """
    if world is None:
        world = _detect_world_name()
    global _simulation_paused

    try:
        timeout = validate_timeout(timeout)

        if use_real_gazebo():
            bridge = get_bridge()

            # Call pause service:
            success = bridge.pause_physics(timeout=timeout, world=world)

            if success:
                _simulation_paused = True
                _logger.info("Paused simulation")
                return OperationResult(
                    success=True,
                    data={"paused": True, "timestamp": datetime.utcnow().isoformat() + "Z"},
                )
            else:
                return OperationResult(
                    success=False,
                    error="Failed to pause simulation",
                    error_code="PAUSE_FAILED",
                )
        else:
            # Mock pause:
            _simulation_paused = True
            _logger.warning("Mock pause - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "paused": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock mode - Gazebo not available",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error pausing simulation", error=str(e))
        return OperationResult(
            success=False, error=f"Failed to pause simulation: {e}", error_code="PAUSE_ERROR"
        )


def unpause_simulation(
    timeout: float = 5.0,
    world: Optional[str] = None
) -> OperationResult:
    """
    Unpause Gazebo physics simulation.

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        timeout: Service call timeout (seconds)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with unpause status

    Example:
        >>> result = unpause_simulation()
        >>> if result.success:
        ...     print("Simulation running")
    """
    if world is None:
        world = _detect_world_name()
    global _simulation_paused

    try:
        timeout = validate_timeout(timeout)

        if use_real_gazebo():
            bridge = get_bridge()

            # Call unpause service:
            success = bridge.unpause_physics(timeout=timeout, world=world)

            if success:
                _simulation_paused = False
                _logger.info("Unpaused simulation")
                return OperationResult(
                    success=True,
                    data={"paused": False, "timestamp": datetime.utcnow().isoformat() + "Z"},
                )
            else:
                return OperationResult(
                    success=False,
                    error="Failed to unpause simulation",
                    error_code="UNPAUSE_FAILED",
                )
        else:
            # Mock unpause:
            _simulation_paused = False
            _logger.warning("Mock unpause - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "paused": False,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock mode - Gazebo not available",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error unpausing simulation", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to unpause simulation: {e}",
            error_code="UNPAUSE_ERROR",
        )


def reset_simulation(
    timeout: float = 10.0,
    world: Optional[str] = None
) -> OperationResult:
    """
    Reset Gazebo simulation to initial state.

    This resets:
    - All model poses to initial positions
    - Simulation time to 0
    - Physics state

    UPDATED (Phase 1B): Added world parameter for multi-world Modern Gazebo support.

    Args:
        timeout: Service call timeout (seconds)
        world: Target world name (Modern Gazebo only, default: "default")

    Returns:
        OperationResult with reset status

    Example:
        >>> result = reset_simulation()
        >>> if result.success:
        ...     print("Simulation reset")
    """
    if world is None:
        world = _detect_world_name()
    try:
        timeout = validate_timeout(timeout)

        if use_real_gazebo():
            bridge = get_bridge()

            # Call reset service:
            success = bridge.reset_simulation(timeout=timeout, world=world)

            if success:
                _logger.info("Reset simulation")
                return OperationResult(
                    success=True,
                    data={
                        "reset": True,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "simulation_time": 0.0,
                    },
                )
            else:
                return OperationResult(
                    success=False,
                    error="Failed to reset simulation",
                    error_code="RESET_FAILED",
                )
        else:
            _logger.warning("Mock reset - Gazebo not available")
            return OperationResult(
                success=True,
                data={
                    "reset": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "simulation_time": 0.0,
                    "note": "Mock mode - Gazebo not available",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error resetting simulation", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to reset simulation: {e}",
            error_code="RESET_ERROR",
        )


def set_simulation_speed(speed_factor: float) -> OperationResult:
    """
    Set simulation speed multiplier.

    Args:
        speed_factor:
            - 1.0 = real-time
            - < 1.0 = slower than real-time
            - > 1.0 = faster than real-time

    Returns:
        OperationResult with speed setting status

    Example:
        >>> # Run simulation at half speed:
        >>> result = set_simulation_speed(0.5)
        >>>
        >>> # Run simulation at 2x speed:
        >>> result = set_simulation_speed(2.0)
    """
    try:
        speed_factor = validate_positive(speed_factor, "speed_factor")

        if use_real_gazebo():
            # Real speed setting via gz_transport not yet supported — returns instructions instead
            _logger.warning("Real simulation speed setting not yet implemented")

            return OperationResult(
                success=True,
                data={
                    "speed_factor": speed_factor,
                    "set": False,
                    "note": "Simulation speed control via MCP will be implemented in a future update",
                    "instructions": """
To set simulation speed manually:

1. Edit Gazebo world file (before launch):
   <physics>
     <real_time_factor>2.0</real_time_factor>
   </physics>

2. Or use Gazebo GUI:
   - Click the physics configuration icon
   - Adjust "Real Time Factor"

Note: Speed factor may be limited by system performance.
                """.strip(),
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "speed_factor": speed_factor,
                    "set": False,
                    "note": "Gazebo not running - cannot set speed",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error setting speed", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to set simulation speed: {e}",
            error_code="SET_SPEED_ERROR",
        )


def get_simulation_time() -> OperationResult:
    """
    Get current simulation time.

    When Gazebo is connected, reads from the /clock topic (subscribed lazily).
    Falls back to zeroes when not connected.

    Returns:
        OperationResult with simulation time data

    Example:
        >>> result = get_simulation_time()
        >>> if result.success:
        ...     sim_time = result.data["simulation_time"]
        ...     real_time = result.data["real_time"]
        ...     print(f"Simulation: {sim_time}s, Real: {real_time}s")
    """
    try:
        if use_real_gazebo():
            bridge = get_bridge()
            stats = bridge.get_simulation_stats()
            return OperationResult(
                success=True,
                data={
                    "simulation_time": stats["simulation_time"],
                    "real_time": stats["real_time"],
                    "paused": _simulation_paused,
                    "iterations": stats.get("iterations", 0),
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "simulation_time": 0.0,
                    "real_time": 0.0,
                    "paused": _simulation_paused,
                    "iterations": 0,
                    "note": "Gazebo not running",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error getting time", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get simulation time: {e}",
            error_code="GET_TIME_ERROR",
        )


def get_simulation_status() -> OperationResult:
    """
    Get overall simulation status.

    Returns:
        OperationResult with complete simulation status

    Example:
        >>> result = get_simulation_status()
        >>> if result.success:
        ...     status = result.data
        ...     print(f"Running: {status['running']}")
        ...     print(f"Paused: {status['paused']}")
        ...     print(f"Time: {status['simulation_time']}s")
    """
    try:
        if use_real_gazebo():
            # Get time info:
            time_result = get_simulation_time()

            return OperationResult(
                success=True,
                data={
                    "running": True,
                    "paused": _simulation_paused,
                    "simulation_time": time_result.data.get("simulation_time", 0.0),
                    "real_time": time_result.data.get("real_time", 0.0),
                    "iterations": time_result.data.get("iterations", 0),
                    "gazebo_connected": True,
                },
            )
        else:
            return OperationResult(
                success=True,
                data={
                    "running": False,
                    "paused": False,
                    "simulation_time": 0.0,
                    "real_time": 0.0,
                    "iterations": 0,
                    "gazebo_connected": False,
                    "note": "Gazebo not running",
                },
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error getting status", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to get simulation status: {e}",
            error_code="GET_STATUS_ERROR",
        )


def list_worlds() -> OperationResult:
    """
    List all active Gazebo worlds.

    Discovers running worlds by inspecting the service graph via gz/ign CLI.
    Falls back to ["default"] when Gazebo is not connected.

    Returns:
        OperationResult with list of world names

    Example:
        >>> result = list_worlds()
        >>> for world in result.data["worlds"]:
        ...     print(world)
    """
    try:
        if use_real_gazebo():
            worlds = _discover_worlds()
            return OperationResult(
                success=True,
                data={"worlds": worlds, "count": len(worlds)},
            )
        else:
            return OperationResult(
                success=True,
                data={"worlds": ["default"], "count": 1, "note": "Gazebo not running"},
            )

    except GazeboMCPError as e:
        return OperationResult(
            success=False, error=e.message, error_code=e.error_code, suggestions=e.suggestions
        )
    except Exception as e:
        _logger.exception("Unexpected error listing worlds", error=str(e))
        return OperationResult(
            success=False,
            error=f"Failed to list worlds: {e}",
            error_code="LIST_WORLDS_ERROR",
        )


def _discover_worlds() -> List[str]:
    """
    Discover active Gazebo worlds by parsing the service list.

    Tries gz CLI (Garden/Harmonic) then ign CLI (Fortress/older).
    Extracts world names from service paths like /world/{name}/control.
    """
    for cli in ["gz", "ign"]:
        try:
            result = subprocess.run(
                [cli, "service", "--list"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if result.returncode == 0 and result.stdout.strip():
                worlds = sorted(set(re.findall(r"/world/([^/\s]+)/control", result.stdout)))
                if worlds:
                    return worlds
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            _logger.warning(f"Timeout listing services via {cli}")
            continue
        except Exception as e:
            _logger.warning(f"Error listing worlds via {cli}: {e}")
            continue

    return ["default"]
