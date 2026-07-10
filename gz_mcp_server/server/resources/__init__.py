"""P3 resource layer for the unified FastMCP app.

Exposes ``gz://sensor/{name}`` resources (latest cached sensor sample) plus the
notify-then-poll subscription wiring. See ``sensors.py``.
"""

from gz_mcp_server.server.resources.sensors import (
    SensorSub,
    register_sensor_resources,
)

__all__ = ["SensorSub", "register_sensor_resources"]
