# Phase 4: World Generation & Manipulation Tools

**Status**: 🟡 Partially Complete (Core Functions Implemented)
**Completion**: ~40% (4 of 5 modules with core features)
**Estimated Duration**: 2-3 days remaining
**Prerequisites**: Phase 3 Complete

---

## Quick Reference

**What you'll build**: Tools for programmatic world creation, terrain modification, object placement, and dynamic lighting

**Tasks**: 35+ across 5 modules
- Module 4.1: World File Management (5 tasks)
- Module 4.2: Object Placement (10 tasks)
- Module 4.3: Terrain Modification (6 tasks)
- Module 4.4: Lighting Control (10 tasks)
- Module 4.5: Live Updates (5 tasks)

**Success criteria**: Can generate complete worlds, create obstacle courses, modify terrain, animate day/night cycles, and update worlds live

**Verification**:
```bash
./verify_phase4.sh  # Automated verification
pytest tests/integration/test_world_creation.py  # Integration test
```

**Key deliverables**:
- ✅ **COMPLETE**: Random obstacle course creation (with seed support)
- ✅ **COMPLETE**: Material property system (6 materials: grass, concrete, ice, sand, wood, rubber)
- ✅ **COMPLETE**: Day/night lighting cycle calculations (smooth transitions)
- ✅ **COMPLETE**: Heightmap-based terrain generation (multiple patterns)
- ⚠️ **PARTIAL**: Programmatic world file generation (generation logic only, no Gazebo integration)
- ❌ **NOT STARTED**: Live world manipulation during simulation (apply_force, apply_torque)

---

## Learning Objectives

By completing this phase, you will understand:

1. **SDF World Structure**
   - How SDF world files are structured
   - World physics configuration
   - Scene and environment settings
   - Model inclusion and referencing

2. **Procedural Generation**
   - How to generate random obstacle layouts
   - Non-overlapping object placement algorithms
   - Heightmap terrain generation
   - Material property systems

3. **Lighting Systems**
   - Different light types (directional, point, spot)
   - Ambient vs. direct lighting
   - Shadow configuration
   - Day/night cycle animation

4. **Physics Properties**
   - Surface friction and restitution
   - Material properties for different surfaces
   - How terrain affects robot navigation
   - Force and torque application

5. **Dynamic World Modification**
   - How to update world state during simulation
   - Live object spawning and deletion
   - Real-time lighting changes
   - Physics parameter updates

---

## Core Principles for This Phase

### 1. Generate Valid SDF

**Always validate SDF before spawning**:
```python
def validate_sdf(sdf_xml: str) -> bool:
    """Validate SDF against schema"""
    try:
        tree = ET.fromstring(sdf_xml)
        # Check required elements
        assert tree.tag == 'sdf'
        assert 'version' in tree.attrib
        # More validation...
        return True
    except Exception as e:
        raise SDFValidationError(f"Invalid SDF: {e}")
```

### 2. Use Templates for Consistency

```python
# Create template library
WORLD_TEMPLATES = {
    'empty': WorldTemplate.create_empty(),
    'with_obstacles': WorldTemplate.create_with_obstacles(),
    'outdoor': WorldTemplate.create_outdoor_terrain(),
}

# Use template
world = WORLD_TEMPLATES['empty'].customize(
    ground_plane=True,
    sun_lighting=True
)
```

### 3. Handle Procedural Generation Safely

```python
def generate_random_position(
    existing_objects: List[Dict],
    area_size: float,
    min_distance: float
) -> Tuple[float, float, float]:
    """
    Generate non-overlapping random position.

    Includes maximum retry limit to prevent infinite loops.
    """
    max_retries = 1000
    for attempt in range(max_retries):
        pos = (
            random.uniform(-area_size/2, area_size/2),
            random.uniform(-area_size/2, area_size/2),
            0.5  # Height
        )

        # Check distance to existing objects
        if all(distance(pos, obj['pos']) >= min_distance
               for obj in existing_objects):
            return pos

    raise GenerationError(
        f"Could not find valid position after {max_retries} attempts. "
        f"Try reducing num_obstacles or increasing area_size."
    )
```

### 4. Provide Material Presets

```python
# Material property library
MATERIAL_PROPERTIES = {
    'grass': {
        'friction': 0.8,
        'restitution': 0.1,  # Low bounce
        'color': (0.2, 0.8, 0.2, 1.0),
        'description': 'Natural grass surface'
    },
    'concrete': {
        'friction': 1.0,
        'restitution': 0.01,  # Very low bounce
        'color': (0.5, 0.5, 0.5, 1.0),
        'description': 'Hard concrete surface'
    },
    'ice': {
        'friction': 0.1,
        'restitution': 0.9,  # High bounce
        'color': (0.8, 0.9, 1.0, 0.7),
        'description': 'Slippery ice surface'
    },
    # ... more materials
}
```

### 5. Test with Real Navigation

**Always test terrain with actual robot navigation**:
```python
@pytest.mark.integration
async def test_terrain_affects_navigation():
    """Verify different surfaces affect robot movement"""

    # Create world with grass
    await create_world_with_surface('grass')
    robot = await spawn_turtlebot3()

    # Measure movement on grass
    grass_distance = await measure_movement(robot, duration=5.0)

    # Change surface to ice
    await set_surface_type('ice')

    # Measure movement on ice (should be different)
    ice_distance = await measure_movement(robot, duration=5.0)

    # Verify surfaces have different effects
    assert abs(grass_distance - ice_distance) > 0.1
```

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

**File**: `src/gazebo_mcp/tools/world_generation.py` ✅ **EXISTS** (736 lines)

### Tasks (0/5) ❌ **NOT IMPLEMENTED**

- [ ] **Tool**: `create_empty_world` - Generate basic world template
- [ ] **Tool**: `load_world` - Load existing .world file
- [ ] **Tool**: `save_world` - Export current world to file
- [ ] **Tool**: `list_world_templates` - Show available templates
- [ ] **Helper**: World SDF template generator

**Note**: File exists with other features but world file management not yet implemented.

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

**File**: `src/gazebo_mcp/tools/world_generation.py` (combined with world_generation)

### Tasks (1/10) ⚠️ **PARTIALLY COMPLETE**

#### Static Objects
- [ ] **Tool**: `place_static_object` - Add static obstacle ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `place_box` - Spawn box obstacle ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `place_sphere` - Spawn sphere obstacle ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `place_cylinder` - Spawn cylinder obstacle ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `place_mesh` - Spawn custom mesh model ❌ **NOT IMPLEMENTED**

#### Dynamic Objects
- [ ] **Tool**: `place_dynamic_object` - Add physics object ❌ **NOT IMPLEMENTED**
- [x] **Tool**: `create_obstacle_course` - Generate random obstacles ✅ **COMPLETE** (with seed, types, spacing)
- [ ] **Tool**: `place_object_grid` - Place multiple objects in pattern ❌ **NOT IMPLEMENTED**

#### Utilities
- [x] **Helper**: Generate primitive shape SDF ✅ **COMPLETE** (part of obstacle_course)
- [x] **Helper**: Calculate non-overlapping positions ✅ **COMPLETE** (with min_distance validation)

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

**File**: `src/gazebo_mcp/tools/world_generation.py` (combined with world_generation)

### Tasks (3/6) ✅ **PARTIALLY COMPLETE**

- [ ] **Tool**: `set_ground_plane` - Configure ground surface ❌ **NOT IMPLEMENTED**
- [x] **Tool**: `generate_heightmap_terrain` - Generate terrain from heightmap ✅ **COMPLETE** (patterns: flat, ramp, hills, valley, canyon, random)
- [x] **Tool**: `add_terrain_variation` - Add hills/valleys ✅ **COMPLETE** (via heightmap patterns)
- [ ] **Tool**: `set_surface_type` - Set material (grass, sand, etc.) ❌ **NOT IMPLEMENTED** (materials exist but no Gazebo integration)
- [x] **Helper**: Heightmap generation ✅ **COMPLETE** (Diamond-Square algorithm)
- [x] **Helper**: Material/texture library ✅ **COMPLETE** (`list_materials()` - 6 materials with properties)

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

**File**: `src/gazebo_mcp/tools/world_generation.py` (combined with world_generation)

### Tasks (3/10) ⚠️ **PARTIALLY COMPLETE**

- [ ] **Tool**: `set_ambient_light` - Configure ambient lighting ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `add_directional_light` - Add sun/directional light ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `add_point_light` - Add point light source ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `add_spot_light` - Add spotlight ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `remove_light` - Delete light source ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `list_lights` - Get all light sources ❌ **NOT IMPLEMENTED**
- [x] **Tool**: `calculate_day_night_cycle` - Calculate lighting for time ✅ **COMPLETE** (smooth transitions, color calculations)
- [x] **Helper**: Day/night cycle presets ✅ **COMPLETE** (`create_lighting_preset()` - 6 presets: day, night, dawn, dusk, indoor, warehouse)
- [x] **Helper**: Light intensity calculations ✅ **COMPLETE** (intensity scaling, color interpolation)
- [ ] **Helper**: Shadow configuration ❌ **NOT IMPLEMENTED**

**Note**: Lighting calculations implemented but no Gazebo integration for applying lights.

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

**File**: `src/gazebo_mcp/tools/live_update_tools.py` ❌ **NOT CREATED**

### Tasks (0/5) ❌ **NOT IMPLEMENTED**

- [ ] **Tool**: `modify_model_property` - Update model on-the-fly ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `apply_force` - Apply forces to objects ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `apply_torque` - Apply torques ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `set_wind` - Configure wind forces ❌ **NOT IMPLEMENTED**
- [ ] **Tool**: `update_light_realtime` - Change lighting dynamically ❌ **NOT IMPLEMENTED**

**Note**: This module requires Gazebo bridge integration from Phase 3.

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

## SDF World Template Structure

### Complete World Template

**Essential for understanding world generation**:

```xml
<?xml version="1.0"?>
<sdf version="1.7">
  <world name="custom_world">

    <!-- Physics Configuration -->
    <physics type="ode">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>1000.0</real_time_update_rate>
      <gravity>0 0 -9.8</gravity>
    </physics>

    <!-- Scene Settings -->
    <scene>
      <ambient>0.4 0.4 0.4 1.0</ambient>
      <background>0.7 0.7 0.7 1.0</background>
      <shadows>true</shadows>
      <grid>false</grid>
    </scene>

    <!-- Ground Plane -->
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
          <surface>
            <friction>
              <ode>
                <mu>0.8</mu>  <!-- Friction coefficient -->
                <mu2>0.8</mu2>
              </ode>
            </friction>
          </surface>
        </collision>
        <visual name="visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.2 0.8 0.2 1</ambient>  <!-- Green grass -->
            <diffuse>0.2 0.8 0.2 1</diffuse>
            <specular>0.1 0.1 0.1 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <!-- Sun (Directional Light) -->
    <light name="sun" type="directional">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>1.0 1.0 1.0 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
    </light>

  </world>
</sdf>
```

### Primitive Object Templates

**Box obstacle**:
```xml
<model name="box_obstacle">
  <static>true</static>
  <pose>0 0 0.5 0 0 0</pose>  <!-- x y z roll pitch yaw -->
  <link name="link">
    <collision name="collision">
      <geometry>
        <box>
          <size>1 1 1</size>  <!-- width depth height -->
        </box>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <box>
          <size>1 1 1</size>
        </box>
      </geometry>
      <material>
        <ambient>0.8 0.1 0.1 1</ambient>  <!-- Red -->
        <diffuse>0.8 0.1 0.1 1</diffuse>
      </material>
    </visual>
  </link>
</model>
```

**Cylinder obstacle**:
```xml
<model name="cylinder_obstacle">
  <static>true</static>
  <pose>0 0 0.5 0 0 0</pose>
  <link name="link">
    <collision name="collision">
      <geometry>
        <cylinder>
          <radius>0.5</radius>
          <length>1.0</length>
        </cylinder>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <cylinder>
          <radius>0.5</radius>
          <length>1.0</length>
        </cylinder>
      </geometry>
      <material>
        <ambient>0.1 0.1 0.8 1</ambient>  <!-- Blue -->
        <diffuse>0.1 0.1 0.8 1</diffuse>
      </material>
    </visual>
  </link>
</model>
```

### Heightmap Terrain Template

```xml
<model name="heightmap_terrain">
  <static>true</static>
  <link name="link">
    <collision name="collision">
      <geometry>
        <heightmap>
          <uri>file://path/to/heightmap.png</uri>
          <size>100 100 10</size>  <!-- x y z (max elevation) -->
          <pos>0 0 0</pos>
        </heightmap>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <heightmap>
          <uri>file://path/to/heightmap.png</uri>
          <size>100 100 10</size>
          <texture>
            <diffuse>file://media/materials/textures/dirt.jpg</diffuse>
            <normal>file://media/materials/textures/dirt_normal.jpg</normal>
            <size>10</size>
          </texture>
        </heightmap>
      </geometry>
    </visual>
  </link>
</model>
```

---

## Success Criteria

### Automated Verification ✅

Run verification script:
```bash
./verify_phase4.sh
```

This checks:
- [ ] All 35+ tasks implemented with tests
- [ ] >80% code coverage for phase 4 modules
- [ ] Type checking passes (mypy --strict)
- [ ] Linting passes (ruff, black)
- [ ] SDF validation works correctly

### Manual Verification Checklist ✅

**World Generation**:
- [ ] Can create empty world programmatically
- [ ] Can load existing .world files
- [ ] Can save generated worlds to disk
- [ ] World templates work correctly
- [ ] Generated SDF validates successfully

**Object Placement**:
- [ ] Can place static objects (box, sphere, cylinder)
- [ ] Can place dynamic objects with physics
- [ ] Can generate random obstacle courses
- [ ] Objects don't overlap (collision detection works)
- [ ] Can place objects in grid patterns
- [ ] Custom mesh models can be loaded

**Terrain Modification**:
- [ ] Can set ground plane material properties
- [ ] Can create heightmap terrain from images
- [ ] Can modify surface types (grass, sand, ice, etc.)
- [ ] Different surfaces have correct friction values
- [ ] Terrain affects robot navigation correctly

**Lighting Control**:
- [ ] Can set ambient light levels
- [ ] Can add directional lights (sun)
- [ ] Can add point lights
- [ ] Can add spotlights
- [ ] Can remove/modify lights
- [ ] Day/night cycle animates smoothly
- [ ] Lighting presets (sunrise, noon, sunset, night) work
- [ ] Shadows render correctly

**Live Updates**:
- [ ] Can spawn objects during simulation
- [ ] Can delete objects during simulation
- [ ] Can modify object properties on-the-fly
- [ ] Can apply forces and torques
- [ ] Can change lighting in real-time
- [ ] World state remains consistent

### Integration Tests ✅

Run with real Gazebo:
```bash
# Start Gazebo
gz sim -s &

# Run integration tests
pytest tests/integration/test_world_creation.py -v
pytest tests/integration/test_obstacle_course.py -v
pytest tests/integration/test_day_night_cycle.py -v
```

Must pass:
- [ ] `test_complete_world_generation` - End-to-end world creation
- [ ] `test_obstacle_course_navigation` - Robot navigates obstacles
- [ ] `test_terrain_variations` - Different surfaces work
- [ ] `test_day_night_animation` - Lighting cycle functions
- [ ] `test_live_world_updates` - Real-time modifications work

### Code Quality Standards ✅

**CRITICAL**: All code must meet these standards:

- [ ] **Type Hints**: Every function fully typed
  ```python
  def create_heightmap(image: str, scale: float) -> Dict[str, Any]:
  ```

- [ ] **SDF Validation**: All generated SDF validated before use
  ```python
  sdf = generate_world_sdf(...)
  validate_sdf(sdf)  # Must pass
  ```

- [ ] **Error Handling**: Procedural generation handles edge cases
- [ ] **Templates**: Reusable templates for common patterns
- [ ] **Documentation**: SDF structure documented
- [ ] **Tests**: >80% coverage including integration tests

### Documentation ✅

- [ ] All tools documented in API reference
- [ ] SDF templates documented with examples
- [ ] Material properties reference complete
- [ ] Heightmap creation guide written
- [ ] Lighting system explained
- [ ] World building best practices documented

### Performance Targets ✅

| Operation | Target | Actual |
|-----------|--------|--------|
| Create empty world | < 1s | ___ |
| Generate obstacle course | < 5s | ___ |
| Create heightmap terrain | < 3s | ___ |
| Apply lighting changes | < 200ms | ___ |
| Live object spawn | < 500ms | ___ |

---

## Next Phase

Once all success criteria are met, proceed to:
**Phase 5: Testing, Documentation & Examples**

---

## Best Practices Summary

**DO** ✅:
- Validate all generated SDF before spawning
- Use templates for consistency
- Test with real robot navigation
- Provide material property presets
- Limit procedural generation retries
- Document SDF structure thoroughly
- Test day/night cycles visually

**DON'T** ❌:
- Generate invalid SDF
- Allow infinite loops in random placement
- Hardcode material properties
- Skip SDF validation
- Ignore terrain physics effects
- Create overlapping objects
- Forget to test lighting animations

---

**Estimated Completion**: 5-7 days
**Priority**: MEDIUM
