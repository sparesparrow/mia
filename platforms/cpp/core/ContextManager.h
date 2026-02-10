#pragma once

// Standard library includes
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace WebGrab {

/**
 * @brief User context information
 */
struct UserContext {
    std::string userId;
    std::string currentLocation;
    std::string preferredLanguage;
    std::string timezone;
    std::unordered_map<std::string, std::string> preferences;
    std::chrono::system_clock::time_point lastActivity;
};

/**
 * @brief Session context for maintaining conversation state
 */
struct SessionContext {
    std::string sessionId;
    std::string userId;
    std::string interfaceType; // voice, text, web, mobile
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point lastAccessed;
    
    // Conversation history
    std::vector<std::string> commandHistory;
    std::vector<std::string> responseHistory;
    
    // Current context variables
    std::unordered_map<std::string, std::string> variables;
    
    // Intent context for follow-up commands
    std::string lastIntent;
    std::unordered_map<std::string, std::string> lastParameters;
    
    // Service context
    std::string lastUsedService;
    std::unordered_map<std::string, std::string> serviceState;
    
    bool isActive() const {
        auto now = std::chrono::system_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::minutes>(now - lastAccessed);
        return duration.count() < 30; // Active for 30 minutes
    }
};

/**
 * @brief Device context for hardware-specific information
 */
struct DeviceContext {
    std::string deviceId;
    std::string deviceType; // raspberry_pi, linux_desktop, android, ios
    std::string platform;   // linux, windows, android, ios
    std::string version;
    
    // Hardware capabilities
    std::vector<std::string> audioDevices;
    std::vector<std::string> gpioCapabilities;
    std::unordered_map<std::string, std::string> systemInfo;
    
    // Current device state
    std::unordered_map<std::string, std::string> currentState;
    std::chrono::system_clock::time_point lastUpdate;
};

/**
 * @brief Context persistence interface
 */
class IContextPersistence {
public:
    virtual ~IContextPersistence() = default;
    
    virtual bool saveUserContext(const UserContext& context) = 0;
    virtual bool loadUserContext(const std::string& userId, UserContext& context) = 0;
    virtual bool deleteUserContext(const std::string& userId) = 0;
    
    virtual bool saveSessionContext(const SessionContext& context) = 0;
    virtual bool loadSessionContext(const std::string& sessionId, SessionContext& context) = 0;
    virtual bool deleteSessionContext(const std::string& sessionId) = 0;
    
    virtual bool saveDeviceContext(const DeviceContext& context) = 0;
    virtual bool loadDeviceContext(const std::string& deviceId, DeviceContext& context) = 0;
    virtual bool deleteDeviceContext(const std::string& deviceId) = 0;
};

/**
 * @brief File-based context persistence implementation
 */
class FileContextPersistence : public IContextPersistence {
public:
    FileContextPersistence(const std::string& dataDirectory);
    ~FileContextPersistence() = default;
    
    bool saveUserContext(const UserContext& context) override;
    bool loadUserContext(const std::string& userId, UserContext& context) override;
    bool deleteUserContext(const std::string& userId) override;
    
    bool saveSessionContext(const SessionContext& context) override;
    bool loadSessionContext(const std::string& sessionId, SessionContext& context) override;
    bool deleteSessionContext(const std::string& sessionId) override;
    
    bool saveDeviceContext(const DeviceContext& context) override;
    bool loadDeviceContext(const std::string& deviceId, DeviceContext& context) override;
    bool deleteDeviceContext(const std::string& deviceId) override;

private:
    std::string dataDirectory;
    std::string usersDir;
    std::string sessionsDir;
    std::string devicesDir;
    
    bool ensureDirectoryExists(const std::string& path);
    std::string serializeUserContext(const UserContext& context);
    std::string serializeSessionContext(const SessionContext& context);
    std::string serializeDeviceContext(const DeviceContext& context);
    
    bool deserializeUserContext(const std::string& data, UserContext& context);
    bool deserializeSessionContext(const std::string& data, SessionContext& context);
    bool deserializeDeviceContext(const std::string& data, DeviceContext& context);
};

/**
 * @brief Context Manager for managing user, session, and device contexts
 */
class ContextManager {
public:
    ContextManager(std::unique_ptr<IContextPersistence> persistence);
    ~ContextManager();
    
    // User context management
    bool createUser(const std::string& userId, const UserContext& context);
    bool updateUser(const std::string& userId, const UserContext& context);
    bool getUserContext(const std::string& userId, UserContext& context);
    bool deleteUser(const std::string& userId);
    
    // Session context management
    std::string createSession(const std::string& userId, const std::string& interfaceType);
    bool updateSession(const std::string& sessionId, const SessionContext& context);
    bool getSessionContext(const std::string& sessionId, SessionContext& context);
    bool deleteSession(const std::string& sessionId);
    void cleanupExpiredSessions();
    
    // Device context management
    bool registerDevice(const std::string& deviceId, const DeviceContext& context);
    bool updateDevice(const std::string& deviceId, const DeviceContext& context);
    bool getDeviceContext(const std::string& deviceId, DeviceContext& context);
    bool deleteDevice(const std::string& deviceId);
    
    // Context operations
    void addCommandToHistory(const std::string& sessionId, const std::string& command, const std::string& response);
    void setSessionVariable(const std::string& sessionId, const std::string& key, const std::string& value);
    std::string getSessionVariable(const std::string& sessionId, const std::string& key);
    
    void updateLastIntent(const std::string& sessionId, const std::string& intent, 
                         const std::unordered_map<std::string, std::string>& parameters);
    
    void updateServiceState(const std::string& sessionId, const std::string& serviceName,
                           const std::unordered_map<std::string, std::string>& state);
    
    // Context queries
    std::vector<std::string> getRecentCommands(const std::string& sessionId, size_t count = 5);
    std::vector<std::string> getActiveSessions(const std::string& userId);
    std::vector<std::string> getAllUsers();
    
    // User preferences
    void setUserPreference(const std::string& userId, const std::string& key, const std::string& value);
    std::string getUserPreference(const std::string& userId, const std::string& key);
    
    // Context-aware command processing
    bool shouldUseContextForCommand(const std::string& sessionId, const std::string& command);
    std::unordered_map<std::string, std::string> getContextualParameters(const std::string& sessionId, const std::string& intent);

private:
    std::unique_ptr<IContextPersistence> persistence;
    
    // In-memory caches for performance
    mutable std::mutex usersMutex;
    std::unordered_map<std::string, UserContext> usersCache;
    
    mutable std::mutex sessionsMutex;
    std::unordered_map<std::string, SessionContext> sessionsCache;
    
    mutable std::mutex devicesMutex;
    std::unordered_map<std::string, DeviceContext> devicesCache;
    
    // Helper methods
    std::string generateSessionId();
    void touchSession(const std::string& sessionId);
    bool isValidSessionId(const std::string& sessionId);
    bool isValidUserId(const std::string& userId);
    
    // Cache management
    void cacheUserContext(const UserContext& context);
    void cacheSessionContext(const SessionContext& context);
    void cacheDeviceContext(const DeviceContext& context);
    
    bool getCachedUserContext(const std::string& userId, UserContext& context);
    bool getCachedSessionContext(const std::string& sessionId, SessionContext& context);
    bool getCachedDeviceContext(const std::string& deviceId, DeviceContext& context);
    
    void removeCachedUserContext(const std::string& userId);
    void removeCachedSessionContext(const std::string& sessionId);
    void removeCachedDeviceContext(const std::string& deviceId);
};

} // namespace WebGrab