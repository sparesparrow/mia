"""Install configuration of the VAG Audi bridge: environment mapping, vehicle identity, safety posture."""

import asyncio
import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.req("REQ-AUTO-014", "REQ-AUTO-006", "REQ-NFR-002")


MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "orchestration"
    / "mcp"
    / "modules"
    / "vag-audi-bridge"
    / "main.py"
)


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("vag_audi_bridge_main_env_identity", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge_module = load_bridge_module()
VagAudiBridge = bridge_module.VagAudiBridge
config_from_env = bridge_module.config_from_env
normalize_vin = bridge_module.normalize_vin

# Syntactically valid ISO 3779 VINs that are obviously made up (no real car).
TEST_VIN = "ABCDEFGH123456789"
OTHER_VIN = "ABCDEFGH987654321"
# Same shape, but contains the forbidden letters I and O.
BAD_VIN = "ABCDEFGHIO3456789"


def run(coro):
    return asyncio.run(coro)


# -- config_from_env ---------------------------------------------------------------------------


def test_empty_environment_leaves_defaults():
    config = config_from_env({})
    defaults = VagAudiBridge.DEFAULT_CONFIG
    for key in (
        "enable_uds_polling",
        "allowed_read_services",
        "default_identifiers",
        "transport_endpoint",
        "expected_vin",
        "model_hint",
        "model_year",
    ):
        assert config[key] == defaults[key], key


def test_config_from_env_does_not_share_default_lists():
    config = config_from_env({})
    config["allowed_read_services"].append("2E")
    assert VagAudiBridge.DEFAULT_CONFIG["allowed_read_services"] == ["19", "22"]


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", " Yes "])
def test_uds_polling_truthy_values(value):
    assert config_from_env({"VAG_ENABLE_UDS_POLLING": value})["enable_uds_polling"] is True


@pytest.mark.parametrize("value", ["false", "0", "no", "", "on", "enabled", "2"])
def test_uds_polling_other_values_are_false(value):
    assert config_from_env({"VAG_ENABLE_UDS_POLLING": value})["enable_uds_polling"] is False


def test_systemd_unit_values_map_onto_config():
    config = config_from_env(
        {
            "VAG_ENABLE_UDS_POLLING": "false",
            "VAG_ALLOWED_READ_SERVICES": "19,22",
            "VAG_DEFAULT_IDENTIFIERS": "F190",
            "ZMQ_TELEMETRY_SUB": "tcp://localhost:5556",
        }
    )
    assert config["enable_uds_polling"] is False
    assert config["allowed_read_services"] == ["19", "22"]
    assert config["default_identifiers"] == ["F190"]
    assert config["transport_endpoint"] == "tcp://localhost:5556"


def test_comma_lists_are_trimmed_and_skip_blanks():
    config = config_from_env(
        {"VAG_ALLOWED_READ_SERVICES": " 22 , ,19 ", "VAG_DEFAULT_IDENTIFIERS": "f190, 0xF187 ,"}
    )
    assert config["allowed_read_services"] == ["22", "19"]
    bridge = VagAudiBridge(config)
    assert bridge.config["default_identifiers"] == ["F190", "F187"]


def test_vehicle_identity_from_env():
    config = config_from_env(
        {
            "MIA_VEHICLE_VIN": f"  {TEST_VIN.lower()} ",
            "MIA_VEHICLE_MODEL": "A4 Cabriolet 8H",
            "MIA_VEHICLE_MODEL_YEAR": "2004",
        }
    )
    assert config["expected_vin"] == TEST_VIN
    assert config["model_hint"] == "A4 Cabriolet 8H"
    assert config["model_year"] == 2004


def test_blank_identity_values_count_as_unset():
    config = config_from_env({"MIA_VEHICLE_VIN": "", "MIA_VEHICLE_MODEL": "  ", "MIA_VEHICLE_MODEL_YEAR": ""})
    assert config["expected_vin"] is None
    assert config["model_hint"] is None
    assert config["model_year"] is None


@pytest.mark.parametrize("value", ["two thousand four", "2004.5", "MY2004"])
def test_invalid_model_year_is_none_with_warning(value, caplog):
    with caplog.at_level(logging.WARNING):
        config = config_from_env({"MIA_VEHICLE_MODEL_YEAR": value})
    assert config["model_year"] is None
    assert "MIA_VEHICLE_MODEL_YEAR" in caplog.text


CURRENT_YEAR = datetime.now(timezone.utc).year


@pytest.mark.parametrize("value", ["1980", "2004", str(CURRENT_YEAR), str(CURRENT_YEAR + 1)])
def test_model_year_within_bounds_is_kept(value):
    assert config_from_env({"MIA_VEHICLE_MODEL_YEAR": value})["model_year"] == int(value)


@pytest.mark.parametrize("value", ["-5", "0", "1000", "1979", str(CURRENT_YEAR + 2), "99999"])
def test_model_year_out_of_bounds_is_none_with_warning(value, caplog):
    with caplog.at_level(logging.WARNING):
        config = config_from_env({"MIA_VEHICLE_MODEL_YEAR": value})
    assert config["model_year"] is None
    assert "MIA_VEHICLE_MODEL_YEAR" in caplog.text


# -- VIN validation ----------------------------------------------------------------------------


def test_normalize_vin_accepts_and_uppercases():
    assert normalize_vin(f" {TEST_VIN.lower()}\n") == TEST_VIN


@pytest.mark.parametrize(
    "value",
    [
        BAD_VIN,  # I and O are not allowed
        "ABCDEFGHQ23456789",  # Q is not allowed
        TEST_VIN[:-1],  # 16 characters
        TEST_VIN + "1",  # 18 characters
        "ABCDEFGH-23456789",  # punctuation
        "ABCDEFGH 23456789",  # inner space
        "",
        None,
        12345678901234567,
    ],
)
def test_normalize_vin_rejects_invalid(value):
    assert normalize_vin(value) is None


def test_invalid_vin_is_ignored_and_not_echoed(caplog):
    with caplog.at_level(logging.WARNING):
        config = config_from_env({"MIA_VEHICLE_VIN": BAD_VIN})
    assert config["expected_vin"] is None
    assert "MIA_VEHICLE_VIN" in caplog.text
    assert BAD_VIN not in caplog.text
    assert BAD_VIN.lower() not in caplog.text.lower()


def test_invalid_vin_passed_directly_to_constructor_is_dropped(caplog):
    with caplog.at_level(logging.WARNING):
        bridge = VagAudiBridge({"expected_vin": BAD_VIN})
    assert bridge.config["expected_vin"] is None
    assert BAD_VIN not in caplog.text


# -- vehicle status: expected_vin and vin_match ------------------------------------------------


def test_status_without_vin_read_has_no_match():
    bridge = VagAudiBridge(config_from_env({"MIA_VEHICLE_VIN": TEST_VIN}))
    status = run(bridge.get_vehicle_status())
    assert status["vehicle_info"]["expected_vin"] == TEST_VIN
    assert status["vehicle_info"]["vin_match"] is None
    # Existing keys stay.
    for key in ("vehicle_info", "current_state", "connection", "telemetry", "diagnostics",
                "adapter_capabilities", "capabilities"):
        assert key in status
    for key in ("brand", "vehicle_family", "model_hint", "model_year"):
        assert key in status["vehicle_info"]


def test_status_vin_match_true_case_insensitive():
    bridge = VagAudiBridge(config_from_env({"MIA_VEHICLE_VIN": TEST_VIN}))
    run(bridge.ingest_transport_message({"vin": TEST_VIN.lower()}))
    assert run(bridge.get_vehicle_status())["vehicle_info"]["vin_match"] is True


def test_status_vin_match_false_for_other_car():
    bridge = VagAudiBridge(config_from_env({"MIA_VEHICLE_VIN": TEST_VIN}))
    run(bridge.ingest_transport_message({"vin": OTHER_VIN}))
    assert run(bridge.get_vehicle_status())["vehicle_info"]["vin_match"] is False


def test_status_vin_match_none_without_expected_vin():
    bridge = VagAudiBridge(config_from_env({}))
    run(bridge.ingest_transport_message({"vin": TEST_VIN}))
    status = run(bridge.get_vehicle_status())
    assert status["vehicle_info"]["expected_vin"] is None
    assert status["vehicle_info"]["vin_match"] is None


def _vin_match_after_read(read_vin, expected=TEST_VIN):
    bridge = VagAudiBridge(config_from_env({"MIA_VEHICLE_VIN": expected}))
    run(bridge.ingest_transport_message({"vin": read_vin}))
    return run(bridge.get_vehicle_status())["vehicle_info"]["vin_match"]


def test_status_vin_match_none_for_empty_read():
    assert _vin_match_after_read("") is None


@pytest.mark.parametrize("read_vin", [TEST_VIN.encode("ascii"), bytearray(TEST_VIN.encode("ascii"))])
def test_status_vin_match_true_for_bytes_read(read_vin):
    assert _vin_match_after_read(read_vin) is True


@pytest.mark.parametrize(
    "read_vin",
    [
        TEST_VIN + "\x00\x00\x00",
        "\x00" + TEST_VIN + " \x00 ",
        f"  {TEST_VIN}\r\n",
        (TEST_VIN + "\x00\x00").encode("ascii"),
        b" " + TEST_VIN.encode("ascii") + b"\x00 ",
    ],
)
def test_status_vin_match_true_for_padded_read(read_vin):
    assert _vin_match_after_read(read_vin) is True


def test_status_vin_match_false_for_bytes_of_other_car():
    assert _vin_match_after_read(OTHER_VIN.encode("ascii")) is False


@pytest.mark.parametrize(
    "read_vin",
    [
        "   ",
        "\x00\x00\x00",
        "garbage",
        BAD_VIN,
        TEST_VIN[:-1],
        TEST_VIN + "1",
        b"\xff\xfe\x00",
        12345678901234567,
        ["not", "a", "vin"],
        {"vin": TEST_VIN},
    ],
)
def test_status_vin_match_none_for_unusable_read(read_vin):
    assert _vin_match_after_read(read_vin) is None


def test_vin_match_does_not_log_vin_values(caplog):
    with caplog.at_level(logging.DEBUG):
        assert _vin_match_after_read(OTHER_VIN.encode("ascii")) is False
        assert _vin_match_after_read("garbage") is None
    assert TEST_VIN not in caplog.text
    assert OTHER_VIN not in caplog.text


def test_status_reports_model_from_env():
    bridge = VagAudiBridge(config_from_env({"MIA_VEHICLE_MODEL": "A4 Cabriolet", "MIA_VEHICLE_MODEL_YEAR": "2004"}))
    info = run(bridge.get_vehicle_status())["vehicle_info"]
    assert info["model_hint"] == "A4 Cabriolet"
    assert info["model_year"] == 2004


# -- safety: the environment cannot loosen the read-only posture ------------------------------

HOSTILE_ENV = {
    "VAG_READ_ONLY": "false",
    "VAG_ALLOW_WRITE_SERVICES": "true",
    "VAG_ALLOW_EXTENDED_SESSION": "true",
    "VAG_ALLOW_SECURITY_ACCESS": "true",
    "READ_ONLY": "false",
    "ALLOW_WRITE_SERVICES": "true",
    # 0x10 session control, 0x27 security access, 0x2E write DID, 0x31 routine control, 0x3E tester present
    "VAG_ALLOWED_READ_SERVICES": "19,22,10,27,2E,0x2e,31,3E",
}


def test_env_cannot_loosen_forced_overrides():
    bridge = VagAudiBridge(config_from_env(HOSTILE_ENV))
    assert bridge.config["read_only"] is True
    assert bridge.config["allow_write_services"] is False
    assert bridge.config["allow_extended_session"] is False
    assert bridge.config["allow_security_access"] is False
    caps = run(bridge.get_vehicle_status())["capabilities"]
    assert caps == {
        "read_only": True,
        "write_operations": False,
        "allow_extended_session": False,
        "allow_security_access": False,
    }


def test_forced_overrides_hold_even_if_env_config_is_tampered():
    config = config_from_env(HOSTILE_ENV)
    config.update(
        read_only=False, allow_write_services=True, allow_extended_session=True, allow_security_access=True
    )
    bridge = VagAudiBridge(config)
    assert bridge.config["read_only"] is True
    assert bridge.config["allow_write_services"] is False
    assert bridge.config["allow_extended_session"] is False
    assert bridge.config["allow_security_access"] is False


def test_read_services_outside_19_and_22_cannot_be_enabled():
    bridge = VagAudiBridge(config_from_env(HOSTILE_ENV))
    assert bridge.config["allowed_read_services"] == ["19", "22"]
    assert bridge.adapter_capabilities["allowed_read_services"] == ["19", "22"]


def test_read_services_can_only_be_narrowed():
    bridge = VagAudiBridge(config_from_env({"VAG_ALLOWED_READ_SERVICES": "0x22"}))
    assert bridge.config["allowed_read_services"] == ["22"]
    dtc = run(bridge.read_dtc_summary())
    assert dtc["status"] == "disabled"


def test_constructor_limits_read_services_given_directly():
    bridge = VagAudiBridge({"allowed_read_services": ["2E", "31", "19"]})
    assert bridge.config["allowed_read_services"] == ["19"]


@pytest.mark.parametrize("value", [None, 22, 1.5, object(), "19,22", b"22", {"19": True}])
def test_tampered_read_services_fail_closed_to_empty(value, caplog):
    with caplog.at_level(logging.WARNING):
        bridge = VagAudiBridge({"allowed_read_services": value})
    assert bridge.config["allowed_read_services"] == []
    assert bridge.adapter_capabilities["allowed_read_services"] == []
    assert "allowed_read_services" in caplog.text
    dtc = run(bridge.read_dtc_summary())
    assert dtc["status"] == "disabled"


@pytest.mark.parametrize("value", [("19", "22"), {"22"}])
def test_read_services_accept_tuple_and_set(value):
    bridge = VagAudiBridge({"allowed_read_services": value})
    assert sorted(bridge.config["allowed_read_services"]) == sorted(value)


def test_uds_enabled_from_env_still_blocked_without_uds_transport():
    bridge = VagAudiBridge(config_from_env({"VAG_ENABLE_UDS_POLLING": "true"}))
    result = run(bridge.read_data_identifiers(["F190"]))
    assert result["status"] == "blocked"
    assert result["values"] == {}


# -- main() reads the unit's environment --------------------------------------------------------


class _Stop(Exception):
    pass


def test_main_builds_bridge_from_environment(monkeypatch):
    captured = {}

    class RecordingBridge(VagAudiBridge):
        async def initialize(self):
            captured["config"] = dict(self.config)
            raise _Stop

    for name in list(HOSTILE_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VAG_ENABLE_UDS_POLLING", "false")
    monkeypatch.setenv("VAG_ALLOWED_READ_SERVICES", "19,22")
    monkeypatch.setenv("VAG_DEFAULT_IDENTIFIERS", "F190")
    monkeypatch.setenv("ZMQ_TELEMETRY_SUB", "tcp://localhost:5556")
    monkeypatch.setenv("MIA_VEHICLE_VIN", TEST_VIN)
    monkeypatch.setenv("MIA_VEHICLE_MODEL", "A4 Cabriolet")
    monkeypatch.setenv("MIA_VEHICLE_MODEL_YEAR", "2004")
    monkeypatch.setattr(bridge_module, "VagAudiBridge", RecordingBridge)

    with pytest.raises(_Stop):
        run(bridge_module.main())

    config = captured["config"]
    assert config["transport_endpoint"] == "tcp://localhost:5556"
    assert config["expected_vin"] == TEST_VIN
    assert config["model_hint"] == "A4 Cabriolet"
    assert config["model_year"] == 2004
    assert config["enable_uds_polling"] is False
    assert config["read_only"] is True
