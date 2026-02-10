#include <Arduino.h>

// Shared State
volatile int g_rpm = 0;
volatile int g_speed = 0;

void setup() {
    Serial.begin(38400); // OBD Scanner connection (Bluetooth/USB)
    Serial2.begin(115200); // Upstream Link to RPi/Ubuntu (Control Plane)
}

void loop() {
    // THREAD 1: FAST PROTOCOL HANDLING (The "ELM327")
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\r');
        cmd.trim();
        
        if (cmd == "ATZ") { 
            Serial.println("ELM327 v1.5"); 
        }
        else if (cmd == "010C") { // Request RPM
            // 1/4 RPM per bit. Value = RPM * 4
            int val = g_rpm * 4;
            byte A = (val >> 8) & 0xFF;
            byte B = val & 0xFF;
            char buf[10];
            sprintf(buf, "41 0C %02X %02X", A, B);
            Serial.println(buf);
        }
        else if (cmd == "010D") { // Request Speed
            char buf[10];
            sprintf(buf, "41 0D %02X", g_speed);
            Serial.println(buf);
        }
        else {
            Serial.println("?"); // Standard ELM error
        }
        Serial.print(">"); // Prompt
    }

    // THREAD 2: STATE UPDATES FROM PYTHON
    if (Serial2.available()) {
        // Format: "S:800:25" (Speed:RPM:Temp)
        String update = Serial2.readStringUntil('\n');
        // ... fast parse logic to update g_rpm/g_speed ...
    }
}
