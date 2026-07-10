"""P4-wire live acceptance: ``GAZEBO_BACKEND=sim_interfaces`` routes the bridge —
and therefore the ``sim_*`` shim tools — through ``SimInterfacesAdapter`` (the
REP-2018 client) end-to-end, against a live ``ros_gz_sim`` gzserver component.

Complements ``test_p4_real_sim_interfaces.py`` (which instantiates the adapter
DIRECTLY) by proving the FACTORY / backend-selection wiring + tool routing — the
follow-up left open when the adapter itself was first landed (2026-07-08):

  * config accepts ``GAZEBO_BACKEND=sim_interfaces`` (unit-tested in
    ``tests/unit/test_sim_interfaces_backend_selection.py``);
  * ``GazeboBridgeNode`` -> factory builds a ``SimInterfacesAdapter`` for that
    backend (asserted live here through ``_bridge_helper.get_bridge()``);
  * the ``sim_*`` shim tools (spawn/step/delete/get_features), which delegate to
    ``scene_*``/``world_*`` and thus to ``get_bridge().adapter``, drive the
    REP-2018 services with no per-tool routing change (polymorphic dispatch);
  * gz-specific ops (sensor/param/joint/wrench) honestly degrade to a
    non-throwing failure under this backend (REP-2018 does not define them).

Marked ``@pytest.mark.gazebo`` — runs under
``pixi run -e full pytest --with-gazebo -m gazebo
tests/integration/test_p4_real_backend_selection.py`` and SKIPS cleanly when the
live stack is unavailable. Bring-up + process-GROUP teardown mirror
``test_p4_real_sim_interfaces.py`` (the launch spawns a component_container child
that a bare parent-SIGINT would orphan).
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
def sim_iface_bridge():
    """Bring up the gzserver component, select the sim_interfaces backend, and
    yield the process-singleton bridge built by the factory for that backend."""
    if shutil.which("gz") is None or shutil.which("ros2") is None:
        pytest.skip("gz/ros2 not on PATH (need -e full)")
    try:
        import rclpy  # noqa: F401
        import simulation_interfaces.srv  # noqa: F401
    except Exception:
        pytest.skip("rclpy / simulation_interfaces not importable (need -e full)")

    import gazebo_mcp.tools._bridge_helper as bh
    from gazebo_mcp.bridge.adapters.sim_interfaces_adapter import SimInterfacesAdapter

    # Select the REP-2018 backend for the process singleton + fresh session bridges.
    saved = {
        k: os.environ.get(k)
        for k in ("GAZEBO_BACKEND", "GAZEBO_SIM_INTERFACES_NS", "GAZEBO_WORLD_NAME")
    }
    os.environ["GAZEBO_BACKEND"] = "sim_interfaces"
    os.environ["GAZEBO_SIM_INTERFACES_NS"] = SERVICE_NS
    os.environ["GAZEBO_WORLD_NAME"] = "empty"
    bh._bridge_node = None
    bh._connection_manager = None

    proc = subprocess.Popen(
        [
            "ros2", "launch", "ros_gz_sim", "gz_server.launch.py",
            f"world_sdf_string:={WORLD_SDF}",
            "use_composition:=True", "create_own_container:=True",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,  # own process group -> group teardown kills the child
    )
    try:
        # get_bridge() connects rclpy (init + node + executor) and builds the
        # adapter via the factory. connect() does NOT probe gz, so it succeeds
        # regardless of the component's readiness; we gate on the service below.
        bridge = bh.get_bridge()
        assert isinstance(bridge.adapter, SimInterfacesAdapter), (
            f"factory did not build SimInterfacesAdapter for "
            f"GAZEBO_BACKEND=sim_interfaces (got {type(bridge.adapter).__name__})"
        )
        node = bridge.adapter.node

        # Wait for the REP-2018 spawn service (bring-up proof).
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

        yield bridge
    finally:
        try:
            if bh._connection_manager is not None:
                bh._connection_manager.disconnect()
        except Exception:  # noqa: BLE001
            pass
        bh._bridge_node = None
        bh._connection_manager = None
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # SIGINT the whole process group so the component_container child dies too.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass


def test_backend_selected_adapter_is_sim_interfaces(sim_iface_bridge):
    """The factory built the REP-2018 adapter for GAZEBO_BACKEND=sim_interfaces."""
    assert sim_iface_bridge.adapter.get_backend_name() == "sim_interfaces"


def test_sim_get_features_tool_reports_sim_interfaces_backend(sim_iface_bridge):
    """The sim_get_features tool reads the live backend name off the bridge."""
    import anyio
    from gazebo_mcp.tools import sim

    res = anyio.run(sim.sim_get_features)
    assert res.success, res
    assert res.data["backend"] == "sim_interfaces", res.data


def test_sim_tools_route_spawn_step_delete_through_rep2018(sim_iface_bridge):
    """sim_spawn/sim_step/sim_delete drive the REP-2018 services end-to-end.

    Pausing is done directly on the adapter (not a routing concern; the sim_*
    surface exposes no pause verb). gz applies queued spawn/delete during an
    UPDATE, so each mutation is followed by a step() to apply it while paused.
    """
    import anyio
    from gazebo_mcp.tools import sim

    adapter = sim_iface_bridge.adapter

    async def _run():
        assert await adapter.pause_simulation() is True

        spawn = await sim.sim_spawn(name="box", sdf=BOX_SDF, x=1.0, y=2.0, world="empty")
        assert spawn.success, spawn
        step = await sim.sim_step(steps=1, world="empty")
        assert step.success, step
        assert "box" in await adapter.list_entities()

        delete = await sim.sim_delete(name="box", world="empty")
        assert delete.success, delete
        assert (await sim.sim_step(steps=1, world="empty")).success
        assert "box" not in await adapter.list_entities()

    anyio.run(_run)


def test_gz_specific_op_degrades_honestly_under_sim_interfaces(sim_iface_bridge):
    """A gz-specific op (sensor listing) is not defined by REP-2018, so under the
    sim_interfaces backend it must fail honestly (non-throwing OperationResult),
    never silently succeed."""
    import anyio
    from gazebo_mcp.tools import sensor

    res = anyio.run(lambda: sensor.sensor_list(world="empty"))
    assert res.success is False, res
