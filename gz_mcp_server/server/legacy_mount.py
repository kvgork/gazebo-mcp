"""
Legacy-tool unification (P3): mount the 69 curated legacy tools as *native*
FastMCP tools on the unified app, so ONE FastMCP server serves the lean (19) +
legacy (69) surfaces over both stdio AND Streamable HTTP.

Why this works (and why the P0-B attempt did not)
--------------------------------------------------
FastMCP infers a tool's argument model (``FuncMetadata.arg_model``) from the
Python function's **typed signature** via ``inspect.signature(fn, eval_str=True)``
(see ``mcp.server.fastmcp.utilities.func_metadata.func_metadata``). The call path
validates incoming arguments against that inferred model. P0-B tried to keep a
``**kwargs`` closure and override ``Tool.parameters`` with the curated JSON
schema — ``tools/list`` looked right, but ``tools/call`` rejected the real
arguments because the inferred ``arg_model`` knew nothing about them.

This module instead synthesizes, for each legacy tool, a closure whose
``__signature__`` mirrors the curated JSON schema (typed, named, defaulted
params). ``Tool.from_function`` / ``mcp.add_tool`` then infer an ``arg_model``
that matches the curated surface, so the tool both LISTS with the right schema
AND CALLS correctly. The closure body delegates to the original adapter handler
and replicates ``sdk_app``'s payload shape verbatim.

Deprecation honor (P2 #17)
--------------------------
``GAZEBO_LEGACY_TOOLS`` (default ``"1"``):
- ``"1"`` (default): mount all 69 legacy tools (back-compat).
- ``"0"``: mount legacy MINUS the 8 deprecated advanced-sensor tools
  (the 7 advanced-sensor tools + ``subscribe_sensor_stream``).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import Any, Callable, Dict, Literal, Optional

from mcp.server.fastmcp import Context

from gazebo_mcp.tools._bridge_helper import (
    get_bridge_for_ctx,
    reset_current_bridge,
    set_current_bridge,
)
from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.utils.metrics import get_metrics_collector
from gz_mcp_server.server import sdk_app

_logger = get_logger("legacy_mount")

# JSON-schema primitive types -> Python type hints. ``array``/``object`` map to
# the bare containers (the curated schemas carry no item/property typing), and
# anything not listed here (or a missing/list ``type``) falls through to ``Any``.
_JSON_TO_HINT: Dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}

# Deprecated advanced-sensor tools (P2 #17). The curated registry exposes these
# under their ``gazebo_``-prefixed names; the spec lists the bare names. We match
# the prefixed names actually present in the registry. Unmounted when
# ``GAZEBO_LEGACY_TOOLS == "0"``.
_DEPRECATED_LEGACY_TOOLS = frozenset(
    {
        "gazebo_fuse_sensor_data",
        "gazebo_visualize_sensor_data",
        "gazebo_process_sensor_data",
        "gazebo_calibrate_sensor",
        "gazebo_record_sensor_stream",
        "gazebo_detect_objects_in_view",
        "gazebo_segment_camera_image",
        "gazebo_subscribe_sensor_stream",
    }
)


def _hint_for(pschema: Dict[str, Any]) -> Any:
    """Map a single JSON-schema property to a Python type hint.

    Edge cases handled:
    - ``enum`` -> ``typing.Literal[...vals]`` (takes precedence over ``type`` so
      an enumerated ``string`` becomes a ``Literal`` of its allowed values).
    - ``array`` WITH ``items`` -> ``list[<item hint>]`` (recursive). FastMCP then
      infers an ``items`` schema, so the advertised ``tools/list`` schema matches
      the curated one (P3 #1 fidelity). ``array`` without ``items`` -> bare
      ``list``. NOTE: giving arrays an item type also tightens ``tools/call``
      validation to that item type — this is an accepted trade-off: FastMCP 1.27.1
      derives BOTH the advertised schema AND the pre-handler validation from the
      same inferred ``arg_model``, so schema fidelity and lenient
      handler-produced errors cannot both be had for a native tool (see the
      module note). We favour fidelity (better LLM tool-calling) + standard
      JSON-RPC validation errors over the legacy rich-OperationResult-on-bad-type.
    - ``object`` -> bare ``dict`` (kept intentionally loose: synthesizing a typed
      model per object param would over-constrain free-form dicts like ``origin``
      for marginal list-schema gain; object ``properties`` fidelity is the
      documented residual of P3 #1).
    - other ``string``/``integer``/``number``/``boolean`` -> mapped primitive.
    - missing ``type`` (e.g. a free-form ``value`` param) or an unrecognized /
      list-valued ``type`` -> ``typing.Any``.
    """
    enum = pschema.get("enum")
    if enum:
        return Literal[tuple(enum)]
    jt = pschema.get("type")
    if jt == "array":
        items = pschema.get("items")
        if isinstance(items, dict):
            # Recursive: items:{type:string} -> list[str]; items:{type:object}
            # -> list[dict]; items with no/opaque type -> list[Any] (bare array).
            return list[_hint_for(items)]
        return list
    if isinstance(jt, str):
        return _JSON_TO_HINT.get(jt, Any)
    return Any


def _legacy_payload(result: OperationResult) -> Dict[str, Any]:
    """Replicate ``sdk_app``'s success payload shape EXACTLY."""
    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "error_code": result.error_code,
        "suggestions": result.suggestions,
    }


def _internal_error_payload(exc: Exception) -> Dict[str, Any]:
    """Replicate ``sdk_app``'s INTERNAL_ERROR catch-all payload EXACTLY."""
    return {
        "success": False,
        "data": None,
        "error": str(exc),
        "error_code": "INTERNAL_ERROR",
        "suggestions": [
            "Check tool arguments",
            "Verify Gazebo is running",
            "Check server logs",
        ],
    }


def _make_legacy_closure(
    name: str, params_schema: Dict[str, Any], handler: Callable
) -> Callable[..., Any]:
    """Build an ASYNC closure whose ``__signature__`` mirrors the curated schema.

    The closure is an ``async def _tool(**kwargs)`` with ``__signature__`` and
    ``__annotations__`` set so ``func_metadata`` / ``inspect.signature`` see real
    typed, named parameters and infer a matching ``arg_model``. The body invokes
    the original (synchronous) adapter ``handler`` and returns the legacy payload
    dict (or the INTERNAL_ERROR payload on the same exception path ``sdk_app``
    uses).

    Per-session isolation + non-blocking (P3, findings #1/#6/#7/#16)
    ---------------------------------------------------------------
    A ``ctx: Optional[Context] = None`` param is appended to the synthesized
    signature. FastMCP detects it by type annotation (``find_context_parameter``
    uses ``typing.get_type_hints``) and EXCLUDES it from the tool's input schema
    (verified on mcp 1.27.1), then INJECTS the request ``Context`` into it at call
    time. At entry the closure resolves the request's per-session bridge from
    ``ctx`` and binds it into the ``_current_bridge`` contextvar, so the sync
    handler's internal ``get_bridge()`` transparently hits the per-session world
    (over HTTP two ``Mcp-Session-Id`` clients stay isolated; over stdio / no ctx
    it stays the singleton — unchanged behaviour).

    The sync handler is run via ``asyncio.to_thread`` so it never blocks the
    event loop (#6). ``asyncio.to_thread`` runs the call inside a copy of the
    CURRENT context (``contextvars.copy_context``), so the contextvar binding set
    here is visible to the handler's ``get_bridge()`` in the worker thread.

    Required params -> no default. Optional params -> ``Optional[T]`` with the
    schema ``default`` if present, else ``None``.
    """
    props: Dict[str, Any] = params_schema.get("properties", {}) or {}
    required = set(params_schema.get("required", []) or [])

    sig_params: list[inspect.Parameter] = []
    annotations: Dict[str, Any] = {}
    for pname, pschema in props.items():
        hint = _hint_for(pschema)
        if pname in required:
            default: Any = inspect.Parameter.empty
        else:
            default = pschema.get("default", None)
            hint = Optional[hint]
        annotations[pname] = hint
        sig_params.append(
            inspect.Parameter(
                pname,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=hint,
            )
        )
    # Append the Context param LAST. FastMCP excludes it from the input schema and
    # injects the request Context into it; the curated data params are unaffected.
    sig_params.append(
        inspect.Parameter(
            "ctx",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=Optional[Context],
        )
    )
    annotations["ctx"] = Optional[Context]
    annotations["return"] = dict

    metrics = get_metrics_collector()

    async def _tool(ctx: Optional[Context] = None, **kwargs: Any) -> Dict[str, Any]:
        start = time.time()
        # Bind the per-session bridge for the duration of this call so the sync
        # handler's get_bridge() sees the right world. No ctx (stdio / unit test)
        # -> no bind -> singleton, unchanged.
        token = None
        if ctx is not None:
            try:
                bridge = await get_bridge_for_ctx(ctx)
                token = set_current_bridge(bridge)
            except Exception as e:  # noqa: BLE001 — fall back to the singleton
                _logger.debug(
                    "Per-session bridge bind failed; using singleton",
                    tool=name,
                    error=str(e),
                )
                token = None
        try:
            # Run the SYNC handler off the event loop. asyncio.to_thread copies
            # the current context (incl. _current_bridge) into the worker thread,
            # so handler -> get_bridge() resolves the per-session bridge.
            result: OperationResult = await asyncio.to_thread(handler, **kwargs)
            metrics.record_tool_call(
                tool_name=name, duration=time.time() - start, success=result.success
            )
            return _legacy_payload(result)
        except Exception as e:  # noqa: BLE001 — mirror sdk_app's catch-all
            metrics.record_tool_call(
                tool_name=name, duration=time.time() - start, success=False
            )
            metrics.record_error(error_type=type(e).__name__, error_message=str(e))
            _logger.exception("Error calling legacy tool", tool=name)
            return _internal_error_payload(e)
        finally:
            if token is not None:
                reset_current_bridge(token)

    _tool.__name__ = name
    _tool.__qualname__ = name
    _tool.__doc__ = None  # description is supplied explicitly to add_tool
    _tool.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        sig_params, return_annotation=dict
    )
    _tool.__annotations__ = annotations
    return _tool


def register_legacy_tools(mcp) -> int:
    """Mount the curated legacy tools onto ``mcp`` as native FastMCP tools.

    Reuses ``sdk_app._build_registry()`` as the source of truth. For each
    ``(types.Tool, handler)`` it builds a typed-signature closure (the proven
    recipe) and registers it via ``mcp.add_tool``.

    - **Lean-tool collisions:** legacy names that duplicate an already-registered
      lean tool are SKIPPED (lean wins; a debug line is logged).
    - **Deprecation gate (P2 #17):** when ``GAZEBO_LEGACY_TOOLS == "0"`` the 8
      deprecated advanced-sensor tools are NOT mounted; otherwise (default) all
      are mounted.

    Args:
        mcp: The ``FastMCP`` app (lean tools already registered).

    Returns:
        The number of legacy tools actually mounted.
    """
    import os

    exclude_deprecated = os.getenv("GAZEBO_LEGACY_TOOLS", "1") == "0"

    tools, handlers = sdk_app._build_registry()

    # Names already registered (the lean tools) — lean wins on collision.
    existing = set(mcp._tool_manager._tools.keys())

    mounted = 0
    skipped_deprecated = 0
    skipped_collision = 0
    for mcp_tool in tools:
        name = mcp_tool.name

        if exclude_deprecated and name in _DEPRECATED_LEGACY_TOOLS:
            skipped_deprecated += 1
            continue

        if name in existing:
            _logger.debug(
                "Skipping legacy tool that collides with a lean tool", tool=name
            )
            skipped_collision += 1
            continue

        params_schema = {
            "properties": mcp_tool.inputSchema.get("properties", {}),
            "required": mcp_tool.inputSchema.get("required", []),
        }
        fn = _make_legacy_closure(name, params_schema, handlers[name])
        mcp.add_tool(fn, name=name, description=mcp_tool.description)
        existing.add(name)
        mounted += 1

    _logger.info(
        "Legacy tools mounted on unified FastMCP app",
        mounted=mounted,
        skipped_deprecated=skipped_deprecated,
        skipped_collision=skipped_collision,
        exclude_deprecated=exclude_deprecated,
    )
    return mounted
