"""
P3 sensor resources — ``gz://sensor/{name}`` (notify-then-poll, bare ping).

This module exposes each sensor's latest sample as an MCP **resource template**
``gz://sensor/{name}`` on the unified FastMCP app, and wires the
``resources/subscribe`` → ``notifications/resources/updated`` → ``resources/read``
("notify-then-poll") round-trip.

Resolution per ``resources/read``
---------------------------------
1. Resolve the request's ``GazeboSession`` via ``app.get_session(ctx)`` (HTTP →
   the per-``Mcp-Session-Id`` session; stdio → the shared/default session).
2. Map the sensor ``{name}`` → topic from ``await bridge.list_sensors()`` (the 4
   mock sensors: ``lidar_front``/``camera_rgb``/``imu_sensor``/``gps_sensor`` on
   ``/scan``/``/camera/image_raw``/``/imu``/``/gps/fix``). An unknown name raises
   (the SDK maps it to a resource error).
3. If the session has a cached subscription sample for that uri (set by a prior
   fetch under an active subscription), serve it; otherwise fetch a fresh
   one-shot via ``await bridge.sensor_snapshot(topic)``, cache it if subscribed,
   and return it.
4. The returned JSON payload is **capped** (``MAX_SAMPLE_JSON_BYTES``) so a
   pathological sample never overruns the transport — a too-large sample is
   replaced by a small ``{"error": "SAMPLE_TOO_LARGE", ...}`` envelope.

Notify-then-poll contract (HONEST, bare ping carries NO data)
-------------------------------------------------------------
- ``resources/subscribe(gz://sensor/<name>)`` records intent in
  ``session.subscriptions[uri]`` as a :class:`SensorSub` (latest-sample cache +
  ``subscribed`` flag + the resolved topic). It then performs an initial fetch
  and emits ONE ``notifications/resources/updated`` carrying ONLY the bare URI
  (no payload). The client reacts by issuing ``resources/read`` to pull the
  cached sample.
- ``notify_sensor_updated(session, ctx, name)`` is the server-side trigger used
  to push a fresh sample to a subscriber: it re-fetches, updates the cache, and
  emits the bare-URI ping. (The mock backend has no async sensor stream, so
  there is no background producer; a real backend's subscription callback would
  call this. The contract — ping-with-no-data, then client read — is fully
  wired and exercised end-to-end via subscribe's initial push and this helper.)

FastMCP 1.27.1 subscription API (verified empirically — see module-level notes)
-------------------------------------------------------------------------------
- ``@mcp.resource("gz://sensor/{name}")`` registers a resource **template**
  (the URI carries a parameter); ``read_resource`` resolves a concrete URI
  against it. A ``ctx: Context`` parameter is auto-injected and excluded from
  the URI-parameter match.
- FastMCP does **NOT** auto-wire ``resources/subscribe``: ``SubscribeRequest``
  is absent from the low-level server's ``request_handlers`` by default. We
  register handlers directly on ``mcp._mcp_server`` via its
  ``subscribe_resource()`` / ``unsubscribe_resource()`` decorators.
- The bare ping is emitted with ``ctx.session.send_resource_updated(uri)`` →
  ``ResourceUpdatedNotification(params=ResourceUpdatedNotificationParams(uri))``
  whose only field is ``uri`` (NO data) — verified against the SDK type.
- **Known SDK limitation:** ``Server.get_capabilities`` hardcodes
  ``ResourcesCapability(subscribe=False, ...)`` in 1.27.1, so the *advertised*
  capability flag stays ``False`` even though our handler is registered and
  functions. The server still processes ``SubscribeRequest`` and the round-trip
  works; only the advertised flag is stale. Documented, not faked.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import mcp.types as types
from mcp.server.fastmcp import Context, FastMCP

from gazebo_mcp.utils.logger import get_logger

_logger = get_logger("sensor_resources")

# URI scheme/prefix for the sensor resource template.
_URI_PREFIX = "gz://sensor/"

# Cap the JSON-encoded sample served by a resource read. A sample larger than
# this is replaced by a small error envelope so the transport is never overrun.
MAX_SAMPLE_JSON_BYTES = 256_000


@dataclass
class SensorSub:
    """Per-session subscription cache for one ``gz://sensor/<name>`` uri.

    Attributes:
        name: The sensor name (e.g. ``imu_sensor``).
        topic: The resolved sensor topic (e.g. ``/imu``).
        latest: The latest cached sample dict (``None`` until first fetch).
        subscribed: ``True`` once ``resources/subscribe`` registered intent;
            flipped to ``False`` by ``resources/unsubscribe``. The entry is kept
            (not deleted) on unsubscribe so a stale cached sample can still be
            read, mirroring the honest notify-then-poll contract.
    """

    name: str
    topic: str
    latest: Optional[dict] = None
    subscribed: bool = False

    def close(self) -> None:
        """Best-effort teardown hook (the mock has no live handle to release)."""
        self.subscribed = False
        self.latest = None


def _name_from_uri(uri: str) -> str:
    """Extract the sensor ``{name}`` from a ``gz://sensor/<name>`` uri."""
    s = str(uri)
    if s.startswith(_URI_PREFIX):
        return s[len(_URI_PREFIX):]
    # Fall back to the last path segment for robustness.
    return s.rstrip("/").rsplit("/", 1)[-1]


async def _name_to_topic(bridge: Any, name: str) -> str:
    """Resolve a sensor ``name`` → its topic via ``bridge.list_sensors()``.

    Raises:
        KeyError: if no sensor with that ``name`` exists (→ resource error).
    """
    sensors = await bridge.list_sensors()
    for s in sensors:
        if s.get("name") == name:
            topic = s.get("topic")
            if topic is None:
                raise KeyError(name)
            return topic
    raise KeyError(name)


def _cap_payload(sample: Any) -> str:
    """JSON-encode ``sample``, capping the result at ``MAX_SAMPLE_JSON_BYTES``.

    Returns the JSON string. A sample that encodes larger than the cap is
    replaced by a small ``SAMPLE_TOO_LARGE`` error envelope (also JSON).
    """
    try:
        encoded = json.dumps(sample, default=str)
    except (TypeError, ValueError) as e:  # noqa: BLE001 — defensive
        return json.dumps({"error": "SAMPLE_NOT_SERIALIZABLE", "detail": str(e)})
    if len(encoded.encode("utf-8")) > MAX_SAMPLE_JSON_BYTES:
        return json.dumps(
            {
                "error": "SAMPLE_TOO_LARGE",
                "limit_bytes": MAX_SAMPLE_JSON_BYTES,
                "topic": sample.get("topic") if isinstance(sample, dict) else None,
            }
        )
    return encoded


async def _fetch_sample(bridge: Any, topic: str) -> dict:
    """Fetch a one-shot sample for ``topic`` via the session bridge."""
    return await bridge.sensor_snapshot(topic)


async def _resolve_sample(ctx: Optional[Context], name: str) -> dict:
    """Resolve the sample for sensor ``name`` for the current request.

    Uses the per-session subscription cache when present (and the entry already
    holds a sample); otherwise fetches a fresh one-shot from the session bridge.
    On an active subscription the freshly fetched sample is written back into the
    cache. Raises ``KeyError`` for an unknown sensor name (→ resource error).
    """
    # Lazy import avoids an import cycle (app → resources → app).
    from gz_mcp_server.server.app import get_session

    session = await get_session(ctx)
    bridge = getattr(session, "bridge", None)
    if bridge is None:
        # Backend was down at create time; surface a structured, capped error.
        raise RuntimeError("sensor bridge unavailable for this session")

    uri = _URI_PREFIX + name
    sub = session.subscriptions.get(uri)
    if isinstance(sub, SensorSub):
        if sub.latest is not None:
            return sub.latest
        sample = await _fetch_sample(bridge, sub.topic)
        sub.latest = sample
        return sample

    # No subscription entry → resolve the topic and fetch one-shot.
    topic = await _name_to_topic(bridge, name)
    return await _fetch_sample(bridge, topic)


async def notify_sensor_updated(
    session: Any, ctx: Optional[Context], name: str
) -> dict:
    """Push a fresh sample to a subscriber: refresh cache + emit the BARE ping.

    Server-side trigger for notify-then-poll. Re-fetches the sample, updates the
    session's :class:`SensorSub` cache, then emits ONE
    ``notifications/resources/updated`` carrying ONLY the URI (no data). Callers
    that hold an active subscription react by issuing ``resources/read``.

    Returns the freshly fetched sample (also now in the cache).
    """
    uri = _URI_PREFIX + name
    bridge = getattr(session, "bridge", None)
    sub = session.subscriptions.get(uri)
    if not isinstance(sub, SensorSub):
        # No subscription → resolve topic and create a (subscribed=False) entry
        # so the cache is consistent, but do not emit a ping for a non-subscriber.
        topic = await _name_to_topic(bridge, name)
        sub = SensorSub(name=name, topic=topic)
        session.subscriptions[uri] = sub

    sample = await _fetch_sample(bridge, sub.topic)
    sub.latest = sample

    if sub.subscribed and ctx is not None:
        try:
            # BARE ping: ResourceUpdatedNotification carries only the URI.
            await ctx.session.send_resource_updated(types.AnyUrl(uri))
        except Exception as e:  # noqa: BLE001 — never let a notify failure abort
            _logger.warning("send_resource_updated failed", uri=uri, error=str(e))
    return sample


def register_sensor_resources(mcp: FastMCP) -> None:
    """Register the ``gz://sensor/{name}`` resource + subscribe/unsubscribe wiring.

    - ``@mcp.resource("gz://sensor/{name}")``: a resource template whose read
      returns the session's latest (capped JSON) sample for sensor ``{name}``.
    - ``mcp._mcp_server.subscribe_resource()``: records subscription intent in
      the session, performs an initial fetch, and emits the initial bare ping.
    - ``mcp._mcp_server.unsubscribe_resource()``: flips the cache entry's
      ``subscribed`` flag off (keeps the stale sample readable).

    FastMCP 1.27.1 does not auto-wire subscribe/unsubscribe, so we register the
    handlers on the underlying low-level server (``mcp._mcp_server``). See the
    module docstring for the verified API + the ``subscribe=False`` capability
    limitation.
    """

    @mcp.resource(
        "gz://sensor/{name}",
        name="gz_sensor",
        title="Gazebo sensor latest sample",
        description=(
            "Latest cached sample for the named Gazebo sensor "
            "(lidar_front/camera_rgb/imu_sensor/gps_sensor). JSON, payload-capped."
        ),
        mime_type="application/json",
    )
    async def sensor_resource(name: str, ctx: Context = None) -> str:  # type: ignore[assignment]
        """Return the latest sample for sensor ``{name}`` as capped JSON."""
        try:
            sample = await _resolve_sample(ctx, name)
        except KeyError as e:
            # Unknown sensor name → raise so FastMCP maps it to a resource error.
            raise ValueError(f"unknown sensor '{name}'") from e
        return _cap_payload(sample)

    # ---- subscribe / unsubscribe (manual wiring; not auto-registered) ----

    @mcp._mcp_server.subscribe_resource()
    async def _on_subscribe(uri) -> None:  # noqa: ANN001 — AnyUrl from the SDK
        """resources/subscribe → record intent + initial fetch + bare ping."""
        # Lazy import avoids the app↔resources import cycle.
        from gz_mcp_server.server.app import get_session

        ctx = mcp.get_context()
        name = _name_from_uri(uri)
        session = await get_session(ctx)
        bridge = getattr(session, "bridge", None)
        if bridge is None:
            _logger.warning("subscribe with no bridge", uri=str(uri))
            return
        try:
            topic = await _name_to_topic(bridge, name)
        except KeyError:
            _logger.warning("subscribe to unknown sensor", uri=str(uri))
            return
        key = _URI_PREFIX + name
        sub = session.subscriptions.get(key)
        if not isinstance(sub, SensorSub):
            sub = SensorSub(name=name, topic=topic)
            session.subscriptions[key] = sub
        sub.topic = topic
        sub.subscribed = True
        # Initial fetch + bare ping so a subscriber gets an immediate updated
        # signal and can poll the cached sample.
        await notify_sensor_updated(session, ctx, name)

    @mcp._mcp_server.unsubscribe_resource()
    async def _on_unsubscribe(uri) -> None:  # noqa: ANN001 — AnyUrl from the SDK
        """resources/unsubscribe → flip the cache entry's subscribed flag off."""
        from gz_mcp_server.server.app import get_session

        ctx = mcp.get_context()
        name = _name_from_uri(uri)
        session = await get_session(ctx)
        sub = session.subscriptions.get(_URI_PREFIX + name)
        if isinstance(sub, SensorSub):
            sub.subscribed = False

    _logger.info("Sensor resources registered (gz://sensor/{name} + subscribe wiring)")
