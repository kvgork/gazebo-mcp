#!/usr/bin/env python3
"""
Launch a provisioned Gazebo Harmonic world + ros_gz_bridge (P0-B, OWN mode).

Starts:
  1. ``gz sim`` on a rendered SDF world (produced by WorldProvisioner from
     ``worlds/provisioned.sdf.jinja``).
  2. A ``ros_gz_bridge parameter_bridge`` exposing the topics/services the
     Modern adapter needs — notably:
       - /world/<w>/pose/info  @ tf2_msgs/msg/TFMessage [ gz.msgs.Pose_V
         (pose readback path)
       - /world/<w>/control    @ ros_gz_interfaces/srv/ControlWorld
         (step / multi_step)

WRITE-ONLY this session: live verification deferred (no gz / ros_gz here).

Usage:
    ros2 launch provisioned_world.launch.py \
        world_name:=default world_sdf:=/tmp/gz_world_default_xxx.sdf
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _setup(context, *args, **kwargs):
    world_name = context.launch_configurations.get("world_name", "default")
    world_sdf = context.launch_configurations.get("world_sdf", "")

    # 1. Gazebo Harmonic simulator on the rendered SDF.
    gz_sim = ExecuteProcess(
        cmd=["gz", "sim", "-r", "-v", "3", world_sdf],
        output="screen",
    )

    # 2. ros_gz_bridge: map the topics/services the Modern adapter uses.
    bridge_args = [
        # Pose readback: gz.msgs.Pose_V -> tf2_msgs/msg/TFMessage (Gazebo -> ROS).
        f"/world/{world_name}/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
        # World control service (pause / multi_step for stepping).
        f"/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld",
        # Entity lifecycle services.
        f"/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity",
        f"/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity",
        f"/world/{world_name}/set_pose@ros_gz_interfaces/srv/SetEntityPose",
        # Clock (Gazebo -> ROS).
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
    ]

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="provisioned_world_bridge",
        output="screen",
        parameters=[{"use_sim_time": True}],
        arguments=bridge_args,
    )

    return [gz_sim, bridge]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world_name",
                default_value="default",
                description="Name of the provisioned Gazebo world.",
            ),
            DeclareLaunchArgument(
                "world_sdf",
                default_value="",
                description="Absolute path to the rendered world SDF file.",
            ),
            OpaqueFunction(function=_setup),
        ]
    )
