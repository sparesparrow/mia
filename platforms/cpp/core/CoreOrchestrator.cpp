#include "CoreOrchestrator.h"

// Local includes
#include "TcpListener.h"
#include "TcpSocket.h"
#include "FlatBuffersRequestReader.h"
#include "FlatBuffersResponseWriter.h"

// Standard library includes
#include <algorithm>
#include <chrono>
#include <iostream>
#include <sstream>
#include <utility>

// Third-party includes
#include <curl/curl.h>

namespace WebGrab {

// NLPProcessor implementation
NLPProcessor::NLPProcessor() {
    initializePatterns();
}

void NLPProcessor::initializePatterns() {
    // Audio and music control
    intentPatterns["play_music"] = {"play", "music", "song", "track", "album", "artist", "spotify", "youtube"};
    intentPatterns["control_volume"] = {"volume", "loud", "quiet", "mute", "unmute", "louder", "quieter"};
    intentPatterns["switch_audio"] = {"switch", "change", "output", "headphones", "speakers", "bluetooth", "rtsp"};
    
    // System control
    intentPatterns["system_control"] = {"open", "close", "launch", "run", "execute", "kill", "start", "stop"};
    intentPatterns["file_operation"] = {"download", "upload", "copy", "move", "delete", "create", "save"};
    
    // Smart home
    intentPatterns["smart_home"] = {"lights", "temperature", "thermostat", "lock", "unlock", "dim", "brightness"};
    
    // Communication
    intentPatterns["communication"] = {"send", "call", "message", "text", "email", "whatsapp", "telegram"};
    
    // Navigation
    intentPatterns["navigation"] = {"directions", "navigate", "route", "map", "location", "traffic", "gps"};
    
    // Hardware control
    intentPatterns["hardware_control"] = {"gpio", "pin", "sensor", "led", "relay", "pwm", "analog", "digital"};
}

IntentResult NLPProcessor::parseCommand(const std::string& text) const {
    IntentResult result;
    result.originalText = text;
    result.confidence = 0.0f;
    
    // Convert to lowercase for processing
    std::string textLower = text;
    std::transform(textLower.begin(), textLower.end(), textLower.begin(), ::tolower);
    
    // Split into words
    std::vector<std::string> words;
    std::istringstream iss(textLower);
    std::string word;
    while (iss >> word) {
        words.push_back(word);
    }
    
    if (words.empty()) {
        result.intent = "unknown";
        return result;
    }
    
    // Calculate intent scores
    std::unordered_map<std::string, int> intentScores;
    for (const auto& [intent, keywords] : intentPatterns) {
        int score = 0;
        for (const std::string& keyword : keywords) {
            if (textLower.find(keyword) != std::string::npos) {
                score++;
            }
        }
        if (score > 0) {
            intentScores[intent] = score;
        }
    }
    
    if (intentScores.empty()) {
        result.intent = "unknown";
        return result;
    }
    
    // Find best intent
    auto bestIntent = std::max_element(intentScores.begin(), intentScores.end(),
        [](const auto& a, const auto& b) { return a.second < b.second; });
    
    result.intent = bestIntent->first;
    result.confidence = static_cast<float>(bestIntent->second) / static_cast<float>(words.size());
    result.parameters = extractParameters(textLower, result.intent, words);
    
    return result;
}

std::unordered_map<std::string, std::string> NLPProcessor::extractParameters(
    const std::string& text, 
    const std::string& intent,
    const std::vector<std::string>& words) const {
    
    std::unordered_map<std::string, std::string> params;
    
    if (intent == "play_music") {
        // Look for artist patterns
        auto byPos = text.find(" by ");
        if (byPos != std::string::npos) {
            params["artist"] = text.substr(byPos + 4);
        }
        
        // Genre detection
        std::vector<std::string> genres = {"jazz", "rock", "classical", "pop", "electronic", "ambient", "folk", "metal"};
        for (const std::string& genre : genres) {
            if (text.find(genre) != std::string::npos) {
                params["genre"] = genre;
                break;
            }
        }
        
        // Default query extraction
        if (params.empty()) {
            std::string query;
            for (const std::string& word : words) {
                if (word != "play" && word != "music" && word != "song") {
                    if (!query.empty()) query += " ";
                    query += word;
                }
            }
            if (!query.empty()) {
                params["query"] = query;
            }
        }
    }
    else if (intent == "control_volume") {
        // Volume level extraction
        std::vector<std::string> volumeActions = {"up", "down", "high", "low", "max", "min", "mute", "unmute"};
        for (const std::string& action : volumeActions) {
            if (std::find(words.begin(), words.end(), action) != words.end()) {
                params["action"] = action;
                break;
            }
        }
        
        // Numeric volume
        for (const std::string& word : words) {
            if (std::all_of(word.begin(), word.end(), ::isdigit)) {
                params["level"] = word;
                break;
            }
        }
    }
    else if (intent == "switch_audio") {
        std::vector<std::string> devices = {"headphones", "speakers", "bluetooth", "rtsp", "hdmi", "usb"};
        for (const std::string& device : devices) {
            if (text.find(device) != std::string::npos) {
                params["device"] = device;
                break;
            }
        }
    }
    else if (intent == "system_control") {
        // Extract action and target
        std::vector<std::string> actions = {"open", "close", "launch", "run", "execute", "kill", "start", "stop"};
        for (size_t i = 0; i < words.size(); ++i) {
            if (std::find(actions.begin(), actions.end(), words[i]) != actions.end()) {
                params["action"] = words[i];
                if (i + 1 < words.size()) {
                    std::string target;
                    for (size_t j = i + 1; j < words.size(); ++j) {
                        if (!target.empty()) target += " ";
                        target += words[j];
                    }
                    params["target"] = target;
                }
                break;
            }
        }
    }
    else if (intent == "hardware_control") {
        // GPIO pin extraction
        for (const std::string& word : words) {
            if (word.find("pin") != std::string::npos || word.find("gpio") != std::string::npos) {
                // Look for number after pin/gpio
                size_t pos = word.find_first_of("0123456789");
                if (pos != std::string::npos) {
                    params["pin"] = word.substr(pos);
                }
            }
        }
        
        // Action extraction
        std::vector<std::string> gpioActions = {"on", "off", "high", "low", "toggle", "read", "write"};
        for (const std::string& action : gpioActions) {
            if (std::find(words.begin(), words.end(), action) != words.end()) {
                params["action"] = action;
                break;
            }
        }
    }
    
    return params;
}

// CommandProcessingJob implementation
CommandProcessingJob::CommandProcessingJob(const std::string& command, 
                                          const std::string& context,
                                          uint32_t sessionId,
                                          IResponseWriter* responseWriter,
                                          CoreOrchestrator* orchestrator)
    : command(command)
    , context(context)
    , sessionId(sessionId)
    , responseWriter(responseWriter)
    , orchestrator(orchestrator) {
}

void CommandProcessingJob::execute() {
    std::cout << "Processing command: " << command << " (session " << sessionId << ")" << std::endl;
    
    try {
        std::string result = orchestrator->processVoiceCommand(command, context);
        
        // Send success response
        StatusResponse response;
        response.sessionId = sessionId;
        response.message = result;
        responseWriter->write(response);
        
    } catch (const std::exception& e) {
        std::cout << "Error processing command: " << e.what() << std::endl;
        
        // Send error response
        ErrorResponse response;
        response.sessionId = sessionId;
        response.error = "Command processing failed: " + std::string(e.what());
        responseWriter->write(response);
    }
}

// CoreOrchestrator implementation
CoreOrchestrator::CoreOrchestrator(uint16_t port, const std::string& workingDir)
    : serverPort(port)
    , workingDirectory(workingDir)
    , running(false) {
    
    messageProcessor = std::make_unique<MessageQueueProcessor>(workingDir);
    nlpProcessor = std::make_unique<NLPProcessor>();
    
    std::cout << "CoreOrchestrator initialized on port " << port 
              << ", working dir: " << workingDir << std::endl;
}

CoreOrchestrator::~CoreOrchestrator() {
    stop();
}

bool CoreOrchestrator::start() {
    if (running.load()) {
        return true;
    }
    
    try {
        // Create TCP listener
        tcpListener = std::make_unique<TcpListener>(serverPort);
        if (!tcpListener->start()) {
            std::cerr << "Failed to start TCP listener on port " << serverPort << std::endl;
            return false;
        }
        
        running.store(true);
        
        // Start accept thread
        acceptThread = std::thread(&CoreOrchestrator::acceptLoop, this);
        
        // Start worker threads for command processing
        const size_t numWorkers = std::thread::hardware_concurrency();
        workerThreads.reserve(numWorkers);
        
        std::cout << "CoreOrchestrator started successfully on port " << serverPort << std::endl;
        std::cout << "Started " << numWorkers << " worker threads" << std::endl;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error starting CoreOrchestrator: " << e.what() << std::endl;
        running.store(false);
        return false;
    }
}

void CoreOrchestrator::stop() {
    if (!running.load()) {
        return;
    }
    
    running.store(false);
    
    // Stop TCP listener
    if (tcpListener) {
        tcpListener->stop();
    }
    
    // Signal all waiting threads
    stateCondition.notify_all();
    
    // Join accept thread
    if (acceptThread.joinable()) {
        acceptThread.join();
    }
    
    // Join worker threads
    for (std::thread& worker : workerThreads) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    
    std::cout << "CoreOrchestrator stopped" << std::endl;
}

bool CoreOrchestrator::registerService(const std::string& name, 
                                     const std::string& host, 
                                     uint16_t port,
                                     const std::vector<std::string>& capabilities) {
    std::lock_guard<std::mutex> lock(servicesMutex);
    
    ServiceInfo service;
    service.name = name;
    service.host = host;
    service.port = port;
    service.capabilities = capabilities;
    service.healthStatus = "registered";
    service.lastSeen = std::chrono::system_clock::now();
    
    services[name] = std::move(service);
    
    std::cout << "Registered service: " << name << " at " << host << ":" << port << std::endl;
    std::cout << "Capabilities: ";
    for (const std::string& cap : capabilities) {
        std::cout << cap << " ";
    }
    std::cout << std::endl;
    
    return true;
}

bool CoreOrchestrator::unregisterService(const std::string& name) {
    std::lock_guard<std::mutex> lock(servicesMutex);
    
    auto it = services.find(name);
    if (it != services.end()) {
        services.erase(it);
        std::cout << "Unregistered service: " << name << std::endl;
        return true;
    }
    
    return false;
}

std::vector<ServiceInfo> CoreOrchestrator::listServices() const {
    std::lock_guard<std::mutex> lock(servicesMutex);
    
    std::vector<ServiceInfo> result;
    result.reserve(services.size());
    
    for (const auto& [name, service] : services) {
        result.push_back(service);
    }
    
    return result;
}

std::string CoreOrchestrator::processVoiceCommand(const std::string& text, const std::string& context) {
    std::cout << "Processing voice command: " << text << std::endl;
    
    // Parse the command
    IntentResult intent = nlpProcessor->parseCommand(text);
    
    std::cout << "Parsed intent: " << intent.intent 
              << " (confidence: " << intent.confidence << ")" << std::endl;
    
    // Route to appropriate service
    return routeCommand(intent, context);
}

IntentResult CoreOrchestrator::parseCommand(const std::string& text) const {
    return nlpProcessor->parseCommand(text);
}

std::string CoreOrchestrator::routeCommand(const IntentResult& intent, const std::string& context) {
    if (intent.confidence < 0.1f) {
        return "Sorry, I couldn't understand the command. Please try again.";
    }
    
    std::string result;
    
    if (intent.intent == "play_music") {
        if (callService("ai-audio-assistant", "play_music", intent.parameters, result)) {
            return "Music command processed: " + result;
        }
        return "Audio service not available";
    }
    else if (intent.intent == "control_volume") {
        if (callService("ai-audio-assistant", "set_volume", intent.parameters, result)) {
            return "Volume command processed: " + result;
        }
        return "Audio service not available";
    }
    else if (intent.intent == "switch_audio") {
        if (callService("ai-audio-assistant", "switch_output", intent.parameters, result)) {
            return "Audio output switched: " + result;
        }
        return "Audio service not available";
    }
    else if (intent.intent == "system_control") {
        // Determine platform service
        std::string serviceName = "ai-platform-linux"; // Default to Linux
        if (callService(serviceName, "execute_command", intent.parameters, result)) {
            return "System command executed: " + result;
        }
        return "Platform service not available";
    }
    else if (intent.intent == "hardware_control") {
        if (callService("hardware-bridge", "gpio_control", intent.parameters, result)) {
            return "Hardware command executed: " + result;
        }
        return "Hardware service not available";
    }
    else if (intent.intent == "file_operation") {
        // Use existing WebGrab functionality for downloads
        if (intent.parameters.find("url") != intent.parameters.end()) {
            // Process as download request
            return "Download request queued";
        }
        return "File operation not supported";
    }
    
    return "Unknown command intent: " + intent.intent;
}

bool CoreOrchestrator::callService(const std::string& serviceName, 
                                 const std::string& toolName,
                                 const std::unordered_map<std::string, std::string>& parameters,
                                 std::string& result) {
    std::lock_guard<std::mutex> lock(servicesMutex);
    
    auto it = services.find(serviceName);
    if (it == services.end()) {
        std::cout << "Service not found: " << serviceName << std::endl;
        return false;
    }
    
    const ServiceInfo& service = it->second;
    
    try {
        // Build JSON payload for MCP call
        std::string payload = R"({"method": "tools/call", "params": {"name": ")" + toolName + R"(", "arguments": {)";
        
        bool first = true;
        for (const auto& [key, value] : parameters) {
            if (!first) payload += ", ";
            payload += "\"" + key + "\": \"" + value + "\"";
            first = false;
        }
        payload += "}}}";
        
        // Call HTTP service
        result = callHttpService(service.host, service.port, "/mcp", payload);
        
        // Update service health
        const_cast<ServiceInfo&>(service).healthStatus = "healthy";
        const_cast<ServiceInfo&>(service).lastSeen = std::chrono::system_clock::now();
        
        std::cout << "Called service " << serviceName << "::" << toolName 
                  << " -> " << result << std::endl;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cout << "Error calling service " << serviceName << ": " << e.what() << std::endl;
        const_cast<ServiceInfo&>(service).healthStatus = "error";
        return false;
    }
}

std::string CoreOrchestrator::callHttpService(const std::string& host, 
                                            uint16_t port,
                                            const std::string& endpoint,
                                            const std::string& payload) {
    CURL* curl = curl_easy_init();
    if (!curl) {
        std::cerr << "Failed to initialize CURL" << std::endl;
        return "";
    }
    
    std::string response_data;
    std::string url = "http://" + host + ":" + std::to_string(port) + endpoint;
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, [](void* contents, size_t size, size_t nmemb, void* userp) -> size_t {
        ((std::string*)userp)->append((char*)contents, size * nmemb);
        return size * nmemb;
    });
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_data);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    
    CURLcode res = curl_easy_perform(curl);
    long response_code = 0;
    if (res == CURLE_OK) {
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
    } else {
        std::cerr << "CURL error: " << curl_easy_strerror(res) << std::endl;
    }
    
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK || response_code != 200) {
        return "";
    }
    
    return response_data;
}

void CoreOrchestrator::acceptLoop() {
    std::cout << "Accept loop started" << std::endl;
    
    while (running.load()) {
        try {
            auto clientSocket = tcpListener->accept();
            if (clientSocket && running.load()) {
                // Handle client in separate thread
                std::thread clientThread(&CoreOrchestrator::handleClient, this, std::move(clientSocket));
                clientThread.detach();
            }
        } catch (const std::exception& e) {
            if (running.load()) {
                std::cerr << "Error in accept loop: " << e.what() << std::endl;
            }
        }
    }
    
    std::cout << "Accept loop stopped" << std::endl;
}

void CoreOrchestrator::handleClient(std::unique_ptr<TcpSocket> clientSocket) {
    try {
        auto reader = std::make_unique<FlatBuffersRequestReader>(clientSocket.get());
        auto writer = std::make_unique<FlatBuffersResponseWriter>(clientSocket.get());
        
        processClientRequest(std::move(reader), writer.get());
        
    } catch (const std::exception& e) {
        std::cerr << "Error handling client: " << e.what() << std::endl;
    }
}

void CoreOrchestrator::processClientRequest(std::unique_ptr<IRequestReader> reader, 
                                          IResponseWriter* writer) {
    RequestEnvelope envelope;
    
    while (reader->good() && reader->next(envelope)) {
        // Check request type and process accordingly
        if (envelope.type == RequestType::VoiceCommand) {
            // Extract voice command data
            std::string command = "example voice command"; // Extract from envelope
            std::string context = "{}"; // Extract context
            
            // Create and execute command processing job
            auto job = std::make_unique<CommandProcessingJob>(
                command, context, envelope.sessionId, writer, this);
            
            job->execute();
        }
        else {
            // Delegate to existing message processor for other request types
            auto legacyJob = messageProcessor->processMessage(std::move(reader), writer);
            if (legacyJob) {
                legacyJob->execute();
            }
        }
    }
}

} // namespace WebGrab