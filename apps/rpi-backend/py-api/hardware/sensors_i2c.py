"""
I2C Sensor Drivers
Implementation of I2C-based sensor drivers for temperature, humidity, pressure sensors.

This module provides drivers for common I2C sensors:
- BME280: Temperature, humidity, pressure
- SHT30: Temperature, humidity
- BMP280: Temperature, pressure
- ADS1115: Analog-to-digital converter
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .sensors import SensorDriver, SensorReading, SensorType

logger = logging.getLogger(__name__)


class I2CError(Exception):
    """I2C communication error."""
    pass


class I2CInterface:
    """
    I2C communication interface for Raspberry Pi.

    Provides low-level I2C read/write operations using the Linux I2C device interface.
    """

    def __init__(self, bus: int = 1):
        """
        Initialize I2C interface.

        Args:
            bus: I2C bus number (default 1 for Raspberry Pi)
        """
        self.bus = bus
        self.device_path = f"/dev/i2c-{bus}"
        self._fd = None

    def open(self):
        """Open I2C bus."""
        try:
            import smbus2
            self._bus = smbus2.SMBus(self.bus)
            logger.debug(f"Opened I2C bus {self.bus}")
        except ImportError:
            raise I2CError("smbus2 library not available. Install with: pip install smbus2")
        except Exception as e:
            raise I2CError(f"Failed to open I2C bus {self.bus}: {e}")

    def close(self):
        """Close I2C bus."""
        if hasattr(self, '_bus') and self._bus:
            self._bus.close()
            self._bus = None

    def write_byte(self, address: int, data: int):
        """Write a single byte."""
        self._bus.write_byte(address, data)

    def read_byte(self, address: int) -> int:
        """Read a single byte."""
        return self._bus.read_byte(address)

    def write_byte_data(self, address: int, register: int, data: int):
        """Write a byte to a register."""
        self._bus.write_byte_data(address, register, data)

    def read_byte_data(self, address: int, register: int) -> int:
        """Read a byte from a register."""
        return self._bus.read_byte_data(address, register)

    def write_word_data(self, address: int, register: int, data: int):
        """Write a word (16-bit) to a register."""
        self._bus.write_word_data(address, register, data)

    def read_word_data(self, address: int, register: int) -> int:
        """Read a word (16-bit) from a register."""
        return self._bus.read_word_data(address, register)

    def write_i2c_block_data(self, address: int, register: int, data: List[int]):
        """Write a block of data."""
        self._bus.write_i2c_block_data(address, register, data)

    def read_i2c_block_data(self, address: int, register: int, length: int) -> List[int]:
        """Read a block of data."""
        return self._bus.read_i2c_block_data(address, register, length)


class BME280Sensor(SensorDriver):
    """
    Bosch BME280 Environmental Sensor.

    Measures temperature, humidity, and atmospheric pressure.

    I2C Address: 0x76 or 0x77 (default 0x76)
    """

    # BME280 Registers
    REG_CHIP_ID = 0xD0
    REG_RESET = 0xE0
    REG_CTRL_HUM = 0xF2
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_PRESS_MSB = 0xF7
    REG_TEMP_MSB = 0xFA
    REG_HUM_MSB = 0xFD

    # Calibration registers
    REG_CALIB00 = 0x88
    REG_CALIB26 = 0xA1

    def __init__(self, sensor_id: str, i2c_address: int = 0x76, i2c_bus: int = 1):
        super().__init__(sensor_id, SensorType.TEMPERATURE)  # Primary sensor type
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.i2c = I2CInterface(i2c_bus)

        # Calibration data
        self.calib_data = {}

        # Secondary sensor IDs for humidity and pressure
        self.humidity_id = f"{sensor_id}_humidity"
        self.pressure_id = f"{sensor_id}_pressure"

    async def initialize(self) -> bool:
        """Initialize BME280 sensor."""
        try:
            self.i2c.open()

            # Check chip ID
            chip_id = self.i2c.read_byte_data(self.i2c_address, self.REG_CHIP_ID)
            if chip_id != 0x60:  # BME280 chip ID
                logger.error(f"Invalid chip ID: 0x{chip_id:02X} (expected 0x60)")
                return False

            # Read calibration data
            self._read_calibration_data()

            # Configure sensor
            # Humidity oversampling x1
            self.i2c.write_byte_data(self.i2c_address, self.REG_CTRL_HUM, 0x01)

            # Temperature/Pressure oversampling x1, Normal mode
            self.i2c.write_byte_data(self.i2c_address, self.REG_CTRL_MEAS, 0x27)

            # Standby 1000ms, filter off
            self.i2c.write_byte_data(self.i2c_address, self.REG_CONFIG, 0xA0)

            # Wait for initial measurement
            await asyncio.sleep(0.1)

            logger.info(f"BME280 sensor {self.sensor_id} initialized on I2C 0x{self.i2c_address:02X}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to initialize BME280 sensor: {e}")
            return False

    async def read(self) -> Optional[SensorReading]:
        """Read temperature, humidity, and pressure from BME280."""
        try:
            # Read raw sensor data
            raw_temp, raw_press, raw_hum = self._read_raw_data()

            # Convert using calibration data
            temperature = self._compensate_temperature(raw_temp)
            pressure = self._compensate_pressure(raw_press)
            humidity = self._compensate_humidity(raw_hum)

            # Return temperature reading (primary sensor)
            # In practice, you'd return all three readings
            reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=self.sensor_type,
                value=round(temperature, 2),
                unit="°C",
                timestamp=time.time(),
                metadata={
                    "sensor": "BME280",
                    "i2c_address": f"0x{self.i2c_address:02X}",
                    "humidity": round(humidity, 1),
                    "pressure": round(pressure, 1)
                }
            )

            self.last_reading = reading
            self.last_error = None
            return reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading BME280 sensor: {e}")
            return None

    def _read_calibration_data(self):
        """Read calibration data from sensor."""
        # Read temperature and pressure calibration (24 bytes)
        calib_t_p = self.i2c.read_i2c_block_data(self.i2c_address, self.REG_CALIB00, 24)

        # Read humidity calibration (7 bytes starting at 0xA1)
        calib_h1 = self.i2c.read_byte_data(self.i2c_address, self.REG_CALIB26)
        calib_h2 = self.i2c.read_word_data(self.i2c_address, 0xE1)  # Signed
        calib_h3 = self.i2c.read_byte_data(self.i2c_address, 0xE3)
        calib_h4 = (self.i2c.read_byte_data(self.i2c_address, 0xE4) << 4) | (self.i2c.read_byte_data(self.i2c_address, 0xE5) & 0x0F)
        calib_h5 = ((self.i2c.read_byte_data(self.i2c_address, 0xE5) >> 4) & 0x0F) | (self.i2c.read_byte_data(self.i2c_address, 0xE6) << 4)
        calib_h6 = self.i2c.read_byte_data(self.i2c_address, 0xE7)

        # Store calibration data
        self.calib_data = {
            'T1': (calib_t_p[1] << 8) | calib_t_p[0],
            'T2': self._twos_complement((calib_t_p[3] << 8) | calib_t_p[2]),
            'T3': self._twos_complement((calib_t_p[5] << 8) | calib_t_p[4]),
            'P1': (calib_t_p[7] << 8) | calib_t_p[6],
            'P2': self._twos_complement((calib_t_p[9] << 8) | calib_t_p[8]),
            'P3': self._twos_complement((calib_t_p[11] << 8) | calib_t_p[10]),
            'P4': self._twos_complement((calib_t_p[13] << 8) | calib_t_p[12]),
            'P5': self._twos_complement((calib_t_p[15] << 8) | calib_t_p[14]),
            'P6': self._twos_complement((calib_t_p[17] << 8) | calib_t_p[16]),
            'P7': self._twos_complement((calib_t_p[19] << 8) | calib_t_p[18]),
            'P8': self._twos_complement((calib_t_p[21] << 8) | calib_t_p[20]),
            'P9': self._twos_complement((calib_t_p[23] << 8) | calib_t_p[22]),
            'H1': calib_h1,
            'H2': self._twos_complement(calib_h2),
            'H3': calib_h3,
            'H4': self._twos_complement(calib_h4),
            'H5': self._twos_complement(calib_h5),
            'H6': calib_h6
        }

    def _read_raw_data(self) -> Tuple[int, int, int]:
        """Read raw temperature, pressure, and humidity data."""
        # Read pressure (3 bytes)
        press_msb = self.i2c.read_byte_data(self.i2c_address, self.REG_PRESS_MSB)
        press_lsb = self.i2c.read_byte_data(self.i2c_address, self.REG_PRESS_MSB + 1)
        press_xlsb = self.i2c.read_byte_data(self.i2c_address, self.REG_PRESS_MSB + 2)
        raw_press = (press_msb << 12) | (press_lsb << 4) | (press_xlsb >> 4)

        # Read temperature (3 bytes)
        temp_msb = self.i2c.read_byte_data(self.i2c_address, self.REG_TEMP_MSB)
        temp_lsb = self.i2c.read_byte_data(self.i2c_address, self.REG_TEMP_MSB + 1)
        temp_xlsb = self.i2c.read_byte_data(self.i2c_address, self.REG_TEMP_MSB + 2)
        raw_temp = (temp_msb << 12) | (temp_lsb << 4) | (temp_xlsb >> 4)

        # Read humidity (2 bytes)
        hum_msb = self.i2c.read_byte_data(self.i2c_address, self.REG_HUM_MSB)
        hum_lsb = self.i2c.read_byte_data(self.i2c_address, self.REG_HUM_MSB + 1)
        raw_hum = (hum_msb << 8) | hum_lsb

        return raw_temp, raw_press, raw_hum

    def _compensate_temperature(self, raw_temp: int) -> float:
        """Compensate raw temperature reading."""
        var1 = (((raw_temp >> 3) - (self.calib_data['T1'] << 1)) * self.calib_data['T2']) >> 11
        var2 = (((((raw_temp >> 4) - self.calib_data['T1']) * ((raw_temp >> 4) - self.calib_data['T1'])) >> 12) * self.calib_data['T3']) >> 14
        self.t_fine = var1 + var2
        return (self.t_fine * 5 + 128) >> 8

    def _compensate_pressure(self, raw_press: int) -> float:
        """Compensate raw pressure reading."""
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.calib_data['P6']
        var2 = var2 + ((var1 * self.calib_data['P5']) << 17)
        var2 = var2 + (self.calib_data['P4'] << 35)
        var1 = ((var1 * var1 * self.calib_data['P3']) >> 8) + ((var1 * self.calib_data['P2']) << 12)
        var1 = (((1 << 47) + var1) * self.calib_data['P1']) >> 33

        if var1 == 0:
            return 0  # Avoid division by zero

        p = 1048576 - raw_press
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.calib_data['P9'] * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.calib_data['P8'] * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self.calib_data['P7'] << 4)

        return p / 256.0 / 100.0  # Convert to hPa

    def _compensate_humidity(self, raw_hum: int) -> float:
        """Compensate raw humidity reading."""
        h = self.t_fine - 76800
        h = ((((raw_hum << 14) - (self.calib_data['H4'] << 20) - (self.calib_data['H5'] * h)) + 16384) >> 15) * \
            (((((((h * self.calib_data['H6']) >> 10) * (((h * self.calib_data['H3']) >> 11) + 32768)) >> 10) + 2097152) * \
              self.calib_data['H2'] + 8192) >> 14)
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.calib_data['H1']) >> 4)
        h = max(0, min(419430400, h))

        return h >> 12

    @staticmethod
    def _twos_complement(value: int) -> int:
        """Convert unsigned 16-bit value to signed."""
        if value > 32767:
            return value - 65536
        return value

    async def shutdown(self) -> None:
        """Shutdown BME280 sensor."""
        self.i2c.close()
        logger.info(f"BME280 sensor {self.sensor_id} shutdown")


class SHT30Sensor(SensorDriver):
    """
    Sensirion SHT30 Temperature and Humidity Sensor.

    High-accuracy temperature and humidity sensor.

    I2C Address: 0x44 or 0x45
    """

    # SHT30 Commands
    CMD_MEASURE_HIGHREP = [0x24, 0x00]  # High repeatability measurement
    CMD_SOFT_RESET = [0x30, 0xA2]       # Soft reset

    def __init__(self, sensor_id: str, i2c_address: int = 0x44, i2c_bus: int = 1):
        super().__init__(sensor_id, SensorType.TEMPERATURE)
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.i2c = I2CInterface(i2c_bus)
        self.humidity_id = f"{sensor_id}_humidity"

    async def initialize(self) -> bool:
        """Initialize SHT30 sensor."""
        try:
            self.i2c.open()

            # Soft reset
            self.i2c.write_i2c_block_data(self.i2c_address, self.CMD_SOFT_RESET[0], [self.CMD_SOFT_RESET[1]])

            # Wait for reset
            await asyncio.sleep(0.01)

            logger.info(f"SHT30 sensor {self.sensor_id} initialized on I2C 0x{self.i2c_address:02X}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to initialize SHT30 sensor: {e}")
            return False

    async def read(self) -> Optional[SensorReading]:
        """Read temperature and humidity from SHT30."""
        try:
            # Start measurement
            self.i2c.write_i2c_block_data(self.i2c_address, self.CMD_MEASURE_HIGHREP[0], [self.CMD_MEASURE_HIGHREP[1]])

            # Wait for measurement (high repeatability)
            await asyncio.sleep(0.015)

            # Read 6 bytes of data
            data = self.i2c.read_i2c_block_data(self.i2c_address, 0, 6)

            # Parse temperature (first 2 bytes + CRC)
            temp_raw = (data[0] << 8) | data[1]
            temperature = -45 + (175 * temp_raw / 65535.0)

            # Parse humidity (next 2 bytes + CRC)
            hum_raw = (data[3] << 8) | data[4]
            humidity = 100 * hum_raw / 65535.0

            # Return temperature reading (primary sensor)
            reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=self.sensor_type,
                value=round(temperature, 2),
                unit="°C",
                timestamp=time.time(),
                metadata={
                    "sensor": "SHT30",
                    "i2c_address": f"0x{self.i2c_address:02X}",
                    "humidity": round(humidity, 1)
                }
            )

            self.last_reading = reading
            self.last_error = None
            return reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading SHT30 sensor: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown SHT30 sensor."""
        self.i2c.close()
        logger.info(f"SHT30 sensor {self.sensor_id} shutdown")


class ADS1115Sensor(SensorDriver):
    """
    Texas Instruments ADS1115 16-bit ADC.

    4-channel analog-to-digital converter with programmable gain.

    I2C Address: 0x48 (default), 0x49, 0x4A, 0x4B
    """

    # ADS1115 Registers
    REG_CONVERSION = 0x00
    REG_CONFIG = 0x01
    REG_LO_THRESH = 0x02
    REG_HI_THRESH = 0x03

    # Config register bits
    OS_START = 0x8000  # Operation status/Start conversion
    MUX_AIN0 = 0x4000  # Input multiplexer AIN0
    MUX_AIN1 = 0x5000  # Input multiplexer AIN1
    MUX_AIN2 = 0x6000  # Input multiplexer AIN2
    MUX_AIN3 = 0x7000  # Input multiplexer AIN3
    PGA_6_144V = 0x0000  # ±6.144V range
    PGA_4_096V = 0x0200  # ±4.096V range
    PGA_2_048V = 0x0400  # ±2.048V range
    PGA_1_024V = 0x0600  # ±1.024V range
    MODE_CONTINUOUS = 0x0000  # Continuous conversion
    MODE_SINGLE = 0x0100  # Single-shot conversion
    DR_8SPS = 0x0000  # 8 samples per second
    DR_16SPS = 0x0020  # 16 samples per second
    DR_32SPS = 0x0040  # 32 samples per second
    DR_64SPS = 0x0060  # 64 samples per second
    DR_128SPS = 0x0080  # 128 samples per second
    DR_250SPS = 0x00A0  # 250 samples per second
    DR_475SPS = 0x00C0  # 475 samples per second
    DR_860SPS = 0x00E0  # 860 samples per second
    COMP_MODE_TRAD = 0x0000  # Traditional comparator
    COMP_POL_LOW = 0x0000  # Active low polarity
    COMP_LAT_NONLAT = 0x0000  # Non-latching comparator
    COMP_QUE_DISABLE = 0x0003  # Disable comparator

    def __init__(self, sensor_id: str, channel: int = 0, i2c_address: int = 0x48, i2c_bus: int = 1,
                 gain: str = "4.096V", sps: str = "128"):
        super().__init__(sensor_id, SensorType.GAS)  # Analog input
        self.channel = channel
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.i2c = I2CInterface(i2c_bus)

        # Configure gain
        self.gain_config = {
            "6.144V": self.PGA_6_144V,
            "4.096V": self.PGA_4_096V,
            "2.048V": self.PGA_2_048V,
            "1.024V": self.PGA_1_024V
        }.get(gain, self.PGA_4_096V)

        # Configure data rate
        self.sps_config = {
            "8": self.DR_8SPS,
            "16": self.DR_16SPS,
            "32": self.DR_32SPS,
            "64": self.DR_64SPS,
            "128": self.DR_128SPS,
            "250": self.DR_250SPS,
            "475": self.DR_475SPS,
            "860": self.DR_860SPS
        }.get(sps, self.DR_128SPS)

        # Configure channel
        self.channel_config = {
            0: self.MUX_AIN0,
            1: self.MUX_AIN1,
            2: self.MUX_AIN2,
            3: self.MUX_AIN3
        }.get(channel, self.MUX_AIN0)

    async def initialize(self) -> bool:
        """Initialize ADS1115 ADC."""
        try:
            self.i2c.open()

            # Test communication by reading config register
            config = self.i2c.read_word_data(self.i2c_address, self.REG_CONFIG)
            logger.info(f"ADS1115 config register: 0x{config:04X}")

            logger.info(f"ADS1115 sensor {self.sensor_id} initialized on I2C 0x{self.i2c_address:02X}, channel {self.channel}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to initialize ADS1115 sensor: {e}")
            return False

    async def read(self) -> Optional[SensorReading]:
        """Read analog value from ADS1115."""
        try:
            # Configure for single-shot conversion
            config = (self.OS_START | self.channel_config | self.gain_config |
                     self.MODE_SINGLE | self.sps_config | self.COMP_MODE_TRAD |
                     self.COMP_POL_LOW | self.COMP_LAT_NONLAT | self.COMP_QUE_DISABLE)

            # Write config register
            self.i2c.write_word_data(self.i2c_address, self.REG_CONFIG, config)

            # Wait for conversion (based on SPS)
            sps_value = int(list(self.sps_config.__dict__.keys())[list(self.sps_config.__dict__.values()).index(self.sps_config)])
            delay = 1.0 / sps_value + 0.001  # Add small buffer
            await asyncio.sleep(delay)

            # Read conversion result
            raw_value = self.i2c.read_word_data(self.i2c_address, self.REG_CONVERSION)

            # Convert to voltage (assuming 4.096V range)
            voltage_range = 4.096
            voltage = (raw_value / 32767.0) * voltage_range

            reading = SensorReading(
                sensor_id=self.sensor_id,
                sensor_type=self.sensor_type,
                value=round(voltage, 4),
                unit="V",
                timestamp=time.time(),
                metadata={
                    "sensor": "ADS1115",
                    "i2c_address": f"0x{self.i2c_address:02X}",
                    "channel": self.channel,
                    "raw_value": raw_value,
                    "gain": f"±{voltage_range}V"
                }
            )

            self.last_reading = reading
            self.last_error = None
            return reading

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading ADS1115 sensor: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown ADS1115 sensor."""
        self.i2c.close()
        logger.info(f"ADS1115 sensor {self.sensor_id} shutdown")


# Sensor factory for easy instantiation
def create_i2c_sensor(sensor_type: str, sensor_id: str, **kwargs) -> Optional[SensorDriver]:
    """
    Factory function to create I2C sensor instances.

    Args:
        sensor_type: Type of sensor ("bme280", "sht30", "ads1115")
        sensor_id: Unique sensor identifier
        **kwargs: Sensor-specific parameters

    Returns:
        Sensor instance or None if type not supported
    """
    sensor_type = sensor_type.lower()

    if sensor_type == "bme280":
        return BME280Sensor(sensor_id, **kwargs)
    elif sensor_type == "sht30":
        return SHT30Sensor(sensor_id, **kwargs)
    elif sensor_type == "ads1115":
        return ADS1115Sensor(sensor_id, **kwargs)
    else:
        logger.error(f"Unsupported I2C sensor type: {sensor_type}")
        return None