#include "CoreOrchestrator.h"
#include "UIAdapter.h"

// Standard library includes
#include <csignal>
#include <iostream>
#include <memory>
#include <string>

using namespace WebGrab;

// Global instances for signal handling
std::unique_ptr<CoreOrchestrator> g_orchestrator;
std::unique_ptr<UIManager> g_uiManager;

void signalHandler(int signal) {
    std::cout << "\nReceived signal " << signal << ", shutting down..." << std::endl;
    
    if (g_uiManager) {
        g_uiManager->stopAll();
    }
    
    if (g_orchestrator) {
        g_orchestrator->stop();
    }
}

void printBanner() {
    std::cout << R"(
╔══════════════════════════════════════════════════════════════╗
║                   AI-SERVIS Universal                        ║
║                  Core Orchestrator Service                   ║
║                                                              ║
║  Multi-Interface AI Assistant with Natural Language         ║
║  Processing and Distributed Service Architecture            ║
╚══════════════════════════════════════════════════════════════╝
)" << std::endl;
}

void printHelp(const char* programName) {
    std::cout << "Usage: " << programName << " [options]" << std::endl;
    std::cout << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  --port <port>           Server port (default: 8080)" << std::endl;
    std::cout << "  --working-dir <path>    Working directory (default: /tmp/ai-servis)" << std::endl;
    std::cout << "  --web-port <port>       Web UI port (default: 8090)" << std::endl;
    std::cout << "  --mobile-port <port>    Mobile API port (default: 8091)" << std::endl;
    std::cout << "  --enable-voice          Enable voice interface" << std::endl;
    std::cout << "  --enable-text           Enable text interface" << std::endl;
    std::cout << "  --enable-web            Enable web interface" << std::endl;
    std::cout << "  --enable-mobile         Enable mobile interface" << std::endl;
    std::cout << "  --enable-all            Enable all interfaces" << std::endl;
    std::cout << "  --help                  Show this help message" << std::endl;
    std::cout << std::endl;
    std::cout << "Examples:" << std::endl;
    std::cout << "  " << programName << " --port 8080 --working-dir /tmp/ai-servis --enable-all" << std::endl;
    std::cout << "  " << programName << " --enable-text --enable-web --web-port 9000" << std::endl;
}

struct Config {
    uint16_t serverPort = 8080;
    std::string workingDir = "/tmp/ai-servis";
    uint16_t webPort = 8090;
    uint16_t mobilePort = 8091;
    bool enableVoice = false;
    bool enableText = false;
    bool enableWeb = false;
    bool enableMobile = false;
    bool showHelp = false;
};

Config parseArguments(int argc, char* argv[]) {
    Config config;
    
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--help") {
            config.showHelp = true;
        }
        else if (arg == "--port" && i + 1 < argc) {
            config.serverPort = static_cast<uint16_t>(std::stoi(argv[++i]));
        }
        else if (arg == "--working-dir" && i + 1 < argc) {
            config.workingDir = argv[++i];
        }
        else if (arg == "--web-port" && i + 1 < argc) {
            config.webPort = static_cast<uint16_t>(std::stoi(argv[++i]));
        }
        else if (arg == "--mobile-port" && i + 1 < argc) {
            config.mobilePort = static_cast<uint16_t>(std::stoi(argv[++i]));
        }
        else if (arg == "--enable-voice") {
            config.enableVoice = true;
        }
        else if (arg == "--enable-text") {
            config.enableText = true;
        }
        else if (arg == "--enable-web") {
            config.enableWeb = true;
        }
        else if (arg == "--enable-mobile") {
            config.enableMobile = true;
        }
        else if (arg == "--enable-all") {
            config.enableVoice = true;
            config.enableText = true;
            config.enableWeb = true;
            config.enableMobile = true;
        }
        else {
            std::cerr << "Unknown argument: " << arg << std::endl;
        }
    }
    
    return config;
}

int main(int argc, char* argv[]) {
    printBanner();
    
    Config config = parseArguments(argc, argv);
    
    if (config.showHelp) {
        printHelp(argv[0]);
        return 0;
    }
    
    // Default to text interface if none specified
    if (!config.enableVoice && !config.enableText && !config.enableWeb && !config.enableMobile) {
        config.enableText = true;
        std::cout << "No interfaces specified, enabling text interface by default" << std::endl;
    }
    
    std::cout << "Configuration:" << std::endl;
    std::cout << "  Server Port: " << config.serverPort << std::endl;
    std::cout << "  Working Directory: " << config.workingDir << std::endl;
    std::cout << "  Web Port: " << config.webPort << std::endl;
    std::cout << "  Mobile Port: " << config.mobilePort << std::endl;
    std::cout << "  Enabled Interfaces: ";
    if (config.enableVoice) std::cout << "Voice ";
    if (config.enableText) std::cout << "Text ";
    if (config.enableWeb) std::cout << "Web ";
    if (config.enableMobile) std::cout << "Mobile ";
    std::cout << std::endl << std::endl;
    
    // Setup signal handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    try {
        // Create core orchestrator
        std::cout << "Initializing Core Orchestrator..." << std::endl;
        g_orchestrator = std::make_unique<CoreOrchestrator>(config.serverPort, config.workingDir);
        
        // Register example services
        std::cout << "Registering services..." << std::endl;
        
        std::vector<std::string> audioCapabilities = {"audio", "music", "voice", "streaming", "volume", "playback"};
        g_orchestrator->registerService("ai-audio-assistant", "localhost", 8082, audioCapabilities);
        
        std::vector<std::string> platformCapabilities = {"system", "process", "file", "command", "application"};
        g_orchestrator->registerService("ai-platform-linux", "localhost", 8083, platformCapabilities);
        
        std::vector<std::string> hardwareCapabilities = {"gpio", "sensor", "actuator", "pwm", "i2c", "spi"};
        g_orchestrator->registerService("hardware-bridge", "localhost", 8084, hardwareCapabilities);
        
        std::vector<std::string> homeCapabilities = {"lights", "temperature", "security", "automation"};
        g_orchestrator->registerService("ai-home-automation", "localhost", 8085, homeCapabilities);
        
        // Create UI Manager
        std::cout << "Initializing UI Manager..." << std::endl;
        g_uiManager = std::make_unique<UIManager>(g_orchestrator.get());
        
        // Register enabled UI adapters
        if (config.enableVoice) {
            std::cout << "Registering Voice UI Adapter..." << std::endl;
            auto voiceAdapter = std::make_unique<VoiceUIAdapter>();
            g_uiManager->registerAdapter(std::move(voiceAdapter));
        }
        
        if (config.enableText) {
            std::cout << "Registering Text UI Adapter..." << std::endl;
            auto textAdapter = std::make_unique<TextUIAdapter>();
            g_uiManager->registerAdapter(std::move(textAdapter));
        }
        
        if (config.enableWeb) {
            std::cout << "Registering Web UI Adapter..." << std::endl;
            auto webAdapter = std::make_unique<WebUIAdapter>(config.webPort);
            g_uiManager->registerAdapter(std::move(webAdapter));
        }
        
        if (config.enableMobile) {
            std::cout << "Registering Mobile UI Adapter..." << std::endl;
            auto mobileAdapter = std::make_unique<MobileUIAdapter>();
            g_uiManager->registerAdapter(std::move(mobileAdapter));
        }
        
        // Start core orchestrator
        std::cout << "Starting Core Orchestrator..." << std::endl;
        if (!g_orchestrator->start()) {
            std::cerr << "Failed to start Core Orchestrator" << std::endl;
            return 1;
        }
        
        // Start all UI adapters
        std::cout << "Starting UI Adapters..." << std::endl;
        if (!g_uiManager->startAll()) {
            std::cerr << "Failed to start all UI adapters" << std::endl;
            return 1;
        }
        
        std::cout << std::endl;
        std::cout << "╔══════════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║                    SYSTEM READY                             ║" << std::endl;
        std::cout << "╚══════════════════════════════════════════════════════════════╝" << std::endl;
        std::cout << std::endl;
        
        // Display service status
        auto services = g_orchestrator->listServices();
        std::cout << "Registered Services (" << services.size() << "):" << std::endl;
        for (const auto& service : services) {
            std::cout << "  ✓ " << service.name << " (" << service.host << ":" << service.port << ")" << std::endl;
            std::cout << "    Capabilities: ";
            for (size_t i = 0; i < service.capabilities.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << service.capabilities[i];
            }
            std::cout << std::endl;
        }
        std::cout << std::endl;
        
        // Display interface information
        std::cout << "Active Interfaces:" << std::endl;
        if (config.enableVoice) {
            std::cout << "  ✓ Voice Interface - Listening for voice commands" << std::endl;
        }
        if (config.enableText) {
            std::cout << "  ✓ Text Interface - Type commands in terminal" << std::endl;
        }
        if (config.enableWeb) {
            std::cout << "  ✓ Web Interface - http://localhost:" << config.webPort << std::endl;
        }
        if (config.enableMobile) {
            std::cout << "  ✓ Mobile API - http://localhost:" << config.mobilePort << "/api" << std::endl;
        }
        std::cout << std::endl;
        
        // Display example commands
        std::cout << "Example Commands:" << std::endl;
        std::cout << "  Audio Control:" << std::endl;
        std::cout << "    • 'play jazz music'              → Routes to audio assistant" << std::endl;
        std::cout << "    • 'set volume 75'                → Routes to audio assistant" << std::endl;
        std::cout << "    • 'switch to bluetooth speakers' → Routes to audio assistant" << std::endl;
        std::cout << std::endl;
        std::cout << "  System Control:" << std::endl;
        std::cout << "    • 'open firefox'                 → Routes to platform controller" << std::endl;
        std::cout << "    • 'run terminal'                 → Routes to platform controller" << std::endl;
        std::cout << "    • 'kill chrome'                  → Routes to platform controller" << std::endl;
        std::cout << std::endl;
        std::cout << "  Hardware Control:" << std::endl;
        std::cout << "    • 'turn on gpio pin 18'         → Routes to hardware bridge" << std::endl;
        std::cout << "    • 'read sensor on pin 21'       → Routes to hardware bridge" << std::endl;
        std::cout << "    • 'set pwm pin 12 to 50'        → Routes to hardware bridge" << std::endl;
        std::cout << std::endl;
        std::cout << "  Smart Home:" << std::endl;
        std::cout << "    • 'turn on living room lights'  → Routes to home automation" << std::endl;
        std::cout << "    • 'set temperature to 22'       → Routes to home automation" << std::endl;
        std::cout << "    • 'lock front door'             → Routes to home automation" << std::endl;
        std::cout << std::endl;
        
        if (config.enableText) {
            std::cout << "Type 'help' for more commands, 'quit' to exit" << std::endl;
        }
        std::cout << "Press Ctrl+C to stop the system" << std::endl;
        std::cout << std::endl;
        
        // Main loop
        while (true) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            
            // Periodic tasks could be added here
            // - Health checks
            // - Service discovery
            // - Performance monitoring
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    std::cout << std::endl;
    std::cout << "AI-SERVIS Core Orchestrator shutdown complete" << std::endl;
    return 0;
}