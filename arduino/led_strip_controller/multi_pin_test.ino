// Multi-Pin LED Test - Tests all PWM pins automatically
// Cycles through pins: 3, 5, 6, 9, 10, 11
#include <FastLED.h>
#define NUM_LEDS 23
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];
const int PIN_LIST[] = {3, 5, 6, 9, 10, 11};
const int NUM_PINS = 6;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("=== MULTI-PIN LED TEST ===");
  Serial.println("Will test pins: 3, 5, 6, 9, 10, 11");
  Serial.println("Watch LEDs - they should light up on the correct pin!");
  Serial.println();
}

void loop() {
  for (int pin_idx = 0; pin_idx < NUM_PINS; pin_idx++) {
    int test_pin = PIN_LIST[pin_idx];
    
    Serial.print("Testing PIN ");
    Serial.print(test_pin);
    Serial.println("...");
    
    // Re-initialize FastLED with new pin
    FastLED.addLeds<LED_TYPE, test_pin, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(255);
    
    // Flash white 3 times
    for (int flash = 0; flash < 3; flash++) {
      fill_solid(leds, NUM_LEDS, CRGB::White);
      FastLED.show();
      delay(500);
      FastLED.clear();
      FastLED.show();
      delay(200);
    }
    
    // Test colors
    Serial.println("  Flashing colors...");
    fill_solid(leds, NUM_LEDS, CRGB::Red);
    FastLED.show();
    delay(1000);
    
    fill_solid(leds, NUM_LEDS, CRGB::Green);
    FastLED.show();
    delay(1000);
    
    fill_solid(leds, NUM_LEDS, CRGB::Blue);
    FastLED.show();
    delay(1000);
    
    // Clear and wait
    FastLED.clear();
    FastLED.show();
    
    Serial.println("  Done - did LEDs light up?");
    Serial.println();
    
    delay(2000); // Wait between pin tests
  }
  
  Serial.println("Cycle complete - restarting...");
  Serial.println();
  delay(1000);
}
