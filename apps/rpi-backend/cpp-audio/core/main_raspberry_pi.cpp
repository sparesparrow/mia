#include "CoreOrchestrator.h"
#include "UIAdapter.h"
#include "HardwareControlServer.h"
#include <csignal>
#include <iostream>
#include <unistd.h>
#include <memory>
#include <thread>
#include <chrono>

using namespace WebGrab;

namespace {

volatile std::sig_atomic_t g_shutdownSignal = 0;

void signalHandler(int signal) {
    if (g_shutdownSignal != 0) {
        ::_exit(128 + signal);
    }

    g_shutdownSignal = signal;
}

bool installSignalHandlers() {
    return std::signal(SIGINT, signalHandler) != SIG_ERR
        && std::signal(SIGTERM, signalHandler) != SIG_ERR
        && std::signal(SIGPIPE, SIG_IGN) != SIG_ERR;
}

bool shutdownRequested() {
    return g_shutdownSignal != 0;
}

} // namespace

int main(int argc, char* argv[]) {
    if (!installSignalHandlers()) {
        std::cerr << "Failed to install signal handlers" << std::endl;
        return 1;
    }

    std::unique_ptr<CoreOrchestrator> orchestrator;
    std::unique_ptr<UIManager> uiManager;
    std::unique_ptr<HardwareControlServer> hardwareServer;

    const auto shutdownServices = [&]() {
        if (uiManager) {
            uiManager->stopAll();
            uiManager.reset();
        }

        if (hardwareServer) {
            hardwareServer->Stop();
            hardwareServer.reset();
        }

        if (orchestrator) {
            orchestrator->stop();
            orchestrator.reset();
        }
    };

    int exitCode = 0;
    
    try {
        std::cout << "========================================" << std::endl;
        std::cout << "  AI-SERVIS Universal - Raspberry Pi" << std::endl;
        std::cout << "========================================" << std::endl;
        std::cout << std::endl;
        
        // Initialize Core Orchestrator
        std::cout << "Initializing Core Orchestrator..." << std::endl;
        orchestrator = std::make_unique<CoreOrchestrator>(8080, "/tmp/mia");
        
        if (!orchestrator->start()) {
            std::cerr << "Failed to start Core Orchestrator" << std::endl;
            exitCode = 1;
        } else {
            std::cout << "✓ Core Orchestrator started on port 8080" << std::endl;
            
            // Initialize Hardware Control Server
            std::cout << "Initializing Hardware Control Server..." << std::endl;
            hardwareServer = std::make_unique<HardwareControlServer>(8081, "localhost", 1883);
            
            if (!hardwareServer->Start()) {
                std::cerr << "Warning: Hardware Control Server failed to start (GPIO may not be available)" << std::endl;
            } else {
                std::cout << "✓ Hardware Control Server started on port 8081" << std::endl;
            }
            
            // Initialize UI Manager
            std::cout << "Initializing UI Manager..." << std::endl;
            uiManager = std::make_unique<UIManager>(orchestrator.get());
            
            // Register UI Adapters
            auto voiceAdapter = std::make_unique<VoiceUIAdapter>();
            if (uiManager->registerAdapter(std::move(voiceAdapter))) {
                std::cout << "✓ Voice UI Adapter registered" << std::endl;
            }
            
            auto textAdapter = std::make_unique<TextUIAdapter>();
            if (uiManager->registerAdapter(std::move(textAdapter))) {
                std::cout << "✓ Text UI Adapter registered" << std::endl;
            }
            
            auto webAdapter = std::make_unique<WebUIAdapter>(8082);
            if (uiManager->registerAdapter(std::move(webAdapter))) {
                std::cout << "✓ Web UI Adapter registered on port 8082" << std::endl;
            }
            
            auto mobileAdapter = std::make_unique<MobileUIAdapter>();
            if (uiManager->registerAdapter(std::move(mobileAdapter))) {
                std::cout << "✓ Mobile UI Adapter registered" << std::endl;
            }
            
            // Start all UI adapters
            if (!uiManager->startAll()) {
                std::cerr << "Warning: Some UI adapters failed to start" << std::endl;
            }
            
            std::cout << std::endl;
            std::cout << "========================================" << std::endl;
            std::cout << "  System Ready!" << std::endl;
            std::cout << "========================================" << std::endl;
            std::cout << "Services:" << std::endl;
            std::cout << "  - Core Orchestrator:  http://localhost:8080" << std::endl;
            std::cout << "  - Hardware Server:    http://localhost:8081" << std::endl;
            std::cout << "  - Web UI:             http://localhost:8082" << std::endl;
            std::cout << std::endl;
            std::cout << "Press Ctrl+C to stop" << std::endl;
            std::cout << std::endl;
            
            while (!shutdownRequested()) {
                std::this_thread::sleep_for(std::chrono::seconds(1));
            }

            std::cout << "Received shutdown signal " << g_shutdownSignal
                      << ", shutting down gracefully..." << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "Raspberry Pi runtime failed: " << e.what() << std::endl;
        exitCode = 1;
    }

    shutdownServices();
    
    return exitCode;
}
