# Test Suite Fix Plan

**Date:** 2025-11-17
**Status:** 236+ tests passing, 11 tests need API alignment
**Overall Coverage:** Phase 3 & 4 = 128 tests passing

---

## Executive Summary

The test suite has **19 pre-existing test failures** due to API mismatches between test expectations and actual implementation. These occurred because the API evolved after tests were initially written.

### Current Status
- ✅ **Phase 3 Core Tests**: 128/128 passing (simulation, model, integration, geometry)
- ✅ **Phase 4 Tests**: 39/39 passing (world_generation)
- ⚠️ **Legacy Tests**: 11 failures in test_sensor_world_tools.py (API mismatch)
- ❌ **Import Error**: 1 test file (test_validators.py - missing exception class)

---

## Test Failures Analysis

### 1. test_sensor_world_tools.py (11 failures)

**Root Cause:** Tests written for old API before implementation refactoring

#### Issue 1: `get_sensor_data()` API Mismatch

**Test Expectation:**
```python
sensor_tools.get_sensor_data(
    model_name="test_robot",  # ❌ Parameter doesn't exist
    sensor_name="scan",
    sensor_type="lidar"        # ❌ Parameter doesn't exist
)
```

**Actual API (sensor_tools.py:224):**
```python
def get_sensor_data(
    sensor_name: str,
    timeout: float = 5.0,
    response_format: str = "concise"
) -> OperationResult:
```

**Fix Required:**
- Remove `model_name` parameter from all test calls
- Remove `sensor_type` parameter (not supported)
- Add `response_format` parameter where needed
- Update assertions to match actual return structure

**Affected Tests:**
1. `test_get_sensor_data_mock_mode` - line 94
2. `test_get_sensor_data_lidar` - line 105
3. `test_get_sensor_data_invalid_timeout` - line 116
4. `test_list_then_read_sensor` - line 338

**Status:** ✅ 3/4 partially fixed (model_name removed, but may need response format updates)

---

#### Issue 2: `subscribe_sensor_stream()` API Mismatch

**Test Expectation:**
```python
sensor_tools.subscribe_sensor_stream(
    model_name="test_robot",  # ❌ Parameter doesn't exist
    sensor_name="scan",
    callback=callback         # ❌ Parameter doesn't exist
)
```

**Actual API (sensor_tools.py:301):**
```python
def subscribe_sensor_stream(
    sensor_name: str,
    topic_name: str,           # ✅ Required parameter
    message_type: str = "auto"
) -> OperationResult:
```

**Fix Required:**
- Remove `model_name` parameter
- Remove `callback` parameter (streaming API changed)
- Add `topic_name` parameter (required)
- Update assertions for new streaming model

**Affected Tests:**
1. `test_subscribe_sensor_stream_mock_mode` - line 134
2. `test_subscribe_sensor_stream_invalid_callback` - line 145

**Notes:** The streaming API fundamentally changed from callback-based to topic-based. These tests need complete rewrite.

---

#### Issue 3: `save_world()` Validation Issues

**Test Failures:**
```python
# Test expects failure for mock mode
assert result.success is False or 'mock' in result.data.get("note", "").lower()

# Actual behavior: Returns success with mock note
assert result.success is True and 'mock' in result.data.get("note", "")
```

**Affected Tests:**
1. `test_save_world_mock_mode` - line 194
2. `test_save_world_invalid_path` - line 201

**Fix Required:**
- Update assertions to match actual mock mode behavior
- Mock mode returns success with "note" field, not failure

---

#### Issue 4: `get_world_properties()` Return Structure

**Test Expectation:**
```python
assert "properties" in result.data
assert "gravity" in result.data["properties"]
```

**Actual Return Structure:**
```python
{
    "gravity": {"x": 0.0, "y": 0.0, "z": -9.8},
    "time_step": 0.001,
    "physics_engine": "ode",
    # ... flat structure, no "properties" wrapper
}
```

**Affected Tests:**
1. `test_get_world_properties_mock_mode` - line 221
2. `test_get_world_properties_includes_gravity` - line 229

**Fix Required:**
- Remove "properties" nesting from assertions
- Access fields directly: `result.data["gravity"]`

---

#### Issue 5: `set_world_property()` Validation

**Test Expectation:**
```python
# Test expects failure for invalid property name
result = world_tools.set_world_property(
    property_name="invalid_property",
    value=123
)
assert result.success is False
```

**Actual Behavior:** May succeed with note about unrecognized property

**Affected Tests:**
1. `test_set_world_property_invalid_name` - line 259

**Fix Required:**
- Update assertion to accept success with warning note
- Or add validation to implementation to reject invalid properties

---

### 2. test_validators.py (Import Error)

**Error:**
```python
ImportError: cannot import name 'InputValidationError' from 'gazebo_mcp.utils.exceptions'
```

**Root Cause:** Exception class renamed or removed

**Available Exceptions (exceptions.py):**
- GazeboMCPError
- ROS2NotConnectedError
- ROS2NodeError
- InvalidParameterError  # ✅ Likely the correct one

**Fix Required:**
- Replace `InputValidationError` with `InvalidParameterError`
- Update all test assertions
- Verify exception messages match

**Estimated Effort:** 10 minutes

---

## Recommended Fix Strategy

### Phase 1: Quick Wins (30 minutes)
1. ✅ Fix test_geometry.py (COMPLETED)
2. ✅ Fix get_sensor_data calls (PARTIALLY COMPLETED)
3. Fix test_validators.py import error
4. Fix get_world_properties assertions

### Phase 2: API Alignment (1-2 hours)
5. Rewrite subscribe_sensor_stream tests for new API
6. Fix save_world validation expectations
7. Fix set_world_property validation test
8. Update integration test expectations

### Phase 3: Comprehensive Verification (30 minutes)
9. Run full test suite
10. Check coverage gaps
11. Add missing edge cases
12. Document test patterns

---

## Detailed Fix Instructions

### Fix 1: test_validators.py

**File:** `tests/unit/test_validators.py:16`

```python
# Before:
from gazebo_mcp.utils.exceptions import InputValidationError

# After:
from gazebo_mcp.utils.exceptions import InvalidParameterError
```

**Then replace all occurrences:**
```python
# Before:
with pytest.raises(InputValidationError):

# After:
with pytest.raises(InvalidParameterError):
```

**Estimated Time:** 5 minutes

---

### Fix 2: get_sensor_data tests

**File:** `tests/unit/test_sensor_world_tools.py`

**Lines to fix:** 94, 105, 116, 338

```python
# Before:
result = sensor_tools.get_sensor_data(
    model_name="test_robot",  # ❌ Remove
    sensor_name="scan",
    sensor_type="lidar"       # ❌ Remove
)

# After:
result = sensor_tools.get_sensor_data(
    sensor_name="scan",
    response_format="concise"  # Optional: add if needed
)
```

**Status:** ✅ Partially complete (model_name removed from 3 tests)

**Estimated Time:** 10 minutes to complete

---

### Fix 3: subscribe_sensor_stream tests

**File:** `tests/unit/test_sensor_world_tools.py`

**Lines to fix:** 134, 145

**Complete rewrite required:**

```python
# Before (callback-based):
def test_subscribe_sensor_stream_mock_mode(self):
    callback = Mock()
    with patch.object(sensor_tools, '_use_real_gazebo', return_value=False):
        result = sensor_tools.subscribe_sensor_stream(
            model_name="test_robot",  # ❌ Remove
            sensor_name="scan",
            callback=callback         # ❌ Remove
        )
    assert result.success is False or "mock" in result.data.get("note", "").lower()

# After (topic-based):
def test_subscribe_sensor_stream_mock_mode(self):
    with patch.object(sensor_tools, '_use_real_gazebo', return_value=False):
        result = sensor_tools.subscribe_sensor_stream(
            sensor_name="scan",
            topic_name="/scan",       # ✅ Required
            message_type="auto"
        )
    # Update expectation based on actual behavior
    assert result.success is False or "note" in result.data

def test_subscribe_sensor_stream_invalid_topic(self):
    """Test subscribing with invalid topic name."""
    result = sensor_tools.subscribe_sensor_stream(
        sensor_name="scan",
        topic_name="",  # Invalid empty topic
        message_type="auto"
    )
    assert result.success is False
```

**Note:** Delete `test_subscribe_sensor_stream_invalid_callback` - no longer relevant

**Estimated Time:** 20 minutes

---

### Fix 4: save_world tests

**File:** `tests/unit/test_sensor_world_tools.py`

**Lines to fix:** 194, 201

```python
# Before:
def test_save_world_mock_mode(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.save_world("/tmp/test_world.sdf")
    # ❌ Wrong expectation
    assert result.success is False or "mock" in result.data.get("note", "").lower()

# After:
def test_save_world_mock_mode(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.save_world("/tmp/test_world.sdf")
    # ✅ Mock mode succeeds with note
    assert result.success is True
    assert "note" in result.data
    assert "mock" in result.data["note"].lower()

# Before:
def test_save_world_invalid_path(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.load_world("/nonexistent/world.sdf")
    assert result.success is False

# After:
def test_save_world_invalid_path(self):
    # Invalid path should fail in validation
    result = world_tools.save_world("")  # Empty path
    assert result.success is False
    assert "INVALID_PARAMETER" in result.error_code
```

**Estimated Time:** 10 minutes

---

### Fix 5: get_world_properties tests

**File:** `tests/unit/test_sensor_world_tools.py`

**Lines to fix:** 221, 229

```python
# Before:
def test_get_world_properties_mock_mode(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.get_world_properties()
    assert result.success is True
    assert "properties" in result.data  # ❌ Wrong structure

# After:
def test_get_world_properties_mock_mode(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.get_world_properties()
    assert result.success is True
    # ✅ Flat structure
    assert "gravity" in result.data
    assert "time_step" in result.data

# Before:
def test_get_world_properties_includes_gravity(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.get_world_properties()
    assert "gravity" in result.data["properties"]  # ❌ Wrong nesting

# After:
def test_get_world_properties_includes_gravity(self):
    with patch.object(world_tools, '_use_real_gazebo', return_value=False):
        result = world_tools.get_world_properties()
    # ✅ Direct access
    assert "gravity" in result.data
    gravity = result.data["gravity"]
    assert "x" in gravity
    assert "y" in gravity
    assert "z" in gravity
```

**Estimated Time:** 10 minutes

---

### Fix 6: set_world_property validation test

**File:** `tests/unit/test_sensor_world_tools.py`

**Line:** 259

**Option A: Update test expectation (if implementation allows invalid properties)**
```python
def test_set_world_property_invalid_name(self):
    result = world_tools.set_world_property(
        property_name="invalid_property",
        value=123
    )
    # Accept success with warning note
    if result.success:
        assert "note" in result.data
        assert "unrecognized" in result.data["note"].lower()
    else:
        assert "INVALID_PARAMETER" in result.error_code
```

**Option B: Add validation to implementation (recommended)**
```python
# In world_tools.py:
VALID_PROPERTIES = {"gravity", "time_step", "physics_engine", "real_time_factor"}

def set_world_property(property_name: str, value: Any) -> OperationResult:
    if property_name not in VALID_PROPERTIES:
        return error_result(
            error=f"Unknown property: {property_name}",
            error_code="INVALID_PARAMETER",
            suggestions=[f"Valid properties: {', '.join(VALID_PROPERTIES)}"]
        )
    # ... rest of implementation
```

**Estimated Time:** 15 minutes (Option B recommended)

---

### Fix 7: Integration test

**File:** `tests/unit/test_sensor_world_tools.py`

**Line:** 338

```python
# Before:
def test_list_then_read_sensor(self):
    # ... list sensors ...
    data_result = sensor_tools.get_sensor_data(
        model_name="test_robot",  # ❌ Remove
        sensor_name="scan"
    )

# After:
def test_list_then_read_sensor(self):
    # ... list sensors ...
    data_result = sensor_tools.get_sensor_data(
        sensor_name="scan",
        response_format="concise"
    )
```

**Estimated Time:** 5 minutes

---

## Test Coverage Goals

### Current Coverage
- simulation_tools: 94%
- model_management: 84%
- world_generation: 85%
- sensor_tools: ~60% (estimated, needs verification)
- world_tools: ~50% (estimated, needs verification)

### Target Coverage
- All Phase 3 tools: >80%
- All Phase 4 tools: >85%
- Critical paths: >95%

---

## Testing Best Practices

### 1. API Alignment
- ✅ Tests should match actual API signatures
- ✅ Update tests when API changes (don't let them drift)
- ✅ Document API changes in CHANGELOG.md

### 2. Mock Mode Testing
- ✅ Test both mock and real Gazebo modes
- ✅ Mock mode should succeed with "note" field indicating mock status
- ✅ Real mode tests should be skippable if Gazebo unavailable

### 3. Validation Testing
- ✅ Test invalid inputs comprehensively
- ✅ Verify error codes are correct
- ✅ Check suggestions are helpful

### 4. Integration Testing
- ✅ Test complete workflows (spawn → move → sense → delete)
- ✅ Test error recovery
- ✅ Test state consistency

---

## Execution Plan

### Priority 1: Critical Fixes (Day 1 - 2 hours)
- [ ] Fix test_validators.py import error
- [ ] Complete get_sensor_data fixes
- [ ] Fix get_world_properties structure
- [ ] Run and verify: 245+ tests passing

### Priority 2: API Rewrites (Day 2 - 2 hours)
- [ ] Rewrite subscribe_sensor_stream tests
- [ ] Fix save_world validation tests
- [ ] Add set_world_property validation
- [ ] Run and verify: 248+ tests passing

### Priority 3: Coverage Improvements (Day 3 - 2 hours)
- [ ] Add missing edge cases
- [ ] Improve sensor_tools to >80% coverage
- [ ] Improve world_tools to >80% coverage
- [ ] Document test patterns

### Priority 4: Integration & Validation (Day 4 - 1 hour)
- [ ] Run full test suite
- [ ] Generate coverage report
- [ ] Update documentation
- [ ] Create test guidelines

---

## Success Criteria

- ✅ All 248+ tests passing
- ✅ No import errors
- ✅ Phase 3 tools: >80% coverage
- ✅ Phase 4 tools: >85% coverage
- ✅ All API mismatches resolved
- ✅ Test patterns documented

---

## Notes

1. **API Documentation:** After fixing tests, update API_REFERENCE.md with correct signatures
2. **Changelog:** Document API changes that caused test failures
3. **Test Guidelines:** Create TESTING.md with patterns and best practices
4. **CI/CD:** Ensure tests run in CI pipeline
5. **Mock Data:** Consider creating realistic mock data fixtures

---

## References

- **Test Files:**
  - `tests/unit/test_sensor_world_tools.py` - 11 failures
  - `tests/unit/test_validators.py` - 1 import error
  - `tests/unit/test_geometry.py` - ✅ Fixed (11 passing)

- **Implementation Files:**
  - `src/gazebo_mcp/tools/sensor_tools.py` - Actual API
  - `src/gazebo_mcp/tools/world_tools.py` - Actual API
  - `src/gazebo_mcp/utils/exceptions.py` - Exception classes

- **Documentation:**
  - `docs/guides/API_REFERENCE.md` - Should match implementation
  - `CHANGELOG.md` - Track API changes

---

**Last Updated:** 2025-11-17
**Status:** Document complete, ready for execution
