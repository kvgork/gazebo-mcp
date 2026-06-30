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

    # P1 actuation: revolute joints of the JETANK arm whose cmd_pos topics are
    # bridged below (continuous arm_base_to_arm_bearing_joint omitted — no
    # positional command). Keep in lockstep with worlds/provisioned.sdf.jinja
    # and models/jetank/manifest.json. WRITE-ONLY this session.
    jetank_revolute_joints = [
        "chassis_to_arm_bearing_joint",
        "arm_base_to_camera_joint",
        "arm_base_to_long_joint",
        "arm_long_to_short_joint",
    ]

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
        # --- P1 actuation (WRITE-ONLY; live-verify deferred) ---------------
        # Wrench commanding: ros_gz_interfaces/EntityWrench -> gz.msgs.EntityWrench
        # (ROS -> Gazebo). In Harmonic gz-sim 8 this topic is serviced by the
        # dedicated ApplyLinkWrench system loaded in the provisioned world (NOT
        # UserCommands). The wrench persists until cleared via .../wrench/clear.
        f"/world/{world_name}/wrench@ros_gz_interfaces/msg/EntityWrench]gz.msgs.EntityWrench",
    ]
    # Per-joint position command: std_msgs/Float64 -> gz.msgs.Double (ROS -> Gazebo),
    # consumed by the JointPositionController plugins in the provisioned world.
    for _joint in jetank_revolute_joints:
        bridge_args.append(
            f"/model/jetank/joint/{_joint}/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double"
        )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="provisioned_world_bridge",
        output="screen",
        parameters=[{"use_sim_time": True}],
        arguments=bridge_args,
    )

    # 3. gz_ros2_control / controller spawners (WRITE-ONLY this session; not run).
    #
    # The per-joint JointPositionController plugins in the provisioned world give
    # us topic-level position commands without ros2_control. For full
    # ros2_control trajectory/effort control (e.g. driving the JETANK arm via a
    # JointTrajectoryController for command_joint_trajectory), the live path adds
    # a gz_ros2_control plugin to the model SDF and spawns controllers here, e.g.:
    #
    #     from launch_ros.actions import Node
    #     joint_state_broadcaster = Node(
    #         package="controller_manager", executable="spawner",
    #         arguments=["joint_state_broadcaster",
    #                    "--controller-manager", "/controller_manager"],
    #         output="screen",
    #     )
    #     arm_traj_controller = Node(
    #         package="controller_manager", executable="spawner",
    #         arguments=["jetank_arm_trajectory_controller",
    #                    "--controller-manager", "/controller_manager"],
    #         output="screen",
    #     )
    #     # append joint_state_broadcaster, arm_traj_controller to the returned list
    #
    # Deferred until the JETANK SDF (with <ros2_control> + gz_ros2_control system)
    # and an arm controller YAML exist; not constructed/run in this session.

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
