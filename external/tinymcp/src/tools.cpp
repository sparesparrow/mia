#include "tinymcp/tools.h"

namespace tinymcp {

Tool::Tool(const std::string& name, const std::string& description) 
    : name(name), description(description) {}

Json::Value Tool::toJson() const {
    Json::Value json;
    json["name"] = name;
    json["description"] = description;
    
    if (!inputSchema.isNull()) {
        json["inputSchema"] = inputSchema;
    }
    
    return json;
}

void Tool::fromJson(const Json::Value& json) {
    name = json.get("name", "").asString();
    description = json.get("description", "").asString();
    inputSchema = json.get("inputSchema", Json::Value());
}

bool Tool::validate(const Json::Value& arguments) const {
    // Basic validation - could be enhanced with JSON schema validation
    if (inputSchema.isNull()) {
        return true;
    }
    
    // Check required fields if specified
    if (inputSchema.isMember("required") && inputSchema["required"].isArray()) {
        for (const auto& required : inputSchema["required"]) {
            if (!arguments.isMember(required.asString())) {
                return false;
            }
        }
    }
    
    return true;
}

void ToolRegistry::registerTool(const Tool& tool) {
    tools[tool.name] = tool;
}

void ToolRegistry::unregisterTool(const std::string& name) {
    tools.erase(name);
}

Tool* ToolRegistry::getTool(const std::string& name) {
    auto it = tools.find(name);
    return (it != tools.end()) ? &it->second : nullptr;
}

std::vector<Tool> ToolRegistry::getAllTools() const {
    std::vector<Tool> result;
    for (const auto& pair : tools) {
        result.push_back(pair.second);
    }
    return result;
}

bool ToolRegistry::hasTool(const std::string& name) const {
    return tools.find(name) != tools.end();
}

} // namespace tinymcp