#include "HardwareControlServer.h"
#include <iostream>
#include <signal.h>
#include <atomic>
#include <thread>
#include <chrono>

std::atomic_bool g_stopServer{false};

void signal_handler(int signal) {
    std::cout << "Received signal " << signal << ", stopping server..." << std::endl;
    g_stopServer = true;
}

int main(int argc, char* argv[]) {
    // Register signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    try {
        // Create and start the hardware control server
        WebGrab::HardwareControlServer server;

        std::cout << "Hardware Control Server starting..." << std::endl;
        std::cout << "GPIO control available via TCP connections on port 8081" << std::endl;
        std::cout << "Example commands:" << std::endl;
        std::cout << "  Configure pin 17 as output: {\"pin\":17,\"direction\":\"output\"}" << std::endl;
        std::cout << "  Set pin 17 high: {\"pin\":17,\"value\":1}" << std::endl;
        std::cout << "  Configure pin 18 as input: {\"pin\":18,\"direction\":\"input\"}" << std::endl;
        std::cout << "  Read pin 18: {\"pin\":18}" << std::endl;
        std::cout << "Press Ctrl+C to stop" << std::endl;

        // Start the server (this will block until stopped)
        if (!server.Start()) {
            std::cerr << "Failed to start Hardware Control Server" << std::endl;
            return 1;
        }

        // Wait for stop signal
        while (!g_stopServer) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

        // Stop the server
        server.Stop();
        std::cout << "Hardware Control Server stopped" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Hardware Control Server failed: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}