#include "UIAdapter.h"
#include "CoreOrchestrator.h"

// Standard library includes
#include <chrono>
#include <cstdlib>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <thread>

// System includes
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <cstring>

namespace WebGrab {

// VoiceUIAdapter implementation
VoiceUIAdapter::VoiceUIAdapter() 
    : running(false)
    , audioInputDevice("default")
    , audioOutputDevice("default") {
}

bool VoiceUIAdapter::initialize() {
    std::cout << "Initializing Voice UI Adapter..." << std::endl;
    
    // In a real implementation, you would initialize audio subsystem
    // For now, we'll simulate voice input/output
    
    std::cout << "Voice UI Adapter initialized (simulated)" << std::endl;
    return true;
}

bool VoiceUIAdapter::start() {
    if (running) {
        return true;
    }
    
    running = true;
    
    // Start audio processing thread
    std::thread audioThread(&VoiceUIAdapter::processAudioInput, this);
    audioThread.detach();
    
    std::cout << "Voice UI Adapter started" << std::endl;
    return true;
}

void VoiceUIAdapter::stop() {
    running = false;
    std::cout << "Voice UI Adapter stopped" << std::endl;
}

void VoiceUIAdapter::processCommand(const std::string& command, const UIContext& context) {
    if (!orchestrator) {
        std::cerr << "No orchestrator available for voice command processing" << std::endl;
        return;
    }
    
    std::cout << "Processing voice command: " << command << std::endl;
    
    // Process command through orchestrator
    std::string result = orchestrator->processVoiceCommand(command, "voice_interface");
    
    // Create response
    UIResponse response;
    response.content = result;
    response.contentType = "audio";
    response.success = true;
    response.metadata["voice_synthesized"] = "true";
    
    // Send response back
    sendResponse(response, context);
}

bool VoiceUIAdapter::sendResponse(const UIResponse& response, const UIContext& context) {
    std::cout << "Voice response: " << response.content << std::endl;
    
    // In a real implementation, convert text to speech and play
    bool ttsSuccess = convertTextToSpeech(response.content, "/tmp/response.wav");
    
    return ttsSuccess;
}

void VoiceUIAdapter::processAudioInput() {
    std::cout << "Voice input processing started (simulated)" << std::endl;
    
    // Simulate voice commands for testing
    std::vector<std::string> testCommands = {
        "play some jazz music",
        "set volume to 70",
        "switch to headphones",
        "open firefox browser"
    };
    
    size_t commandIndex = 0;
    
    while (running) {
        std::this_thread::sleep_for(std::chrono::seconds(10));
        
        if (!running) break;
        
        // Simulate voice input
        if (commandIndex < testCommands.size()) {
            std::cout << "Simulated voice input: " << testCommands[commandIndex] << std::endl;
            
            UIContext context;
            context.userId = "voice_user";
            context.sessionId = "voice_session_" + std::to_string(commandIndex);
            context.interfaceType = "voice";
            context.timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
            
            processCommand(testCommands[commandIndex], context);
            commandIndex++;
        }
    }
    
    std::cout << "Voice input processing stopped" << std::endl;
}

bool VoiceUIAdapter::convertTextToSpeech(const std::string& text, const std::string& outputFile) {
    // Use espeak or festival for TTS on Raspberry Pi
    // Try espeak first (more commonly available)
    std::string command = "espeak -s 150 -v en -w \"" + outputFile + "\" \"" + text + "\" 2>/dev/null";
    
    int result = system(command.c_str());
    if (result == 0) {
        return true;
    }
    
    // Fallback to festival if espeak is not available
    command = "echo \"" + text + "\" | text2wave -o \"" + outputFile + "\" 2>/dev/null";
    result = system(command.c_str());
    
    if (result == 0) {
        return true;
    }
    
    // If both fail, try pico2wave (available on some Raspberry Pi systems)
    command = "pico2wave --wave=\"" + outputFile + "\" \"" + text + "\" 2>/dev/null";
    result = system(command.c_str());
    
    return result == 0;
}

std::string VoiceUIAdapter::convertSpeechToText(const std::string& audioFile) {
    // For Raspberry Pi, use pocketsphinx or vosk for speech-to-text
    // This is a simplified implementation - in production, use a proper STT library
    
    // Try vosk (if available)
    std::string command = "vosk-transcriber -i \"" + audioFile + "\" 2>/dev/null";
    FILE* pipe = popen(command.c_str(), "r");
    if (pipe) {
        char buffer[128];
        std::string result;
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            result += buffer;
        }
        pclose(pipe);
        if (!result.empty()) {
            // Remove trailing newline
            if (!result.empty() && result.back() == '\n') {
                result.pop_back();
            }
            return result;
        }
    }
    
    // Fallback to pocketsphinx (if available)
    command = "pocketsphinx_continuous -infile \"" + audioFile + "\" -logfn /dev/null 2>/dev/null";
    pipe = popen(command.c_str(), "r");
    if (pipe) {
        char buffer[128];
        std::string result;
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            result += buffer;
        }
        pclose(pipe);
        if (!result.empty()) {
            // Extract text from pocketsphinx output (format: "word1 word2 ...")
            // This is simplified - real implementation would parse properly
            if (!result.empty() && result.back() == '\n') {
                result.pop_back();
            }
            return result;
        }
    }
    
    // If both fail, return empty string
    return "";
}

// TextUIAdapter implementation
TextUIAdapter::TextUIAdapter() : running(false) {
}

bool TextUIAdapter::initialize() {
    std::cout << "Initializing Text UI Adapter..." << std::endl;
    return true;
}

bool TextUIAdapter::start() {
    if (running) {
        return true;
    }
    
    running = true;
    
    // Start input loop thread
    std::thread inputThread(&TextUIAdapter::inputLoop, this);
    inputThread.detach();
    
    std::cout << "Text UI Adapter started" << std::endl;
    std::cout << "Type 'help' for available commands, 'quit' to exit" << std::endl;
    
    return true;
}

void TextUIAdapter::stop() {
    running = false;
    std::cout << "Text UI Adapter stopped" << std::endl;
}

void TextUIAdapter::processCommand(const std::string& command, const UIContext& context) {
    if (!orchestrator) {
        std::cerr << "No orchestrator available for text command processing" << std::endl;
        return;
    }
    
    if (command == "help") {
        displayResponse("Available commands:\n"
                       "  play music [genre/artist] - Play music\n"
                       "  set volume [level]        - Set volume level\n"
                       "  switch to [device]        - Switch audio output\n"
                       "  open [application]        - Open application\n"
                       "  gpio [pin] [action]       - Control GPIO pin\n"
                       "  quit                      - Exit application");
        return;
    }
    
    if (command == "quit") {
        running = false;
        return;
    }
    
    // Process command through orchestrator
    std::string result = orchestrator->processVoiceCommand(command, "text_interface");
    
    // Create and send response
    UIResponse response;
    response.content = result;
    response.contentType = "text";
    response.success = true;
    
    sendResponse(response, context);
}

bool TextUIAdapter::sendResponse(const UIResponse& response, const UIContext& context) {
    displayResponse(response.content);
    return true;
}

void TextUIAdapter::inputLoop() {
    while (running) {
        displayPrompt();
        
        std::string input;
        if (!std::getline(std::cin, input)) {
            break;
        }
        
        if (input.empty()) {
            continue;
        }
        
        UIContext context;
        context.userId = "text_user";
        context.sessionId = "text_session";
        context.interfaceType = "text";
        context.timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        
        processCommand(input, context);
    }
}

void TextUIAdapter::displayPrompt() {
    std::cout << "ai-servis> ";
    std::cout.flush();
}

void TextUIAdapter::displayResponse(const std::string& response) {
    std::cout << response << std::endl;
}

// WebUIAdapter implementation
WebUIAdapter::WebUIAdapter(uint16_t port) 
    : httpPort(port)
    , running(false)
    , httpServerSocket(-1) {
}

bool WebUIAdapter::initialize() {
    std::cout << "Initializing Web UI Adapter on port " << httpPort << "..." << std::endl;
    
    // Create server socket
    httpServerSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (httpServerSocket < 0) {
        std::cerr << "Failed to create HTTP server socket" << std::endl;
        return false;
    }
    
    int opt = 1;
    setsockopt(httpServerSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(httpPort);
    
    if (bind(httpServerSocket, reinterpret_cast<sockaddr*>(&serverAddr), sizeof(serverAddr)) < 0) {
        std::cerr << "Failed to bind HTTP server socket" << std::endl;
        close(httpServerSocket);
        httpServerSocket = -1;
        return false;
    }
    
    if (listen(httpServerSocket, 10) < 0) {
        std::cerr << "Failed to listen on HTTP server socket" << std::endl;
        close(httpServerSocket);
        httpServerSocket = -1;
        return false;
    }
    
    return true;
}

bool WebUIAdapter::start() {
    if (running) {
        return true;
    }
    
    if (httpServerSocket < 0) {
        if (!initialize()) {
            return false;
        }
    }
    
    running = true;
    
    // Start HTTP server thread
    httpServerThread = std::thread(&WebUIAdapter::httpServerLoop, this);
    
    std::cout << "Web UI Adapter started on port " << httpPort << std::endl;
    std::cout << "Web interface available at: http://localhost:" << httpPort << std::endl;
    
    return true;
}

void WebUIAdapter::stop() {
    running = false;
    
    if (httpServerSocket >= 0) {
        close(httpServerSocket);
        httpServerSocket = -1;
    }
    
    if (httpServerThread.joinable()) {
        httpServerThread.join();
    }
    
    std::cout << "Web UI Adapter stopped" << std::endl;
}

void WebUIAdapter::processCommand(const std::string& command, const UIContext& context) {
    if (!orchestrator) {
        std::cerr << "No orchestrator available for web command processing" << std::endl;
        return;
    }
    
    std::cout << "Processing web command: " << command << std::endl;
    
    // Process command through orchestrator
    std::string result = orchestrator->processVoiceCommand(command, "web_interface");
    
    // Create response
    UIResponse response;
    response.content = result;
    response.contentType = "json";
    response.success = true;
    response.metadata["timestamp"] = context.timestamp;
    
    // Send response back
    sendResponse(response, context);
}

bool WebUIAdapter::sendResponse(const UIResponse& response, const UIContext& context) {
    std::cout << "Web response to session " << context.sessionId << ": " << response.content << std::endl;
    
    // In a real implementation, send HTTP/WebSocket response
    return true;
}

void WebUIAdapter::handleHttpRequest(const std::string& path, const std::string& body, std::string& response) {
    // Simple HTTP request handler
    if (path == "/" || path == "/index.html") {
        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                   "<html><body><h1>AI-SERVIS Web Interface</h1>"
                   "<p>Voice command interface</p></body></html>";
    } else if (path == "/api/command" && !body.empty()) {
        // Process command via orchestrator
        UIContext context;
        context.userId = "web_user";
        context.sessionId = generateSessionId();
        context.interfaceType = "web";
        context.timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        
        processCommand(body, context);
        
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
                   R"({"status": "ok", "message": "Command processed"})";
    } else if (path == "/api/status") {
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
                   R"({"status": "ok", "service": "ai-servis"})";
    } else {
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found";
    }
}

void WebUIAdapter::httpServerLoop() {
    while (running && httpServerSocket >= 0) {
        sockaddr_in clientAddr{};
        socklen_t clientAddrLen = sizeof(clientAddr);
        
        int clientSocket = accept(httpServerSocket, reinterpret_cast<sockaddr*>(&clientAddr), &clientAddrLen);
        if (clientSocket < 0) {
            if (running) {
                std::cerr << "Failed to accept HTTP client connection" << std::endl;
            }
            continue;
        }
        
        // Handle request in a simple way (single-threaded for now)
        char buffer[4096];
        ssize_t bytesRead = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
        if (bytesRead > 0) {
            buffer[bytesRead] = '\0';
            std::string request(buffer);
            
            // Parse HTTP request (simplified)
            std::string method, path, body;
            size_t methodEnd = request.find(' ');
            if (methodEnd != std::string::npos) {
                method = request.substr(0, methodEnd);
                size_t pathStart = methodEnd + 1;
                size_t pathEnd = request.find(' ', pathStart);
                if (pathEnd != std::string::npos) {
                    path = request.substr(pathStart, pathEnd - pathStart);
                }
            }
            
            // Extract body if present
            size_t bodyStart = request.find("\r\n\r\n");
            if (bodyStart != std::string::npos) {
                body = request.substr(bodyStart + 4);
            }
            
            std::string httpResponse;
            handleHttpRequest(path, body, httpResponse);
            
            send(clientSocket, httpResponse.c_str(), httpResponse.length(), 0);
        }
        
        close(clientSocket);
    }
}

void WebUIAdapter::handleWebSocketMessage(const std::string& sessionId, const std::string& message) {
    // Placeholder for WebSocket message handling
    std::cout << "WebSocket message from " << sessionId << ": " << message << std::endl;
}

std::string WebUIAdapter::generateSessionId() {
    // Simple session ID generation
    auto now = std::chrono::system_clock::now().time_since_epoch().count();
    return "web_session_" + std::to_string(now);
}

// MobileUIAdapter implementation
MobileUIAdapter::MobileUIAdapter() 
    : running(false)
    , apiPort(8081) {
}

bool MobileUIAdapter::initialize() {
    std::cout << "Initializing Mobile UI Adapter on port " << apiPort << "..." << std::endl;
    return true;
}

bool MobileUIAdapter::start() {
    if (running) {
        return true;
    }
    
    running = true;
    
    std::cout << "Mobile UI Adapter started on port " << apiPort << std::endl;
    std::cout << "Mobile API available at: http://localhost:" << apiPort << "/api" << std::endl;
    
    return true;
}

void MobileUIAdapter::stop() {
    running = false;
    std::cout << "Mobile UI Adapter stopped" << std::endl;
}

void MobileUIAdapter::processCommand(const std::string& command, const UIContext& context) {
    if (!orchestrator) {
        std::cerr << "No orchestrator available for mobile command processing" << std::endl;
        return;
    }
    
    std::cout << "Processing mobile command: " << command << std::endl;
    
    // Process command through orchestrator
    std::string result = orchestrator->processVoiceCommand(command, "mobile_interface");
    
    // Create response
    UIResponse response;
    response.content = result;
    response.contentType = "json";
    response.success = true;
    response.metadata["mobile_optimized"] = "true";
    
    // Send response back
    sendResponse(response, context);
}

bool MobileUIAdapter::sendResponse(const UIResponse& response, const UIContext& context) {
    std::cout << "Mobile response: " << response.content << std::endl;
    
    // In a real implementation, send mobile-optimized response
    return true;
}

void MobileUIAdapter::handleMobileAPIRequest(const std::string& endpoint, const std::string& payload, std::string& response) {
    // Mobile API request handler
    if (endpoint == "/api/command") {
        UIContext context;
        context.userId = "mobile_user";
        context.sessionId = "mobile_session";
        context.interfaceType = "mobile";
        context.timestamp = std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        
        if (orchestrator) {
            std::string result = orchestrator->processVoiceCommand(payload, "mobile_interface");
            response = R"({"status": "ok", "result": ")" + result + R"("})";
        } else {
            response = R"({"status": "error", "message": "Orchestrator not available"})";
        }
    } else if (endpoint == "/api/status") {
        response = R"({"status": "ok", "service": "ai-servis", "platform": "mobile"})";
    } else {
        response = R"({"status": "error", "message": "Unknown endpoint"})";
    }
}

bool MobileUIAdapter::authenticateRequest(const std::string& token) {
    // Simple token-based authentication
    // In production, this should validate against a proper authentication system
    if (token.empty()) {
        return false;
    }
    
    // For now, accept any non-empty token
    // In production, validate against a token database or JWT
    return token.length() >= 8; // Minimum token length check
}

// UIManager implementation
UIManager::UIManager(CoreOrchestrator* orchestrator) 
    : orchestrator(orchestrator) {
}

UIManager::~UIManager() {
    stopAll();
}

bool UIManager::registerAdapter(std::unique_ptr<IUIAdapter> adapter) {
    if (!adapter) {
        return false;
    }
    
    std::string type = adapter->getType();
    adapter->setOrchestrator(orchestrator);
    
    if (!adapter->initialize()) {
        std::cerr << "Failed to initialize " << type << " adapter" << std::endl;
        return false;
    }
    
    adapters[type] = std::move(adapter);
    std::cout << "Registered " << type << " UI adapter" << std::endl;
    
    return true;
}

bool UIManager::startAll() {
    bool allStarted = true;
    
    for (auto& [type, adapter] : adapters) {
        if (!adapter->start()) {
            std::cerr << "Failed to start " << type << " adapter" << std::endl;
            allStarted = false;
        }
    }
    
    if (allStarted) {
        std::cout << "All UI adapters started successfully" << std::endl;
    }
    
    return allStarted;
}

void UIManager::stopAll() {
    for (auto& [type, adapter] : adapters) {
        adapter->stop();
    }
    adapters.clear();
    std::cout << "All UI adapters stopped" << std::endl;
}

IUIAdapter* UIManager::getAdapter(const std::string& type) {
    auto it = adapters.find(type);
    return (it != adapters.end()) ? it->second.get() : nullptr;
}

void UIManager::processCommand(const std::string& command, const UIContext& context) {
    IUIAdapter* adapter = getAdapter(context.interfaceType);
    if (adapter) {
        adapter->processCommand(command, context);
    } else {
        std::cerr << "No adapter found for interface type: " << context.interfaceType << std::endl;
    }
}

bool UIManager::sendResponse(const UIResponse& response, const UIContext& context) {
    IUIAdapter* adapter = getAdapter(context.interfaceType);
    if (adapter) {
        return adapter->sendResponse(response, context);
    }
    
    std::cerr << "No adapter found for interface type: " << context.interfaceType << std::endl;
    return false;
}

} // namespace WebGrab