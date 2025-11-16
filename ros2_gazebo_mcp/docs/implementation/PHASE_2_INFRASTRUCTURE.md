# Phase 2: Core MCP Server Infrastructure

**Status**: 🔵 Not Started
**Estimated Duration**: 2-3 days
**Prerequisites**: Phase 1 Complete ✅

---

## Overview

Build the foundational MCP server and ROS2 bridge infrastructure. This phase establishes the core communication layer between AI assistants and Gazebo.

## Objectives

1. Create working MCP server that accepts tool calls
2. Implement ROS2 bridge node for Gazebo communication
3. Build connection management with lifecycle handling
4. Establish logging and error handling infrastructure
5. Create base utilities for validation and conversion

---

## Task Breakdown

### 2.1 Base Utilities (5 tasks)

Build foundational utilities used throughout the project.

#### Task 2.1.1: Create Exception Classes ⏳
**File**: `src/gazebo_mcp/utils/exceptions.py`

```python
"""Custom exception types for Gazebo MCP Server"""

class GazeboMCPError(Exception):
    """Base exception for all Gazebo MCP errors"""
    pass

class ConnectionError(GazeboMCPError):
    """ROS2 connection failed or lost"""
    pass

class ValidationError(GazeboMCPError):
    """Invalid input parameters"""
    pass

class SimulationError(GazeboMCPError):
    """Gazebo operation failed"""
    pass

class TimeoutError(GazeboMCPError):
    """Operation timed out"""
    pass

class ModelNotFoundError(GazeboMCPError):
    """Requested model does not exist"""
    pass
```

**Checklist**:
- [ ] Create base `GazeboMCPError` class
- [ ] Add specific error types (Connection, Validation, Simulation, Timeout)
- [ ] Add docstrings to each exception
- [ ] Write unit tests in `tests/test_exceptions.py`

---

#### Task 2.1.2: Create Logger ⏳
**File**: `src/gazebo_mcp/utils/logger.py`

```python
"""Structured logging for Gazebo MCP Server"""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logger(
    name: str = "gazebo_mcp",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_json: bool = False
) -> logging.Logger:
    """
    Set up logger with console and optional file output.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logs
        format_json: If True, output JSON format

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if format_json:
        # JSON formatting
        formatter = JsonFormatter()
    else:
        # Human-readable formatting
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
```

**Checklist**:
- [ ] Implement `setup_logger()` function
- [ ] Add console handler with formatting
- [ ] Add optional file handler
- [ ] Support JSON format option
- [ ] Add structured logging helpers
- [ ] Write tests for logger configuration

---

#### Task 2.1.3: Create Validators ⏳
**File**: `src/gazebo_mcp/utils/validators.py`

```python
"""Input validation utilities"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field, validator
import re

def validate_model_name(name: str) -> str:
    """Validate model name follows conventions"""
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValidationError(
            f"Invalid model name: {name}. "
            "Must contain only alphanumeric characters and underscores."
        )
    return name

def validate_coordinates(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Validate 3D coordinates are finite"""
    for coord in [x, y, z]:
        if not math.isfinite(coord):
            raise ValidationError(f"Coordinate must be finite, got: {coord}")
    return (x, y, z)

class SpawnModelParams(BaseModel):
    """Parameters for spawning a model"""
    model_name: str = Field(..., min_length=1, max_length=100)
    model_type: str = Field(default="turtlebot3_burger")
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    yaw: float = Field(default=0.0)

    @validator('model_name')
    def validate_name(cls, v):
        return validate_model_name(v)

    @validator('x', 'y', 'z')
    def validate_coord(cls, v):
        if not math.isfinite(v):
            raise ValueError("Coordinate must be finite")
        return v
```

**Checklist**:
- [ ] Create validation functions for common inputs
- [ ] Add Pydantic models for tool parameters
- [ ] Implement coordinate validation
- [ ] Implement model name validation
- [ ] Add SDF/URDF validation (basic)
- [ ] Write validation tests

---

#### Task 2.1.4: Create Converters ⏳
**File**: `src/gazebo_mcp/utils/converters.py`

```python
"""Type conversion utilities for ROS2 messages"""

from typing import Dict, Any
from geometry_msgs.msg import Pose, Point, Quaternion, Vector3
from std_msgs.msg import Header
import numpy as np

def dict_to_pose(data: Dict[str, Any]) -> Pose:
    """Convert dictionary to ROS2 Pose message"""
    pose = Pose()
    pose.position = Point(
        x=data.get('x', 0.0),
        y=data.get('y', 0.0),
        z=data.get('z', 0.0)
    )
    # Convert yaw to quaternion
    yaw = data.get('yaw', 0.0)
    pose.orientation = yaw_to_quaternion(yaw)
    return pose

def pose_to_dict(pose: Pose) -> Dict[str, Any]:
    """Convert ROS2 Pose message to dictionary"""
    return {
        'position': {
            'x': pose.position.x,
            'y': pose.position.y,
            'z': pose.position.z
        },
        'orientation': {
            'x': pose.orientation.x,
            'y': pose.orientation.y,
            'z': pose.orientation.z,
            'w': pose.orientation.w
        }
    }

def yaw_to_quaternion(yaw: float) -> Quaternion:
    """Convert yaw angle to quaternion"""
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = np.sin(yaw / 2.0)
    q.w = np.cos(yaw / 2.0)
    return q
```

**Checklist**:
- [ ] Implement dict ↔ Pose conversions
- [ ] Implement dict ↔ Twist conversions
- [ ] Add quaternion ↔ euler conversions
- [ ] Add sensor message converters
- [ ] Write converter tests

---

#### Task 2.1.5: Create Geometry Utilities ⏳
**File**: `src/gazebo_mcp/utils/geometry.py`

```python
"""Geometric calculations and transformations"""

import math
import numpy as np
from typing import Tuple

def quaternion_to_euler(x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
    """
    Convert quaternion to Euler angles (roll, pitch, yaw)

    Returns:
        (roll, pitch, yaw) in radians
    """
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)

def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance between two 3D points"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
```

**Checklist**:
- [ ] Implement quaternion conversions
- [ ] Add distance calculations
- [ ] Add transformation utilities
- [ ] Write geometry tests

---

### 2.2 Connection Manager (5 tasks)

Manage ROS2 node lifecycle and connection state.

#### Task 2.2.1: Connection Manager Core ⏳
**File**: `src/gazebo_mcp/bridge/connection_manager.py`

```python
"""Manages ROS2 node lifecycle and connection state"""

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
import threading
from enum import Enum
from typing import Optional
from ..utils.logger import setup_logger
from ..utils.exceptions import ConnectionError

class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class ConnectionManager:
    """
    Manages ROS2 connection lifecycle.

    Handles:
    - ROS2 initialization
    - Node creation and lifecycle
    - Connection monitoring
    - Automatic reconnection
    """

    def __init__(self, node_name: str = "gazebo_mcp_bridge"):
        self.node_name = node_name
        self.node: Optional[Node] = None
        self.executor: Optional[MultiThreadedExecutor] = None
        self.spin_thread: Optional[threading.Thread] = None
        self.state = ConnectionState.DISCONNECTED
        self.logger = setup_logger("connection_manager")

    def connect(self) -> None:
        """Initialize ROS2 and create node"""
        if self.state == ConnectionState.CONNECTED:
            self.logger.warning("Already connected")
            return

        try:
            self.state = ConnectionState.CONNECTING
            self.logger.info("Initializing ROS2...")

            # Initialize ROS2
            if not rclpy.ok():
                rclpy.init()

            # Create node
            self.node = Node(self.node_name)
            self.logger.info(f"Created ROS2 node: {self.node_name}")

            # Create executor
            self.executor = MultiThreadedExecutor()
            self.executor.add_node(self.node)

            # Start spinning in background thread
            self.spin_thread = threading.Thread(
                target=self._spin,
                daemon=True
            )
            self.spin_thread.start()

            self.state = ConnectionState.CONNECTED
            self.logger.info("ROS2 connection established")

        except Exception as e:
            self.state = ConnectionState.ERROR
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"ROS2 connection failed: {e}")

    def disconnect(self) -> None:
        """Shutdown ROS2 connection"""
        if self.state == ConnectionState.DISCONNECTED:
            return

        self.logger.info("Disconnecting ROS2...")

        if self.executor:
            self.executor.shutdown()

        if self.node:
            self.node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

        self.state = ConnectionState.DISCONNECTED
        self.logger.info("Disconnected")

    def _spin(self) -> None:
        """Spin executor in background thread"""
        try:
            self.executor.spin()
        except Exception as e:
            self.logger.error(f"Executor error: {e}")
            self.state = ConnectionState.ERROR

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.state == ConnectionState.CONNECTED and rclpy.ok()
```

**Checklist**:
- [ ] Define `ConnectionState` enum
- [ ] Implement `ConnectionManager` class
- [ ] Add `connect()` method
- [ ] Add `disconnect()` method
- [ ] Add background thread for spinning
- [ ] Add connection state checking
- [ ] Write connection manager tests

---

#### Task 2.2.2-2.2.5: Additional Connection Features ⏳

**Task 2.2.2**: Add auto-reconnect logic
**Task 2.2.3**: Add connection health monitoring
**Task 2.2.4**: Add timeout handling
**Task 2.2.5**: Add connection status reporting

These will be implemented as methods on `ConnectionManager`.

---

### 2.3 ROS2 Bridge Node (5 tasks)

#### Task 2.3.1: Bridge Node Core ⏳
**File**: `src/gazebo_mcp/bridge/gazebo_bridge_node.py`

```python
"""ROS2 bridge node for Gazebo communication"""

from typing import Dict, Any, Optional, Callable
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from gazebo_msgs.srv import SpawnEntity, DeleteEntity
from geometry_msgs.msg import Twist
from ..utils.logger import setup_logger

class GazeboBridgeNode:
    """
    ROS2 bridge for communicating with Gazebo.

    Provides high-level interface for:
    - Spawning/deleting models
    - Sending velocity commands
    - Querying simulation state
    - Accessing sensor data
    """

    def __init__(self, node: Node):
        self.node = node
        self.logger = setup_logger("gazebo_bridge")

        # Service clients
        self.spawn_client = None
        self.delete_client = None

        # Publishers
        self.cmd_vel_publishers: Dict[str, Any] = {}

        # QoS profiles
        self.reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self._setup_clients()

    def _setup_clients(self) -> None:
        """Set up service clients"""
        self.spawn_client = self.node.create_client(
            SpawnEntity,
            '/gazebo/spawn_entity'
        )
        self.delete_client = self.node.create_client(
            DeleteEntity,
            '/gazebo/delete_entity'
        )

        self.logger.info("Service clients created")

    async def spawn_entity(
        self,
        name: str,
        xml: str,
        robot_namespace: str = "",
        initial_pose: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Spawn entity in Gazebo.

        Args:
            name: Entity name
            xml: SDF or URDF XML string
            robot_namespace: ROS namespace for robot
            initial_pose: Initial pose {x, y, z, yaw}

        Returns:
            Result dictionary with success status
        """
        if not self.spawn_client.wait_for_service(timeout_sec=5.0):
            raise TimeoutError("Spawn service not available")

        request = SpawnEntity.Request()
        request.name = name
        request.xml = xml
        request.robot_namespace = robot_namespace

        if initial_pose:
            # Set initial pose
            from ..utils.converters import dict_to_pose
            request.initial_pose = dict_to_pose(initial_pose)

        future = self.spawn_client.call_async(request)
        # Wait for result (in async context)
        result = await future

        return {
            'success': result.success,
            'status_message': result.status_message
        }
```

**Checklist**:
- [ ] Create `GazeboBridgeNode` class
- [ ] Set up service clients (spawn, delete, etc.)
- [ ] Define QoS profiles
- [ ] Implement `spawn_entity()` method
- [ ] Implement `delete_entity()` method
- [ ] Add error handling
- [ ] Write bridge node tests

---

#### Task 2.3.2-2.3.5: Additional Bridge Features ⏳

**Task 2.3.2**: Implement topic publishers/subscribers
**Task 2.3.3**: Add velocity command publishing
**Task 2.3.4**: Add sensor data subscription
**Task 2.3.5**: Add state query methods

---

### 2.4 MCP Server (5 tasks)

#### Task 2.4.1: MCP Server Core ⏳
**File**: `src/gazebo_mcp/server.py`

```python
"""Main MCP server for Gazebo control"""

import asyncio
from typing import Any, Dict
from mcp import Server, Tool
from mcp.server.stdio import stdio_server

from .bridge.connection_manager import ConnectionManager
from .bridge.gazebo_bridge_node import GazeboBridgeNode
from .utils.logger import setup_logger
from .utils.exceptions import GazeboMCPError

class GazeboMCPServer:
    """
    MCP server for Gazebo simulation control.

    Exposes tools for:
    - Simulation control
    - Model management
    - Sensor access
    - World generation
    """

    def __init__(self):
        self.server = Server("gazebo-mcp")
        self.logger = setup_logger("gazebo_mcp_server")
        self.connection_manager: Optional[ConnectionManager] = None
        self.bridge: Optional[GazeboBridgeNode] = None

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all MCP tools"""
        # Tools will be registered here
        # Example:
        # self.server.add_tool(self.spawn_model_tool)
        pass

    async def start(self) -> None:
        """Start the MCP server"""
        self.logger.info("Starting Gazebo MCP Server...")

        # Initialize ROS2 connection
        self.connection_manager = ConnectionManager()
        self.connection_manager.connect()

        # Create bridge
        self.bridge = GazeboBridgeNode(self.connection_manager.node)

        self.logger.info("Server ready")

    async def stop(self) -> None:
        """Stop the MCP server"""
        self.logger.info("Stopping server...")

        if self.connection_manager:
            self.connection_manager.disconnect()

        self.logger.info("Server stopped")

async def main():
    """Main entry point"""
    server = GazeboMCPServer()

    try:
        await server.start()
        # Run stdio server
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Checklist**:
- [ ] Create `GazeboMCPServer` class
- [ ] Implement server initialization
- [ ] Connect to ROS2 via `ConnectionManager`
- [ ] Create `GazeboBridgeNode` instance
- [ ] Implement `start()` and `stop()` methods
- [ ] Add `main()` entry point with stdio server
- [ ] Add graceful shutdown handling
- [ ] Write server initialization tests

---

#### Task 2.4.2-2.4.5: Additional Server Features ⏳

**Task 2.4.2**: Implement health check endpoint
**Task 2.4.3**: Add tool registration system
**Task 2.4.4**: Add request logging
**Task 2.4.5**: Add error response formatting

---

## Testing Requirements

### Unit Tests
- [ ] Test all exception types
- [ ] Test logger configuration
- [ ] Test validators with valid/invalid inputs
- [ ] Test message converters
- [ ] Test geometry calculations
- [ ] Test connection manager lifecycle
- [ ] Test bridge node client setup

### Integration Tests
- [ ] Test MCP server startup/shutdown
- [ ] Test ROS2 connection establishment
- [ ] Test service client communication (with mock)
- [ ] Test end-to-end tool call (with mock Gazebo)

### Test Coverage Target
- **Minimum**: 80% code coverage
- **Goal**: 90% code coverage

---

## Configuration Files

### Task 2.5.1: Server Configuration ⏳
**File**: `config/server_config.yaml`

```yaml
server:
  name: "gazebo-mcp"
  protocol: "stdio"  # or "http"
  log_level: "INFO"
  log_file: "logs/gazebo_mcp.log"

timeouts:
  service_call: 10.0  # seconds
  connection: 5.0
  operation: 30.0
```

### Task 2.5.2: ROS2 Configuration ⏳
**File**: `config/ros2_config.yaml`

```yaml
ros2:
  node_name: "gazebo_mcp_bridge"
  namespace: "/gazebo_mcp"

  qos:
    default:
      reliability: "reliable"
      durability: "volatile"
      history: "keep_last"
      depth: 10
```

---

## Success Criteria

Phase 2 is complete when:

- [x] All utilities implemented and tested
- [x] Connection manager working with lifecycle
- [x] ROS2 bridge node connects to Gazebo
- [x] MCP server starts and accepts connections
- [x] Health checks pass
- [x] All unit tests pass (>80% coverage)
- [x] Integration test with mock Gazebo passes
- [x] Configuration files created
- [x] Documentation updated

---

## Next Phase

Proceed to **Phase 3: Gazebo Connection & Control Tools**

Implement actual MCP tools for:
- Simulation control (start, stop, pause)
- Model management (spawn, delete)
- Sensor data access
- Robot control

---

**Estimated Completion**: 2-3 days
**Priority**: HIGH - Blocking for all other phases
