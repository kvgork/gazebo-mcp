#!/usr/bin/env python3
"""
World name proxy node.

Advertises ROS2 services for world='default' and forwards them to
the actual running Ignition world (auto-detected or set via --target).

Usage:
    python3 scripts/world_proxy.py [--source default] [--target empty]
"""

import sys
import argparse
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='default', help='World name the MCP bridge expects')
    parser.add_argument('--target', default='empty',   help='Actual running Ignition world name')
    args, _ = parser.parse_known_args()

    rclpy.init()

    from ros_gz_interfaces.srv import SpawnEntity, DeleteEntity, ControlWorld, SetEntityPose

    class WorldProxy(Node):
        def __init__(self):
            super().__init__('world_proxy')
            src = args.source
            tgt = args.target
            self.get_logger().info(f'Proxying /world/{src}/* -> /world/{tgt}/*')

            # Clients to the real world
            self.spawn_cli   = self.create_client(SpawnEntity,   f'/world/{tgt}/create')
            self.delete_cli  = self.create_client(DeleteEntity,  f'/world/{tgt}/remove')
            self.control_cli = self.create_client(ControlWorld,  f'/world/{tgt}/control')
            self.pose_cli    = self.create_client(SetEntityPose, f'/world/{tgt}/set_pose')

            # Servers pretending to be the source world
            self.create_service(SpawnEntity,   f'/world/{src}/create',  self._spawn)
            self.create_service(DeleteEntity,  f'/world/{src}/remove',  self._delete)
            self.create_service(ControlWorld,  f'/world/{src}/control', self._control)
            self.create_service(SetEntityPose, f'/world/{src}/set_pose', self._set_pose)

        def _relay(self, client, request, response):
            if not client.wait_for_service(timeout_sec=5.0):
                self.get_logger().error(f'Target service not available: {client.srv_name}')
                return response
            future = client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)
            if future.done() and future.result() is not None:
                return future.result()
            self.get_logger().warning('Relay call timed out or failed')
            return response

        def _spawn(self, req, res):
            self.get_logger().info(f'Proxying spawn: {req.entity_factory.name}')
            return self._relay(self.spawn_cli, req, res)

        def _delete(self, req, res):
            self.get_logger().info(f'Proxying delete')
            return self._relay(self.delete_cli, req, res)

        def _control(self, req, res):
            self.get_logger().info(f'Proxying control')
            return self._relay(self.control_cli, req, res)

        def _set_pose(self, req, res):
            self.get_logger().info(f'Proxying set_pose')
            return self._relay(self.pose_cli, req, res)

    node = WorldProxy()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
