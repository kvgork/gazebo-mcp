"""
Gazebo World Generation Tools.

Provides functions for creating and manipulating Gazebo worlds programmatically:
- Create obstacle courses
- Generate terrain
- Place objects
- Control lighting
"""

import random
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from gazebo_mcp.utils import (
    OperationResult,
    success_result,
    error_result,
)
from gazebo_mcp.utils.exceptions import GazeboMCPError, InvalidParameterError
from gazebo_mcp.utils.validators import (
    validate_entity_name,
    validate_positive,
    validate_non_negative,
    validate_position,
)
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.utils.exceptions import ROS2NotConnectedError

_logger = get_logger("world_generation")

# Module-level bridge (singleton pattern for spawning):
_connection_manager: Optional['ConnectionManager'] = None
_bridge_node: Optional['GazeboBridgeNode'] = None

# Material property library
MATERIAL_PROPERTIES = {
    "grass": {
        "friction": 0.8,
        "restitution": 0.1,
        "color": {"r": 0.2, "g": 0.8, "b": 0.2, "a": 1.0},
        "description": "Natural grass surface",
    },
    "concrete": {
        "friction": 1.0,
        "restitution": 0.01,
        "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0},
        "description": "Hard concrete surface",
    },
    "ice": {
        "friction": 0.1,
        "restitution": 0.9,
        "color": {"r": 0.8, "g": 0.9, "b": 1.0, "a": 0.7},
        "description": "Slippery ice surface",
    },
    "sand": {
        "friction": 0.6,
        "restitution": 0.05,
        "color": {"r": 0.9, "g": 0.8, "b": 0.6, "a": 1.0},
        "description": "Sandy terrain",
    },
    "wood": {
        "friction": 0.7,
        "restitution": 0.3,
        "color": {"r": 0.6, "g": 0.4, "b": 0.2, "a": 1.0},
        "description": "Wooden surface",
    },
    "rubber": {
        "friction": 0.9,
        "restitution": 0.8,
        "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1.0},
        "description": "Rubber surface",
    },
}


def create_obstacle_course(
    num_obstacles: int = 10,
    area_size: float = 20.0,
    obstacle_types: Optional[List[str]] = None,
    min_distance: float = 2.0,
    seed: Optional[int] = None,
) -> OperationResult:
    """
    Generate a random obstacle course for robot navigation testing.

    Creates a layout of randomly placed obstacles with configurable density,
    types, and spacing. Perfect for testing navigation algorithms.

    Args:
        num_obstacles: Number of obstacles to place (1-100)
        area_size: Size of square area in meters (5-100)
        obstacle_types: List of obstacle types ['box', 'cylinder', 'sphere']
                       If None, uses all types
        min_distance: Minimum distance between obstacles in meters (0.5-5.0)
        seed: Random seed for reproducible layouts (optional)

    Returns:
        OperationResult with obstacle course layout and SDF generation info

    Example:
        >>> result = create_obstacle_course(
        ...     num_obstacles=15,
        ...     area_size=20.0,
        ...     obstacle_types=['box', 'cylinder'],
        ...     min_distance=2.5,
        ...     seed=42
        ... )
        >>> if result.success:
        ...     print(f"Created {len(result.data['obstacles'])} obstacles")
        ...     print(f"Course area: {result.data['area_size']}m²")
    """
    try:
        # Validate parameters
        num_obstacles = int(validate_positive(num_obstacles, "num_obstacles"))
        if num_obstacles > 100:
            return error_result(
                error="num_obstacles must be <= 100",
                error_code="INVALID_PARAMETER",
                suggestions=["Try using fewer obstacles", "Increase area_size"],
            )

        area_size = validate_positive(area_size, "area_size")
        if area_size < 5.0 or area_size > 100.0:
            return error_result(
                error="area_size must be between 5.0 and 100.0 meters",
                error_code="INVALID_PARAMETER",
            )

        min_distance = validate_positive(min_distance, "min_distance")
        if min_distance < 0.5 or min_distance > 5.0:
            return error_result(
                error="min_distance must be between 0.5 and 5.0 meters",
                error_code="INVALID_PARAMETER",
            )

        # Set obstacle types
        if obstacle_types is None:
            obstacle_types = ["box", "cylinder", "sphere"]
        else:
            valid_types = ["box", "cylinder", "sphere"]
            for otype in obstacle_types:
                if otype not in valid_types:
                    return error_result(
                        error=f"Invalid obstacle type: {otype}",
                        error_code="INVALID_PARAMETER",
                        suggestions=[
                            f"Valid types: {', '.join(valid_types)}",
                            "Check spelling",
                        ],
                    )

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)

        # Generate obstacle positions
        obstacles = []
        max_retries = 1000

        for i in range(num_obstacles):
            placed = False
            for attempt in range(max_retries):
                # Random position in area
                x = random.uniform(-area_size / 2, area_size / 2)
                y = random.uniform(-area_size / 2, area_size / 2)
                z = 0.5  # Height above ground

                # Check distance to existing obstacles
                too_close = False
                for existing in obstacles:
                    dist = math.sqrt(
                        (x - existing["position"]["x"]) ** 2 + (y - existing["position"]["y"]) ** 2
                    )
                    if dist < min_distance:
                        too_close = True
                        break

                if not too_close:
                    # Choose random obstacle type and size
                    obstacle_type = random.choice(obstacle_types)
                    size = random.uniform(0.3, 1.5)

                    obstacles.append(
                        {
                            "name": f"obstacle_{i}",
                            "type": obstacle_type,
                            "position": {"x": x, "y": y, "z": z},
                            "size": size,
                            "color": {
                                "r": random.uniform(0.3, 0.9),
                                "g": random.uniform(0.3, 0.9),
                                "b": random.uniform(0.3, 0.9),
                                "a": 1.0,
                            },
                        }
                    )
                    placed = True
                    break

            if not placed:
                _logger.warning(f"Could not place obstacle {i} after {max_retries} attempts")
                return error_result(
                    error=f"Could not place all obstacles (placed {len(obstacles)}/{num_obstacles})",
                    error_code="GENERATION_ERROR",
                    suggestions=[
                        "Reduce num_obstacles",
                        "Increase area_size",
                        "Reduce min_distance",
                    ],
                )

        _logger.info(f"Generated obstacle course with {len(obstacles)} obstacles")

        return success_result(
            {
                "obstacles": obstacles,
                "num_obstacles": len(obstacles),
                "area_size": area_size,
                "min_distance": min_distance,
                "seed": seed,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "note": "Obstacle course layout generated. Use spawn_model() to place obstacles.",
            }
        )

    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "GENERATION_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error generating obstacle course", error=str(e))
        return error_result(
            error=f"Failed to generate obstacle course: {e}",
            error_code="GENERATION_ERROR",
        )


def list_materials() -> OperationResult:
    """
    List available material properties for surfaces.

    Returns material presets that can be used for terrain and objects,
    including friction, restitution (bounciness), and visual properties.

    Returns:
        OperationResult with material properties dictionary

    Example:
        >>> result = list_materials()
        >>> if result.success:
        ...     for name, props in result.data['materials'].items():
        ...         print(f"{name}: friction={props['friction']}")
    """
    try:
        return success_result(
            {
                "materials": MATERIAL_PROPERTIES,
                "count": len(MATERIAL_PROPERTIES),
                "available_types": list(MATERIAL_PROPERTIES.keys()),
            }
        )
    except Exception as e:
        _logger.exception("Error listing materials", error=str(e))
        return error_result(error=f"Failed to list materials: {e}", error_code="MATERIALS_ERROR")


def create_lighting_preset(preset_name: str, intensity: float = 1.0) -> OperationResult:
    """
    Create lighting configuration preset.

    Provides predefined lighting setups for different scenarios:
    - 'day': Bright outdoor daylight
    - 'night': Dark with moonlight
    - 'dawn': Orange morning light
    - 'dusk': Red evening light
    - 'indoor': Uniform indoor lighting
    - 'warehouse': Industrial overhead lighting

    Args:
        preset_name: Name of lighting preset
        intensity: Light intensity multiplier (0.0-2.0)

    Returns:
        OperationResult with lighting configuration

    Example:
        >>> result = create_lighting_preset('dawn', intensity=0.8)
        >>> if result.success:
        ...     config = result.data['lighting']
        ...     print(f"Sun angle: {config['sun_angle']}")
    """
    try:
        preset_name = preset_name.lower()
        intensity = validate_positive(intensity, "intensity")

        if intensity > 2.0:
            return error_result(
                error="intensity must be <= 2.0",
                error_code="INVALID_PARAMETER",
                suggestions=["Use value between 0.0 and 2.0"],
            )

        presets = {
            "day": {
                "ambient": {"r": 0.6, "g": 0.6, "b": 0.6, "a": 1.0},
                "sun_angle": 45.0,  # degrees
                "sun_color": {"r": 1.0, "g": 1.0, "b": 0.9, "a": 1.0},
                "shadows": True,
                "description": "Bright midday sunlight",
            },
            "night": {
                "ambient": {"r": 0.05, "g": 0.05, "b": 0.1, "a": 1.0},
                "sun_angle": -30.0,  # Below horizon
                "sun_color": {"r": 0.3, "g": 0.3, "b": 0.4, "a": 1.0},
                "shadows": False,
                "description": "Dark night with moonlight",
            },
            "dawn": {
                "ambient": {"r": 0.4, "g": 0.3, "b": 0.3, "a": 1.0},
                "sun_angle": 10.0,  # Low on horizon
                "sun_color": {"r": 1.0, "g": 0.7, "b": 0.5, "a": 1.0},
                "shadows": True,
                "description": "Orange morning light",
            },
            "dusk": {
                "ambient": {"r": 0.3, "g": 0.2, "b": 0.3, "a": 1.0},
                "sun_angle": -10.0,  # Setting below horizon
                "sun_color": {"r": 1.0, "g": 0.5, "b": 0.3, "a": 1.0},
                "shadows": True,
                "description": "Red evening light",
            },
            "indoor": {
                "ambient": {"r": 0.7, "g": 0.7, "b": 0.7, "a": 1.0},
                "sun_angle": 90.0,  # Overhead
                "sun_color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
                "shadows": False,
                "description": "Uniform indoor lighting",
            },
            "warehouse": {
                "ambient": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0},
                "sun_angle": 80.0,  # High overhead
                "sun_color": {"r": 1.0, "g": 1.0, "b": 0.95, "a": 1.0},
                "shadows": True,
                "description": "Industrial overhead lighting",
            },
        }

        if preset_name not in presets:
            return error_result(
                error=f"Unknown lighting preset: {preset_name}",
                error_code="INVALID_PARAMETER",
                suggestions=[
                    f"Available presets: {', '.join(presets.keys())}",
                    "Check spelling",
                ],
            )

        config = presets[preset_name].copy()

        # Apply intensity multiplier to colors
        for color_key in ["ambient", "sun_color"]:
            if color_key in config:
                for channel in ["r", "g", "b"]:
                    config[color_key][channel] = min(1.0, config[color_key][channel] * intensity)

        return success_result(
            {
                "preset": preset_name,
                "lighting": config,
                "intensity": intensity,
                "available_presets": list(presets.keys()),
                "note": "Use world_tools.set_world_property() to apply lighting configuration",
            }
        )

    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "LIGHTING_ERROR"))
    except Exception as e:
        _logger.exception("Error creating lighting preset", error=str(e))
        return error_result(
            error=f"Failed to create lighting preset: {e}",
            error_code="LIGHTING_ERROR",
        )


def calculate_day_night_cycle(time_of_day: float, cycle_duration: float = 24.0) -> OperationResult:
    """
    Calculate lighting for day/night cycle animation.

    Computes sun position and color based on time of day, enabling
    dynamic day/night cycles in simulation.

    Args:
        time_of_day: Time in hours (0.0-24.0), where 0=midnight, 12=noon
        cycle_duration: Duration of full cycle in simulation hours (default: 24.0)

    Returns:
        OperationResult with calculated lighting parameters

    Example:
        >>> # Sunrise at 6:00 AM
        >>> result = calculate_day_night_cycle(6.0)
        >>> if result.success:
        ...     print(f"Sun angle: {result.data['sun_angle']}°")
        ...     print(f"Phase: {result.data['phase']}")  # 'dawn'
    """
    try:
        time_of_day = validate_non_negative(time_of_day, "time_of_day")

        if time_of_day > 24.0:
            return error_result(
                error="time_of_day must be between 0.0 and 24.0",
                error_code="INVALID_PARAMETER",
            )

        # Normalize time to 0-24 range
        time_normalized = time_of_day % 24.0

        # Calculate sun angle (-90 to 90 degrees)
        # Noon (12.0) = 90°, Midnight (0.0 or 24.0) = -90°
        sun_angle = 90.0 * math.sin(math.pi * (time_normalized - 6.0) / 12.0)

        # Determine phase
        if 5.0 <= time_normalized < 7.0:
            phase = "dawn"
        elif 7.0 <= time_normalized < 17.0:
            phase = "day"
        elif 17.0 <= time_normalized < 19.0:
            phase = "dusk"
        else:
            phase = "night"

        # Calculate color based on sun angle
        if sun_angle > 30.0:  # High sun (day)
            sun_color = {"r": 1.0, "g": 1.0, "b": 0.95, "a": 1.0}
            ambient = {"r": 0.6, "g": 0.6, "b": 0.6, "a": 1.0}
        elif 0.0 <= sun_angle <= 30.0:  # Low sun (dawn/dusk)
            # Orange/red tint
            t = sun_angle / 30.0  # 0 at horizon, 1 at 30°
            sun_color = {
                "r": 1.0,
                "g": 0.5 + 0.5 * t,
                "b": 0.3 + 0.6 * t,
                "a": 1.0,
            }
            ambient = {"r": 0.4, "g": 0.3 * t, "b": 0.3, "a": 1.0}
        else:  # Below horizon (night)
            sun_color = {"r": 0.3, "g": 0.3, "b": 0.4, "a": 1.0}
            ambient = {"r": 0.05, "g": 0.05, "b": 0.1, "a": 1.0}

        return success_result(
            {
                "time_of_day": time_normalized,
                "sun_angle": round(sun_angle, 2),
                "phase": phase,
                "sun_color": sun_color,
                "ambient": ambient,
                "shadows": sun_angle > 0.0,
                "cycle_duration": cycle_duration,
                "note": "Use world_tools.set_world_property() to apply lighting",
            }
        )

    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "CYCLE_ERROR"))
    except Exception as e:
        _logger.exception("Error calculating day/night cycle", error=str(e))
        return error_result(
            error=f"Failed to calculate day/night cycle: {e}",
            error_code="CYCLE_ERROR",
        )


def generate_heightmap_terrain(
    width: int = 129,
    height: int = 129,
    pattern: str = "hills",
    min_elevation: float = 0.0,
    max_elevation: float = 10.0,
    smoothness: float = 1.0,
    seed: Optional[int] = None,
) -> OperationResult:
    """
    Generate heightmap terrain data for Gazebo.

    Creates elevation data for terrain generation using various patterns.
    Heightmaps are 2D arrays where each value represents ground elevation.

    Args:
        width: Heightmap width in pixels (must be power of 2 + 1, e.g., 129, 257, 513)
        height: Heightmap height in pixels (must be power of 2 + 1)
        pattern: Terrain pattern type:
            - 'flat': Flat terrain at min_elevation
            - 'ramp': Linear slope from min to max
            - 'hills': Rolling hills using sine waves
            - 'mountains': Mountain-like terrain with peaks
            - 'random': Random noise terrain
            - 'canyon': Valley with steep walls
        min_elevation: Minimum terrain height (meters)
        max_elevation: Maximum terrain height (meters)
        smoothness: Terrain smoothness factor (0.1-10.0):
            - < 1.0 = rougher, more detail
            - = 1.0 = balanced
            - > 1.0 = smoother, less detail
        seed: Random seed for reproducible terrain (optional)

    Returns:
        OperationResult with heightmap data and metadata

    Example:
        >>> # Generate rolling hills terrain
        >>> result = generate_heightmap_terrain(
        ...     width=129,
        ...     height=129,
        ...     pattern="hills",
        ...     min_elevation=0.0,
        ...     max_elevation=5.0
        ... )
        >>> if result.success:
        ...     heightmap = result.data["elevation_data"]
        ...     print(f"Generated {len(heightmap)}x{len(heightmap[0])} heightmap")
    """
    try:
        # Validate dimensions (must be power of 2 + 1 for Gazebo)
        width = int(validate_positive(width, "width"))
        height = int(validate_positive(height, "height"))

        def is_valid_size(n):
            """Check if n is of form 2^k + 1."""
            if n < 2:
                return False
            n_minus_1 = n - 1
            # Check if n-1 is power of 2
            return n_minus_1 > 0 and (n_minus_1 & (n_minus_1 - 1)) == 0

        if not is_valid_size(width):
            return error_result(
                error=f"width must be 2^n + 1 (e.g., 129, 257, 513), got {width}",
                error_code="INVALID_PARAMETER",
                suggestions=[
                    "Common sizes: 129 (2^7+1), 257 (2^8+1), 513 (2^9+1)",
                    "Smaller is faster but less detailed",
                ],
            )

        if not is_valid_size(height):
            return error_result(
                error=f"height must be 2^n + 1 (e.g., 129, 257, 513), got {height}",
                error_code="INVALID_PARAMETER",
                suggestions=[
                    "Common sizes: 129 (2^7+1), 257 (2^8+1), 513 (2^9+1)",
                    "Use same size for width and height for square terrain",
                ],
            )

        # Validate elevation range
        min_elevation = float(min_elevation)
        max_elevation = float(validate_positive(max_elevation, "max_elevation"))

        if min_elevation >= max_elevation:
            return error_result(
                error=f"min_elevation ({min_elevation}) must be < max_elevation ({max_elevation})",
                error_code="INVALID_PARAMETER",
            )

        # Validate smoothness
        smoothness = validate_positive(smoothness, "smoothness")
        if smoothness < 0.1 or smoothness > 10.0:
            return error_result(
                error="smoothness must be between 0.1 and 10.0",
                error_code="INVALID_PARAMETER",
                suggestions=["Use 0.5 for rough, 1.0 for balanced, 2.0 for smooth"],
            )

        # Validate pattern
        valid_patterns = ["flat", "ramp", "hills", "mountains", "random", "canyon"]
        pattern = pattern.lower()
        if pattern not in valid_patterns:
            return error_result(
                error=f"Unknown pattern: {pattern}",
                error_code="INVALID_PARAMETER",
                suggestions=[f"Valid patterns: {', '.join(valid_patterns)}"],
            )

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)

        # Generate heightmap based on pattern
        elevation_range = max_elevation - min_elevation

        if pattern == "flat":
            # Flat terrain at minimum elevation
            elevation_data = [[min_elevation for _ in range(width)] for _ in range(height)]

        elif pattern == "ramp":
            # Linear ramp from min to max elevation
            elevation_data = []
            for y in range(height):
                row = []
                progress = y / (height - 1)  # 0.0 to 1.0
                elevation = min_elevation + progress * elevation_range
                row = [elevation for _ in range(width)]
                elevation_data.append(row)

        elif pattern == "hills":
            # Rolling hills using sine waves
            elevation_data = []
            frequency = 2.0 * math.pi / (width * smoothness)
            for y in range(height):
                row = []
                for x in range(width):
                    # Combine multiple sine waves for natural hills
                    value = (
                        math.sin(x * frequency) * 0.4
                        + math.sin(y * frequency) * 0.4
                        + math.sin((x + y) * frequency * 0.7) * 0.2
                    )
                    # Normalize to [-1, 1] and scale to elevation range
                    elevation = min_elevation + (value + 1.0) * 0.5 * elevation_range
                    row.append(elevation)
                elevation_data.append(row)

        elif pattern == "mountains":
            # Mountain-like terrain with peaks
            elevation_data = []
            for y in range(height):
                row = []
                for x in range(width):
                    # Distance from center
                    cx = (x - width / 2) / width
                    cy = (y - height / 2) / height
                    dist = math.sqrt(cx * cx + cy * cy)

                    # Create peaks with noise
                    base = 1.0 - min(dist * 2.0, 1.0)  # Peak at center
                    noise = random.uniform(-0.2, 0.2) / smoothness

                    value = max(0.0, min(1.0, base + noise))
                    elevation = min_elevation + value * elevation_range
                    row.append(elevation)
                elevation_data.append(row)

        elif pattern == "random":
            # Random noise terrain
            elevation_data = []
            for y in range(height):
                row = []
                for x in range(width):
                    # Pure random noise
                    value = random.random()
                    elevation = min_elevation + value * elevation_range
                    row.append(elevation)
                elevation_data.append(row)

            # Apply smoothing if requested
            if smoothness > 1.0:
                # Simple box blur for smoothing
                smoothed = [[0.0 for _ in range(width)] for _ in range(height)]
                kernel_size = int(smoothness)
                for y in range(height):
                    for x in range(width):
                        total = 0.0
                        count = 0
                        for dy in range(-kernel_size, kernel_size + 1):
                            for dx in range(-kernel_size, kernel_size + 1):
                                ny = max(0, min(height - 1, y + dy))
                                nx = max(0, min(width - 1, x + dx))
                                total += elevation_data[ny][nx]
                                count += 1
                        smoothed[y][x] = total / count
                elevation_data = smoothed

        elif pattern == "canyon":
            # Valley with steep walls
            elevation_data = []
            for y in range(height):
                row = []
                for x in range(width):
                    # Distance from center line
                    center = width / 2
                    dist = abs(x - center) / center

                    # Steep walls with flat bottom
                    if dist < 0.3:
                        value = 0.0  # Flat valley floor
                    else:
                        value = (dist - 0.3) / 0.7  # Steep walls

                    elevation = min_elevation + value * elevation_range
                    row.append(elevation)
                elevation_data.append(row)

        # Calculate statistics
        all_elevations = [val for row in elevation_data for val in row]
        actual_min = min(all_elevations)
        actual_max = max(all_elevations)
        avg_elevation = sum(all_elevations) / len(all_elevations)

        _logger.info(
            f"Generated {width}x{height} heightmap with pattern '{pattern}' "
            f"(elevation range: {actual_min:.2f} to {actual_max:.2f}m)"
        )

        return success_result(
            {
                "elevation_data": elevation_data,
                "width": width,
                "height": height,
                "pattern": pattern,
                "min_elevation": actual_min,
                "max_elevation": actual_max,
                "avg_elevation": avg_elevation,
                "smoothness": smoothness,
                "seed": seed,
                "total_points": width * height,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "note": "Use this heightmap data with Gazebo heightmap terrain plugin",
                "example_sdf": f"""
<heightmap>
  <uri>file://path/to/heightmap.png</uri>
  <size>{width} {height} {max_elevation - min_elevation}</size>
  <pos>0 0 {(max_elevation + min_elevation) / 2}</pos>
  <texture>
    <diffuse>file://materials/textures/grass.jpg</diffuse>
    <normal>file://materials/textures/grass_normal.jpg</normal>
    <size>10</size>
  </texture>
</heightmap>
                """.strip(),
            }
        )

    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "HEIGHTMAP_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error generating heightmap", error=str(e))
        return error_result(
            error=f"Failed to generate heightmap: {e}",
            error_code="HEIGHTMAP_ERROR",
        )


# World Templates Library
WORLD_TEMPLATES = {
    "empty": {
        "name": "empty",
        "description": "Minimal empty world with just physics configuration",
        "parameters": {
            "include_ground_plane": False,
            "include_sun": False,
        },
    },
    "basic": {
        "name": "basic",
        "description": "Basic world with ground plane and sun lighting",
        "parameters": {
            "include_ground_plane": True,
            "include_sun": True,
        },
    },
    "with_ground": {
        "name": "with_ground",
        "description": "World with ground plane but no lighting (for custom lighting setups)",
        "parameters": {
            "include_ground_plane": True,
            "include_sun": False,
        },
    },
    "outdoor": {
        "name": "outdoor",
        "description": "Outdoor environment with realistic sun and ground plane",
        "parameters": {
            "include_ground_plane": True,
            "include_sun": True,
            "sun_intensity": 1.0,
        },
    },
}


def create_empty_world(
    world_name: str,
    include_ground_plane: bool = True,
    include_sun: bool = True,
    physics_step_size: float = 0.001,
    real_time_factor: float = 1.0,
) -> OperationResult:
    """
    Create an empty Gazebo world with basic configuration.
    
    Generates a complete SDF world file with physics, scene configuration,
    and optional ground plane and sun lighting.
    
    Args:
        world_name: Name for the world (must be non-empty)
        include_ground_plane: Include a flat ground plane model
        include_sun: Include directional sun lighting
        physics_step_size: Physics simulation step size in seconds (default: 0.001)
        real_time_factor: Target real-time factor (default: 1.0)
        
    Returns:
        OperationResult with world SDF content and metadata
        
    Example:
        >>> result = create_empty_world(
        ...     "my_test_world",
        ...     include_ground_plane=True,
        ...     include_sun=True
        ... )
        >>> if result.success:
        ...     print(result.data["world_name"])
        ...     # Save to file:
        ...     save_world("my_test_world", result.data["sdf_content"], "my_world.sdf")
    """
    try:
        # Validation
        validate_entity_name(world_name)
        validate_positive(physics_step_size, "physics_step_size")
        validate_positive(real_time_factor, "real_time_factor")
        
        if not world_name or not world_name.strip():
            raise InvalidParameterError("world_name", world_name, "World name cannot be empty")
        
        # Generate SDF world file
        sdf_parts = []
        
        # XML declaration and SDF opening
        sdf_parts.append('<?xml version="1.0"?>')
        sdf_parts.append('<sdf version="1.7">')
        sdf_parts.append(f'  <world name="{world_name}">')
        
        # Physics configuration
        sdf_parts.append('    <physics type="ode">')
        sdf_parts.append(f'      <max_step_size>{physics_step_size}</max_step_size>')
        sdf_parts.append(f'      <real_time_factor>{real_time_factor}</real_time_factor>')
        sdf_parts.append(f'      <real_time_update_rate>{1.0/physics_step_size}</real_time_update_rate>')
        sdf_parts.append('      <gravity>0 0 -9.8</gravity>')
        sdf_parts.append('    </physics>')
        
        # Scene configuration
        sdf_parts.append('    <scene>')
        sdf_parts.append('      <ambient>0.4 0.4 0.4 1.0</ambient>')
        sdf_parts.append('      <background>0.7 0.7 0.7 1.0</background>')
        sdf_parts.append('      <shadows>true</shadows>')
        sdf_parts.append('      <grid>false</grid>')
        sdf_parts.append('    </scene>')
        
        # Ground plane (optional)
        if include_ground_plane:
            sdf_parts.append('    <model name="ground_plane">')
            sdf_parts.append('      <static>true</static>')
            sdf_parts.append('      <link name="link">')
            sdf_parts.append('        <collision name="collision">')
            sdf_parts.append('          <geometry>')
            sdf_parts.append('            <plane>')
            sdf_parts.append('              <normal>0 0 1</normal>')
            sdf_parts.append('              <size>100 100</size>')
            sdf_parts.append('            </plane>')
            sdf_parts.append('          </geometry>')
            sdf_parts.append('          <surface>')
            sdf_parts.append('            <friction>')
            sdf_parts.append('              <ode>')
            sdf_parts.append('                <mu>0.8</mu>')
            sdf_parts.append('                <mu2>0.8</mu2>')
            sdf_parts.append('              </ode>')
            sdf_parts.append('            </friction>')
            sdf_parts.append('          </surface>')
            sdf_parts.append('        </collision>')
            sdf_parts.append('        <visual name="visual">')
            sdf_parts.append('          <geometry>')
            sdf_parts.append('            <plane>')
            sdf_parts.append('              <normal>0 0 1</normal>')
            sdf_parts.append('              <size>100 100</size>')
            sdf_parts.append('            </plane>')
            sdf_parts.append('          </geometry>')
            sdf_parts.append('          <material>')
            sdf_parts.append('            <ambient>0.2 0.8 0.2 1</ambient>')
            sdf_parts.append('            <diffuse>0.2 0.8 0.2 1</diffuse>')
            sdf_parts.append('            <specular>0.1 0.1 0.1 1</specular>')
            sdf_parts.append('          </material>')
            sdf_parts.append('        </visual>')
            sdf_parts.append('      </link>')
            sdf_parts.append('    </model>')
        
        # Sun lighting (optional)
        if include_sun:
            sdf_parts.append('    <light name="sun" type="directional">')
            sdf_parts.append('      <cast_shadows>true</cast_shadows>')
            sdf_parts.append('      <pose>0 0 10 0 0 0</pose>')
            sdf_parts.append('      <diffuse>1.0 1.0 1.0 1</diffuse>')
            sdf_parts.append('      <specular>0.2 0.2 0.2 1</specular>')
            sdf_parts.append('      <direction>-0.5 0.1 -0.9</direction>')
            sdf_parts.append('      <attenuation>')
            sdf_parts.append('        <range>1000</range>')
            sdf_parts.append('        <constant>0.9</constant>')
            sdf_parts.append('        <linear>0.01</linear>')
            sdf_parts.append('        <quadratic>0.001</quadratic>')
            sdf_parts.append('      </attenuation>')
            sdf_parts.append('    </light>')
        
        # Close tags
        sdf_parts.append('  </world>')
        sdf_parts.append('</sdf>')
        
        sdf_content = '\n'.join(sdf_parts)
        
        _logger.info(f"Created empty world: {world_name}", 
                    ground_plane=include_ground_plane, sun=include_sun)
        
        return success_result({
            "world_name": world_name,
            "sdf_content": sdf_content,
            "include_ground_plane": include_ground_plane,
            "include_sun": include_sun,
            "physics_step_size": physics_step_size,
            "real_time_factor": real_time_factor,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Use save_world() to write this world to a file, or spawn models directly"
        })
        
    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "WORLD_CREATION_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error creating world", error=str(e))
        return error_result(
            error=f"Failed to create world: {e}",
            error_code="WORLD_CREATION_ERROR"
        )


def save_world(
    world_name: str,
    sdf_content: str,
    file_path: str,
) -> OperationResult:
    """
    Save world SDF content to a file.
    
    Creates parent directories if they don't exist. Validates SDF content
    before writing to ensure it's well-formed XML.
    
    Args:
        world_name: Name of the world (for logging)
        sdf_content: Complete SDF XML content
        file_path: Path where to save the file (absolute or relative)
        
    Returns:
        OperationResult with file path and save status
        
    Example:
        >>> # Create world first
        >>> result = create_empty_world("my_world")
        >>> # Save to file
        >>> save_result = save_world(
        ...     "my_world",
        ...     result.data["sdf_content"],
        ...     "worlds/my_world.sdf"
        ... )
        >>> print(save_result.data["file_path"])
    """
    try:
        # Validation
        validate_entity_name(world_name)
        
        if not sdf_content or not sdf_content.strip():
            raise InvalidParameterError("sdf_content", "", "SDF content cannot be empty")
        
        # Basic XML validation
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(sdf_content)
        except ET.ParseError as e:
            raise InvalidParameterError("sdf_content", sdf_content[:100], 
                                      f"Invalid XML: {e}")
        
        # Create parent directories
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        path.write_text(sdf_content, encoding='utf-8')
        
        _logger.info(f"Saved world to file", world=world_name, path=str(path))
        
        return success_result({
            "world_name": world_name,
            "file_path": str(path.absolute()),
            "file_size_bytes": len(sdf_content.encode('utf-8')),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "WORLD_SAVE_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error saving world", error=str(e))
        return error_result(
            error=f"Failed to save world: {e}",
            error_code="WORLD_SAVE_ERROR"
        )


def load_world(file_path: str) -> OperationResult:
    """
    Load world SDF content from a file.
    
    Reads and validates SDF file, extracting world name from content.
    
    Args:
        file_path: Path to the world SDF file
        
    Returns:
        OperationResult with SDF content and world metadata
        
    Example:
        >>> result = load_world("worlds/my_world.sdf")
        >>> if result.success:
        ...     print(f"Loaded world: {result.data['world_name']}")
        ...     # Use the SDF content
        ...     sdf = result.data['sdf_content']
    """
    try:
        # Check file exists
        path = Path(file_path)
        if not path.exists():
            return error_result(
                error=f"World file not found: {file_path}",
                error_code="FILE_NOT_FOUND"
            )
        
        # Read file
        sdf_content = path.read_text(encoding='utf-8')
        
        # Parse and validate XML
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(sdf_content)
        except ET.ParseError as e:
            return error_result(
                error=f"Invalid SDF XML: {e}",
                error_code="INVALID_SDF"
            )
        
        # Extract world name
        world_elem = root.find('.//world')
        if world_elem is None:
            return error_result(
                error="No <world> element found in SDF",
                error_code="INVALID_SDF"
            )
        
        world_name = world_elem.get('name', 'unknown')
        
        _logger.info(f"Loaded world from file", world=world_name, path=str(path))
        
        return success_result({
            "world_name": world_name,
            "sdf_content": sdf_content,
            "file_path": str(path.absolute()),
            "file_size_bytes": len(sdf_content.encode('utf-8')),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        _logger.exception("Unexpected error loading world", error=str(e))
        return error_result(
            error=f"Failed to load world: {e}",
            error_code="WORLD_LOAD_ERROR"
        )


def list_world_templates() -> OperationResult:
    """
    List available world templates.
    
    Returns information about built-in world templates that can be used
    with create_empty_world() or as starting points for custom worlds.
    
    Returns:
        OperationResult with list of available templates
        
    Example:
        >>> result = list_world_templates()
        >>> for template in result.data["templates"]:
        ...     print(f"{template['name']}: {template['description']}")
        ...     print(f"  Parameters: {template.get('parameters', {})}")
    """
    try:
        templates = []
        for template_name, template_info in WORLD_TEMPLATES.items():
            templates.append({
                "name": template_info["name"],
                "description": template_info["description"],
                "parameters": template_info.get("parameters", {}),
            })
        
        return success_result({
            "templates": templates,
            "count": len(templates),
            "note": "Use these templates as starting points for create_empty_world()"
        })
        
    except Exception as e:
        _logger.exception("Unexpected error listing templates", error=str(e))
        return error_result(
            error=f"Failed to list templates: {e}",
            error_code="TEMPLATE_LIST_ERROR"
        )


def _generate_primitive_sdf(
    name: str,
    shape_type: str,
    position: Tuple[float, float, float],
    shape_params: Dict[str, float],
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
) -> str:
    """
    Generate SDF for primitive shape (box, sphere, cylinder).
    
    Helper function for object placement.
    
    Args:
        name: Model name
        shape_type: 'box', 'sphere', or 'cylinder'
        position: (x, y, z) position
        shape_params: Shape-specific parameters
        color: RGBA color dict (default: gray)
        static: Whether object is static (no physics)
        
    Returns:
        Complete SDF XML string
    """
    # Default color (gray)
    if color is None:
        color = {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0}
    
    color_str = f"{color['r']} {color['g']} {color['b']} {color['a']}"
    
    # Generate geometry XML based on shape type
    if shape_type == "box":
        geometry_xml = f"""
            <box>
              <size>{shape_params['width']} {shape_params['depth']} {shape_params['height']}</size>
            </box>"""
    elif shape_type == "sphere":
        geometry_xml = f"""
            <sphere>
              <radius>{shape_params['radius']}</radius>
            </sphere>"""
    elif shape_type == "cylinder":
        geometry_xml = f"""
            <cylinder>
              <radius>{shape_params['radius']}</radius>
              <length>{shape_params['length']}</length>
            </cylinder>"""
    else:
        raise InvalidParameterError("shape_type", shape_type, 
                                   "Must be 'box', 'sphere', or 'cylinder'")
    
    # Build complete SDF
    sdf_parts = []
    sdf_parts.append('<?xml version="1.0"?>')
    sdf_parts.append('<sdf version="1.7">')
    sdf_parts.append(f'  <model name="{name}">')
    
    if static:
        sdf_parts.append('    <static>true</static>')
    else:
        sdf_parts.append('    <static>false</static>')
    
    sdf_parts.append(f'    <pose>{position[0]} {position[1]} {position[2]} 0 0 0</pose>')
    sdf_parts.append('    <link name="link">')
    
    # Collision
    sdf_parts.append('      <collision name="collision">')
    sdf_parts.append('        <geometry>')
    sdf_parts.append(f'          {geometry_xml.strip()}')
    sdf_parts.append('        </geometry>')
    
    if not static:
        # Add surface properties for dynamic objects
        sdf_parts.append('        <surface>')
        sdf_parts.append('          <friction>')
        sdf_parts.append('            <ode>')
        sdf_parts.append('              <mu>0.8</mu>')
        sdf_parts.append('              <mu2>0.8</mu2>')
        sdf_parts.append('            </ode>')
        sdf_parts.append('          </friction>')
        sdf_parts.append('        </surface>')
    
    sdf_parts.append('      </collision>')
    
    # Visual
    sdf_parts.append('      <visual name="visual">')
    sdf_parts.append('        <geometry>')
    sdf_parts.append(f'          {geometry_xml.strip()}')
    sdf_parts.append('        </geometry>')
    sdf_parts.append('        <material>')
    sdf_parts.append(f'          <ambient>{color_str}</ambient>')
    sdf_parts.append(f'          <diffuse>{color_str}</diffuse>')
    sdf_parts.append(f'          <specular>0.1 0.1 0.1 1</specular>')
    sdf_parts.append('        </material>')
    sdf_parts.append('      </visual>')
    
    if not static:
        # Add inertial properties for dynamic objects
        sdf_parts.append('      <inertial>')
        sdf_parts.append('        <mass>1.0</mass>')
        sdf_parts.append('        <inertia>')
        sdf_parts.append('          <ixx>0.1</ixx>')
        sdf_parts.append('          <ixy>0</ixy>')
        sdf_parts.append('          <ixz>0</ixz>')
        sdf_parts.append('          <iyy>0.1</iyy>')
        sdf_parts.append('          <iyz>0</iyz>')
        sdf_parts.append('          <izz>0.1</izz>')
        sdf_parts.append('        </inertia>')
        sdf_parts.append('      </inertial>')
    
    sdf_parts.append('    </link>')
    sdf_parts.append('  </model>')
    sdf_parts.append('</sdf>')
    
    return '\n'.join(sdf_parts)


def place_box(
    name: str,
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    depth: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
) -> OperationResult:
    """
    Place a box obstacle in the world.
    
    Generates SDF for a box-shaped object that can be spawned in Gazebo.
    Use with spawn_entity() from model_management to add to running simulation.
    
    Args:
        name: Unique name for the box
        x: X position in meters
        y: Y position in meters
        z: Z position in meters (typically half the height for ground placement)
        width: Width (X dimension) in meters
        height: Height (Z dimension) in meters
        depth: Depth (Y dimension) in meters
        color: RGBA color dict with keys 'r', 'g', 'b', 'a' (0-1 range)
        static: If True, box is static (no physics). If False, box has physics.
        
    Returns:
        OperationResult with SDF content ready for spawning
        
    Example:
        >>> # Create a red box obstacle
        >>> result = place_box(
        ...     name="red_obstacle",
        ...     x=2.0, y=0.0, z=0.5,
        ...     width=1.0, height=1.0, depth=1.0,
        ...     color={"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        ...     static=True
        ... )
        >>> # Spawn in Gazebo
        >>> from gazebo_mcp.tools.model_management import spawn_model
        >>> spawn_model("red_obstacle", result.data["sdf_content"])
    """
    try:
        # Validation
        validate_entity_name(name)
        validate_position(x, y, z)
        validate_positive(width, "width")
        validate_positive(height, "height")
        validate_positive(depth, "depth")
        
        # Generate SDF
        sdf_content = _generate_primitive_sdf(
            name=name,
            shape_type="box",
            position=(x, y, z),
            shape_params={"width": width, "height": height, "depth": depth},
            color=color,
            static=static
        )
        
        _logger.info(f"Generated box SDF", name=name, static=static)
        
        return success_result({
            "name": name,
            "sdf_content": sdf_content,
            "shape_type": "box",
            "position": {"x": x, "y": y, "z": z},
            "dimensions": {"width": width, "height": height, "depth": depth},
            "static": static,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Use spawn_model() to add this box to the running simulation"
        })
        
    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "BOX_PLACEMENT_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error placing box", error=str(e))
        return error_result(
            error=f"Failed to place box: {e}",
            error_code="BOX_PLACEMENT_ERROR"
        )


def place_sphere(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
) -> OperationResult:
    """
    Place a sphere obstacle in the world.
    
    Generates SDF for a spherical object that can be spawned in Gazebo.
    
    Args:
        name: Unique name for the sphere
        x: X position in meters
        y: Y position in meters
        z: Z position in meters (typically radius for ground placement)
        radius: Sphere radius in meters
        color: RGBA color dict with keys 'r', 'g', 'b', 'a' (0-1 range)
        static: If True, sphere is static (no physics). If False, sphere has physics.
        
    Returns:
        OperationResult with SDF content ready for spawning
        
    Example:
        >>> # Create a green sphere
        >>> result = place_sphere(
        ...     name="green_ball",
        ...     x=1.0, y=1.0, z=0.5,
        ...     radius=0.5,
        ...     color={"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0},
        ...     static=False  # Dynamic (rolls)
        ... )
        >>> # Spawn in Gazebo
        >>> spawn_model("green_ball", result.data["sdf_content"])
    """
    try:
        # Validation
        validate_entity_name(name)
        validate_position(x, y, z)
        validate_positive(radius, "radius")
        
        # Generate SDF
        sdf_content = _generate_primitive_sdf(
            name=name,
            shape_type="sphere",
            position=(x, y, z),
            shape_params={"radius": radius},
            color=color,
            static=static
        )
        
        _logger.info(f"Generated sphere SDF", name=name, static=static)
        
        return success_result({
            "name": name,
            "sdf_content": sdf_content,
            "shape_type": "sphere",
            "position": {"x": x, "y": y, "z": z},
            "radius": radius,
            "static": static,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Use spawn_model() to add this sphere to the running simulation"
        })
        
    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "SPHERE_PLACEMENT_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error placing sphere", error=str(e))
        return error_result(
            error=f"Failed to place sphere: {e}",
            error_code="SPHERE_PLACEMENT_ERROR"
        )


def place_cylinder(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    length: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
) -> OperationResult:
    """
    Place a cylinder obstacle in the world.
    
    Generates SDF for a cylindrical object that can be spawned in Gazebo.
    Cylinder is oriented vertically (along Z axis).
    
    Args:
        name: Unique name for the cylinder
        x: X position in meters
        y: Y position in meters
        z: Z position in meters (typically length/2 for ground placement)
        radius: Cylinder radius in meters
        length: Cylinder length/height in meters
        color: RGBA color dict with keys 'r', 'g', 'b', 'a' (0-1 range)
        static: If True, cylinder is static (no physics). If False, has physics.
        
    Returns:
        OperationResult with SDF content ready for spawning
        
    Example:
        >>> # Create a blue cylinder pillar
        >>> result = place_cylinder(
        ...     name="pillar",
        ...     x=0.0, y=0.0, z=1.0,
        ...     radius=0.2,
        ...     length=2.0,
        ...     color={"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0},
        ...     static=True
        ... )
        >>> # Spawn in Gazebo
        >>> spawn_model("pillar", result.data["sdf_content"])
    """
    try:
        # Validation
        validate_entity_name(name)
        validate_position(x, y, z)
        validate_positive(radius, "radius")
        validate_positive(length, "length")
        
        # Generate SDF
        sdf_content = _generate_primitive_sdf(
            name=name,
            shape_type="cylinder",
            position=(x, y, z),
            shape_params={"radius": radius, "length": length},
            color=color,
            static=static
        )
        
        _logger.info(f"Generated cylinder SDF", name=name, static=static)
        
        return success_result({
            "name": name,
            "sdf_content": sdf_content,
            "shape_type": "cylinder",
            "position": {"x": x, "y": y, "z": z},
            "radius": radius,
            "length": length,
            "static": static,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "Use spawn_model() to add this cylinder to the running simulation"
        })
        
    except (InvalidParameterError, GazeboMCPError) as e:
        return error_result(error=str(e), error_code=getattr(e, "error_code", "CYLINDER_PLACEMENT_ERROR"))
    except Exception as e:
        _logger.exception("Unexpected error placing cylinder", error=str(e))
        return error_result(
            error=f"Failed to place cylinder: {e}",
            error_code="CYLINDER_PLACEMENT_ERROR"
        )


# ============================================================================
# Gazebo Bridge Integration - Spawning Functions
# ============================================================================


def _get_bridge():
    """
    Get or create Gazebo bridge node for spawning.

    Lazy initialization with auto-connection following the singleton pattern
    from model_management.py.

    Returns:
        GazeboBridgeNode instance

    Raises:
        ROS2NotConnectedError: If connection fails
    """
    global _connection_manager, _bridge_node

    if _bridge_node is not None:
        return _bridge_node

    try:
        # Import here to avoid circular dependencies
        from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

        # Create connection manager if needed
        if _connection_manager is None:
            _connection_manager = ConnectionManager()
            _connection_manager.connect(timeout=10.0)
            _logger.info("Connected to ROS2 for world generation spawning")

        # Create bridge node
        _bridge_node = GazeboBridgeNode(_connection_manager.get_node())
        _logger.info("Created Gazebo bridge node for spawning")

        return _bridge_node

    except Exception as e:
        _logger.error(f"Failed to create bridge", error=str(e))
        raise ROS2NotConnectedError(f"Failed to connect to ROS2/Gazebo: {e}") from e


def spawn_box(
    name: str,
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    depth: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
    timeout: float = 10.0
) -> OperationResult:
    """
    Generate box SDF and spawn it in Gazebo simulation.

    Combines SDF generation (place_box) with Gazebo spawning via bridge.

    Args:
        name: Unique entity name
        x, y, z: Position coordinates (meters)
        width: Box width (x-axis, meters)
        height: Box height (z-axis, meters)
        depth: Box depth (y-axis, meters)
        color: Optional RGBA color dict {"r": 0-1, "g": 0-1, "b": 0-1, "a": 0-1}
        static: If True, object is fixed in place; if False, physics-enabled
        timeout: Spawn service call timeout (seconds)

    Returns:
        OperationResult with spawn status and entity info

    Example:
        >>> # Spawn a red box obstacle
        >>> result = spawn_box(
        ...     name="red_obstacle",
        ...     x=2.0, y=1.0, z=0.5,
        ...     width=1.0, height=1.0, depth=1.0,
        ...     color={"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
        ...     static=True
        ... )
        >>> if result.success:
        ...     print(f"Spawned {result.data['name']} at position {result.data['position']}")
        ... else:
        ...     print(f"Spawn failed: {result.error}")
    """
    try:
        # Step 1: Generate SDF using place_box
        gen_result = place_box(name, x, y, z, width, height, depth, color, static)

        if not gen_result.success:
            return gen_result  # Return generation error

        sdf_content = gen_result.data["sdf_content"]

        # Step 2: Get bridge and spawn entity
        bridge = _get_bridge()

        # Create pose dict
        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }

        # Spawn in Gazebo
        success = bridge.spawn_entity(
            name=name,
            xml_content=sdf_content,
            pose=pose,
            reference_frame="world",
            timeout=timeout
        )

        if success:
            _logger.info(f"Spawned box in Gazebo", name=name, position={"x": x, "y": y, "z": z})
            return success_result({
                "name": name,
                "spawned": True,
                "shape_type": "box",
                "position": {"x": x, "y": y, "z": z},
                "dimensions": {"width": width, "height": height, "depth": depth},
                "static": static,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to spawn box '{name}' in Gazebo",
                error_code="SPAWN_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced: source /opt/ros/humble/setup.bash",
                "Start Gazebo simulation before spawning",
                "Check ROS2 node connectivity: ros2 node list"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error spawning box", error=str(e))
        return error_result(
            error=f"Failed to spawn box: {e}",
            error_code="SPAWN_ERROR"
        )


def spawn_sphere(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
    timeout: float = 10.0
) -> OperationResult:
    """
    Generate sphere SDF and spawn it in Gazebo simulation.

    Args:
        name: Unique entity name
        x, y, z: Position coordinates (meters)
        radius: Sphere radius (meters)
        color: Optional RGBA color dict
        static: If True, fixed; if False, physics-enabled (will roll!)
        timeout: Spawn service call timeout (seconds)

    Returns:
        OperationResult with spawn status

    Example:
        >>> # Spawn a dynamic green ball that will roll
        >>> result = spawn_sphere(
        ...     name="rolling_ball",
        ...     x=1.0, y=1.0, z=1.0,
        ...     radius=0.5,
        ...     color={"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0},
        ...     static=False  # Physics enabled!
        ... )
    """
    try:
        # Step 1: Generate SDF
        gen_result = place_sphere(name, x, y, z, radius, color, static)

        if not gen_result.success:
            return gen_result

        sdf_content = gen_result.data["sdf_content"]

        # Step 2: Spawn in Gazebo
        bridge = _get_bridge()

        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }

        success = bridge.spawn_entity(
            name=name,
            xml_content=sdf_content,
            pose=pose,
            reference_frame="world",
            timeout=timeout
        )

        if success:
            _logger.info(f"Spawned sphere in Gazebo", name=name, radius=radius)
            return success_result({
                "name": name,
                "spawned": True,
                "shape_type": "sphere",
                "position": {"x": x, "y": y, "z": z},
                "radius": radius,
                "static": static,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to spawn sphere '{name}' in Gazebo",
                error_code="SPAWN_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error spawning sphere", error=str(e))
        return error_result(
            error=f"Failed to spawn sphere: {e}",
            error_code="SPAWN_ERROR"
        )


def spawn_cylinder(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    length: float,
    color: Optional[Dict[str, float]] = None,
    static: bool = True,
    timeout: float = 10.0
) -> OperationResult:
    """
    Generate cylinder SDF and spawn it in Gazebo simulation.

    Args:
        name: Unique entity name
        x, y, z: Position coordinates (meters)
        radius: Cylinder radius (meters)
        length: Cylinder length along z-axis (meters)
        color: Optional RGBA color dict
        static: If True, fixed; if False, physics-enabled
        timeout: Spawn service call timeout (seconds)

    Returns:
        OperationResult with spawn status

    Example:
        >>> # Spawn a blue pillar
        >>> result = spawn_cylinder(
        ...     name="pillar_1",
        ...     x=3.0, y=0.0, z=1.0,
        ...     radius=0.2,
        ...     length=2.0,
        ...     color={"r": 0.0, "g": 0.0, "b": 1.0, "a": 1.0}
        ... )
    """
    try:
        # Step 1: Generate SDF
        gen_result = place_cylinder(name, x, y, z, radius, length, color, static)

        if not gen_result.success:
            return gen_result

        sdf_content = gen_result.data["sdf_content"]

        # Step 2: Spawn in Gazebo
        bridge = _get_bridge()

        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }

        success = bridge.spawn_entity(
            name=name,
            xml_content=sdf_content,
            pose=pose,
            reference_frame="world",
            timeout=timeout
        )

        if success:
            _logger.info(f"Spawned cylinder in Gazebo", name=name, radius=radius, length=length)
            return success_result({
                "name": name,
                "spawned": True,
                "shape_type": "cylinder",
                "position": {"x": x, "y": y, "z": z},
                "radius": radius,
                "length": length,
                "static": static,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to spawn cylinder '{name}' in Gazebo",
                error_code="SPAWN_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error spawning cylinder", error=str(e))
        return error_result(
            error=f"Failed to spawn cylinder: {e}",
            error_code="SPAWN_ERROR"
        )


# ============================================================================
# Live Physics Updates
# ============================================================================


def apply_force(
    model_name: str,
    force_x: float,
    force_y: float,
    force_z: float,
    duration: Optional[float] = None,
    timeout: float = 10.0
) -> OperationResult:
    """
    Apply force to a model in Gazebo simulation.

    Applies force by setting the model's linear velocity. This simulates
    the effect of a force impulse on the object.

    Note: For realistic physics, consider the model's mass when determining
    force magnitude. Higher forces will result in higher velocities.

    Args:
        model_name: Name of the model to apply force to
        force_x, force_y, force_z: Force components (Newtons approximation)
        duration: Force duration in seconds (None = instantaneous impulse)
        timeout: Service call timeout

    Returns:
        OperationResult with force application status

    Example:
        >>> # Apply horizontal force to push object forward
        >>> result = apply_force(
        ...     model_name="box_1",
        ...     force_x=10.0,  # Forward force
        ...     force_y=0.0,
        ...     force_z=0.0,
        ...     duration=1.0   # Apply for 1 second
        ... )
        >>> if result.success:
        ...     print("Force applied successfully")
    """
    try:
        # Validate parameters
        validate_entity_name(model_name)

        # Get bridge
        bridge = _get_bridge()

        # Convert force to velocity (F = ma, assuming unit mass for simplicity)
        # In real physics, you'd divide by mass: v = F/m * dt
        # Here we approximate with direct force-to-velocity mapping
        velocity_scale = 0.1  # Scaling factor to prevent excessive velocities

        twist = {
            "linear": {
                "x": force_x * velocity_scale,
                "y": force_y * velocity_scale,
                "z": force_z * velocity_scale
            },
            "angular": {"x": 0.0, "y": 0.0, "z": 0.0}
        }

        # Apply velocity (simulates force)
        success = bridge.set_entity_state(
            name=model_name,
            twist=twist,
            timeout=timeout
        )

        if success:
            _logger.info(
                f"Applied force to model",
                model=model_name,
                force={"x": force_x, "y": force_y, "z": force_z}
            )

            return success_result({
                "model_name": model_name,
                "force_applied": True,
                "force": {"x": force_x, "y": force_y, "z": force_z},
                "duration": duration,
                "method": "velocity_impulse",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "note": "Force applied as velocity impulse (F~v approximation)"
            })
        else:
            return error_result(
                error=f"Failed to apply force to '{model_name}'",
                error_code="FORCE_APPLICATION_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error applying force", error=str(e))
        return error_result(
            error=f"Failed to apply force: {e}",
            error_code="FORCE_APPLICATION_ERROR"
        )


def apply_torque(
    model_name: str,
    torque_x: float,
    torque_y: float,
    torque_z: float,
    duration: Optional[float] = None,
    timeout: float = 10.0
) -> OperationResult:
    """
    Apply torque to a model in Gazebo simulation.

    Applies rotational force by setting the model's angular velocity.
    This simulates the effect of a torque impulse on the object.

    Args:
        model_name: Name of the model to apply torque to
        torque_x, torque_y, torque_z: Torque components (Newton-meters approximation)
        duration: Torque duration in seconds (None = instantaneous)
        timeout: Service call timeout

    Returns:
        OperationResult with torque application status

    Example:
        >>> # Spin a sphere around Z-axis
        >>> result = apply_torque(
        ...     model_name="sphere_1",
        ...     torque_x=0.0,
        ...     torque_y=0.0,
        ...     torque_z=5.0,  # Spin counterclockwise
        ...     duration=2.0
        ... )
        >>> if result.success:
        ...     print("Torque applied - object is spinning!")
    """
    try:
        # Validate parameters
        validate_entity_name(model_name)

        # Get bridge
        bridge = _get_bridge()

        # Convert torque to angular velocity (τ = Iα, assuming unit inertia)
        angular_velocity_scale = 0.1  # Scaling factor

        twist = {
            "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
            "angular": {
                "x": torque_x * angular_velocity_scale,
                "y": torque_y * angular_velocity_scale,
                "z": torque_z * angular_velocity_scale
            }
        }

        # Apply angular velocity (simulates torque)
        success = bridge.set_entity_state(
            name=model_name,
            twist=twist,
            timeout=timeout
        )

        if success:
            _logger.info(
                f"Applied torque to model",
                model=model_name,
                torque={"x": torque_x, "y": torque_y, "z": torque_z}
            )

            return success_result({
                "model_name": model_name,
                "torque_applied": True,
                "torque": {"x": torque_x, "y": torque_y, "z": torque_z},
                "duration": duration,
                "method": "angular_velocity_impulse",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "note": "Torque applied as angular velocity impulse (τ~ω approximation)"
            })
        else:
            return error_result(
                error=f"Failed to apply torque to '{model_name}'",
                error_code="TORQUE_APPLICATION_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error applying torque", error=str(e))
        return error_result(
            error=f"Failed to apply torque: {e}",
            error_code="TORQUE_APPLICATION_ERROR"
        )


def set_wind(
    linear_x: float,
    linear_y: float,
    linear_z: float = 0.0
) -> OperationResult:
    """
    Configure global wind settings for the simulation.

    Note: This function generates wind configuration but does not directly
    apply it to a running simulation. Wind in Gazebo requires physics plugin
    configuration in the world file.

    This function provides the configuration and instructions for setting up wind.

    Args:
        linear_x: Wind velocity in X direction (m/s)
        linear_y: Wind velocity in Y direction (m/s)
        linear_z: Wind velocity in Z direction (m/s, usually 0)

    Returns:
        OperationResult with wind configuration and setup instructions

    Example:
        >>> # Configure eastward wind at 2 m/s
        >>> result = set_wind(
        ...     linear_x=2.0,
        ...     linear_y=0.0,
        ...     linear_z=0.0
        ... )
        >>> if result.success:
        ...     print("Wind configuration:")
        ...     print(result.data["plugin_instructions"])
    """
    try:
        # Create wind configuration
        wind_config = {
            "linear": {
                "x": float(linear_x),
                "y": float(linear_y),
                "z": float(linear_z)
            }
        }

        # Calculate wind speed and direction
        import math
        wind_speed = math.sqrt(linear_x**2 + linear_y**2 + linear_z**2)
        if wind_speed > 0:
            wind_direction_deg = math.degrees(math.atan2(linear_y, linear_x))
        else:
            wind_direction_deg = 0.0

        # Generate plugin XML configuration
        plugin_xml = f"""
<!-- Add this to your world SDF file inside <world> tag -->
<plugin name="wind_plugin" filename="libWindPlugin.so">
  <horizontal>
    <magnitude>{wind_speed:.2f}</magnitude>
    <direction>{wind_direction_deg:.2f}</direction>
  </horizontal>
  <vertical>{linear_z:.2f}</vertical>
</plugin>
"""

        # Generate instructions
        instructions = [
            "Wind in Gazebo requires physics plugin configuration",
            "Add the wind plugin to your world SDF file",
            "Plugin affects all non-static models with aerodynamic properties",
            f"Current wind: {wind_speed:.2f} m/s at {wind_direction_deg:.1f}°",
        ]

        if wind_speed == 0:
            instructions.append("Note: Zero wind configured (calm conditions)")

        _logger.info(
            f"Generated wind configuration",
            speed=wind_speed,
            direction=wind_direction_deg
        )

        return success_result({
            "wind_config": wind_config,
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": wind_direction_deg,
            "plugin_xml": plugin_xml.strip(),
            "plugin_instructions": instructions,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "usage_example": """
# To use this wind configuration:
# 1. Save wind plugin XML to your world file
# 2. Ensure Gazebo wind plugin is installed
# 3. Restart simulation with updated world file
# 4. Wind will affect all dynamic objects
"""
        })

    except Exception as e:
        _logger.exception("Unexpected error configuring wind", error=str(e))
        return error_result(
            error=f"Failed to configure wind: {e}",
            error_code="WIND_CONFIGURATION_ERROR"
        )


# ============================================================================
# Dynamic Lighting Control
# ============================================================================


def spawn_light(
    name: str,
    light_type: str,
    position: Dict[str, float],
    direction: Optional[Dict[str, float]] = None,
    diffuse: Optional[Dict[str, float]] = None,
    specular: Optional[Dict[str, float]] = None,
    attenuation_range: float = 10.0,
    attenuation_constant: float = 1.0,
    attenuation_linear: float = 0.0,
    attenuation_quadratic: float = 0.0,
    cast_shadows: bool = True,
    spot_inner_angle: float = 0.0,
    spot_outer_angle: float = 0.0,
    spot_falloff: float = 0.0,
    timeout: float = 10.0
) -> OperationResult:
    """
    Generate light SDF and spawn it in Gazebo simulation.

    Supports three light types:
    - **directional**: Sun-like parallel light (requires direction)
    - **point**: Omnidirectional bulb-like light
    - **spot**: Flashlight-like cone of light (requires direction and angles)

    Args:
        name: Unique light name
        light_type: "directional", "point", or "spot"
        position: Light position {"x": float, "y": float, "z": float}
        direction: Light direction (required for directional/spot)
        diffuse: Diffuse color {"r": 0-1, "g": 0-1, "b": 0-1, "a": 0-1}
        specular: Specular color (defaults to diffuse)
        attenuation_range: Maximum light distance (point/spot only)
        attenuation_constant: Constant attenuation factor
        attenuation_linear: Linear attenuation factor
        attenuation_quadratic: Quadratic attenuation factor
        cast_shadows: Whether light casts shadows
        spot_inner_angle: Inner cone angle in radians (spot only)
        spot_outer_angle: Outer cone angle in radians (spot only)
        spot_falloff: Light falloff exponent (spot only)
        timeout: Spawn timeout

    Returns:
        OperationResult with spawn status

    Example:
        >>> # Spawn a warm point light (lamp)
        >>> result = spawn_light(
        ...     name="lamp_1",
        ...     light_type="point",
        ...     position={"x": 2, "y": 2, "z": 3},
        ...     diffuse={"r": 1.0, "g": 0.8, "b": 0.6, "a": 1.0},
        ...     attenuation_range=10.0
        ... )
        >>>
        >>> # Spawn a spotlight
        >>> result = spawn_light(
        ...     name="spotlight_1",
        ...     light_type="spot",
        ...     position={"x": 0, "y": 0, "z": 5},
        ...     direction={"x": 0, "y": 0, "z": -1},
        ...     spot_inner_angle=0.5,
        ...     spot_outer_angle=1.0
        ... )
    """
    try:
        # Validate parameters
        validate_entity_name(name)

        if light_type not in ["directional", "point", "spot"]:
            return error_result(
                error=f"Invalid light_type: {light_type}",
                error_code="INVALID_PARAMETER",
                suggestions=["Valid types: directional, point, spot"]
            )

        if light_type in ["directional", "spot"] and direction is None:
            return error_result(
                error=f"{light_type} light requires direction parameter",
                error_code="MISSING_PARAMETER"
            )

        # Default colors
        if diffuse is None:
            diffuse = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
        if specular is None:
            specular = diffuse.copy()

        # Build light SDF
        px, py, pz = position["x"], position["y"], position["z"]

        sdf_parts = [
            '<?xml version="1.0"?>',
            '<sdf version="1.7">',
            f'  <light name="{name}" type="{light_type}">',
            f'    <pose>{px} {py} {pz} 0 0 0</pose>',
        ]

        # Diffuse color
        dr, dg, db, da = diffuse["r"], diffuse["g"], diffuse["b"], diffuse["a"]
        sdf_parts.append(f'    <diffuse>{dr} {dg} {db} {da}</diffuse>')

        # Specular color
        sr, sg, sb, sa = specular["r"], specular["g"], specular["b"], specular["a"]
        sdf_parts.append(f'    <specular>{sr} {sg} {sb} {sa}</specular>')

        # Attenuation (for point and spot lights)
        if light_type in ["point", "spot"]:
            sdf_parts.extend([
                '    <attenuation>',
                f'      <range>{attenuation_range}</range>',
                f'      <constant>{attenuation_constant}</constant>',
                f'      <linear>{attenuation_linear}</linear>',
                f'      <quadratic>{attenuation_quadratic}</quadratic>',
                '    </attenuation>',
            ])

        # Direction (for directional and spot lights)
        if direction and light_type in ["directional", "spot"]:
            dx, dy, dz = direction["x"], direction["y"], direction["z"]
            sdf_parts.append(f'    <direction>{dx} {dy} {dz}</direction>')

        # Spot-specific parameters
        if light_type == "spot":
            sdf_parts.extend([
                '    <spot>',
                f'      <inner_angle>{spot_inner_angle}</inner_angle>',
                f'      <outer_angle>{spot_outer_angle}</outer_angle>',
                f'      <falloff>{spot_falloff}</falloff>',
                '    </spot>',
            ])

        # Shadows
        shadows_str = "true" if cast_shadows else "false"
        sdf_parts.append(f'    <cast_shadows>{shadows_str}</cast_shadows>')

        sdf_parts.extend([
            '  </light>',
            '</sdf>'
        ])

        sdf_content = '\n'.join(sdf_parts)

        # Get bridge and spawn
        bridge = _get_bridge()

        pose_dict = {
            "position": position,
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        }

        success = bridge.spawn_entity(
            name=name,
            xml_content=sdf_content,
            pose=pose_dict,
            reference_frame="world",
            timeout=timeout
        )

        if success:
            _logger.info(
                f"Spawned light in Gazebo",
                name=name,
                type=light_type,
                position=position
            )

            return success_result({
                "name": name,
                "light_type": light_type,
                "position": position,
                "direction": direction,
                "diffuse": diffuse,
                "attenuation_range": attenuation_range,
                "cast_shadows": cast_shadows,
                "spawned": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to spawn light '{name}'",
                error_code="LIGHT_SPAWN_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error spawning light", error=str(e))
        return error_result(
            error=f"Failed to spawn light: {e}",
            error_code="LIGHT_SPAWN_ERROR"
        )


def delete_light(
    name: str,
    timeout: float = 10.0
) -> OperationResult:
    """
    Delete a light from Gazebo simulation.

    Args:
        name: Name of the light to delete
        timeout: Service call timeout

    Returns:
        OperationResult with deletion status

    Example:
        >>> result = delete_light("lamp_1")
        >>> if result.success:
        ...     print(f"Light {result.data['name']} deleted")
    """
    try:
        # Validate parameters
        validate_entity_name(name)

        # Get bridge and delete
        bridge = _get_bridge()

        success = bridge.delete_entity(name=name, timeout=timeout)

        if success:
            _logger.info(f"Deleted light", name=name)

            return success_result({
                "name": name,
                "deleted": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to delete light '{name}'",
                error_code="DELETE_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced",
                "Start Gazebo simulation",
                "Verify bridge connectivity"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error deleting light", error=str(e))
        return error_result(
            error=f"Failed to delete light: {e}",
            error_code="LIGHT_DELETE_ERROR"
        )


# ==============================================================================
# Advanced Features: Mesh Loading, Grid Placement, Batch Spawning
# ==============================================================================


def place_mesh(
    name: str,
    mesh_file: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    scale: float = 1.0,
    collision_mesh_file: Optional[str] = None,
    static: bool = True,
    mass: float = 1.0,
    color: Optional[Dict[str, float]] = None
) -> OperationResult:
    """
    Generate SDF for a mesh-based model.

    Supports loading custom 3D models in .dae (COLLADA), .stl, or .obj formats.
    Useful for robots, furniture, terrain, or any custom geometry.

    Args:
        name: Unique model name
        mesh_file: Path to mesh file (relative to Gazebo model path or absolute)
        x, y, z: Position coordinates (meters)
        roll, pitch, yaw: Orientation in radians
        scale: Uniform scaling factor (1.0 = original size)
        collision_mesh_file: Optional separate collision mesh (for performance)
        static: If True, fixed; if False, physics-enabled
        mass: Mass for dynamic objects (kg)
        color: Optional RGBA color override (may not work with textured meshes)

    Returns:
        OperationResult with generated SDF content

    Example:
        >>> # Load a robot model
        >>> result = place_mesh(
        ...     name="my_robot",
        ...     mesh_file="models/robot.dae",
        ...     x=0, y=0, z=0.5,
        ...     scale=1.0,
        ...     static=False,
        ...     mass=50.0
        ... )
        >>> sdf = result.data["sdf_content"]

        >>> # Use simplified collision mesh for performance
        >>> result = place_mesh(
        ...     name="complex_building",
        ...     mesh_file="models/building_visual.dae",
        ...     collision_mesh_file="models/building_collision.stl",
        ...     x=10, y=10, z=0,
        ...     static=True
        ... )
    """
    try:
        # Validate parameters
        validate_entity_name(name)
        validate_position(x, y, z)

        # Validate mesh file format
        supported_formats = [".dae", ".stl", ".obj"]
        mesh_ext = mesh_file.lower().split('.')[-1]
        if not any(mesh_file.lower().endswith(fmt) for fmt in supported_formats):
            return error_result(
                error=f"Unsupported mesh format: .{mesh_ext}",
                error_code="INVALID_MESH_FORMAT",
                suggestions=[
                    f"Supported formats: {', '.join(supported_formats)}",
                    "Convert your mesh to COLLADA (.dae) for best compatibility"
                ]
            )

        # Use same mesh for collision if not specified
        if collision_mesh_file is None:
            collision_mesh_file = mesh_file

        # Default color
        if color is None:
            color = {"r": 0.8, "g": 0.8, "b": 0.8, "a": 1.0}

        # Build SDF
        static_str = "true" if static else "false"
        cr, cg, cb, ca = color["r"], color["g"], color["b"], color["a"]

        sdf_parts = [
            '<?xml version="1.0"?>',
            '<sdf version="1.7">',
            f'  <model name="{name}">',
            f'    <static>{static_str}</static>',
            f'    <pose>{x} {y} {z} {roll} {pitch} {yaw}</pose>',
            '    <link name="link">',
        ]

        # Inertial properties for dynamic objects
        if not static:
            # Simple inertial approximation
            ixx = iyy = izz = mass * 0.1  # Simplified
            sdf_parts.extend([
                '      <inertial>',
                f'        <mass>{mass}</mass>',
                '        <inertia>',
                f'          <ixx>{ixx}</ixx>',
                f'          <iyy>{iyy}</iyy>',
                f'          <izz>{izz}</izz>',
                '          <ixy>0.0</ixy>',
                '          <ixz>0.0</ixz>',
                '          <iyz>0.0</iyz>',
                '        </inertia>',
                '      </inertial>',
            ])

        # Visual geometry
        sdf_parts.extend([
            '      <visual name="visual">',
            '        <geometry>',
            '          <mesh>',
            f'            <uri>{mesh_file}</uri>',
            f'            <scale>{scale} {scale} {scale}</scale>',
            '          </mesh>',
            '        </geometry>',
            '        <material>',
            f'          <ambient>{cr} {cg} {cb} {ca}</ambient>',
            f'          <diffuse>{cr} {cg} {cb} {ca}</diffuse>',
            '          <specular>0.1 0.1 0.1 1</specular>',
            '        </material>',
            '      </visual>',
        ])

        # Collision geometry
        sdf_parts.extend([
            '      <collision name="collision">',
            '        <geometry>',
            '          <mesh>',
            f'            <uri>{collision_mesh_file}</uri>',
            f'            <scale>{scale} {scale} {scale}</scale>',
            '          </mesh>',
            '        </geometry>',
            '        <surface>',
            '          <friction>',
            '            <ode>',
            '              <mu>0.8</mu>',
            '              <mu2>0.8</mu2>',
            '            </ode>',
            '          </friction>',
            '        </surface>',
            '      </collision>',
        ])

        sdf_parts.extend([
            '    </link>',
            '  </model>',
            '</sdf>'
        ])

        sdf_content = '\n'.join(sdf_parts)

        _logger.info(
            f"Generated mesh SDF",
            name=name,
            mesh_file=mesh_file,
            scale=scale,
            static=static
        )

        return success_result({
            "name": name,
            "sdf_content": sdf_content,
            "mesh_file": mesh_file,
            "collision_mesh_file": collision_mesh_file,
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"roll": roll, "pitch": pitch, "yaw": yaw},
            "scale": scale,
            "static": static,
            "mass": mass,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    except Exception as e:
        _logger.exception("Error generating mesh SDF", error=str(e))
        return error_result(
            error=f"Failed to generate mesh SDF: {e}",
            error_code="MESH_GENERATION_ERROR"
        )


def spawn_mesh(
    name: str,
    mesh_file: str,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    scale: float = 1.0,
    collision_mesh_file: Optional[str] = None,
    static: bool = True,
    mass: float = 1.0,
    color: Optional[Dict[str, float]] = None,
    timeout: float = 10.0
) -> OperationResult:
    """
    Generate mesh SDF and spawn it in Gazebo simulation.

    Args:
        name: Unique model name
        mesh_file: Path to mesh file (.dae, .stl, .obj)
        x, y, z: Position coordinates (meters)
        roll, pitch, yaw: Orientation in radians
        scale: Uniform scaling factor
        collision_mesh_file: Optional separate collision mesh
        static: If True, fixed; if False, physics-enabled
        mass: Mass for dynamic objects (kg)
        color: Optional RGBA color override
        timeout: Spawn service call timeout (seconds)

    Returns:
        OperationResult with spawn status

    Example:
        >>> # Spawn a robot
        >>> result = spawn_mesh(
        ...     name="turtlebot3",
        ...     mesh_file="models/turtlebot3.dae",
        ...     x=1.0, y=0.0, z=0.1,
        ...     scale=1.0,
        ...     static=False,
        ...     mass=1.5
        ... )
    """
    try:
        # Step 1: Generate SDF
        gen_result = place_mesh(
            name=name,
            mesh_file=mesh_file,
            x=x, y=y, z=z,
            roll=roll, pitch=pitch, yaw=yaw,
            scale=scale,
            collision_mesh_file=collision_mesh_file,
            static=static,
            mass=mass,
            color=color
        )

        if not gen_result.success:
            return gen_result

        sdf_content = gen_result.data["sdf_content"]

        # Step 2: Spawn in Gazebo
        bridge = _get_bridge()

        pose = {
            "position": {"x": x, "y": y, "z": z},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}  # TODO: Convert roll/pitch/yaw to quaternion
        }

        success = bridge.spawn_entity(
            name=name,
            xml_content=sdf_content,
            pose=pose,
            reference_frame="world",
            timeout=timeout
        )

        if success:
            _logger.info(f"Spawned mesh in Gazebo", name=name, mesh_file=mesh_file)
            return success_result({
                "name": name,
                "spawned": True,
                "mesh_file": mesh_file,
                "position": {"x": x, "y": y, "z": z},
                "scale": scale,
                "static": static,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            return error_result(
                error=f"Failed to spawn mesh '{name}' in Gazebo",
                error_code="SPAWN_FAILED"
            )

    except ROS2NotConnectedError as e:
        return error_result(
            error=str(e),
            error_code="ROS2_NOT_CONNECTED",
            suggestions=[
                "Ensure ROS2 is sourced: source /opt/ros/humble/setup.bash",
                "Start Gazebo simulation before spawning",
                "Check ROS2 node connectivity: ros2 node list"
            ]
        )
    except Exception as e:
        _logger.exception("Unexpected error spawning mesh", error=str(e))
        return error_result(
            error=f"Failed to spawn mesh: {e}",
            error_code="MESH_SPAWN_ERROR"
        )


def place_grid(
    object_type: str,
    rows: int,
    cols: int,
    spacing: float,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    offset_z: float = 0.0,
    object_params: Optional[Dict[str, Any]] = None
) -> OperationResult:
    """
    Generate SDF for a grid of objects (boxes, spheres, or cylinders).

    Useful for creating obstacle courses, testing environments, or structured layouts.

    Args:
        object_type: Type of object ("box", "sphere", "cylinder")
        rows: Number of rows in grid
        cols: Number of columns in grid
        spacing: Distance between object centers (meters)
        offset_x, offset_y, offset_z: Grid origin offset (meters)
        object_params: Parameters for object generation (width, height, radius, etc.)

    Returns:
        OperationResult with list of generated objects and their SDF content

    Example:
        >>> # Create a 3x3 grid of boxes
        >>> result = place_grid(
        ...     object_type="box",
        ...     rows=3, cols=3,
        ...     spacing=2.0,
        ...     object_params={"width": 1.0, "height": 1.0, "depth": 1.0, "static": True}
        ... )
        >>> print(f"Generated {len(result.data['objects'])} objects")

        >>> # Create a grid of spheres offset from origin
        >>> result = place_grid(
        ...     object_type="sphere",
        ...     rows=2, cols=4,
        ...     spacing=1.5,
        ...     offset_x=5.0, offset_y=5.0,
        ...     object_params={"radius": 0.3, "color": {"r": 1, "g": 0, "b": 0, "a": 1}}
        ... )
    """
    try:
        # Validate parameters
        if object_type not in ["box", "sphere", "cylinder"]:
            return error_result(
                error=f"Invalid object_type: {object_type}",
                error_code="INVALID_OBJECT_TYPE",
                suggestions=["Valid types: box, sphere, cylinder"]
            )

        if rows < 1 or cols < 1:
            return error_result(
                error=f"Invalid grid dimensions: rows={rows}, cols={cols}",
                error_code="INVALID_GRID_DIMENSIONS",
                suggestions=["Both rows and cols must be >= 1"]
            )

        if spacing <= 0:
            return error_result(
                error=f"Invalid spacing: {spacing}",
                error_code="INVALID_SPACING",
                suggestions=["Spacing must be > 0"]
            )

        # Default object parameters
        if object_params is None:
            object_params = {}

        objects = []

        # Generate grid positions
        for row in range(rows):
            for col in range(cols):
                # Calculate position
                x = offset_x + col * spacing
                y = offset_y + row * spacing
                z = offset_z

                # Generate unique name
                name = f"{object_type}_r{row}_c{col}"

                # Generate SDF based on type
                if object_type == "box":
                    width = object_params.get("width", 1.0)
                    height = object_params.get("height", 1.0)
                    depth = object_params.get("depth", 1.0)
                    color = object_params.get("color", None)
                    static = object_params.get("static", True)

                    gen_result = place_box(
                        name=name,
                        x=x, y=y, z=z,
                        width=width, height=height, depth=depth,
                        color=color,
                        static=static
                    )

                elif object_type == "sphere":
                    radius = object_params.get("radius", 0.5)
                    color = object_params.get("color", None)
                    static = object_params.get("static", True)

                    gen_result = place_sphere(
                        name=name,
                        x=x, y=y, z=z,
                        radius=radius,
                        color=color,
                        static=static
                    )

                elif object_type == "cylinder":
                    radius = object_params.get("radius", 0.5)
                    length = object_params.get("length", 1.0)
                    color = object_params.get("color", None)
                    static = object_params.get("static", True)

                    gen_result = place_cylinder(
                        name=name,
                        x=x, y=y, z=z,
                        radius=radius, length=length,
                        color=color,
                        static=static
                    )

                if gen_result.success:
                    objects.append({
                        "name": name,
                        "type": object_type,
                        "position": {"x": x, "y": y, "z": z},
                        "row": row,
                        "col": col,
                        "sdf_content": gen_result.data["sdf_content"]
                    })
                else:
                    _logger.warning(
                        f"Failed to generate object in grid",
                        row=row, col=col,
                        error=gen_result.error
                    )

        _logger.info(
            f"Generated grid of objects",
            object_type=object_type,
            rows=rows, cols=cols,
            total_objects=len(objects)
        )

        return success_result({
            "object_type": object_type,
            "rows": rows,
            "cols": cols,
            "spacing": spacing,
            "offset": {"x": offset_x, "y": offset_y, "z": offset_z},
            "total_objects": len(objects),
            "objects": objects,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    except Exception as e:
        _logger.exception("Error generating grid", error=str(e))
        return error_result(
            error=f"Failed to generate grid: {e}",
            error_code="GRID_GENERATION_ERROR"
        )


def spawn_multiple(
    objects: List[Dict[str, Any]],
    continue_on_error: bool = True,
    timeout: float = 10.0
) -> OperationResult:
    """
    Spawn multiple objects in Gazebo in batch.

    More efficient than spawning objects one by one. Provides detailed
    success/failure tracking for each object.

    Args:
        objects: List of object specifications, each containing:
            - type: "box", "sphere", "cylinder", or "mesh"
            - name: Unique entity name
            - position: {"x": float, "y": float, "z": float}
            - params: Type-specific parameters
        continue_on_error: If True, continue spawning even if some fail
        timeout: Spawn timeout per object (seconds)

    Returns:
        OperationResult with batch spawn statistics

    Example:
        >>> objects = [
        ...     {
        ...         "type": "box",
        ...         "name": "obstacle_1",
        ...         "position": {"x": 1, "y": 0, "z": 0.5},
        ...         "params": {"width": 1, "height": 1, "depth": 1}
        ...     },
        ...     {
        ...         "type": "sphere",
        ...         "name": "ball_1",
        ...         "position": {"x": 3, "y": 0, "z": 0.5},
        ...         "params": {"radius": 0.5, "static": False}
        ...     }
        ... ]
        >>> result = spawn_multiple(objects)
        >>> print(f"Spawned {result.data['spawned']}/{result.data['total']}")
    """
    try:
        if not objects:
            return error_result(
                error="No objects provided",
                error_code="EMPTY_OBJECT_LIST"
            )

        total = len(objects)
        spawned = 0
        failed = 0
        results = []

        for obj_spec in objects:
            # Extract common fields
            obj_type = obj_spec.get("type")
            obj_name = obj_spec.get("name")
            position = obj_spec.get("position", {})
            params = obj_spec.get("params", {})

            if not obj_type or not obj_name:
                _logger.warning(
                    "Skipping object with missing type or name",
                    spec=obj_spec
                )
                failed += 1
                results.append({
                    "name": obj_name or "unknown",
                    "success": False,
                    "error": "Missing type or name"
                })
                continue

            # Extract position
            x = position.get("x", 0.0)
            y = position.get("y", 0.0)
            z = position.get("z", 0.0)

            # Spawn based on type
            spawn_result = None

            try:
                if obj_type == "box":
                    spawn_result = spawn_box(
                        name=obj_name,
                        x=x, y=y, z=z,
                        width=params.get("width", 1.0),
                        height=params.get("height", 1.0),
                        depth=params.get("depth", 1.0),
                        color=params.get("color"),
                        static=params.get("static", True),
                        timeout=timeout
                    )

                elif obj_type == "sphere":
                    spawn_result = spawn_sphere(
                        name=obj_name,
                        x=x, y=y, z=z,
                        radius=params.get("radius", 0.5),
                        color=params.get("color"),
                        static=params.get("static", True),
                        timeout=timeout
                    )

                elif obj_type == "cylinder":
                    spawn_result = spawn_cylinder(
                        name=obj_name,
                        x=x, y=y, z=z,
                        radius=params.get("radius", 0.5),
                        length=params.get("length", 1.0),
                        color=params.get("color"),
                        static=params.get("static", True),
                        timeout=timeout
                    )

                elif obj_type == "mesh":
                    spawn_result = spawn_mesh(
                        name=obj_name,
                        mesh_file=params.get("mesh_file", ""),
                        x=x, y=y, z=z,
                        roll=params.get("roll", 0.0),
                        pitch=params.get("pitch", 0.0),
                        yaw=params.get("yaw", 0.0),
                        scale=params.get("scale", 1.0),
                        collision_mesh_file=params.get("collision_mesh_file"),
                        static=params.get("static", True),
                        mass=params.get("mass", 1.0),
                        color=params.get("color"),
                        timeout=timeout
                    )

                else:
                    spawn_result = error_result(
                        error=f"Unknown object type: {obj_type}",
                        error_code="UNKNOWN_OBJECT_TYPE"
                    )

                # Track result
                if spawn_result and spawn_result.success:
                    spawned += 1
                    results.append({
                        "name": obj_name,
                        "type": obj_type,
                        "success": True
                    })
                else:
                    failed += 1
                    error_msg = spawn_result.error if spawn_result else "Unknown error"
                    results.append({
                        "name": obj_name,
                        "type": obj_type,
                        "success": False,
                        "error": error_msg
                    })

                    if not continue_on_error:
                        break

            except Exception as e:
                _logger.exception(
                    "Error spawning object in batch",
                    name=obj_name,
                    type=obj_type,
                    error=str(e)
                )
                failed += 1
                results.append({
                    "name": obj_name,
                    "type": obj_type,
                    "success": False,
                    "error": str(e)
                })

                if not continue_on_error:
                    break

        _logger.info(
            f"Batch spawn complete",
            total=total,
            spawned=spawned,
            failed=failed
        )

        return success_result({
            "total": total,
            "spawned": spawned,
            "failed": failed,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    except Exception as e:
        _logger.exception("Error in batch spawn", error=str(e))
        return error_result(
            error=f"Batch spawn failed: {e}",
            error_code="BATCH_SPAWN_ERROR"
        )
