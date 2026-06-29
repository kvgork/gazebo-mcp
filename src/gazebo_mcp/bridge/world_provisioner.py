"""
World provisioner for the Gazebo MCP bridge (P0-B).

Two operating modes, selected by ``GazeboConfig.own_world``:

- OWN mode (``own_world=True``): the bridge provisions and owns its own world.
  :meth:`WorldProvisioner.provision` renders ``worlds/provisioned.sdf.jinja`` to
  a temp file (substituting ``world_name``/``step_size``/``rtf`` plus any models
  from the manifest), launches it via ``launch/provisioned_world.launch.py``,
  and returns the world name. :meth:`destroy` tears the launched process down.

- ATTACH mode (``own_world=False``): the bridge attaches to an externally
  launched world; :meth:`provision` returns ``None`` and :meth:`destroy` is a
  no-op.

Import-safety: this module imports nothing from ``ros_gz``/``rclpy``/``jinja2``
at module load. Templating is hand-rolled with :class:`string.Template` so the
module imports cleanly in the ``-e dev`` environment (which has no jinja2). The
launch side is WRITE-ONLY this session (live verification deferred).
"""

import asyncio
import json
import os
import string
import tempfile
from typing import List, Optional

from .config import GazeboConfig
from ..utils.logger import get_logger


# Path to the world template, resolved relative to the repo root.
# (this file: <repo>/src/gazebo_mcp/bridge/world_provisioner.py)
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)
_TEMPLATE_PATH = os.path.join(_REPO_ROOT, "worlds", "provisioned.sdf.jinja")
_LAUNCH_PATH = os.path.join(_REPO_ROOT, "launch", "provisioned_world.launch.py")


class WorldProvisioner:
    """Provisions (OWN mode) or attaches to (ATTACH mode) a Gazebo world."""

    def __init__(self, config: GazeboConfig):
        """
        Args:
            config: Gazebo configuration. ``own_world`` selects the mode;
                ``world_name``/``step_size``/``rtf``/``model_manifest`` feed the
                rendered template.
        """
        self.config = config
        self.logger = get_logger("world_provisioner")
        self._proc = None  # launched subprocess (OWN mode only)
        self._rendered_path: Optional[str] = None  # temp SDF path (OWN mode)

    # -- public API --

    async def provision(self) -> Optional[str]:
        """
        Provision the world.

        Returns:
            The world name (OWN mode) or ``None`` (ATTACH mode / not own_world).
        """
        if not self.config.own_world:
            self.logger.info(
                "ATTACH mode (own_world=False): not provisioning a world; "
                "attaching to an externally launched world."
            )
            return None

        world_name = self.config.world_name
        sdf = self._render_world()

        # Write rendered SDF to a temp file the launch file can consume.
        fd, path = tempfile.mkstemp(
            prefix=f"gz_world_{world_name}_", suffix=".sdf"
        )
        with os.fdopen(fd, "w") as f:
            f.write(sdf)
        self._rendered_path = path
        self.logger.info(f"Rendered provisioned world '{world_name}' to {path}")

        await self._launch(world_name, path)
        return world_name

    async def destroy(self) -> None:
        """Tear down a provisioned world (OWN mode). No-op in ATTACH mode."""
        if self._proc is not None:
            self.logger.info("Terminating provisioned world launch process")
            try:
                self._proc.terminate()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Launch process did not exit; killing")
                    self._proc.kill()
                    await self._proc.wait()
            except ProcessLookupError:
                pass
            except Exception as e:  # noqa: BLE001 - teardown is best-effort
                self.logger.warning(f"Error terminating launch process: {e}")
            finally:
                self._proc = None

        if self._rendered_path and os.path.exists(self._rendered_path):
            try:
                os.unlink(self._rendered_path)
            except OSError as e:
                self.logger.warning(
                    f"Could not remove rendered world {self._rendered_path}: {e}"
                )
            finally:
                self._rendered_path = None

    # -- internals --

    def _load_models(self) -> List[dict]:
        """Load model definitions from the JSON manifest, if any."""
        manifest = self.config.model_manifest
        if not manifest:
            return []
        if not os.path.exists(manifest):
            self.logger.warning(f"Model manifest not found: {manifest}")
            return []
        try:
            with open(manifest, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(f"Could not read model manifest {manifest}: {e}")
            return []
        # Accept either a bare list or {"models": [...]}.
        if isinstance(data, dict):
            data = data.get("models", [])
        return data if isinstance(data, list) else []

    @staticmethod
    def _render_models(models: List[dict]) -> str:
        """Render manifest models into <include> blocks for the world body."""
        blocks = []
        for m in models:
            name = m.get("name", "model")
            uri = m.get("uri", "")
            pose = m.get("pose", [0, 0, 0, 0, 0, 0])
            pose_str = " ".join(str(v) for v in pose)
            blocks.append(
                "    <include>\n"
                f"      <name>{name}</name>\n"
                f"      <uri>{uri}</uri>\n"
                f"      <pose>{pose_str}</pose>\n"
                "    </include>"
            )
        return "\n".join(blocks)

    def _render_world(self) -> str:
        """
        Render the world SDF from the template.

        Uses :class:`string.Template` (``$world_name`` etc.) so no jinja2
        dependency is required. The template file lives at ``_TEMPLATE_PATH``.
        """
        with open(_TEMPLATE_PATH, "r") as f:
            template_src = f.read()

        models = self._render_models(self._load_models())

        return string.Template(template_src).safe_substitute(
            world_name=self.config.world_name,
            step_size=self.config.step_size,
            rtf=self.config.rtf,
            models=models,
        )

    async def _launch(self, world_name: str, sdf_path: str) -> None:
        """
        Launch the provisioned world via ros2 launch (OWN mode).

        WRITE-ONLY this session: live verification is deferred (no ros_gz / gz
        installed in ``-e dev``). The command is constructed to match
        ``launch/provisioned_world.launch.py``.
        """
        cmd = [
            "ros2",
            "launch",
            _LAUNCH_PATH,
            f"world_name:={world_name}",
            f"world_sdf:={sdf_path}",
        ]
        self.logger.info(f"Launching provisioned world: {' '.join(cmd)}")
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
