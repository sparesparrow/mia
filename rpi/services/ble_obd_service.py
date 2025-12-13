#!/usr/bin/env python3
"""
BLE OBD Service - Raspberry Pi BLE Peripheral for OBD-II Communication
Acts as a BLE GATT server that Android app can connect to for OBD-II data

This service:
- Creates a BLE GATT server with Nordic UART Service (NUS)
- Accepts OBD-II commands from connected Android devices
- Forwards commands to OBD worker via ZeroMQ
- Returns OBD responses to Android device
"""

import sys
import os
import json
import logging
import asyncio
import signal
from typing import Optional, Dict, TYPE_CHECKING
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if TYPE_CHECKING:
    from bleak import BleakServer, BleakGATTCharacteristic, BleakGATTDescriptor
    from bleak.backends.characteristic import BleakGATTCharacteristicProperties

try:
    from bleak import BleakServer, BleakGATTCharacteristic, BleakGATTDescriptor
    from bleak.backends.characteristic import BleakGATTCharacteristicProperties
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    # Create dummy types for type hints when bleak is not available
    BleakServer = None
    BleakGATTCharacteristic = None
    BleakGATTDescriptor = None
    BleakGATTCharacteristicProperties = None
    logging.warning("Bleak library not available. Install with: pip3 install bleak")

import zmq

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Nordic UART Service UUIDs (compatible with Android BLEManager)
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Write/Command
NUS_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Notify/Response

# Device name advertised
DEVICE_NAME = "MIA OBD-II Adapter"


class BLEOBDService:
    """
    BLE GATT server that provides OBD-II interface
    """
    
    def __init__(self,
                 broker_url: str = "tcp://localhost:5555",
                 device_name: str = DEVICE_NAME):
        self.broker_url = broker_url
        self.device_name = device_name
        self.server: Optional[BleakServer] = None
        self.context = zmq.Context()
        self.broker_socket: Optional[zmq.Socket] = None
        self.running = False
        
        # Characteristic handles
        self.tx_char: Optional[BleakGATTCharacteristic] = None
        self.rx_char: Optional[BleakGATTCharacteristic] = None
        
        # Response buffer
        self.response_queue = asyncio.Queue()
        
        if not BLEAK_AVAILABLE:
            logger.error("Bleak library not available. Cannot start BLE service.")
            raise ImportError("Bleak library required. Install with: pip3 install bleak")
    
    async def start(self):
        """Start the BLE GATT server"""
        try:
            # Connect to ZeroMQ broker
            self.broker_socket = self.context.socket(zmq.DEALER)
            import uuid
            worker_id = f"ble-obd-{uuid.uuid4()}"
            self.broker_socket.setsockopt_string(zmq.IDENTITY, worker_id)
            self.broker_socket.connect(self.broker_url)
            
            logger.info(f"Connected to ZeroMQ broker at {self.broker_url}")
            
            # Register with broker
            self._register_worker()
            
            # Create BLE GATT server
            # Note: BleakServer may not be available in all versions
            # Alternative: Use bluez D-Bus API directly (see ble_advertiser.py)
            try:
                self.server = BleakServer(self.device_name)
                
                # Setup GATT characteristics
                await self._setup_gatt_characteristics()
                
                # Start advertising
                await self.server.start()
                logger.info(f"BLE GATT server started, advertising as '{self.device_name}'")
            except Exception as e:
                logger.error(f"BleakServer not available or failed: {e}")
                logger.info("Falling back to bluez D-Bus API (implemented in ble_advertiser.py)")
                # For now, we'll use the advertiser service for discovery
                # GATT server functionality may need bluez D-Bus implementation
                raise
            
            self.running = True
            
            # Start response handler
            asyncio.create_task(self._response_handler())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start BLE service: {e}")
            logger.exception(e)
            return False
    
    async def _setup_gatt_characteristics(self):
        """Setup GATT service and characteristics"""
        # Create Nordic UART Service
        service = await self.server.add_service(NUS_SERVICE_UUID)
        
        # TX Characteristic (Android writes commands here)
        self.tx_char = await service.add_characteristic(
            NUS_TX_CHAR_UUID,
            properties=BleakGATTCharacteristicProperties.write | 
                      BleakGATTCharacteristicProperties.write_without_response,
            value=None
        )
        self.tx_char.set_write_callback(self._on_command_received)
        
        # RX Characteristic (Android receives responses via notifications)
        self.rx_char = await service.add_characteristic(
            NUS_RX_CHAR_UUID,
            properties=BleakGATTCharacteristicProperties.notify |
                      BleakGATTCharacteristicProperties.read,
            value=None
        )
        
        logger.info("GATT characteristics configured")
    
    def _on_command_received(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """Handle incoming OBD command from Android device"""
        try:
            command = data.decode('utf-8').strip()
            logger.debug(f"Received OBD command: {command}")
            
            # Forward command to OBD worker via ZeroMQ
            asyncio.create_task(self._forward_command(command))
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    async def _forward_command(self, command: str):
        """Forward OBD command to OBD worker via ZeroMQ"""
        try:
            message = {
                "type": "OBD_COMMAND",
                "command": command,
                "timestamp": datetime.now().isoformat()
            }
            
            self.broker_socket.send_json(message)
            
            # Wait for response (with timeout)
            poller = zmq.Poller()
            poller.register(self.broker_socket, zmq.POLLIN)
            
            # Poll for response
            response_received = False
            timeout = 5000  # 5 seconds
            
            for _ in range(50):  # 50 * 100ms = 5 seconds
                socks = dict(poller.poll(100))
                if self.broker_socket in socks:
                    response = self.broker_socket.recv_json()
                    if response.get("type") == "OBD_RESPONSE":
                        await self._send_response(response.get("response", ""))
                        response_received = True
                        break
                
                await asyncio.sleep(0.1)
            
            if not response_received:
                logger.warning(f"No response received for command: {command}")
                await self._send_response("NO DATA")
                
        except Exception as e:
            logger.error(f"Error forwarding command: {e}")
            await self._send_response("ERROR")
    
    async def _send_response(self, response: str):
        """Send OBD response to connected Android device"""
        if not self.rx_char or not self.server:
            return
        
        try:
            # Format response like ELM327 (with > prompt)
            formatted_response = f"{response}\r>"
            data = formatted_response.encode('utf-8')
            
            # Update characteristic value and notify
            await self.server.notify(self.rx_char, data)
            logger.debug(f"Sent OBD response: {response}")
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    async def _response_handler(self):
        """Handle responses from ZeroMQ broker"""
        while self.running:
            try:
                # This would be used if we receive async responses
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in response handler: {e}")
                await asyncio.sleep(1)
    
    def _register_worker(self):
        """Register this worker with the ZeroMQ broker"""
        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "BLE_OBD",
            "capabilities": ["OBD_COMMAND", "OBD_RESPONSE"],
            "timestamp": datetime.now().isoformat()
        }
        self.broker_socket.send_json(message)
        logger.info("Registered BLE OBD worker with broker")
    
    async def stop(self):
        """Stop the BLE service"""
        self.running = False
        
        if self.server:
            await self.server.stop()
            logger.info("BLE GATT server stopped")
        
        if self.broker_socket:
            self.broker_socket.close()
        
        self.context.term()
        logger.info("BLE OBD service stopped")


async def main():
    """Main entry point"""
    service = BLEOBDService()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        if await service.start():
            logger.info("BLE OBD service running. Press Ctrl+C to stop.")
            await stop_event.wait()
        else:
            logger.error("Failed to start BLE OBD service")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.exception(e)
        sys.exit(1)
