/*
 * MIA Serial Bridge Firmware for ESP32/Arduino
 * 
 * This firmware reads analog inputs (potentiometers) and sends JSON telemetry
 * to the Raspberry Pi via USB Serial for OBD-II simulation.
 * 
 * Hardware Setup:
 * - Potentiometer 1 (RPM): Connect to A0
 * - Potentiometer 2 (Speed): Connect to A1
 * 
 * Serial Protocol:
 * - Baud Rate: 115200
 * - Format: JSON lines, one per update
 * - Example: {"pot1":512, "pot2":256}
 */

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  
  // Wait for serial port to be ready (optional, for USB serial)
  #ifdef ESP32
    delay(1000);
  #endif
  
  // Configure analog pins (if needed)
  // ESP32: 12-bit ADC (0-4095)
  // Arduino Uno: 10-bit ADC (0-1023)
  
  Serial.println("MIA Serial Bridge Firmware Started");
}

void loop() {
  // Read analog inputs
  int pot1 = analogRead(A0);  // RPM Input (0-1023 or 0-4095)
  int pot2 = analogRead(A1);  // Speed Input (0-1023 or 0-4095)
  
  // Optional: Read additional sensors
  // int throttle = analogRead(A2);
  // int coolant = analogRead(A3);
  
  // Send JSON formatted line
  Serial.print("{\"pot1\":");
  Serial.print(pot1);
  Serial.print(", \"pot2\":");
  Serial.print(pot2);
  
  // Add optional fields if sensors are connected
  // Serial.print(", \"throttle\":");
  // Serial.print(throttle);
  // Serial.print(", \"coolant\":");
  // Serial.print(coolant);
  
  Serial.println("}");
  
  // Update rate: 10Hz (100ms delay)
  // Adjust for faster/slower updates
  delay(100);
}
