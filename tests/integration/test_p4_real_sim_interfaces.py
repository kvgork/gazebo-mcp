"""
P4-real acceptance: the REP-2018 ``SimInterfacesAdapter`` driven against a LIVE
``simulation_interfaces`` backend — the ``ros_gz_sim`` gzserver component
(``libgzserver_component.so``), which exposes the standard services under
``/gz_server``. This is cross-sim portability proven end-to-end: gazebo-mcp's
``GazeboInterface`` spoken entirely through REP-2018 services, not gz-specific ones.

Marked ``@pytest.mark.gazebo`` — runs under ``pixi run -e full pytest -m gazebo``;
SKIPS cleanly when the live stack is unavailable (no ``gz``/``ros2``, no
``rclpy``/``simulation_interfaces``, or the component doesn't come up in time).

Bring-up: ``ros2 launch ros_gz_sim gz_server.launch.py ... use_composition:=True
create_own_container:=True`` in its OWN process session; teardown SIGINTs the
whole process GROUP (the launch spawns a component_container child that a bare
parent-SIGINT leaves orphaned — verified 2026-07-08).
"""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.gazebo

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

SERVICE_NS = "/gz_server"
WORLD_SDF = (
    "<?xml version='1.0'?><sdf version='1.8'><world name='empty'>"
    "<plugin filename='gz-sim-physics-system' name='gz::sim::systems::Physics'/>"
    "<plugin filename='gz-sim-user-commands-system' name='gz::sim::systems::UserCommands'/>"
    "<plugin filename='gz-sim-scene-broadcaster-system' name='gz::sim::systems::SceneBroadcaster'/>"
    "</world></sdf>"
)
BOX_SDF = (
    "<?xml version='1.0'?><sdf version='1.8'><model name='box'><link name='l'>"
    "<collision name='c'><geometry><box><size>1 1 1</size></box></geometry></collision>"
    "<visual name='v'><geometry><box><size>1 1 1</size></box></geometry></visual>"
    "</link></model></sdf>"
)


@pytest.fixture(scope="module")
def sim_iface_adapter():
    if shutil.which("gz") is None or shutil.which("ros2") is None:
        pytest.skip("gz/ros2 not on PATH (need -e full)")
    try:
        import rclpy  # noqa: F401
        import simulation_interfaces.srv  # noqa: F401
    except Exception:
        pytest.skip("rclpy / simulation_interfaces not importable (need -e full)")

    proc = subprocess.Popen(
        [
            "ros2", "launch", "ros_gz_sim", "gz_server.launch.py",
            f"world_sdf_string:={WORLD_SDF}",
            "use_composition:=True", "create_own_container:=True",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,  # own process group -> group teardown kills the container child
    )
    node = None
    try:
        import rclpy
        rclpy.init()
        node = rclpy.create_node("gzmcp_p4_real_test")

        # Wait for the REP-2018 spawn service to appear (bring-up proof).
        deadline = time.time() + 40.0
        target = f"{SERVICE_NS}/spawn_entity"
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.skip("gz_server launch exited before services came up")
            if target in dict(node.get_service_names_and_types()):
                break
            time.sleep(0.5)
        else:
            pytest.skip(f"{target} did not appear in time")

        from gazebo_mcp.bridge.adapters.sim_interfaces_adapter import SimInterfacesAdapter
        yield SimInterfacesAdapter(node, service_ns=SERVICE_NS, timeout=10.0)
    finally:
        if node is not None:
            import rclpy
            node.destroy_node()
            rclpy.shutdown()
        # SIGINT the whole process group so the component_container child dies too.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass


def test_p4_real_sim_interfaces_full_lifecycle(sim_iface_adapter):
    """Full portable lifecycle over REP-2018 services: features -> pause -> spawn
    -> list -> get_state -> step -> set_state -> world props -> delete ->
    not-found -> reset — all through simulation_interfaces, no gz-specific calls."""
    import anyio
    from gazebo_mcp.bridge.gazebo_interface import EntityPose
    from gazebo_mcp.utils.exceptions import ModelNotFoundError

    adapter = sim_iface_adapter

    async def _run():
        # Capability discovery advertises at least spawn support.
        from simulation_interfaces.msg import SimulatorFeatures
        feats = await adapter.get_simulator_features()
        assert feats, "simulator advertised no features"
        assert SimulatorFeatures.SPAWNING in feats

        # Pause for deterministic poses + stepping. NOTE: gz applies queued
        # commands (spawn/set/delete) during an UPDATE, so each is followed by a
        # step() to apply it deterministically while paused (the adapter's step
        # pauses first, then StepSimulation).
        assert await adapter.pause_simulation() is True

        # Spawn via resource_string (SDF) + initial_pose, then step to apply it.
        assert await adapter.spawn_entity(
            "box", BOX_SDF, EntityPose(position=(1.0, 2.0, 0.5), orientation=(0.0, 0.0, 0.0, 1.0))
        ) is True
        r = await adapter.step(steps=1)
        assert r["steps"] == 1

        assert "box" in await adapter.list_entities()

        st = await adapter.get_entity_state("box")
        assert st["pose"]["position"][0] == pytest.approx(1.0, abs=0.05), st
        assert st["pose"]["position"][1] == pytest.approx(2.0, abs=0.05), st

        # Multi-step (adapter pauses first, as REP-2018 requires the sim PAUSED).
        assert (await adapter.step(steps=5))["steps"] == 5

        # Teleport via set_entity_state, apply with a step, then read it back.
        assert await adapter.set_entity_state(
            "box", EntityPose(position=(3.0, 4.0, 0.5), orientation=(0.0, 0.0, 0.0, 1.0))
        ) is True
        await adapter.step(steps=1)
        st2 = await adapter.get_entity_state("box")
        assert st2["pose"]["position"][0] == pytest.approx(3.0, abs=0.1), st2
        assert st2["pose"]["position"][1] == pytest.approx(4.0, abs=0.1), st2

        # World properties reflect the paused state + the live entity.
        info = await adapter.get_world_properties()
        assert info.paused is True
        assert "box" in info.models

        # Delete, apply with a step, then it is gone.
        assert await adapter.delete_entity("box") is True
        await adapter.step(steps=1)
        assert "box" not in await adapter.list_entities()

        # Getting a missing entity is an honest ModelNotFoundError.
        with pytest.raises(ModelNotFoundError):
            await adapter.get_entity_state("box")

        # Reset the simulation (SCOPE_ALL).
        assert await adapter.reset_simulation() is True

    anyio.run(_run)
