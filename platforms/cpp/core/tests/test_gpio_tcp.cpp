#include "../HardwareControlServer.h"
#include "../TcpSocket.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>

// Test GPIO control via TCP connection
void testGpioViaTcp() {
    using namespace WebGrab;
    
    // Start server
    HardwareControlServer server(9998, "localhost", 1883);
    if (!server.Start()) {
        std::cout << "  GPIO server failed to start" << std::endl;
        return;
    }
    
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    
    // Connect via TCP
    TcpSocket client("localhost", 9998);
    if (!client.connect()) {
        std::cout << "  Failed to connect to GPIO server" << std::endl;
        server.Stop();
        return;
    }
    
    // Send GPIO control request
    std::string request = R"({"pin": 18, "direction": "output", "value": 1})";
    if (client.send(request.c_str(), request.length())) {
        std::cout << "  Sent GPIO control request" << std::endl;
        
        // Receive response
        std::vector<uint8_t> buffer;
        if (client.receive(buffer)) {
            std::string response(buffer.begin(), buffer.end());
            std::cout << "  Received response: " << response << std::endl;
        }
    }
    
    client.disconnect();
    server.Stop();
}
