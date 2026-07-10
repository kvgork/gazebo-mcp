"""
Per-session Gazebo state for the unified FastMCP app (P3).

A ``GazeboSession`` bundles everything that must be *isolated per MCP session*:
its own bridge (Gazebo connection / mock adapter), an optional connection
manager, and the set of live sensor subscriptions. Two distinct
``Mcp-Session-Id`` HTTP sessions each own a separate ``GazeboSession`` (separate
bridges + subscriptions); stdio is a single implicit session that owns one
shared/default ``GazeboSession``.

Mock-safe by design: in ``GAZEBO_BACKEND=mock`` the bridge is the node-less
``MockGazeboAdapter`` (built via ``_bridge_helper``), there is no connection
manager, and ``aclose()`` is a no-op-safe teardown. This keeps the full
``-e dev`` suite runnable without Gazebo.

stdio vs HTTP bridge resolution
-------------------------------
- **stdio (default):** lean tools call the module-level ``get_bridge()`` process
  singleton. ``GazeboSession.create()`` reuses that same singleton in mock mode,
  so the default session and the lean-tool singleton are the same object.
- **HTTP (opt-in):** each ``Mcp-Session-Id`` resolves to its own
  ``GazeboSession`` via ``app.get_session(ctx)``; resources/HTTP tools that need
  the per-session bridge use ``_bridge_helper.get_bridge_for_ctx(ctx)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("gazebo_session")


@dataclass
class GazeboSession:
    """Lifespan/per-session context.

    Attributes:
        bridge: The ``GazeboBridgeNode`` for this session (mock in ``-e dev``).
            ``None`` only if the backend was unreachable at create time.
        connection_manager: Owning ``ConnectionManager`` when this session
            created its own ROS2 connection; ``None`` for mock / shared-singleton
            sessions (those do not own a connection to tear down).
        subscriptions: Map ``uri -> sub`` of live sensor subscriptions
            (e.g. ``gz://sensor/<name> -> SensorSub`` with a latest-sample cache
            and a handle). Populated by the P3 resource layer (Exec-C).
        real: ``True`` when backed by a real Gazebo, ``False`` for the mock.
    """

    bridge: object
    connection_manager: object | None = None
    subscriptions: dict[str, object] = field(default_factory=dict)
    real: bool = False

    @classmethod
    async def create(
        cls, config: Optional[object] = None, *, use_singleton: bool = False
    ) -> "GazeboSession":
        """Build a ``GazeboSession``, resilient to a down backend.

        Two bridge-binding modes:

        - ``use_singleton=True`` (the stdio/default session): bind to the process
          singleton via ``_bridge_helper.get_bridge()`` so the lean tools (which
          call ``get_bridge()`` directly) and this session share one world. No
          connection manager is owned (the singleton owns its own).
        - ``use_singleton=False`` (default — each per-HTTP-session session): build
          a *fresh, independent* bridge via ``_bridge_helper.build_fresh_bridge()``
          so two ``Mcp-Session-Id`` sessions get isolated state (the spec's
          "factory with node=None" path; the mock adapter's ``_worlds`` is
          instance-scoped, so a fresh node = a fresh world). In real mode the
          fresh bridge owns its own ``ConnectionManager``, recorded here so
          ``aclose()`` can disconnect it.

        Backend failures are swallowed so a session is always created (tools and
        resources retry lazily per call and return a structured error), mirroring
        the P0-B resilient-startup fix.

        ``config`` is accepted for forward-compatibility (per-session backend
        overrides) but currently unused — the helper reads the environment.

        Args:
            config: Reserved for a future per-session ``GazeboConfig`` override.
            use_singleton: Bind to the process singleton instead of a fresh
                bridge (used for the stdio/default session).

        Returns:
            A ``GazeboSession``; ``bridge`` may be ``None`` if the backend was
            unreachable at create time.
        """
        # Lazy import: keep the bridge helper out of the import path until a
        # session is actually built (avoids import cost for pure tools/list).
        from gazebo_mcp.tools._bridge_helper import (
            backend_is_mock,
            build_fresh_bridge,
            get_bridge,
        )

        is_mock = False
        try:
            is_mock = backend_is_mock()
        except Exception as e:  # noqa: BLE001 — env probe must not abort create
            _logger.warning("Backend probe failed; assuming non-mock", error=str(e))

        bridge = None
        try:
            bridge = get_bridge() if use_singleton else build_fresh_bridge()
        except Exception as e:  # noqa: BLE001 — a down backend must not kill create
            _logger.warning(
                "Bridge unavailable at session create; will retry lazily per call",
                error=str(e),
            )

        # A fresh real bridge owns a ConnectionManager (stashed by the helper);
        # the singleton/default session owns none (the helper owns the singleton).
        connection_manager = None
        if bridge is not None and not use_singleton:
            connection_manager = getattr(bridge, "_owning_connection_manager", None)

        # ``real`` reflects the configured backend, not whether the bridge is
        # currently up: ``real=False`` iff the MOCK backend is selected.
        return cls(
            bridge=bridge,
            connection_manager=connection_manager,
            subscriptions={},
            real=not is_mock,
        )

    async def aclose(self) -> None:
        """Tear down this session: drop subscriptions, close owned resources.

        Idempotent and mock-safe: clearing an empty ``subscriptions`` dict and a
        ``None`` connection manager are no-ops. Each step is best-effort — a
        failure to close one resource never prevents closing the others.
        """
        # 1) Unsubscribe / drop all sensor subscriptions.
        for uri, sub in list(self.subscriptions.items()):
            try:
                close = getattr(sub, "aclose", None) or getattr(sub, "close", None)
                if close is not None:
                    res = close()
                    if hasattr(res, "__await__"):
                        await res
            except Exception as e:  # noqa: BLE001 — best-effort teardown
                _logger.warning("Failed to close subscription", uri=uri, error=str(e))
        self.subscriptions.clear()

        # 2) Close the bridge if it exposes a close/shutdown hook (mock has none).
        if self.bridge is not None:
            try:
                close = (
                    getattr(self.bridge, "aclose", None)
                    or getattr(self.bridge, "close", None)
                    or getattr(self.bridge, "shutdown", None)
                )
                if close is not None:
                    res = close()
                    if hasattr(res, "__await__"):
                        await res
            except Exception as e:  # noqa: BLE001 — best-effort teardown
                _logger.warning("Failed to close bridge", error=str(e))

        # 3) Disconnect a connection manager this session owns (never the shared
        #    singleton — that one is owned by ``_bridge_helper``).
        if self.connection_manager is not None:
            try:
                disconnect = getattr(self.connection_manager, "disconnect", None)
                if disconnect is not None:
                    res = disconnect()
                    if hasattr(res, "__await__"):
                        await res
            except Exception as e:  # noqa: BLE001 — best-effort teardown
                _logger.warning("Failed to disconnect connection manager", error=str(e))
            finally:
                self.connection_manager = None
