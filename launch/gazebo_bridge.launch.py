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

        # Pose information topic (Gazebo -> ROS2). FULL topic syntax is
        # `topic@ROS_type[GZ_type`; the `@ROS_type` before the `[` direction
        # symbol is REQUIRED. The earlier `pose/info[ros_gz_interfaces/msg/ParamVec`
        # was doubly wrong: (a) no `@ROS_type`, so parameter_bridge treated the
        # WHOLE argv as malformed, printed usage, and exited — bridging NOTHING,
        # incl. the 4 services above; (b) ParamVec is not what the adapter reads.
        # gz publishes gz.msgs.Pose_V here; the ros_gz mapping to
        # tf2_msgs/msg/TFMessage is what ModernGazeboAdapter subscribes to.
        # VERIFIED 2026-07-04: with this corrected syntax the 4 services bridge
        # and live spawn+step succeed.
        # KNOWN GAP (P0-B-real): the Pose_V->TFMessage bridge in this ros_gz
        # version emits EMPTY frame_id/child_frame_id, so the adapter's
        # child_frame_id-keyed pose cache can't resolve a model — pose readback
        # needs a redesign (bridge Pose_V preserving `name`, or read gz-transport
        # directly). Tracked in REMAINING_WORK Section B (P0-B-real).
        f'/world/{world_name}/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',

        # Clock topic (Gazebo -> ROS2) — same full `@ROS_type[GZ_type` form.
        '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
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
