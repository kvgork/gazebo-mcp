"""
Gazebo backend configuration system.

Manages backend selection (Classic vs Modern) via environment variables.
"""

import os
from enum import Enum
from typing import Optional


class GazeboBackend(Enum):
    """Available Gazebo backends."""
    CLASSIC = "classic"
    MODERN = "modern"
    AUTO = "auto"
    MOCK = "mock"  # In-memory deterministic backend for CI / no-Gazebo dev


class GazeboConfig:
    """
    Configuration for Gazebo backend selection.

    Environment Variables:
    - GAZEBO_BACKEND: 'classic', 'modern', or 'auto' (default: modern)
    - GAZEBO_WORLD_NAME: Default world name for Modern (default: 'default')
    - GAZEBO_TIMEOUT: Service call timeout in seconds (default: 5.0)

    NOTE: Classic Gazebo is DEPRECATED and will be removed in v2.0.0.
          Default is now 'modern' to encourage migration.
    """

    def __init__(
        self,
        backend: Optional[GazeboBackend] = None,
        world_name: str = "default",
        timeout: float = 5.0,
        own_world: bool = False,
        step_size: float = 0.001,
        rtf: float = 1.0,
        model_manifest: Optional[str] = None,
        *,
        max_force_n: float = 1000.0,
        max_torque_nm: float = 500.0,
        max_joint_velocity: float = 10.0,
        max_joint_effort: float = 500.0,
        max_persistent_wrenches: int = 8,
        rate_limit_hz: float = 50.0,
        strict_bounds: bool = False,
    ):
        """
        Initialize Gazebo configuration.

        Args:
            backend: Gazebo backend to use (reads from env if None)
            world_name: Default world name
            timeout: Service call timeout in seconds
            own_world: If True, the bridge provisions and owns its own world
                (OWN mode); if False, it attaches to an externally-launched
                world (ATTACH mode). Reads GAZEBO_OWN_WORLD when default.
            step_size: Physics step size in seconds (max_step_size).
            rtf: Target real-time factor for the provisioned world.
            model_manifest: Optional path to a JSON manifest describing models
                to pre-spawn into a provisioned world (None = none).

        Actuation-bounds (P5 hardening, keyword-only, backward compatible). These
        feed ``BoundsConfig.from_config`` and are enforced inside the bridge as a
        safety backstop (clamp when ``strict_bounds`` is False, raise when True):
            max_force_n: Cap on |force| vector magnitude (N).
            max_torque_nm: Cap on |torque| vector magnitude (N·m).
            max_joint_velocity: Cap on |vel-mode value| (rad/s or m/s).
            max_joint_effort: Cap on |force/effort-mode value| (N·m or N).
            max_persistent_wrenches: Max simultaneous persistent wrenches.
            rate_limit_hz: Per-entity actuation rate cap (Hz); <=0 disables.
            strict_bounds: False => clamp over-limit commands; True => raise.
        """
        # Read from environment if not provided
        # Default changed from 'auto' to 'modern' (Classic is deprecated)
        if backend is None:
            backend_str = os.getenv('GAZEBO_BACKEND', 'modern').lower()
            try:
                backend = GazeboBackend(backend_str)
            except ValueError:
                raise ValueError(
                    f"Invalid GAZEBO_BACKEND: {backend_str}. "
                    f"Must be 'classic', 'modern', 'auto', or 'mock'"
                )

        self.backend = backend
        self.world_name = world_name
        self.timeout = timeout
        self.own_world = own_world
        self.step_size = step_size
        self.rtf = rtf
        self.model_manifest = model_manifest

        # Actuation-bounds (P5 hardening).
        self.max_force_n = max_force_n
        self.max_torque_nm = max_torque_nm
        self.max_joint_velocity = max_joint_velocity
        self.max_joint_effort = max_joint_effort
        self.max_persistent_wrenches = max_persistent_wrenches
        self.rate_limit_hz = rate_limit_hz
        self.strict_bounds = strict_bounds

        self._validate()

    def _validate(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if not self.world_name:
            raise ValueError("World name cannot be empty")

        if self.step_size <= 0:
            raise ValueError("step_size must be positive")

        if self.rtf <= 0:
            raise ValueError("rtf must be positive")

        # Actuation-bounds caps must be non-negative (0 = maximally restrictive).
        # rate_limit_hz is DELIBERATELY EXCLUDED: <= 0 is the documented "rate
        # limiting disabled" sentinel (see RateLimiter + p5-hardening.md §1.4),
        # not an invalid value — rejecting it here would crash a legitimate
        # GAZEBO_RATE_LIMIT_HZ=0 / negative "disable" configuration.
        for _name in (
            "max_force_n",
            "max_torque_nm",
            "max_joint_velocity",
            "max_joint_effort",
        ):
            if getattr(self, _name) < 0:
                raise ValueError(f"{_name} must be non-negative")

        if self.max_persistent_wrenches < 0:
            raise ValueError("max_persistent_wrenches must be non-negative")

    @staticmethod
    def from_environment() -> 'GazeboConfig':
        """
        Create config from environment variables.

        Environment Variables:
        - GAZEBO_BACKEND, GAZEBO_WORLD_NAME, GAZEBO_TIMEOUT
        - GAZEBO_OWN_WORLD: '1'/'true'/'yes' enables OWN mode (default: False)
        - GAZEBO_STEP_SIZE: physics step size in seconds (default: 0.001)
        - GAZEBO_RTF: target real-time factor (default: 1.0)
        - GAZEBO_MODEL_MANIFEST: path to a JSON model manifest (default: None)
        - GAZEBO_MAX_FORCE_N: |force| magnitude cap in N (default: 1000)
        - GAZEBO_MAX_TORQUE_NM: |torque| magnitude cap in N·m (default: 500)
        - GAZEBO_MAX_JOINT_VELOCITY: |vel-mode| cap (default: 10)
        - GAZEBO_MAX_JOINT_EFFORT: |force/effort-mode| cap (default: 500)
        - GAZEBO_MAX_PERSISTENT_WRENCHES: max simultaneous persistent (default: 8)
        - GAZEBO_RATE_LIMIT_HZ: per-entity actuation rate cap; <=0 disables (default: 50)
        - GAZEBO_STRICT_BOUNDS: '1'/'true'/'yes' => raise instead of clamp (default: 0)

        Returns:
            GazeboConfig instance
        """
        def _env_float(name: str, default: str) -> float:
            raw = os.getenv(name, default)
            try:
                return float(raw)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{name} must be a number, got {raw!r}. "
                    f"Unset it to use the default ({default})."
                )

        def _env_int(name: str, default: str) -> int:
            raw = os.getenv(name, default)
            try:
                return int(raw)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{name} must be an integer, got {raw!r}. "
                    f"Unset it to use the default ({default})."
                )

        def _env_bool(name: str, default: str) -> bool:
            return os.getenv(name, default).lower() in ('1', 'true', 'yes')

        return GazeboConfig(
            backend=None,  # Read from GAZEBO_BACKEND
            world_name=os.getenv('GAZEBO_WORLD_NAME', 'default'),
            timeout=_env_float('GAZEBO_TIMEOUT', '5.0'),
            own_world=os.getenv('GAZEBO_OWN_WORLD', '0').lower() in ('1', 'true', 'yes'),
            step_size=_env_float('GAZEBO_STEP_SIZE', '0.001'),
            rtf=_env_float('GAZEBO_RTF', '1.0'),
            model_manifest=os.getenv('GAZEBO_MODEL_MANIFEST'),
            # Actuation-bounds (P5 hardening).
            max_force_n=_env_float('GAZEBO_MAX_FORCE_N', '1000.0'),
            max_torque_nm=_env_float('GAZEBO_MAX_TORQUE_NM', '500.0'),
            max_joint_velocity=_env_float('GAZEBO_MAX_JOINT_VELOCITY', '10.0'),
            max_joint_effort=_env_float('GAZEBO_MAX_JOINT_EFFORT', '500.0'),
            max_persistent_wrenches=_env_int('GAZEBO_MAX_PERSISTENT_WRENCHES', '8'),
            rate_limit_hz=_env_float('GAZEBO_RATE_LIMIT_HZ', '50.0'),
            strict_bounds=_env_bool('GAZEBO_STRICT_BOUNDS', '0'),
        )

    # Spec alias — `from_env()` is the name used by the P0-B contract.
    from_env = from_environment

    def __repr__(self) -> str:
        return (
            f"GazeboConfig(backend={self.backend.value}, "
            f"world_name={self.world_name}, timeout={self.timeout}, "
            f"own_world={self.own_world}, step_size={self.step_size}, "
            f"rtf={self.rtf}, model_manifest={self.model_manifest}, "
            f"max_force_n={self.max_force_n}, max_torque_nm={self.max_torque_nm}, "
            f"max_joint_velocity={self.max_joint_velocity}, "
            f"max_joint_effort={self.max_joint_effort}, "
            f"max_persistent_wrenches={self.max_persistent_wrenches}, "
            f"rate_limit_hz={self.rate_limit_hz}, strict_bounds={self.strict_bounds})"
        )
