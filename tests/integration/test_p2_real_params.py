"""
P2-real / P*-real #3 acceptance: live gz parameter registry round-trip against a
headless Gazebo Harmonic, driving the real ``ModernGazeboAdapter``.

Marked ``@pytest.mark.gazebo`` — runs under ``pixi run -e full pytest -m gazebo``;
SKIPS cleanly when the live stack is unavailable. Never breaks the ``-e dev`` mock
suite (the mock adapter has its own param impl).

Background: Harmonic exposes parameters on GZ-TRANSPORT under registry namespace
``/world/<w>`` (services ``declare_parameter`` / ``get_parameter`` /
``set_parameter`` / ``list_parameters``, typed ``gz.msgs.Parameter`` whose
``value`` is a ``google.protobuf.Any``). Stock worlds DECLARE NO parameters, so
this test declares a few itself via the ``declare_parameter`` service (the
Any-type-url text form), then exercises the adapter's list/get/set.

Two live bugs this codifies as fixed (found 2026-07-08 once a param-declaring
world existed — previously "get/set round-trip UNVERIFIED"):
  1. ``param_set`` used ``-t double -m 7.25``; ``gz param -s`` actually wants
     ``-t gz.msgs.Double -m 'data: 7.25'`` (message type + proto-text body), so
     set NEVER worked on a real registry.
  2. ``param_get`` returned ``splitlines()[-1]`` — the trailing ``----``
     separator — instead of the ``data:`` line; and proto3 omits ``data:`` for a
     default/false value.
"""

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


def _declare(name: str, type_url: str, body: str) -> bool:
    """Declare a parameter via the gz-transport declare_parameter service (the
    google.protobuf.Any type-url text form). Returns True on service success."""
    req = f'name: "{name}", value {{ [type.googleapis.com/{type_url}] {{ {body} }} }}'
    try:
        r = subprocess.run(
            [
                "gz", "service", "-s", f"/world/{WORLD}/declare_parameter",
                "--reqtype", "gz.msgs.Parameter",
                "--reptype", "gz.msgs.ParameterError",
                "--timeout", "5000", "--req", req,
            ],
            capture_output=True, text=True, timeout=10.0,
        )
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="module")
def live_param_adapter():
    """Headless gz empty.sdf + declared params + real ModernGazeboAdapter."""
    if shutil.which("gz") is None:
        pytest.skip("gz binary not on PATH (need -e full / -e sim)")
    try:
        import rclpy  # noqa: F401
    except Exception:
        pytest.skip("rclpy not importable (need -e full)")

    proc = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "-v0", "empty.sdf"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    node = None
    try:
        # Wait for the declare_parameter service to appear (bring-up proof).
        deadline = time.time() + 25.0
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.skip("gz exited before the param registry came up")
            try:
                svc = subprocess.run(
                    ["gz", "service", "-l"], capture_output=True, text=True, timeout=5.0
                )
                if f"/world/{WORLD}/declare_parameter" in svc.stdout:
                    ready = True
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        if not ready:
            pytest.skip("declare_parameter service did not appear in time")

        # Declare one param of each supported type (fresh world declares none).
        assert _declare("pd", "gz.msgs.Double", "data: 2.5"), "declare pd failed"
        assert _declare("ps", "gz.msgs.StringMsg", 'data: "hi"'), "declare ps failed"
        assert _declare("pb", "gz.msgs.Boolean", "data: true"), "declare pb failed"
        assert _declare("pi", "gz.msgs.Int32", "data: 3"), "declare pi failed"

        import rclpy
        rclpy.init()
        node = rclpy.create_node("gzmcp_p2_real_params_test")
        from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter
        adapter = ModernGazeboAdapter(node, default_world=WORLD, timeout=8.0)
        yield adapter
    finally:
        if node is not None:
            import rclpy
            node.destroy_node()
            rclpy.shutdown()
        try:
            proc.terminate()
            proc.wait(timeout=6)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


def test_p2_real_param_list_get_set_roundtrip(live_param_adapter):
    """list surfaces the declared params; get returns typed declared values; set
    updates them (the two fixed bugs); get reflects the new values."""
    import anyio

    adapter = live_param_adapter

    async def _run():
        names = await adapter.param_list(world=WORLD)
        for n in ("pd", "ps", "pb", "pi"):
            assert n in names, f"{n} missing from param_list {names}"

        # GET declared values, typed by gz message type.
        assert (await adapter.param_get("pd", world=WORLD))["value"] == pytest.approx(2.5)
        assert (await adapter.param_get("ps", world=WORLD))["value"] == "hi"
        assert (await adapter.param_get("pb", world=WORLD))["value"] is True
        assert (await adapter.param_get("pi", world=WORLD))["value"] == 3

        # SET each (was silently broken: wrong -t/-m form).
        assert await adapter.param_set("pd", 7.25, world=WORLD) is True
        assert await adapter.param_set("ps", "bye", world=WORLD) is True
        assert await adapter.param_set("pb", False, world=WORLD) is True
        assert await adapter.param_set("pi", 9, world=WORLD) is True

        # GET back the new values (pb=False exercises the proto3 default-omit path).
        assert (await adapter.param_get("pd", world=WORLD))["value"] == pytest.approx(7.25)
        assert (await adapter.param_get("ps", world=WORLD))["value"] == "bye"
        assert (await adapter.param_get("pb", world=WORLD))["value"] is False
        assert (await adapter.param_get("pi", world=WORLD))["value"] == 9

    anyio.run(_run)


def test_p2_real_param_get_undeclared_raises_keyerror(live_param_adapter):
    """An undeclared parameter is an honest KeyError (not a fabricated value)."""
    import anyio

    adapter = live_param_adapter

    async def _run():
        with pytest.raises(KeyError):
            await adapter.param_get("no_such_param_xyz", world=WORLD)

    anyio.run(_run)
