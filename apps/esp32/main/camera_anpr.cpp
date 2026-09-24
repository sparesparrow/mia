/*
 * MIA ESP32 ANPR Camera Firmware
 * Captures images from OV2640 camera and sends to backend API
 * 
 * Hardware:
 * - ESP32-CAM with OV2640 camera
 * - WiFi for backend communication
 * - GPIO for camera flash (optional)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ===== CAMERA PINS =====
// ESP32-S3 camera board variants define these in pins_arduino.h.
// Fall back to the common AI Thinker ESP32-CAM pin map when they are absent.
#ifndef PWDN_GPIO_NUM
#define PWDN_GPIO_NUM     32
#endif
#ifndef RESET_GPIO_NUM
#define RESET_GPIO_NUM    -1
#endif
#ifndef XCLK_GPIO_NUM
#define XCLK_GPIO_NUM      0
#endif
#ifndef SIOD_GPIO_NUM
#define SIOD_GPIO_NUM     26
#endif
#ifndef SIOC_GPIO_NUM
#define SIOC_GPIO_NUM     27
#endif
#ifndef Y9_GPIO_NUM
#define Y9_GPIO_NUM       35
#endif
#ifndef Y8_GPIO_NUM
#define Y8_GPIO_NUM       34
#endif
#ifndef Y7_GPIO_NUM
#define Y7_GPIO_NUM       39
#endif
#ifndef Y6_GPIO_NUM
#define Y6_GPIO_NUM       36
#endif
#ifndef Y5_GPIO_NUM
#define Y5_GPIO_NUM       21
#endif
#ifndef Y4_GPIO_NUM
#define Y4_GPIO_NUM       19
#endif
#ifndef Y3_GPIO_NUM
#define Y3_GPIO_NUM       18
#endif
#ifndef Y2_GPIO_NUM
#define Y2_GPIO_NUM        5
#endif
#ifndef VSYNC_GPIO_NUM
#define VSYNC_GPIO_NUM    25
#endif
#ifndef HREF_GPIO_NUM
#define HREF_GPIO_NUM     23
#endif
#ifndef PCLK_GPIO_NUM
#define PCLK_GPIO_NUM     22
#endif
#ifndef FLASH_GPIO_NUM
#define FLASH_GPIO_NUM     4
#endif

// ===== NETWORK CONFIGURATION =====
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* BACKEND_URL = "http://YOUR_BACKEND:8000";

// ===== CAMERA SETTINGS =====
#define JPEG_QUALITY 85
#define MAX_FRAME_SIZE FRAMESIZE_VGA  // 640x480
#define CAMERA_CLOCK_SPEED 20000000   // 20 MHz

// ===== GLOBALS =====
bool camera_ready = false;
unsigned long last_capture_time = 0;
const unsigned long CAPTURE_INTERVAL = 5000;  // 5 seconds
WebServer server(80);

// Function declarations
void init_camera();
void init_wifi();
void init_control_server();
void capture_and_send();
void send_image_to_backend(uint8_t* buf, size_t len);
void handle_command(const String& command);
String build_status_json();

bool continuous_capture = false;

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n=== MIA ESP32 ANPR Camera ===");
  
  // Initialize camera
  init_camera();
  
  // Initialize WiFi
  init_wifi();

  if (WiFi.status() == WL_CONNECTED) {
    init_control_server();
  }
  
  Serial.println("Setup complete!");
}

// ===== MAIN LOOP =====
void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    server.handleClient();
  }

  // Check for serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    handle_command(cmd);
  }
  
  // Periodic capture (if enabled)
  if (continuous_capture && millis() - last_capture_time >= CAPTURE_INTERVAL) {
    if (camera_ready) {
      capture_and_send();
      last_capture_time = millis();
    }
  }
  
  delay(100);
}

// ===== HTTP CONTROL SERVER =====
void init_control_server() {
  server.on("/status", HTTP_GET, []() {
    server.send(200, "application/json", build_status_json());
  });

  server.on("/capture", HTTP_ANY, []() {
    capture_and_send();
    DynamicJsonDocument doc(256);
    doc["status"] = "success";
    doc["message"] = "capture triggered";
    doc["camera_ready"] = camera_ready;
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
  });

  server.on("/start", HTTP_ANY, []() {
    continuous_capture = true;
    last_capture_time = millis();
    server.send(200, "application/json", "{\"status\":\"success\",\"continuous_capture\":true}");
  });

  server.on("/stop", HTTP_ANY, []() {
    continuous_capture = false;
    server.send(200, "application/json", "{\"status\":\"success\",\"continuous_capture\":false}");
  });

  server.begin();
  Serial.println("HTTP control server started on port 80");
}

// ===== CAMERA INITIALIZATION =====
void init_camera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = CAMERA_CLOCK_SPEED;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = psramFound() ? MAX_FRAME_SIZE : FRAMESIZE_QVGA;
  config.jpeg_quality = JPEG_QUALITY;
  config.fb_count = psramFound() ? 2 : 1;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    camera_ready = false;
    return;
  }

  // Adjust camera settings
  sensor_t* s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_brightness(s, 0);      // 0
    s->set_contrast(s, 0);        // 0
    s->set_saturation(s, 0);      // 0
    s->set_sharpness(s, 2);       // 0-2
    s->set_denoise(s, 2);         // 0-2
    s->set_quality(s, JPEG_QUALITY);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec_value(s, 300);     // 0-1200
    s->set_aec2(s, 1);            // 0 or 1
    s->set_agc_gain(s, 0);        // 0-30
    s->set_gainceiling(s, GAINCEILING_2X);
    s->set_bpc(s, 1);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_hmirror(s, 0);
    s->set_vflip(s, 0);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
  }

  camera_ready = true;
  Serial.println("Camera initialized successfully");
}

// ===== WIFI INITIALIZATION =====
void init_wifi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

// ===== CAPTURE AND SEND IMAGE =====
void capture_and_send() {
  if (!camera_ready) {
    Serial.println("Camera not ready!");
    return;
  }
  
  // Turn on flash if available
  if (FLASH_GPIO_NUM >= 0) {
    pinMode(FLASH_GPIO_NUM, OUTPUT);
    digitalWrite(FLASH_GPIO_NUM, HIGH);
  }
  delay(100);
  
  // Capture frame
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    if (FLASH_GPIO_NUM >= 0) {
      digitalWrite(FLASH_GPIO_NUM, LOW);
    }
    return;
  }
  
  // Turn off flash
  if (FLASH_GPIO_NUM >= 0) {
    digitalWrite(FLASH_GPIO_NUM, LOW);
  }
  
  Serial.printf("Captured frame: %dx%d, size=%u bytes\n", 
                fb->width, fb->height, fb->len);
  
  // Send to backend
  send_image_to_backend(fb->buf, fb->len);
  
  // Return frame buffer
  esp_camera_fb_return(fb);
}

// ===== SEND IMAGE TO BACKEND =====
void send_image_to_backend(uint8_t* buf, size_t len) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }
  
  HTTPClient http;
  String url = String(BACKEND_URL) + "/anpr/process";
  
  // Prepare multipart form data
  String boundary = "----MIAWebKitFormBoundary";
  String content_type = "multipart/form-data; boundary=" + boundary;
  
  // Build multipart body
  String body = "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"file\"; filename=\"anpr_capture.jpg\"\r\n";
  body += "Content-Type: image/jpeg\r\n\r\n";
  
  String footer = "\r\n--" + boundary + "\r\n";
  footer += "Content-Disposition: form-data; name=\"auto_check_edalnice\"\r\n\r\n";
  footer += "true\r\n";
  footer += "--" + boundary + "--\r\n";
  
  // Calculate total size
  size_t total_size = body.length() + len + footer.length();
  uint8_t* payload = (uint8_t*)malloc(total_size);
  if (!payload) {
    Serial.println("Failed to allocate HTTP payload buffer");
    return;
  }

  memcpy(payload, body.c_str(), body.length());
  memcpy(payload + body.length(), buf, len);
  memcpy(payload + body.length() + len, footer.c_str(), footer.length());
  
  http.begin(url);
  http.addHeader("Content-Type", content_type);
  http.addHeader("Content-Length", String(total_size));
  
  // Send request
  int response_code = http.POST(payload, total_size);
  free(payload);
  
  if (response_code > 0) {
    if (response_code == HTTP_CODE_OK || response_code == HTTP_CODE_CREATED) {
      String response = http.getString();
      Serial.println("Image sent successfully!");
      Serial.println("Response: " + response.substring(0, 200));
    } else {
      Serial.printf("Server responded with code: %d\n", response_code);
    }
  } else {
    Serial.printf("HTTP request failed: %s\n", http.errorToString(response_code).c_str());
  }
  
  http.end();
}

// ===== COMMAND HANDLER =====
void handle_command(const String& cmd) {
  if (cmd == "capture") {
    Serial.println("Capture command received");
    capture_and_send();
  }
  else if (cmd == "start") {
    Serial.println("Continuous capture enabled");
    continuous_capture = true;
    last_capture_time = millis();
  }
  else if (cmd == "stop") {
    Serial.println("Continuous capture disabled");
    continuous_capture = false;
  }
  else if (cmd == "status") {
    Serial.println(build_status_json());
  }
  else if (cmd == "reboot") {
    Serial.println("Rebooting...");
    delay(1000);
    ESP.restart();
  }
  else {
    Serial.println("Unknown command: " + cmd);
  }
}

String build_status_json() {
  DynamicJsonDocument doc(256);
  doc["camera_ready"] = camera_ready;
  doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["ip_address"] = WiFi.localIP().toString();
  doc["continuous_capture"] = continuous_capture;
  doc["uptime_ms"] = millis();

  String response;
  serializeJson(doc, response);
  return response;
}
