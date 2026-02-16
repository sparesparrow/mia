#include "test_gpio_control.h"
#include "../HardwareControlServer.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <stdexcept>

void testGpioControl() {
    using namespace WebGrab;
    
    // Test GPIO initialization (only works on Raspberry Pi with proper permissions)
    HardwareControlServer server(9998, "localhost", 1883);
    
    // Try to start the server
    // This will fail gracefully if not on Raspberry Pi or without permissions
    bool started = server.Start();
    
    if (started) {
        std::cout << "  GPIO server started successfully" << std::endl;
        
        // Test GPIO control via TCP connection (simulate)
        // Note: HandleGPIOControl is private, so we test via TCP
        // For a real test, we would connect via TCP socket
        
        // Give it a moment to initialize
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        
        std::cout << "  GPIO server is running (connect via TCP port 9998 to test)" << std::endl;
        
        server.Stop();
    } else {
        std::cout << "  GPIO server failed to start (expected if not on Raspberry Pi)" << std::endl;
        throw std::runtime_error("GPIO not available - this is expected if not running on Raspberry Pi");
    }
}
