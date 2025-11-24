#!/usr/bin/env python3
"""
Launch file for bridging Modern Gazebo services to ROS2.

This launch file starts ros_gz_bridge to expose Modern Gazebo (Ignition)
services as ROS2 services, enabling the Modern Gazebo adapter to function.

Services bridged:
- /world/{world}/create - Spawn entities
- /world/{world}/remove - Delete entities
- /world/{world}/set_pose - Set entity poses
- /world/{world}/control - Control simulation (pause/unpause/reset)

Usage:
    ros2 launch gazebo_mcp gazebo_bridge.launch.py world_name:=empty
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_bridge(context, *args, **kwargs):
    """Launch bridge with world name from context."""

    # Get world name from launch configuration
    world_name = context.launch_configurations.get('world_name', 'default')

    # Bridge configuration for services
    # Format: service@ROS2_srv_type
    bridge_config = [
        # Spawn entity service
        f'/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity',

        # Delete entity service
        f'/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity',

        # Set entity pose service
        f'/world/{world_name}/set_pose@ros_gz_interfaces/srv/SetEntityPose',

        # Control world service (pause, unpause, reset)
        f'/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld',

        # Pose information topic (Gazebo -> ROS2)
        f'/world/{world_name}/pose/info[ros_gz_interfaces/msg/ParamVec',

        # Clock topic (Gazebo -> ROS2)
        '/clock[rosgraph_msgs/msg/Clock',
    ]

    # Create ros_gz_bridge node
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gazebo_ros_bridge',
        output='screen',
        parameters=[{
            'use_sim_time': True,
        }],
        arguments=bridge_config,
    )

    return [bridge_node]


def generate_launch_description():
    """Generate launch description for Gazebo bridge."""

    # Declare launch arguments
    world_name_arg = DeclareLaunchArgument(
        'world_name',
        default_value='default',
        description='Name of the Gazebo world to bridge'
    )

    return LaunchDescription([
        world_name_arg,
        OpaqueFunction(function=launch_bridge),
    ])
