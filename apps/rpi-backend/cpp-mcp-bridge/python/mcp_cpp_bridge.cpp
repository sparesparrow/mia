#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>
#include <pybind11/complex.h>
#include <pybind11/numpy.h>
#include <json/json.h>
#include "mcp/server/server.h"
#include "mcp/client/client.h"
#include "mcp/core/tinymcp_wrapper.h"
#include "mcp/transport/stdio_transport.h"
#include "mcp/transport/tcp_transport.h"
#include "mcp/transport/websocket_transport.h"

namespace py = pybind11;
using namespace mcp;

// JSON conversion helpers for jsoncpp
namespace {
    py::object json_to_python(const Json::Value& j) {
        if (j.isNull()) return py::none();
        if (j.isBool()) return py::bool_(j.asBool());
        if (j.isInt()) return py::int_(j.asInt64());
        if (j.isDouble()) return py::float_(j.asDouble());
        if (j.isString()) return py::str(j.asString());
        
        if (j.isArray()) {
            py::list lst;
            for (const auto& item : j) {
                lst.append(json_to_python(item));
            }
            return lst;
        }
        
        if (j.isObject()) {
            py::dict d;
            for (const auto& key : j.getMemberNames()) {
                d[py::str(key)] = json_to_python(j[key]);
            }
            return d;
        }
        
        return py::none();
    }
    
    Json::Value python_to_json(const py::handle& obj) {
        Json::Value result;
        
        if (obj.is_none()) {
            return result; // Returns null value
        }
        if (py::isinstance<py::bool_>(obj)) {
            result = obj.cast<bool>();
            return result;
        }
        if (py::isinstance<py::int_>(obj)) {
            result = static_cast<Json::Int64>(obj.cast<int64_t>());
            return result;
        }
        if (py::isinstance<py::float_>(obj)) {
            result = obj.cast<double>();
            return result;
        }
        if (py::isinstance<py::str>(obj)) {
            result = obj.cast<std::string>();
            return result;
        }
        
        if (py::isinstance<py::list>(obj) || py::isinstance<py::tuple>(obj)) {
            result = Json::Value(Json::arrayValue);
            for (const auto& item : obj) {
                result.append(python_to_json(item));
            }
            return result;
        }
        
        if (py::isinstance<py::dict>(obj)) {
            result = Json::Value(Json::objectValue);
            for (const auto& item : obj.cast<py::dict>()) {
                result[item.first.cast<std::string>()] = python_to_json(item.second);
            }
            return result;
        }
        
        throw std::runtime_error("Unsupported Python type for JSON conversion");
    }
}

PYBIND11_MODULE(mcp_cpp_bridge, m) {
    m.doc() = "MCP C++ Bridge - High-performance Model Context Protocol implementation";
    
    // Protocol module
    auto protocol = m.def_submodule("protocol", "MCP Protocol definitions");
    
    py::enum_<Protocol::ErrorCode>(protocol, "ErrorCode")
        .value("ParseError", Protocol::ErrorCode::ParseError)
        .value("InvalidRequest", Protocol::ErrorCode::InvalidRequest)
        .value("MethodNotFound", Protocol::ErrorCode::MethodNotFound)
        .value("InvalidParams", Protocol::ErrorCode::InvalidParams)
        .value("InternalError", Protocol::ErrorCode::InternalError)
        .value("ResourceNotFound", Protocol::ErrorCode::ResourceNotFound)
        .value("ResourceAccessDenied", Protocol::ErrorCode::ResourceAccessDenied)
        .value("ToolExecutionError", Protocol::ErrorCode::ToolExecutionError)
        .value("PromptRejected", Protocol::ErrorCode::PromptRejected);
    
    py::class_<Tool>(protocol, "Tool")
        .def(py::init<>())
        .def_readwrite("name", &Tool::name)
        .def_readwrite("description", &Tool::description)
        .def_property("input_schema",
            [](const Tool& t) { return json_to_python(t.input_schema); },
            [](Tool& t, py::object obj) { t.input_schema = python_to_json(obj); })
        .def("set_handler", [](Tool& t, py::function handler) {
            t.handler = [handler](const Json::Value& params) -> Json::Value {
                py::gil_scoped_acquire acquire;
                auto result = handler(json_to_python(params));
                return python_to_json(result);
            };
        });
    
    py::class_<Resource>(protocol, "Resource")
        .def(py::init<>())
        .def_readwrite("uri", &Resource::uri)
        .def_readwrite("name", &Resource::name)
        .def_readwrite("description", &Resource::description)
        .def_readwrite("mime_type", &Resource::mime_type);
    
    py::class_<Prompt>(protocol, "Prompt")
        .def(py::init<>())
        .def_readwrite("name", &Prompt::name)
        .def_readwrite("description", &Prompt::description)
        .def_readwrite("arguments", &Prompt::arguments);
    
    // Server module
    auto server_module = m.def_submodule("server", "MCP Server implementation");
    
    py::class_<ServerCapabilities>(server_module, "ServerCapabilities")
        .def(py::init<>())
        .def_readwrite("tools", &ServerCapabilities::tools)
        .def_readwrite("prompts", &ServerCapabilities::prompts)
        .def_readwrite("resources", &ServerCapabilities::resources)
        .def_readwrite("logging", &ServerCapabilities::logging);
    
    py::class_<server::Server::Config>(server_module, "ServerConfig")
        .def(py::init<>())
        .def_readwrite("name", &server::Server::Config::name)
        .def_readwrite("version", &server::Server::Config::version)
        .def_readwrite("capabilities", &server::Server::Config::capabilities)
        .def_readwrite("worker_threads", &server::Server::Config::worker_threads)
        .def_readwrite("max_concurrent_requests", &server::Server::Config::max_concurrent_requests)
        .def_readwrite("request_timeout", &server::Server::Config::request_timeout);
    
    py::class_<server::Server::Stats>(server_module, "ServerStats")
        .def_readonly("requests_received", &server::Server::Stats::requests_received)
        .def_readonly("requests_processed", &server::Server::Stats::requests_processed)
        .def_readonly("requests_failed", &server::Server::Stats::requests_failed)
        .def_readonly("notifications_received", &server::Server::Stats::notifications_received)
        .def_readonly("avg_response_time", &server::Server::Stats::avg_response_time);
    
    py::class_<server::Server>(server_module, "Server")
        .def(py::init<server::Server::Config>(), py::arg("config") = server::Server::Config{})
        .def("register_tool", &server::Server::register_tool)
        .def("unregister_tool", &server::Server::unregister_tool)
        .def("register_resource", &server::Server::register_resource)
        .def("unregister_resource", &server::Server::unregister_resource)
        .def("register_prompt", &server::Server::register_prompt)
        .def("unregister_prompt", &server::Server::unregister_prompt)
        .def("start", &server::Server::start)
        .def("stop", &server::Server::stop)
        .def("is_running", &server::Server::is_running)
        .def("get_stats", &server::Server::get_stats);
    
    py::class_<server::ServerBuilder>(server_module, "ServerBuilder")
        .def(py::init<>())
        .def("with_name", &server::ServerBuilder::with_name)
        .def("with_version", &server::ServerBuilder::with_version)
        .def("with_capabilities", &server::ServerBuilder::with_capabilities)
        .def("with_worker_threads", &server::ServerBuilder::with_worker_threads)
        .def("with_max_concurrent_requests", &server::ServerBuilder::with_max_concurrent_requests)
        .def("add_tool", &server::ServerBuilder::add_tool)
        .def("add_resource", &server::ServerBuilder::add_resource)
        .def("add_prompt", &server::ServerBuilder::add_prompt)
        .def("build", &server::ServerBuilder::build);
    
    // TinyMCP wrapper module
    auto tinymcp_module = m.def_submodule("tinymcp", "TinyMCP integration");
    
    py::class_<TinyMCPWrapper>(tinymcp_module, "TinyMCPWrapper")
        .def(py::init<>())
        .def_static("create_server", &TinyMCPWrapper::createServer, 
            "Create a TinyMCP server with configuration")
        .def_static("create_client", &TinyMCPWrapper::createClient,
            "Create a TinyMCP client");
    
    py::class_<ExtendedMCPServer>(tinymcp_module, "ExtendedMCPServer")
        .def(py::init<const server::Server::Config&>())
        .def("register_advanced_tool", &ExtendedMCPServer::registerAdvancedTool)
        .def("enable_metrics", &ExtendedMCPServer::enableMetrics)
        .def("enable_tracing", &ExtendedMCPServer::enableTracing)
        .def("set_thread_pool", &ExtendedMCPServer::setThreadPool)
        .def("enable_caching", &ExtendedMCPServer::enableCaching);
    
    py::class_<ExtendedMCPClient>(tinymcp_module, "ExtendedMCPClient")
        .def(py::init<const std::string&>())
        .def("enable_connection_pool", &ExtendedMCPClient::enableConnectionPool)
        .def("enable_batching", &ExtendedMCPClient::enableBatching)
        .def("set_retry_policy", &ExtendedMCPClient::setRetryPolicy);
    
    // Version info
    m.attr("__version__") = "1.0.0";
    m.attr("__author__") = "AI-SERVIS Team";
    m.attr("__tinymcp_version__") = "0.2.0";
}