#include "tinymcp/protocol.h"
#include "tinymcp/utils.h"
#include <sstream>

namespace tinymcp {

Json::CharReaderBuilder ProtocolSerializer::readerBuilder;
Json::StreamWriterBuilder ProtocolSerializer::writerBuilder;

// Request implementation
Request::Request(const std::string& method) : method(method) {
    id = utils::generateUuid();
}

Json::Value Request::toJson() const {
    Json::Value json;
    json["jsonrpc"] = jsonrpc;
    json["id"] = id;
    json["method"] = method;
    if (!params.isNull()) {
        json["params"] = params;
    }
    return json;
}

void Request::fromJson(const Json::Value& json) {
    jsonrpc = json.get("jsonrpc", "2.0").asString();
    id = json.get("id", "").asString();
    method = json.get("method", "").asString();
    params = json.get("params", Json::Value());
}

// Response implementation
Response::Response(const std::string& id) {
    this->id = id;
}

Json::Value Response::toJson() const {
    Json::Value json;
    json["jsonrpc"] = jsonrpc;
    json["id"] = id;
    
    if (!error.isNull()) {
        json["error"] = error;
    } else {
        json["result"] = result;
    }
    
    return json;
}

void Response::fromJson(const Json::Value& json) {
    jsonrpc = json.get("jsonrpc", "2.0").asString();
    id = json.get("id", "").asString();
    
    if (json.isMember("error")) {
        error = json["error"];
    } else {
        result = json.get("result", Json::Value());
    }
}

// Notification implementation
Notification::Notification(const std::string& method) : method(method) {}

Json::Value Notification::toJson() const {
    Json::Value json;
    json["jsonrpc"] = jsonrpc;
    json["method"] = method;
    if (!params.isNull()) {
        json["params"] = params;
    }
    return json;
}

void Notification::fromJson(const Json::Value& json) {
    jsonrpc = json.get("jsonrpc", "2.0").asString();
    method = json.get("method", "").asString();
    params = json.get("params", Json::Value());
}

// ProtocolSerializer implementation
std::string ProtocolSerializer::serialize(const Message& message) {
    Json::Value json = message.toJson();
    std::ostringstream oss;
    std::unique_ptr<Json::StreamWriter> writer(writerBuilder.newStreamWriter());
    writer->write(json, &oss);
    return oss.str();
}

std::unique_ptr<Message> ProtocolSerializer::deserialize(const std::string& data) {
    Json::Value json;
    std::istringstream iss(data);
    std::string errors;
    
    std::unique_ptr<Json::CharReader> reader(readerBuilder.newCharReader());
    if (!reader->parse(data.c_str(), data.c_str() + data.length(), &json, &errors)) {
        throw utils::MCPException("Failed to parse JSON: " + errors);
    }
    
    std::unique_ptr<Message> message;
    
    if (json.isMember("method")) {
        if (json.isMember("id")) {
            auto request = std::make_unique<Request>();
            request->fromJson(json);
            message = std::move(request);
        } else {
            auto notification = std::make_unique<Notification>();
            notification->fromJson(json);
            message = std::move(notification);
        }
    } else if (json.isMember("result") || json.isMember("error")) {
        auto response = std::make_unique<Response>();
        response->fromJson(json);
        message = std::move(response);
    } else {
        throw utils::MCPException("Unknown message type");
    }
    
    return message;
}

} // namespace tinymcp