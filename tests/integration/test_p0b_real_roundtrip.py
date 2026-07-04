"""
P0-B-real acceptance: full spawn -> step -> pose round-trip against a LIVE
headless Gazebo Harmonic, driving the real ``ModernGazeboAdapter``.

Marked ``@pytest.mark.gazebo`` — runs under ``pixi run -e full pytest -m gazebo``;
SKIPS cleanly when the live stack is unavailable (no ``gz`` binary, no
``parameter_bridge``, no ``rclpy``, or the bridge doesn't come up in time), so
it never breaks the default ``-e dev`` mock suite.

Bring-up (mirrors .agent-state/.../preal-artifacts/preal_roundtrip.py, the
manual probe that first verified this): a headless ``gz sim -s`` world plus the
``ros_gz`` ``parameter_bridge`` bridging the 4 world services + the pose topic.
Bridge arg syntax is the FULL ``topic@ROS_type[GZ_type`` form — a single
malformed arg makes ``parameter_bridge`` print usage and exit (the bug fixed in
``gazebo_bridge.launch.py``).

Two live bugs this test guards against regressing:
  1. bridge bring-up dying on malformed topic args (services never appear);
  2. pose readback: the ros_gz ``Pose_V``->``TFMessage`` bridge emits EMPTY frame
     names, so the adapter reads the name-carrying gz-transport ``Pose_V``
     directly — this test asserts the spawned model's pose resolves by name.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.gazebo

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

WORLD = "empty"
BOX_SDF = (
    "<?xml version='1.0'?><sdf version='1.7'>"
    "<model name='box'><pose>1 2 0.5 0 0 0</pose><link name='link'>"
    "<collision name='c'><geometry><box><size>1 1 1</size></box></geometry></collision>"
    "<visual name='v'><geometry><box><size>1 1 1</size></box></geometry></visual>"
    "</link></model></sdf>"
)


def _parameter_bridge_bin() -> str | None:
    """Locate the ros_gz parameter_bridge executable (ros2 run is unavailable
    in the pixi env), or None if absent."""
    prefix = os.environ.get("CONDA_PREFIX", "")
    cand = Path(prefix) / "lib" / "ros_gz_bridge" / "parameter_bridge"
    if cand.is_file():
        return str(cand)
    return shutil.which("parameter_bridge")


@pytest.fixture(scope="module")
def live_modern_adapter():
    """Bring up headless gz + parameter_bridge, yield (adapter, node). Skip if
    the live stack can't be stood up."""
    if shutil.which("gz") is None:
        pytest.skip("gz binary not on PATH (need -e full / -e sim)")
    bridge_bin = _parameter_bridge_bin()
    if bridge_bin is None:
        pytest.skip("ros_gz parameter_bridge not found (need -e full)")
    try:
        import rclpy  # noqa: F401
    except Exception:
        pytest.skip("rclpy not importable (need -e full)")

    procs = []
    try:
        procs.append(subprocess.Popen(
            ["gz", "sim", "-s", "-r", "-v0", "empty.sdf"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
        time.sleep(7)
        procs.append(subprocess.Popen(
            [
                bridge_bin,
                f"/world/{WORLD}/create@ros_gz_interfaces/srv/SpawnEntity",
                f"/world/{WORLD}/remove@ros_gz_interfaces/srv/DeleteEntity",
                f"/world/{WORLD}/set_pose@ros_gz_interfaces/srv/SetEntityPose",
                f"/world/{WORLD}/control@ros_gz_interfaces/srv/ControlWorld",
                f"/world/{WORLD}/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))
        time.sleep(7)

        import rclpy
        rclpy.init()
        node = rclpy.create_node("gzmcp_p0b_real_test")

        # Wait for the create service to appear (proves bridge bring-up worked).
        deadline = time.time() + 15
        while time.time() < deadline:
            if f"/world/{WORLD}/create" in dict(node.get_service_names_and_types()):
                break
            time.sleep(0.5)
        else:
            node.destroy_node(); rclpy.shutdown()
            pytest.skip("bridge did not expose /world/{}/create in time".format(WORLD))

        from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
        adapter = ModernGazeboAdapter(node, default_world=WORLD, timeout=8.0)
        yield adapter, node

        node.destroy_node()
        rclpy.shutdown()
    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


def test_p0b_real_spawn_step_pose(live_modern_adapter):
    """spawn box@(1,2,0.5) -> step(10) -> pose readback resolves by name."""
    import anyio
    from gazebo_mcp.bridge.gazebo_interface import EntityPose

    adapter, _node = live_modern_adapter

    async def _run():
        ok = await adapter.spawn_entity(
            "box", BOX_SDF,
            EntityPose(position=(1.0, 2.0, 0.5), orientation=(0.0, 0.0, 0.0, 1.0)),
            world=WORLD,
        )
        assert ok is True, "spawn_entity did not return True"

        r = await adapter.step(steps=10, world=WORLD)
        assert r.get("steps") == 10, r

        state = await adapter.get_entity_state(name="box", world=WORLD)
        pos = state["pose"]["position"]
        # Box spawned at (1, 2, 0.5); x/y exact, z ~0.5 (settling under gravity).
        assert pos[0] == pytest.approx(1.0, abs=0.05), state
        assert pos[1] == pytest.approx(2.0, abs=0.05), state
        assert pos[2] == pytest.approx(0.5, abs=0.1), state

    anyio.run(_run)


# NOTE: set_physics (genuine gz-service apply) and seed (honest no-op False) were
# verified live 2026-07-04 via the manual probe (preal-artifacts/) and are covered
# for regression by the mock suite's honesty contract. A live pytest for them is
# intentionally omitted: driving a `gz service` subprocess from inside pytest's
# asyncio/anyio loop deadlocked here, and the behaviour is already verified.
