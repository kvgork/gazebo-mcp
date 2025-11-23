# Gazebo Migration Quick Start Guide

> **TL;DR**: 3-phase migration from Classic to Modern Gazebo over 4-6 weeks using abstraction layer pattern.

## 📋 Quick Reference

### Current State
- ✅ Uses Gazebo Classic (gazebo_msgs, gazebo_ros)
- ⚠️ README incorrectly claims "Gazebo Harmonic" support
- 📝 SDF 1.7 generation
- 🔧 Direct service calls to `/gazebo/*` paths

### Target State
- ✅ Uses Gazebo Modern (ros_gz_interfaces, ros_gz_sim)
- ✅ SDF 1.9+ generation
- ✅ World-namespaced paths `/world/{name}/*`
- 🔧 Abstraction layer supporting both backends

---

## 🚀 Getting Started

### Prerequisites
```bash
# Install Modern Gazebo
sudo apt-get install gz-fortress ros-humble-ros-gz

# Verify installation
gz sim --version  # Should show Fortress/Harmonic
ros2 pkg list | grep ros_gz  # Should list bridge packages
```

### File Locations
- **Full Plan**: `docs/GAZEBO_MIGRATION_LEARNING_PLAN.md` (comprehensive guide)
- **Summary**: `docs/MIGRATION_SUMMARY.md` (executive overview)
- **This File**: Quick start for immediate action

---

## 📅 3-Phase Timeline

### Phase 1: Dual Support (Weeks 1-3) - BUILD FOUNDATION
**Goal**: Both backends work simultaneously

**Critical Files**:
```
src/gazebo_mcp/bridge/
├── gazebo_interface.py          ← NEW: Abstract base class
├── config.py                     ← NEW: Configuration system
├── detection.py                  ← NEW: Auto-detect Gazebo version
├── factory.py                    ← NEW: Create appropriate adapter
├── adapters/
│   ├── classic_adapter.py        ← NEW: Wrap existing code
│   └── modern_adapter.py         ← NEW: Stub (implement Phase 2)
└── gazebo_bridge_node.py         ← MODIFY: Use adapter pattern
```

**Key Tasks**:
1. Create `GazeboInterface` ABC (5-10 methods)
2. Implement `ClassicGazeboAdapter` (wrap existing services)
3. Stub `ModernGazeboAdapter` (NotImplementedError for now)
4. Add configuration system (environment variables)
5. Implement auto-detection logic
6. Create factory pattern
7. Refactor `GazeboBridgeNode` to use adapter
8. Update all 17 MCP tools (add `world` parameter)

**Success Check**:
```bash
export GAZEBO_BACKEND=classic
gazebo --verbose &
python -m gazebo_mcp.server  # Should work via adapter
```

### Phase 2: Modern Implementation (Weeks 4-5) - IMPLEMENT MODERN
**Goal**: Modern Gazebo fully functional

**Critical Changes**:
```python
# Message format changes
from gazebo_msgs.srv import SpawnEntity  # OLD
from ros_gz_interfaces.srv import SpawnEntity  # NEW

# Field name changes
request.xml = sdf_string         # OLD: 'xml' field
request.sdf = sdf_string         # NEW: 'sdf' field
request.initial_pose = pose      # OLD: 'initial_pose'
request.pose = pose              # NEW: 'pose'
request.world = "default"        # NEW: Required field

# Service path changes
'/gazebo/spawn_entity'           # OLD: Classic path
'/world/default/create'          # NEW: Modern path
```

**Key Tasks**:
1. Implement all `ModernGazeboAdapter` methods
2. Update SDF generation (1.7 → 1.9+)
3. Add inertial properties to generated models
4. Implement world-namespaced paths
5. Write integration tests (both backends)
6. Performance benchmark

**Success Check**:
```bash
export GAZEBO_BACKEND=modern
gz sim -v4 &
python -m gazebo_mcp.server  # Should work with Modern
```

### Phase 3: Transition (Week 6) - SWITCH DEFAULT
**Goal**: Modern default, Classic deprecated

**Key Changes**:
```python
# config.py - Change default
backend_str = os.getenv('GAZEBO_BACKEND', 'modern')  # Was 'auto'

# classic_adapter.py - Add warning
warnings.warn(
    "Gazebo Classic is deprecated. Migrate to Modern.",
    DeprecationWarning
)
```

**Key Tasks**:
1. Change default backend to Modern
2. Add deprecation warnings
3. Create migration guide
4. Update all documentation
5. Set removal timeline (v2.0 in 2 months)

**Success Check**:
```bash
# No env var - should use Modern by default
gz sim -v4 &
python -m gazebo_mcp.server
```

---

## 🎯 Key Design Patterns

### 1. Abstraction Layer (Strategy Pattern)
```python
from abc import ABC, abstractmethod

class GazeboInterface(ABC):
    @abstractmethod
    async def spawn_entity(self, name, sdf, pose, world):
        pass
```

### 2. Adapter Pattern
```python
class ClassicGazeboAdapter(GazeboInterface):
    async def spawn_entity(self, name, sdf, pose, world):
        # Translate to Classic API
        request.xml = sdf  # Classic uses 'xml' not 'sdf'
        # world param ignored (Classic doesn't support)
```

### 3. Factory Pattern
```python
def create_adapter(config):
    if config.backend == CLASSIC:
        return ClassicGazeboAdapter(node)
    else:
        return ModernGazeboAdapter(node)
```

---

## 📊 Impact Assessment

### Code Changes
| Component | Files | Lines | Complexity |
|-----------|-------|-------|------------|
| Bridge Layer | 7 | ~1200 | HIGH |
| SDF Generation | 1 | ~400 | MEDIUM |
| MCP Tools | 17 | ~200 | LOW |
| Tests | 15 | ~1000 | MEDIUM |
| **Total** | **40** | **~2800** | **HIGH** |

### Migration Complexity
- **Overall**: 7/10 (HIGH)
- **Duration**: 4-6 weeks (20-30 hours/week)
- **Risk**: MEDIUM (mitigated by phased approach)

---

## ✅ Critical Success Factors

### Phase 1 Must-Haves
- [ ] GazeboInterface fully defined
- [ ] Classic adapter working
- [ ] Factory creates correct adapter
- [ ] Auto-detection functional
- [ ] Zero breaking changes to MCP tools

### Phase 2 Must-Haves
- [ ] Modern adapter fully implemented
- [ ] SDF 1.9 generation working
- [ ] All tests pass for both backends
- [ ] Performance acceptable (≤1.2x Classic)
- [ ] Error handling consistent

### Phase 3 Must-Haves
- [ ] Modern is default
- [ ] Deprecation warnings shown
- [ ] Migration guide published
- [ ] Timeline communicated (2 months)
- [ ] Classic still available (fallback)

---

## 🔧 Environment Variables

```bash
# Backend selection
export GAZEBO_BACKEND=classic   # Use Classic (deprecated)
export GAZEBO_BACKEND=modern    # Use Modern (default after Phase 3)
export GAZEBO_BACKEND=auto      # Auto-detect (default Phases 1-2)

# Modern Gazebo settings
export GAZEBO_WORLD_NAME=default  # Default world name
export GAZEBO_TIMEOUT=5.0         # Service timeout (seconds)
```

---

## 🆘 Common Issues

### "No Gazebo detected"
```bash
# Solution: Start Gazebo first
gz sim -v4 &
sleep 5
python -m gazebo_mcp.server
```

### "NotImplementedError: Modern adapter"
```bash
# Solution: Use Classic during Phase 1
export GAZEBO_BACKEND=classic
```

### "Service timeout"
```bash
# Solution: Increase timeout
export GAZEBO_TIMEOUT=10.0
```

### "SDF validation failed"
```bash
# Solution: Update to SDF 1.9
# - Add version='1.9'
# - Add <inertial> section
# - Add relative_to attributes
```

---

## 📚 Documentation Links

### Full Guides
- [Complete Migration Plan](GAZEBO_MIGRATION_LEARNING_PLAN.md) - 200+ pages, educational
- [Migration Summary](MIGRATION_SUMMARY.md) - Executive overview
- [This Quickstart](MIGRATION_QUICKSTART.md) - Fast reference

### External Resources
- [Gazebo Sim Docs](https://gazebosim.org/docs)
- [ros_gz GitHub](https://github.com/gazebosim/ros_gz)
- [SDF Spec](http://sdformat.org/spec)
- [Official Migration](https://github.com/gazebosim/docs/blob/master/fortress/migration_from_gazebo_classic.md)

### Specialist Help
```bash
# Get help from teaching specialists
/ask-specialist gazebo-simulation-mentor
/ask-specialist ros2-learning-mentor
/ask-specialist code-architecture-mentor
```

---

## 🎓 Learning Path

### Beginner (Start Here)
1. Read this quickstart
2. Review architecture diagram in MIGRATION_SUMMARY.md
3. Try running demos with both backends
4. Study GazeboInterface design

### Intermediate (Implementation)
1. Read full migration plan (Phase 1)
2. Study adapter pattern examples
3. Implement abstraction layer
4. Write tests for both backends

### Advanced (Optimization)
1. Implement Modern adapter (Phase 2)
2. Update SDF generation
3. Performance benchmark
4. Plan deprecation strategy (Phase 3)

---

## 📞 Getting Help

1. **Check documentation first** (this file, full plan, summary)
2. **Use teaching specialists** (`/ask-specialist <name>`)
3. **File GitHub issues** for bugs
4. **Review examples** in `tests/` and `examples/`
5. **Consult official Gazebo docs** for API details

---

## 🎯 Next Steps

### Ready to Start?
1. **Read full plan**: `docs/GAZEBO_MIGRATION_LEARNING_PLAN.md`
2. **Set up environment**: Install both Gazebo versions
3. **Create branch**: `git checkout -b feature/gazebo-modern-migration`
4. **Start Phase 1**: Create `gazebo_interface.py`

### Not Ready Yet?
1. **Study current code**: Understand existing implementation
2. **Run demos**: Test current functionality
3. **Review tests**: See how system is tested
4. **Ask questions**: Use teaching specialists

---

*Last Updated: 2025-11-23*
*Status: Ready for implementation*
*Estimated Duration: 4-6 weeks*
