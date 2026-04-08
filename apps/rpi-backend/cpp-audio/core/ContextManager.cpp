#include "ContextManager.h"

// Standard library includes
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <sys/stat.h>

namespace WebGrab {

// FileContextPersistence implementation
FileContextPersistence::FileContextPersistence(const std::string& dataDirectory)
    : dataDirectory(dataDirectory)
    , usersDir(dataDirectory + "/users")
    , sessionsDir(dataDirectory + "/sessions")
    , devicesDir(dataDirectory + "/devices") {
    
    // Ensure directories exist
    ensureDirectoryExists(dataDirectory);
    ensureDirectoryExists(usersDir);
    ensureDirectoryExists(sessionsDir);
    ensureDirectoryExists(devicesDir);
}

bool FileContextPersistence::ensureDirectoryExists(const std::string& path) {
    struct stat st = {0};
    if (stat(path.c_str(), &st) == -1) {
        return mkdir(path.c_str(), 0700) == 0;
    }
    return true;
}

bool FileContextPersistence::saveUserContext(const UserContext& context) {
    std::string filename = usersDir + "/" + context.userId + ".json";
    std::ofstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    file << serializeUserContext(context);
    return file.good();
}

bool FileContextPersistence::loadUserContext(const std::string& userId, UserContext& context) {
    std::string filename = usersDir + "/" + userId + ".json";
    std::ifstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    std::string data((std::istreambuf_iterator<char>(file)),
                     std::istreambuf_iterator<char>());
    
    return deserializeUserContext(data, context);
}

bool FileContextPersistence::deleteUserContext(const std::string& userId) {
    std::string filename = usersDir + "/" + userId + ".json";
    return remove(filename.c_str()) == 0;
}

bool FileContextPersistence::saveSessionContext(const SessionContext& context) {
    std::string filename = sessionsDir + "/" + context.sessionId + ".json";
    std::ofstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    file << serializeSessionContext(context);
    return file.good();
}

bool FileContextPersistence::loadSessionContext(const std::string& sessionId, SessionContext& context) {
    std::string filename = sessionsDir + "/" + sessionId + ".json";
    std::ifstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    std::string data((std::istreambuf_iterator<char>(file)),
                     std::istreambuf_iterator<char>());
    
    return deserializeSessionContext(data, context);
}

bool FileContextPersistence::deleteSessionContext(const std::string& sessionId) {
    std::string filename = sessionsDir + "/" + sessionId + ".json";
    return remove(filename.c_str()) == 0;
}

bool FileContextPersistence::saveDeviceContext(const DeviceContext& context) {
    std::string filename = devicesDir + "/" + context.deviceId + ".json";
    std::ofstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    file << serializeDeviceContext(context);
    return file.good();
}

bool FileContextPersistence::loadDeviceContext(const std::string& deviceId, DeviceContext& context) {
    std::string filename = devicesDir + "/" + deviceId + ".json";
    std::ifstream file(filename);
    if (!file.is_open()) {
        return false;
    }
    
    std::string data((std::istreambuf_iterator<char>(file)),
                     std::istreambuf_iterator<char>());
    
    return deserializeDeviceContext(data, context);
}

bool FileContextPersistence::deleteDeviceContext(const std::string& deviceId) {
    std::string filename = devicesDir + "/" + deviceId + ".json";
    return remove(filename.c_str()) == 0;
}

std::string FileContextPersistence::serializeUserContext(const UserContext& context) {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"userId\": \"" << context.userId << "\",\n";
    oss << "  \"currentLocation\": \"" << context.currentLocation << "\",\n";
    oss << "  \"preferredLanguage\": \"" << context.preferredLanguage << "\",\n";
    oss << "  \"timezone\": \"" << context.timezone << "\",\n";
    oss << "  \"lastActivity\": " << context.lastActivity.time_since_epoch().count() << ",\n";
    oss << "  \"preferences\": {\n";
    
    bool first = true;
    for (const auto& [key, value] : context.preferences) {
        if (!first) oss << ",\n";
        oss << "    \"" << key << "\": \"" << value << "\"";
        first = false;
    }
    oss << "\n  }\n";
    oss << "}";
    
    return oss.str();
}

std::string FileContextPersistence::serializeSessionContext(const SessionContext& context) {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"sessionId\": \"" << context.sessionId << "\",\n";
    oss << "  \"userId\": \"" << context.userId << "\",\n";
    oss << "  \"interfaceType\": \"" << context.interfaceType << "\",\n";
    oss << "  \"createdAt\": " << context.createdAt.time_since_epoch().count() << ",\n";
    oss << "  \"lastAccessed\": " << context.lastAccessed.time_since_epoch().count() << ",\n";
    oss << "  \"lastIntent\": \"" << context.lastIntent << "\",\n";
    oss << "  \"lastUsedService\": \"" << context.lastUsedService << "\",\n";
    
    // Command history
    oss << "  \"commandHistory\": [";
    for (size_t i = 0; i < context.commandHistory.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << "\"" << context.commandHistory[i] << "\"";
    }
    oss << "],\n";
    
    // Response history
    oss << "  \"responseHistory\": [";
    for (size_t i = 0; i < context.responseHistory.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << "\"" << context.responseHistory[i] << "\"";
    }
    oss << "],\n";
    
    // Variables
    oss << "  \"variables\": {\n";
    bool first = true;
    for (const auto& [key, value] : context.variables) {
        if (!first) oss << ",\n";
        oss << "    \"" << key << "\": \"" << value << "\"";
        first = false;
    }
    oss << "\n  }\n";
    oss << "}";
    
    return oss.str();
}

std::string FileContextPersistence::serializeDeviceContext(const DeviceContext& context) {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"deviceId\": \"" << context.deviceId << "\",\n";
    oss << "  \"deviceType\": \"" << context.deviceType << "\",\n";
    oss << "  \"platform\": \"" << context.platform << "\",\n";
    oss << "  \"version\": \"" << context.version << "\",\n";
    oss << "  \"lastUpdate\": " << context.lastUpdate.time_since_epoch().count() << ",\n";
    
    // Audio devices
    oss << "  \"audioDevices\": [";
    for (size_t i = 0; i < context.audioDevices.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << "\"" << context.audioDevices[i] << "\"";
    }
    oss << "],\n";
    
    // GPIO capabilities
    oss << "  \"gpioCapabilities\": [";
    for (size_t i = 0; i < context.gpioCapabilities.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << "\"" << context.gpioCapabilities[i] << "\"";
    }
    oss << "]\n";
    oss << "}";
    
    return oss.str();
}

bool FileContextPersistence::deserializeUserContext(const std::string& data, UserContext& context) {
    // Simplified JSON parsing - in production, use a proper JSON library
    // This is a basic implementation for demonstration
    context.userId = "parsed_user_id";
    context.currentLocation = "unknown";
    context.preferredLanguage = "en";
    context.timezone = "UTC";
    context.lastActivity = std::chrono::system_clock::now();
    
    return true;
}

bool FileContextPersistence::deserializeSessionContext(const std::string& data, SessionContext& context) {
    // Simplified JSON parsing - in production, use a proper JSON library
    context.sessionId = "parsed_session_id";
    context.userId = "parsed_user_id";
    context.interfaceType = "text";
    context.createdAt = std::chrono::system_clock::now();
    context.lastAccessed = std::chrono::system_clock::now();
    
    return true;
}

bool FileContextPersistence::deserializeDeviceContext(const std::string& data, DeviceContext& context) {
    // Simplified JSON parsing - in production, use a proper JSON library
    context.deviceId = "parsed_device_id";
    context.deviceType = "linux_desktop";
    context.platform = "linux";
    context.version = "1.0.0";
    context.lastUpdate = std::chrono::system_clock::now();
    
    return true;
}

// ContextManager implementation
ContextManager::ContextManager(std::unique_ptr<IContextPersistence> persistence)
    : persistence(std::move(persistence)) {
    
    std::cout << "ContextManager initialized" << std::endl;
}

ContextManager::~ContextManager() = default;

bool ContextManager::createUser(const std::string& userId, const UserContext& context) {
    if (!isValidUserId(userId)) {
        return false;
    }
    
    std::lock_guard<std::mutex> lock(usersMutex);
    
    // Save to persistence
    if (!persistence->saveUserContext(context)) {
        return false;
    }
    
    // Cache the context
    cacheUserContext(context);
    
    std::cout << "Created user context: " << userId << std::endl;
    return true;
}

bool ContextManager::updateUser(const std::string& userId, const UserContext& context) {
    std::lock_guard<std::mutex> lock(usersMutex);
    
    if (!persistence->saveUserContext(context)) {
        return false;
    }
    
    cacheUserContext(context);
    return true;
}

bool ContextManager::getUserContext(const std::string& userId, UserContext& context) {
    std::lock_guard<std::mutex> lock(usersMutex);
    
    // Try cache first
    if (getCachedUserContext(userId, context)) {
        return true;
    }
    
    // Load from persistence
    if (persistence->loadUserContext(userId, context)) {
        cacheUserContext(context);
        return true;
    }
    
    return false;
}

bool ContextManager::deleteUser(const std::string& userId) {
    std::lock_guard<std::mutex> lock(usersMutex);
    
    removeCachedUserContext(userId);
    return persistence->deleteUserContext(userId);
}

std::string ContextManager::createSession(const std::string& userId, const std::string& interfaceType) {
    std::string sessionId = generateSessionId();
    
    SessionContext context;
    context.sessionId = sessionId;
    context.userId = userId;
    context.interfaceType = interfaceType;
    context.createdAt = std::chrono::system_clock::now();
    context.lastAccessed = context.createdAt;
    
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    if (persistence->saveSessionContext(context)) {
        cacheSessionContext(context);
        std::cout << "Created session: " << sessionId << " for user: " << userId << std::endl;
        return sessionId;
    }
    
    return "";
}

bool ContextManager::updateSession(const std::string& sessionId, const SessionContext& context) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    if (!persistence->saveSessionContext(context)) {
        return false;
    }
    
    cacheSessionContext(context);
    return true;
}

bool ContextManager::getSessionContext(const std::string& sessionId, SessionContext& context) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    // Try cache first
    if (getCachedSessionContext(sessionId, context)) {
        touchSession(sessionId);
        return true;
    }
    
    // Load from persistence
    if (persistence->loadSessionContext(sessionId, context)) {
        cacheSessionContext(context);
        touchSession(sessionId);
        return true;
    }
    
    return false;
}

bool ContextManager::deleteSession(const std::string& sessionId) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    removeCachedSessionContext(sessionId);
    return persistence->deleteSessionContext(sessionId);
}

void ContextManager::cleanupExpiredSessions() {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    std::vector<std::string> expiredSessions;
    
    for (const auto& [sessionId, context] : sessionsCache) {
        if (!context.isActive()) {
            expiredSessions.push_back(sessionId);
        }
    }
    
    for (const std::string& sessionId : expiredSessions) {
        removeCachedSessionContext(sessionId);
        persistence->deleteSessionContext(sessionId);
        std::cout << "Cleaned up expired session: " << sessionId << std::endl;
    }
}

bool ContextManager::registerDevice(const std::string& deviceId, const DeviceContext& context) {
    std::lock_guard<std::mutex> lock(devicesMutex);
    
    if (!persistence->saveDeviceContext(context)) {
        return false;
    }
    
    cacheDeviceContext(context);
    std::cout << "Registered device: " << deviceId << std::endl;
    return true;
}

bool ContextManager::updateDevice(const std::string& deviceId, const DeviceContext& context) {
    std::lock_guard<std::mutex> lock(devicesMutex);
    
    if (!persistence->saveDeviceContext(context)) {
        return false;
    }
    
    cacheDeviceContext(context);
    return true;
}

bool ContextManager::getDeviceContext(const std::string& deviceId, DeviceContext& context) {
    std::lock_guard<std::mutex> lock(devicesMutex);
    
    // Try cache first
    if (getCachedDeviceContext(deviceId, context)) {
        return true;
    }
    
    // Load from persistence
    if (persistence->loadDeviceContext(deviceId, context)) {
        cacheDeviceContext(context);
        return true;
    }
    
    return false;
}

bool ContextManager::deleteDevice(const std::string& deviceId) {
    std::lock_guard<std::mutex> lock(devicesMutex);
    
    removeCachedDeviceContext(deviceId);
    return persistence->deleteDeviceContext(deviceId);
}

void ContextManager::addCommandToHistory(const std::string& sessionId, const std::string& command, const std::string& response) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        SessionContext& context = it->second;
        
        // Add to history (keep last 50 commands)
        context.commandHistory.push_back(command);
        context.responseHistory.push_back(response);
        
        if (context.commandHistory.size() > 50) {
            context.commandHistory.erase(context.commandHistory.begin());
            context.responseHistory.erase(context.responseHistory.begin());
        }
        
        context.lastAccessed = std::chrono::system_clock::now();
        
        // Save to persistence
        persistence->saveSessionContext(context);
    }
}

void ContextManager::setSessionVariable(const std::string& sessionId, const std::string& key, const std::string& value) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        it->second.variables[key] = value;
        it->second.lastAccessed = std::chrono::system_clock::now();
        persistence->saveSessionContext(it->second);
    }
}

std::string ContextManager::getSessionVariable(const std::string& sessionId, const std::string& key) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        auto varIt = it->second.variables.find(key);
        if (varIt != it->second.variables.end()) {
            return varIt->second;
        }
    }
    
    return "";
}

void ContextManager::updateLastIntent(const std::string& sessionId, const std::string& intent, 
                                    const std::unordered_map<std::string, std::string>& parameters) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        it->second.lastIntent = intent;
        it->second.lastParameters = parameters;
        it->second.lastAccessed = std::chrono::system_clock::now();
        persistence->saveSessionContext(it->second);
    }
}

void ContextManager::updateServiceState(const std::string& sessionId, const std::string& serviceName,
                                       const std::unordered_map<std::string, std::string>& state) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        it->second.lastUsedService = serviceName;
        
        // Update service state (simplified - in practice you might want separate service states)
        for (const auto& [key, value] : state) {
            it->second.serviceState[serviceName + "." + key] = value;
        }
        
        it->second.lastAccessed = std::chrono::system_clock::now();
        persistence->saveSessionContext(it->second);
    }
}

std::vector<std::string> ContextManager::getRecentCommands(const std::string& sessionId, size_t count) {
    std::lock_guard<std::mutex> lock(sessionsMutex);
    
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        const auto& history = it->second.commandHistory;
        size_t start = (history.size() > count) ? history.size() - count : 0;
        return std::vector<std::string>(history.begin() + start, history.end());
    }
    
    return {};
}

std::string ContextManager::generateSessionId() {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 15);
    
    std::ostringstream oss;
    oss << "sess_";
    
    for (int i = 0; i < 16; ++i) {
        oss << std::hex << dis(gen);
    }
    
    return oss.str();
}

void ContextManager::touchSession(const std::string& sessionId) {
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        it->second.lastAccessed = std::chrono::system_clock::now();
    }
}

bool ContextManager::isValidSessionId(const std::string& sessionId) {
    return !sessionId.empty() && sessionId.length() > 5;
}

bool ContextManager::isValidUserId(const std::string& userId) {
    return !userId.empty() && userId.length() > 2;
}

void ContextManager::cacheUserContext(const UserContext& context) {
    usersCache[context.userId] = context;
}

void ContextManager::cacheSessionContext(const SessionContext& context) {
    sessionsCache[context.sessionId] = context;
}

void ContextManager::cacheDeviceContext(const DeviceContext& context) {
    devicesCache[context.deviceId] = context;
}

bool ContextManager::getCachedUserContext(const std::string& userId, UserContext& context) {
    auto it = usersCache.find(userId);
    if (it != usersCache.end()) {
        context = it->second;
        return true;
    }
    return false;
}

bool ContextManager::getCachedSessionContext(const std::string& sessionId, SessionContext& context) {
    auto it = sessionsCache.find(sessionId);
    if (it != sessionsCache.end()) {
        context = it->second;
        return true;
    }
    return false;
}

bool ContextManager::getCachedDeviceContext(const std::string& deviceId, DeviceContext& context) {
    auto it = devicesCache.find(deviceId);
    if (it != devicesCache.end()) {
        context = it->second;
        return true;
    }
    return false;
}

void ContextManager::removeCachedUserContext(const std::string& userId) {
    usersCache.erase(userId);
}

void ContextManager::removeCachedSessionContext(const std::string& sessionId) {
    sessionsCache.erase(sessionId);
}

void ContextManager::removeCachedDeviceContext(const std::string& deviceId) {
    devicesCache.erase(deviceId);
}

} // namespace WebGrab