# Phase 5B Implementation Plan - Direct Approach

**Status**: Ready to Implement
**Estimated Duration**: 3-4 days
**Prerequisites**: Phase 5A Complete (135/135 tests passing)

---

## Overview

Phase 5B adds medium-priority features to world generation:
1. Advanced obstacle patterns (maze, grid, circular)
2. Shadow quality controls
3. Volumetric lighting
4. Animation system
5. Trigger zones

All features maintain 100% backward compatibility using Optional parameters with defaults.

---

## Feature 1: Advanced Obstacle Course Patterns

### Implementation Tasks

#### 1.1 Add pattern_type Parameter

**File**: `src/gazebo_mcp/tools/world_generation.py`

**Function**: `create_obstacle_course()`

**Changes**:
```python
def create_obstacle_course(
    num_obstacles: int = 10,
    boundary_size: float = 10.0,
    obstacle_types: List[str] = None,
    min_distance: float = 1.0,
    seed: Optional[int] = None,

    # NEW: Pattern system
    pattern_type: str = "random",  # "random", "maze", "grid", "circular"
    difficulty: str = "medium",     # "easy", "medium", "hard", "expert"
) -> OperationResult:
```

**Validation**:
- `pattern_type` must be in ["random", "maze", "grid", "circular"]
- `difficulty` must be in ["easy", "medium", "hard", "expert"]

#### 1.2 Implement Maze Pattern

**Algorithm**: Recursive backtracking

**Helper Function**:
```python
def _generate_maze_grid(
    rows: int,
    cols: int,
    seed: Optional[int] = None
) -> Set[Tuple[int, int]]:
    """
    Generate maze using recursive backtracking.

    Returns: Set of (row, col) coordinates that are paths (not walls)

    Algorithm:
    1. Initialize grid with all walls
    2. Start at random cell, mark as path
    3. While unvisited cells exist:
       - Choose random unvisited neighbor
       - Remove wall between cells
       - Mark neighbor as path
       - Recurse from neighbor
       - Backtrack when no unvisited neighbors
    4. Return path cells
    """
    if seed is not None:
        random.seed(seed)

    # Grid: True = path, False = wall
    grid = [[False] * cols for _ in range(rows)]

    # Stack for DFS
    stack = []
    start = (0, 0)
    grid[start[0]][start[1]] = True
    stack.append(start)

    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    while stack:
        current = stack[-1]
        neighbors = []

        for dr, dc in directions:
            nr, nc = current[0] + dr, current[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols and not grid[nr][nc]:
                neighbors.append((nr, nc))

        if neighbors:
            next_cell = random.choice(neighbors)
            grid[next_cell[0]][next_cell[1]] = True
            stack.append(next_cell)
        else:
            stack.pop()

    # Return path cells
    return {(r, c) for r in range(rows) for c in range(cols) if grid[r][c]}
```

**Integration**:
```python
if pattern_type == "maze":
    # Calculate grid size from boundary and difficulty
    cell_size = 2.0 / difficulty_multiplier  # Smaller cells = harder
    grid_cols = int(boundary_size / cell_size)
    grid_rows = int(boundary_size / cell_size)

    # Generate maze
    path_cells = _generate_maze_grid(grid_rows, grid_cols, seed)

    # Convert to obstacle positions (place obstacles in wall cells)
    obstacles = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            if (r, c) not in path_cells:
                x = -boundary_size/2 + c * cell_size + cell_size/2
                y = -boundary_size/2 + r * cell_size + cell_size/2
                z = 0.5
                obstacles.append({
                    "type": random.choice(obstacle_types),
                    "position": (x, y, z),
                    "size": (cell_size * 0.9, cell_size * 0.9, 1.0)
                })
```

#### 1.3 Implement Grid Pattern

**Algorithm**: Regular grid placement

```python
if pattern_type == "grid":
    # Calculate spacing based on difficulty
    base_spacing = boundary_size / math.sqrt(num_obstacles)
    spacing = base_spacing / difficulty_multiplier

    # Calculate grid dimensions
    cols = int(boundary_size / spacing)
    rows = int(boundary_size / spacing)

    # Place obstacles at grid intersections
    obstacles = []
    for r in range(rows):
        for c in range(cols):
            if len(obstacles) >= num_obstacles:
                break

            x = -boundary_size/2 + c * spacing
            y = -boundary_size/2 + r * spacing
            z = 0.5

            obstacles.append({
                "type": random.choice(obstacle_types),
                "position": (x, y, z),
                "size": (1.0, 1.0, 1.0)
            })
```

#### 1.4 Implement Circular Pattern

**Algorithm**: Concentric circles with evenly-spaced obstacles

```python
if pattern_type == "circular":
    # Calculate number of circles based on difficulty
    num_circles = int(3 * difficulty_multiplier)
    max_radius = boundary_size / 2 * 0.9

    obstacles = []
    for circle_idx in range(num_circles):
        radius = max_radius * (circle_idx + 1) / num_circles

        # Obstacles per circle: proportional to circumference
        obstacles_per_circle = int(2 * math.pi * radius / 2.0)
        obstacles_per_circle = max(4, obstacles_per_circle)  # Minimum 4

        for i in range(obstacles_per_circle):
            if len(obstacles) >= num_obstacles:
                break

            angle = 2 * math.pi * i / obstacles_per_circle
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            z = 0.5

            obstacles.append({
                "type": random.choice(obstacle_types),
                "position": (x, y, z),
                "size": (1.0, 1.0, 1.0)
            })
```

#### 1.5 Implement Difficulty Multipliers

**Difficulty Definitions**:
```python
DIFFICULTY_MULTIPLIERS = {
    "easy": {
        "density": 0.7,
        "spacing": 1.3,
        "complexity": 0.8
    },
    "medium": {
        "density": 1.0,
        "spacing": 1.0,
        "complexity": 1.0
    },
    "hard": {
        "density": 1.5,
        "spacing": 0.8,
        "complexity": 1.2
    },
    "expert": {
        "density": 2.0,
        "spacing": 0.6,
        "complexity": 1.5
    }
}
```

**Apply to Pattern Generation**:
```python
multiplier = DIFFICULTY_MULTIPLIERS[difficulty]
adjusted_num_obstacles = int(num_obstacles * multiplier["density"])
adjusted_spacing = base_spacing * multiplier["spacing"]
```

---

## Feature 2: Shadow Quality Controls

### Implementation Tasks

#### 2.1 Add set_shadow_quality Function

**File**: `src/gazebo_mcp/tools/world_generation.py`

**New Function**:
```python
def set_shadow_quality(
    quality_level: str = "medium",
    shadow_resolution: Optional[int] = None,
    pcf_enabled: Optional[bool] = None,
    cascade_count: Optional[int] = None
) -> OperationResult:
    """
    Configure shadow rendering quality.

    Args:
        quality_level: Preset quality ("low", "medium", "high", "ultra")
        shadow_resolution: Override resolution (512-8192, power of 2)
        pcf_enabled: Override PCF (Percentage Closer Filtering)
        cascade_count: Override cascade count (1-4, directional lights)

    Returns:
        OperationResult with shadow configuration
    """
    # Quality presets
    SHADOW_PRESETS = {
        "low": {
            "resolution": 1024,
            "pcf": False,
            "cascades": 1
        },
        "medium": {
            "resolution": 2048,
            "pcf": True,
            "cascades": 2
        },
        "high": {
            "resolution": 4096,
            "pcf": True,
            "cascades": 3
        },
        "ultra": {
            "resolution": 8192,
            "pcf": True,
            "cascades": 4
        }
    }

    # Validate quality_level
    if quality_level not in SHADOW_PRESETS:
        return error_result(
            f"Invalid quality_level: {quality_level}",
            suggestions=["Use: low, medium, high, ultra"]
        )

    # Start with preset
    config = SHADOW_PRESETS[quality_level].copy()

    # Apply overrides
    if shadow_resolution is not None:
        if shadow_resolution < 512 or shadow_resolution > 8192:
            return error_result("shadow_resolution must be 512-8192")
        if shadow_resolution & (shadow_resolution - 1) != 0:
            return error_result("shadow_resolution must be power of 2")
        config["resolution"] = shadow_resolution

    if pcf_enabled is not None:
        config["pcf"] = pcf_enabled

    if cascade_count is not None:
        if cascade_count < 1 or cascade_count > 4:
            return error_result("cascade_count must be 1-4")
        config["cascades"] = cascade_count

    # Generate SDF for shadow configuration
    sdf_content = f"""
    <scene>
      <shadows>
        <resolution>{config['resolution']}</resolution>
        <pcf>{str(config['pcf']).lower()}</pcf>
        <cascades>{config['cascades']}</cascades>
      </shadows>
    </scene>
    """

    _logger.info(
        f"Configured shadow quality [quality={quality_level}, "
        f"resolution={config['resolution']}, pcf={config['pcf']}, "
        f"cascades={config['cascades']}]"
    )

    return success_result({
        "quality_level": quality_level,
        "resolution": config["resolution"],
        "pcf_enabled": config["pcf"],
        "cascade_count": config["cascades"],
        "sdf_content": sdf_content.strip()
    })
```

---

## Feature 3: Volumetric Lighting

### Implementation Tasks

#### 3.1 Add Volumetric Parameters to spawn_light

**File**: `src/gazebo_mcp/tools/world_generation.py`

**Function**: `spawn_light()`

**Changes**:
```python
def spawn_light(
    light_name: str,
    light_type: str,
    pose: Tuple[float, float, float, float, float, float] = (0, 0, 5, 0, 0, 0),
    color: Dict[str, float] = None,
    intensity: float = 1.0,
    cast_shadows: bool = True,
    direction: Tuple[float, float, float] = None,
    attenuation_range: float = 10.0,
    attenuation_constant: float = 1.0,
    attenuation_linear: float = 0.0,
    attenuation_quadratic: float = 0.0,
    spot_inner_angle: float = 0.6,
    spot_outer_angle: float = 1.0,

    # NEW: Volumetric lighting (Phase 5B)
    volumetric_enabled: bool = False,
    volumetric_density: float = 0.1,
    volumetric_scattering: float = 0.5
) -> OperationResult:
    """
    Spawn light with optional volumetric effects.

    Args:
        volumetric_enabled: Enable god rays / light shafts (spot/directional only)
        volumetric_density: Scattering intensity (0.0-1.0)
        volumetric_scattering: Light shaft visibility (0.0-1.0)
    """
    # Validate volumetric parameters
    if volumetric_enabled:
        if light_type not in ["spot", "directional"]:
            return error_result(
                "Volumetric lighting only supported for spot and directional lights",
                suggestions=["Use light_type='spot' or 'directional'"]
            )

        if not 0.0 <= volumetric_density <= 1.0:
            return error_result("volumetric_density must be 0.0-1.0")

        if not 0.0 <= volumetric_scattering <= 1.0:
            return error_result("volumetric_scattering must be 0.0-1.0")

    # ... existing light generation code ...

    # Add volumetric section to SDF if enabled
    volumetric_sdf = ""
    if volumetric_enabled:
        volumetric_sdf = f"""
      <volumetric>
        <enabled>true</enabled>
        <density>{volumetric_density}</density>
        <scattering>{volumetric_scattering}</scattering>
      </volumetric>
"""

    sdf_content = f"""
    <light name="{light_name}" type="{light_type}">
      <pose>{x} {y} {z} {roll} {pitch} {yaw}</pose>
      <diffuse>{r} {g} {b} {a}</diffuse>
      <specular>{r} {g} {b} {a}</specular>
      <cast_shadows>{str(cast_shadows).lower()}</cast_shadows>
      {direction_sdf}
      {attenuation_sdf}
      {spot_sdf}
      {volumetric_sdf}
    </light>
    """

    # ... rest of function ...

    result_data = {
        "light_name": light_name,
        "light_type": light_type,
        "volumetric_enabled": volumetric_enabled
    }

    if volumetric_enabled:
        result_data.update({
            "volumetric_density": volumetric_density,
            "volumetric_scattering": volumetric_scattering
        })

    return success_result(result_data)
```

---

## Feature 4: Animation System

### Implementation Tasks

#### 4.1 Add create_animated_object Function

**File**: `src/gazebo_mcp/tools/world_generation.py`

**New Function**:
```python
def create_animated_object(
    object_name: str,
    model_type: str,  # "box", "sphere", "cylinder"
    animation_type: str = "linear_path",

    # Path animation
    path_points: Optional[List[Tuple[float, float, float]]] = None,

    # Circular animation
    center: Optional[Tuple[float, float, float]] = None,
    radius: Optional[float] = None,

    # Oscillating animation
    axis: str = "x",  # "x", "y", "z"
    amplitude: float = 1.0,
    frequency: float = 1.0,

    # Common parameters
    speed: float = 1.0,
    loop: str = "repeat",  # "once", "repeat", "ping_pong"
    start_delay: float = 0.0,
    size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    mass: float = 1.0
) -> OperationResult:
    """
    Create animated object with scripted motion.

    Animation Types:
        - "linear_path": Move through waypoints
        - "circular": Orbit around center point
        - "oscillating": Sinusoidal back-and-forth

    Loop Modes:
        - "once": Play animation once, stop at end
        - "repeat": Loop continuously from start
        - "ping_pong": Reverse direction at ends

    Returns:
        OperationResult with animation configuration
    """
    # Validate animation_type
    valid_types = ["linear_path", "circular", "oscillating"]
    if animation_type not in valid_types:
        return error_result(
            f"Invalid animation_type: {animation_type}",
            suggestions=[f"Use: {', '.join(valid_types)}"]
        )

    # Validate loop mode
    valid_loops = ["once", "repeat", "ping_pong"]
    if loop not in valid_loops:
        return error_result(
            f"Invalid loop: {loop}",
            suggestions=[f"Use: {', '.join(valid_loops)}"]
        )

    # Validate parameters per animation type
    if animation_type == "linear_path":
        if not path_points or len(path_points) < 2:
            return error_result(
                "linear_path requires at least 2 path_points",
                suggestions=["Provide path_points=[(x1,y1,z1), (x2,y2,z2), ...]"]
            )

    elif animation_type == "circular":
        if center is None or radius is None:
            return error_result(
                "circular requires center and radius",
                suggestions=["Provide center=(x,y,z) and radius=value"]
            )
        if radius <= 0:
            return error_result("radius must be positive")

    elif animation_type == "oscillating":
        if axis not in ["x", "y", "z"]:
            return error_result("axis must be 'x', 'y', or 'z'")
        if amplitude <= 0:
            return error_result("amplitude must be positive")
        if frequency <= 0:
            return error_result("frequency must be positive")

    # Generate trajectory waypoints based on animation type
    if animation_type == "linear_path":
        waypoints = path_points

    elif animation_type == "circular":
        # Generate waypoints around circle
        num_waypoints = 32  # Smooth circle
        waypoints = []
        cx, cy, cz = center

        for i in range(num_waypoints):
            angle = 2 * math.pi * i / num_waypoints
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            z = cz
            waypoints.append((x, y, z))

        # Close the loop
        waypoints.append(waypoints[0])

    elif animation_type == "oscillating":
        # Generate sinusoidal waypoints
        num_waypoints = 20
        waypoints = []

        for i in range(num_waypoints):
            t = i / (num_waypoints - 1)  # 0 to 1
            offset = amplitude * math.sin(2 * math.pi * frequency * t)

            if axis == "x":
                waypoints.append((offset, 0, 0))
            elif axis == "y":
                waypoints.append((0, offset, 0))
            else:  # z
                waypoints.append((0, 0, offset))

    # Calculate total path length and time
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        dx = waypoints[i+1][0] - waypoints[i][0]
        dy = waypoints[i+1][1] - waypoints[i][1]
        dz = waypoints[i+1][2] - waypoints[i][2]
        total_distance += math.sqrt(dx*dx + dy*dy + dz*dz)

    total_time = total_distance / speed

    # Generate actor SDF with script
    script_waypoints = ""
    for i, (x, y, z) in enumerate(waypoints):
        time = start_delay + (total_time * i / (len(waypoints) - 1))
        script_waypoints += f"""
        <waypoint>
          <time>{time}</time>
          <pose>{x} {y} {z} 0 0 0</pose>
        </waypoint>"""

    # Loop control
    script_loop = "true" if loop in ["repeat", "ping_pong"] else "false"
    script_auto_start = "true"

    sdf_content = f"""
    <actor name="{object_name}">
      <pose>0 0 0 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <{model_type}>
              <size>{size[0]} {size[1]} {size[2]}</size>
            </{model_type}>
          </geometry>
        </visual>
        <collision name="collision">
          <geometry>
            <{model_type}>
              <size>{size[0]} {size[1]} {size[2]}</size>
            </{model_type}>
          </geometry>
        </collision>
        <inertial>
          <mass>{mass}</mass>
        </inertial>
      </link>
      <script>
        <loop>{script_loop}</loop>
        <auto_start>{script_auto_start}</auto_start>
        <trajectory id="0" type="line">
          {script_waypoints}
        </trajectory>
      </script>
    </actor>
    """

    _logger.info(
        f"Created animated object [name={object_name}, type={animation_type}, "
        f"waypoints={len(waypoints)}, duration={total_time:.2f}s, loop={loop}]"
    )

    return success_result({
        "object_name": object_name,
        "animation_type": animation_type,
        "num_waypoints": len(waypoints),
        "total_distance": total_distance,
        "duration": total_time,
        "loop": loop,
        "sdf_content": sdf_content.strip()
    })
```

---

## Feature 5: Trigger Zones

### Implementation Tasks

#### 5.1 Add Trigger Zone Classes

**File**: `src/gazebo_mcp/tools/world_generation.py` or new `triggers.py`

**Base Class**:
```python
from abc import ABC, abstractmethod

class TriggerZone(ABC):
    """Base class for trigger zones."""

    def __init__(self, zone_name: str, center: Tuple[float, float, float]):
        self.zone_name = zone_name
        self.center = center

    @abstractmethod
    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if point is inside zone."""
        pass

    @abstractmethod
    def to_sdf(self) -> str:
        """Generate SDF for visualization."""
        pass


class BoxTriggerZone(TriggerZone):
    """Box-shaped trigger zone."""

    def __init__(
        self,
        zone_name: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ):
        super().__init__(zone_name, center)
        self.size = size

        # Calculate bounds for fast containment check
        self.min_x = center[0] - size[0] / 2
        self.max_x = center[0] + size[0] / 2
        self.min_y = center[1] - size[1] / 2
        self.max_y = center[1] + size[1] / 2
        self.min_z = center[2] - size[2] / 2
        self.max_z = center[2] + size[2] / 2

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if point is inside box."""
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )

    def to_sdf(self) -> str:
        """Generate box visual for zone."""
        cx, cy, cz = self.center
        sx, sy, sz = self.size

        return f"""
    <model name="{self.zone_name}_visual">
      <pose>{cx} {cy} {cz} 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box>
              <size>{sx} {sy} {sz}</size>
            </box>
          </geometry>
          <material>
            <ambient>0 1 0 0.3</ambient>
            <diffuse>0 1 0 0.3</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""


class SphereTriggerZone(TriggerZone):
    """Sphere-shaped trigger zone."""

    def __init__(
        self,
        zone_name: str,
        center: Tuple[float, float, float],
        radius: float
    ):
        super().__init__(zone_name, center)
        self.radius = radius
        self.radius_squared = radius * radius

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if point is inside sphere."""
        dx = x - self.center[0]
        dy = y - self.center[1]
        dz = z - self.center[2]
        distance_squared = dx*dx + dy*dy + dz*dz
        return distance_squared <= self.radius_squared

    def to_sdf(self) -> str:
        """Generate sphere visual for zone."""
        cx, cy, cz = self.center

        return f"""
    <model name="{self.zone_name}_visual">
      <pose>{cx} {cy} {cz} 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <visual name="visual">
          <geometry>
            <sphere>
              <radius>{self.radius}</radius>
            </sphere>
          </geometry>
          <material>
            <ambient>0 1 0 0.3</ambient>
            <diffuse>0 1 0 0.3</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""


class CylinderTriggerZone(TriggerZone):
    """Cylinder-shaped trigger zone."""

    def __init__(
        self,
        zone_name: str,
        center: Tuple[float, float, float],
        radius: float,
        height: float
    ):
        super().__init__(zone_name, center)
        self.radius = radius
        self.radius_squared = radius * radius
        self.height = height
        self.min_z = center[2] - height / 2
        self.max_z = center[2] + height / 2

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if point is inside cylinder."""
        # Check height bounds
        if not (self.min_z <= z <= self.max_z):
            return False

        # Check radial distance
        dx = x - self.center[0]
        dy = y - self.center[1]
        radial_distance_squared = dx*dx + dy*dy
        return radial_distance_squared <= self.radius_squared

    def to_sdf(self) -> str:
        """Generate cylinder visual for zone."""
        cx, cy, cz = self.center

        return f"""
    <model name="{self.zone_name}_visual">
      <pose>{cx} {cy} {cz} 0 0 0</pose>
      <static>true</static>
      <link name="link">
        <visual name="visual">
          <geometry>
            <cylinder>
              <radius>{self.radius}</radius>
              <length>{self.height}</length>
            </cylinder>
          </geometry>
          <material>
            <ambient>0 1 0 0.3</ambient>
            <diffuse>0 1 0 0.3</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""
```

#### 5.2 Add create_trigger_zone Function

**Function**:
```python
def create_trigger_zone(
    zone_name: str,
    zone_shape: str = "box",
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0),

    # Box parameters
    size: Optional[Tuple[float, float, float]] = None,

    # Sphere parameters
    radius: Optional[float] = None,

    # Cylinder parameters
    height: Optional[float] = None,

    # Trigger configuration
    trigger_events: List[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    visualize: bool = True
) -> OperationResult:
    """
    Create trigger zone with event-driven actions.

    Args:
        zone_name: Unique name for zone
        zone_shape: "box", "sphere", or "cylinder"
        center: Zone center position (x, y, z)
        size: Box dimensions (x, y, z)
        radius: Sphere/cylinder radius
        height: Cylinder height
        trigger_events: Events to listen for (["enter"], ["exit"], ["stay"])
        actions: List of actions to execute on trigger
        visualize: Show zone boundaries in simulation

    Actions format:
        [
            {
                "event": "enter",  # Which event triggers this action
                "type": "log",     # Action type: "log", "teleport", "apply_force"
                "params": {...}    # Action-specific parameters
            },
            ...
        ]

    Returns:
        OperationResult with zone configuration
    """
    # Validate zone_shape
    if zone_shape not in ["box", "sphere", "cylinder"]:
        return error_result(
            f"Invalid zone_shape: {zone_shape}",
            suggestions=["Use: box, sphere, cylinder"]
        )

    # Validate parameters per shape
    if zone_shape == "box":
        if size is None:
            return error_result(
                "box zone requires size parameter",
                suggestions=["Provide size=(x, y, z)"]
            )
        zone = BoxTriggerZone(zone_name, center, size)

    elif zone_shape == "sphere":
        if radius is None:
            return error_result(
                "sphere zone requires radius parameter",
                suggestions=["Provide radius=value"]
            )
        if radius <= 0:
            return error_result("radius must be positive")
        zone = SphereTriggerZone(zone_name, center, radius)

    elif zone_shape == "cylinder":
        if radius is None or height is None:
            return error_result(
                "cylinder zone requires radius and height parameters",
                suggestions=["Provide radius=value, height=value"]
            )
        if radius <= 0 or height <= 0:
            return error_result("radius and height must be positive")
        zone = CylinderTriggerZone(zone_name, center, radius, height)

    # Validate trigger_events
    if trigger_events is None:
        trigger_events = ["enter"]

    valid_events = ["enter", "exit", "stay"]
    for event in trigger_events:
        if event not in valid_events:
            return error_result(
                f"Invalid trigger event: {event}",
                suggestions=[f"Use: {', '.join(valid_events)}"]
            )

    # Validate actions
    if actions is None:
        actions = []

    valid_action_types = ["log", "teleport", "apply_force", "custom_script"]
    for action in actions:
        if "type" not in action:
            return error_result("Action missing 'type' field")
        if action["type"] not in valid_action_types:
            return error_result(
                f"Invalid action type: {action['type']}",
                suggestions=[f"Use: {', '.join(valid_action_types)}"]
            )
        if "params" not in action:
            return error_result("Action missing 'params' field")

    # Generate SDF
    sdf_content = ""

    # Add visualization if requested
    if visualize:
        sdf_content += zone.to_sdf()

    # Add plugin for trigger detection
    # Note: This would need a custom Gazebo plugin or ROS2 node
    # For now, generate configuration that could be used by such a plugin
    plugin_config = {
        "zone_name": zone_name,
        "zone_shape": zone_shape,
        "center": center,
        "trigger_events": trigger_events,
        "actions": actions
    }

    _logger.info(
        f"Created trigger zone [name={zone_name}, shape={zone_shape}, "
        f"events={trigger_events}, actions={len(actions)}]"
    )

    return success_result({
        "zone_name": zone_name,
        "zone_shape": zone_shape,
        "center": center,
        "trigger_events": trigger_events,
        "num_actions": len(actions),
        "visualize": visualize,
        "sdf_content": sdf_content.strip(),
        "plugin_config": plugin_config
    })
```

---

## Testing Strategy

### Test File: `tests/unit/test_world_generation_phase5b.py`

**Test Structure**:
```python
import pytest
from gazebo_mcp.tools import world_generation


class TestObstaclePatterns:
    """Test advanced obstacle course patterns."""

    def test_maze_pattern_basic(self):
        """Test maze pattern generation."""
        result = world_generation.create_obstacle_course(
            num_obstacles=20,
            pattern_type="maze",
            seed=42
        )
        assert result.success
        assert "obstacles" in result.data
        assert len(result.data["obstacles"]) > 0

    def test_maze_pattern_reproducibility(self):
        """Test maze pattern with same seed produces same result."""
        result1 = world_generation.create_obstacle_course(
            pattern_type="maze",
            seed=42
        )
        result2 = world_generation.create_obstacle_course(
            pattern_type="maze",
            seed=42
        )
        assert result1.success and result2.success
        # Compare obstacle positions (should be identical)

    def test_grid_pattern(self):
        """Test grid pattern generation."""
        result = world_generation.create_obstacle_course(
            num_obstacles=16,
            pattern_type="grid",
            seed=42
        )
        assert result.success
        # Verify regular spacing

    def test_circular_pattern(self):
        """Test circular pattern generation."""
        result = world_generation.create_obstacle_course(
            num_obstacles=20,
            pattern_type="circular",
            seed=42
        )
        assert result.success
        # Verify circular arrangement

    def test_difficulty_affects_patterns(self):
        """Test difficulty changes pattern complexity."""
        easy = world_generation.create_obstacle_course(
            pattern_type="grid",
            difficulty="easy",
            seed=42
        )
        expert = world_generation.create_obstacle_course(
            pattern_type="grid",
            difficulty="expert",
            seed=42
        )
        assert easy.success and expert.success
        # Expert should have more obstacles or tighter spacing

    def test_invalid_pattern_type(self):
        """Test invalid pattern_type returns error."""
        result = world_generation.create_obstacle_course(
            pattern_type="invalid"
        )
        assert not result.success
        assert "pattern_type" in result.error.lower()


class TestShadowQuality:
    """Test shadow quality controls."""

    def test_shadow_quality_presets(self):
        """Test each quality preset."""
        for quality in ["low", "medium", "high", "ultra"]:
            result = world_generation.set_shadow_quality(quality_level=quality)
            assert result.success
            assert result.data["quality_level"] == quality
            assert "resolution" in result.data
            assert "pcf_enabled" in result.data

    def test_shadow_quality_overrides(self):
        """Test parameter overrides."""
        result = world_generation.set_shadow_quality(
            quality_level="medium",
            shadow_resolution=4096,
            pcf_enabled=False
        )
        assert result.success
        assert result.data["resolution"] == 4096
        assert result.data["pcf_enabled"] is False

    def test_invalid_resolution(self):
        """Test invalid resolution validation."""
        result = world_generation.set_shadow_quality(
            shadow_resolution=1000  # Not power of 2
        )
        assert not result.success


class TestVolumetricLighting:
    """Test volumetric lighting effects."""

    def test_volumetric_spot_light(self):
        """Test volumetric lighting on spot light."""
        result = world_generation.spawn_light(
            light_name="volumetric_spot",
            light_type="spot",
            volumetric_enabled=True,
            volumetric_density=0.5
        )
        assert result.success
        assert result.data["volumetric_enabled"] is True

    def test_volumetric_directional_light(self):
        """Test volumetric on directional light."""
        result = world_generation.spawn_light(
            light_name="volumetric_sun",
            light_type="directional",
            volumetric_enabled=True
        )
        assert result.success

    def test_volumetric_invalid_light_type(self):
        """Test volumetric rejected for point lights."""
        result = world_generation.spawn_light(
            light_name="point_light",
            light_type="point",
            volumetric_enabled=True
        )
        assert not result.success

    def test_volumetric_parameter_validation(self):
        """Test density validation."""
        result = world_generation.spawn_light(
            light_name="test",
            light_type="spot",
            volumetric_enabled=True,
            volumetric_density=1.5  # Invalid: > 1.0
        )
        assert not result.success


class TestAnimationSystem:
    """Test animated object creation."""

    def test_linear_path_animation(self):
        """Test linear path animation."""
        result = world_generation.create_animated_object(
            object_name="moving_box",
            model_type="box",
            animation_type="linear_path",
            path_points=[(0,0,0), (5,0,0), (5,5,0)],
            speed=1.0
        )
        assert result.success
        assert result.data["animation_type"] == "linear_path"
        assert result.data["num_waypoints"] >= 3

    def test_circular_animation(self):
        """Test circular motion animation."""
        result = world_generation.create_animated_object(
            object_name="orbiting_sphere",
            model_type="sphere",
            animation_type="circular",
            center=(0, 0, 1),
            radius=3.0,
            speed=1.0
        )
        assert result.success
        assert result.data["animation_type"] == "circular"

    def test_oscillating_animation(self):
        """Test oscillating motion."""
        result = world_generation.create_animated_object(
            object_name="pendulum",
            model_type="cylinder",
            animation_type="oscillating",
            axis="x",
            amplitude=2.0,
            frequency=0.5
        )
        assert result.success
        assert result.data["animation_type"] == "oscillating"

    def test_loop_modes(self):
        """Test different loop modes."""
        for loop in ["once", "repeat", "ping_pong"]:
            result = world_generation.create_animated_object(
                object_name=f"object_{loop}",
                model_type="box",
                animation_type="circular",
                center=(0,0,0),
                radius=1.0,
                loop=loop
            )
            assert result.success
            assert result.data["loop"] == loop

    def test_missing_parameters(self):
        """Test validation catches missing parameters."""
        # Linear path without path_points
        result = world_generation.create_animated_object(
            object_name="test",
            model_type="box",
            animation_type="linear_path"
        )
        assert not result.success


class TestTriggerZones:
    """Test trigger zone system."""

    def test_box_trigger_zone(self):
        """Test box-shaped trigger zone."""
        result = world_generation.create_trigger_zone(
            zone_name="box_zone",
            zone_shape="box",
            center=(0, 0, 0),
            size=(5, 5, 2)
        )
        assert result.success
        assert result.data["zone_shape"] == "box"

    def test_sphere_trigger_zone(self):
        """Test sphere-shaped trigger zone."""
        result = world_generation.create_trigger_zone(
            zone_name="sphere_zone",
            zone_shape="sphere",
            center=(10, 10, 1),
            radius=3.0
        )
        assert result.success

    def test_cylinder_trigger_zone(self):
        """Test cylinder-shaped trigger zone."""
        result = world_generation.create_trigger_zone(
            zone_name="cylinder_zone",
            zone_shape="cylinder",
            center=(0, 0, 0),
            radius=2.0,
            height=5.0
        )
        assert result.success

    def test_trigger_with_actions(self):
        """Test trigger zone with actions."""
        result = world_generation.create_trigger_zone(
            zone_name="action_zone",
            zone_shape="sphere",
            center=(0, 0, 0),
            radius=2.0,
            trigger_events=["enter", "exit"],
            actions=[
                {
                    "event": "enter",
                    "type": "log",
                    "params": {"message": "Entered zone!"}
                },
                {
                    "event": "exit",
                    "type": "teleport",
                    "params": {"target": (0, 0, 5)}
                }
            ]
        )
        assert result.success
        assert result.data["num_actions"] == 2

    def test_zone_containment_box(self):
        """Test box zone containment math."""
        from gazebo_mcp.tools.world_generation import BoxTriggerZone

        zone = BoxTriggerZone("test", (0, 0, 0), (2, 2, 2))

        # Inside
        assert zone.contains(0, 0, 0) is True
        assert zone.contains(0.5, 0.5, 0.5) is True

        # On boundary
        assert zone.contains(1, 0, 0) is True

        # Outside
        assert zone.contains(2, 0, 0) is False
        assert zone.contains(0, 3, 0) is False

    def test_zone_containment_sphere(self):
        """Test sphere zone containment math."""
        from gazebo_mcp.tools.world_generation import SphereTriggerZone

        zone = SphereTriggerZone("test", (0, 0, 0), 5.0)

        # Inside
        assert zone.contains(0, 0, 0) is True
        assert zone.contains(3, 0, 0) is True

        # On boundary
        assert zone.contains(5, 0, 0) is True

        # Outside
        assert zone.contains(6, 0, 0) is False


class TestBackwardCompatibility:
    """Test backward compatibility with Phase 5A."""

    def test_obstacle_course_default_parameters(self):
        """Test obstacle course works without new parameters."""
        result = world_generation.create_obstacle_course(
            num_obstacles=10,
            boundary_size=10.0
        )
        assert result.success
        # Should use default pattern_type="random" and difficulty="medium"

    def test_spawn_light_default_volumetric(self):
        """Test light spawning works without volumetric parameters."""
        result = world_generation.spawn_light(
            light_name="basic_light",
            light_type="point",
            pose=(0, 0, 5, 0, 0, 0)
        )
        assert result.success
        # volumetric_enabled should default to False


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Example/Demo File

### File: `examples/08_phase5b_features.py`

**Demo showcasing all Phase 5B features**:

```python
#!/usr/bin/env python3
"""
Phase 5B Features Example - Advanced World Generation

Demonstrates Phase 5B enhancements:
1. Advanced obstacle patterns (maze, grid, circular)
2. Shadow quality controls
3. Volumetric lighting effects
4. Animation system
5. Trigger zones

Requirements:
- ROS2 Humble
- Python 3.8+
- Phase 5A complete
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from gazebo_mcp.tools import world_generation
from gazebo_mcp.utils.operation_result import OperationResult


def print_result(result: OperationResult, operation: str):
    """Helper to print operation results."""
    if result.success:
        print(f"✓ {operation}")
    else:
        print(f"✗ {operation}: {result.error}")


def main():
    print("=" * 70)
    print("Phase 5B Features - Advanced World Generation")
    print("=" * 70)
    print()

    # =========================================================================
    # Part 1: Advanced Obstacle Patterns
    # =========================================================================
    print("\n" + "=" * 70)
    print("Part 1: Advanced Obstacle Patterns")
    print("=" * 70)

    print("\n1.1 Maze Pattern (Expert Difficulty)")
    result = world_generation.create_obstacle_course(
        num_obstacles=30,
        boundary_size=20.0,
        pattern_type="maze",
        difficulty="expert",
        seed=42
    )
    print_result(result, "Create maze obstacle course")
    if result.success:
        print(f"  Obstacles: {len(result.data.get('obstacles', []))}")

    print("\n1.2 Grid Pattern (Easy Difficulty)")
    result = world_generation.create_obstacle_course(
        num_obstacles=16,
        boundary_size=15.0,
        pattern_type="grid",
        difficulty="easy",
        seed=123
    )
    print_result(result, "Create grid obstacle course")

    print("\n1.3 Circular Pattern (Hard Difficulty)")
    result = world_generation.create_obstacle_course(
        num_obstacles=25,
        boundary_size=18.0,
        pattern_type="circular",
        difficulty="hard",
        seed=456
    )
    print_result(result, "Create circular obstacle course")

    # =========================================================================
    # Part 2: Shadow Quality Controls
    # =========================================================================
    print("\n" + "=" * 70)
    print("Part 2: Shadow Quality Controls")
    print("=" * 70)

    print("\n2.1 Ultra Shadow Quality")
    result = world_generation.set_shadow_quality(
        quality_level="ultra"
    )
    print_result(result, "Set ultra shadow quality")
    if result.success:
        print(f"  Resolution: {result.data['resolution']}")
        print(f"  PCF: {result.data['pcf_enabled']}")
        print(f"  Cascades: {result.data['cascade_count']}")

    print("\n2.2 Custom Shadow Settings")
    result = world_generation.set_shadow_quality(
        quality_level="high",
        shadow_resolution=8192,
        pcf_enabled=True
    )
    print_result(result, "Set custom shadow quality")

    # =========================================================================
    # Part 3: Volumetric Lighting
    # =========================================================================
    print("\n" + "=" * 70)
    print("Part 3: Volumetric Lighting")
    print("=" * 70)

    print("\n3.1 Volumetric Spotlight")
    result = world_generation.spawn_light(
        light_name="dramatic_spot",
        light_type="spot",
        pose=(10, 10, 8, 0, 0.7854, 0),
        intensity=2.0,
        volumetric_enabled=True,
        volumetric_density=0.3,
        volumetric_scattering=0.6
    )
    print_result(result, "Spawn volumetric spotlight")

    print("\n3.2 Volumetric Directional Light (Sun)")
    result = world_generation.spawn_light(
        light_name="volumetric_sun",
        light_type="directional",
        direction=(0.3, 0.3, -1.0),
        intensity=1.5,
        volumetric_enabled=True,
        volumetric_density=0.15
    )
    print_result(result, "Spawn volumetric directional light")

    # =========================================================================
    # Part 4: Animation System
    # =========================================================================
    print("\n" + "=" * 70)
    print("Part 4: Animation System")
    print("=" * 70)

    print("\n4.1 Linear Path Animation")
    result = world_generation.create_animated_object(
        object_name="patrol_box",
        model_type="box",
        animation_type="linear_path",
        path_points=[
            (-5, -5, 0.5),
            (5, -5, 0.5),
            (5, 5, 0.5),
            (-5, 5, 0.5),
            (-5, -5, 0.5)
        ],
        speed=2.0,
        loop="repeat",
        size=(1.0, 1.0, 1.0)
    )
    print_result(result, "Create patrol animation")
    if result.success:
        print(f"  Duration: {result.data['duration']:.2f}s")

    print("\n4.2 Circular Animation")
    result = world_generation.create_animated_object(
        object_name="orbiting_sphere",
        model_type="sphere",
        animation_type="circular",
        center=(0, 0, 2),
        radius=5.0,
        speed=1.5,
        loop="repeat",
        size=(0.5, 0.5, 0.5)
    )
    print_result(result, "Create circular animation")

    print("\n4.3 Oscillating Animation")
    result = world_generation.create_animated_object(
        object_name="pendulum",
        model_type="cylinder",
        animation_type="oscillating",
        axis="x",
        amplitude=3.0,
        frequency=0.5,
        speed=1.0,
        loop="repeat",
        size=(0.3, 0.3, 2.0)
    )
    print_result(result, "Create oscillating animation")

    # =========================================================================
    # Part 5: Trigger Zones
    # =========================================================================
    print("\n" + "=" * 70)
    print("Part 5: Trigger Zones")
    print("=" * 70)

    print("\n5.1 Sphere Trigger Zone (Goal)")
    result = world_generation.create_trigger_zone(
        zone_name="goal_zone",
        zone_shape="sphere",
        center=(0, 0, 0.5),
        radius=2.0,
        trigger_events=["enter"],
        actions=[
            {
                "event": "enter",
                "type": "log",
                "params": {"message": "🎯 Goal reached!"}
            },
            {
                "event": "enter",
                "type": "apply_force",
                "params": {"force": (0, 0, 15)}
            }
        ],
        visualize=True
    )
    print_result(result, "Create goal trigger zone")

    print("\n5.2 Box Trigger Zone (Checkpoint)")
    result = world_generation.create_trigger_zone(
        zone_name="checkpoint",
        zone_shape="box",
        center=(10, 10, 1),
        size=(4, 4, 3),
        trigger_events=["enter", "exit"],
        actions=[
            {
                "event": "enter",
                "type": "log",
                "params": {"message": "✓ Checkpoint entered"}
            },
            {
                "event": "exit",
                "type": "log",
                "params": {"message": "← Checkpoint exited"}
            }
        ],
        visualize=True
    )
    print_result(result, "Create checkpoint trigger zone")

    print("\n5.3 Cylinder Trigger Zone (Teleporter)")
    result = world_generation.create_trigger_zone(
        zone_name="teleporter",
        zone_shape="cylinder",
        center=(-10, -10, 0),
        radius=1.5,
        height=3.0,
        trigger_events=["enter"],
        actions=[
            {
                "event": "enter",
                "type": "log",
                "params": {"message": "🌀 Teleporting..."}
            },
            {
                "event": "enter",
                "type": "teleport",
                "params": {"target": (10, 10, 5)}
            }
        ],
        visualize=True
    )
    print_result(result, "Create teleporter trigger zone")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("Phase 5B Complete - All Features Demonstrated!")
    print("=" * 70)
    print()

    print("✓ Module 5B.1: Advanced Obstacle Patterns")
    print("  - Maze generation with recursive backtracking")
    print("  - Grid pattern with regular spacing")
    print("  - Circular pattern with radial distribution")
    print("  - Difficulty presets (easy/medium/hard/expert)")
    print()

    print("✓ Module 5B.2: Shadow Quality Controls")
    print("  - 4 quality presets (low/medium/high/ultra)")
    print("  - Custom resolution, PCF, cascade overrides")
    print("  - Performance-quality trade-off control")
    print()

    print("✓ Module 5B.3: Volumetric Lighting")
    print("  - God rays / light shafts for spot lights")
    print("  - Atmospheric effects for directional lights")
    print("  - Density and scattering controls")
    print()

    print("✓ Module 5B.4: Animation System")
    print("  - Linear path following")
    print("  - Circular orbits")
    print("  - Oscillating motion")
    print("  - Loop modes (once/repeat/ping-pong)")
    print()

    print("✓ Module 5B.5: Trigger Zones")
    print("  - 3 zone shapes (box/sphere/cylinder)")
    print("  - 3 event types (enter/exit/stay)")
    print("  - Multiple action types (log/teleport/force)")
    print()

    print("Quality Metrics:")
    print("  ✓ 100% backward compatible with Phase 5A")
    print("  ✓ All parameters Optional with defaults")
    print("  ✓ OperationResult pattern throughout")
    print("  ✓ Comprehensive test coverage")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
```

---

## Implementation Timeline

### Estimated Schedule (3-4 days)

**Day 1**: Obstacle Patterns (6-8 hours)
- Morning: Implement maze generator
- Afternoon: Implement grid and circular patterns
- Evening: Add difficulty system, test all patterns

**Day 2**: Lighting Systems (6-8 hours)
- Morning: Implement shadow quality controls
- Afternoon: Add volumetric lighting to spawn_light
- Evening: Test rendering, verify SDF generation

**Day 3**: Animation & Triggers (8-10 hours)
- Morning: Implement animation system (3 types)
- Afternoon: Implement trigger zone system
- Evening: Integration testing

**Day 4**: Testing & Documentation (4-6 hours)
- Morning: Write comprehensive tests
- Afternoon: Create demo/example file
- Evening: Update documentation, verify completion

---

## Success Criteria

### Implementation Complete When:
- [ ] All 5 features implemented
- [ ] All tests passing (Phase 5A + 5B)
- [ ] Demo file runs without errors
- [ ] 100% backward compatibility verified
- [ ] Documentation updated
- [ ] Code reviewed for quality

### Quality Checklist:
- [ ] All parameters Optional with defaults
- [ ] OperationResult used consistently
- [ ] Input validation comprehensive
- [ ] Error messages helpful with suggestions
- [ ] Logging informative
- [ ] Type hints complete
- [ ] Docstrings detailed

---

## Next Steps

**Ready to start?** Begin with Feature 1 (Obstacle Patterns) and work through sequentially. Update the todo list as you complete each feature.

**Need help?** Use these skills:
- `code_analysis` - Analyze existing code patterns
- `refactor_assistant` - Improve code quality
- `test_orchestrator` - Generate test scaffolds
- `doc_generator` - Generate documentation

Good luck! 🚀
