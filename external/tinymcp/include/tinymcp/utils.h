#pragma once

#include <json/json.h>
#include <string>
#include <vector>
#include <chrono>
#include <stdexcept>

namespace tinymcp {

/**
 * Utility functions for TinyMCP
 */
namespace utils {

/**
 * String utilities
 */
std::string trim(const std::string& str);
std::vector<std::string> split(const std::string& str, char delimiter);
std::string join(const std::vector<std::string>& parts, const std::string& delimiter);
std::string toLowerCase(const std::string& str);
std::string toUpperCase(const std::string& str);

/**
 * UUID generation
 */
std::string generateUuid();

/**
 * Time utilities
 */
std::string getCurrentTimestamp();
int64_t getCurrentTimeMillis();

/**
 * JSON utilities
 */
bool validateJsonSchema(const Json::Value& data, const Json::Value& schema);
Json::Value mergeJson(const Json::Value& base, const Json::Value& overlay);

/**
 * Error handling
 */
class MCPException : public std::runtime_error {
public:
    explicit MCPException(const std::string& message);
    MCPException(int code, const std::string& message);
    
    int getCode() const { return code; }
    
private:
    int code = -1;
};

/**
 * Logging interface
 */
class ILogger {
public:
    enum class Level {
        Debug,
        Info,
        Warning,
        Error
    };
    
    virtual ~ILogger() = default;
    virtual void log(Level level, const std::string& message) = 0;
};

/**
 * Default logger implementation
 */
class DefaultLogger : public ILogger {
public:
    void log(Level level, const std::string& message) override;
    void setLevel(Level level);
    
private:
    Level minLevel = Level::Info;
};

/**
 * Global logger instance
 */
ILogger* getLogger();
void setLogger(ILogger* logger);

} // namespace utils
} // namespace tinymcp