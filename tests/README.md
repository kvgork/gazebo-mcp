# Gazebo MCP Tests

Comprehensive test suite for the Gazebo MCP server.

## Test Structure

```
tests/
├── conftest.py           # Pytest fixtures and configuration
├── test_integration.py   # Integration tests (ROS2 + Gazebo)
├── test_utils.py         # Unit tests (validators, converters, geometry)
└── README.md             # This file
```

## Running Tests

### 1. Unit Tests (No Dependencies)

Run tests that don't require ROS2 or Gazebo:

```bash
pytest tests/test_utils.py -v
```

This tests:
- Validators (coordinates, quaternions, model names, etc.)
- Converters (Euler ↔ Quaternion, Pose ↔ dict)
- Geometry utilities (quaternion math, SLERP, transforms)
- Exceptions (error handling)

### 2. Integration Tests (ROS2 Required)

Run tests that require ROS2 to be sourced:

```bash
# Source ROS2 first:
source /opt/ros/humble/setup.bash  # or jazzy

# Run ROS2 tests:
pytest tests/test_integration.py -v --with-ros2
```

This tests:
- ConnectionManager lifecycle (connect, disconnect, reconnect)
- ConnectionManager callbacks and health monitoring
- GazeboBridgeNode creation
- Model management without Gazebo (mock data)

### 3. Full Integration Tests (Gazebo Required)

Run tests that require Gazebo to be running:

```bash
# Terminal 1: Start Gazebo
ros2 launch gazebo_ros gazebo.launch.py

# Terminal 2: Run Gazebo tests
pytest tests/test_integration.py -v --with-gazebo
```

This tests:
- Real model list queries
- Model spawn and delete operations
- Model state queries
- Full ROS2 ↔ Gazebo integration

### 4. Run All Tests

```bash
# Without Gazebo (safe to run anytime):
pytest tests/ -v

# With ROS2:
pytest tests/ -v --with-ros2

# With Gazebo:
pytest tests/ -v --with-gazebo
```

## Test Markers

Tests are marked with these pytest markers:

- `@pytest.mark.ros2` - Requires ROS2 to be sourced
- `@pytest.mark.gazebo` - Requires Gazebo to be running
- `@pytest.mark.slow` - Takes > 1 second to run

## Test Coverage

### Unit Tests (test_utils.py)

**Validators:**
- ✅ Coordinate validation (min/max, NaN, Inf)
- ✅ Position validation (3D coordinates)
- ✅ Angle validation (radians/degrees conversion)
- ✅ Orientation validation (Euler angles)
- ✅ Quaternion validation (normalized check)
- ✅ Model name validation (format, length)
- ✅ Sensor type validation (12 sensor types)
- ✅ Timeout validation (range checks)
- ✅ Positive/non-negative validation
- ✅ Response format validation

**Converters:**
- ✅ Euler ↔ Quaternion conversion (both directions)
- ✅ Roundtrip conversion (identity preservation)
- ✅ Edge cases (identity, 90° rotations)

**Geometry:**
- ✅ Quaternion operations (multiply, conjugate, inverse, normalize)
- ✅ Quaternion SLERP (endpoints, halfway)
- ✅ Vector rotation by quaternion
- ✅ Distance calculations (2D, 3D)
- ✅ Angle calculations (between vectors, between quaternions)
- ✅ Transform composition and inversion
- ✅ Angle normalization to [-π, π]
- ✅ Degrees ↔ Radians conversion

**Exceptions:**
- ✅ Base GazeboMCPError
- ✅ InvalidParameterError
- ✅ MissingParameterError
- ✅ Exception to_dict() method

### Integration Tests (test_integration.py)

**ConnectionManager (without ROS2):**
- ✅ Import and creation
- ✅ ConnectionState enum
- ✅ Properties and configuration

**ConnectionManager (with ROS2):**
- ✅ Connect/disconnect lifecycle
- ✅ Reconnect functionality
- ✅ Context manager usage
- ✅ ensure_connected() guard
- ✅ Event callbacks (on_connected, on_disconnected)

**GazeboBridgeNode (with ROS2):**
- ✅ Creation and initialization

**GazeboBridgeNode (with Gazebo):**
- ✅ get_model_list() with real data
- ✅ spawn_entity() and delete_entity()
- ✅ Full lifecycle (spawn → verify → delete)

**Model Management:**
- ✅ Import and basic functionality
- ✅ list_models() with mock data
- ✅ Filtered response format
- ✅ Parameter validation
- ✅ ResultFilter integration

**Model Management (with Gazebo):**
- ✅ list_models() with real data
- ✅ spawn_model() and delete_model()
- ✅ get_model_state()

**Error Handling:**
- ✅ Error result structure
- ✅ model_not_found_error() helper

**ResultFilter:**
- ✅ search() by keyword
- ✅ filter_by_field()
- ✅ limit()
- ✅ top_n_by_field()

## Expected Test Results

### Without Gazebo

```
tests/test_integration.py::test_connection_manager_import PASSED
tests/test_integration.py::test_connection_state_enum PASSED
tests/test_integration.py::test_connection_manager_creation PASSED
tests/test_integration.py::test_model_management_import PASSED
tests/test_integration.py::test_list_models_mock_data PASSED
tests/test_integration.py::test_result_filter_with_models PASSED
tests/test_utils.py::TestValidators::test_validate_coordinate_valid PASSED
tests/test_utils.py::TestConverters::test_euler_to_quaternion_identity PASSED
tests/test_utils.py::TestGeometry::test_quaternion_normalize PASSED
... (60+ tests)

SKIPPED: Tests marked with @pytest.mark.ros2 or @pytest.mark.gazebo
```

### With ROS2

Additional tests:
```
tests/test_integration.py::test_connection_manager_connect PASSED
tests/test_integration.py::test_connection_manager_reconnect PASSED
tests/test_integration.py::test_connection_manager_context_manager PASSED
tests/test_integration.py::test_bridge_node_creation PASSED
... (10+ additional tests)
```

### With Gazebo

Additional tests:
```
tests/test_integration.py::test_bridge_node_get_model_list PASSED
tests/test_integration.py::test_bridge_node_spawn_delete_entity PASSED
tests/test_integration.py::test_list_models_real_gazebo PASSED
tests/test_integration.py::test_spawn_delete_model_real_gazebo PASSED
... (5+ additional tests)
```

## Troubleshooting

### "No module named rclpy"

ROS2 is not sourced. Run:
```bash
source /opt/ros/humble/setup.bash
```

### "Gazebo not available" errors

Gazebo is not running. Start it:
```bash
ros2 launch gazebo_ros gazebo.launch.py
```

### Test timeouts

Some tests may timeout if:
- Gazebo is slow to start (increase timeout in test)
- System is under heavy load
- Network issues with ROS2 daemon

### Import errors

Make sure you're in the project root and the source directory is in PYTHONPATH:
```bash
cd <path-to-ros2_gazebo_mcp>
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
pytest tests/ -v
```

## Test Statistics

- **Total Tests:** 80+
- **Unit Tests:** 60+ (validators, converters, geometry)
- **Integration Tests:** 20+ (ConnectionManager, BridgeNode, model_management)
- **Gazebo Tests:** 5+ (real spawn/delete/query)

**Coverage:**
- Validators: ~95%
- Converters: ~90%
- Geometry: ~90%
- ConnectionManager: ~85%
- GazeboBridgeNode: ~70% (core operations)
- model_management: ~80%

## Adding New Tests

### Unit Test Template

```python
def test_my_feature():
    """Test description."""
    from gazebo_mcp.utils.validators import validate_something

    # Test:
    result = validate_something(valid_input)
    assert result == expected_output

    # Test error case:
    with pytest.raises(InvalidParameterError):
        validate_something(invalid_input)
```

### Integration Test Template

```python
@pytest.mark.gazebo
def test_my_integration(gazebo_available):
    """Test description."""
    if not gazebo_available:
        pytest.skip("Gazebo not available")

    from gazebo_mcp.bridge import ConnectionManager, GazeboBridgeNode

    manager = ConnectionManager()
    try:
        manager.connect(timeout=10.0)
        bridge = GazeboBridgeNode(manager.get_node())

        # Test something...

    finally:
        manager.disconnect()
```

## Continuous Integration

These tests are designed to run in CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run unit tests
  run: pytest tests/test_utils.py -v

- name: Run integration tests
  run: |
    source /opt/ros/humble/setup.bash
    pytest tests/test_integration.py -v --with-ros2
```

For Gazebo tests in CI, you'll need:
1. ROS2 Humble/Jazzy installed
2. Gazebo Harmonic installed
3. Virtual display (Xvfb) for headless Gazebo
