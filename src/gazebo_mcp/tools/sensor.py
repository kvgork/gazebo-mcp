"""
Lean one-shot sensor tools (P2).

Framework-agnostic async functions that wrap the GazeboBridgeNode sensor surface
(``list_sensors`` / ``sensor_snapshot`` / ``sensor_camera_image``) and return a
structured ``OperationResult``. The FastMCP app (``gz_mcp_server.server.app``)
delegates its ``@mcp.tool`` sensor_* functions to these; the camera wrapper
re-encodes the base64 image into a FastMCP ``Image`` content block.

The bridge node's sensor methods are ``async`` (passthrough to the adapter), so
these wrappers ``await`` them. Each function is non-throwing: any exception is
captured into ``OperationResult(success=False, ...)`` so callers (and the MCP
transport) always receive a well-formed payload.

Health folding: every descriptor returned by ``list_sensors`` already carries a
``health`` field, so ``sensor_list`` subsumes the legacy ``monitor_sensor_health``
tool at the lean layer.

Resolution / payload caps (clean, testable contract):
  - ``MAX_IMAGE_DIM`` (4096 px): a requested width or height above this is
    REJECTED with ``IMAGE_TOO_LARGE`` BEFORE the bridge is touched (we do NOT
    silently downscale — the rejection is a deterministic, testable contract).
  - ``MAX_IMAGE_B64_BYTES`` (1.5 MB): if the base64-encoded image exceeds this,
    the result is rejected with ``IMAGE_TOO_LARGE`` (guards the transport even
    when the dimensions are individually in range).
"""

import base64

from gazebo_mcp.tools._bridge_helper import get_bridge
from gazebo_mcp.utils import OperationResult

_SENSOR_OP_FAILED = "SENSOR_OP_FAILED"

# Reject any requested camera dimension above this many pixels (REJECT, not cap).
MAX_IMAGE_DIM = 4096

# Reject an encoded camera image whose base64 string exceeds this many bytes.
MAX_IMAGE_B64_BYTES = 1_500_000


async def sensor_list(sensor_type: str | None = None, world: str = "default") -> OperationResult:
    """List sensors in the world, optionally filtered by ``sensor_type``.

    Each descriptor carries a ``health`` field (folding in the legacy
    ``monitor_sensor_health`` tool). ``data`` = {"sensors", "count", "world"}.
    """
    try:
        b = get_bridge()
        sensors = await b.list_sensors(world)
        if sensor_type is not None:
            sensors = [s for s in sensors if s.get("type") == sensor_type]
        return OperationResult(
            success=True,
            data={"sensors": sensors, "count": len(sensors), "world": world},
        )
    except Exception as e:  # noqa: BLE001 — surface as structured failure
        return OperationResult(success=False, error=str(e), error_code=_SENSOR_OP_FAILED)


async def sensor_snapshot(topic: str, world: str = "default") -> OperationResult:
    """Return the latest sample for the sensor publishing on ``topic``.

    The sample shape is backend-dependent and callers branch on ``data["typed"]``:
      - MOCK backend: a deterministic TYPED dict (``"typed": True``) with
        per-sensor-type fields.
      - MODERN backend: a RAW gz-text echo (``{"format": "gz-text", "raw": ...,
        "typed": False}``); typed parsing is DEFERRED to P2-real.

    An unknown topic (``KeyError`` from the bridge) maps to
    ``error_code="UNKNOWN_TOPIC"``.
    """
    try:
        b = get_bridge()
        sample = await b.sensor_snapshot(topic, world)
        return OperationResult(success=True, data=sample)
    except KeyError:
        return OperationResult(
            success=False,
            error=f"unknown sensor topic '{topic}'",
            error_code="UNKNOWN_TOPIC",
            suggestions=["List available sensors with sensor_list to find a valid topic"],
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SENSOR_OP_FAILED)


async def sensor_camera_image(
    topic: str,
    resolution: str = "640x480",
    quality: int = 60,
    world: str = "default",
) -> OperationResult:
    """Return a one-shot encoded camera image as base64.

    Validation (before the bridge is touched):
      - ``resolution`` not in "WxH" form    -> INVALID_RESOLUTION
      - width or height <= 0                 -> INVALID_RESOLUTION
      - width or height > MAX_IMAGE_DIM      -> IMAGE_TOO_LARGE (REJECT, no cap)

    After encoding:
      - base64 length > MAX_IMAGE_B64_BYTES -> IMAGE_TOO_LARGE

    Bridge errors:
      - non-camera topic (``KeyError``)        -> NOT_A_CAMERA
      - modern backend (``NotImplementedError``) -> NOT_IMPLEMENTED_REAL

    ``quality`` is currently a NO-OP: the mock backend always emits a lossless
    PNG, so the quality hint is ignored. It is reserved for the real backend's
    JPEG encoding path (deferred).

    On success ``data`` = {"format", "width", "height", "bytes_b64",
    "image_b64"} plus ``synthetic``/``backend`` when the mock backend marks the
    frame as a synthetic solid-color fill.
    """
    try:
        # Parse + validate resolution BEFORE any bridge call.
        try:
            w_str, h_str = resolution.lower().split("x")
            req_w = int(w_str)
            req_h = int(h_str)
        except (ValueError, AttributeError):
            return OperationResult(
                success=False,
                error=f"invalid resolution '{resolution}'; expected 'WxH' (e.g. '640x480')",
                error_code="INVALID_RESOLUTION",
                suggestions=["Pass resolution as 'WxH', e.g. '640x480'"],
            )

        # Reject zero/negative dimensions here (INVALID_RESOLUTION) so they do
        # NOT slip through to the bridge and misclassify as SENSOR_OP_FAILED.
        if req_w < 1 or req_h < 1:
            return OperationResult(
                success=False,
                error=f"invalid resolution '{resolution}'; each dimension must be >= 1",
                error_code="INVALID_RESOLUTION",
                suggestions=["Pass positive dimensions, e.g. '640x480'"],
            )

        if req_w > MAX_IMAGE_DIM or req_h > MAX_IMAGE_DIM:
            return OperationResult(
                success=False,
                error=f"resolution exceeds {MAX_IMAGE_DIM} px cap",
                error_code="IMAGE_TOO_LARGE",
                suggestions=[f"Request a resolution with each dimension <= {MAX_IMAGE_DIM} px"],
            )

        b = get_bridge()
        img = await b.sensor_camera_image(topic, resolution, quality, world)

        b64 = base64.b64encode(img["data"]).decode()
        # MAX_IMAGE_B64_BYTES is a DEFENSIVE guard for the real backend's frames;
        # the mock's solid-color PNGs (capped at MAX_IMAGE_DIM) never approach it.
        if len(b64) > MAX_IMAGE_B64_BYTES:
            return OperationResult(
                success=False,
                error=f"encoded image exceeds {MAX_IMAGE_B64_BYTES} byte cap",
                error_code="IMAGE_TOO_LARGE",
                suggestions=["Request a smaller resolution or lower quality"],
            )

        data = {
            "format": img["format"],
            "width": img["width"],
            "height": img["height"],
            "bytes_b64": len(b64),
            "image_b64": b64,
        }
        # Propagate the synthetic/backend markers so an agent/vision consumer can
        # tell a mock solid-color fill from a real rendered frame.
        if "synthetic" in img:
            data["synthetic"] = img["synthetic"]
        if "backend" in img:
            data["backend"] = img["backend"]

        return OperationResult(success=True, data=data)
    except KeyError:
        return OperationResult(
            success=False,
            error=f"topic '{topic}' is not a camera image topic",
            error_code="NOT_A_CAMERA",
            suggestions=[
                "Use sensor_list to find a camera topic (e.g. '/camera/image_raw')",
            ],
        )
    except NotImplementedError:
        return OperationResult(
            success=False,
            error="camera image capture is not yet implemented on the real backend",
            error_code="NOT_IMPLEMENTED_REAL",
            suggestions=[
                "Run with GAZEBO_BACKEND=mock to exercise the deterministic camera path",
            ],
        )
    except Exception as e:  # noqa: BLE001
        return OperationResult(success=False, error=str(e), error_code=_SENSOR_OP_FAILED)
