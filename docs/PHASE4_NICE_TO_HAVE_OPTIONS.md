# Phase 4 Nice-to-Have Option Additions

**Document Version:** 1.0
**Date:** 2025-11-17
**Status:** Recommendations for Enhancement
**Phase:** Phase 4 - World Generation & Manipulation Tools

---

## Executive Summary

This document identifies **50+ optional parameter enhancements** for Phase 4 tools that would significantly improve the ROS2 Gazebo MCP Server's capabilities without breaking existing functionality. These enhancements focus on:

- **Reproducibility** - Seeds for deterministic random generation
- **Realism** - Advanced physics, materials, and environmental effects
- **Testing** - Standardized benchmark worlds and sensor test scenarios
- **Usability** - Batch operations, presets, and quality-of-life improvements

All enhancements maintain compatibility with the existing `OperationResult` pattern and `ResultFilter` token efficiency approach.

---

## Priority Classification

### 🔴 HIGH PRIORITY (Maximum Impact)

1. **Reproducible Seeds** - Critical for benchmarking and research
2. **Material System Expansion** - 10+ additional realistic materials
3. **Advanced Obstacle Course** - Patterns, difficulty levels, maze generation
4. **Unified Weather System** - Integrated lighting, fog, precipitation, wind
5. **Batch Operations** - Performance optimization for large-scale changes

### 🟡 MEDIUM PRIORITY (Quality-of-Life)

6. **Animation System** - Moving obstacles for dynamic scenarios
7. **Trigger Zones** - Interactive training environments
8. **Undo/Redo** - World editing workflow improvement
9. **Heightmap Enhancements** - Multi-texture blending, erosion effects
10. **Advanced Shadow Controls** - Precision shadow tuning for vision tasks

### 🟢 LOW PRIORITY (Future Phases)

11. **AI-Assisted Generation** - LLM-powered world creation
12. **Recording/Playback** - Time-series world state capture
13. **Seasonal Variations** - Long-term environmental changes
14. **Acoustic Simulation** - Audio sensors and effects
15. **Digital Twin Integration** - Real-world synchronization

---

## Module 4.1: World File Management

### Enhanced Tool: `create_empty_world`

**Current Signature:**
```python
create_empty_world(
    world_name: str,
    ground_plane: bool = True,
    sun: bool = True
) -> OperationResult
```

**Enhanced Signature:**
```python
create_empty_world(
    world_name: str,
    ground_plane: bool = True,
    sun: bool = True,

    # Physics Configuration
    physics_engine: str = "ode",  # "ode", "bullet", "simbody"
    gravity: Tuple[float, float, float] = (0, 0, -9.8),
    max_step_size: float = 0.001,
    real_time_factor: float = 1.0,

    # Visual Configuration
    background_color: Optional[Dict[str, float]] = None,  # {r, g, b, a}
    grid_visible: bool = False,
    initial_camera_pose: Optional[Dict[str, float]] = None,  # {x, y, z, roll, pitch, yaw}

    # World Size
    world_size: Tuple[float, float] = (100.0, 100.0),  # Ground plane dimensions
) -> OperationResult
```

**Use Cases:**
- **Moon/Space Simulation:** `gravity=(0, 0, -1.62)` for lunar gravity
- **High-Precision Testing:** `max_step_size=0.0001` for fine control
- **Slow-Motion Analysis:** `real_time_factor=0.1` for detailed observation
- **Custom Environments:** `background_color={'r': 0.1, 'g': 0.1, 'b': 0.2, 'a': 1.0}` for night sky

**Implementation Priority:** 🔴 HIGH - Frequently requested for research

---

## Module 4.2: Object Placement Tools

### Enhanced Tool: `place_static_object`

**Enhanced Signature:**
```python
place_static_object(
    object_type: str,
    name: str,
    x: float, y: float, z: float,
    size: Dict[str, float],
    color: Optional[Dict[str, float]] = None,

    # Orientation
    orientation: Optional[Dict[str, float]] = None,  # {roll, pitch, yaw} in degrees

    # Material & Appearance
    material_preset: Optional[str] = None,  # "metal", "wood", "plastic", "glass"
    texture_path: Optional[str] = None,
    transparency: float = 1.0,  # 0.0 = invisible, 1.0 = opaque

    # Physics Properties
    physics_properties: Optional[Dict] = None,  # {mass, inertia_tensor}

    # Rendering
    cast_shadows: bool = True,
    receive_shadows: bool = True,

    # Advanced Geometry
    collision_shape: Optional[str] = None,  # Use different shape for collisions
    visual_mesh: Optional[str] = None,  # Path to custom mesh file
) -> OperationResult
```

**Material Presets:**
```python
MATERIAL_PRESETS = {
    'metal': {
        'color': (0.7, 0.7, 0.7, 1.0),
        'roughness': 0.3,
        'metallic': 1.0,
        'friction': 0.5,
        'restitution': 0.3,
    },
    'wood': {
        'color': (0.6, 0.4, 0.2, 1.0),
        'roughness': 0.8,
        'metallic': 0.0,
        'friction': 0.6,
        'restitution': 0.2,
    },
    'plastic': {
        'color': (0.8, 0.2, 0.2, 1.0),
        'roughness': 0.5,
        'metallic': 0.0,
        'friction': 0.4,
        'restitution': 0.5,
    },
    'glass': {
        'color': (0.9, 0.9, 1.0, 0.3),
        'roughness': 0.05,
        'metallic': 0.0,
        'friction': 0.3,
        'restitution': 0.1,
    },
    'rubber': {
        'color': (0.2, 0.2, 0.2, 1.0),
        'roughness': 0.9,
        'metallic': 0.0,
        'friction': 1.2,
        'restitution': 0.8,
    },
}
```

**Use Cases:**
- **Glass Walls:** `material_preset="glass", transparency=0.3`
- **Weighted Obstacles:** `physics_properties={'mass': 1000.0}`
- **Rotated Objects:** `orientation={'roll': 0, 'pitch': 45, 'yaw': 0}`

**Implementation Priority:** 🟡 MEDIUM - Adds significant realism

---

### Enhanced Tool: `create_obstacle_course`

**Current Signature:**
```python
create_obstacle_course(
    num_obstacles: int = 10,
    area_size: float = 20.0,
    obstacle_types: List[str] = ["box", "cylinder"],
    min_distance: float = 1.0
) -> OperationResult
```

**Enhanced Signature:**
```python
create_obstacle_course(
    num_obstacles: int = 10,
    area_size: float = 20.0,
    obstacle_types: List[str] = ["box", "cylinder"],
    min_distance: float = 1.0,

    # Reproducibility (CRITICAL!)
    seed: Optional[int] = None,  # Fixed seed for deterministic generation

    # Obstacle Variation
    height_range: Tuple[float, float] = (0.5, 2.0),
    size_variance: float = 0.3,  # ±30% randomization

    # Visual Styling
    color_scheme: Optional[str] = None,  # "monochrome", "rainbow", "traffic", "custom"
    custom_colors: Optional[List[Dict[str, float]]] = None,  # If color_scheme="custom"

    # Layout Patterns
    pattern: str = "random",  # "random", "grid", "circular", "maze", "spiral"
    center_clearance: float = 0.0,  # Keep center area clear (radius in meters)
    boundary_type: str = "square",  # "square", "circular", "rectangular"
    boundary_size: Optional[Tuple[float, float]] = None,  # Custom boundary dimensions

    # Difficulty Settings
    difficulty_level: str = "medium",  # "easy", "medium", "hard", "expert"
    obstacle_distribution: str = "uniform",  # "uniform", "clustered", "sparse_center", "dense_perimeter"

    # Boundary Features
    include_walls: bool = False,
    wall_height: float = 2.0,
    wall_thickness: float = 0.2,

    # Maze-Specific (if pattern="maze")
    maze_complexity: float = 0.5,  # 0.0 = simple, 1.0 = complex
    maze_solution_path: bool = False,  # Guarantee solvable

    # Export Options
    export_metadata: bool = True,  # Save obstacle positions for analysis
    metadata_path: Optional[str] = None,
) -> OperationResult
```

**Difficulty Level Mappings:**
```python
DIFFICULTY_SETTINGS = {
    'easy': {
        'default_obstacles': 5,
        'min_distance': 3.0,
        'height_range': (0.3, 1.0),
        'clear_paths': True,
    },
    'medium': {
        'default_obstacles': 10,
        'min_distance': 2.0,
        'height_range': (0.5, 1.5),
        'clear_paths': True,
    },
    'hard': {
        'default_obstacles': 20,
        'min_distance': 1.5,
        'height_range': (0.5, 2.0),
        'clear_paths': False,
    },
    'expert': {
        'default_obstacles': 30,
        'min_distance': 1.0,
        'height_range': (0.3, 2.5),
        'clear_paths': False,
        'narrow_passages': True,
    },
}
```

**Pattern Examples:**
```python
# Maze pattern for navigation testing
create_obstacle_course(
    pattern="maze",
    maze_complexity=0.7,
    difficulty_level="hard",
    seed=42,  # Reproducible
)

# Circular pattern for sensor testing
create_obstacle_course(
    pattern="circular",
    num_obstacles=12,
    boundary_type="circular",
    center_clearance=5.0,
    seed=42,
)

# Grid pattern for perception benchmarking
create_obstacle_course(
    pattern="grid",
    num_obstacles=25,  # 5x5 grid
    color_scheme="rainbow",
    seed=42,
)
```

**Use Cases:**
- **Benchmarking:** Fixed `seed` ensures reproducibility across experiments
- **Training Progression:** `difficulty_level` from "easy" to "expert"
- **Sensor Testing:** `pattern="circular"` with robot at center
- **Research Publications:** `export_metadata=True` for documentation

**Implementation Priority:** 🔴 HIGH - Critical for benchmarking and research

---

### New Tool: `place_object_grid`

**Signature:**
```python
place_object_grid(
    object_type: str,
    name_prefix: str,
    grid_size: Tuple[int, int],  # (rows, cols)
    spacing: float = 2.0,

    # Placement Options
    center_at_origin: bool = True,
    stagger: bool = False,  # Offset alternating rows (like bricks)

    # Variation
    rotation_variance: float = 0.0,  # Random rotation ±degrees
    height_variance: float = 0.0,  # Random z offset ±meters
    skip_probability: float = 0.0,  # Randomly omit objects (0.0-1.0)

    # Pattern Alternatives
    spiral_pattern: bool = False,

    # Reproducibility
    seed: Optional[int] = None,
) -> OperationResult
```

**Use Cases:**
- **Sensor Arrays:** Regular grid for LiDAR calibration
- **Multi-Robot:** Spawn fleet in formation
- **Perception Testing:** Structured obstacle detection

**Implementation Priority:** 🟡 MEDIUM - Useful for specific scenarios

---

## Module 4.3: Terrain Modification Tools

### Enhanced Tool: `create_heightmap`

**Enhanced Signature:**
```python
create_heightmap(
    heightmap_image: str,  # Path or base64
    scale: float = 1.0,
    elevation_range: float = 10.0,
    position: Optional[Dict[str, float]] = None,

    # Texture Mapping
    texture_image: Optional[str] = None,
    blend_textures: bool = False,  # Blend by elevation
    texture_mapping: Optional[Dict[str, str]] = None,  # {elevation_range: texture_path}
    normal_map: Optional[str] = None,
    tile_size: float = 10.0,

    # Heightmap Processing
    erosion_effect: float = 0.0,  # Procedural erosion (0.0-1.0)
    smoothing: float = 0.0,  # Smooth sharp edges (0.0-1.0)
    invert_heightmap: bool = False,
    base_height: float = 0.0,  # Vertical offset

    # Performance Optimization
    collision_simplification: Optional[int] = None,  # Reduce mesh detail
    lod_levels: int = 1,  # Level-of-detail for rendering
) -> OperationResult
```

**Texture Blending Example:**
```python
create_heightmap(
    heightmap_image="terrain.png",
    blend_textures=True,
    texture_mapping={
        '0-50': 'textures/grass.jpg',     # Low elevations
        '50-150': 'textures/rock.jpg',    # Mid elevations
        '150-300': 'textures/snow.jpg',   # High elevations
    }
)
```

**Use Cases:**
- **Realistic Terrains:** Multi-texture blending by elevation
- **Mars Simulation:** Custom heightmaps with red rock textures
- **Performance Testing:** `collision_simplification=10` for complex terrains
- **Underwater Terrain:** `invert_heightmap=True` for ocean floor

**Implementation Priority:** 🟡 MEDIUM - Enhances visual realism

---

### Enhanced Tool: `set_surface_type`

**Enhanced Signature:**
```python
set_surface_type(
    surface_name: str,
    material: str,
    friction: Optional[float] = None,
    restitution: Optional[float] = None,

    # Advanced Friction Models
    rolling_friction: Optional[float] = None,  # For wheeled robots
    spin_friction: Optional[float] = None,  # Rotational resistance

    # Surface Properties
    surface_roughness: float = 0.0,  # Visual and physics (0.0-1.0)
    wetness: float = 0.0,  # Affects friction/appearance (0.0-1.0)

    # Environmental
    temperature: Optional[float] = None,  # Celsius (for thermal sensors)

    # Effects
    contact_sound: Optional[str] = None,  # "footstep_grass", "wheel_concrete"
    particle_effects: Optional[str] = None,  # "dust", "splash", "snow"

    # Dynamic Properties
    wear_over_time: bool = False,  # Surface degrades with use
) -> OperationResult
```

**Extended Material Library:**
```python
EXTENDED_MATERIALS = {
    'grass': {...},  # Existing
    'concrete': {...},  # Existing
    'ice': {...},  # Existing

    # NEW MATERIALS:
    'wet_grass': {
        'friction': 0.5,  # Lower than dry grass
        'wetness': 0.8,
        'particle_effects': 'splash',
        'color': (0.15, 0.7, 0.15, 1.0),
    },
    'gravel': {
        'friction': 0.7,
        'rolling_friction': 0.05,
        'particle_effects': 'dust',
        'contact_sound': 'gravel_crunch',
    },
    'mud': {
        'friction': 0.4,
        'rolling_friction': 0.15,
        'wetness': 0.9,
        'particle_effects': 'mud_splash',
    },
    'sand': {
        'friction': 0.6,
        'rolling_friction': 0.08,
        'particle_effects': 'sand_kick',
        'color': (0.9, 0.8, 0.6, 1.0),
    },
    'snow': {
        'friction': 0.3,
        'rolling_friction': 0.1,
        'color': (0.95, 0.95, 0.98, 1.0),
        'particle_effects': 'snow_puff',
    },
    'asphalt': {
        'friction': 1.0,
        'rolling_friction': 0.01,
        'color': (0.2, 0.2, 0.2, 1.0),
    },
    'dirt': {
        'friction': 0.75,
        'particle_effects': 'dust',
        'color': (0.5, 0.35, 0.2, 1.0),
    },
    'metal_plate': {
        'friction': 0.4,
        'restitution': 0.2,
        'metallic': 1.0,
        'contact_sound': 'metal_clang',
    },
    'rubber_mat': {
        'friction': 1.5,
        'restitution': 0.7,
        'rolling_friction': 0.02,
    },
    'wood_floor': {
        'friction': 0.6,
        'contact_sound': 'wood_creak',
        'color': (0.6, 0.4, 0.2, 1.0),
    },
}
```

**Use Cases:**
- **Wheeled Robots:** `rolling_friction` for realistic tire behavior
- **Weather Conditions:** Switch from "grass" to "wet_grass"
- **Sensor Testing:** `particle_effects="dust"` to test vision in dusty environments
- **Thermal Simulation:** `temperature=35.0` for heat mapping

**Implementation Priority:** 🔴 HIGH - Critical for realistic robot testing

---

### New Tool: `create_procedural_terrain`

**Signature:**
```python
create_procedural_terrain(
    terrain_type: str,  # "mountains", "desert", "canyon", "hills", "mars", "lunar"
    size: Tuple[float, float] = (100.0, 100.0),
    resolution: int = 256,  # Heightmap resolution

    # Reproducibility
    seed: Optional[int] = None,

    # Perlin Noise Parameters
    octaves: int = 6,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    base_frequency: float = 1.0,

    # Terrain Characteristics
    feature_scale: float = 1.0,  # Size of terrain features
    elevation_range: float = 10.0,

    # Type-Specific
    type_params: Optional[Dict[str, Any]] = None,
) -> OperationResult
```

**Terrain Type Presets:**
```python
TERRAIN_PRESETS = {
    'mountains': {
        'octaves': 8,
        'persistence': 0.6,
        'elevation_range': 50.0,
        'material': 'rock',
    },
    'desert': {
        'octaves': 4,
        'persistence': 0.3,
        'elevation_range': 5.0,
        'material': 'sand',
    },
    'mars': {
        'octaves': 6,
        'persistence': 0.5,
        'elevation_range': 20.0,
        'material': 'mars_soil',
        'color_tint': (0.8, 0.3, 0.1, 1.0),
    },
    'lunar': {
        'octaves': 5,
        'persistence': 0.4,
        'elevation_range': 15.0,
        'material': 'lunar_regolith',
        'crater_generation': True,
    },
}
```

**Use Cases:**
- **Quick Test Worlds:** No need for external heightmap images
- **Planetary Robotics:** Mars/Lunar presets
- **Reproducible Terrains:** `seed=42` for consistent generation

**Implementation Priority:** 🟡 MEDIUM - Convenience feature

---

### New Tool: `add_terrain_variation`

**Signature:**
```python
add_terrain_variation(
    terrain_name: str,
    variation_type: str,  # "hills", "valleys", "ridges", "craters", "bumps"

    # Feature Count and Size
    num_features: int = 5,
    feature_size: Tuple[float, float] = (5.0, 10.0),  # (min, max) meters
    feature_height: Tuple[float, float] = (1.0, 5.0),  # (min, max) meters

    # Shape Characteristics
    smoothness: float = 0.5,  # 0=sharp, 1=smooth

    # Reproducibility
    seed: Optional[int] = None,

    # Blending
    blend_mode: str = "add",  # "add", "multiply", "overlay", "subtract"

    # Regional Application
    regions: Optional[List[Dict]] = None,  # Apply only to specific areas
) -> OperationResult
```

**Use Cases:**
- **Obstacle Addition:** Add hills to flat terrain
- **Crater Fields:** Lunar/Mars environments
- **Natural Variation:** Break up perfectly flat terrains

**Implementation Priority:** 🟢 LOW - Nice addition but not critical

---

## Module 4.4: Lighting Control Tools

### Enhanced Tool: `set_ambient_light`

**Enhanced Signature:**
```python
set_ambient_light(
    color: Dict[str, float],
    intensity: float,

    # Atmospheric Effects
    fog_enabled: bool = False,
    fog_density: float = 0.01,
    fog_color: Optional[Dict[str, float]] = None,
    fog_start: float = 10.0,  # Meters from camera
    fog_end: float = 100.0,

    # Hemisphere Lighting
    hemisphere_lighting: bool = False,
    ground_color: Optional[Dict[str, float]] = None,  # Different color from below
) -> OperationResult
```

**Use Cases:**
- **Fog Testing:** Test vision algorithms in low visibility
- **Realistic Outdoor:** Hemisphere lighting for natural sky/ground color difference

**Implementation Priority:** 🔴 HIGH - Fog critical for sensor testing

---

### Enhanced Tool: `add_directional_light`

**Enhanced Signature:**
```python
add_directional_light(
    name: str,
    direction: Dict[str, float],
    intensity: float = 1.0,
    color: Optional[Dict[str, float]] = None,
    cast_shadows: bool = True,

    # Shadow Quality
    shadow_resolution: int = 1024,  # Shadow map size
    shadow_bias: float = 0.001,  # Fix shadow acne
    shadow_darkness: float = 0.5,  # Shadow opacity (0.0-1.0)
    cascade_count: int = 3,  # Cascaded shadow maps for large scenes

    # Volumetric Effects
    volumetric_enabled: bool = False,  # God rays / light shafts
    volumetric_density: float = 0.1,

    # Color Temperature
    temperature: int = 5500,  # Kelvin (sunlight = 5500K)
    use_realistic_sun: bool = False,  # Apply sun-specific physics
) -> OperationResult
```

**Color Temperature Presets:**
```python
COLOR_TEMPERATURES = {
    'candle': 1800,
    'sunrise_sunset': 2500,
    'tungsten_bulb': 3200,
    'fluorescent': 4000,
    'daylight': 5500,
    'overcast': 6500,
    'blue_sky': 10000,
}
```

**Use Cases:**
- **High-Quality Shadows:** `shadow_resolution=2048` for precision
- **Cinematic Scenes:** `volumetric_enabled=True` for god rays
- **Realistic Lighting:** `temperature=2500` for warm sunrise

**Implementation Priority:** 🟡 MEDIUM - Shadow quality important for vision

---

### Enhanced Tool: `add_point_light`

**Enhanced Signature:**
```python
add_point_light(
    name: str,
    position: Dict[str, float],
    intensity: float = 1.0,
    color: Optional[Dict[str, float]] = None,

    # Attenuation (Light Falloff)
    attenuation_range: float = 10.0,
    attenuation_constant: float = 1.0,
    attenuation_linear: float = 0.0,
    attenuation_quadratic: float = 1.0,  # Physically accurate

    # Shadows
    cast_shadows: bool = False,  # Expensive for point lights

    # Animation Effects
    flicker_enabled: bool = False,  # Realistic fire/candle
    flicker_frequency: float = 2.0,  # Hz
    flicker_intensity: float = 0.1,  # Variation amount

    pulse_enabled: bool = False,  # Rhythmic pulsing
    pulse_frequency: float = 1.0,  # Hz

    # Visual Effects
    lens_flare: bool = False,
) -> OperationResult
```

**Use Cases:**
- **Indoor Lighting:** Room lights with proper falloff
- **Emergency Lights:** `pulse_enabled=True, color={'r': 1, 'g': 0, 'b': 0}`
- **Torches/Flames:** `flicker_enabled=True`

**Implementation Priority:** 🟡 MEDIUM - Useful for indoor scenarios

---

### Enhanced Tool: `add_spot_light`

**Enhanced Signature:**
```python
add_spot_light(
    name: str,
    position: Dict[str, float],
    direction: Dict[str, float],
    intensity: float = 1.0,
    color: Optional[Dict[str, float]] = None,

    # Cone Shape
    inner_cone_angle: float = 30.0,  # Full brightness cone
    outer_cone_angle: float = 45.0,  # Falloff edge
    cone_softness: float = 0.5,  # Edge blur (0.0-1.0)

    # Projection Mapping
    gobo_texture: Optional[str] = None,  # Project pattern/image

    # Volumetric
    volumetric_enabled: bool = False,  # Visible light beam

    # Animation
    animation: Optional[str] = None,  # "sweep", "rotate", "flicker"
    animation_speed: float = 1.0,

    # Standard Parameters
    attenuation_range: float = 20.0,
    cast_shadows: bool = True,
) -> OperationResult
```

**Use Cases:**
- **Searchlights:** Sweeping animated spotlights
- **Pattern Projection:** `gobo_texture="grid.png"` for calibration patterns
- **Vehicle Headlights:** Realistic cone with falloff

**Implementation Priority:** 🟢 LOW - Specialized use cases

---

### Enhanced Tool: `set_day_night_cycle`

**Enhanced Signature:**
```python
set_day_night_cycle(
    cycle_duration: float = 60.0,  # Seconds for full 24hr cycle
    start_time: str = "sunrise",  # "sunrise", "noon", "sunset", "night"
    enabled: bool = True,

    # Precise Time Control
    time_of_day: Optional[float] = None,  # 0-24 hours (overrides start_time)

    # Astronomical Accuracy
    latitude: float = 0.0,  # Affects sun angle (-90 to 90)
    day_of_year: int = 172,  # 1-365 (172 = summer solstice)

    # Celestial Bodies
    include_moon: bool = False,
    moon_phase: float = 0.5,  # 0=new, 0.5=full, 1=new

    # Night Sky
    star_field: bool = False,
    star_intensity: float = 0.5,

    # Weather Integration
    cloud_cover: float = 0.0,  # 0.0-1.0
    cloud_speed: float = 0.1,

    # Atmosphere
    atmospheric_scattering: bool = False,  # Realistic sky colors

    # Animation Control
    transition_speed: str = "smooth",  # "smooth", "stepped", "instant"
    custom_schedule: Optional[List[Dict]] = None,  # Keyframe animation
) -> OperationResult
```

**Custom Schedule Example:**
```python
set_day_night_cycle(
    custom_schedule=[
        {'time': 0.0, 'preset': 'night'},
        {'time': 6.0, 'preset': 'sunrise'},
        {'time': 12.0, 'preset': 'noon'},
        {'time': 18.0, 'preset': 'sunset'},
        {'time': 24.0, 'preset': 'night'},
    ]
)
```

**Astronomical Accuracy Example:**
```python
# Simulate winter in Alaska (low sun angle)
set_day_night_cycle(
    latitude=64.0,  # Fairbanks, AK
    day_of_year=355,  # December 21
    atmospheric_scattering=True,
)
```

**Use Cases:**
- **Solar Panel Testing:** Accurate sun angles by latitude/date
- **Long-Duration Tests:** Full day/night cycles
- **Vision Algorithm Testing:** Test camera auto-exposure
- **Astronomical Research:** Moon phase, star fields

**Implementation Priority:** 🔴 HIGH - Critical for outdoor robotics

---

### New Tool: `create_lighting_preset`

**Signature:**
```python
create_lighting_preset(
    preset_name: str,
    base_preset: str = "noon",
    modifications: Dict[str, Any],
    save_to_library: bool = True,
) -> OperationResult
```

**Example:**
```python
# Create custom "golden hour" preset
create_lighting_preset(
    preset_name="golden_hour",
    base_preset="sunset",
    modifications={
        'sun_intensity': 0.8,
        'ambient': (0.6, 0.4, 0.3, 1.0),
        'temperature': 2500,
    }
)
```

**Implementation Priority:** 🟢 LOW - Convenience feature

---

### New Tool: `add_environment_effects`

**Signature:**
```python
add_environment_effects(
    effect_type: str,  # "rain", "snow", "fog", "sandstorm", "dust", "aurora"
    intensity: float = 0.5,  # 0.0-1.0
    duration: Optional[float] = None,  # Seconds (None = continuous)

    # Particle System
    particle_count: int = 1000,
    particle_size: float = 0.01,

    # Physics
    wind_direction: Optional[Dict[str, float]] = None,
    fall_speed: float = 1.0,  # For rain/snow

    # Appearance
    color_tint: Optional[Dict[str, float]] = None,

    # Sensor Impact
    affects_cameras: bool = True,
    affects_lidar: bool = True,
) -> OperationResult
```

**Use Cases:**
- **Weather Testing:** Test sensors in rain, snow, fog
- **Visibility Challenges:** Sandstorms for desert robotics
- **Visual Effects:** Aurora for northern environments

**Implementation Priority:** 🟡 MEDIUM - Important for sensor testing

---

## Module 4.5: Live Update Tools

### Enhanced Tool: `apply_force`

**Enhanced Signature:**
```python
apply_force(
    model_name: str,
    link_name: str,
    force: Dict[str, float],  # {x, y, z} in Newtons
    duration: float = 0.1,

    # Application Point
    application_point: Optional[Dict[str, float]] = None,  # Local offset

    # Force Characteristics
    force_type: str = "impulse",  # "impulse", "continuous", "sinusoidal"
    frequency: Optional[float] = None,  # Hz (for sinusoidal)
    ramp_up_time: float = 0.0,  # Gradual application

    # Reference Frame
    relative_to: str = "world",  # "world", "model", "link"
) -> OperationResult
```

**Use Cases:**
- **Wind Gusts:** `force_type="sinusoidal", frequency=0.5`
- **Collision Testing:** Sudden impulse forces
- **Vibration Testing:** Sinusoidal forces

**Implementation Priority:** 🟡 MEDIUM - Useful for dynamics testing

---

### Enhanced Tool: `set_wind`

**Enhanced Signature:**
```python
set_wind(
    direction: Dict[str, float],
    strength: float,

    # Turbulence
    turbulence: float = 0.0,  # Wind variance (0.0-1.0)

    # Gusts
    gusts_enabled: bool = False,
    gust_frequency: float = 5.0,  # Seconds between gusts
    gust_strength_multiplier: float = 2.0,
    gust_duration: float = 2.0,

    # Altitude Effects
    altitude_gradient: float = 0.0,  # Wind increases with height

    # Selective Application
    affected_models: Optional[List[str]] = None,  # Apply to specific models only

    # Wind Field Type
    wind_field_type: str = "uniform",  # "uniform", "vortex", "custom"
    vortex_center: Optional[Dict[str, float]] = None,  # If type="vortex"
) -> OperationResult
```

**Use Cases:**
- **Drone Testing:** Turbulence and gusts
- **Sailing Robots:** Vortex wind fields
- **Altitude Simulation:** Increasing wind with height

**Implementation Priority:** 🔴 HIGH - Critical for aerial robotics

---

### New Tool: `create_animated_object`

**Signature:**
```python
create_animated_object(
    model_name: str,
    animation_type: str,  # "orbit", "patrol", "oscillate", "follow_path", "random_walk"

    # Path Definition
    path_points: Optional[List[Dict[str, float]]] = None,
    orbit_center: Optional[Dict[str, float]] = None,  # For orbit
    orbit_radius: float = 5.0,

    # Motion Characteristics
    speed: float = 1.0,  # m/s
    loop: bool = True,
    start_immediately: bool = True,

    # Smoothing
    easing: str = "linear",  # "linear", "ease-in", "ease-out", "ease-in-out"

    # Orientation
    face_direction: bool = True,  # Orient along path
) -> OperationResult
```

**Use Cases:**
- **Moving Obstacles:** Patrol paths for navigation testing
- **Target Tracking:** Orbiting targets for camera systems
- **Traffic Simulation:** Animated "vehicles"

**Implementation Priority:** 🟡 MEDIUM - Useful for dynamic scenarios

---

### New Tool: `modify_model_appearance`

**Signature:**
```python
modify_model_appearance(
    model_name: str,
    property: str,  # "color", "transparency", "texture", "scale", "visible"
    value: Any,

    # Animation
    transition_duration: float = 0.0,  # Smooth transition (seconds)

    # Scope
    affect_children: bool = True,  # Apply to all child links
    specific_link: Optional[str] = None,  # Apply to one link only
) -> OperationResult
```

**Use Cases:**
- **Color Coding:** Change robot colors for identification
- **Hide/Show:** Toggle object visibility
- **Graduated Appearance:** Smooth color transitions

**Implementation Priority:** 🟢 LOW - Nice for visualization

---

### New Tool: `create_trigger_zone`

**Signature:**
```python
create_trigger_zone(
    zone_name: str,
    shape: str,  # "box", "sphere", "cylinder"
    position: Dict[str, float],
    size: Dict[str, float],

    # Trigger Conditions
    trigger_on: str = "enter",  # "enter", "exit", "stay"

    # Action
    callback_action: str,  # Python code or preset action
    action_params: Optional[Dict[str, Any]] = None,

    # Behavior
    one_shot: bool = False,  # Trigger only once
    cooldown_time: float = 0.0,  # Seconds between triggers

    # Filtering
    filter_models: Optional[List[str]] = None,  # Which models trigger

    # Visualization
    visible: bool = False,  # Show zone for debugging
    color: Optional[Dict[str, float]] = None,  # If visible
) -> OperationResult
```

**Example:**
```python
# Checkpoint zone
create_trigger_zone(
    zone_name="checkpoint_1",
    shape="box",
    position={'x': 10, 'y': 5, 'z': 0},
    size={'width': 2, 'height': 3, 'depth': 2},
    trigger_on="enter",
    callback_action="record_checkpoint",
    action_params={'checkpoint_id': 1},
    filter_models=["robot_1"],
)
```

**Use Cases:**
- **Waypoint Navigation:** Checkpoint zones
- **Training Scenarios:** Reward/penalty zones
- **Safety Testing:** Hazard zones

**Implementation Priority:** 🟡 MEDIUM - Useful for autonomous navigation

---

## Additional Tools for Consideration

### Tool: `create_benchmark_world`

**Signature:**
```python
create_benchmark_world(
    benchmark_type: str,  # "nav2_standard", "slam_office", "warehouse", "outdoor"
    difficulty: str = "medium",

    # Variations
    include_dynamic_obstacles: bool = False,
    include_people: bool = False,

    # Reproducibility
    seed: Optional[int] = None,

    # Metadata
    export_ground_truth: bool = True,  # Save reference map
    export_specification: bool = True,  # Save world parameters
) -> OperationResult
```

**Implementation Priority:** 🔴 HIGH - Critical for research benchmarking

---

### Tool: `spawn_robot_fleet`

**Signature:**
```python
spawn_robot_fleet(
    robot_type: str,
    count: int,
    formation: str = "line",  # "line", "grid", "circle", "random"
    spacing: float = 2.0,

    # Naming
    namespace_prefix: str = "robot",

    # Placement
    start_position: Dict[str, float] = {"x": 0, "y": 0, "z": 0},

    # Variation
    unique_sensors: bool = False,
    randomize_orientation: bool = False,

    # Reproducibility
    seed: Optional[int] = None,
) -> OperationResult
```

**Implementation Priority:** 🟡 MEDIUM - Useful for multi-robot research

---

### Tool: `create_sensor_test_environment`

**Signature:**
```python
create_sensor_test_environment(
    sensor_type: str,  # "camera", "lidar", "radar", "imu", "gps"
    test_scenarios: List[str],

    # Standard Test Targets
    target_objects: Optional[List[Dict]] = None,
    target_distances: List[float] = [1, 5, 10, 20],

    # Ground Truth
    ground_truth_markers: bool = True,
    export_calibration_data: bool = True,
) -> OperationResult
```

**Implementation Priority:** 🟡 MEDIUM - Useful for sensor validation

---

### Tool: `batch_world_updates`

**Signature:**
```python
batch_world_updates(
    updates: List[Dict[str, Any]],
    atomic: bool = True,  # All-or-nothing
    optimize_order: bool = True,  # Reorder for efficiency
    parallel_execution: bool = False,
) -> OperationResult
```

**Example:**
```python
batch_world_updates([
    {'action': 'spawn_model', 'params': {...}},
    {'action': 'set_lighting', 'params': {...}},
    {'action': 'modify_terrain', 'params': {...}},
])
```

**Implementation Priority:** 🔴 HIGH - Performance optimization

---

## Implementation Guidelines

### Parameter Validation Pattern

```python
def validate_enhanced_params(
    param_name: str,
    value: Any,
    valid_range: Optional[Tuple] = None,
    valid_options: Optional[List] = None,
) -> OperationResult:
    """Validate optional parameter values"""

    if valid_range and not (valid_range[0] <= value <= valid_range[1]):
        return failure_result(
            f"{param_name} must be between {valid_range[0]} and {valid_range[1]}",
            suggestion=f"Try adjusting to within valid range",
        )

    if valid_options and value not in valid_options:
        return failure_result(
            f"{param_name} must be one of: {', '.join(valid_options)}",
            suggestion=f"Available options: {valid_options}",
        )

    return success_result()
```

### Documentation Template

For each new optional parameter:

```python
"""
Args:
    new_param: Description of what it does
        - Valid range: X to Y
        - Default: Z (meaning...)
        - Use when: Specific use case
        - Interacts with: Related parameters

Example:
    >>> tool_name(
    ...     required_param="value",
    ...     new_param=0.5,  # Specific effect
    ... )
"""
```

### Backward Compatibility

All enhancements MUST:
1. ✅ Use `Optional[]` type hints for new parameters
2. ✅ Provide sensible defaults
3. ✅ Not change existing parameter behavior
4. ✅ Maintain existing OperationResult format
5. ✅ Work with ResultFilter pattern

---

## Testing Requirements

### For Each Enhancement

```python
@pytest.mark.parametric
def test_enhanced_parameter_validation():
    """Test new parameter accepts valid values"""

def test_enhanced_parameter_default():
    """Test backward compatibility with defaults"""

def test_enhanced_parameter_integration():
    """Test interaction with other parameters"""

def test_enhanced_parameter_edge_cases():
    """Test boundary values and error cases"""
```

---

## Migration Path

### Phase 1: High Priority (1-2 weeks)
- Reproducible seeds for all procedural tools
- Extended material library (10+ materials)
- Fog and atmospheric effects
- Advanced wind system
- Batch operations

### Phase 2: Medium Priority (1-2 weeks)
- Advanced obstacle course patterns
- Heightmap texture blending
- Animation system
- Trigger zones
- Shadow quality controls

### Phase 3: Low Priority (Future)
- AI-assisted generation
- Recording/playback
- Seasonal variations
- Advanced acoustics

---

## Estimated Impact

### Token Efficiency
- **No impact** - All enhancements work with existing ResultFilter pattern
- Optional parameters only sent when needed

### Performance
- **Positive** - Batch operations reduce round-trips
- **Neutral** - Optional parameters have minimal overhead
- **Controlled** - LOD and simplification options improve performance

### Developer Experience
- **Significantly improved** - More control and flexibility
- **Learning curve** - Well-documented with examples
- **Backward compatible** - Existing code continues to work

---

## Conclusion

These **50+ optional enhancements** significantly expand the capabilities of the Phase 4 tools while maintaining full backward compatibility. Priority should be given to:

1. **Reproducibility** (seeds) - Critical for research
2. **Material expansion** - Realistic simulations
3. **Weather/atmosphere** - Sensor testing
4. **Batch operations** - Performance
5. **Advanced obstacle courses** - Benchmarking

All enhancements follow the established OperationResult and ResultFilter patterns, ensuring they integrate seamlessly with the existing MCP architecture.

---

**Document Status:** ✅ COMPLETE
**Next Steps:** Review priorities, select subset for Phase 4 implementation
**Author:** Claude (Anthropic)
**Date:** 2025-11-17
