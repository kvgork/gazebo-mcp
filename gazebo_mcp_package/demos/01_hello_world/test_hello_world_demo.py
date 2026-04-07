#!/usr/bin/env python3
"""Tests for Hello World demo."""
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

    assert config.demo_name == "Hello World"
    assert config.gazebo_world == "empty"
    assert config.timeout == 30.0


def test_config_has_hello_box():
    """Test that hello_box model is configured."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    box_config = ConfigLoader.get_model_config(config, 'hello_box')
    assert box_config is not None
    assert 'pose' in box_config
    assert 'position' in box_config['pose']
    assert 'orientation' in box_config['pose']


def test_config_validates():
    """Test that config passes validation."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    is_valid, errors = ConfigLoader.validate_config(config)
    assert is_valid, f"Config validation failed: {errors}"


def test_box_pose_is_valid():
    """Test that box pose has correct format."""
    config_path = Path(__file__).parent / "config.yaml"
    config = ConfigLoader.load_demo_config(str(config_path))

    pose = ConfigLoader.get_model_pose(config, 'hello_box')
    assert pose is not None

    # Check position
    position = pose['position']
    assert isinstance(position, list)
    assert len(position) == 3
    assert all(isinstance(x, (int, float)) for x in position)

    # Check orientation
    orientation = pose['orientation']
    assert isinstance(orientation, list)
    assert len(orientation) == 4
    assert all(isinstance(x, (int, float)) for x in orientation)


def test_ros2_command_check():
    """Test ROS2 command validation (if ROS2 installed)."""
    result = DemoValidator.check_command_exists("ros2")
    # This may pass or fail depending on environment
    # Just verify we get a ValidationResult
    assert hasattr(result, 'passed')
    assert hasattr(result, 'component')
    assert hasattr(result, 'message')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
