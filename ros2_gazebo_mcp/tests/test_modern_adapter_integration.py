#!/usr/bin/env python3
"""
Integration tests for Modern Gazebo adapter.

Tests all 10 GazeboInterface methods with Modern Gazebo (ros_gz_interfaces).

Requirements:
- Modern Gazebo (Fortress/Garden/Harmonic) running
- ros_gz packages installed
- Environment: GAZEBO_BACKEND=modern

Run:
    python3 tests/test_modern_adapter_integration.py
"""

import sys
import os
import time
import asyncio
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import rclpy
from rclpy.node import Node

from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
from gazebo_mcp.bridge.gazebo_interface import EntityPose, EntityTwist
from gazebo_mcp.utils.exceptions import (
    GazeboNotRunningError,
    GazeboTimeoutError,
    GazeboServiceError,
    ModelNotFoundError
)


class ModernAdapterTester:
    """Test suite for Modern Gazebo adapter."""

    def __init__(self):
        """Initialize test suite."""
        rclpy.init()
        self.node = Node('modern_adapter_test_node')
        self.world_name = os.environ.get('GAZEBO_WORLD_NAME', 'default')
        # Get timeout from environment, default to 20.0 seconds
        timeout = float(os.environ.get('GAZEBO_TIMEOUT', '20.0'))
        self.adapter = ModernGazeboAdapter(self.node, default_world=self.world_name, timeout=timeout)
        self.test_results: Dict[str, Dict[str, Any]] = {}

    def log(self, message: str, level: str = "INFO"):
        """Log test message."""
        print(f"[{level}] {message}")

    def record_test(self, test_name: str, passed: bool, message: str = "", error: str = ""):
        """Record test result."""
        self.test_results[test_name] = {
            "passed": passed,
            "message": message,
            "error": error
        }
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"  └─ {message}")
        if error:
            print(f"  └─ ERROR: {error}")

    async def test_backend_name(self):
        """Test 0: Verify backend name."""
        try:
            backend = self.adapter.get_backend_name()
            assert backend == "modern", f"Expected 'modern', got '{backend}'"
            self.record_test("test_backend_name", True, f"Backend: {backend}")
        except Exception as e:
            self.record_test("test_backend_name", False, error=str(e))

    async def test_spawn_entity(self):
        """Test 1: Spawn a simple box entity."""
        try:
            # Simple box SDF
            sdf_content = """
            <?xml version="1.0"?>
            <sdf version="1.8">
              <model name="test_box">
                <static>true</static>
                <link name="link">
                  <visual name="visual">
                    <geometry>
                      <box><size>1 1 1</size></box>
                    </geometry>
                  </visual>
                  <collision name="collision">
                    <geometry>
                      <box><size>1 1 1</size></box>
                    </geometry>
                  </collision>
                </link>
              </model>
            </sdf>
            """

            pose = EntityPose(
                position=(2.0, 0.0, 0.5),
                orientation=(0.0, 0.0, 0.0, 1.0)
            )

            success = await self.adapter.spawn_entity(
                name="test_box",
                sdf=sdf_content,
                pose=pose,
                world=self.world_name
            )

            assert success, "Spawn returned False"
            self.record_test("test_spawn_entity", True, "Successfully spawned test_box")
            return True
        except GazeboNotRunningError:
            self.record_test("test_spawn_entity", False, error="Gazebo not running")
            return False
        except Exception as e:
            self.record_test("test_spawn_entity", False, error=str(e))
            return False

    async def test_list_entities(self):
        """Test 2: List all entities in world."""
        try:
            entities = await self.adapter.list_entities(world="default")
            assert isinstance(entities, list), "Expected list of entities"

            # Should contain test_box from previous test
            self.record_test("test_list_entities", True,
                            f"Found {len(entities)} entities: {entities[:5]}")
            return True
        except Exception as e:
            self.record_test("test_list_entities", False, error=str(e))
            return False

    async def test_get_entity_state(self):
        """Test 3: Get state of spawned entity."""
        try:
            state = await self.adapter.get_entity_state(
                name="test_box",
                world=self.world_name
            )

            assert isinstance(state, dict), "Expected dict state"
            assert "name" in state, "State missing 'name'"
            assert "pose" in state, "State missing 'pose'"
            assert "twist" in state, "State missing 'twist'"

            self.record_test("test_get_entity_state", True,
                            f"Got state for test_box: pose={state['pose']['position']}")
            return True
        except Exception as e:
            self.record_test("test_get_entity_state", False, error=str(e))
            return False

    async def test_set_entity_state(self):
        """Test 4: Set entity pose."""
        try:
            new_pose = EntityPose(
                position=(3.0, 1.0, 0.5),
                orientation=(0.0, 0.0, 0.0, 1.0)
            )

            success = await self.adapter.set_entity_state(
                name="test_box",
                pose=new_pose,
                twist=None,  # Modern doesn't support twist in set_entity_state
                world=self.world_name
            )

            assert success, "Set entity state returned False"
            self.record_test("test_set_entity_state", True, "Successfully moved test_box")
            return True
        except Exception as e:
            self.record_test("test_set_entity_state", False, error=str(e))
            return False

    async def test_get_world_properties(self):
        """Test 5: Get world properties."""
        try:
            world_info = await self.adapter.get_world_properties(world=self.world_name)

            assert world_info.name == self.world_name, f"Expected world '{self.world_name}', got '{world_info.name}'"
            assert isinstance(world_info.models, list), "Expected list of models"

            self.record_test("test_get_world_properties", True,
                            f"World: {world_info.name}, Models: {len(world_info.models)}")
            return True
        except Exception as e:
            self.record_test("test_get_world_properties", False, error=str(e))
            return False

    async def test_pause_simulation(self):
        """Test 6: Pause simulation."""
        try:
            success = await self.adapter.pause_simulation(world=self.world_name)
            assert success, "Pause returned False"

            # Give it a moment
            await asyncio.sleep(0.5)

            self.record_test("test_pause_simulation", True, "Successfully paused simulation")
            return True
        except Exception as e:
            self.record_test("test_pause_simulation", False, error=str(e))
            return False

    async def test_unpause_simulation(self):
        """Test 7: Unpause simulation."""
        try:
            success = await self.adapter.unpause_simulation(world=self.world_name)
            assert success, "Unpause returned False"

            # Give it a moment
            await asyncio.sleep(0.5)

            self.record_test("test_unpause_simulation", True, "Successfully unpaused simulation")
            return True
        except Exception as e:
            self.record_test("test_unpause_simulation", False, error=str(e))
            return False

    async def test_reset_world(self):
        """Test 8: Reset world (model states only)."""
        try:
            success = await self.adapter.reset_world(world=self.world_name)
            assert success, "Reset world returned False"

            self.record_test("test_reset_world", True, "Successfully reset world")
            return True
        except Exception as e:
            self.record_test("test_reset_world", False, error=str(e))
            return False

    async def test_delete_entity(self):
        """Test 9: Delete spawned entity."""
        try:
            success = await self.adapter.delete_entity(
                name="test_box",
                world=self.world_name
            )

            assert success, "Delete returned False"
            self.record_test("test_delete_entity", True, "Successfully deleted test_box")
            return True
        except Exception as e:
            self.record_test("test_delete_entity", False, error=str(e))
            return False

    async def test_reset_simulation(self):
        """Test 10: Reset simulation (full reset)."""
        try:
            success = await self.adapter.reset_simulation(world=self.world_name)
            assert success, "Reset simulation returned False"

            self.record_test("test_reset_simulation", True, "Successfully reset simulation")
            return True
        except Exception as e:
            self.record_test("test_reset_simulation", False, error=str(e))
            return False

    async def run_all_tests(self):
        """Run all tests in sequence."""
        self.log("=" * 70)
        self.log("Modern Gazebo Adapter Integration Tests")
        self.log("=" * 70)
        self.log("")

        # Test 0: Backend name
        await self.test_backend_name()

        # Test if Gazebo is running by attempting spawn
        self.log("\nChecking if Modern Gazebo is running...")
        gazebo_running = await self.test_spawn_entity()

        if not gazebo_running:
            self.log("\n⚠️  WARNING: Modern Gazebo not detected!", "WARN")
            self.log("Please start Modern Gazebo first:", "WARN")
            self.log("  gz sim empty.sdf", "WARN")
            self.log("Or check if GAZEBO_BACKEND=modern is set", "WARN")
            self.print_summary()
            return

        # Run remaining tests
        self.log("\nRunning entity management tests...")
        await self.test_list_entities()
        await self.test_get_entity_state()
        await self.test_set_entity_state()

        self.log("\nRunning world property tests...")
        await self.test_get_world_properties()

        self.log("\nRunning simulation control tests...")
        await self.test_pause_simulation()
        await self.test_unpause_simulation()
        await self.test_reset_world()

        self.log("\nRunning cleanup tests...")
        await self.test_delete_entity()
        await self.test_reset_simulation()

        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        self.log("")
        self.log("=" * 70)
        self.log("Test Summary")
        self.log("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results.values() if r["passed"])
        failed = total - passed

        self.log(f"Total Tests:  {total}")
        self.log(f"Passed:       {passed} ✅")
        self.log(f"Failed:       {failed} ❌")

        if failed > 0:
            self.log("\nFailed Tests:")
            for name, result in self.test_results.items():
                if not result["passed"]:
                    self.log(f"  - {name}: {result['error']}")

        self.log("")
        if passed == total:
            self.log("🎉 All tests passed! Modern Gazebo adapter is fully functional.", "SUCCESS")
        else:
            self.log(f"⚠️  {failed} test(s) failed. Review errors above.", "WARN")

        self.log("=" * 70)

    def cleanup(self):
        """Cleanup resources."""
        self.node.destroy_node()
        rclpy.shutdown()


def main():
    """Main test entry point."""
    tester = ModernAdapterTester()

    try:
        # Run async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(tester.run_all_tests())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
