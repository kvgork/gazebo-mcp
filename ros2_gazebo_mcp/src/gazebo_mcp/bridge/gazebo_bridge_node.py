"""
Gazebo Bridge Node for Gazebo MCP.

ROS2 node that interfaces with Gazebo simulation:
- Service clients for Gazebo services (spawn, delete, get state, etc.)
- Topic subscriptions for sensor data
- Transform listener for TF data
- Action clients for complex operations

This is a CRITICAL component - it provides the actual Gazebo integration.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..utils.exceptions import (
    GazeboNotRunningError,
    GazeboTimeoutError,
    ModelNotFoundError,
    ModelSpawnError,
    ModelDeleteError,
    ROS2ServiceError,
    ROS2TopicError
)
from ..utils.logger import get_logger
from ..utils.converters import pose_to_dict, dict_to_pose
from ..utils.validators import (
    validate_model_name,
    validate_position,
    validate_timeout
)


@dataclass
class ModelState:
    """Model state information."""
    name: str
    pose: Dict[str, Any]
    twist: Optional[Dict[str, Any]] = None
    state: str = "active"


class GazeboBridgeNode:
    """
    ROS2 node for Gazebo simulation interface.

    Provides high-level interface to Gazebo services and topics.

    Example:
        >>> node = GazeboBridgeNode(ros2_node)
        >>> models = node.get_model_list()
        >>> node.spawn_entity("turtlebot3", sdf_content, pose)
        >>> node.delete_entity("turtlebot3")
    """

    def __init__(self, ros2_node):
        """
        Initialize Gazebo bridge node.

        Args:
            ros2_node: ROS2 node instance from ConnectionManager
        """
        self.node = ros2_node
        self.logger = get_logger("gazebo_bridge")

        # Service clients (lazy initialization):
        self._spawn_entity_client = None
        self._delete_entity_client = None
        self._get_model_list_client = None
        self._get_model_state_client = None
        self._set_model_state_client = None
        self._pause_physics_client = None
        self._unpause_physics_client = None
        self._reset_simulation_client = None
        self._reset_world_client = None

        # Subscribers (lazy initialization):
        self._model_states_subscriber = None
        self._model_states_data = None

        # TF listener (lazy initialization):
        self._tf_buffer = None
        self._tf_listener = None

        self.logger.info("Initialized Gazebo bridge node")

    # Service client creation (lazy initialization):

    def _get_spawn_entity_client(self):
        """Get or create spawn_entity service client."""
        if self._spawn_entity_client is None:
            try:
                from gazebo_msgs.srv import SpawnEntity
                self._spawn_entity_client = self.node.create_client(
                    SpawnEntity,
                    '/spawn_entity'
                )
                self.logger.debug("Created spawn_entity service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/spawn_entity",
                    "Failed to import gazebo_msgs - ensure Gazebo ROS packages are installed"
                ) from e
        return self._spawn_entity_client

    def _get_delete_entity_client(self):
        """Get or create delete_entity service client."""
        if self._delete_entity_client is None:
            try:
                from gazebo_msgs.srv import DeleteEntity
                self._delete_entity_client = self.node.create_client(
                    DeleteEntity,
                    '/delete_entity'
                )
                self.logger.debug("Created delete_entity service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/delete_entity",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._delete_entity_client

    def _get_set_model_state_client(self):
        """Get or create set_model_state service client."""
        if self._set_model_state_client is None:
            try:
                from gazebo_msgs.srv import SetEntityState
                self._set_model_state_client = self.node.create_client(
                    SetEntityState,
                    '/gazebo/set_entity_state'
                )
                self.logger.debug("Created set_entity_state service client")
            except ImportError as e:
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._set_model_state_client

    def _get_model_states_subscriber(self):
        """Get or create model_states topic subscriber."""
        if self._model_states_subscriber is None:
            try:
                from gazebo_msgs.msg import ModelStates

                def callback(msg):
                    self._model_states_data = msg

                self._model_states_subscriber = self.node.create_subscription(
                    ModelStates,
                    '/gazebo/model_states',
                    callback,
                    10
                )
                self.logger.debug("Created model_states subscriber")
            except ImportError as e:
                raise ROS2TopicError(
                    "/gazebo/model_states",
                    "Failed to import gazebo_msgs"
                ) from e
        return self._model_states_subscriber

    # Entity management:

    def spawn_entity(
        self,
        name: str,
        xml_content: str,
        pose: Optional[Dict[str, Any]] = None,
        reference_frame: str = "world",
        timeout: float = 10.0
    ) -> bool:
        """
        Spawn an entity in Gazebo.

        Args:
            name: Entity name (must be unique)
            xml_content: SDF or URDF XML content
            pose: Spawn pose (position and orientation)
            reference_frame: Reference frame for pose
            timeout: Service call timeout

        Returns:
            True if spawn successful

        Raises:
            ModelSpawnError: If spawn fails
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running

        Example:
            >>> pose = {
            ...     "position": {"x": 1.0, "y": 2.0, "z": 0.0},
            ...     "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
            ... }
            >>> node.spawn_entity("my_robot", urdf_content, pose)
        """
        with self.logger.operation("spawn_entity", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            # Get service client:
            client = self._get_spawn_entity_client()

            # Wait for service:
            if not client.wait_for_service(timeout_sec=5.0):
                raise GazeboNotRunningError()

            # Create request:
            try:
                from gazebo_msgs.srv import SpawnEntity
                request = SpawnEntity.Request()
                request.name = name
                request.xml = xml_content
                request.reference_frame = reference_frame

                # Set pose:
                if pose:
                    request.initial_pose = dict_to_pose(pose)

            except Exception as e:
                raise ModelSpawnError(name, f"Failed to create request: {e}") from e

            # Call service:
            try:
                future = client.call_async(request)

                # Wait for response:
                start_time = time.time()
                while not future.done():
                    if time.time() - start_time > timeout:
                        raise GazeboTimeoutError("spawn_entity", timeout)
                    time.sleep(0.01)

                response = future.result()

                if not response.success:
                    raise ModelSpawnError(name, response.status_message)

                self.logger.log_model_event("spawned", name, reference_frame=reference_frame)
                return True

            except Exception as e:
                if isinstance(e, (ModelSpawnError, GazeboTimeoutError)):
                    raise
                raise ModelSpawnError(name, f"Service call failed: {e}") from e

    def delete_entity(
        self,
        name: str,
        timeout: float = 10.0
    ) -> bool:
        """
        Delete an entity from Gazebo.

        Args:
            name: Entity name
            timeout: Service call timeout

        Returns:
            True if deletion successful

        Raises:
            ModelDeleteError: If deletion fails
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running

        Example:
            >>> node.delete_entity("my_robot")
        """
        with self.logger.operation("delete_entity", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            # Get service client:
            client = self._get_delete_entity_client()

            # Wait for service:
            if not client.wait_for_service(timeout_sec=5.0):
                raise GazeboNotRunningError()

            # Create request:
            try:
                from gazebo_msgs.srv import DeleteEntity
                request = DeleteEntity.Request()
                request.name = name
            except Exception as e:
                raise ModelDeleteError(name, f"Failed to create request: {e}") from e

            # Call service:
            try:
                future = client.call_async(request)

                # Wait for response:
                start_time = time.time()
                while not future.done():
                    if time.time() - start_time > timeout:
                        raise GazeboTimeoutError("delete_entity", timeout)
                    time.sleep(0.01)

                response = future.result()

                if not response.success:
                    raise ModelDeleteError(name, response.status_message)

                self.logger.log_model_event("deleted", name)
                return True

            except Exception as e:
                if isinstance(e, (ModelDeleteError, GazeboTimeoutError)):
                    raise
                raise ModelDeleteError(name, f"Service call failed: {e}") from e

    def set_entity_state(
        self,
        name: str,
        pose: Optional[Dict[str, Any]] = None,
        twist: Optional[Dict[str, Any]] = None,
        reference_frame: str = "world",
        timeout: float = 10.0
    ) -> bool:
        """
        Set entity state (pose and/or twist) in Gazebo.

        Args:
            name: Entity name
            pose: Target pose {position: {x,y,z}, orientation: {x,y,z,w}} or {roll,pitch,yaw}
            twist: Target velocity {linear: {x,y,z}, angular: {x,y,z}}
            reference_frame: Reference frame for pose (default: "world")
            timeout: Service call timeout

        Returns:
            True if state set successfully

        Raises:
            ModelNotFoundError: If model doesn't exist
            GazeboTimeoutError: If service call times out
            GazeboNotRunningError: If Gazebo is not running
            ROS2ServiceError: If service call fails

        Example:
            >>> # Set position only
            >>> node.set_entity_state("robot", pose={"position": {"x": 1, "y": 2, "z": 0.5}})
            >>>
            >>> # Set position and velocity
            >>> node.set_entity_state(
            ...     "robot",
            ...     pose={"position": {"x": 1, "y": 2, "z": 0.5}},
            ...     twist={"linear": {"x": 0.5, "y": 0, "z": 0}}
            ... )
        """
        with self.logger.operation("set_entity_state", name=name):
            # Validate parameters:
            name = validate_model_name(name)
            timeout = validate_timeout(timeout)

            if pose is None and twist is None:
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    "Must provide either pose or twist (or both)"
                )

            # Get service client:
            client = self._get_set_model_state_client()

            # Wait for service:
            if not client.wait_for_service(timeout_sec=5.0):
                raise GazeboNotRunningError()

            # Create request:
            try:
                from gazebo_msgs.srv import SetEntityState
                from gazebo_msgs.msg import EntityState

                request = SetEntityState.Request()
                state = EntityState()
                state.name = name
                state.reference_frame = reference_frame

                # Set pose if provided:
                if pose:
                    from ..utils.converters import dict_to_pose
                    state.pose = dict_to_pose(pose)

                # Set twist if provided:
                if twist:
                    from ..utils.converters import dict_to_twist
                    state.twist = dict_to_twist(twist)

                request.state = state

            except Exception as e:
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    f"Failed to create request: {e}"
                ) from e

            # Call service:
            try:
                future = client.call_async(request)

                # Wait for response:
                start_time = time.time()
                while not future.done():
                    if time.time() - start_time > timeout:
                        raise GazeboTimeoutError("set_entity_state", timeout)
                    time.sleep(0.01)

                response = future.result()

                if not response.success:
                    # Check if model not found:
                    if "does not exist" in response.status_message.lower():
                        raise ModelNotFoundError(name)
                    raise ROS2ServiceError(
                        "/gazebo/set_entity_state",
                        response.status_message
                    )

                self.logger.log_model_event("state_updated", name, reference_frame=reference_frame)
                return True

            except Exception as e:
                if isinstance(e, (ModelNotFoundError, GazeboTimeoutError, ROS2ServiceError)):
                    raise
                raise ROS2ServiceError(
                    "/gazebo/set_entity_state",
                    f"Service call failed: {e}"
                ) from e

    def get_model_list(self, timeout: float = 5.0) -> List[ModelState]:
        """
        Get list of models in Gazebo.

        Subscribes to /gazebo/model_states topic to get current models.

        Args:
            timeout: Timeout for receiving model states

        Returns:
            List of ModelState objects

        Raises:
            GazeboNotRunningError: If Gazebo is not running
            GazeboTimeoutError: If timeout exceeded

        Example:
            >>> models = node.get_model_list()
            >>> for model in models:
            ...     print(f"{model.name}: {model.pose}")
        """
        with self.logger.operation("get_model_list"):
            # Validate timeout:
            timeout = validate_timeout(timeout)

            # Ensure subscriber is created:
            self._get_model_states_subscriber()

            # Wait for model states data:
            start_time = time.time()
            while self._model_states_data is None:
                if time.time() - start_time > timeout:
                    raise GazeboTimeoutError("get_model_list", timeout)
                time.sleep(0.01)

            # Convert to ModelState objects:
            models = []
            msg = self._model_states_data

            for i, name in enumerate(msg.name):
                # Skip ground_plane and other static models if needed:
                if name == "ground_plane":
                    continue

                model = ModelState(
                    name=name,
                    pose=pose_to_dict(msg.pose[i]),
                    twist={
                        "linear": {
                            "x": msg.twist[i].linear.x,
                            "y": msg.twist[i].linear.y,
                            "z": msg.twist[i].linear.z
                        },
                        "angular": {
                            "x": msg.twist[i].angular.x,
                            "y": msg.twist[i].angular.y,
                            "z": msg.twist[i].angular.z
                        }
                    },
                    state="active"
                )
                models.append(model)

            self.logger.info(f"Retrieved model list", count=len(models))
            return models

    def get_model_state(self, name: str, timeout: float = 5.0) -> Optional[ModelState]:
        """
        Get state of a specific model.

        Args:
            name: Model name
            timeout: Timeout for receiving data

        Returns:
            ModelState object or None if not found

        Example:
            >>> state = node.get_model_state("turtlebot3")
            >>> print(state.pose)
        """
        # Validate parameters:
        name = validate_model_name(name)

        # Get all models:
        models = self.get_model_list(timeout=timeout)

        # Find the requested model:
        for model in models:
            if model.name == name:
                return model

        return None

    # Physics control:

    def pause_physics(self, timeout: float = 5.0) -> bool:
        """
        Pause Gazebo physics simulation.

        Args:
            timeout: Service call timeout

        Returns:
            True if successful

        Example:
            >>> node.pause_physics()
        """
        # TODO: Implement when needed
        # Uses /pause_physics service
        self.logger.warning("pause_physics not yet implemented")
        return False

    def unpause_physics(self, timeout: float = 5.0) -> bool:
        """
        Unpause Gazebo physics simulation.

        Args:
            timeout: Service call timeout

        Returns:
            True if successful

        Example:
            >>> node.unpause_physics()
        """
        # TODO: Implement when needed
        # Uses /unpause_physics service
        self.logger.warning("unpause_physics not yet implemented")
        return False

    # Simulation control:

    def reset_simulation(self, timeout: float = 10.0) -> bool:
        """
        Reset Gazebo simulation to initial state.

        Args:
            timeout: Service call timeout

        Returns:
            True if successful

        Example:
            >>> node.reset_simulation()
        """
        # TODO: Implement when needed
        # Uses /reset_simulation service
        self.logger.warning("reset_simulation not yet implemented")
        return False

    def reset_world(self, timeout: float = 10.0) -> bool:
        """
        Reset world to initial state (models + physics).

        Args:
            timeout: Service call timeout

        Returns:
            True if successful

        Example:
            >>> node.reset_world()
        """
        # TODO: Implement when needed
        # Uses /reset_world service
        self.logger.warning("reset_world not yet implemented")
        return False

    # TF (Transform) operations:

    def get_transform(
        self,
        target_frame: str,
        source_frame: str,
        timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Get transform between two frames.

        Args:
            target_frame: Target frame name
            source_frame: Source frame name
            timeout: Lookup timeout

        Returns:
            Transform dictionary or None if not available

        Example:
            >>> tf = node.get_transform("map", "base_link")
            >>> print(tf["translation"])
        """
        # Initialize TF listener if needed:
        if self._tf_buffer is None:
            try:
                from tf2_ros import Buffer, TransformListener
                self._tf_buffer = Buffer()
                self._tf_listener = TransformListener(self._tf_buffer, self.node)
                self.logger.debug("Created TF listener")
            except ImportError:
                self.logger.error("tf2_ros not available")
                return None

        # Lookup transform:
        try:
            from rclpy.time import Time, Duration
            transform_stamped = self._tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                Time(),
                timeout=Duration(seconds=timeout)
            )

            # Convert to dictionary:
            from ..utils.converters import transform_to_dict
            return transform_to_dict(transform_stamped.transform)

        except Exception as e:
            self.logger.warning(
                f"Failed to get transform",
                target=target_frame,
                source=source_frame,
                error=str(e)
            )
            return None

    # Sensor data access:

    def subscribe_to_topic(
        self,
        topic_name: str,
        msg_type,
        callback,
        qos_profile=10
    ):
        """
        Subscribe to a ROS2 topic.

        Args:
            topic_name: Topic name
            msg_type: Message type class
            callback: Callback function
            qos_profile: QoS profile

        Returns:
            Subscription object

        Example:
            >>> from sensor_msgs.msg import LaserScan
            >>> def laser_callback(msg):
            ...     print(f"Laser ranges: {len(msg.ranges)}")
            >>> sub = node.subscribe_to_topic("/scan", LaserScan, laser_callback)
        """
        try:
            subscription = self.node.create_subscription(
                msg_type,
                topic_name,
                callback,
                qos_profile
            )
            self.logger.info(f"Subscribed to topic", topic=topic_name)
            return subscription
        except Exception as e:
            raise ROS2TopicError(topic_name, f"Failed to subscribe: {e}") from e

    # Cleanup:

    def destroy(self):
        """Clean up resources."""
        self.logger.info("Destroying Gazebo bridge node")

        # Destroy service clients:
        if self._spawn_entity_client:
            self.node.destroy_client(self._spawn_entity_client)
        if self._delete_entity_client:
            self.node.destroy_client(self._delete_entity_client)

        # Destroy subscribers:
        if self._model_states_subscriber:
            self.node.destroy_subscription(self._model_states_subscriber)


# Example usage:
if __name__ == "__main__":
    import rclpy
    from rclpy.executors import SingleThreadedExecutor

    # Initialize ROS2:
    rclpy.init()

    try:
        # Create node:
        node = rclpy.create_node('gazebo_bridge_test')

        # Create bridge:
        bridge = GazeboBridgeNode(node)

        # Get model list:
        print("Getting model list...")
        models = bridge.get_model_list(timeout=5.0)
        print(f"Found {len(models)} models:")
        for model in models:
            print(f"  - {model.name}: {model.pose['position']}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Cleanup:
        bridge.destroy()
        node.destroy_node()
        rclpy.shutdown()
