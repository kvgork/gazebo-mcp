#!/usr/bin/env python3
"""Tests for Obstacle Course demo."""
import sys
import os
import pytest
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from framework import ConfigLoader, DemoValidator


def test_config_loads():
    """Test that config.yaml loads correctly."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    assert config.demo_name == "Obstacle Course Challenge"
    assert config.gazebo_world == "obstacle_course"
    assert config.timeout == 45.0


def test_config_has_robot():
    """Test that robot model is configured."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    robot_config = ConfigLoader.get_model_config(config, 'robot')
    assert robot_config is not None
    assert 'pose' in robot_config
    assert 'waypoints' in robot_config
    assert 'max_velocity' in robot_config


def test_config_has_obstacles():
    """Test that obstacle models are configured."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    # Check wall_1
    wall1_config = ConfigLoader.get_model_config(config, 'wall_1')
    assert wall1_config is not None
    assert 'geometry' in wall1_config
    assert wall1_config['geometry']['type'] == 'box'

    # Check wall_2
    wall2_config = ConfigLoader.get_model_config(config, 'wall_2')
    assert wall2_config is not None
    assert 'geometry' in wall2_config


def test_config_has_target():
    """Test that target zone is configured."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    target_config = ConfigLoader.get_model_config(config, 'target')
    assert target_config is not None
    assert 'geometry' in target_config
    assert target_config['geometry']['type'] == 'cylinder'


def test_robot_waypoints_valid():
    """Test that robot waypoints are valid."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    robot_config = ConfigLoader.get_model_config(config, 'robot')
    waypoints = robot_config['waypoints']

    # Should have at least 4 waypoints
    assert len(waypoints) >= 4

    # Each waypoint should be [x, y]
    for waypoint in waypoints:
        assert isinstance(waypoint, list)
        assert len(waypoint) == 2
        assert all(isinstance(coord, (int, float)) for coord in waypoint)


def test_config_validates():
    """Test that config passes validation."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    is_valid, errors = ConfigLoader.validate_config(config)
    assert is_valid, f"Config validation failed: {errors}"


def test_world_file_exists():
    """Test that world SDF file exists."""
    world_file = Path(__file__).parent / "worlds" / "obstacle_course.sdf"
    assert world_file.exists(), f"World file not found: {world_file}"


def test_robot_model_file_exists():
    """Test that robot model file exists."""
    robot_file = Path(__file__).parent / "models" / "simple_robot.sdf"
    assert robot_file.exists(), f"Robot model not found: {robot_file}"


def test_setup_script_exists():
    """Test that setup script exists."""
    setup_script = Path(__file__).parent / "setup.sh"
    assert setup_script.exists(), f"Setup script not found: {setup_script}"
    # Check if executable
    assert os.access(setup_script, os.X_OK), "Setup script is not executable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
