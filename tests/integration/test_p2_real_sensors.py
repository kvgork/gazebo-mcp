"""
P2-real acceptance: live sensor discovery + snapshot against a headless Gazebo
Harmonic, driving the real ``ModernGazeboAdapter``.

Marked ``@pytest.mark.gazebo`` — runs under ``pixi run -e full pytest -m gazebo``;
SKIPS cleanly when the live stack is unavailable (no ``gz`` binary, no ``rclpy``,
a sensor world that never publishes, or — for the camera case — a host that
cannot render headless). Never breaks the default ``-e dev`` mock suite.

Two built-in worlds cover the render / non-render split:
  - ``sensors.sdf``       -> NON-render sensors: ``/imu`` ``/altimeter``
                             ``/magnetometer`` ``/air_pressure`` (no GPU needed).
  - ``camera_sensor.sdf`` -> a render camera on ``/camera``, brought up headless
                             via EGL (``--headless-rendering
                             --render-engine-api-backend egl``) — works on a GPU
                             host; skips where headless rendering is unavailable.

What this guards (P2-real items 2/3/4, B1 live-verify):
  1. ``list_sensors`` discovers + classifies live ``gz topic -l`` topics (imu,
     camera). NOTE the classifier is topic-name-substring only, so altimeter /
     magnetometer / air_pressure are intentionally NOT classified (B3 gap — real
     health/classification is still deferred; asserted here so the gap is
     documented live, not silently assumed fixed).
  2. ``sensor_snapshot`` returns a TYPED ``gz-json`` sample for a BINARY Imu
     message AND a binary camera Image — the ``--json-output`` path that fixed
     the confirmed plain-text ``/imu`` echo hang (B1).
  3. ``sensor_camera_image`` (PNG/JPEG re-encode) remains honestly DEFERRED on
     the modern backend (raises rather than fabricating an image).
"""

import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

pytestmark = pytest.mark.gazebo

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _gz_topics() -> list:
    """Current gz topic list (empty on any failure)."""
    try:
        r = subprocess.run(
            ["gz", "topic", "-l"], capture_output=True, text=True, timeout=5.0
        )
        return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    except Exception:  # noqa: BLE001 - best-effort
        return []


@contextmanager
def _live_gz(world_file: str, expect_topic: str, render: bool = False):
    """Bring up a headless ``gz sim -s`` for ``world_file``, wait until
    ``expect_topic`` appears (proof of bring-up), yield, then SIGTERM-teardown
    ONLY the gz process we launched. Skips (never fails) if the stack/host can't
    stand the world up."""
    if shutil.which("gz") is None:
        pytest.skip("gz binary not on PATH (need -e full / -e sim)")
    cmd = ["gz", "sim", "-s", "-r", "-v0"]
    if render:
        # Headless EGL rendering for camera/render sensors (needs a GPU or a
        # software-GL EGL). Absent that, expect_topic never appears -> skip.
        cmd += ["--headless-rendering", "--render-engine-api-backend", "egl"]
    cmd += [world_file]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 25.0
        while time.time() < deadline:
            if expect_topic in _gz_topics():
                break
            if proc.poll() is not None:
                pytest.skip(f"gz exited before publishing {expect_topic}")
            time.sleep(0.5)
        else:
            reason = "render/GPU unavailable?" if render else "sensors unavailable?"
            pytest.skip(f"{expect_topic} not published in time ({reason})")
        yield
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=6)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


@pytest.fixture(scope="module")
def rclpy_node():
    """One rclpy node for the module (ModernGazeboAdapter needs a node, even
    though its sensor reads shell out to the ``gz`` CLI)."""
    try:
        import rclpy
    except Exception:
        pytest.skip("rclpy not importable (need -e full)")
    rclpy.init()
    node = rclpy.create_node("gzmcp_p2_real_sensors_test")
    yield node
    node.destroy_node()
    rclpy.shutdown()


def _adapter(node, world: str):
    from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter

    return ModernGazeboAdapter(node, default_world=world, timeout=8.0)


def test_p2_real_list_and_snapshot_imu(rclpy_node):
    """Non-render: list_sensors classifies ``/imu``; sensor_snapshot returns a
    TYPED gz-json sample for the binary Imu message (the B1 fix — no hang)."""
    import anyio

    with _live_gz("sensors.sdf", "/imu", render=False):
        adapter = _adapter(rclpy_node, "sensors")

        async def _run():
            sensors = await adapter.list_sensors(world="sensors")
            imus = [s for s in sensors if s["type"] == "imu"]
            assert imus, f"no imu classified among {sensors}"
            assert any(s["topic"] == "/imu" for s in imus), imus
            # B3 gap (documented live): the substring classifier does NOT
            # recognise altimeter/magnetometer/air_pressure -> not in the list.
            assert not any(
                s["topic"] in ("/altimeter", "/magnetometer", "/air_pressure")
                for s in sensors
            ), "classifier unexpectedly recognised a non-render, non-keyword sensor"

            snap = await adapter.sensor_snapshot("/imu", world="sensors")
            assert snap["typed"] is True, snap
            assert snap["format"] == "gz-json", snap
            sample = snap["sample"]
            # Imu carries an orientation quaternion + angular_velocity fields.
            assert "orientation" in sample, sample

        anyio.run(_run)


def test_p2_real_camera_snapshot_egl(rclpy_node):
    """Render: headless EGL camera publishes on ``/camera``; list_sensors
    classifies it; sensor_snapshot returns a TYPED image sample carrying real
    width/height/pixel data (B1 binary-safe on an Image message). Skips where the
    host cannot render headless."""
    import anyio

    with _live_gz("camera_sensor.sdf", "/camera", render=True):
        adapter = _adapter(rclpy_node, "camera_sensor")

        async def _run():
            sensors = await adapter.list_sensors(world="camera_sensor")
            assert any(
                s["type"] == "camera" and s["topic"] == "/camera" for s in sensors
            ), sensors

            snap = await adapter.sensor_snapshot("/camera", world="camera_sensor")
            assert snap["typed"] is True, snap
            assert snap["format"] == "gz-json", snap
            sample = snap["sample"]
            assert sample.get("width"), sample
            assert sample.get("height"), sample
            assert sample.get("data"), "camera image carried no pixel data"

        anyio.run(_run)


def test_p2_real_camera_image_still_deferred(rclpy_node):
    """``sensor_camera_image`` (PNG/JPEG re-encode) stays honestly DEFERRED on the
    modern backend — it needs an image codec (cv_bridge/Pillow) not wired here, so
    it must raise rather than fabricate an image."""
    import anyio

    adapter = _adapter(rclpy_node, "camera_sensor")

    async def _run():
        with pytest.raises(NotImplementedError):
            await adapter.sensor_camera_image("/camera", world="camera_sensor")

    anyio.run(_run)
