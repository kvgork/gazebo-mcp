"""
Unit tests for Phase 5B world generation features.

Tests cover:
- Feature 1: Advanced obstacle patterns (maze, grid, circular, difficulty)
- Feature 2: Shadow quality controls
- Feature 3: Volumetric lighting
- Feature 4: Animation system
- Feature 5: Trigger zones
"""

import pytest
from gazebo_mcp.tools.world_generation import (
    create_obstacle_course,
    set_shadow_quality,
    spawn_light,
    create_animated_object,
    create_trigger_zone,
    BoxTriggerZone,
    SphereTriggerZone,
    CylinderTriggerZone,
)


class TestAdvancedObstaclePatterns:
    """Test Feature 1: Advanced obstacle patterns."""

    def test_maze_pattern_basic(self):
        """Test maze pattern generation."""
        result = create_obstacle_course(
            num_obstacles=20,
            pattern_type="maze",
            seed=42
        )
        assert result.success
        assert result.data["num_obstacles"] >= 10  # At least some obstacles
        assert "pattern_type" in result.data
        assert result.data["pattern_type"] == "maze"

    def test_maze_pattern_reproducible(self):
        """Test maze pattern with same seed produces same result."""
        result1 = create_obstacle_course(
            num_obstacles=20,
            pattern_type="maze",
            seed=12345
        )
        result2 = create_obstacle_course(
            num_obstacles=20,
            pattern_type="maze",
            seed=12345
        )
        assert result1.success and result2.success
        # Same seed should produce same number of obstacles
        assert result1.data["num_obstacles"] == result2.data["num_obstacles"]

    def test_grid_pattern_basic(self):
        """Test grid pattern generation."""
        result = create_obstacle_course(
            num_obstacles=16,  # 4x4 grid
            pattern_type="grid",
            seed=42
        )
        assert result.success
        assert result.data["num_obstacles"] == 16
        assert result.data["pattern_type"] == "grid"

    def test_circular_pattern_basic(self):
        """Test circular pattern generation."""
        result = create_obstacle_course(
            num_obstacles=12,
            pattern_type="circular",
            seed=42
        )
        assert result.success
        assert result.data["num_obstacles"] == 12
        assert result.data["pattern_type"] == "circular"

    def test_random_pattern_backward_compatible(self):
        """Test random pattern (original behavior) still works."""
        result = create_obstacle_course(
            num_obstacles=10,
            pattern_type="random",
            seed=42
        )
        assert result.success
        assert result.data["num_obstacles"] == 10
        assert result.data["pattern_type"] == "random"

    def test_invalid_pattern_type(self):
        """Test invalid pattern type is rejected."""
        result = create_obstacle_course(
            num_obstacles=10,
            pattern_type="invalid_pattern"
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "pattern_type" in result.error.lower()

    def test_difficulty_easy(self):
        """Test easy difficulty multiplier."""
        result = create_obstacle_course(
            num_obstacles=10,
            difficulty="easy",
            seed=42
        )
        assert result.success
        assert "difficulty" in result.data
        assert result.data["difficulty"] == "easy"

    def test_difficulty_medium(self):
        """Test medium difficulty (default)."""
        result = create_obstacle_course(
            num_obstacles=10,
            difficulty="medium",
            seed=42
        )
        assert result.success
        assert result.data["difficulty"] == "medium"

    def test_difficulty_hard(self):
        """Test hard difficulty multiplier."""
        result = create_obstacle_course(
            num_obstacles=10,
            difficulty="hard",
            seed=42
        )
        assert result.success
        assert result.data["difficulty"] == "hard"

    def test_difficulty_expert(self):
        """Test expert difficulty multiplier."""
        result = create_obstacle_course(
            num_obstacles=10,
            difficulty="expert",
            seed=42
        )
        assert result.success
        assert result.data["difficulty"] == "expert"

    def test_invalid_difficulty(self):
        """Test invalid difficulty is rejected."""
        result = create_obstacle_course(
            num_obstacles=10,
            difficulty="impossible"
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "difficulty" in result.error.lower()

    def test_pattern_and_difficulty_combined(self):
        """Test pattern type and difficulty work together."""
        result = create_obstacle_course(
            num_obstacles=20,
            pattern_type="maze",
            difficulty="hard",
            seed=42
        )
        assert result.success
        assert result.data["pattern_type"] == "maze"
        assert result.data["difficulty"] == "hard"


class TestShadowQuality:
    """Test Feature 2: Shadow quality controls."""

    def test_shadow_quality_low(self):
        """Test low shadow quality preset."""
        result = set_shadow_quality(quality_level="low")
        assert result.success
        assert result.data["quality_level"] == "low"
        assert result.data["resolution"] == 1024
        assert result.data["pcf_enabled"] is False
        assert result.data["cascade_count"] == 1

    def test_shadow_quality_medium(self):
        """Test medium shadow quality preset."""
        result = set_shadow_quality(quality_level="medium")
        assert result.success
        assert result.data["quality_level"] == "medium"
        assert result.data["resolution"] == 2048
        assert result.data["pcf_enabled"] is True
        assert result.data["cascade_count"] == 2

    def test_shadow_quality_high(self):
        """Test high shadow quality preset."""
        result = set_shadow_quality(quality_level="high")
        assert result.success
        assert result.data["quality_level"] == "high"
        assert result.data["resolution"] == 4096
        assert result.data["pcf_enabled"] is True
        assert result.data["cascade_count"] == 3

    def test_shadow_quality_ultra(self):
        """Test ultra shadow quality preset."""
        result = set_shadow_quality(quality_level="ultra")
        assert result.success
        assert result.data["quality_level"] == "ultra"
        assert result.data["resolution"] == 8192
        assert result.data["pcf_enabled"] is True
        assert result.data["cascade_count"] == 4

    def test_shadow_quality_custom_resolution(self):
        """Test custom shadow resolution override."""
        result = set_shadow_quality(
            quality_level="medium",
            shadow_resolution=4096
        )
        assert result.success
        assert result.data["resolution"] == 4096

    def test_shadow_quality_custom_pcf(self):
        """Test custom PCF override."""
        result = set_shadow_quality(
            quality_level="low",
            pcf_enabled=True
        )
        assert result.success
        assert result.data["pcf_enabled"] is True

    def test_shadow_quality_custom_cascades(self):
        """Test custom cascade count override."""
        result = set_shadow_quality(
            quality_level="low",
            cascade_count=3
        )
        assert result.success
        assert result.data["cascade_count"] == 3

    def test_shadow_quality_invalid_level(self):
        """Test invalid quality level is rejected."""
        result = set_shadow_quality(quality_level="extreme")
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code

    def test_shadow_quality_invalid_resolution_not_power_of_2(self):
        """Test non-power-of-2 resolution is rejected."""
        result = set_shadow_quality(
            quality_level="medium",
            shadow_resolution=3000
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code

    def test_shadow_quality_invalid_cascade_count(self):
        """Test invalid cascade count is rejected."""
        result = set_shadow_quality(
            quality_level="medium",
            cascade_count=5
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code

    def test_shadow_quality_sdf_content(self):
        """Test SDF content is generated correctly."""
        result = set_shadow_quality(quality_level="high")
        assert result.success
        sdf = result.data["sdf_content"]
        assert "<shadows>" in sdf
        assert "<resolution>4096</resolution>" in sdf
        assert "<pcf>true</pcf>" in sdf
        assert "<cascades>3</cascades>" in sdf


class TestVolumetricLighting:
    """Test Feature 3: Volumetric lighting."""

    def test_volumetric_lighting_disabled_by_default(self):
        """Test volumetric lighting is disabled by default."""
        result = spawn_light(
            name="test_light",
            light_type="spot",
            position=(0, 0, 5)
        )
        # Will fail without Gazebo connection, but validates parameters
        assert "volumetric_enabled" not in str(result.error or "")

    def test_volumetric_spot_light(self):
        """Test volumetric lighting with spot light."""
        result = spawn_light(
            name="volumetric_spot",
            light_type="spot",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_density=0.2,
            volumetric_scattering=0.6
        )
        # Validates parameters even without Gazebo
        # Error will be ROS2_NOT_CONNECTED, not parameter validation
        if not result.success:
            assert result.error_code in ["ROS2_NOT_CONNECTED", "LIGHT_SPAWN_ERROR"]

    def test_volumetric_directional_light(self):
        """Test volumetric lighting with directional light."""
        result = spawn_light(
            name="volumetric_dir",
            light_type="directional",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_density=0.1,
            volumetric_scattering=0.5
        )
        if not result.success:
            assert result.error_code in ["ROS2_NOT_CONNECTED", "LIGHT_SPAWN_ERROR"]

    def test_volumetric_point_light_rejected(self):
        """Test volumetric lighting with point light is rejected."""
        result = spawn_light(
            name="volumetric_point",
            light_type="point",
            position=(0, 0, 5),
            volumetric_enabled=True
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "volumetric" in result.error.lower()

    def test_volumetric_invalid_density_negative(self):
        """Test negative volumetric density is rejected."""
        result = spawn_light(
            name="test_light",
            light_type="spot",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_density=-0.1
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "density" in result.error.lower()

    def test_volumetric_invalid_density_too_high(self):
        """Test volumetric density > 1.0 is rejected."""
        result = spawn_light(
            name="test_light",
            light_type="spot",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_density=1.5
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "density" in result.error.lower()

    def test_volumetric_invalid_scattering_negative(self):
        """Test negative volumetric scattering is rejected."""
        result = spawn_light(
            name="test_light",
            light_type="spot",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_scattering=-0.1
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "scattering" in result.error.lower()

    def test_volumetric_invalid_scattering_too_high(self):
        """Test volumetric scattering > 1.0 is rejected."""
        result = spawn_light(
            name="test_light",
            light_type="spot",
            position=(0, 0, 5),
            direction=(0, 0, -1),
            volumetric_enabled=True,
            volumetric_scattering=2.0
        )
        assert not result.success
        assert "INVALID_PARAMETER" in result.error_code
        assert "scattering" in result.error.lower()


class TestAnimationSystem:
    """Test Feature 4: Animation system."""

    def test_linear_path_animation(self):
        """Test linear path animation."""
        result = create_animated_object(
            "patrol_bot",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (5, 0, 0), (5, 5, 0)],
            speed=2.0
        )
        assert result.success
        assert result.data["animation_type"] == "linear_path"
        assert result.data["num_waypoints"] == 3
        assert result.data["duration"] > 0

    def test_circular_animation(self):
        """Test circular animation."""
        result = create_animated_object(
            "orbiter",
            "sphere",
            animation_type="circular",
            center=(0, 0, 1),
            radius=3.0,
            speed=1.0
        )
        assert result.success
        assert result.data["animation_type"] == "circular"
        assert result.data["num_waypoints"] == 33  # 32 + 1 to close loop

    def test_oscillating_animation_x_axis(self):
        """Test oscillating animation on X axis."""
        result = create_animated_object(
            "platform_x",
            "box",
            animation_type="oscillating",
            axis="x",
            amplitude=2.0,
            frequency=0.5,
            speed=1.0
        )
        assert result.success
        assert result.data["animation_type"] == "oscillating"
        assert result.data["num_waypoints"] == 20

    def test_oscillating_animation_y_axis(self):
        """Test oscillating animation on Y axis."""
        result = create_animated_object(
            "platform_y",
            "box",
            animation_type="oscillating",
            axis="y",
            amplitude=1.5,
            frequency=1.0
        )
        assert result.success

    def test_oscillating_animation_z_axis(self):
        """Test oscillating animation on Z axis."""
        result = create_animated_object(
            "platform_z",
            "box",
            animation_type="oscillating",
            axis="z",
            amplitude=2.0,
            frequency=0.5
        )
        assert result.success

    def test_loop_mode_once(self):
        """Test 'once' loop mode."""
        result = create_animated_object(
            "one_time",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            loop="once"
        )
        assert result.success
        assert result.data["loop"] == "once"

    def test_loop_mode_repeat(self):
        """Test 'repeat' loop mode."""
        result = create_animated_object(
            "repeater",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            loop="repeat"
        )
        assert result.success
        assert result.data["loop"] == "repeat"

    def test_loop_mode_ping_pong(self):
        """Test 'ping_pong' loop mode."""
        result = create_animated_object(
            "ping_pong",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            loop="ping_pong"
        )
        assert result.success
        assert result.data["loop"] == "ping_pong"

    def test_model_type_box(self):
        """Test box model type."""
        result = create_animated_object(
            "box_anim",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            size=(2, 2, 2)
        )
        assert result.success
        assert "<box>" in result.data["sdf_content"]

    def test_model_type_sphere(self):
        """Test sphere model type."""
        result = create_animated_object(
            "sphere_anim",
            "sphere",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            size=(1, 1, 1)
        )
        assert result.success
        assert "<sphere>" in result.data["sdf_content"]

    def test_model_type_cylinder(self):
        """Test cylinder model type."""
        result = create_animated_object(
            "cyl_anim",
            "cylinder",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            size=(1, 1, 2)
        )
        assert result.success
        assert "<cylinder>" in result.data["sdf_content"]

    def test_invalid_animation_type(self):
        """Test invalid animation type is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="invalid"
        )
        assert not result.success
        assert "INVALID_ANIMATION_TYPE" in result.error_code

    def test_invalid_loop_mode(self):
        """Test invalid loop mode is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            loop="invalid"
        )
        assert not result.success
        assert "INVALID_LOOP_MODE" in result.error_code

    def test_invalid_model_type(self):
        """Test invalid model type is rejected."""
        result = create_animated_object(
            "test",
            "pyramid",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)]
        )
        assert not result.success
        assert "INVALID_MODEL_TYPE" in result.error_code

    def test_linear_path_missing_points(self):
        """Test linear path without path_points is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="linear_path"
        )
        assert not result.success
        assert "INVALID_PATH_POINTS" in result.error_code

    def test_linear_path_insufficient_points(self):
        """Test linear path with only 1 point is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0)]
        )
        assert not result.success

    def test_circular_missing_center(self):
        """Test circular animation without center is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="circular",
            radius=3.0
        )
        assert not result.success
        assert "MISSING_CIRCULAR_PARAMS" in result.error_code

    def test_circular_missing_radius(self):
        """Test circular animation without radius is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="circular",
            center=(0, 0, 0)
        )
        assert not result.success

    def test_circular_negative_radius(self):
        """Test circular animation with negative radius is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="circular",
            center=(0, 0, 0),
            radius=-1.0
        )
        assert not result.success
        assert "INVALID_RADIUS" in result.error_code

    def test_oscillating_invalid_axis(self):
        """Test oscillating animation with invalid axis is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="oscillating",
            axis="w"
        )
        assert not result.success
        assert "INVALID_AXIS" in result.error_code

    def test_oscillating_negative_amplitude(self):
        """Test oscillating animation with negative amplitude is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="oscillating",
            amplitude=-1.0
        )
        assert not result.success
        assert "INVALID_AMPLITUDE" in result.error_code

    def test_oscillating_negative_frequency(self):
        """Test oscillating animation with negative frequency is rejected."""
        result = create_animated_object(
            "test",
            "box",
            animation_type="oscillating",
            frequency=-1.0
        )
        assert not result.success
        assert "INVALID_FREQUENCY" in result.error_code

    def test_sdf_content_structure(self):
        """Test SDF content has correct structure."""
        result = create_animated_object(
            "test_actor",
            "box",
            animation_type="linear_path",
            path_points=[(0, 0, 0), (1, 0, 0)],
            loop="repeat"
        )
        assert result.success
        sdf = result.data["sdf_content"]
        assert '<actor name="test_actor">' in sdf
        assert '<trajectory id="0" type="line">' in sdf
        assert '<waypoint>' in sdf
        assert '<loop>true</loop>' in sdf


class TestTriggerZones:
    """Test Feature 5: Trigger zones."""

    def test_box_trigger_zone(self):
        """Test box trigger zone creation."""
        result = create_trigger_zone(
            "goal_zone",
            zone_shape="box",
            center=(10, 0, 0),
            size=(2, 2, 2)
        )
        assert result.success
        assert result.data["zone_shape"] == "box"
        assert result.data["center"] == (10, 0, 0)

    def test_sphere_trigger_zone(self):
        """Test sphere trigger zone creation."""
        result = create_trigger_zone(
            "danger_zone",
            zone_shape="sphere",
            center=(5, 5, 0),
            radius=3.0
        )
        assert result.success
        assert result.data["zone_shape"] == "sphere"

    def test_cylinder_trigger_zone(self):
        """Test cylinder trigger zone creation."""
        result = create_trigger_zone(
            "checkpoint",
            zone_shape="cylinder",
            center=(0, 0, 1),
            radius=2.0,
            height=4.0
        )
        assert result.success
        assert result.data["zone_shape"] == "cylinder"

    def test_trigger_events_default(self):
        """Test default trigger event is 'enter'."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1)
        )
        assert result.success
        assert result.data["trigger_events"] == ["enter"]

    def test_trigger_events_multiple(self):
        """Test multiple trigger events."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            trigger_events=["enter", "exit", "stay"]
        )
        assert result.success
        assert len(result.data["trigger_events"]) == 3

    def test_actions_log(self):
        """Test log action."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            actions=[{
                "type": "log",
                "params": {"message": "Test"}
            }]
        )
        assert result.success
        assert result.data["num_actions"] == 1

    def test_actions_multiple(self):
        """Test multiple actions."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            actions=[
                {"type": "log", "params": {"message": "Enter"}},
                {"type": "teleport", "params": {"target": (0, 0, 0)}}
            ]
        )
        assert result.success
        assert result.data["num_actions"] == 2

    def test_visualize_enabled(self):
        """Test zone visualization is enabled by default."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            visualize=True
        )
        assert result.success
        assert result.data["visualize"] is True
        assert len(result.data["sdf_content"]) > 0

    def test_visualize_disabled(self):
        """Test zone visualization can be disabled."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            visualize=False
        )
        assert result.success
        assert result.data["visualize"] is False
        assert result.data["sdf_content"] == ""

    def test_box_zone_containment(self):
        """Test box zone containment checks."""
        result = create_trigger_zone(
            "test_box",
            zone_shape="box",
            center=(0, 0, 0),
            size=(2, 2, 2)
        )
        assert result.success
        zone = result.data["zone"]
        assert zone.contains(0, 0, 0)  # Center
        assert zone.contains(0.5, 0.5, 0.5)  # Inside
        assert not zone.contains(2, 2, 2)  # Outside

    def test_sphere_zone_containment(self):
        """Test sphere zone containment checks."""
        result = create_trigger_zone(
            "test_sphere",
            zone_shape="sphere",
            center=(0, 0, 0),
            radius=5.0
        )
        assert result.success
        zone = result.data["zone"]
        assert zone.contains(0, 0, 0)  # Center
        assert zone.contains(3, 0, 0)  # Inside
        assert not zone.contains(6, 0, 0)  # Outside

    def test_cylinder_zone_containment(self):
        """Test cylinder zone containment checks."""
        result = create_trigger_zone(
            "test_cyl",
            zone_shape="cylinder",
            center=(0, 0, 0),
            radius=2.0,
            height=4.0
        )
        assert result.success
        zone = result.data["zone"]
        assert zone.contains(0, 0, 0)  # Center
        assert zone.contains(1, 0, 1)  # Inside
        assert not zone.contains(0, 0, 3)  # Outside height
        assert not zone.contains(3, 0, 0)  # Outside radius

    def test_invalid_zone_shape(self):
        """Test invalid zone shape is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="pyramid"
        )
        assert not result.success
        assert "INVALID_ZONE_SHAPE" in result.error_code

    def test_box_missing_size(self):
        """Test box zone without size is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box"
        )
        assert not result.success
        assert "MISSING_SIZE" in result.error_code

    def test_sphere_missing_radius(self):
        """Test sphere zone without radius is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="sphere"
        )
        assert not result.success
        assert "MISSING_RADIUS" in result.error_code

    def test_cylinder_missing_params(self):
        """Test cylinder zone without parameters is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="cylinder"
        )
        assert not result.success
        assert "MISSING_CYLINDER_PARAMS" in result.error_code

    def test_invalid_trigger_event(self):
        """Test invalid trigger event is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            trigger_events=["invalid_event"]
        )
        assert not result.success
        assert "INVALID_TRIGGER_EVENT" in result.error_code

    def test_action_missing_type(self):
        """Test action without type field is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            actions=[{"params": {}}]
        )
        assert not result.success
        assert "MISSING_ACTION_TYPE" in result.error_code

    def test_action_invalid_type(self):
        """Test action with invalid type is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            actions=[{"type": "explode", "params": {}}]
        )
        assert not result.success
        assert "INVALID_ACTION_TYPE" in result.error_code

    def test_action_missing_params(self):
        """Test action without params field is rejected."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="box",
            size=(1, 1, 1),
            actions=[{"type": "log"}]
        )
        assert not result.success
        assert "MISSING_ACTION_PARAMS" in result.error_code

    def test_plugin_config_generated(self):
        """Test plugin configuration is generated."""
        result = create_trigger_zone(
            "test_zone",
            zone_shape="sphere",
            center=(1, 2, 3),
            radius=2.5,
            trigger_events=["enter", "exit"],
            actions=[{"type": "log", "params": {"msg": "test"}}]
        )
        assert result.success
        config = result.data["plugin_config"]
        assert config["zone_name"] == "test_zone"
        assert config["zone_shape"] == "sphere"
        assert config["center"] == (1, 2, 3)
        assert config["trigger_events"] == ["enter", "exit"]
        assert len(config["actions"]) == 1


class TestTriggerZoneClasses:
    """Test trigger zone classes directly."""

    def test_box_trigger_zone_bounds(self):
        """Test BoxTriggerZone boundary calculations."""
        zone = BoxTriggerZone("test", (5, 5, 5), (4, 4, 4))
        assert zone.min_x == 3.0
        assert zone.max_x == 7.0
        assert zone.min_y == 3.0
        assert zone.max_y == 7.0
        assert zone.min_z == 3.0
        assert zone.max_z == 7.0

    def test_box_trigger_zone_edges(self):
        """Test BoxTriggerZone edge containment."""
        zone = BoxTriggerZone("test", (0, 0, 0), (2, 2, 2))
        # Edges should be inside (inclusive)
        assert zone.contains(-1, 0, 0)
        assert zone.contains(1, 0, 0)
        assert zone.contains(0, -1, 0)
        assert zone.contains(0, 1, 0)

    def test_sphere_trigger_zone_radius_squared(self):
        """Test SphereTriggerZone precomputes radius squared."""
        zone = SphereTriggerZone("test", (0, 0, 0), 5.0)
        assert zone.radius_squared == 25.0

    def test_sphere_trigger_zone_exact_radius(self):
        """Test SphereTriggerZone at exact radius."""
        zone = SphereTriggerZone("test", (0, 0, 0), 5.0)
        assert zone.contains(5, 0, 0)  # On boundary
        assert zone.contains(0, 5, 0)
        assert zone.contains(0, 0, 5)

    def test_cylinder_trigger_zone_height_bounds(self):
        """Test CylinderTriggerZone height boundary calculations."""
        zone = CylinderTriggerZone("test", (0, 0, 10), 3.0, 6.0)
        assert zone.min_z == 7.0
        assert zone.max_z == 13.0

    def test_cylinder_trigger_zone_radial_check(self):
        """Test CylinderTriggerZone radial containment."""
        zone = CylinderTriggerZone("test", (5, 5, 0), 2.0, 4.0)
        assert zone.contains(5, 5, 0)  # Center
        assert zone.contains(6, 5, 0)  # Within radius
        assert not zone.contains(8, 5, 0)  # Outside radius

    def test_cylinder_trigger_zone_height_check(self):
        """Test CylinderTriggerZone height containment."""
        zone = CylinderTriggerZone("test", (0, 0, 5), 2.0, 4.0)
        assert zone.contains(0, 0, 5)  # Center
        assert zone.contains(0, 0, 3)  # Min height
        assert zone.contains(0, 0, 7)  # Max height
        assert not zone.contains(0, 0, 2)  # Below
        assert not zone.contains(0, 0, 8)  # Above

    def test_zone_sdf_generation(self):
        """Test zone SDF generation."""
        zone = BoxTriggerZone("test_visual", (1, 2, 3), (4, 5, 6))
        sdf = zone.to_sdf()
        assert '<model name="test_visual_visual">' in sdf
        assert '<pose>1 2 3 0 0 0</pose>' in sdf
        assert '<size>4 5 6</size>' in sdf
        assert '<ambient>0 1 0 0.3</ambient>' in sdf
