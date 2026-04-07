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
        self._running = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    async def initialize(self) -> bool:
        self._running = True
        if self.config["enable_passive_monitoring"]:
            self.current_state = "passive_monitoring"
        else:
            self.current_state = "ready"
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
        await self._update_base_telemetry(payload)
        if payload:
            self.current_state = "ready"

    async def _update_base_telemetry(self, payload: dict[str, Any]) -> None:
        if not payload:
            return

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
                    break

        if "dtc_codes" in payload and isinstance(payload["dtc_codes"], list):
            self.telemetry.dtc_codes = [str(code) for code in payload["dtc_codes"]]

        if "did_values" in payload and isinstance(payload["did_values"], dict):
            self.telemetry.did_values.update(payload["did_values"])

        self.telemetry.timestamp = datetime.now(timezone.utc)

    async def _refresh_readonly_identifiers(self) -> None:
        if not self.config["enable_uds_polling"]:
            return
        await self.read_data_identifiers(self.config["default_identifiers"])

    async def read_data_identifiers(self, identifiers: list[str]) -> dict[str, Any]:
        normalized_identifiers = [self._normalize_identifier(identifier) for identifier in identifiers]

        if not self.config["enable_uds_polling"]:
            return {
                "status": "disabled",
                "message": "UDS polling is disabled for the VAG Audi bridge.",
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
        if not self.config["enable_uds_polling"]:
            return {
                "status": "disabled",
                "message": "UDS polling is disabled for the VAG Audi bridge.",
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
                "last_topic": self.last_topic,
                "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            },
            "telemetry": self.telemetry.to_dict(),
            "diagnostics": {
                "dtc_codes": list(self.telemetry.dtc_codes),
                "did_values": dict(self.telemetry.did_values),
            },
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
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }

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