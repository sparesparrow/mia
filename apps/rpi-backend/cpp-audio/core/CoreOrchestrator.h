#pragma once

// Local includes
#include "IJob.h"
#include "IRequestReader.h"
#include "IResponseWriter.h"
#include "MessageQueueProcessor.h"

// Standard library includes
#include <atomic>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

// Forward declarations
class TcpListener;
class TcpSocket;

namespace WebGrab {

/**
 * @brief Service information for registered modules
 */
struct ServiceInfo {
    std::string name;
    std::string host;
    uint16_t port;
    std::vector<std::string> capabilities;
    std::string healthStatus;
    std::chrono::system_clock::time_point lastSeen;
};

/**
 * @brief Intent classification result
 */
struct IntentResult {
    std::string intent;
    float confidence;
    std::unordered_map<std::string, std::string> parameters;
    std::string originalText;
};

/**
 * @brief Natural Language Processing engine for intent recognition
 */
class NLPProcessor {
public:
    NLPProcessor();
    ~NLPProcessor() = default;

    /**
     * @brief Parse natural language command into intent and parameters
     */
    IntentResult parseCommand(const std::string& text) const;

private:
    std::unordered_map<std::string, std::vector<std::string>> intentPatterns;
    
    void initializePatterns();
    std::unordered_map<std::string, std::string> extractParameters(
        const std::string& text, 
        const std::string& intent,
        const std::vector<std::string>& words) const;
};

/**
 * @brief Command processing job for orchestrator
 */
class CommandProcessingJob : public IJob {
public:
    CommandProcessingJob(const std::string& command, 
                        const std::string& context,
                        uint32_t sessionId,
                        IResponseWriter* responseWriter,
                        class CoreOrchestrator* orchestrator);
    
    void execute() override;
    
    [[nodiscard]] uint32_t getSessionId() const { return sessionId; }

private:
    std::string command;
    std::string context;
    uint32_t sessionId;
    IResponseWriter* responseWriter;
    CoreOrchestrator* orchestrator;
};

/**
 * @brief Core Orchestrator Service
 * 
 * Main MCP host that coordinates all AI modules and provides
 * natural language processing pipeline for voice commands.
 */
class CoreOrchestrator {
public:
    CoreOrchestrator(uint16_t port, const std::string& workingDir);
    ~CoreOrchestrator();

    bool start();
    void stop();

    // Service management
    bool registerService(const std::string& name, 
                        const std::string& host, 
                        uint16_t port,
                        const std::vector<std::string>& capabilities);
    
    bool unregisterService(const std::string& name);
    std::vector<ServiceInfo> listServices() const;
    bool checkServiceHealth(const std::string& name);

    // Command processing
    std::string processVoiceCommand(const std::string& text, const std::string& context = "");
    IntentResult parseCommand(const std::string& text) const;
    std::string routeCommand(const IntentResult& intent, const std::string& context);

    // MCP integration
    bool callService(const std::string& serviceName, 
                    const std::string& toolName,
                    const std::unordered_map<std::string, std::string>& parameters,
                    std::string& result);

private:
    // Core components
    std::unique_ptr<MessageQueueProcessor> messageProcessor;
    std::unique_ptr<TcpListener> tcpListener;
    std::unique_ptr<NLPProcessor> nlpProcessor;
    
    // Service registry
    mutable std::mutex servicesMutex;
    std::unordered_map<std::string, ServiceInfo> services;
    
    // Server state
    std::atomic<bool> running;
    uint16_t serverPort;
    std::string workingDirectory;
    
    // Worker threads
    std::vector<std::thread> workerThreads;
    std::thread acceptThread;
    
    // Thread synchronization
    std::mutex stateMutex;
    std::condition_variable stateCondition;

    // Private methods
    void acceptLoop();
    void handleClient(std::unique_ptr<TcpSocket> clientSocket);
    void processClientRequest(std::unique_ptr<IRequestReader> reader, 
                             IResponseWriter* writer);
    
    std::string callHttpService(const std::string& host, 
                               uint16_t port,
                               const std::string& endpoint,
                               const std::string& payload);
    
    bool validateServiceConnection(const ServiceInfo& service);
    void periodicHealthCheck();
};

} // namespace WebGrab