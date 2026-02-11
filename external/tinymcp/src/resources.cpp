#include "tinymcp/resources.h"

namespace tinymcp {

Resource::Resource(const std::string& uri, const std::string& name) 
    : uri(uri), name(name) {}

Json::Value Resource::toJson() const {
    Json::Value json;
    json["uri"] = uri;
    json["name"] = name;
    
    if (!description.empty()) {
        json["description"] = description;
    }
    
    if (!mimeType.empty()) {
        json["mimeType"] = mimeType;
    }
    
    return json;
}

void Resource::fromJson(const Json::Value& json) {
    uri = json.get("uri", "").asString();
    name = json.get("name", "").asString();
    description = json.get("description", "").asString();
    mimeType = json.get("mimeType", "").asString();
}

std::string Resource::getContent() const {
    if (contentProvider) {
        return contentProvider();
    }
    return "";
}

void ResourceRegistry::registerResource(const Resource& resource) {
    resources[resource.uri] = resource;
}

void ResourceRegistry::unregisterResource(const std::string& uri) {
    resources.erase(uri);
}

Resource* ResourceRegistry::getResource(const std::string& uri) {
    auto it = resources.find(uri);
    return (it != resources.end()) ? &it->second : nullptr;
}

std::vector<Resource> ResourceRegistry::getAllResources() const {
    std::vector<Resource> result;
    for (const auto& pair : resources) {
        result.push_back(pair.second);
    }
    return result;
}

bool ResourceRegistry::hasResource(const std::string& uri) const {
    return resources.find(uri) != resources.end();
}

} // namespace tinymcp