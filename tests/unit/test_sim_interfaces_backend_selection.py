"""P4-wire: ``GAZEBO_BACKEND=sim_interfaces`` backend selection.

Proves the config enum + factory branch route to ``SimInterfacesAdapter`` (the
REP-2018 client). The config-parse assertions run everywhere (mock/dev). The
factory-construction assertion needs ``geometry_msgs``/``simulation_interfaces``
(sim/full env only) so it ``importorskip``s — the factory imports the adapter
lazily on the SIM_INTERFACES branch precisely so ``-e dev`` stays import-safe.
"""

from unittest.mock import MagicMock

import pytest

from gazebo_mcp.bridge.config import GazeboBackend, GazeboConfig
from gazebo_mcp.bridge.factory import GazeboAdapterFactory


def test_config_enum_has_sim_interfaces():
    assert GazeboBackend("sim_interfaces") is GazeboBackend.SIM_INTERFACES


def test_config_from_env_selects_sim_interfaces(monkeypatch):
    monkeypatch.setenv("GAZEBO_BACKEND", "sim_interfaces")
    cfg = GazeboConfig.from_environment()
    assert cfg.backend is GazeboBackend.SIM_INTERFACES


def test_config_rejects_unknown_backend_message_lists_sim_interfaces(monkeypatch):
    monkeypatch.setenv("GAZEBO_BACKEND", "bogus")
    with pytest.raises(ValueError, match="sim_interfaces"):
        GazeboConfig.from_environment()


def test_factory_builds_sim_interfaces_adapter(monkeypatch):
    pytest.importorskip("geometry_msgs")
    pytest.importorskip("simulation_interfaces")
    monkeypatch.setenv("GAZEBO_SIM_INTERFACES_NS", "/custom_ns")
    cfg = GazeboConfig(
        backend=GazeboBackend.SIM_INTERFACES, world_name="empty", timeout=8.0
    )
    adapter = GazeboAdapterFactory(node=MagicMock(), config=cfg).create_adapter()

    from gazebo_mcp.bridge.adapters.sim_interfaces_adapter import SimInterfacesAdapter

    assert isinstance(adapter, SimInterfacesAdapter)
    assert adapter.get_backend_name() == "sim_interfaces"
    # honors GAZEBO_SIM_INTERFACES_NS
    assert adapter.service_ns == "/custom_ns"


def test_factory_sim_interfaces_default_namespace(monkeypatch):
    pytest.importorskip("geometry_msgs")
    pytest.importorskip("simulation_interfaces")
    monkeypatch.delenv("GAZEBO_SIM_INTERFACES_NS", raising=False)
    cfg = GazeboConfig(
        backend=GazeboBackend.SIM_INTERFACES, world_name="empty", timeout=8.0
    )
    adapter = GazeboAdapterFactory(node=MagicMock(), config=cfg).create_adapter()
    # default namespace = the ros_gz_sim gzserver component
    assert adapter.service_ns == "/gz_server"
