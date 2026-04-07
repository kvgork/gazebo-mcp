"""
Connection Manager for Gazebo MCP.

Manages ROS2 node lifecycle, connection state, and health monitoring:
- ROS2 context and node initialization
- Connection state tracking (disconnected, connecting, connected, error)
- Auto-reconnect with exponential backoff
- Health monitoring (periodic connection checks)
- Thread-safe operations
- Error recovery

This is a CRITICAL component - all ROS2 communication goes through this manager.
"""

import time
import threading
from enum import Enum
from typing import Optional, Callable
from contextlib import contextmanager

from ..utils.exceptions import (
    ROS2NotConnectedError,
    ROS2ConnectionLostError,
    ROS2NodeError
)
from ..utils.logger import get_logger


class ConnectionState(Enum):
    """ROS2 connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class ConnectionManager:
    """
    Manages ROS2 connection lifecycle and health.

    Provides thread-safe ROS2 connection management with auto-reconnect,
    health monitoring, and error recovery.

    Example:
        >>> manager = ConnectionManager()
        >>> manager.connect()
        >>> if manager.is_connected():
        ...     # Use ROS2 node
        ...     pass
        >>> manager.disconnect()
    """

    def __init__(
        self,
        node_name: str = "gazebo_mcp_bridge",
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        reconnect_base_delay: float = 1.0,
        health_check_interval: float = 5.0
    ):
        """
        Initialize connection manager.

        Args:
            node_name: Name for the ROS2 node
            auto_reconnect: Enable automatic reconnection
            max_reconnect_attempts: Maximum reconnection attempts (0 = infinite)
            reconnect_base_delay: Base delay for exponential backoff (seconds)
            health_check_interval: Interval for health checks (seconds)
        """
        self.node_name = node_name
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        self.health_check_interval = health_check_interval

        self._state = ConnectionState.DISCONNECTED
        self._state_lock = threading.Lock()

        self._context = None
        self._node = None
        self._executor = None

        self._reconnect_count = 0
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_stop = threading.Event()

        self._on_connected_callbacks = []
        self._on_disconnected_callbacks = []
        self._on_error_callbacks = []

        self.logger = get_logger("connection_manager")

    @property
    def state(self) -> ConnectionState:
        """Get current connection state (thread-safe)."""
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, new_state: ConnectionState):
        """Set connection state and trigger callbacks (thread-safe)."""
        with self._state_lock:
            if self._state != new_state:
                old_state = self._state
                self._state = new_state
                self.logger.info(f"Connection state changed", old=old_state.value, new=new_state.value)

                # Trigger callbacks:
                if new_state == ConnectionState.CONNECTED:
                    for callback in self._on_connected_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            self.logger.error("Error in connected callback", error=str(e))
                elif new_state == ConnectionState.DISCONNECTED:
                    for callback in self._on_disconnected_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            self.logger.error("Error in disconnected callback", error=str(e))
                elif new_state == ConnectionState.ERROR:
                    for callback in self._on_error_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            self.logger.error("Error in error callback", error=str(e))

    def is_connected(self) -> bool:
        """Check if ROS2 connection is active."""
        return self.state == ConnectionState.CONNECTED

    def is_disconnected(self) -> bool:
        """Check if ROS2 connection is inactive."""
        return self.state == ConnectionState.DISCONNECTED

    def is_error(self) -> bool:
        """Check if ROS2 connection is in error state."""
        return self.state == ConnectionState.ERROR

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Establish ROS2 connection.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful

        Raises:
            ROS2NodeError: If connection fails

        Example:
            >>> manager = ConnectionManager()
            >>> manager.connect(timeout=5.0)
        """
        with self.logger.operation("ros2_connect"):
            if self.is_connected():
                self.logger.warning("Already connected to ROS2")
                return True

            self.state = ConnectionState.CONNECTING
            self._reconnect_count = 0

            try:
                # Import ROS2 packages:
                try:
                    import rclpy
                    from rclpy.executors import SingleThreadedExecutor
                except ImportError as e:
                    raise ROS2NodeError(
                        self.node_name,
                        "Failed to import rclpy - ensure ROS2 is sourced"
                    ) from e

                # Initialize ROS2 context:
                if not rclpy.ok():
                    rclpy.init()

                self._context = rclpy.get_default_context()

                # Create node:
                self._node = rclpy.create_node(self.node_name)
                self.logger.info("Created ROS2 node", node=self.node_name)

                # Create executor:
                self._executor = SingleThreadedExecutor()
                self._executor.add_node(self._node)

                # Start executor in separate thread:
                self._executor_thread = threading.Thread(
                    target=self._executor.spin,
                    daemon=True
                )
                self._executor_thread.start()

                # Update state:
                self.state = ConnectionState.CONNECTED
                self.logger.log_ros2_connection("connected", node=self.node_name)

                # Start health monitoring:
                if self.health_check_interval > 0:
                    self._start_health_monitoring()

                return True

            except Exception as e:
                self.state = ConnectionState.ERROR
                self.logger.exception("Failed to connect to ROS2", error=str(e))
                raise ROS2NodeError(self.node_name, f"Connection failed: {e}") from e

    def disconnect(self):
        """
        Disconnect from ROS2.

        Cleanly shuts down the ROS2 node, executor, and context.

        Example:
            >>> manager.disconnect()
        """
        with self.logger.operation("ros2_disconnect"):
            if self.is_disconnected():
                self.logger.warning("Already disconnected from ROS2")
                return

            try:
                # Stop health monitoring:
                self._stop_health_monitoring()

                # Stop executor:
                if self._executor:
                    self._executor.shutdown()
                    self._executor = None

                # Destroy node:
                if self._node:
                    try:
                        import rclpy
                        self._node.destroy_node()
                        self._node = None
                        self.logger.info("Destroyed ROS2 node", node=self.node_name)
                    except Exception as e:
                        self.logger.error("Error destroying node", error=str(e))

                # Shutdown context:
                if self._context:
                    try:
                        import rclpy
                        if rclpy.ok():
                            rclpy.shutdown()
                        self._context = None
                    except Exception as e:
                        self.logger.error("Error shutting down ROS2", error=str(e))

                self.state = ConnectionState.DISCONNECTED
                self.logger.log_ros2_connection("disconnected", node=self.node_name)

            except Exception as e:
                self.logger.exception("Error during disconnect", error=str(e))
                self.state = ConnectionState.ERROR

    def reconnect(self) -> bool:
        """
        Reconnect to ROS2.

        Uses exponential backoff for reconnection attempts.

        Returns:
            True if reconnection successful

        Example:
            >>> if not manager.is_connected():
            ...     manager.reconnect()
        """
        if self.is_connected():
            return True

        self.state = ConnectionState.RECONNECTING
        self._reconnect_count += 1

        # Check if exceeded max attempts:
        if self.max_reconnect_attempts > 0 and self._reconnect_count > self.max_reconnect_attempts:
            self.logger.error(
                "Exceeded maximum reconnection attempts",
                attempts=self._reconnect_count,
                max_attempts=self.max_reconnect_attempts
            )
            self.state = ConnectionState.ERROR
            return False

        # Calculate backoff delay:
        delay = self.reconnect_base_delay * (2 ** (self._reconnect_count - 1))
        delay = min(delay, 60.0)  # Cap at 60 seconds

        self.logger.log_ros2_connection(
            "reconnecting",
            attempt=self._reconnect_count,
            delay=f"{delay:.1f}s"
        )

        # Wait before reconnecting:
        time.sleep(delay)

        # Disconnect first:
        try:
            self.disconnect()
        except Exception as e:
            self.logger.error("Error during disconnect before reconnect", error=str(e))

        # Attempt reconnection:
        try:
            return self.connect()
        except Exception as e:
            self.logger.error("Reconnection failed", error=str(e), attempt=self._reconnect_count)
            return False

    def _start_health_monitoring(self):
        """Start background health monitoring thread."""
        if self._health_check_thread and self._health_check_thread.is_alive():
            return

        self._health_check_stop.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        self.logger.debug("Started health monitoring", interval=self.health_check_interval)

    def _stop_health_monitoring(self):
        """Stop background health monitoring thread."""
        if not self._health_check_thread:
            return

        self._health_check_stop.set()
        if self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=2.0)
        self._health_check_thread = None
        self.logger.debug("Stopped health monitoring")

    def _health_check_loop(self):
        """Background health monitoring loop."""
        while not self._health_check_stop.wait(self.health_check_interval):
            try:
                if not self._check_health():
                    self.logger.warning("Health check failed")

                    if self.auto_reconnect:
                        self.logger.info("Auto-reconnect enabled, attempting reconnection")
                        self.reconnect()
                    else:
                        self.state = ConnectionState.ERROR

            except Exception as e:
                self.logger.error("Error during health check", error=str(e))

    def _check_health(self) -> bool:
        """
        Check ROS2 connection health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if context is valid:
            if not self._context or not self._context.ok():
                self.logger.warning("ROS2 context is not OK")
                return False

            # Check if node is valid:
            if not self._node:
                self.logger.warning("ROS2 node is None")
                return False

            # Additional health checks can be added here
            # (e.g., check if specific topics/services are available)

            return True

        except Exception as e:
            self.logger.error("Health check exception", error=str(e))
            return False

    @contextmanager
    def ensure_connected(self):
        """
        Context manager to ensure ROS2 connection.

        Raises:
            ROS2NotConnectedError: If not connected and cannot connect

        Example:
            >>> with manager.ensure_connected():
            ...     # Use ROS2 node here
            ...     pass
        """
        if not self.is_connected():
            raise ROS2NotConnectedError("ROS2 connection required for this operation")

        try:
            yield
        except Exception as e:
            # Check if connection was lost during operation:
            if not self.is_connected():
                raise ROS2ConnectionLostError("ROS2 connection lost during operation") from e
            raise

    def get_node(self):
        """
        Get the ROS2 node instance.

        Returns:
            ROS2 node instance

        Raises:
            ROS2NotConnectedError: If not connected

        Example:
            >>> node = manager.get_node()
            >>> # Use node for ROS2 operations
        """
        if not self.is_connected():
            raise ROS2NotConnectedError("Must connect before getting node")

        if not self._node:
            raise ROS2NodeError(self.node_name, "Node is None despite connected state")

        return self._node

    # Callback registration:

    def on_connected(self, callback: Callable[[], None]):
        """Register callback for connection established event."""
        self._on_connected_callbacks.append(callback)

    def on_disconnected(self, callback: Callable[[], None]):
        """Register callback for disconnection event."""
        self._on_disconnected_callbacks.append(callback)

    def on_error(self, callback: Callable[[], None]):
        """Register callback for error state event."""
        self._on_error_callbacks.append(callback)

    # Cleanup:

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __del__(self):
        """Destructor - ensure cleanup."""
        try:
            if self.is_connected():
                self.disconnect()
        except Exception:
            pass  # Ignore errors during cleanup


# Example usage:
if __name__ == "__main__":
    # Basic usage:
    manager = ConnectionManager()

    try:
        # Connect:
        manager.connect()
        print(f"Connected! State: {manager.state.value}")

        # Use ROS2:
        with manager.ensure_connected():
            node = manager.get_node()
            print(f"Node name: {node.get_name()}")

        # Disconnect:
        manager.disconnect()
        print(f"Disconnected! State: {manager.state.value}")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 50 + "\n")

    # Context manager usage:
    print("Context manager usage:")
    with ConnectionManager() as manager:
        print(f"State: {manager.state.value}")
        node = manager.get_node()
        print(f"Node: {node.get_name()}")
    print("Exited context, connection closed")
