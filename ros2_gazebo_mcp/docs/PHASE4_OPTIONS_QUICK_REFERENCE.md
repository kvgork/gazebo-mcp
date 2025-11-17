# Phase 4 Options Quick Reference

**Quick lookup guide for nice-to-have optional parameters**

---

## Priority Matrix

| Priority | Feature | Impact | Effort |
|----------|---------|--------|--------|
| 🔴 HIGH | Reproducible Seeds | Critical for research | Low |
| 🔴 HIGH | Extended Materials (10+) | Realistic testing | Medium |
| 🔴 HIGH | Fog & Weather Effects | Sensor testing | Medium |
| 🔴 HIGH | Advanced Wind System | Aerial robotics | Low |
| 🔴 HIGH | Batch Operations | Performance | Medium |
| 🔴 HIGH | Astronomical Day/Night | Outdoor robotics | Medium |
| 🔴 HIGH | Benchmark Worlds | Research | High |
| 🟡 MEDIUM | Obstacle Course Patterns | Testing variety | Medium |
| 🟡 MEDIUM | Animation System | Dynamic scenarios | High |
| 🟡 MEDIUM | Heightmap Multi-texture | Visual realism | Medium |
| 🟡 MEDIUM | Shadow Quality Controls | Vision tasks | Low |
| 🟡 MEDIUM | Trigger Zones | Interactive training | Medium |
| 🟢 LOW | AI-Assisted Generation | Future feature | Very High |
| 🟢 LOW | Recording/Playback | Nice to have | High |
| 🟢 LOW | Seasonal Variations | Long-term sims | High |

---

## Top 10 Most Requested Options

### 1. **Reproducible Random Seeds** 🔴
```python
create_obstacle_course(..., seed=42)
create_procedural_terrain(..., seed=42)
```
**Why:** Essential for benchmarking and reproducible research

---

### 2. **Extended Material Library** 🔴
```python
MATERIALS = [
    'grass', 'wet_grass', 'concrete', 'ice', 'sand', 'snow',
    'mud', 'gravel', 'asphalt', 'dirt', 'metal_plate',
    'rubber_mat', 'wood_floor', 'mars_soil', 'lunar_regolith'
]
```
**Why:** Realistic physics for diverse environments

---

### 3. **Fog and Atmospheric Effects** 🔴
```python
set_ambient_light(
    fog_enabled=True,
    fog_density=0.05,
    fog_color={'r': 0.7, 'g': 0.7, 'b': 0.7, 'a': 1.0}
)
```
**Why:** Test vision algorithms in challenging conditions

---

### 4. **Advanced Obstacle Course Patterns** 🟡
```python
create_obstacle_course(
    pattern="maze",  # or "grid", "circular", "spiral"
    difficulty_level="hard",  # "easy", "medium", "hard", "expert"
    seed=42
)
```
**Why:** Standardized navigation testing

---

### 5. **Advanced Wind System** 🔴
```python
set_wind(
    turbulence=0.3,
    gusts_enabled=True,
    gust_frequency=5.0,
    altitude_gradient=0.1
)
```
**Why:** Critical for drone/UAV testing

---

### 6. **Astronomical Day/Night Cycle** 🔴
```python
set_day_night_cycle(
    latitude=64.0,  # Geographic location
    day_of_year=172,  # Summer solstice
    include_moon=True,
    atmospheric_scattering=True
)
```
**Why:** Accurate solar panel/sensor testing

---

### 7. **Batch World Updates** 🔴
```python
batch_world_updates([
    {'action': 'spawn_model', 'params': {...}},
    {'action': 'set_lighting', 'params': {...}},
    {'action': 'modify_terrain', 'params': {...}},
])
```
**Why:** Performance optimization

---

### 8. **Advanced Material Properties** 🔴
```python
set_surface_type(
    material="grass",
    rolling_friction=0.05,  # For wheeled robots
    wetness=0.8,  # Affects appearance and friction
    particle_effects="splash"
)
```
**Why:** Realistic wheeled robot behavior

---

### 9. **Trigger Zones** 🟡
```python
create_trigger_zone(
    zone_name="checkpoint_1",
    shape="box",
    trigger_on="enter",
    callback_action="record_checkpoint"
)
```
**Why:** Interactive training scenarios

---

### 10. **Weather System Integration** 🔴
```python
add_environment_effects(
    effect_type="rain",  # or "snow", "fog", "sandstorm"
    intensity=0.7,
    affects_cameras=True,
    affects_lidar=True
)
```
**Why:** Comprehensive sensor robustness testing

---

## Module-by-Module Quick Reference

### 4.1 World File Management

| Option | Priority | Use Case |
|--------|----------|----------|
| `physics_engine` selection | 🟡 | Alternative physics |
| `gravity` customization | 🟡 | Moon/space sims |
| `background_color` | 🟢 | Visual customization |
| `initial_camera_pose` | 🟢 | Consistent views |

---

### 4.2 Object Placement

| Option | Priority | Use Case |
|--------|----------|----------|
| `seed` parameter | 🔴 | Reproducibility |
| `pattern` types | 🟡 | Structured testing |
| `difficulty_level` | 🟡 | Progressive training |
| `material_preset` | 🟡 | Realistic objects |
| `export_metadata` | 🔴 | Research documentation |

---

### 4.3 Terrain Tools

| Option | Priority | Use Case |
|--------|----------|----------|
| Extended materials (15+) | 🔴 | Diverse environments |
| `rolling_friction` | 🔴 | Wheeled robots |
| `texture_blending` | 🟡 | Visual realism |
| `procedural_terrain` | 🟡 | Quick world creation |
| `wetness` property | 🟡 | Weather effects |

---

### 4.4 Lighting Tools

| Option | Priority | Use Case |
|--------|----------|----------|
| `fog_enabled` | 🔴 | Vision testing |
| `latitude`/`day_of_year` | 🔴 | Astronomical accuracy |
| `shadow_resolution` | 🟡 | Shadow quality |
| `volumetric_enabled` | 🟢 | Cinematic effects |
| `temperature` (Kelvin) | 🟡 | Color accuracy |

---

### 4.5 Live Updates

| Option | Priority | Use Case |
|--------|----------|----------|
| `turbulence`/`gusts` | 🔴 | Aerial robotics |
| `batch_updates` | 🔴 | Performance |
| `animation_type` | 🟡 | Moving obstacles |
| `trigger_zones` | 🟡 | Interactive scenarios |

---

## Implementation Checklist

### Before Adding New Options

- [ ] Backward compatible (uses `Optional[]`)
- [ ] Sensible default provided
- [ ] Documentation includes:
  - [ ] Parameter description
  - [ ] Valid range
  - [ ] Default behavior
  - [ ] Use case examples
  - [ ] Interaction with other params
- [ ] Validation logic implemented
- [ ] Unit tests created
- [ ] Integration test updated
- [ ] Works with `OperationResult` pattern
- [ ] Works with `ResultFilter` pattern

---

## Code Pattern Template

```python
async def enhanced_tool(
    # Existing required params
    required_param: str,

    # Existing optional params
    existing_optional: float = 1.0,

    # NEW OPTIONAL PARAMETERS
    new_param: Optional[float] = None,  # None = use default
    new_enum: str = "default",  # Explicit default value
    new_advanced: Optional[Dict[str, Any]] = None,  # Complex types

) -> OperationResult:
    """
    Tool description.

    Args:
        required_param: Existing param
        existing_optional: Existing optional (default: 1.0)
        new_param: NEW - Description
            - Valid range: 0.0 to 1.0
            - Default: Calculated based on context
            - Use when: Specific scenario
        new_enum: NEW - Description
            - Options: "default", "option1", "option2"
            - Default: "default"
        new_advanced: NEW - Advanced configuration
            - Structure: {'key1': value1, 'key2': value2}
            - Default: Standard configuration
            - Use when: Expert users only

    Returns:
        OperationResult with enhanced data

    Example:
        >>> enhanced_tool(
        ...     required_param="value",
        ...     new_param=0.5,
        ...     new_enum="option1"
        ... )
    """

    # Validate new parameters
    if new_param is not None:
        if not (0.0 <= new_param <= 1.0):
            return failure_result(
                f"new_param must be between 0.0 and 1.0, got {new_param}",
                suggestion="Use value in valid range"
            )

    # Apply defaults
    if new_param is None:
        new_param = calculate_context_default()

    # Existing implementation...
    # Use new parameters as appropriate

    return success_result(data={...})
```

---

## Migration Strategy

### Week 1: High Priority Core
- [ ] Add `seed` parameter to all procedural tools
- [ ] Implement extended material library
- [ ] Add fog support to ambient lighting

### Week 2: High Priority Advanced
- [ ] Wind system with turbulence/gusts
- [ ] Astronomical day/night cycle
- [ ] Batch operations framework

### Week 3: Medium Priority
- [ ] Obstacle course patterns
- [ ] Shadow quality controls
- [ ] Basic animation system

### Week 4: Polish & Testing
- [ ] Comprehensive testing
- [ ] Documentation updates
- [ ] Example scenarios

---

## Quick Decision Tree

**Need reproducible environments?**
→ Add `seed` parameters (🔴 HIGH)

**Testing vision algorithms?**
→ Add fog, shadows, lighting effects (🔴 HIGH)

**Testing aerial robotics?**
→ Add wind turbulence/gusts (🔴 HIGH)

**Testing wheeled robots?**
→ Add rolling friction, extended materials (🔴 HIGH)

**Need dynamic scenarios?**
→ Add animation system, trigger zones (🟡 MEDIUM)

**Want visual realism?**
→ Add multi-texture terrains, volumetric lighting (🟡 MEDIUM)

**Future-proofing?**
→ Add AI generation, recording (🟢 LOW)

---

## Common Combinations

### Urban Outdoor Testing
```python
create_empty_world(background_color={'r': 0.5, 'g': 0.7, 'b': 1.0})
set_surface_type(material="asphalt", rolling_friction=0.01)
set_day_night_cycle(latitude=40.7, day_of_year=172)  # NYC, summer
add_environment_effects(effect_type="rain", intensity=0.3)
```

### Desert/Mars Robotics
```python
create_procedural_terrain(terrain_type="desert", seed=42)
set_surface_type(material="sand", particle_effects="dust")
set_ambient_light(fog_enabled=True, fog_color={'r': 0.8, 'g': 0.6, 'b': 0.4})
set_day_night_cycle(latitude=0, temperature=5500)
```

### Drone Testing Course
```python
create_obstacle_course(pattern="circular", seed=42, height_range=(3.0, 10.0))
set_wind(turbulence=0.3, gusts_enabled=True, altitude_gradient=0.1)
add_environment_effects(effect_type="fog", intensity=0.2)
```

### Indoor Warehouse
```python
create_benchmark_world(benchmark_type="warehouse", seed=42)
set_surface_type(material="concrete", rolling_friction=0.02)
add_point_light(..., flicker_enabled=True)  # Fluorescent lights
```

---

## Performance Considerations

### High Performance Options
- ✅ Batch operations
- ✅ Collision simplification
- ✅ LOD levels
- ✅ Shadow resolution control

### Moderate Performance Impact
- ⚠️ Volumetric lighting
- ⚠️ Particle effects
- ⚠️ Complex animations

### Consider Carefully
- ❌ High particle counts (>10,000)
- ❌ Many animated objects (>20)
- ❌ Very high shadow resolution (>4096)
- ❌ Real-time recording

---

## Testing Priorities

### Must Test
1. Seed reproducibility (same seed = same world)
2. Material property physics accuracy
3. Fog visibility ranges
4. Wind force calculations
5. Batch operation atomicity

### Should Test
6. Animation smoothness
7. Shadow quality levels
8. Trigger zone accuracy
9. Weather effect performance
10. Multi-texture blending

### Nice to Test
11. Volumetric light performance
12. Complex particle systems
13. Undo/redo consistency
14. AI generation quality

---

**Document Version:** 1.0
**Last Updated:** 2025-11-17
**Related:** `PHASE4_NICE_TO_HAVE_OPTIONS.md` (full specification)
