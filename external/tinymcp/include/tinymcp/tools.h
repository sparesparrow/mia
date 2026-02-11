#pragma once

#include <json/json.h>
#include <string>
#include <functional>
#include <map>
#include <vector>

namespace tinymcp {

/**
 * Tool definition for MCP
 */
class Tool {
public:
    Tool() = default;
    Tool(const std::string& name, const std::string& description);
    
    // Properties
    std::string name;
    std::string description;
    Json::Value inputSchema;
    
    // Handler function type
    using Handler = std::function<Json::Value(const Json::Value& arguments)>;
    Handler handler;
    
    // Serialization
    Json::Value toJson() const;
    void fromJson(const Json::Value& json);
    
    // Validation
    bool validate(const Json::Value& arguments) const;
};

/**
 * Tool registry for managing tools
 */
class ToolRegistry {
public:
    void registerTool(const Tool& tool);
    void unregisterTool(const std::string& name);
    Tool* getTool(const std::string& name);
    std::vector<Tool> getAllTools() const;
    bool hasTool(const std::string& name) const;
    
private:
    std::map<std::string, Tool> tools;
};

} // namespace tinymcp