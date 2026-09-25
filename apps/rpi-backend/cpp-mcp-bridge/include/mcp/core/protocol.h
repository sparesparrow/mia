#pragma once

#include <string>
#include <variant>
#include <optional>
#include <vector>
#include <memory>
#include <functional>
#include <json/json.h>

namespace mcp {

/**
 * Core MCP Protocol implementation following JSON-RPC 2.0
 */
class Protocol {
public:
    // Request/Response ID type
    using Id = std::variant<std::monostate, int64_t, std::string>;
    
    // Error codes following JSON-RPC 2.0 spec
    enum class ErrorCode : int {
        ParseError = -32700,
        InvalidRequest = -32600,
        MethodNotFound = -32601,
        InvalidParams = -32602,
        InternalError = -32603,
        
        // MCP-specific errors
        ResourceNotFound = -32001,
        ResourceAccessDenied = -32002,
        ToolExecutionError = -32003,
        PromptRejected = -32004
    };
    
    struct Error {
        ErrorCode code;
        std::string message;
        std::optional<Json::Value> data;
        
        Json::Value toJson() const;
    };
    
    struct Request {
        std::string jsonrpc = "2.0";
        std::string method;
        std::optional<Json::Value> params;
        std::optional<Id> id;
        
        static Request fromJson(const Json::Value& j);
        Json::Value toJson() const;
    };
    
    struct Response {
        std::string jsonrpc = "2.0";
        std::optional<Json::Value> result;
        std::optional<Error> error;
        Id id;
        
        static Response fromJson(const Json::Value& j);
        Json::Value toJson() const;
    };
    
    struct Notification {
        std::string jsonrpc = "2.0";
        std::string method;
        std::optional<Json::Value> params;
        
        static Notification fromJson(const Json::Value& j);
        Json::Value toJson() const;
    };
    
    // MCP-specific message types
    using Message = std::variant<Request, Response, Notification>;
    
    // Parse raw JSON into MCP message
    static std::optional<Message> parse(const std::string& jsonStr);
    static std::optional<Message> parse(const Json::Value& json);
    
    // Serialize MCP message to JSON
    static std::string serialize(const Message& msg);
    static Json::Value toJson(const Message& msg);
};

/**
 * MCP Tool definition
 */
struct Tool {
    std::string name;
    std::string description;
    Json::Value inputSchema;
    
    // Tool execution handler
    using Handler = std::function<Json::Value(const Json::Value& params)>;
    Handler handler;
    
    Json::Value toJson() const;
};

/**
 * MCP Resource definition
 */
struct Resource {
    std::string uri;
    std::string name;
    std::optional<std::string> description;
    std::optional<std::string> mimeType;
    
    Json::Value toJson() const;
};

/**
 * MCP Prompt definition
 */
struct Prompt {
    std::string name;
    std::string description;
    std::vector<std::pair<std::string, std::string>> arguments;
    
    Json::Value toJson() const;
};

/**
 * Server capabilities
 */
struct ServerCapabilities {
    std::optional<bool> tools;
    std::optional<bool> prompts;
    std::optional<bool> resources;
    std::optional<bool> logging;
    
    Json::Value toJson() const;
};

/**
 * Client capabilities  
 */
struct ClientCapabilities {
    std::optional<bool> sampling;
    std::optional<bool> roots;
    
    Json::Value toJson() const;
};

} // namespace mcp