#!/usr/bin/env python3
"""
TF relay node.

Subscribes to Ignition-bridged model TF topics (e.g. /model/turtlebot3/tf)
and republishes on /tf so standard TF2 listeners can use the transforms.

Usage:
    python3 scripts/tf_relay.py [--model turtlebot3]
"""

import argparse
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class TFRelay(Node):
    def __init__(self, model_name: str):
        super().__init__('tf_relay')
        self.pub = self.create_publisher(TFMessage, '/tf', 10)
        src = f'/model/{model_name}/tf'
        self.create_subscription(TFMessage, src, self._relay, 10)
        self.get_logger().info(f'Relaying {src} -> /tf')

    def _relay(self, msg: TFMessage):
        self.pub.publish(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='turtlebot3',
                        help='Ignition model name (default: turtlebot3)')
    args, _ = parser.parse_known_args()

    rclpy.init()
    node = TFRelay(args.model)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
