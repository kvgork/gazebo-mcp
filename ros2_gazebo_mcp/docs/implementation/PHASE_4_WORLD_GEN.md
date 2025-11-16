# Phase 4: World Generation & Manipulation Tools

**Status**: 🔵 Not Started
**Estimated Duration**: 5-7 days
**Prerequisites**: Phase 3 Complete

---

## Overview

Implement tools for dynamic world generation and manipulation, including object placement, terrain modification, lighting control, and live updates during simulation.

## Objectives

1. Create world file management tools
2. Implement object placement (static and dynamic)
3. Build terrain modification tools
4. Create comprehensive lighting control
5. Enable live world updates

---

## Module 4.1: World File Management

**File**: `src/gazebo_mcp/tools/world_generation.py`

### Tasks (0/5)

- [ ] **Tool**: `create_empty_world` - Generate basic world template
- [ ] **Tool**: `load_world` - Load existing .world file
- [ ] **Tool**: `save_world` - Export current world to file
- [ ] **Tool**: `list_world_templates` - Show available templates
- [ ] **Helper**: World SDF template generator

### Implementation Example

```python
@mcp_tool(
    name="create_empty_world",
    description="Create a new empty Gazebo world"
)
async def create_empty_world(
    world_name: str,
    ground_plane: bool = True,
    sun: bool = True
) -> Dict[str, Any]:
    """
    Create basic world with ground and lighting.

    Args:
        world_name: Name for the world
        ground_plane: Include ground plane
        sun: Include sun lighting

    Returns:
        World creation status and path
    """
    # Generate world SDF
    world_sdf = WorldTemplate.create_empty(
        name=world_name,
        include_ground=ground_plane,
        include_sun=sun
    )

    # Save to worlds directory
    world_path = Path(f"worlds/{world_name}.world")
    world_path.write_text(world_sdf)

    return {
        'success': True,
        'world_name': world_name,
        'path': str(world_path)
    }
```

---

## Module 4.2: Object Placement Tools

**File**: `src/gazebo_mcp/tools/object_placement.py`

### Tasks (0/10)

#### Static Objects
- [ ] **Tool**: `place_static_object` - Add static obstacle
- [ ] **Tool**: `place_box` - Spawn box obstacle
- [ ] **Tool**: `place_sphere` - Spawn sphere obstacle
- [ ] **Tool**: `place_cylinder` - Spawn cylinder obstacle
- [ ] **Tool**: `place_mesh` - Spawn custom mesh model

#### Dynamic Objects
- [ ] **Tool**: `place_dynamic_object` - Add physics object
- [ ] **Tool**: `create_obstacle_course` - Generate random obstacles
- [ ] **Tool**: `place_object_grid` - Place multiple objects in pattern

#### Utilities
- [ ] **Helper**: Generate primitive shape SDF
- [ ] **Helper**: Calculate non-overlapping positions

### Implementation Example

```python
@mcp_tool(
    name="place_static_object",
    description="Place a static object in the world"
)
async def place_static_object(
    object_type: str,  # box, sphere, cylinder
    name: str,
    x: float,
    y: float,
    z: float,
    size: Dict[str, float],  # {width, height, depth} or {radius}
    color: Optional[Dict[str, float]] = None  # {r, g, b, a}
) -> Dict[str, Any]:
    """
    Place static object (no physics).

    Args:
        object_type: Shape type
        name: Object name
        x, y, z: Position
        size: Dimensions
        color: RGBA color (0-1)

    Returns:
        Success status
    """
    # Generate SDF for primitive
    sdf = generate_primitive_sdf(
        shape=object_type,
        name=name,
        position=(x, y, z),
        size=size,
        color=color,
        static=True
    )

    # Spawn in Gazebo
    result = await bridge.spawn_entity(name=name, xml=sdf)
    return result

@mcp_tool(
    name="create_obstacle_course",
    description="Generate random obstacle course"
)
async def create_obstacle_course(
    num_obstacles: int = 10,
    area_size: float = 20.0,
    obstacle_types: List[str] = ["box", "cylinder"],
    min_distance: float = 1.0
) -> Dict[str, Any]:
    """
    Create random obstacle course.

    Args:
        num_obstacles: Number of obstacles
        area_size: Size of square area
        obstacle_types: Types to use
        min_distance: Minimum distance between obstacles

    Returns:
        List of spawned obstacles
    """
    spawned = []

    for i in range(num_obstacles):
        # Generate random position (avoiding overlaps)
        pos = generate_random_position(
            area_size=area_size,
            existing=spawned,
            min_distance=min_distance
        )

        # Random type and size
        obj_type = random.choice(obstacle_types)
        size = generate_random_size(obj_type)

        # Spawn
        name = f"obstacle_{i}"
        await place_static_object(
            object_type=obj_type,
            name=name,
            x=pos[0], y=pos[1], z=pos[2],
            size=size
        )
        spawned.append({'name': name, 'position': pos})

    return {'success': True, 'obstacles': spawned}
```

---

## Module 4.3: Terrain Modification Tools

**File**: `src/gazebo_mcp/tools/terrain_tools.py`

### Tasks (0/6)

- [ ] **Tool**: `set_ground_plane` - Configure ground surface
- [ ] **Tool**: `create_heightmap` - Generate terrain from heightmap
- [ ] **Tool**: `add_terrain_variation` - Add hills/valleys
- [ ] **Tool**: `set_surface_type` - Set material (grass, sand, etc.)
- [ ] **Helper**: Heightmap image generator
- [ ] **Helper**: Material/texture library

### Surface Types

Support for:
- Grass (green, medium friction)
- Concrete (gray, high friction)
- Sand (tan, low friction)
- Gravel (gray/brown, medium friction)
- Ice (white/blue, very low friction)
- Mud (brown, variable friction)

### Implementation Example

```python
@mcp_tool(
    name="create_heightmap",
    description="Create terrain from heightmap"
)
async def create_heightmap(
    heightmap_image: str,  # Path or base64
    scale: float = 1.0,
    elevation_range: float = 10.0,
    position: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Generate terrain from heightmap image.

    Args:
        heightmap_image: Image path or base64 data
        scale: Horizontal scale (meters per pixel)
        elevation_range: Max elevation difference (meters)
        position: Center position

    Returns:
        Heightmap creation status
    """
    # Load or decode heightmap
    heightmap = load_heightmap_image(heightmap_image)

    # Generate heightmap SDF
    sdf = generate_heightmap_sdf(
        image=heightmap,
        scale=scale,
        elevation=elevation_range,
        pos=position or {'x': 0, 'y': 0, 'z': 0}
    )

    # Spawn terrain
    result = await bridge.spawn_entity(name="terrain", xml=sdf)
    return result

@mcp_tool(
    name="set_surface_type",
    description="Set terrain surface material"
)
async def set_surface_type(
    surface_name: str,
    material: str,  # grass, concrete, sand, etc.
    friction: Optional[float] = None,
    restitution: Optional[float] = None
) -> Dict[str, Any]:
    """
    Configure surface material properties.

    Args:
        surface_name: Name of surface/ground model
        material: Material type
        friction: Custom friction coefficient
        restitution: Custom bounce coefficient

    Returns:
        Update status
    """
    # Get material properties
    mat_props = get_material_properties(material)
    if friction is not None:
        mat_props['friction'] = friction
    if restitution is not None:
        mat_props['restitution'] = restitution

    # Update surface properties
    await bridge.set_surface_properties(surface_name, mat_props)

    return {'success': True, 'material': material}
```

---

## Module 4.4: Lighting Control Tools

**File**: `src/gazebo_mcp/tools/lighting_tools.py`

### Tasks (0/10)

- [ ] **Tool**: `set_ambient_light` - Configure ambient lighting
- [ ] **Tool**: `add_directional_light` - Add sun/directional light
- [ ] **Tool**: `add_point_light` - Add point light source
- [ ] **Tool**: `add_spot_light` - Add spotlight
- [ ] **Tool**: `remove_light` - Delete light source
- [ ] **Tool**: `list_lights` - Get all light sources
- [ ] **Tool**: `set_day_night_cycle` - Animate lighting
- [ ] **Helper**: Day/night cycle presets
- [ ] **Helper**: Light intensity calculations
- [ ] **Helper**: Shadow configuration

### Day/Night Presets

```python
LIGHTING_PRESETS = {
    'sunrise': {
        'sun_intensity': 0.3,
        'sun_direction': (0.5, 0.0, 0.5),
        'ambient': (0.4, 0.3, 0.3, 1.0),
        'sky_color': (1.0, 0.5, 0.3)
    },
    'noon': {
        'sun_intensity': 1.0,
        'sun_direction': (0.0, 0.0, 1.0),
        'ambient': (0.8, 0.8, 0.8, 1.0),
        'sky_color': (0.5, 0.7, 1.0)
    },
    'sunset': {
        'sun_intensity': 0.4,
        'sun_direction': (-0.5, 0.0, 0.3),
        'ambient': (0.5, 0.3, 0.2, 1.0),
        'sky_color': (1.0, 0.4, 0.2)
    },
    'night': {
        'sun_intensity': 0.0,
        'ambient': (0.1, 0.1, 0.15, 1.0),
        'sky_color': (0.05, 0.05, 0.15)
    }
}
```

### Implementation Example

```python
@mcp_tool(
    name="set_day_night_cycle",
    description="Configure day/night cycle animation"
)
async def set_day_night_cycle(
    cycle_duration: float = 60.0,  # seconds
    start_time: str = "sunrise",
    enabled: bool = True
) -> Dict[str, Any]:
    """
    Set up day/night lighting cycle.

    Args:
        cycle_duration: Duration of full cycle (seconds)
        start_time: Starting time (sunrise, noon, sunset, night)
        enabled: Enable/disable animation

    Returns:
        Cycle configuration status
    """
    if not enabled:
        # Stop any running cycle
        stop_lighting_animation()
        return {'success': True, 'status': 'stopped'}

    # Get preset
    initial_lighting = LIGHTING_PRESETS.get(start_time, LIGHTING_PRESETS['noon'])

    # Start animation loop
    start_lighting_animation(
        duration=cycle_duration,
        initial=initial_lighting,
        presets=LIGHTING_PRESETS
    )

    return {
        'success': True,
        'cycle_duration': cycle_duration,
        'start_time': start_time
    }

@mcp_tool(
    name="add_directional_light",
    description="Add directional light (sun)"
)
async def add_directional_light(
    name: str,
    direction: Dict[str, float],  # {x, y, z}
    intensity: float = 1.0,
    color: Optional[Dict[str, float]] = None,  # {r, g, b}
    cast_shadows: bool = True
) -> Dict[str, Any]:
    """
    Add directional light source.

    Args:
        name: Light name
        direction: Light direction vector
        intensity: Light intensity (0-1)
        color: RGB color (0-1)
        cast_shadows: Enable shadow casting

    Returns:
        Light creation status
    """
    # Generate light SDF
    light_sdf = generate_directional_light_sdf(
        name=name,
        direction=(direction['x'], direction['y'], direction['z']),
        intensity=intensity,
        color=color or {'r': 1.0, 'g': 1.0, 'b': 1.0},
        shadows=cast_shadows
    )

    # Spawn light
    result = await bridge.spawn_entity(name=name, xml=light_sdf)
    return result
```

---

## Module 4.5: Live Update Tools

**File**: `src/gazebo_mcp/tools/live_update_tools.py`

### Tasks (0/5)

- [ ] **Tool**: `modify_model_property` - Update model on-the-fly
- [ ] **Tool**: `apply_force` - Apply forces to objects
- [ ] **Tool**: `apply_torque` - Apply torques
- [ ] **Tool**: `set_wind` - Configure wind forces
- [ ] **Tool**: `update_light_realtime` - Change lighting dynamically

### Implementation Example

```python
@mcp_tool(
    name="apply_force",
    description="Apply force to dynamic object"
)
async def apply_force(
    model_name: str,
    link_name: str,
    force: Dict[str, float],  # {x, y, z}
    duration: float = 0.1
) -> Dict[str, Any]:
    """
    Apply force to object.

    Args:
        model_name: Target model
        link_name: Target link
        force: Force vector (Newtons)
        duration: Force duration (seconds)

    Returns:
        Success status
    """
    # Create force service request
    result = await bridge.apply_body_wrench(
        model=model_name,
        link=link_name,
        force=(force['x'], force['y'], force['z']),
        torque=(0, 0, 0),
        duration=duration
    )

    return result
```

---

## World Template Utilities

**File**: `src/gazebo_mcp/utils/world_template.py`

### Tasks (0/3)

- [ ] Create `WorldTemplate` class
- [ ] Implement SDF world generation
- [ ] Add template library (empty, with obstacles, with terrain)

---

## Testing Requirements

### Unit Tests
- [ ] Test world file generation
- [ ] Test object placement validation
- [ ] Test heightmap processing
- [ ] Test lighting calculations
- [ ] Test SDF generation for all primitives

### Integration Tests
- [ ] Test complete world creation workflow
- [ ] Test obstacle course generation
- [ ] Test day/night cycle animation
- [ ] Test live force application
- [ ] Test terrain with robot navigation

### Test Files
- `tests/test_world_generation.py`
- `tests/test_object_placement.py`
- `tests/test_terrain_tools.py`
- `tests/test_lighting_tools.py`
- `tests/test_live_updates.py`

---

## Success Criteria

Phase 4 is complete when:

- [ ] All 25+ tasks implemented
- [ ] Can generate complete worlds programmatically
- [ ] Obstacle courses work correctly
- [ ] Terrain and heightmaps functional
- [ ] Day/night cycles animate properly
- [ ] Live updates work during simulation
- [ ] All tests pass (>80% coverage)
- [ ] Documentation complete

---

## Next Phase

Proceed to **Phase 5: Testing, Documentation & Examples**

---

**Estimated Completion**: 5-7 days
**Priority**: MEDIUM
