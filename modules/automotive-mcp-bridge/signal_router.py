"""
Automotive Signal Router - MergedMapping Adaptation for CAN Signal Routing

This module provides CAN signal routing tables with sparse indexing,
ECU-specific message ID clustering, and DID lookup capabilities for
automotive diagnostic and communication systems.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Generic, TypeVar
from dataclasses import dataclass
from enum import Enum
import struct

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MessageType(Enum):
    """CAN message types for routing classification"""
    DIAGNOSTIC = "diagnostic"
    SENSOR_DATA = "sensor_data"
    CONTROL_COMMAND = "control_command"
    STATUS_INFO = "status_info"
    BROADCAST = "broadcast"


class AddressingMode(Enum):
    """CAN addressing modes"""
    PHYSICAL = "physical"      # Specific ECU addressing
    FUNCTIONAL = "functional"  # Broadcast to multiple ECUs


@dataclass
class CANSignalMetadata:
    """Metadata for CAN signal routing"""
    message_id: int
    signal_name: str
    message_type: MessageType
    addressing_mode: AddressingMode
    ecu_source: Optional[int] = None
    ecu_targets: Set[int] = None
    data_length: int = 8  # Standard CAN frame
    priority: int = 0     # 0 = highest priority
    cycle_time_ms: int = 100  # Default 100ms cycle

    def __post_init__(self):
        if self.ecu_targets is None:
            self.ecu_targets = set()

    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message"""
        return self.addressing_mode == AddressingMode.FUNCTIONAL or not self.ecu_targets


class ECURange:
    """ECU address range definition for clustering"""

    def __init__(self, start_id: int, end_id: int, ecu_name: str):
        self.start_id = start_id
        self.end_id = end_id
        self.ecu_name = ecu_name
        self.range_size = end_id - start_id + 1

    def contains(self, ecu_id: int) -> bool:
        """Check if ECU ID is within this range"""
        return self.start_id <= ecu_id <= self.end_id

    def get_ecu_name(self) -> str:
        """Get ECU name for this range"""
        return self.ecu_name


class DIDCategory(Enum):
    """DID (Data Identifier) categories per ISO 14229"""
    IDENTIFICATION = "identification"    # 0xF1xx range
    OEM_SPECIFIC = "oem_specific"        # 0xFDxx range
    VEHICLE_MANUFACTURER = "vehicle_mnf" # 0xFExx range
    SYSTEM_SUPPLIER = "system_supplier"  # 0xFFxx range
    DIAGNOSTIC_DATA = "diagnostic_data"  # Other ranges


@dataclass
class DIDEntry:
    """DID lookup table entry"""
    did: int
    name: str
    category: DIDCategory
    data_length: int
    description: str
    read_handler: Optional[Callable[[], bytes]] = None
    write_handler: Optional[Callable[[bytes], bool]] = None
    scaling: Optional[Dict[str, Any]] = None

    def is_readable(self) -> bool:
        """Check if DID supports read operations"""
        return self.read_handler is not None

    def is_writable(self) -> bool:
        """Check if DID supports write operations"""
        return self.write_handler is not None

    def get_category_range(self) -> Tuple[int, int]:
        """Get the DID range for this category"""
        if self.category == DIDCategory.IDENTIFICATION:
            return (0xF100, 0xF1FF)
        elif self.category == DIDCategory.OEM_SPECIFIC:
            return (0xFD00, 0xFDFF)
        elif self.category == DIDCategory.VEHICLE_MANUFACTURER:
            return (0xFE00, 0xFEFF)
        elif self.category == DIDCategory.SYSTEM_SUPPLIER:
            return (0xFF00, 0xFFFF)
        else:
            return (0x0000, 0xFFFF)  # Diagnostic data can be anywhere


class SignalRouter:
    """
    Automotive Signal Router - MergedMapping adaptation for CAN signal routing

    Provides O(1) CAN message routing with:
    - ECU address clustering (0x100-0x1FF = ECU1)
    - DID category organization (0xF1xx identification, 0xFDxx OEM)
    - Sparse indexing for ECU-specific message IDs
    - Const-correct read-only access patterns
    - Range validation for safety-critical lookups
    """

    def __init__(self, max_message_id: int = 0x7FF):  # 11-bit CAN ID
        """
        Initialize Signal Router

        Args:
            max_message_id: Maximum CAN message ID (default 0x7FF for 11-bit)
        """
        self.max_message_id = max_message_id

        # ECU clustering ranges (configurable)
        self._ecu_ranges: List[ECURange] = []
        self._setup_default_ecu_ranges()

        # Sparse routing table: message_id -> signal metadata
        self._routing_table: Dict[int, CANSignalMetadata] = {}

        # DID lookup tables organized by category
        self._did_tables: Dict[DIDCategory, Dict[int, DIDEntry]] = {
            category: {} for category in DIDCategory
        }

        # Reverse lookups for fast access
        self._ecu_to_messages: Dict[int, Set[int]] = {}  # ECU ID -> message IDs
        self._name_to_did: Dict[str, int] = {}           # DID name -> DID value

        # Statistics and monitoring
        self._route_lookups = 0
        self._route_hits = 0
        self._did_lookups = 0
        self._did_hits = 0
        self._invalid_accesses = 0

    def _setup_default_ecu_ranges(self) -> None:
        """Set up default ECU address ranges"""
        # Standard automotive ECU clustering
        self._ecu_ranges = [
            ECURange(0x100, 0x1FF, "ECU1_Engine"),
            ECURange(0x200, 0x2FF, "ECU2_Transmission"),
            ECURange(0x300, 0x3FF, "ECU3_Brake"),
            ECURange(0x400, 0x4FF, "ECU4_Steering"),
            ECURange(0x500, 0x5FF, "ECU5_Suspension"),
            ECURange(0x600, 0x6FF, "ECU6_BodyControl"),
            ECURange(0x700, 0x7FF, "ECU7_Infotainment"),
        ]

    def add_ecu_range(self, start_id: int, end_id: int, ecu_name: str) -> None:
        """Add custom ECU address range"""
        self._ecu_ranges.append(ECURange(start_id, end_id, ecu_name))

    def register_signal(self, metadata: CANSignalMetadata) -> bool:
        """
        Register a CAN signal in the routing table

        Args:
            metadata: Signal metadata to register

        Returns:
            True if registered successfully, False if message ID invalid/out of range
        """
        if not self._is_valid_message_id(metadata.message_id):
            logger.error(f"Invalid message ID: {metadata.message_id:#x}")
            return False

        if metadata.message_id in self._routing_table:
            logger.warning(f"Message ID {metadata.message_id:#x} already registered, overwriting")

        self._routing_table[metadata.message_id] = metadata

        # Update reverse lookups
        if metadata.ecu_source is not None:
            if metadata.ecu_source not in self._ecu_to_messages:
                self._ecu_to_messages[metadata.ecu_source] = set()
            self._ecu_to_messages[metadata.ecu_source].add(metadata.message_id)

        # Add target ECUs to reverse lookup
        for ecu_id in metadata.ecu_targets:
            if ecu_id not in self._ecu_to_messages:
                self._ecu_to_messages[ecu_id] = set()
            self._ecu_to_messages[ecu_id].add(metadata.message_id)

        logger.debug(f"Registered signal: {metadata.signal_name} (ID: {metadata.message_id:#x})")
        return True

    def route_message(self, message_id: int, data: bytes = b'') -> Optional[CANSignalMetadata]:
        """
        Route CAN message to appropriate signal handler - O(1) lookup

        Args:
            message_id: CAN message ID
            data: Optional message data for validation

        Returns:
            Signal metadata if route found, None otherwise
        """
        self._route_lookups += 1

        # Range validation for safety
        if not self._is_valid_message_id(message_id):
            self._invalid_accesses += 1
            logger.warning(f"Invalid message ID access: {message_id:#x}")
            return None

        # O(1) lookup in sparse table
        metadata = self._routing_table.get(message_id)

        if metadata is not None:
            self._route_hits += 1

            # Additional validation for safety-critical data
            if len(data) != metadata.data_length:
                logger.warning(f"Data length mismatch for {metadata.signal_name}: "
                             f"expected {metadata.data_length}, got {len(data)}")
                return None

        return metadata

    def get_ecu_name(self, ecu_id: int) -> str:
        """Get ECU name for given ECU ID"""
        for ecu_range in self._ecu_ranges:
            if ecu_range.contains(ecu_id):
                return ecu_range.ecu_name
        return f"ECU_{ecu_id:#x}"

    def get_messages_for_ecu(self, ecu_id: int) -> Set[int]:
        """Get all message IDs associated with an ECU"""
        return self._ecu_to_messages.get(ecu_id, set())

    def register_did(self, entry: DIDEntry) -> bool:
        """
        Register a DID in the lookup table

        Args:
            entry: DID entry to register

        Returns:
            True if registered successfully
        """
        # Validate DID range for category
        range_start, range_end = entry.get_category_range()
        if not (range_start <= entry.did <= range_end):
            logger.error(f"DID {entry.did:#x} not in valid range for category {entry.category.value}")
            return False

        self._did_tables[entry.category][entry.did] = entry
        self._name_to_did[entry.name] = entry.did

        logger.debug(f"Registered DID: {entry.name} ({entry.did:#x})")
        return True

    def lookup_did(self, did: int) -> Optional[DIDEntry]:
        """
        Lookup DID entry by value

        Args:
            did: DID value to lookup

        Returns:
            DID entry if found, None otherwise
        """
        self._did_lookups += 1

        # Search through all categories (could be optimized with category detection)
        for category_table in self._did_tables.values():
            entry = category_table.get(did)
            if entry is not None:
                self._did_hits += 1
                return entry

        return None

    def lookup_did_by_name(self, name: str) -> Optional[DIDEntry]:
        """Lookup DID entry by name"""
        did = self._name_to_did.get(name)
        if did is not None:
            return self.lookup_did(did)
        return None

    def read_did(self, did: int) -> Optional[bytes]:
        """
        Read DID value using registered handler

        Args:
            did: DID to read

        Returns:
            DID data if successful, None otherwise
        """
        entry = self.lookup_did(did)
        if entry and entry.is_readable():
            try:
                return entry.read_handler()
            except Exception as e:
                logger.error(f"Error reading DID {did:#x}: {e}")
                return None
        return None

    def write_did(self, did: int, data: bytes) -> bool:
        """
        Write DID value using registered handler

        Args:
            did: DID to write
            data: Data to write

        Returns:
            True if successful, False otherwise
        """
        entry = self.lookup_did(did)
        if entry and entry.is_writable():
            try:
                return entry.write_handler(data)
            except Exception as e:
                logger.error(f"Error writing DID {did:#x}: {e}")
                return False
        return False

    def get_dids_by_category(self, category: DIDCategory) -> List[DIDEntry]:
        """Get all DIDs in a specific category"""
        return list(self._did_tables[category].values())

    def _is_valid_message_id(self, message_id: int) -> bool:
        """Validate message ID range"""
        return 0 <= message_id <= self.max_message_id

    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics for monitoring"""
        total_routes = len(self._routing_table)
        total_dids = sum(len(table) for table in self._did_tables.values())

        route_hit_rate = (self._route_hits / self._route_lookups * 100) if self._route_lookups > 0 else 0
        did_hit_rate = (self._did_hits / self._did_lookups * 100) if self._did_lookups > 0 else 0

        return {
            'total_signals': total_routes,
            'total_dids': total_dids,
            'route_lookups': self._route_lookups,
            'route_hit_rate': route_hit_rate,
            'did_lookups': self._did_lookups,
            'did_hit_rate': did_hit_rate,
            'invalid_accesses': self._invalid_accesses,
            'ecu_count': len(self._ecu_to_messages)
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters"""
        self._route_lookups = 0
        self._route_hits = 0
        self._did_lookups = 0
        self._did_hits = 0
        self._invalid_accesses = 0

    def validate_routing_table(self) -> List[str]:
        """
        Validate routing table integrity for safety compliance

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check for duplicate signal names
        signal_names = {}
        for metadata in self._routing_table.values():
            if metadata.signal_name in signal_names:
                errors.append(f"Duplicate signal name: {metadata.signal_name}")
            else:
                signal_names[metadata.signal_name] = metadata.message_id

        # Check for overlapping ECU ranges
        for i, range1 in enumerate(self._ecu_ranges):
            for j, range2 in enumerate(self._ecu_ranges):
                if i != j and self._ranges_overlap(range1, range2):
                    errors.append(f"Overlapping ECU ranges: {range1.ecu_name} and {range2.ecu_name}")

        # Check DID table integrity
        for category, table in self._did_tables.items():
            did_names = {}
            for entry in table.values():
                if entry.name in did_names:
                    errors.append(f"Duplicate DID name in {category.value}: {entry.name}")
                else:
                    did_names[entry.name] = entry.did

        return errors

    def _ranges_overlap(self, range1: ECURange, range2: ECURange) -> bool:
        """Check if two ECU ranges overlap"""
        return not (range1.end_id < range2.start_id or range2.end_id < range1.start_id)