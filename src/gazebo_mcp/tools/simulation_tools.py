"""
Gazebo Simulation Control Tools.

Provides functions for controlling simulation physics, time, and state:
- Pause/unpause physics
- Reset simulation
- Control simulation speed
- Get simulation time
"""

import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add claude project to path for ResultFilter:
# Use environment variable or relative path from project root
CLAUDE_ROOT = Path(os.environ.get("CLAUDE_ROOT", Path(__file__).parents[3] / "claude"))
if CLAUDE_ROOT.exists():
    sys.path.insert(0, str(CLAUDE_ROOT))

from gazebo_mcp.utils import (
    OperationResult,
    success_result,
    error_result,
)
from gazebo_mcp.utils.exceptions import GazeboMCPError, ROS2NotConnectedError
from gazebo_mcp.utils.validators import validate_positive, validate_timeout
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

# Module-level connection manager (singleton pattern):
_connection_manager: Optional[ConnectionManager] = None
_bridge_node: Optional[GazeboBridgeNode] = None
_logger = get_logger("simulation_tools")

# Simulation state tracking:
_simulation_paused = False


def _get_bridge() -> GazeboBridgeNode:
    """Get or create Gazebo bridge node."""
    global _connection_manager, _bridge_node

    if _bridge_node is not None:
        return _bridge_node

    try:
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2 for simulation tools")

        _bridge_node = GazeboBridgeNode(_connection_manager.get_node())
        _logger.info("Created Gazebo bridge node for simulation tools")

        return _bridge_node

    except Exception as e:
        _logger.error(f"Failed to create bridge", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def _use_real_gazebo() -> bool:
    """Check if we should use real Gazebo or mock data."""
    try:
        _get_bridge()
        return True
    except Exception:
        return False


def pause_simulation(
    timeout: float = 5.0,
    world: str = "default"
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
    global _simulation_paused

    try:
        timeout = validate_timeout(timeout)

        if _use_real_gazebo():
            bridge = _get_bridge()

            # Call pause service:
            success = bridge.pause_physics(timeout=timeout, world=world)

            if success:
                _simulation_paused = True
                _logger.info("Paused simulation")
                return success_result(
                    {"paused": True, "timestamp": datetime.utcnow().isoformat() + "Z"}
                )
            else:
                return error_result(error="Failed to pause simulation", error_code="PAUSE_FAILED")
        else:
            # Mock pause:
            _simulation_paused = True
            _logger.warning("Mock pause - Gazebo not available")
            return success_result(
                {
                    "paused": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock mode - Gazebo not available",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error pausing simulation", error=str(e))
        return error_result(error=f"Failed to pause simulation: {e}", error_code="PAUSE_ERROR")


def unpause_simulation(
    timeout: float = 5.0,
    world: str = "default"
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
    global _simulation_paused

    try:
        timeout = validate_timeout(timeout)

        if _use_real_gazebo():
            bridge = _get_bridge()

            # Call unpause service:
            success = bridge.unpause_physics(timeout=timeout, world=world)

            if success:
                _simulation_paused = False
                _logger.info("Unpaused simulation")
                return success_result(
                    {"paused": False, "timestamp": datetime.utcnow().isoformat() + "Z"}
                )
            else:
                return error_result(
                    error="Failed to unpause simulation", error_code="UNPAUSE_FAILED"
                )
        else:
            # Mock unpause:
            _simulation_paused = False
            _logger.warning("Mock unpause - Gazebo not available")
            return success_result(
                {
                    "paused": False,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "note": "Mock mode - Gazebo not available",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error unpausing simulation", error=str(e))
        return error_result(error=f"Failed to unpause simulation: {e}", error_code="UNPAUSE_ERROR")


def reset_simulation(
    timeout: float = 10.0,
    world: str = "default"
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
    try:
        timeout = validate_timeout(timeout)

        if _use_real_gazebo():
            bridge = _get_bridge()

            # Call reset service:
            success = bridge.reset_simulation(timeout=timeout, world=world)

            if success:
                _logger.info("Reset simulation")
                return success_result(
                    {
                        "reset": True,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "simulation_time": 0.0,
                    }
                )
            else:
                return error_result(error="Failed to reset simulation", error_code="RESET_FAILED")
        else:
            _logger.warning("Mock reset - Gazebo not available")
            return success_result(
                {
                    "reset": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "simulation_time": 0.0,
                    "note": "Mock mode - Gazebo not available",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error resetting simulation", error=str(e))
        return error_result(error=f"Failed to reset simulation: {e}", error_code="RESET_ERROR")


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

        if _use_real_gazebo():
            # TODO: Implement real speed setting via Gazebo services
            _logger.warning("Real simulation speed setting not yet implemented")

            return success_result(
                {
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
                }
            )
        else:
            return success_result(
                {
                    "speed_factor": speed_factor,
                    "set": False,
                    "note": "Gazebo not running - cannot set speed",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error setting speed", error=str(e))
        return error_result(
            error=f"Failed to set simulation speed: {e}", error_code="SET_SPEED_ERROR"
        )


def get_simulation_time() -> OperationResult:
    """
    Get current simulation time.

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
        if _use_real_gazebo():
            # TODO: Implement real time query
            _logger.warning("Using mock time data - real query not yet implemented")

            return success_result(
                {
                    "simulation_time": 123.456,
                    "real_time": 125.678,
                    "paused": _simulation_paused,
                    "iterations": 123456,
                    "note": "Mock data - real time query not yet implemented",
                }
            )
        else:
            return success_result(
                {
                    "simulation_time": 0.0,
                    "real_time": 0.0,
                    "paused": _simulation_paused,
                    "iterations": 0,
                    "note": "Gazebo not running",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error getting time", error=str(e))
        return error_result(
            error=f"Failed to get simulation time: {e}", error_code="GET_TIME_ERROR"
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
        if _use_real_gazebo():
            # Get time info:
            time_result = get_simulation_time()

            return success_result(
                {
                    "running": True,
                    "paused": _simulation_paused,
                    "simulation_time": time_result.data.get("simulation_time", 0.0),
                    "real_time": time_result.data.get("real_time", 0.0),
                    "iterations": time_result.data.get("iterations", 0),
                    "gazebo_connected": True,
                }
            )
        else:
            return success_result(
                {
                    "running": False,
                    "paused": False,
                    "simulation_time": 0.0,
                    "real_time": 0.0,
                    "iterations": 0,
                    "gazebo_connected": False,
                    "note": "Gazebo not running",
                }
            )

    except GazeboMCPError as e:
        return error_result(error=e.message, error_code=e.error_code, suggestions=e.suggestions)
    except Exception as e:
        _logger.exception("Unexpected error getting status", error=str(e))
        return error_result(
            error=f"Failed to get simulation status: {e}", error_code="GET_STATUS_ERROR"
        )
