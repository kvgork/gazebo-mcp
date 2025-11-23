# Phase 1: Gazebo Classic → Modern Migration - Complete Implementation Plan

**Branch**: `feature/gazebo-modern-migration`
**Goal**: Migrate from Gazebo Classic (gazebo_msgs) to Modern Gazebo (ros_gz_interfaces)
**Strategy**: Adapter pattern for dual support, then deprecate Classic

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Current Status](#current-status)
3. [Detailed Implementation Steps](#detailed-implementation-steps)
4. [File Structure](#file-structure)
5. [Testing Strategy](#testing-strategy)
6. [Migration Path](#migration-path)

---

## Overview

### Problem
- System claims "Gazebo Harmonic" support but uses Classic Gazebo (gazebo_msgs)
- Classic Gazebo is deprecated
- Need Modern Gazebo (Fortress/Harmonic) with ros_gz_interfaces

### Solution
- **Phase 1**: Build adapter pattern for dual support (CURRENT)
- **Phase 2**: Implement Modern Gazebo adapter fully
- **Phase 3**: Deprecate and remove Classic support

### Key Differences Between Classic and Modern

| Aspect | Classic Gazebo | Modern Gazebo |
|--------|---------------|---------------|
| Package | gazebo_msgs | ros_gz_interfaces |
| Service paths | /gazebo/* | /world/{world_name}/* |
| SDF field | .xml | .sdf |
| Pose field | .initial_pose | .pose |
| Worlds | Single world | Multi-world support |
| SDF version | 1.6-1.7 | 1.8+ |

---

## Current Status

### ✅ Completed (Phase 1A & 1B)

#### Phase 1A: Foundation
- [x] Created feature branch: `feature/gazebo-modern-migration`
- [x] GazeboInterface abstraction (bridge/gazebo_interface.py)
  - Abstract base class with 10 methods
  - Common data structures: EntityPose, EntityTwist, WorldInfo
- [x] GazeboConfig configuration (bridge/config.py)
  - Environment variables: GAZEBO_BACKEND, GAZEBO_WORLD_NAME, GAZEBO_TIMEOUT
  - Backends: classic, modern, auto
- [x] GazeboDetector auto-detection (bridge/detection.py)
  - Service-based detection
  - Process-based fallback
- [x] ClassicGazeboAdapter (bridge/adapters/classic_adapter.py)
  - Full 500-line implementation
  - All 10 interface methods
- [x] ModernGazeboAdapter stub (bridge/adapters/modern_adapter.py)
  - Structure ready, NotImplementedError
- [x] GazeboAdapterFactory (bridge/factory.py)
  - Creates correct adapter based on config

#### Phase 1B: Integration
- [x] Refactored GazeboBridgeNode (bridge/gazebo_bridge_node.py)
  - Dependency injection (config, adapter parameters)
  - All methods delegate to adapter
  - Helper methods: _run_async, _dict_to_entity_pose, _dict_to_entity_twist
- [x] Updated MCP tools with world parameter:
  - model_management.py: list_models, spawn_model, delete_model, get_model_state, set_model_state
  - simulation_tools.py: pause_simulation, unpause_simulation, reset_simulation
- [x] Backward compatibility maintained
  - All parameters default to "default"
  - Existing code works unchanged

### 📊 Metrics So Far
- **Files created/modified**: 11
- **Lines of code**: ~1,600
- **Commits**: 4 detailed commits
- **Breaking changes**: 0

---

## Detailed Implementation Steps

### 🔄 Phase 1C: Preparation for Modern Gazebo (NEXT - IN PROGRESS)

#### Step 1: Check Installed Gazebo Version
**File**: N/A (terminal command)
**Action**: Determine which Gazebo is installed

```bash
# Check for Modern Gazebo (Fortress, Garden, Harmonic)
gz sim --version

# Check for Classic Gazebo
gazebo --version

# Check ROS 2 Gazebo packages
ros2 pkg list | grep -i gazebo
ros2 pkg list | grep -i gz
```

**Expected Output**:
- Modern: `gz sim, version X.Y.Z`
- Classic: `Gazebo multi-robot simulator, version 11.X.Y`

**Todo Item**: ✅ Determine installed Gazebo version

---

#### Step 2: Update Default Configuration to Modern
**File**: `ros2_gazebo_mcp/src/gazebo_mcp/bridge/config.py`
**Action**: Change default backend from AUTO to MODERN

**Current Code** (line 43-45):
```python
def __init__(
    self,
    backend: Optional[GazeboBackend] = None,
    world_name: str = "default",
    timeout: float = 5.0
):
    if backend is None:
        backend_str = os.getenv('GAZEBO_BACKEND', 'auto').lower()  # ← Change 'auto' to 'modern'
```

**Change To**:
```python
def __init__(
    self,
    backend: Optional[GazeboBackend] = None,
    world_name: str = "default",
    timeout: float = 5.0
):
    if backend is None:
        backend_str = os.getenv('GAZEBO_BACKEND', 'modern').lower()  # ← Changed to 'modern'
```

**Rationale**: Default to Modern Gazebo, require explicit override for Classic

**Todo Item**: ✅ Set default backend to 'modern'

---

#### Step 3: Mark Classic Adapter as Deprecated
**File**: `ros2_gazebo_mcp/src/gazebo_mcp/bridge/adapters/classic_adapter.py`
**Action**: Add deprecation warnings

**Add to top of file** (after imports):
```python
import warnings

warnings.warn(
    "ClassicGazeboAdapter is deprecated and will be removed in v2.0.0. "
    "Please migrate to Modern Gazebo (Fortress/Harmonic) using ModernGazeboAdapter.",
    DeprecationWarning,
    stacklevel=2
)
```

**Add to __init__ method**:
```python
def __init__(self, node, timeout: float = 5.0):
    self.node = node
    self.timeout = timeout
    self.logger = get_logger("classic_adapter")

    # DEPRECATION WARNING
    self.logger.warning(
        "⚠️  Classic Gazebo support is DEPRECATED and will be removed in v2.0.0. "
        "Please migrate to Modern Gazebo (Fortress/Harmonic)."
    )
```

**Todo Item**: ✅ Add deprecation warnings to Classic adapter

---

### 🚀 Phase 2: Modern Gazebo Implementation (UPCOMING)

#### Step 4: Implement ModernGazeboAdapter
**File**: `ros2_gazebo_mcp/src/gazebo_mcp/bridge/adapters/modern_adapter.py`
**Action**: Replace NotImplementedError with full implementation

**Implementation Checklist**:
- [ ] Import ros_gz_interfaces instead of gazebo_msgs
- [ ] Implement spawn_entity using /world/{world}/create service
- [ ] Implement delete_entity using /world/{world}/remove service
- [ ] Implement get_entity_state using /world/{world}/state service
- [ ] Implement set_entity_state using /world/{world}/set_pose service
- [ ] Implement list_entities using /world/{world}/state service
- [ ] Implement get_world_properties using /world/{world}/info service
- [ ] Implement pause_simulation using /world/{world}/control service
- [ ] Implement unpause_simulation using /world/{world}/control service
- [ ] Implement reset_simulation using /world/{world}/control service
- [ ] Implement reset_world using /world/{world}/control service

**Key Differences to Handle**:
```python
# Classic Gazebo
from gazebo_msgs.srv import SpawnEntity
request.xml = sdf_content           # ← Field name
request.initial_pose = pose         # ← Field name
client = node.create_client(SpawnEntity, '/spawn_entity')  # ← Path

# Modern Gazebo
from ros_gz_interfaces.srv import SpawnEntity
request.sdf = sdf_content           # ← Different field name
request.pose = pose                 # ← Different field name
client = node.create_client(SpawnEntity, f'/world/{world}/create')  # ← Different path
```

**Todo Item**: ⬜ Implement ModernGazeboAdapter fully (~500 lines)

---

#### Step 5: Update Detection Logic
**File**: `ros2_gazebo_mcp/src/gazebo_mcp/bridge/detection.py`
**Action**: Improve Modern Gazebo detection

**Current Code** (lines 78-95):
```python
def _check_modern_services(self) -> bool:
    """Check for Modern Gazebo services."""
    # Check for /world/{world_name}/create service pattern
    service_names = self.node.get_service_names_and_types()

    for name, _ in service_names:
        if '/world/' in name and '/create' in name:
            self.logger.debug(f"Found Modern Gazebo service: {name}")
            return True
```

**Improve To**:
```python
def _check_modern_services(self) -> bool:
    """Check for Modern Gazebo services."""
    service_names = self.node.get_service_names_and_types()

    # Check for multiple Modern Gazebo service patterns
    modern_patterns = ['/world/', '/create', '/remove', '/control']
    modern_service_count = 0

    for name, _ in service_names:
        if any(pattern in name for pattern in modern_patterns):
            self.logger.debug(f"Found Modern Gazebo service: {name}")
            modern_service_count += 1

    # Require at least 2 Modern patterns to confirm
    return modern_service_count >= 2
```

**Todo Item**: ⬜ Improve Modern Gazebo detection logic

---

#### Step 6: Create Integration Tests
**File**: `ros2_gazebo_mcp/tests/test_modern_adapter.py` (NEW)
**Action**: Create comprehensive tests

**Test Structure**:
```python
import pytest
from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose

class TestModernGazeboAdapter:
    """Tests for Modern Gazebo adapter."""

    def test_spawn_entity(self):
        """Test entity spawning with Modern Gazebo."""
        # Test implementation
        pass

    def test_delete_entity(self):
        """Test entity deletion."""
        pass

    def test_multi_world_support(self):
        """Test multi-world operations."""
        pass

    # ... more tests
```

**Todo Item**: ⬜ Create integration tests for Modern adapter

---

#### Step 7: Update Documentation
**Files to Update**:
- `ros2_gazebo_mcp/README.md`
- `ros2_gazebo_mcp/docs/ARCHITECTURE.md`
- `ros2_gazebo_mcp/docs/MIGRATION_SUMMARY.md`

**Changes Needed**:
- [ ] Update README to show Modern Gazebo as primary
- [ ] Add deprecation notice for Classic Gazebo
- [ ] Update architecture diagrams
- [ ] Add Modern Gazebo installation instructions
- [ ] Document environment variables

**Example README Update**:
```markdown
## Gazebo Support

**Primary**: Modern Gazebo (Fortress, Garden, Harmonic)
**Deprecated**: Classic Gazebo 11 (support will be removed in v2.0.0)

### Installation

#### Modern Gazebo (Recommended)
\`\`\`bash
# ROS 2 Humble + Gazebo Fortress
sudo apt install ros-humble-ros-gz

# ROS 2 Iron + Gazebo Harmonic
sudo apt install ros-iron-ros-gz
\`\`\`

#### Environment Variables
- `GAZEBO_BACKEND`: Backend to use (modern, classic, auto)
- `GAZEBO_WORLD_NAME`: Default world name (default: "default")
- `GAZEBO_TIMEOUT`: Service call timeout in seconds (default: 5.0)
```

**Todo Item**: ⬜ Update all documentation for Modern Gazebo

---

### 🧪 Phase 3: Testing and Validation (FUTURE)

#### Step 8: End-to-End Testing
**File**: `ros2_gazebo_mcp/tests/test_e2e_modern.py` (NEW)

**Test Scenarios**:
- [ ] Launch Modern Gazebo
- [ ] Spawn multiple models
- [ ] Control simulation (pause/unpause/reset)
- [ ] Multi-world operations
- [ ] Performance benchmarks

**Todo Item**: ⬜ Create end-to-end tests

---

#### Step 9: Migration Guide
**File**: `ros2_gazebo_mcp/docs/MIGRATION_GUIDE.md` (NEW)

**Content**:
- Step-by-step migration from Classic to Modern
- Common issues and solutions
- API compatibility matrix
- Example code updates

**Todo Item**: ⬜ Write migration guide for users

---

### 🗑️ Phase 4: Deprecation (FUTURE - After Modern is Stable)

#### Step 10: Remove Classic Gazebo Support
**Timeline**: v2.0.0 release

**Files to Modify/Delete**:
- [ ] Delete `bridge/adapters/classic_adapter.py`
- [ ] Remove Classic backend from GazeboBackend enum
- [ ] Remove Classic detection logic
- [ ] Update factory to only create Modern adapter
- [ ] Update all tests

**Todo Item**: ⬜ Remove Classic Gazebo support (v2.0.0)

---

## File Structure

```
ros2_gazebo_mcp/
├── src/gazebo_mcp/
│   ├── bridge/
│   │   ├── __init__.py
│   │   ├── gazebo_interface.py        ✅ Abstract interface (Phase 1A)
│   │   ├── config.py                  ✅ Configuration (Phase 1A) → 🔄 Update default (Phase 1C)
│   │   ├── detection.py               ✅ Auto-detection (Phase 1A) → 🔄 Improve (Phase 2)
│   │   ├── factory.py                 ✅ Adapter factory (Phase 1A)
│   │   ├── gazebo_bridge_node.py      ✅ Main bridge (Phase 1B)
│   │   └── adapters/
│   │       ├── __init__.py            ✅ (Phase 1A)
│   │       ├── classic_adapter.py     ✅ Classic impl (Phase 1A) → 🔄 Deprecate (Phase 1C)
│   │       └── modern_adapter.py      ✅ Stub (Phase 1A) → ⬜ Implement (Phase 2)
│   └── tools/
│       ├── model_management.py        ✅ Updated with world param (Phase 1B)
│       ├── simulation_tools.py        ✅ Updated with world param (Phase 1B)
│       └── world_generation.py        (unchanged)
├── docs/
│   ├── IMPLEMENTATION_ROADMAP.md      ✅ Progress tracking
│   ├── PHASE1_IMPLEMENTATION_PLAN.md  ⬜ THIS FILE (Phase 1C)
│   ├── GAZEBO_MIGRATION_LEARNING_PLAN.md  ✅ (Phase 1A)
│   ├── MIGRATION_SUMMARY.md           ✅ (Phase 1A) → 🔄 Update (Phase 2)
│   ├── MIGRATION_QUICKSTART.md        ✅ (Phase 1A)
│   └── MIGRATION_GUIDE.md             ⬜ (Phase 3)
└── tests/
    ├── test_modern_adapter.py         ⬜ (Phase 2)
    └── test_e2e_modern.py             ⬜ (Phase 3)
```

**Legend**:
- ✅ Completed
- 🔄 Needs update
- ⬜ Not started

---

## Testing Strategy

### Unit Tests
- Mock ROS 2 services
- Test adapter methods individually
- Verify data conversions

### Integration Tests
- Use real Modern Gazebo instance
- Test full workflows
- Multi-world scenarios

### Performance Tests
- Benchmark adapter overhead
- Compare Classic vs Modern performance
- Memory usage analysis

---

## Migration Path

### For Users

1. **Immediate** (v1.x - Current):
   - System defaults to Modern Gazebo
   - Classic still works with `GAZEBO_BACKEND=classic`
   - Deprecation warnings shown

2. **Transition** (v1.5 - 3 months):
   - Modern Gazebo fully tested
   - Migration guide available
   - Classic support in maintenance mode

3. **Final** (v2.0 - 6 months):
   - Classic support removed
   - Modern Gazebo only

### For Developers

1. Use Modern Gazebo for new features
2. Test with Modern Gazebo primarily
3. Report any Modern Gazebo issues immediately

---

## Quick Reference Commands

### Check Gazebo Version
```bash
gz sim --version          # Modern Gazebo
gazebo --version          # Classic Gazebo
```

### Set Backend
```bash
export GAZEBO_BACKEND=modern   # Use Modern (default)
export GAZEBO_BACKEND=classic  # Use Classic (deprecated)
export GAZEBO_BACKEND=auto     # Auto-detect
```

### Run Tests
```bash
pytest tests/test_modern_adapter.py
pytest tests/test_e2e_modern.py
```

---

## Next Immediate Steps (Phase 1C)

1. ✅ Check installed Gazebo version (`gz sim --version`)
2. ✅ Update default backend to 'modern' in config.py
3. ✅ Add deprecation warnings to classic_adapter.py

**After Phase 1C**, we proceed to Phase 2: Implementing ModernGazeboAdapter.

---

**Last Updated**: 2025-11-23
**Status**: Phase 1C in progress
**Next Phase**: Phase 2 (Modern Gazebo Implementation)
