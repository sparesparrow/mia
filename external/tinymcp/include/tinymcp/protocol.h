#pragma once

#include <json/json.h>
#include <string>
#include <memory>
#include <functional>
#include <vector>
#include <map>

namespace tinymcp {

/**
 * TinyMCP - Lightweight Model Context Protocol Implementation
 * A minimal, efficient C++ implementation of MCP
 */

// Forward declarations
class Message;
class Request;
class Response;
class Notification;

/**
 * MCP Protocol Version
 */
constexpr const char* PROTOCOL_VERSION = "0.1.0";

/**
 * Message types in MCP
 */
enum class MessageType {
    Request,
    Response,
    Notification,
    Error
};

/**
 * Base message class for MCP communication
 */
class Message {
public:
    Message() = default;
    virtual ~Message() = default;
    
    virtual MessageType getType() const = 0;
    virtual Json::Value toJson() const = 0;
    virtual void fromJson(const Json::Value& json) = 0;
    
    std::string id;
    std::string jsonrpc = "2.0";
};

/**
 * Request message
 */
class Request : public Message {
public:
    Request() = default;
    Request(const std::string& method);
    
    MessageType getType() const override { return MessageType::Request; }
    Json::Value toJson() const override;
    void fromJson(const Json::Value& json) override;
    
    std::string method;
    Json::Value params;
};

/**
 * Response message
 */
class Response : public Message {
public:
    Response() = default;
    Response(const std::string& id);
    
    MessageType getType() const override { return MessageType::Response; }
    Json::Value toJson() const override;
    void fromJson(const Json::Value& json) override;
    
    Json::Value result;
    Json::Value error;
};

/**
 * Notification message
 */
class Notification : public Message {
public:
    Notification() = default;
    Notification(const std::string& method);
    
    MessageType getType() const override { return MessageType::Notification; }
    Json::Value toJson() const override;
    void fromJson(const Json::Value& json) override;
    
    std::string method;
    Json::Value params;
};

/**
 * Protocol handler interface
 */
class IProtocolHandler {
public:
    virtual ~IProtocolHandler() = default;
    
    virtual void onRequest(const Request& request, Response& response) = 0;
    virtual void onNotification(const Notification& notification) = 0;
    virtual void onResponse(const Response& response) = 0;
};

/**
 * Protocol serializer/deserializer
 */
class ProtocolSerializer {
public:
    static std::string serialize(const Message& message);
    static std::unique_ptr<Message> deserialize(const std::string& data);
    
private:
    static Json::CharReaderBuilder readerBuilder;
    static Json::StreamWriterBuilder writerBuilder;
};

} // namespace tinymcp