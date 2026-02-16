"""
Automotive DTC Manager - LogManager Extension for ISO 14229-1 DTC Management

This module provides ISO 14229-1 compliant DTC (Diagnostic Trouble Code)
management with status byte handling, freeze frame capture, and AUTOSAR DEM
integration for automotive diagnostic systems.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, Flag
import json

logger = logging.getLogger(__name__)


class DTCStatus(Flag):
    """ISO 14229-1 DTC status bits"""
    TEST_FAILED = 0x01          # Bit 0: Test failed
    TEST_FAILED_THIS_OP_CYCLE = 0x02  # Bit 1: Test failed this operation cycle
    PENDING_DTC = 0x04          # Bit 2: Pending DTC
    CONFIRMED_DTC = 0x08        # Bit 3: Confirmed DTC
    TEST_NOT_COMPLETED_SINCE_LAST_CLEAR = 0x10  # Bit 4: Test not completed since last clear
    TEST_FAILED_SINCE_LAST_CLEAR = 0x20         # Bit 5: Test failed since last clear
    TEST_NOT_COMPLETED_THIS_OP_CYCLE = 0x40     # Bit 6: Test not completed this operation cycle
    WARNING_INDICATOR_REQUESTED = 0x80          # Bit 7: Warning indicator requested


class DTCFormat(Enum):
    """DTC format types"""
    SAE_J2012 = "SAE_J2012"     # P0xxx, C0xxx, B0xxx, U0xxx
    ISO_14229_1 = "ISO_14229_1" # 4-byte hex format


@dataclass
class FreezeFrameData:
    """Freeze frame data captured at fault confirmation"""
    timestamp: int              # Unix timestamp when freeze frame was captured
    ignition_cycles: int        # Number of ignition cycles since last clear
    distance_km: float         # Distance traveled since last clear (km)
    engine_runtime_sec: int    # Engine runtime since last clear (seconds)

    # Vehicle data at time of fault
    vehicle_speed: Optional[float] = None      # km/h
    engine_rpm: Optional[float] = None         # RPM
    engine_load: Optional[float] = None        # %
    coolant_temp: Optional[float] = None       # °C
    fuel_level: Optional[float] = None         # %
    battery_voltage: Optional[float] = None    # V

    # Additional custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'ignition_cycles': self.ignition_cycles,
            'distance_km': self.distance_km,
            'engine_runtime_sec': self.engine_runtime_sec,
            'vehicle_speed': self.vehicle_speed,
            'engine_rpm': self.engine_rpm,
            'engine_load': self.engine_load,
            'coolant_temp': self.coolant_temp,
            'fuel_level': self.fuel_level,
            'battery_voltage': self.battery_voltage,
            'custom_data': self.custom_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FreezeFrameData':
        """Create from dictionary"""
        return cls(
            timestamp=data['timestamp'],
            ignition_cycles=data['ignition_cycles'],
            distance_km=data['distance_km'],
            engine_runtime_sec=data['engine_runtime_sec'],
            vehicle_speed=data.get('vehicle_speed'),
            engine_rpm=data.get('engine_rpm'),
            engine_load=data.get('engine_load'),
            coolant_temp=data.get('coolant_temp'),
            fuel_level=data.get('fuel_level'),
            battery_voltage=data.get('battery_voltage'),
            custom_data=data.get('custom_data', {})
        )


@dataclass
class ExtendedDataRecord:
    """Extended data record mapped to LogEntry pattern"""
    record_number: int          # Record number (0x01-0xEF)
    data: bytes                 # Raw data bytes
    description: str           # Human-readable description
    timestamp: int             # When this record was created

    def to_log_entry(self) -> Dict[str, Any]:
        """Convert to LogEntry compatible format"""
        return {
            'level': 'ERROR',
            'message': f'Extended Data Record {self.record_number}: {self.description}',
            'timestamp': self.timestamp,
            'data': self.data.hex(),
            'record_number': self.record_number
        }


@dataclass
class DTCEntry:
    """Complete DTC entry with status and associated data"""
    dtc_code: int               # DTC code (e.g., 0x012345)
    dtc_format: DTCFormat      # DTC format type
    status: DTCStatus          # Current status byte
    occurrence_count: int      # Number of times this DTC has occurred
    pending_count: int         # Number of pending occurrences
    confirmed_count: int       # Number of confirmed occurrences
    healed_count: int          # Number of times this DTC was healed
    last_failed_time: Optional[int] = None     # Last time test failed
    last_confirmed_time: Optional[int] = None  # Last time DTC was confirmed
    first_failed_time: Optional[int] = None    # First time this DTC failed

    # Associated data
    freeze_frames: List[FreezeFrameData] = field(default_factory=list)
    extended_records: List[ExtendedDataRecord] = field(default_factory=list)

    # Healing configuration
    healing_threshold: int = 3  # Number of good cycles needed to heal
    healing_counter: int = 0    # Current healing counter

    def __post_init__(self):
        if self.first_failed_time is None:
            self.first_failed_time = int(time.time())

    def get_status_byte(self) -> int:
        """Get DTC status as byte value"""
        return self.status.value

    def set_status_bit(self, bit: DTCStatus) -> None:
        """Set a specific status bit"""
        self.status |= bit

    def clear_status_bit(self, bit: DTCStatus) -> None:
        """Clear a specific status bit"""
        self.status &= ~bit

    def is_active(self) -> bool:
        """Check if DTC is currently active (TestFailed bit set)"""
        return DTCStatus.TEST_FAILED in self.status

    def is_pending(self) -> bool:
        """Check if DTC is pending confirmation"""
        return DTCStatus.PENDING_DTC in self.status

    def is_confirmed(self) -> bool:
        """Check if DTC is confirmed"""
        return DTCStatus.CONFIRMED_DTC in self.status

    def needs_freeze_frame(self) -> bool:
        """Check if freeze frame should be captured"""
        # Capture freeze frame when DTC becomes confirmed
        return (DTCStatus.CONFIRMED_DTC in self.status and
                len(self.freeze_frames) == 0) or \
               (DTCStatus.CONFIRMED_DTC in self.status and
                self.last_confirmed_time != self.freeze_frames[-1].timestamp)

    def can_heal(self) -> bool:
        """Check if DTC can be healed"""
        return self.healing_counter >= self.healing_threshold

    def increment_healing_counter(self) -> None:
        """Increment healing counter"""
        self.healing_counter = min(self.healing_counter + 1, self.healing_threshold)

    def reset_healing_counter(self) -> None:
        """Reset healing counter (on failure)"""
        self.healing_counter = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'dtc_code': self.dtc_code,
            'dtc_format': self.dtc_format.value,
            'status': self.status.value,
            'occurrence_count': self.occurrence_count,
            'pending_count': self.pending_count,
            'confirmed_count': self.confirmed_count,
            'healed_count': self.healed_count,
            'last_failed_time': self.last_failed_time,
            'last_confirmed_time': self.last_confirmed_time,
            'first_failed_time': self.first_failed_time,
            'healing_threshold': self.healing_threshold,
            'healing_counter': self.healing_counter,
            'freeze_frames': [ff.to_dict() for ff in self.freeze_frames],
            'extended_records': [{
                'record_number': rec.record_number,
                'data': rec.data.hex(),
                'description': rec.description,
                'timestamp': rec.timestamp
            } for rec in self.extended_records]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DTCEntry':
        """Create from dictionary"""
        entry = cls(
            dtc_code=data['dtc_code'],
            dtc_format=DTCFormat(data['dtc_format']),
            status=DTCStatus(data['status']),
            occurrence_count=data['occurrence_count'],
            pending_count=data['pending_count'],
            confirmed_count=data['confirmed_count'],
            healed_count=data['healed_count'],
            last_failed_time=data.get('last_failed_time'),
            last_confirmed_time=data.get('last_confirmed_time'),
            first_failed_time=data.get('first_failed_time'),
            healing_threshold=data.get('healing_threshold', 3),
            healing_counter=data.get('healing_counter', 0)
        )

        # Restore freeze frames
        for ff_data in data.get('freeze_frames', []):
            entry.freeze_frames.append(FreezeFrameData.from_dict(ff_data))

        # Restore extended records
        for rec_data in data.get('extended_records', []):
            entry.extended_records.append(ExtendedDataRecord(
                record_number=rec_data['record_number'],
                data=bytes.fromhex(rec_data['data']),
                description=rec_data['description'],
                timestamp=rec_data['timestamp']
            ))

        return entry


class DTCManager:
    """
    Automotive DTC Manager - LogManager extension for ISO 14229-1 compliance

    Provides DTC status management, freeze frame capture, extended data records,
    and AUTOSAR DEM integration for automotive diagnostic systems.
    """

    def __init__(self, max_dtcs: int = 100, persistence_file: Optional[str] = None):
        """
        Initialize DTC Manager

        Args:
            max_dtcs: Maximum number of DTCs to store
            persistence_file: File path for DTC persistence across ignition cycles
        """
        self.max_dtcs = max_dtcs
        self.persistence_file = persistence_file

        # DTC storage
        self._dtc_table: Dict[int, DTCEntry] = {}
        self._lock = threading.RLock()

        # Vehicle state for freeze frames
        self._vehicle_data_callbacks: Dict[str, Callable[[], Any]] = {}

        # AUTOSAR DEM integration callbacks
        self._dem_report_callback: Optional[Callable[[int, str], None]] = None
        self._dem_clear_callback: Optional[Callable[[int], None]] = None

        # Statistics
        self._total_failures = 0
        self._total_confirmations = 0
        self._total_clear_operations = 0
        self._total_healings = 0

        # Load persisted DTCs if available
        if persistence_file:
            self._load_persisted_dtcs()

    def register_vehicle_data_callback(self, data_type: str, callback: Callable[[], Any]) -> None:
        """
        Register callback for vehicle data capture in freeze frames

        Args:
            data_type: Type of vehicle data (e.g., 'vehicle_speed', 'engine_rpm')
            callback: Function that returns current value
        """
        self._vehicle_data_callbacks[data_type] = callback

    def set_dem_callbacks(self,
                         report_callback: Optional[Callable[[int, str], None]] = None,
                         clear_callback: Optional[Callable[[int], None]] = None) -> None:
        """
        Set AUTOSAR DEM integration callbacks

        Args:
            report_callback: Callback for reporting faults to DEM (dtc_code, event_name)
            clear_callback: Callback for clearing faults from DEM (dtc_code)
        """
        self._dem_report_callback = report_callback
        self._dem_clear_callback = clear_callback

    def report_failure(self, dtc_code: int, dtc_format: DTCFormat = DTCFormat.ISO_14229_1,
                      extended_data: Optional[bytes] = None) -> bool:
        """
        Report a diagnostic test failure

        Args:
            dtc_code: DTC code that failed
            dtc_format: DTC format type
            extended_data: Optional extended data to store

        Returns:
            True if failure was recorded
        """
        with self._lock:
            current_time = int(time.time())

            # Get or create DTC entry
            if dtc_code not in self._dtc_table:
                if len(self._dtc_table) >= self.max_dtcs:
                    logger.warning("Maximum DTC count reached, cannot add new DTC")
                    return False

                self._dtc_table[dtc_code] = DTCEntry(
                    dtc_code=dtc_code,
                    dtc_format=dtc_format,
                    status=DTCStatus(0),
                    occurrence_count=0,
                    pending_count=0,
                    confirmed_count=0,
                    healed_count=0
                )

            dtc_entry = self._dtc_table[dtc_code]

            # Update failure statistics
            dtc_entry.occurrence_count += 1
            dtc_entry.last_failed_time = current_time
            self._total_failures += 1

            # Set status bits
            dtc_entry.set_status_bit(DTCStatus.TEST_FAILED)
            dtc_entry.set_status_bit(DTCStatus.TEST_FAILED_THIS_OP_CYCLE)
            dtc_entry.set_status_bit(DTCStatus.TEST_FAILED_SINCE_LAST_CLEAR)

            # Reset healing counter on failure
            dtc_entry.reset_healing_counter()

            # Set pending status if not already confirmed
            if not dtc_entry.is_confirmed():
                dtc_entry.set_status_bit(DTCStatus.PENDING_DTC)
                dtc_entry.pending_count += 1

            # Add extended data record if provided
            if extended_data:
                record = ExtendedDataRecord(
                    record_number=len(dtc_entry.extended_records) + 1,
                    data=extended_data,
                    description=f"Failure data - occurrence {dtc_entry.occurrence_count}",
                    timestamp=current_time
                )
                dtc_entry.extended_records.append(record)

            # Report to AUTOSAR DEM
            if self._dem_report_callback:
                try:
                    self._dem_report_callback(dtc_code, f"DTC_{dtc_code:06X}_FAILURE")
                except Exception as e:
                    logger.error(f"DEM report callback error: {e}")

            logger.info(f"DTC failure reported: {dtc_code:06X}")
            return True

    def confirm_dtc(self, dtc_code: int, capture_freeze_frame: bool = True) -> bool:
        """
        Confirm a pending DTC (move from pending to confirmed status)

        Args:
            dtc_code: DTC code to confirm
            capture_freeze_frame: Whether to capture freeze frame data

        Returns:
            True if DTC was confirmed
        """
        with self._lock:
            if dtc_code not in self._dtc_table:
                return False

            dtc_entry = self._dtc_table[dtc_code]
            current_time = int(time.time())

            # Only confirm if currently pending
            if not dtc_entry.is_pending():
                return False

            # Clear pending, set confirmed
            dtc_entry.clear_status_bit(DTCStatus.PENDING_DTC)
            dtc_entry.set_status_bit(DTCStatus.CONFIRMED_DTC)
            dtc_entry.confirmed_count += 1
            dtc_entry.last_confirmed_time = current_time
            self._total_confirmations += 1

            # Capture freeze frame if needed
            if capture_freeze_frame and dtc_entry.needs_freeze_frame():
                freeze_frame = self._capture_freeze_frame()
                dtc_entry.freeze_frames.append(freeze_frame)

            # Report to AUTOSAR DEM
            if self._dem_report_callback:
                try:
                    self._dem_report_callback(dtc_code, f"DTC_{dtc_code:06X}_CONFIRMED")
                except Exception as e:
                    logger.error(f"DEM report callback error: {e}")

            logger.info(f"DTC confirmed: {dtc_code:06X}")
            return True

    def _capture_freeze_frame(self) -> FreezeFrameData:
        """Capture current vehicle state for freeze frame"""
        # Get current vehicle data
        vehicle_data = {}
        for data_type, callback in self._vehicle_data_callbacks.items():
            try:
                vehicle_data[data_type] = callback()
            except Exception as e:
                logger.warning(f"Failed to capture {data_type}: {e}")
                vehicle_data[data_type] = None

        # Create freeze frame with available data
        return FreezeFrameData(
            timestamp=int(time.time()),
            ignition_cycles=self._get_vehicle_data('ignition_cycles', 0),
            distance_km=self._get_vehicle_data('odometer_km', 0.0),
            engine_runtime_sec=self._get_vehicle_data('engine_runtime_sec', 0),
            vehicle_speed=vehicle_data.get('vehicle_speed'),
            engine_rpm=vehicle_data.get('engine_rpm'),
            engine_load=vehicle_data.get('engine_load'),
            coolant_temp=vehicle_data.get('coolant_temp'),
            fuel_level=vehicle_data.get('fuel_level'),
            battery_voltage=vehicle_data.get('battery_voltage')
        )

    def _get_vehicle_data(self, key: str, default: Any) -> Any:
        """Helper to get vehicle data with default"""
        callback = self._vehicle_data_callbacks.get(key)
        if callback:
            try:
                return callback()
            except Exception:
                pass
        return default

    def clear_dtc(self, dtc_code: int) -> bool:
        """
        Clear a DTC (reset status and optionally delete entry)

        Args:
            dtc_code: DTC code to clear

        Returns:
            True if DTC was cleared
        """
        with self._lock:
            if dtc_code not in self._dtc_table:
                return False

            dtc_entry = self._dtc_table[dtc_code]

            # Clear status bits
            dtc_entry.status = DTCStatus(0)

            # Clear AUTOSAR DEM
            if self._dem_clear_callback:
                try:
                    self._dem_clear_callback(dtc_code)
                except Exception as e:
                    logger.error(f"DEM clear callback error: {e}")

            # Optionally remove entry if no history needed
            # For now, keep entries for historical tracking

            self._total_clear_operations += 1
            logger.info(f"DTC cleared: {dtc_code:06X}")
            return True

    def heal_dtc(self, dtc_code: int) -> bool:
        """
        Attempt to heal a DTC (increment healing counter)

        Args:
            dtc_code: DTC code to heal

        Returns:
            True if DTC was healed (cleared)
        """
        with self._lock:
            if dtc_code not in self._dtc_table:
                return False

            dtc_entry = self._dtc_table[dtc_code]

            # Increment healing counter
            dtc_entry.increment_healing_counter()

            # Check if healing threshold reached
            if dtc_entry.can_heal():
                # Clear the DTC
                dtc_entry.clear_status_bit(DTCStatus.TEST_FAILED)
                dtc_entry.clear_status_bit(DTCStatus.CONFIRMED_DTC)
                dtc_entry.healed_count += 1
                self._total_healings += 1

                logger.info(f"DTC healed: {dtc_code:06X}")
                return True

            return False

    def get_dtc_status(self, dtc_code: int) -> Optional[DTCEntry]:
        """Get DTC entry for given code"""
        with self._lock:
            return self._dtc_table.get(dtc_code)

    def get_all_dtcs(self, status_filter: Optional[DTCStatus] = None) -> List[DTCEntry]:
        """Get all DTCs, optionally filtered by status"""
        with self._lock:
            dtcs = list(self._dtc_table.values())

            if status_filter:
                dtcs = [dtc for dtc in dtcs if status_filter in dtc.status]

            return dtcs

    def get_dtc_snapshot(self) -> List[Tuple[int, int]]:
        """Get DTC snapshot (code, status_byte) for UDS responses"""
        with self._lock:
            return [(dtc.dtc_code, dtc.get_status_byte()) for dtc in self._dtc_table.values()]

    def persist_dtcs(self) -> None:
        """Persist DTCs to storage for ignition cycle persistence"""
        if not self.persistence_file:
            return

        try:
            with self._lock:
                data = {
                    'timestamp': int(time.time()),
                    'dtcs': [dtc.to_dict() for dtc in self._dtc_table.values()],
                    'statistics': self.get_statistics()
                }

            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"DTCs persisted to {self.persistence_file}")

        except Exception as e:
            logger.error(f"Failed to persist DTCs: {e}")

    def _load_persisted_dtcs(self) -> None:
        """Load persisted DTCs from storage"""
        if not self.persistence_file:
            return

        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)

            dtcs_data = data.get('dtcs', [])
            for dtc_data in dtcs_data:
                dtc_entry = DTCEntry.from_dict(dtc_data)
                self._dtc_table[dtc_entry.dtc_code] = dtc_entry

            logger.info(f"Loaded {len(dtcs_data)} persisted DTCs")

        except FileNotFoundError:
            logger.info("No persisted DTCs found")
        except Exception as e:
            logger.error(f"Failed to load persisted DTCs: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get DTC manager statistics"""
        with self._lock:
            active_dtcs = sum(1 for dtc in self._dtc_table.values() if dtc.is_active())
            pending_dtcs = sum(1 for dtc in self._dtc_table.values() if dtc.is_pending())
            confirmed_dtcs = sum(1 for dtc in self._dtc_table.values() if dtc.is_confirmed())

            return {
                'total_dtcs': len(self._dtc_table),
                'active_dtcs': active_dtcs,
                'pending_dtcs': pending_dtcs,
                'confirmed_dtcs': confirmed_dtcs,
                'total_failures': self._total_failures,
                'total_confirmations': self._total_confirmations,
                'total_clear_operations': self._total_clear_operations,
                'total_healings': self._total_healings
            }

    def get_log_entries(self) -> List[Dict[str, Any]]:
        """Get DTC events as LogEntry compatible format"""
        entries = []

        with self._lock:
            for dtc in self._dtc_table.values():
                # Add DTC status entry
                entries.append({
                    'level': 'ERROR' if dtc.is_confirmed() else 'WARNING',
                    'message': f'DTC {dtc.dtc_code:06X}: Status={dtc.status.value:02X}, '
                              f'Occurrences={dtc.occurrence_count}',
                    'timestamp': dtc.last_failed_time or dtc.first_failed_time,
                    'dtc_code': dtc.dtc_code,
                    'status': dtc.get_status_byte()
                })

                # Add extended data records
                for record in dtc.extended_records:
                    entries.append(record.to_log_entry())

        # Sort by timestamp
        entries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return entries