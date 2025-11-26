#!/usr/bin/env python3
"""
Demo 6: World Generation Showcase

This demonstration showcases ALL world generation features:
- Obstacle patterns (maze, grid, circular)
- Advanced lighting (volumetric, shadows)
- Animations (linear, circular, oscillating)
- Trigger zones (box, sphere, cylinder)
- Environmental effects (fog, wind)
- Material system
- Benchmark worlds with reproducible seeds

This is a comprehensive showcase of the world generation capabilities.

Usage:
    python3 06_world_generation_showcase.py [--export-all]

Options:
    --export-all    Export all generated worlds to SDF files

Requirements:
    - ROS2 Gazebo MCP Server installed
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add src to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools.world_generation import WorldGenerator
from gazebo_mcp.utils.logger import setup_logger

# Setup logging
logger = setup_logger("world_showcase", level="INFO")


def print_banner(title: str):
    """Print a formatted banner."""
    width = 70
    print(f"\n{'=' * width}")
    print(f"{title:^{width}}")
    print(f"{'=' * width}\n")


def print_feature(name: str, status: str = "✅"):
    """Print a feature status."""
    print(f"{status} {name}")


def print_detail(detail: str):
    """Print a detail line."""
    print(f"   • {detail}")


def showcase_obstacle_patterns(export_path: Path = None) -> Dict[str, Any]:
    """Showcase different obstacle patterns."""
    print_banner("Obstacle Patterns Showcase")

    results = {}

    # 1. Maze Pattern
    print("\n1. Maze Pattern (High Difficulty)")
    print("-" * 70)

    gen = WorldGenerator()
    gen.create_world(name="maze_world", description="Maze obstacle pattern demo")
    gen.add_ground_plane(size=(20.0, 20.0), material="concrete")

    result = gen.add_obstacle_course(
        pattern="maze",
        difficulty="hard",
        num_obstacles=25,
        area_size=(15.0, 15.0),
        center=(0.0, 0.0)
    )

    print_feature("Maze pattern generated")
    print_detail(f"Obstacles: {result['obstacles_added']}")
    print_detail(f"Difficulty: Hard")
    print_detail(f"Area: 15m x 15m")

    if export_path:
        path = export_path / "maze_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    results['maze'] = result

    # 2. Grid Pattern
    print("\n2. Grid Pattern (Medium Difficulty)")
    print("-" * 70)

    gen = WorldGenerator()
    gen.create_world(name="grid_world", description="Grid obstacle pattern demo")
    gen.add_ground_plane(size=(20.0, 20.0), material="asphalt")

    result = gen.add_obstacle_course(
        pattern="grid",
        difficulty="medium",
        num_obstacles=20,
        area_size=(12.0, 12.0),
        center=(0.0, 0.0)
    )

    print_feature("Grid pattern generated")
    print_detail(f"Obstacles: {result['obstacles_added']}")
    print_detail(f"Difficulty: Medium")
    print_detail(f"Area: 12m x 12m")

    if export_path:
        path = export_path / "grid_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    results['grid'] = result

    # 3. Circular Pattern
    print("\n3. Circular Pattern (Low Difficulty)")
    print("-" * 70)

    gen = WorldGenerator()
    gen.create_world(name="circular_world", description="Circular obstacle pattern demo")
    gen.add_ground_plane(size=(20.0, 20.0), material="grass")

    result = gen.add_obstacle_course(
        pattern="circular",
        difficulty="low",
        num_obstacles=12,
        area_size=(10.0, 10.0),
        center=(0.0, 0.0)
    )

    print_feature("Circular pattern generated")
    print_detail(f"Obstacles: {result['obstacles_added']}")
    print_detail(f"Difficulty: Low")
    print_detail(f"Area: 10m x 10m")

    if export_path:
        path = export_path / "circular_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    results['circular'] = result

    return results


def showcase_lighting_effects(export_path: Path = None) -> Dict[str, Any]:
    """Showcase advanced lighting features."""
    print_banner("Advanced Lighting Showcase")

    results = {}

    # 1. Volumetric Lighting
    print("\n1. Volumetric Lighting (God Rays)")
    print("-" * 70)

    gen = WorldGenerator()
    gen.create_world(name="volumetric_world", description="Volumetric lighting demo")
    gen.add_ground_plane(size=(20.0, 20.0))

    # Add fog for volumetric effect
    gen.add_fog(
        density=0.05,
        color=(0.8, 0.8, 0.9),
        fog_type="linear",
        start=5.0,
        end=25.0
    )

    # Add spot light with volumetric effect
    result = gen.add_light(
        name="spotlight_volumetric",
        light_type="spot",
        pose={"position": [0, 0, 10], "orientation": [0, 1.57, 0]},
        intensity=2.0,
        spot_inner_angle=0.3,
        spot_outer_angle=0.5,
        volumetric_lighting=True,
        volumetric_density=1.0,
        volumetric_quality="high"
    )

    print_feature("Volumetric lighting configured")
    print_detail("Type: Spot light with god rays")
    print_detail("Quality: High")
    print_detail("Fog integration: Enabled")

    if export_path:
        path = export_path / "volumetric_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    results['volumetric'] = result

    # 2. Shadow Quality Presets
    print("\n2. Shadow Quality Comparison")
    print("-" * 70)

    for quality in ['low', 'medium', 'high', 'ultra']:
        gen = WorldGenerator()
        gen.create_world(name=f"shadows_{quality}", description=f"Shadow quality: {quality}")
        gen.add_ground_plane(size=(20.0, 20.0))

        result = gen.add_light(
            name="sun",
            light_type="directional",
            pose={"position": [0, 0, 10], "orientation": [0, 0, 0]},
            intensity=1.0,
            cast_shadows=True,
            shadow_quality=quality
        )

        print_feature(f"Shadow quality: {quality.upper()}")

        if export_path:
            path = export_path / f"shadows_{quality}_world.sdf"
            path.write_text(gen.export_world())

    results['shadows'] = {'presets': ['low', 'medium', 'high', 'ultra']}

    return results


def showcase_animations(export_path: Path = None) -> Dict[str, Any]:
    """Showcase animation system."""
    print_banner("Animation System Showcase")

    results = {}

    gen = WorldGenerator()
    gen.create_world(name="animation_world", description="Animation showcase")
    gen.add_ground_plane(size=(20.0, 20.0))

    # 1. Linear Animation
    print("\n1. Linear Path Animation")
    print("-" * 70)

    result1 = gen.add_animated_obstacle(
        name="linear_obstacle",
        animation_type="linear",
        path=[(0, 0, 0.5), (5, 0, 0.5), (5, 5, 0.5), (0, 5, 0.5)],
        duration=10.0,
        loop_mode="repeat",
        model_type="box",
        size=(1.0, 1.0, 1.0)
    )

    print_feature("Linear path animation added")
    print_detail("Path: Square (4 waypoints)")
    print_detail("Duration: 10 seconds")
    print_detail("Loop: Repeat")

    results['linear'] = result1

    # 2. Circular Animation
    print("\n2. Circular Animation")
    print("-" * 70)

    result2 = gen.add_animated_obstacle(
        name="circular_obstacle",
        animation_type="circular",
        center=(0, 0, 2.0),
        radius=3.0,
        duration=8.0,
        loop_mode="repeat",
        model_type="sphere",
        size=(0.5, 0.5, 0.5)
    )

    print_feature("Circular animation added")
    print_detail("Radius: 3.0m")
    print_detail("Duration: 8 seconds")
    print_detail("Model: Sphere")

    results['circular'] = result2

    # 3. Oscillating Animation
    print("\n3. Oscillating Animation")
    print("-" * 70)

    result3 = gen.add_animated_obstacle(
        name="oscillating_obstacle",
        animation_type="oscillating",
        center=(0, 0, 1.0),
        axis="z",
        amplitude=2.0,
        frequency=0.5,
        loop_mode="ping_pong",
        model_type="cylinder",
        size=(0.3, 0.3, 1.0)
    )

    print_feature("Oscillating animation added")
    print_detail("Axis: Z (vertical)")
    print_detail("Amplitude: 2.0m")
    print_detail("Frequency: 0.5 Hz")

    results['oscillating'] = result3

    if export_path:
        path = export_path / "animation_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    return results


def showcase_trigger_zones(export_path: Path = None) -> Dict[str, Any]:
    """Showcase trigger zone system."""
    print_banner("Trigger Zones Showcase")

    results = {}

    gen = WorldGenerator()
    gen.create_world(name="trigger_world", description="Trigger zones demo")
    gen.add_ground_plane(size=(20.0, 20.0))

    # 1. Box Trigger Zone
    print("\n1. Box Trigger Zone")
    print("-" * 70)

    result1 = gen.add_trigger_zone(
        name="box_trigger",
        zone_shape="box",
        center=(0, 0, 0.5),
        size=(2.0, 2.0, 1.0),
        events=["enter", "exit"],
        actions=[
            {"type": "log", "message": "Robot entered box zone"},
            {"type": "log", "message": "Robot exited box zone"}
        ],
        visualize=True
    )

    print_feature("Box trigger zone added")
    print_detail("Size: 2m x 2m x 1m")
    print_detail("Events: enter, exit")
    print_detail("Visualized: Yes")

    results['box'] = result1

    # 2. Sphere Trigger Zone
    print("\n2. Sphere Trigger Zone")
    print("-" * 70)

    result2 = gen.add_trigger_zone(
        name="sphere_trigger",
        zone_shape="sphere",
        center=(5, 5, 0.5),
        radius=1.5,
        events=["enter"],
        actions=[{"type": "log", "message": "Robot in sphere zone"}],
        visualize=True
    )

    print_feature("Sphere trigger zone added")
    print_detail("Radius: 1.5m")
    print_detail("Events: enter")

    results['sphere'] = result2

    # 3. Cylinder Trigger Zone
    print("\n3. Cylinder Trigger Zone")
    print("-" * 70)

    result3 = gen.add_trigger_zone(
        name="cylinder_trigger",
        zone_shape="cylinder",
        center=(-5, -5, 0.5),
        radius=1.0,
        height=2.0,
        events=["enter", "stay", "exit"],
        actions=[{"type": "log", "message": "Robot activity in cylinder"}],
        visualize=True
    )

    print_feature("Cylinder trigger zone added")
    print_detail("Radius: 1.0m, Height: 2.0m")
    print_detail("Events: enter, stay, exit")

    results['cylinder'] = result3

    if export_path:
        path = export_path / "trigger_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    return results


def showcase_environmental_effects(export_path: Path = None) -> Dict[str, Any]:
    """Showcase environmental effects."""
    print_banner("Environmental Effects Showcase")

    results = {}

    gen = WorldGenerator()
    gen.create_world(name="environment_world", description="Environmental effects demo")
    gen.add_ground_plane(size=(20.0, 20.0))

    # 1. Fog Effects
    print("\n1. Fog System")
    print("-" * 70)

    result1 = gen.add_fog(
        density=0.1,
        color=(0.7, 0.7, 0.8),
        fog_type="exponential",
        start=2.0,
        end=20.0
    )

    print_feature("Fog system configured")
    print_detail("Type: Exponential")
    print_detail("Density: 0.1")
    print_detail("Color: Light gray-blue")

    results['fog'] = result1

    # 2. Wind System
    print("\n2. Advanced Wind")
    print("-" * 70)

    result2 = gen.add_wind(
        base_velocity=(2.0, 1.0, 0.0),
        enable_turbulence=True,
        turbulence_intensity=0.5,
        enable_gusts=True,
        gust_frequency=0.1,
        gust_magnitude=3.0
    )

    print_feature("Wind system configured")
    print_detail("Base velocity: (2.0, 1.0, 0.0) m/s")
    print_detail("Turbulence: Enabled (intensity 0.5)")
    print_detail("Gusts: Enabled (freq 0.1, mag 3.0)")

    results['wind'] = result2

    if export_path:
        path = export_path / "environment_world.sdf"
        path.write_text(gen.export_world())
        print_detail(f"Exported to: {path.name}")

    return results


def showcase_benchmark_worlds(export_path: Path = None) -> Dict[str, Any]:
    """Showcase reproducible benchmark worlds."""
    print_banner("Benchmark Worlds Showcase")

    results = {}

    print("\nGenerating reproducible benchmark worlds...")
    print("-" * 70)

    seeds = [42, 123, 999]

    for seed in seeds:
        gen = WorldGenerator()
        gen.create_world(
            name=f"benchmark_{seed}",
            description=f"Reproducible benchmark world (seed={seed})"
        )
        gen.add_ground_plane(size=(20.0, 20.0))

        # Add reproducible obstacles
        result = gen.add_obstacle_course(
            pattern="random",
            difficulty="medium",
            num_obstacles=20,
            area_size=(15.0, 15.0),
            center=(0.0, 0.0),
            seed=seed  # Reproducible generation
        )

        print_feature(f"Benchmark world created (seed={seed})")
        print_detail(f"Obstacles: {result.get('obstacles_added', 20)}")
        print_detail("Reproducible: Yes")

        if export_path:
            path = export_path / f"benchmark_{seed}_world.sdf"
            path.write_text(gen.export_world())
            print_detail(f"Exported to: {path.name}")

        results[f'seed_{seed}'] = result

    print("\n✅ All benchmark worlds are reproducible!")
    print("   Running with the same seed will generate identical worlds.")

    return results


def print_summary(all_results: Dict[str, Any], export_path: Path = None):
    """Print comprehensive summary."""
    print_banner("World Generation Showcase Summary")

    print("Features Demonstrated:")
    print("")

    print("1. Obstacle Patterns:")
    print_detail("Maze pattern (high complexity)")
    print_detail("Grid pattern (structured)")
    print_detail("Circular pattern (open areas)")

    print("\n2. Advanced Lighting:")
    print_detail("Volumetric lighting (god rays)")
    print_detail("Shadow quality presets (4 levels)")
    print_detail("Multiple light types")

    print("\n3. Animation System:")
    print_detail("Linear path animations")
    print_detail("Circular animations")
    print_detail("Oscillating animations")
    print_detail("Multiple loop modes")

    print("\n4. Trigger Zones:")
    print_detail("Box zones")
    print_detail("Sphere zones")
    print_detail("Cylinder zones")
    print_detail("Event system (enter/stay/exit)")

    print("\n5. Environmental Effects:")
    print_detail("Fog system (multiple types)")
    print_detail("Wind with turbulence")
    print_detail("Dynamic gusts")

    print("\n6. Reproducibility:")
    print_detail("Benchmark worlds with seeds")
    print_detail("Consistent generation")
    print_detail("Metadata export")

    if export_path:
        print(f"\n📁 All worlds exported to: {export_path}")
        print(f"   Total files: {len(list(export_path.glob('*.sdf')))}")

    print("\n" + "=" * 70)
    print("✅ World Generation Showcase Complete!")
    print("=" * 70)


def main():
    """Run the world generation showcase."""
    parser = argparse.ArgumentParser(description="World Generation Showcase")
    parser.add_argument('--export-all', action='store_true',
                        help='Export all generated worlds to SDF files')
    args = parser.parse_args()

    export_path = None
    if args.export_all:
        export_path = PROJECT_ROOT / "examples/demos/worlds"
        export_path.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Worlds will be exported to: {export_path}\n")

    try:
        all_results = {}

        # Run all showcases
        all_results['obstacles'] = showcase_obstacle_patterns(export_path)
        all_results['lighting'] = showcase_lighting_effects(export_path)
        all_results['animations'] = showcase_animations(export_path)
        all_results['triggers'] = showcase_trigger_zones(export_path)
        all_results['environment'] = showcase_environmental_effects(export_path)
        all_results['benchmarks'] = showcase_benchmark_worlds(export_path)

        # Print summary
        print_summary(all_results, export_path)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Showcase interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Showcase failed")
        print(f"\n❌ Showcase failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
