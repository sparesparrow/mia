from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


logger = logging.getLogger(__name__)


@dataclass
class VagAudiTelemetry:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    speed_kmh: Optional[float] = None
    engine_rpm: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    fuel_level_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    vin: Optional[str] = None
    dtc_codes: list[str] = field(default_factory=list)
    did_values: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        return payload


class VagAudiBridge:
    CAPABILITY_ORDER = {
        "unknown": 0,
        "generic_pid_only": 1,
        "uds_read_only": 2,
    }
    CONNECTION_STATES = {
        "initializing",
        "probing",
        "connected",
        "degraded",
        "disconnected",
        "error",
    }

    DEFAULT_CONFIG = {
        "brand": "Audi",
        "vehicle_family": "VAG",
        "read_only": True,
        "transport_endpoint": "tcp://127.0.0.1:5556",
        "transport_format": "auto",
        "telemetry_topics": ["obd/telemetry", "mcu/status"],
        "enable_passive_monitoring": True,
        "enable_uds_polling": False,
        "poll_interval_seconds": 5.0,
        "timeout_seconds": 1.0,
        "request_can_id": "7E0",
        "response_can_id": "7E8",
        "functional_can_id": "7DF",
        "allowed_read_services": ["19", "22"],
        "default_identifiers": ["F190"],
        "allow_extended_session": False,
        "allow_security_access": False,
        "allow_write_services": False,
        "model_hint": None,
        "model_year": None,
    }

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        merged_config = dict(self.DEFAULT_CONFIG)
        if config:
            merged_config.update(config)

        # Force safe defaults even if a caller tries to loosen them.
        merged_config["read_only"] = True
        merged_config["allow_extended_session"] = False
        merged_config["allow_security_access"] = False
        merged_config["allow_write_services"] = False
        merged_config["allowed_read_services"] = [
            service.upper() for service in merged_config.get("allowed_read_services", [])
        ]
        merged_config["default_identifiers"] = [
            self._normalize_identifier(identifier)
            for identifier in merged_config.get("default_identifiers", [])
        ]

        self.config = merged_config
        self.telemetry = VagAudiTelemetry()
        self.current_state = "inactive"
        self.last_topic: Optional[str] = None
        self.last_message_at: Optional[datetime] = None
        self.adapter_capabilities = self._build_adapter_capabilities()
        self._running = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    async def initialize(self) -> bool:
        self._running = True
        if self.config["enable_passive_monitoring"]:
            self.current_state = "passive_monitoring"
            self.adapter_capabilities["connection_state"] = "probing"
        else:
            self.current_state = "ready"
            self.adapter_capabilities["connection_state"] = "connected"
        return True

    async def shutdown(self) -> None:
        self._running = False
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        self.current_state = "inactive"
        self.adapter_capabilities["connection_state"] = "disconnected"

    async def _monitor_telemetry(self) -> None:
        while self._running:
            await asyncio.sleep(self.config["poll_interval_seconds"])

    def _decode_transport_message(self, raw_message: Any) -> tuple[Optional[str], dict[str, Any]]:
        topic: Optional[str] = None
        payload_source = raw_message

        if isinstance(raw_message, (tuple, list)) and len(raw_message) >= 2:
            topic = self._decode_topic(raw_message[0])
            payload_source = raw_message[1]

        payload = self._decode_payload(payload_source)
        return topic, payload

    async def ingest_transport_message(self, raw_message: Any) -> None:
        topic, payload = self._decode_transport_message(raw_message)
        self.last_topic = topic
        self.last_message_at = datetime.now(timezone.utc)
        self.adapter_capabilities["last_message_at"] = self.last_message_at.isoformat()
        await self._update_base_telemetry(payload)
        if payload:
            self.current_state = "ready"
            if self.adapter_capabilities["connection_state"] != "error":
                self.adapter_capabilities["connection_state"] = "connected"

    async def _update_base_telemetry(self, payload: dict[str, Any]) -> None:
        if not payload:
            return

        capability_payload = payload.get("adapter_capabilities")
        if not isinstance(capability_payload, dict):
            capability_payload = {}

        now = datetime.now(timezone.utc)
        generic_pid_seen = False
        uds_data_seen = False

        field_aliases = {
            "speed_kmh": ("speed_kmh", "speed"),
            "engine_rpm": ("engine_rpm", "rpm"),
            "coolant_temp_c": ("coolant_temp_c", "coolant_temp", "coolant"),
            "fuel_level_percent": ("fuel_level_percent", "fuel_level"),
            "battery_voltage": ("battery_voltage", "voltage"),
            "vin": ("vin",),
        }

        for target_field, aliases in field_aliases.items():
            for alias in aliases:
                if alias in payload and payload[alias] is not None:
                    setattr(self.telemetry, target_field, payload[alias])
                    if target_field != "vin":
                        generic_pid_seen = True
                    break

        if "dtc_codes" in payload and isinstance(payload["dtc_codes"], list):
            self.telemetry.dtc_codes = [str(code) for code in payload["dtc_codes"]]
            if self.telemetry.dtc_codes:
                uds_data_seen = True

        if "did_values" in payload and isinstance(payload["did_values"], dict):
            self.telemetry.did_values.update(payload["did_values"])
            if payload["did_values"]:
                uds_data_seen = True

        self._update_adapter_runtime_state(payload, capability_payload, generic_pid_seen, uds_data_seen, now)
        self.telemetry.timestamp = now

    async def _refresh_readonly_identifiers(self) -> None:
        if not self.config["enable_uds_polling"] or not self._transport_supports_uds():
            return
        await self.read_data_identifiers(self.config["default_identifiers"])

    async def read_data_identifiers(self, identifiers: list[str]) -> dict[str, Any]:
        normalized_identifiers = [self._normalize_identifier(identifier) for identifier in identifiers]
        if normalized_identifiers:
            self.adapter_capabilities["last_uds_service"] = "22"
            self.adapter_capabilities["last_uds_identifier"] = normalized_identifiers[0]

        if not self.config["enable_uds_polling"]:
            return {
                "status": "disabled",
                "message": "UDS polling is disabled for the VAG Audi bridge.",
                "identifiers": normalized_identifiers,
                "values": {},
            }

        if not self._transport_supports_uds():
            return {
                "status": "blocked",
                "message": (
                    "Transport capability class "
                    f"'{self.adapter_capabilities['capability_class']}' does not support read-only UDS polling."
                ),
                "identifiers": normalized_identifiers,
                "values": {},
            }

        if "22" not in self.config["allowed_read_services"]:
            return {
                "status": "blocked",
                "message": "Service 0x22 is not allowlisted for this bridge.",
                "identifiers": normalized_identifiers,
                "values": {},
            }

        values = {
            identifier: self.telemetry.did_values.get(identifier)
            for identifier in normalized_identifiers
        }
        self.telemetry.did_values.update(values)

        return {
            "status": "unavailable",
            "message": "Read-only scaffold is not connected to a live UDS transport yet.",
            "identifiers": normalized_identifiers,
            "values": values,
        }

    async def read_dtc_summary(self) -> dict[str, Any]:
        self.adapter_capabilities["last_uds_service"] = "19"

        if not self.config["enable_uds_polling"]:
            return {
                "status": "disabled",
                "message": "UDS polling is disabled for the VAG Audi bridge.",
                "codes": [],
            }

        if not self._transport_supports_uds():
            return {
                "status": "blocked",
                "message": (
                    "Transport capability class "
                    f"'{self.adapter_capabilities['capability_class']}' does not support read-only UDS polling."
                ),
                "codes": [],
            }

        if "19" not in self.config["allowed_read_services"]:
            return {
                "status": "blocked",
                "message": "Service 0x19 is not allowlisted for this bridge.",
                "codes": [],
            }

        return {
            "status": "unavailable",
            "message": "Read-only scaffold is not connected to a live DTC source yet.",
            "codes": list(self.telemetry.dtc_codes),
        }

    async def get_vehicle_status(self) -> dict[str, Any]:
        return {
            "vehicle_info": {
                "brand": self.config["brand"],
                "vehicle_family": self.config["vehicle_family"],
                "model_hint": self.config["model_hint"],
                "model_year": self.config["model_year"],
            },
            "current_state": self.current_state,
            "connection": {
                "transport_endpoint": self.config["transport_endpoint"],
                "transport_format": self.config["transport_format"],
                "passive_monitoring": self.config["enable_passive_monitoring"],
                "uds_polling": self.config["enable_uds_polling"],
                "connection_state": self.adapter_capabilities["connection_state"],
                "last_topic": self.last_topic,
                "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            },
            "telemetry": self.telemetry.to_dict(),
            "diagnostics": {
                "dtc_codes": list(self.telemetry.dtc_codes),
                "did_values": dict(self.telemetry.did_values),
            },
            "adapter_capabilities": dict(self.adapter_capabilities),
            "capabilities": {
                "read_only": True,
                "write_operations": False,
                "allow_extended_session": False,
                "allow_security_access": False,
            },
        }

    async def get_diagnostics_report(self) -> dict[str, Any]:
        dtc_summary = await self.read_dtc_summary()
        return {
            "status": "ok",
            "message": "Read-only diagnostics report generated.",
            "vehicle_family": self.config["vehicle_family"],
            "brand": self.config["brand"],
            "read_only": True,
            "dtc_summary": dtc_summary,
            "did_values": dict(self.telemetry.did_values),
            "adapter_capabilities": dict(self.adapter_capabilities),
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }

    def _build_adapter_capabilities(self) -> dict[str, Any]:
        configured_class = self._normalize_capability_class(self.config.get("capability_class"))
        capability_source = self.config.get("capability_source")
        if configured_class != "unknown":
            capability_source = capability_source or "configured"
        else:
            capability_source = capability_source or "unknown"

        return {
            "capability_class": configured_class,
            "capability_source": capability_source,
            "adapter_kind": str(self.config.get("adapter_kind") or "unknown"),
            "transport": str(
                self.config.get("transport")
                or self._detect_transport(
                    self.config.get("transport_endpoint"),
                    self.config.get("device_path_or_address"),
                )
            ),
            "device_path_or_address": self.config.get("device_path_or_address"),
            "connection_state": "initializing",
            "active_protocol": self.config.get("active_protocol"),
            "addressing_mode": self.config.get("addressing_mode") or "functional",
            "request_can_id": self.config["request_can_id"],
            "response_can_id": self.config["response_can_id"],
            "functional_can_id": self.config["functional_can_id"],
            "uds_enabled": self.config["enable_uds_polling"],
            "read_only": True,
            "allowed_read_services": list(self.config["allowed_read_services"]),
            "default_identifiers": list(self.config["default_identifiers"]),
            "last_message_at": None,
            "last_pid_success_at": None,
            "last_uds_success_at": None,
            "last_uds_service": None,
            "last_uds_identifier": None,
            "last_nrc": None,
            "last_error": None,
        }

    def _update_adapter_runtime_state(
        self,
        payload: dict[str, Any],
        capability_payload: dict[str, Any],
        generic_pid_seen: bool,
        uds_data_seen: bool,
        now: datetime,
    ) -> None:
        explicit_capability = self._first_present(
            payload,
            capability_payload,
            names=("capability_class",),
        )
        if explicit_capability is not None:
            self._merge_capability_class(explicit_capability, "verified")

        supports_uds = self._first_present(payload, capability_payload, names=("supports_uds",))
        if supports_uds is True:
            self._merge_capability_class("uds_read_only", "probed")
        elif supports_uds is False and generic_pid_seen:
            self._merge_capability_class("generic_pid_only", "probed")
        elif generic_pid_seen:
            self._merge_capability_class("generic_pid_only", "probed")

        if uds_data_seen:
            self._merge_capability_class("uds_read_only", "verified")

        field_aliases = {
            "adapter_kind": ("adapter_kind", "adapter_type", "adapter"),
            "transport": ("transport",),
            "device_path_or_address": ("device_path_or_address", "device_path", "device", "address"),
            "active_protocol": ("active_protocol", "protocol"),
            "addressing_mode": ("addressing_mode",),
            "request_can_id": ("request_can_id",),
            "response_can_id": ("response_can_id",),
            "functional_can_id": ("functional_can_id",),
            "last_nrc": ("last_nrc", "nrc"),
            "last_error": ("last_error", "error"),
        }

        for field_name, aliases in field_aliases.items():
            value = self._first_present(payload, capability_payload, names=aliases)
            if value is not None:
                self.adapter_capabilities[field_name] = value

        connection_state = self._first_present(payload, capability_payload, names=("connection_state",))
        if isinstance(connection_state, str) and connection_state in self.CONNECTION_STATES:
            self.adapter_capabilities["connection_state"] = connection_state

        if generic_pid_seen:
            self.adapter_capabilities["last_pid_success_at"] = now.isoformat()

        if uds_data_seen:
            self.adapter_capabilities["last_uds_success_at"] = now.isoformat()
            service = self._normalize_service(
                self._first_present(payload, capability_payload, names=("last_uds_service", "uds_service"))
            )
            identifier = self._first_present(
                payload,
                capability_payload,
                names=("last_uds_identifier", "uds_identifier"),
            )
            if not identifier and self.telemetry.did_values:
                identifier = next(iter(self.telemetry.did_values))

            if service is None:
                service = "22" if self.telemetry.did_values else "19"

            self.adapter_capabilities["last_uds_service"] = service
            if identifier is not None:
                self.adapter_capabilities["last_uds_identifier"] = self._normalize_identifier(identifier)

    def _merge_capability_class(self, capability_class: Any, source: str) -> None:
        normalized = self._normalize_capability_class(capability_class)
        if normalized == "unknown":
            return

        current = self.adapter_capabilities["capability_class"]
        if self.CAPABILITY_ORDER[normalized] >= self.CAPABILITY_ORDER[current]:
            self.adapter_capabilities["capability_class"] = normalized
            self.adapter_capabilities["capability_source"] = source

    def _transport_supports_uds(self) -> bool:
        return self.adapter_capabilities["capability_class"] == "uds_read_only"

    @classmethod
    def _normalize_capability_class(cls, capability_class: Any) -> str:
        normalized = str(capability_class or "unknown").strip().lower()
        return normalized if normalized in cls.CAPABILITY_ORDER else "unknown"

    @staticmethod
    def _normalize_service(service: Any) -> Optional[str]:
        if service is None:
            return None
        normalized = str(service).upper().removeprefix("0X")
        return normalized or None

    @staticmethod
    def _detect_transport(transport_endpoint: Any, device_path_or_address: Any) -> str:
        endpoint = str(transport_endpoint or "")
        device_path = str(device_path_or_address or "")

        if device_path.startswith("/dev/"):
            return "usb_serial"
        if endpoint.startswith("ble://"):
            return "ble"
        if endpoint.startswith("can://") or endpoint.startswith("socketcan://"):
            return "socketcan"
        if endpoint.startswith("tcp://"):
            return "tcp_bridge"
        return "unknown"

    @staticmethod
    def _first_present(primary: dict[str, Any], secondary: dict[str, Any], names: tuple[str, ...]) -> Any:
        for source in (primary, secondary):
            for name in names:
                if name in source and source[name] is not None:
                    return source[name]
        return None

    @staticmethod
    def _normalize_identifier(identifier: Any) -> str:
        return str(identifier).upper().removeprefix("0X")

    @staticmethod
    def _decode_topic(raw_topic: Any) -> str:
        if isinstance(raw_topic, bytes):
            return raw_topic.decode("utf-8", errors="ignore")
        return str(raw_topic)

    @staticmethod
    def _decode_payload(payload_source: Any) -> dict[str, Any]:
        if isinstance(payload_source, dict):
            return payload_source

        if isinstance(payload_source, bytes):
            payload_source = payload_source.decode("utf-8", errors="ignore")

        if isinstance(payload_source, str):
            try:
                decoded = json.loads(payload_source)
            except json.JSONDecodeError:
                logger.debug("Ignoring undecodable transport payload")
                return {}
            return decoded if isinstance(decoded, dict) else {}

        return {}


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    bridge = VagAudiBridge()
    await bridge.initialize()
    logger.info("VAG Audi bridge scaffold initialized in %s mode", bridge.current_state)

    try:
        while True:
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopping VAG Audi bridge scaffold")
    finally:
        await bridge.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))