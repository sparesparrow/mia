#pragma once

#include <json/json.h>
#include <string>
#include <vector>
#include <functional>
#include <map>

namespace tinymcp {

/**
 * Resource definition for MCP
 */
class Resource {
public:
    Resource() = default;
    Resource(const std::string& uri, const std::string& name);
    
    // Properties
    std::string uri;
    std::string name;
    std::string description;
    std::string mimeType;
    
    // Content provider function
    using ContentProvider = std::function<std::string()>;
    ContentProvider contentProvider;
    
    // Serialization
    Json::Value toJson() const;
    void fromJson(const Json::Value& json);
    
    // Content access
    std::string getContent() const;
};

/**
 * Resource registry for managing resources
 */
class ResourceRegistry {
public:
    void registerResource(const Resource& resource);
    void unregisterResource(const std::string& uri);
    Resource* getResource(const std::string& uri);
    std::vector<Resource> getAllResources() const;
    bool hasResource(const std::string& uri) const;
    
private:
    std::map<std::string, Resource> resources;
};

} // namespace tinymcp