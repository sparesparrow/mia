#include "CoreOrchestrator.h"
#include "UIAdapter.h"
#include "HardwareControlServer.h"
#include <iostream>
#include <signal.h>
#include <unistd.h>
#include <memory>
#include <thread>
#include <chrono>

using namespace WebGrab;

// Global pointers for signal handling
std::unique_ptr<CoreOrchestrator> g_orchestrator;
std::unique_ptr<UIManager> g_uiManager;
std::unique_ptr<HardwareControlServer> g_hardwareServer;

void signalHandler(int signal) {
    std::cout << "\nReceived signal " << signal << ", shutting down gracefully..." << std::endl;
    
    if (g_uiManager) {
        g_uiManager->stopAll();
    }
    
    if (g_hardwareServer) {
        g_hardwareServer->Stop();
    }
    
    if (g_orchestrator) {
        g_orchestrator->stop();
    }
    
    exit(0);
}

int main(int argc, char* argv[]) {
    // Register signal handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    std::cout << "========================================" << std::endl;
    std::cout << "  AI-SERVIS Universal - Raspberry Pi" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    // Initialize Core Orchestrator
    std::cout << "Initializing Core Orchestrator..." << std::endl;
    g_orchestrator = std::make_unique<CoreOrchestrator>(8080);
    
    if (!g_orchestrator->start()) {
        std::cerr << "Failed to start Core Orchestrator" << std::endl;
        return 1;
    }
    std::cout << "✓ Core Orchestrator started on port 8080" << std::endl;
    
    // Initialize Hardware Control Server
    std::cout << "Initializing Hardware Control Server..." << std::endl;
    g_hardwareServer = std::make_unique<HardwareControlServer>(8081, "localhost", 1883);
    
    if (!g_hardwareServer->Start()) {
        std::cerr << "Warning: Hardware Control Server failed to start (GPIO may not be available)" << std::endl;
    } else {
        std::cout << "✓ Hardware Control Server started on port 8081" << std::endl;
    }
    
    // Initialize UI Manager
    std::cout << "Initializing UI Manager..." << std::endl;
    g_uiManager = std::make_unique<UIManager>(g_orchestrator.get());
    
    // Register UI Adapters
    auto voiceAdapter = std::make_unique<VoiceUIAdapter>();
    if (g_uiManager->registerAdapter(std::move(voiceAdapter))) {
        std::cout << "✓ Voice UI Adapter registered" << std::endl;
    }
    
    auto textAdapter = std::make_unique<TextUIAdapter>();
    if (g_uiManager->registerAdapter(std::move(textAdapter))) {
        std::cout << "✓ Text UI Adapter registered" << std::endl;
    }
    
    auto webAdapter = std::make_unique<WebUIAdapter>(8082);
    if (g_uiManager->registerAdapter(std::move(webAdapter))) {
        std::cout << "✓ Web UI Adapter registered on port 8082" << std::endl;
    }
    
    auto mobileAdapter = std::make_unique<MobileUIAdapter>();
    if (g_uiManager->registerAdapter(std::move(mobileAdapter))) {
        std::cout << "✓ Mobile UI Adapter registered" << std::endl;
    }
    
    // Start all UI adapters
    if (!g_uiManager->startAll()) {
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
    
    // Main loop - keep running until signal
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        
        // Check if services are still running
        // In a production system, you might want to add health checks here
    }
    
    return 0;
}
