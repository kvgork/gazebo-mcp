"""Unit coverage for ModernGazeboAdapter._parse_last_json_object.

Locks the P2-real robustness fix (2026-07-10): ``gz topic -e -n 1 --json-output``
can flush several concatenated messages under load; the snapshot must still
return the LATEST typed sample instead of dropping to the raw-text fallback.
Pure string parsing — no gz / ROS needed, runs in the default (dev) suite.
"""

from gazebo_mcp.bridge.adapters.modern_adapter import ModernGazeboAdapter

_parse = ModernGazeboAdapter._parse_last_json_object


def test_single_object():
    assert _parse('{"a": 1}') == {"a": 1}


def test_newline_concatenated_returns_last():
    txt = '{"seq": 0}\n{"seq": 1}\n{"seq": 2}\n'
    assert _parse(txt) == {"seq": 2}


def test_concatenated_without_separator_returns_last():
    assert _parse('{"seq": 0}{"seq": 1}') == {"seq": 1}


def test_pretty_printed_single_object():
    assert _parse('{\n  "a": 1,\n  "b": 2\n}') == {"a": 1, "b": 2}


def test_trailing_partial_object_ignored():
    # the last object is incomplete -> return the last COMPLETE one
    assert _parse('{"seq": 0}\n{"seq": 1}\n{"seq":') == {"seq": 1}


def test_non_json_returns_none():
    assert _parse("not json at all") is None


def test_empty_returns_none():
    assert _parse("   ") is None


# --- wiring: prove _parse_last_json_object is actually used by _gz_snapshot ---
# (unit-testing the static helper alone would pass even if the helper were dead
#  code; these drive the production _gz_snapshot with a mocked `gz` subprocess so
#  a revert of the wiring at modern_adapter.py fails here.)

def _snapshot_adapter():
    """A ModernGazeboAdapter with only the attrs _gz_snapshot touches — bypasses
    __init__ (no rclpy/ROS needed). ``self._parse_last_json_object`` still
    resolves because the instance is a real ModernGazeboAdapter."""
    from types import SimpleNamespace

    adapter = object.__new__(ModernGazeboAdapter)
    adapter.timeout = 5.0
    adapter.logger = SimpleNamespace(warning=lambda *a, **k: None, debug=lambda *a, **k: None)
    return adapter


def test_gz_snapshot_returns_latest_typed_sample_on_multi_message_flush():
    from types import SimpleNamespace
    from unittest.mock import patch

    adapter = _snapshot_adapter()
    multi = '{"seq": 0}\n{"seq": 1}\n{"seq": 2}\n'  # gz flushed 3 buffered msgs
    with patch("subprocess.run",
               return_value=SimpleNamespace(returncode=0, stdout=multi, stderr="")):
        out = adapter._gz_snapshot("/imu")
    assert out == {"topic": "/imu", "format": "gz-json", "sample": {"seq": 2}, "typed": True}


def test_gz_snapshot_non_json_falls_back_to_gz_text():
    from types import SimpleNamespace
    from unittest.mock import patch

    adapter = _snapshot_adapter()
    with patch("subprocess.run",
               return_value=SimpleNamespace(returncode=0, stdout="not json echo", stderr="")):
        out = adapter._gz_snapshot("/imu")
    assert out["format"] == "gz-text" and out["typed"] is False
