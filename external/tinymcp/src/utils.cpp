#include "tinymcp/utils.h"
#include <algorithm>
#include <cctype>
#include <random>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <iostream>

namespace tinymcp {
namespace utils {

std::string trim(const std::string& str) {
    size_t first = str.find_first_not_of(" \t\n\r");
    if (first == std::string::npos) return "";
    size_t last = str.find_last_not_of(" \t\n\r");
    return str.substr(first, last - first + 1);
}

std::vector<std::string> split(const std::string& str, char delimiter) {
    std::vector<std::string> result;
    std::stringstream ss(str);
    std::string item;
    
    while (std::getline(ss, item, delimiter)) {
        result.push_back(item);
    }
    
    return result;
}

std::string join(const std::vector<std::string>& parts, const std::string& delimiter) {
    std::string result;
    for (size_t i = 0; i < parts.size(); ++i) {
        result += parts[i];
        if (i < parts.size() - 1) {
            result += delimiter;
        }
    }
    return result;
}

std::string toLowerCase(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::tolower);
    return result;
}

std::string toUpperCase(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), ::toupper);
    return result;
}

std::string generateUuid() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    static std::uniform_int_distribution<> dis2(8, 11);
    
    std::stringstream ss;
    ss << std::hex;
    
    for (int i = 0; i < 8; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 4; i++) ss << dis(gen);
    ss << "-4";
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    ss << dis2(gen);
    for (int i = 0; i < 3; i++) ss << dis(gen);
    ss << "-";
    for (int i = 0; i < 12; i++) ss << dis(gen);
    
    return ss.str();
}

std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

int64_t getCurrentTimeMillis() {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
}

bool validateJsonSchema(const Json::Value& data, const Json::Value& schema) {
    // Basic validation - could be enhanced with full JSON schema validation
    if (schema.isMember("required") && schema["required"].isArray()) {
        for (const auto& required : schema["required"]) {
            if (!data.isMember(required.asString())) {
                return false;
            }
        }
    }
    return true;
}

Json::Value mergeJson(const Json::Value& base, const Json::Value& overlay) {
    Json::Value result = base;
    
    for (const auto& key : overlay.getMemberNames()) {
        if (result.isMember(key) && result[key].isObject() && overlay[key].isObject()) {
            result[key] = mergeJson(result[key], overlay[key]);
        } else {
            result[key] = overlay[key];
        }
    }
    
    return result;
}

MCPException::MCPException(const std::string& message) 
    : std::runtime_error(message) {}

MCPException::MCPException(int code, const std::string& message) 
    : std::runtime_error(message), code(code) {}

void DefaultLogger::log(Level level, const std::string& message) {
    if (level < minLevel) return;
    
    const char* levelStr = "";
    switch (level) {
        case Level::Debug: levelStr = "DEBUG"; break;
        case Level::Info: levelStr = "INFO"; break;
        case Level::Warning: levelStr = "WARN"; break;
        case Level::Error: levelStr = "ERROR"; break;
    }
    
    std::cerr << "[" << getCurrentTimestamp() << "] [" << levelStr << "] " << message << std::endl;
}

void DefaultLogger::setLevel(Level level) {
    minLevel = level;
}

static ILogger* globalLogger = nullptr;

ILogger* getLogger() {
    if (!globalLogger) {
        static DefaultLogger defaultLogger;
        globalLogger = &defaultLogger;
    }
    return globalLogger;
}

void setLogger(ILogger* logger) {
    globalLogger = logger;
}

} // namespace utils
} // namespace tinymcp