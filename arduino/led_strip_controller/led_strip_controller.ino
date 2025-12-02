/*
 * Arduino Uno LED Strip Controller
 * Controls 23 programmable 5V LED diodes (WS2812B/NeoPixel compatible)
 * Communicates with Raspberry Pi via USB Serial (ttyUSB0)
 * 
 * Hardware Requirements:
 * - Arduino Uno
 * - WS2812B LED strip (23 LEDs)
 * - USB connection to Raspberry Pi
 * - LED strip connected to pin 6 (PWM capable)
 * 
 * Communication Protocol:
 * - JSON commands via Serial
 * - Commands: set_color, set_brightness, animation, clear, status
 * - Responses: JSON status messages
 */

#include <ArduinoJson.h>
#include <FastLED.h>

// LED Configuration
#define LED_PIN 6           // PWM pin for LED data
#define NUM_LEDS 23         // Number of LEDs in strip
#define LED_TYPE WS2812B    // LED chip type
#define COLOR_ORDER GRB     // Color order (may vary by manufacturer)

// Create LED array
CRGB leds[NUM_LEDS];

// Current state
int brightness = 128;      // 0-255
CRGB current_color = CRGB::White;
String current_animation = "none";
unsigned long last_update = 0;
int animation_step = 0;

// JSON buffer size
const size_t JSON_BUFFER_SIZE = 512;

void setup() {
  // Initialize Serial communication
  Serial.begin(115200);
  while (!Serial) {
    delay(10); // Wait for serial port to connect
  }
  
  // Initialize FastLED
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(brightness);
  FastLED.clear();
  FastLED.show();
  
  // Send ready message
  sendStatus("ready", "LED strip controller initialized");
  
  delay(100);
}

void loop() {
  // Check for incoming serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() > 0) {
      processCommand(command);
    }
  }
  
  // Update animations
  updateAnimation();
  
  // Small delay to prevent overwhelming the serial buffer
  delay(10);
}

void processCommand(String jsonCommand) {
  StaticJsonDocument<JSON_BUFFER_SIZE> doc;
  DeserializationError error = deserializeJson(doc, jsonCommand);
  
  if (error) {
    sendError("parse_error", "Failed to parse JSON: " + String(error.c_str()));
    return;
  }
  
  String cmd = doc["command"] | "";
  
  if (cmd == "set_color") {
    handleSetColor(doc);
  }
  else if (cmd == "set_brightness") {
    handleSetBrightness(doc);
  }
  else if (cmd == "set_led") {
    handleSetLed(doc);
  }
  else if (cmd == "animation") {
    handleAnimation(doc);
  }
  else if (cmd == "clear") {
    handleClear();
  }
  else if (cmd == "status") {
    handleStatus();
  }
  else if (cmd == "rainbow") {
    handleRainbow(doc);
  }
  else if (cmd == "chase") {
    handleChase(doc);
  }
  else {
    sendError("unknown_command", "Unknown command: " + cmd);
  }
}

void handleSetColor(JsonDocument& doc) {
  int r = doc["r"] | 255;
  int g = doc["g"] | 255;
  int b = doc["b"] | 255;
  
  current_color = CRGB(r, g, b);
  current_animation = "none";
  
  // Set all LEDs to the same color
  fill_solid(leds, NUM_LEDS, current_color);
  FastLED.show();
  
  sendStatus("color_set", "Color set to RGB(" + String(r) + "," + String(g) + "," + String(b) + ")");
}

void handleSetBrightness(JsonDocument& doc) {
  int new_brightness = doc["brightness"] | brightness;
  new_brightness = constrain(new_brightness, 0, 255);
  
  brightness = new_brightness;
  FastLED.setBrightness(brightness);
  FastLED.show();
  
  sendStatus("brightness_set", "Brightness set to " + String(brightness));
}

void handleSetLed(JsonDocument& doc) {
  int led_index = doc["led"] | -1;
  int r = doc["r"] | 0;
  int g = doc["g"] | 0;
  int b = doc["b"] | 0;
  
  if (led_index < 0 || led_index >= NUM_LEDS) {
    sendError("invalid_led", "LED index must be 0-" + String(NUM_LEDS - 1));
    return;
  }
  
  leds[led_index] = CRGB(r, g, b);
  FastLED.show();
  
  sendStatus("led_set", "LED " + String(led_index) + " set to RGB(" + String(r) + "," + String(g) + "," + String(b) + ")");
}

void handleAnimation(JsonDocument& doc) {
  String anim = doc["animation"] | "none";
  current_animation = anim;
  animation_step = 0;
  
  if (anim == "blink") {
    int speed = doc["speed"] | 500;
    // Store speed in animation_step temporarily
    animation_step = speed;
  }
  else if (anim == "fade") {
    int speed = doc["speed"] | 50;
    animation_step = speed;
  }
  
  sendStatus("animation_set", "Animation set to: " + anim);
}

void handleClear() {
  FastLED.clear();
  FastLED.show();
  current_animation = "none";
  sendStatus("cleared", "All LEDs cleared");
}

void handleStatus() {
  StaticJsonDocument<JSON_BUFFER_SIZE> response;
  response["status"] = "ok";
  response["brightness"] = brightness;
  response["current_color"]["r"] = current_color.r;
  response["current_color"]["g"] = current_color.g;
  response["current_color"]["b"] = current_color.b;
  response["animation"] = current_animation;
  response["num_leds"] = NUM_LEDS;
  
  serializeJson(response, Serial);
  Serial.println();
}

void handleRainbow(JsonDocument& doc) {
  int speed = doc["speed"] | 10;
  current_animation = "rainbow";
  animation_step = speed;
  sendStatus("rainbow_started", "Rainbow animation started");
}

void handleChase(JsonDocument& doc) {
  int r = doc["r"] | 255;
  int g = doc["g"] | 0;
  int b = doc["b"] | 0;
  int speed = doc["speed"] | 100;
  
  current_color = CRGB(r, g, b);
  current_animation = "chase";
  animation_step = speed;
  sendStatus("chase_started", "Chase animation started");
}

void updateAnimation() {
  unsigned long current_time = millis();
  
  if (current_animation == "blink") {
    int speed = animation_step;
    if (current_time - last_update >= speed) {
      static bool state = false;
      state = !state;
      if (state) {
        fill_solid(leds, NUM_LEDS, current_color);
      } else {
        FastLED.clear();
      }
      FastLED.show();
      last_update = current_time;
    }
  }
  else if (current_animation == "fade") {
    int speed = animation_step;
    if (current_time - last_update >= speed) {
      static int fade_value = 0;
      static bool fade_direction = true;
      
      if (fade_direction) {
        fade_value += 5;
        if (fade_value >= 255) {
          fade_value = 255;
          fade_direction = false;
        }
      } else {
        fade_value -= 5;
        if (fade_value <= 0) {
          fade_value = 0;
          fade_direction = true;
        }
      }
      
      CRGB fade_color = current_color;
      fade_color.fadeToBlackBy(255 - fade_value);
      fill_solid(leds, NUM_LEDS, fade_color);
      FastLED.show();
      last_update = current_time;
    }
  }
  else if (current_animation == "rainbow") {
    int speed = animation_step;
    if (current_time - last_update >= speed) {
      static uint8_t hue = 0;
      for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CHSV((hue + i * 10) % 255, 255, 255);
      }
      FastLED.show();
      hue++;
      last_update = current_time;
    }
  }
  else if (current_animation == "chase") {
    int speed = animation_step;
    if (current_time - last_update >= speed) {
      static int pos = 0;
      FastLED.clear();
      leds[pos] = current_color;
      leds[(pos + 1) % NUM_LEDS] = current_color;
      leds[(pos + 2) % NUM_LEDS] = current_color;
      FastLED.show();
      pos = (pos + 1) % NUM_LEDS;
      last_update = current_time;
    }
  }
}

void sendStatus(String status, String message) {
  StaticJsonDocument<JSON_BUFFER_SIZE> response;
  response["status"] = status;
  response["message"] = message;
  response["brightness"] = brightness;
  response["current_color"]["r"] = current_color.r;
  response["current_color"]["g"] = current_color.g;
  response["current_color"]["b"] = current_color.b;
  
  serializeJson(response, Serial);
  Serial.println();
}

void sendError(String error_type, String message) {
  StaticJsonDocument<JSON_BUFFER_SIZE> response;
  response["status"] = "error";
  response["error_type"] = error_type;
  response["message"] = message;
  
  serializeJson(response, Serial);
  Serial.println();
}
