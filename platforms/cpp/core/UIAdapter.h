#pragma once

// Standard library includes
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace WebGrab {

// Forward declaration
class CoreOrchestrator;

/**
 * @brief UI command context information
 */
struct UIContext {
    std::string userId;
    std::string sessionId;
    std::string interfaceType; // "voice", "text", "web", "mobile"
    std::string location;
    std::string timestamp;
    std::unordered_map<std::string, std::string> metadata;
};

/**
 * @brief UI response format
 */
struct UIResponse {
    std::string content;
    std::string contentType; // "text", "audio", "json", "html"
    bool success;
    std::unordered_map<std::string, std::string> metadata;
};

/**
 * @brief Abstract base class for UI adapters
 */
class IUIAdapter {
public:
    virtual ~IUIAdapter() = default;
    
    /**
     * @brief Initialize the UI adapter
     */
    virtual bool initialize() = 0;
    
    /**
     * @brief Start the UI adapter
     */
    virtual bool start() = 0;
    
    /**
     * @brief Stop the UI adapter
     */
    virtual void stop() = 0;
    
    /**
     * @brief Process incoming command from UI
     */
    virtual void processCommand(const std::string& command, const UIContext& context) = 0;
    
    /**
     * @brief Send response back to UI
     */
    virtual bool sendResponse(const UIResponse& response, const UIContext& context) = 0;
    
    /**
     * @brief Get adapter type identifier
     */
    virtual std::string getType() const = 0;

protected:
    CoreOrchestrator* orchestrator = nullptr;
    
    void setOrchestrator(CoreOrchestrator* orch) { orchestrator = orch; }
    friend class UIManager;
};

/**
 * @brief Voice interface adapter
 */
class VoiceUIAdapter : public IUIAdapter {
public:
    VoiceUIAdapter();
    ~VoiceUIAdapter() override = default;
    
    bool initialize() override;
    bool start() override;
    void stop() override;
    void processCommand(const std::string& command, const UIContext& context) override;
    bool sendResponse(const UIResponse& response, const UIContext& context) override;
    std::string getType() const override { return "voice"; }

private:
    bool running;
    std::string audioInputDevice;
    std::string audioOutputDevice;
    
    void processAudioInput();
    bool convertTextToSpeech(const std::string& text, const std::string& outputFile);
    std::string convertSpeechToText(const std::string& audioFile);
};

/**
 * @brief Text-based interface adapter (CLI/Terminal)
 */
class TextUIAdapter : public IUIAdapter {
public:
    TextUIAdapter();
    ~TextUIAdapter() override = default;
    
    bool initialize() override;
    bool start() override;
    void stop() override;
    void processCommand(const std::string& command, const UIContext& context) override;
    bool sendResponse(const UIResponse& response, const UIContext& context) override;
    std::string getType() const override { return "text"; }

private:
    bool running;
    
    void inputLoop();
    void displayPrompt();
    void displayResponse(const std::string& response);
};

/**
 * @brief Web interface adapter (HTTP/WebSocket)
 */
class WebUIAdapter : public IUIAdapter {
public:
    WebUIAdapter(uint16_t port = 8080);
    ~WebUIAdapter() override = default;
    
    bool initialize() override;
    bool start() override;
    void stop() override;
    void processCommand(const std::string& command, const UIContext& context) override;
    bool sendResponse(const UIResponse& response, const UIContext& context) override;
    std::string getType() const override { return "web"; }

private:
    uint16_t httpPort;
    bool running;
    int httpServerSocket;
    std::thread httpServerThread;
    std::unordered_map<std::string, UIContext> activeSessions;
    
    void handleHttpRequest(const std::string& path, const std::string& body, std::string& response);
    void handleWebSocketMessage(const std::string& sessionId, const std::string& message);
    void httpServerLoop();
    std::string generateSessionId();
};

/**
 * @brief Mobile interface adapter (for mobile apps)
 */
class MobileUIAdapter : public IUIAdapter {
public:
    MobileUIAdapter();
    ~MobileUIAdapter() override = default;
    
    bool initialize() override;
    bool start() override;
    void stop() override;
    void processCommand(const std::string& command, const UIContext& context) override;
    bool sendResponse(const UIResponse& response, const UIContext& context) override;
    std::string getType() const override { return "mobile"; }

private:
    bool running;
    uint16_t apiPort;
    
    void handleMobileAPIRequest(const std::string& endpoint, const std::string& payload, std::string& response);
    bool authenticateRequest(const std::string& token);
};

/**
 * @brief UI Manager that coordinates multiple UI adapters
 */
class UIManager {
public:
    UIManager(CoreOrchestrator* orchestrator);
    ~UIManager();
    
    /**
     * @brief Register a UI adapter
     */
    bool registerAdapter(std::unique_ptr<IUIAdapter> adapter);
    
    /**
     * @brief Start all registered adapters
     */
    bool startAll();
    
    /**
     * @brief Stop all adapters
     */
    void stopAll();
    
    /**
     * @brief Get adapter by type
     */
    IUIAdapter* getAdapter(const std::string& type);
    
    /**
     * @brief Process command through appropriate adapter
     */
    void processCommand(const std::string& command, const UIContext& context);
    
    /**
     * @brief Send response through appropriate adapter
     */
    bool sendResponse(const UIResponse& response, const UIContext& context);

private:
    CoreOrchestrator* orchestrator;
    std::unordered_map<std::string, std::unique_ptr<IUIAdapter>> adapters;
    
    // Callback for processing commands
    std::function<void(const std::string&, const UIContext&)> commandCallback;
};

} // namespace WebGrab