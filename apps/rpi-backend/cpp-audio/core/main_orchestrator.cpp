#include "CoreOrchestrator.h"

// Standard library includes
#include <csignal>
#include <iostream>
#include <string>

using namespace WebGrab;

// Global orchestrator instance for signal handling
std::unique_ptr<CoreOrchestrator> g_orchestrator;

void signalHandler(int signal) {
    std::cout << "\nReceived signal " << signal << ", shutting down..." << std::endl;
    if (g_orchestrator) {
        g_orchestrator->stop();
    }
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <port> <working_dir>" << std::endl;
        std::cerr << "Example: " << argv[0] << " 8080 /tmp/webgrab" << std::endl;
        return 1;
    }

    // Parse command line arguments
    uint16_t port;
    try {
        port = static_cast<uint16_t>(std::stoi(argv[1]));
    } catch (const std::exception& e) {
        std::cerr << "Invalid port number: " << argv[1] << std::endl;
        return 1;
    }

    std::string workingDir = argv[2];

    std::cout << "AI-SERVIS Core Orchestrator" << std::endl;
    std::cout << "============================" << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Working Directory: " << workingDir << std::endl;
    std::cout << std::endl;

    // Setup signal handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    try {
        // Create orchestrator
        g_orchestrator = std::make_unique<CoreOrchestrator>(port, workingDir);

        // Register some example services
        std::vector<std::string> audioCapabilities = {"audio", "music", "voice", "streaming"};
        g_orchestrator->registerService("ai-audio-assistant", "localhost", 8082, audioCapabilities);

        std::vector<std::string> platformCapabilities = {"system", "process", "file", "command"};
        g_orchestrator->registerService("ai-platform-linux", "localhost", 8083, platformCapabilities);

        std::vector<std::string> hardwareCapabilities = {"gpio", "sensor", "actuator", "pwm"};
        g_orchestrator->registerService("hardware-bridge", "localhost", 8084, hardwareCapabilities);

        // Start the orchestrator
        if (!g_orchestrator->start()) {
            std::cerr << "Failed to start Core Orchestrator" << std::endl;
            return 1;
        }

        std::cout << "Core Orchestrator started successfully!" << std::endl;
        std::cout << "Listening on port " << port << std::endl;
        std::cout << std::endl;

        // List registered services
        auto services = g_orchestrator->listServices();
        std::cout << "Registered Services:" << std::endl;
        for (const auto& service : services) {
            std::cout << "  - " << service.name << " (" << service.host << ":" << service.port << ")" << std::endl;
            std::cout << "    Capabilities: ";
            for (const std::string& cap : service.capabilities) {
                std::cout << cap << " ";
            }
            std::cout << std::endl;
        }
        std::cout << std::endl;

        std::cout << "Available Commands:" << std::endl;
        std::cout << "  Voice Commands:" << std::endl;
        std::cout << "    - 'play music jazz'         -> Routes to audio assistant" << std::endl;
        std::cout << "    - 'set volume 50'           -> Routes to audio assistant" << std::endl;
        std::cout << "    - 'switch to headphones'    -> Routes to audio assistant" << std::endl;
        std::cout << "    - 'open firefox'            -> Routes to platform controller" << std::endl;
        std::cout << "    - 'turn on gpio pin 18'     -> Routes to hardware bridge" << std::endl;
        std::cout << std::endl;

        std::cout << "Press Ctrl+C to stop the server" << std::endl;

        // Keep running until signal
        while (true) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            
            // Periodic health checks could be added here
            // g_orchestrator->checkServiceHealth();
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "Core Orchestrator shutdown complete" << std::endl;
    return 0;
}