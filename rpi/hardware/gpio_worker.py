"""
GPIO Worker - Hardware Control
Implements Phase 2.2: GPIO Control & Sensor Integration
Listens to ZeroMQ messages and controls GPIO pins
"""
import zmq
import json
import logging
import time
from typing import Dict, Optional
from datetime import datetime

# Try to import GPIO libraries
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import gpiozero
        GPIO_AVAILABLE = True
        USE_GPIOZERO = True
    except ImportError:
        GPIO_AVAILABLE = False
        USE_GPIOZERO = False
        logging.warning("No GPIO library available. Running in simulation mode.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPIOWorker:
    """
    GPIO Worker that controls Raspberry Pi GPIO pins
    Subscribes to ZeroMQ messages and executes GPIO commands
    """
    
    def __init__(self, broker_url: str = "tcp://localhost:5555"):
        self.broker_url = broker_url
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        self.pin_states: Dict[int, Dict[str, any]] = {}  # pin -> {direction, value}
        
        if GPIO_AVAILABLE:
            if USE_GPIOZERO:
                logger.info("Using gpiozero library")
            else:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                logger.info("Using RPi.GPIO library")
        else:
            logger.warning("Running in simulation mode - no actual GPIO control")
    
    def start(self):
        """Start the GPIO worker"""
        self.socket = self.context.socket(zmq.DEALER)
        # Generate unique worker ID
        import uuid
        worker_id = str(uuid.uuid4())
        self.socket.setsockopt_string(zmq.IDENTITY, worker_id)
        self.socket.connect(self.broker_url)
        
        self.running = True
        logger.info(f"GPIO worker started, connected to {self.broker_url}")
        
        # Register with broker
        self._register_worker()
        
        # Start message loop
        self._message_loop()
        
        return True
    
    def stop(self):
        """Stop the GPIO worker"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.context.term()
        
        if GPIO_AVAILABLE and not USE_GPIOZERO:
            GPIO.cleanup()
        
        logger.info("GPIO worker stopped")
    
    def _register_worker(self):
        """Register this worker with the broker"""
        message = {
            "type": "WORKER_REGISTER",
            "worker_type": "GPIO",
            "capabilities": ["GPIO_CONFIGURE", "GPIO_SET", "GPIO_GET", "GPIO_STATUS"],
            "timestamp": datetime.now().isoformat()
        }
        self.socket.send_json(message)
    
    def _message_loop(self):
        """Main message processing loop"""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        
        while self.running:
            try:
                socks = dict(poller.poll(1000))  # 1 second timeout
                
                if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                    message = self.socket.recv_json()
                    self._handle_message(message)
            except zmq.ZMQError as e:
                if self.running:
                    logger.error(f"ZMQ error: {e}")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                time.sleep(0.1)
    
    def _handle_message(self, message: Dict):
        """Handle incoming message"""
        message_type = message.get("type")
        # Correlation id for broker to route responses back to clients
        self._current_request_id: Optional[str] = message.get("request_id")

        try:
            if message_type == "GPIO_CONFIGURE":
                self._handle_configure(message)
            elif message_type == "GPIO_SET":
                self._handle_set(message)
            elif message_type == "GPIO_GET":
                self._handle_get(message)
            elif message_type == "GPIO_STATUS":
                self._handle_status(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            self._send_error(str(e))
    
    def _handle_configure(self, message: Dict):
        """Handle GPIO configure command"""
        pin = message.get("pin")
        direction = message.get("direction", "output")
        request_id = message.get("request_id")
        
        if not pin:
            self._send_error("Missing pin parameter")
            return
        
        try:
            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # gpiozero handles configuration automatically
                    pass
                else:
                    if direction == "output":
                        GPIO.setup(pin, GPIO.OUT)
                    elif direction == "input":
                        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    else:
                        raise ValueError(f"Invalid direction: {direction}")
            
            # Store pin state
            if pin not in self.pin_states:
                self.pin_states[pin] = {}
            self.pin_states[pin]["direction"] = direction
            
            response = {
                "type": "GPIO_CONFIGURE_RESPONSE",
                "pin": pin,
                "direction": direction,
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)
            logger.info(f"Configured GPIO pin {pin} as {direction}")
        except Exception as e:
            logger.error(f"Error configuring pin {pin}: {e}")
            self._send_error(f"Failed to configure pin {pin}: {e}")
    
    def _handle_set(self, message: Dict):
        """Handle GPIO set command"""
        pin = message.get("pin")
        value = message.get("value")
        request_id = message.get("request_id")
        
        if pin is None or value is None:
            self._send_error("Missing pin or value parameter")
            return
        
        try:
            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # Would need to create/update device objects
                    logger.warning("gpiozero set not fully implemented")
                else:
                    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
            
            # Update pin state
            if pin not in self.pin_states:
                self.pin_states[pin] = {"direction": "output"}
            self.pin_states[pin]["value"] = value
            
            response = {
                "type": "GPIO_SET_RESPONSE",
                "pin": pin,
                "value": value,
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)
            logger.info(f"Set GPIO pin {pin} to {value}")
        except Exception as e:
            logger.error(f"Error setting pin {pin}: {e}")
            self._send_error(f"Failed to set pin {pin}: {e}")
    
    def _handle_get(self, message: Dict):
        """Handle GPIO get command"""
        pin = message.get("pin")
        request_id = message.get("request_id")
        
        if pin is None:
            self._send_error("Missing pin parameter")
            return
        
        try:
            value = None
            if GPIO_AVAILABLE:
                if USE_GPIOZERO:
                    # Would need device object
                    logger.warning("gpiozero get not fully implemented")
                else:
                    value = bool(GPIO.input(pin))
            else:
                # Simulation mode - return stored value
                value = self.pin_states.get(pin, {}).get("value", False)
            
            response = {
                "type": "GPIO_GET_RESPONSE",
                "pin": pin,
                "value": value,
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            self.socket.send_json(response)
        except Exception as e:
            logger.error(f"Error getting pin {pin}: {e}")
            self._send_error(f"Failed to get pin {pin}: {e}")
    
    def _handle_status(self, message: Dict):
        """Handle GPIO status request"""
        request_id = message.get("request_id")
        pins = []
        for pin, state in self.pin_states.items():
            pins.append({
                "pin": pin,
                "direction": state.get("direction", "unknown"),
                "value": state.get("value", None)
            })
        
        response = {
            "type": "GPIO_STATUS_RESPONSE",
            "pins": pins,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
        self.socket.send_json(response)
    
    def _send_error(self, error: str):
        """Send error response"""
        # Try to include request id if currently processing a request
        request_id = getattr(self, "_current_request_id", None)
        response = {
            "type": "ERROR",
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
        self.socket.send_json(response)


def main():
    """Main entry point for GPIO worker"""
    worker = GPIOWorker()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down GPIO worker...")
        worker.stop()


if __name__ == "__main__":
    main()
