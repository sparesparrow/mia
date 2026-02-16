# Error Handling and Logging

## Error Handling Strategy

The MIA system uses a comprehensive error handling approach:

### 1. Return Value Pattern
Most functions return `bool` to indicate success/failure:
```cpp
bool initialize();
bool start();
bool executeCommand(const std::string& cmd);
```

### 2. Exception Handling
Critical errors throw exceptions:
```cpp
try {
    chip = std::make_unique<gpiod::chip>("gpiochip0");
} catch (const std::exception& e) {
    std::cerr << "GPIO initialization failed: " << e.what() << std::endl;
    return false;
}
```

### 3. Graceful Degradation
Optional features fail gracefully:
- MQTT connection failure doesn't stop the server
- GPIO unavailable on non-Raspberry Pi systems
- Missing TTS/STT tools fall back to alternatives

### 4. Logging Levels
- **std::cout**: Normal operation, status messages
- **std::cerr**: Errors, warnings
- **std::cout with prefixes**: Structured logging (✓, ✗, ⚠)

## Error Codes

### GPIO Errors
- GPIO chip not found: Check `/dev/gpiochip*` exists
- Permission denied: Run with sudo or add to gpio group
- Pin already in use: Release pin before reconfiguring

### Network Errors
- Port already in use: Check with `netstat -tulpn`
- Connection refused: Service not running
- Timeout: Network or service unavailable

### MQTT Errors
- Connection failed: Check mosquitto is running
- Subscribe failed: Check broker permissions
- Publish failed: Check topic permissions

## Best Practices

1. **Always check return values**
   ```cpp
   if (!server.Start()) {
       // Handle error
   }
   ```

2. **Use try-catch for critical operations**
   ```cpp
   try {
       // Critical operation
   } catch (const std::exception& e) {
       // Log and handle
   }
   ```

3. **Provide meaningful error messages**
   ```cpp
   std::cerr << "Failed to initialize GPIO: " << e.what() << std::endl;
   ```

4. **Fail fast for critical errors**
   ```cpp
   if (!critical_operation()) {
       return false; // Don't continue
   }
   ```

5. **Continue with degraded functionality for optional features**
   ```cpp
   if (!InitializeMQTT()) {
       std::cerr << "MQTT unavailable, continuing without it" << std::endl;
       // Continue operation
   }
   ```
