from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, save, load, rmdir, collect_libs
from conan.tools.build import check_min_cppstd
import os


class KernunMCPToolsConan(ConanFile):
    """Kernun MCP Tools - Proxy MCP integration for network security analysis"""
    
    name = "kernun-mcp-tools"
    version = "0.1.0"
    license = "Proprietary"
    author = "MIA Team"
    url = "https://github.com/sparesparrow/mia"
    homepage = "https://github.com/sparesparrow/mia"
    description = "MCP integration for Kernun proxy network security analysis tools"
    topics = ("mcp", "proxy", "network-security", "traffic-analysis", "tls")
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_demo": [True, False],
        "with_tests": [True, False],
        "enable_logging": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_demo": False,
        "with_tests": False,
        "enable_logging": True
    }
    
    # Source path configuration - adjust based on Kernun source location
    _kernun_source_path = None  # Set during source() or via environment
    
    @property
    def _min_cppstd(self):
        return "17"
    
    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
    
    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def layout(self):
        cmake_layout(self)
    
    def requirements(self):
        # Core dependencies for MCP and proxy functionality
        self.requires("jsoncpp/1.9.5")
        self.requires("openssl/3.3.2")
        self.requires("libcurl/8.10.1")
        
        if self.options.enable_logging:
            self.requires("spdlog/1.13.0")
    
    def build_requirements(self):
        self.tool_requires("cmake/3.28.1")
        if self.options.with_tests:
            self.requires("gtest/1.14.0")
    
    def export_sources(self):
        # Export local wrapper sources
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "src/*", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "include/*", src=self.recipe_folder, dst=self.export_sources_folder)
    
    def source(self):
        # Create wrapper CMakeLists.txt if Kernun sources are available
        # Otherwise, create stub implementation for development
        self._create_wrapper_sources()
    
    def _create_wrapper_sources(self):
        """Create C++ wrapper sources for Kernun MCP tools"""
        
        # Create include directory structure
        include_dir = os.path.join(self.source_folder, "include", "kernun_mcp")
        os.makedirs(include_dir, exist_ok=True)
        
        # Create src directory
        src_dir = os.path.join(self.source_folder, "src")
        os.makedirs(src_dir, exist_ok=True)
        
        # Main header file
        header_content = '''#pragma once

#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <json/json.h>

#ifdef KERNUN_MCP_SHARED
    #ifdef KERNUN_MCP_EXPORTS
        #define KERNUN_MCP_API __attribute__((visibility("default")))
    #else
        #define KERNUN_MCP_API
    #endif
#else
    #define KERNUN_MCP_API
#endif

namespace kernun {
namespace mcp {

/**
 * @brief Traffic analysis result structure
 */
struct TrafficAnalysis {
    std::string session_id;
    std::string source_ip;
    std::string dest_ip;
    int source_port;
    int dest_port;
    std::string protocol;
    size_t bytes_sent;
    size_t bytes_received;
    std::vector<std::string> detected_threats;
    double risk_score;
};

/**
 * @brief Session inspection result
 */
struct SessionInfo {
    std::string session_id;
    std::string state;
    std::string client_info;
    std::string server_info;
    int64_t start_time;
    int64_t last_activity;
    std::string tls_version;
    std::string cipher_suite;
};

/**
 * @brief TLS policy configuration
 */
struct TLSPolicy {
    std::string policy_id;
    std::string name;
    std::vector<std::string> allowed_ciphers;
    std::vector<std::string> allowed_protocols;
    bool require_client_cert;
    bool enable_ocsp_stapling;
};

/**
 * @brief Proxy rule definition
 */
struct ProxyRule {
    std::string rule_id;
    std::string name;
    std::string action;  // "allow", "deny", "log", "inspect"
    std::string source_pattern;
    std::string dest_pattern;
    int priority;
    bool enabled;
};

/**
 * @brief Clearweb category entry
 */
struct ClearwebCategory {
    std::string domain;
    std::string category;
    std::string subcategory;
    double confidence;
    int64_t last_updated;
};

/**
 * @brief MCP Tool result wrapper
 */
struct ToolResult {
    bool success;
    std::string message;
    Json::Value data;
};

/**
 * @brief Callback type for async operations
 */
using ToolCallback = std::function<void(const ToolResult&)>;

/**
 * @brief Kernun Proxy MCP Server
 * 
 * Exposes Kernun proxy functionality as MCP tools:
 * - analyze_traffic: Network traffic analysis
 * - inspect_session: Session inspection
 * - modify_tls_policy: TLS policy management
 * - update_proxy_rules: Firewall rules management
 * - update_clearweb_database: Content categorization
 */
class KERNUN_MCP_API ProxyMCPServer {
public:
    ProxyMCPServer();
    ~ProxyMCPServer();
    
    // Prevent copying
    ProxyMCPServer(const ProxyMCPServer&) = delete;
    ProxyMCPServer& operator=(const ProxyMCPServer&) = delete;
    
    /**
     * @brief Initialize the MCP server
     * @param config_path Path to configuration file
     * @return true on success
     */
    bool initialize(const std::string& config_path = "");
    
    /**
     * @brief Start the MCP server
     * @param port Port to listen on (default: 3000)
     * @return true on success
     */
    bool start(int port = 3000);
    
    /**
     * @brief Stop the MCP server
     */
    void stop();
    
    /**
     * @brief Check if server is running
     */
    bool isRunning() const;
    
    // MCP Tool implementations
    
    /**
     * @brief Analyze network traffic
     * @param session_id Optional session ID to filter
     * @param time_range_seconds Time range to analyze
     * @return Traffic analysis result
     */
    ToolResult analyzeTraffic(const std::string& session_id = "", 
                               int time_range_seconds = 300);
    
    /**
     * @brief Inspect a specific session
     * @param session_id Session identifier
     * @return Session information
     */
    ToolResult inspectSession(const std::string& session_id);
    
    /**
     * @brief List all active sessions
     * @return List of session info
     */
    ToolResult listSessions();
    
    /**
     * @brief Modify TLS policy
     * @param policy_id Policy to modify
     * @param updates JSON object with updates
     * @return Operation result
     */
    ToolResult modifyTLSPolicy(const std::string& policy_id, 
                                const Json::Value& updates);
    
    /**
     * @brief Get current TLS policies
     * @return List of TLS policies
     */
    ToolResult getTLSPolicies();
    
    /**
     * @brief Update proxy rules
     * @param rules Vector of rules to update/add
     * @return Operation result
     */
    ToolResult updateProxyRules(const std::vector<ProxyRule>& rules);
    
    /**
     * @brief Get current proxy rules
     * @return List of proxy rules
     */
    ToolResult getProxyRules();
    
    /**
     * @brief Delete proxy rule
     * @param rule_id Rule to delete
     * @return Operation result
     */
    ToolResult deleteProxyRule(const std::string& rule_id);
    
    /**
     * @brief Update clearweb database entries
     * @param entries Vector of category entries
     * @return Operation result
     */
    ToolResult updateClearwebDatabase(const std::vector<ClearwebCategory>& entries);
    
    /**
     * @brief Lookup domain category
     * @param domain Domain to lookup
     * @return Category information
     */
    ToolResult lookupDomainCategory(const std::string& domain);
    
    /**
     * @brief Get server statistics
     * @return Server statistics JSON
     */
    ToolResult getStatistics();

private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

/**
 * @brief MCP Client for connecting to Kernun proxy MCP server
 */
class KERNUN_MCP_API ProxyMCPClient {
public:
    ProxyMCPClient();
    ~ProxyMCPClient();
    
    /**
     * @brief Connect to MCP server
     * @param host Server host
     * @param port Server port
     * @return true on success
     */
    bool connect(const std::string& host, int port = 3000);
    
    /**
     * @brief Disconnect from server
     */
    void disconnect();
    
    /**
     * @brief Check connection status
     */
    bool isConnected() const;
    
    /**
     * @brief Call MCP tool
     * @param tool_name Name of the tool
     * @param arguments Tool arguments as JSON
     * @return Tool result
     */
    ToolResult callTool(const std::string& tool_name, 
                        const Json::Value& arguments);
    
    /**
     * @brief Call MCP tool asynchronously
     * @param tool_name Name of the tool
     * @param arguments Tool arguments
     * @param callback Callback for result
     */
    void callToolAsync(const std::string& tool_name,
                       const Json::Value& arguments,
                       ToolCallback callback);
    
    /**
     * @brief List available tools
     * @return List of tool names and descriptions
     */
    ToolResult listTools();

private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

} // namespace mcp
} // namespace kernun
'''
        save(self, os.path.join(include_dir, "kernun_mcp.h"), header_content)
        
        # Implementation file
        impl_content = '''#include "kernun_mcp/kernun_mcp.h"

#ifdef KERNUN_MCP_ENABLE_LOGGING
#include <spdlog/spdlog.h>
#endif

#include <atomic>
#include <thread>
#include <mutex>
#include <condition_variable>

namespace kernun {
namespace mcp {

// Server Implementation
class ProxyMCPServer::Impl {
public:
    std::atomic<bool> running{false};
    int port{3000};
    std::string config_path;
    std::mutex mutex;
    std::condition_variable cv;
    std::thread server_thread;
    
    // Simulated data stores (replace with real Kernun integration)
    std::vector<TLSPolicy> tls_policies;
    std::vector<ProxyRule> proxy_rules;
    std::vector<ClearwebCategory> clearweb_db;
};

ProxyMCPServer::ProxyMCPServer() : pImpl(std::make_unique<Impl>()) {
#ifdef KERNUN_MCP_ENABLE_LOGGING
    spdlog::info("Kernun MCP Server created");
#endif
}

ProxyMCPServer::~ProxyMCPServer() {
    stop();
}

bool ProxyMCPServer::initialize(const std::string& config_path) {
    pImpl->config_path = config_path;
    
    // Initialize default TLS policy
    TLSPolicy default_policy;
    default_policy.policy_id = "default";
    default_policy.name = "Default TLS Policy";
    default_policy.allowed_protocols = {"TLSv1.2", "TLSv1.3"};
    default_policy.allowed_ciphers = {"TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"};
    default_policy.require_client_cert = false;
    default_policy.enable_ocsp_stapling = true;
    pImpl->tls_policies.push_back(default_policy);
    
#ifdef KERNUN_MCP_ENABLE_LOGGING
    spdlog::info("Kernun MCP Server initialized with config: {}", 
                 config_path.empty() ? "(default)" : config_path);
#endif
    return true;
}

bool ProxyMCPServer::start(int port) {
    if (pImpl->running) return false;
    
    pImpl->port = port;
    pImpl->running = true;
    
#ifdef KERNUN_MCP_ENABLE_LOGGING
    spdlog::info("Kernun MCP Server started on port {}", port);
#endif
    return true;
}

void ProxyMCPServer::stop() {
    if (!pImpl->running) return;
    
    pImpl->running = false;
    pImpl->cv.notify_all();
    
    if (pImpl->server_thread.joinable()) {
        pImpl->server_thread.join();
    }
    
#ifdef KERNUN_MCP_ENABLE_LOGGING
    spdlog::info("Kernun MCP Server stopped");
#endif
}

bool ProxyMCPServer::isRunning() const {
    return pImpl->running;
}

ToolResult ProxyMCPServer::analyzeTraffic(const std::string& session_id, 
                                           int time_range_seconds) {
    ToolResult result;
    result.success = true;
    result.message = "Traffic analysis complete";
    
    // Create sample analysis data
    TrafficAnalysis analysis;
    analysis.session_id = session_id.empty() ? "all" : session_id;
    analysis.bytes_sent = 1024 * 1024;  // 1MB
    analysis.bytes_received = 2048 * 1024;  // 2MB
    analysis.risk_score = 0.15;
    
    result.data["session_id"] = analysis.session_id;
    result.data["bytes_sent"] = static_cast<Json::UInt64>(analysis.bytes_sent);
    result.data["bytes_received"] = static_cast<Json::UInt64>(analysis.bytes_received);
    result.data["risk_score"] = analysis.risk_score;
    result.data["time_range_seconds"] = time_range_seconds;
    
    return result;
}

ToolResult ProxyMCPServer::inspectSession(const std::string& session_id) {
    ToolResult result;
    
    if (session_id.empty()) {
        result.success = false;
        result.message = "Session ID required";
        return result;
    }
    
    result.success = true;
    result.message = "Session inspection complete";
    
    SessionInfo info;
    info.session_id = session_id;
    info.state = "active";
    info.tls_version = "TLSv1.3";
    info.cipher_suite = "TLS_AES_256_GCM_SHA384";
    
    result.data["session_id"] = info.session_id;
    result.data["state"] = info.state;
    result.data["tls_version"] = info.tls_version;
    result.data["cipher_suite"] = info.cipher_suite;
    
    return result;
}

ToolResult ProxyMCPServer::listSessions() {
    ToolResult result;
    result.success = true;
    result.message = "Sessions listed";
    result.data["sessions"] = Json::Value(Json::arrayValue);
    return result;
}

ToolResult ProxyMCPServer::modifyTLSPolicy(const std::string& policy_id, 
                                            const Json::Value& updates) {
    ToolResult result;
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    for (auto& policy : pImpl->tls_policies) {
        if (policy.policy_id == policy_id) {
            if (updates.isMember("name")) {
                policy.name = updates["name"].asString();
            }
            if (updates.isMember("require_client_cert")) {
                policy.require_client_cert = updates["require_client_cert"].asBool();
            }
            result.success = true;
            result.message = "Policy updated";
            return result;
        }
    }
    
    result.success = false;
    result.message = "Policy not found: " + policy_id;
    return result;
}

ToolResult ProxyMCPServer::getTLSPolicies() {
    ToolResult result;
    result.success = true;
    result.message = "Policies retrieved";
    
    Json::Value policies(Json::arrayValue);
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    for (const auto& policy : pImpl->tls_policies) {
        Json::Value p;
        p["policy_id"] = policy.policy_id;
        p["name"] = policy.name;
        p["require_client_cert"] = policy.require_client_cert;
        p["enable_ocsp_stapling"] = policy.enable_ocsp_stapling;
        policies.append(p);
    }
    
    result.data["policies"] = policies;
    return result;
}

ToolResult ProxyMCPServer::updateProxyRules(const std::vector<ProxyRule>& rules) {
    ToolResult result;
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    for (const auto& new_rule : rules) {
        bool found = false;
        for (auto& existing : pImpl->proxy_rules) {
            if (existing.rule_id == new_rule.rule_id) {
                existing = new_rule;
                found = true;
                break;
            }
        }
        if (!found) {
            pImpl->proxy_rules.push_back(new_rule);
        }
    }
    
    result.success = true;
    result.message = "Rules updated";
    result.data["count"] = static_cast<int>(rules.size());
    return result;
}

ToolResult ProxyMCPServer::getProxyRules() {
    ToolResult result;
    result.success = true;
    result.message = "Rules retrieved";
    
    Json::Value rules(Json::arrayValue);
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    for (const auto& rule : pImpl->proxy_rules) {
        Json::Value r;
        r["rule_id"] = rule.rule_id;
        r["name"] = rule.name;
        r["action"] = rule.action;
        r["source_pattern"] = rule.source_pattern;
        r["dest_pattern"] = rule.dest_pattern;
        r["priority"] = rule.priority;
        r["enabled"] = rule.enabled;
        rules.append(r);
    }
    
    result.data["rules"] = rules;
    return result;
}

ToolResult ProxyMCPServer::deleteProxyRule(const std::string& rule_id) {
    ToolResult result;
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    auto it = std::remove_if(pImpl->proxy_rules.begin(), pImpl->proxy_rules.end(),
                             [&rule_id](const ProxyRule& r) { return r.rule_id == rule_id; });
    
    if (it != pImpl->proxy_rules.end()) {
        pImpl->proxy_rules.erase(it, pImpl->proxy_rules.end());
        result.success = true;
        result.message = "Rule deleted";
    } else {
        result.success = false;
        result.message = "Rule not found: " + rule_id;
    }
    
    return result;
}

ToolResult ProxyMCPServer::updateClearwebDatabase(const std::vector<ClearwebCategory>& entries) {
    ToolResult result;
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    for (const auto& entry : entries) {
        bool found = false;
        for (auto& existing : pImpl->clearweb_db) {
            if (existing.domain == entry.domain) {
                existing = entry;
                found = true;
                break;
            }
        }
        if (!found) {
            pImpl->clearweb_db.push_back(entry);
        }
    }
    
    result.success = true;
    result.message = "Clearweb database updated";
    result.data["count"] = static_cast<int>(entries.size());
    return result;
}

ToolResult ProxyMCPServer::lookupDomainCategory(const std::string& domain) {
    ToolResult result;
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    for (const auto& entry : pImpl->clearweb_db) {
        if (entry.domain == domain) {
            result.success = true;
            result.message = "Domain found";
            result.data["domain"] = entry.domain;
            result.data["category"] = entry.category;
            result.data["subcategory"] = entry.subcategory;
            result.data["confidence"] = entry.confidence;
            return result;
        }
    }
    
    result.success = false;
    result.message = "Domain not found in database";
    return result;
}

ToolResult ProxyMCPServer::getStatistics() {
    ToolResult result;
    result.success = true;
    result.message = "Statistics retrieved";
    
    std::lock_guard<std::mutex> lock(pImpl->mutex);
    
    result.data["running"] = pImpl->running.load();
    result.data["port"] = pImpl->port;
    result.data["tls_policies_count"] = static_cast<int>(pImpl->tls_policies.size());
    result.data["proxy_rules_count"] = static_cast<int>(pImpl->proxy_rules.size());
    result.data["clearweb_entries_count"] = static_cast<int>(pImpl->clearweb_db.size());
    
    return result;
}

// Client Implementation
class ProxyMCPClient::Impl {
public:
    std::string host;
    int port{3000};
    std::atomic<bool> connected{false};
};

ProxyMCPClient::ProxyMCPClient() : pImpl(std::make_unique<Impl>()) {}

ProxyMCPClient::~ProxyMCPClient() {
    disconnect();
}

bool ProxyMCPClient::connect(const std::string& host, int port) {
    pImpl->host = host;
    pImpl->port = port;
    pImpl->connected = true;
    
#ifdef KERNUN_MCP_ENABLE_LOGGING
    spdlog::info("Connected to Kernun MCP Server at {}:{}", host, port);
#endif
    return true;
}

void ProxyMCPClient::disconnect() {
    pImpl->connected = false;
}

bool ProxyMCPClient::isConnected() const {
    return pImpl->connected;
}

ToolResult ProxyMCPClient::callTool(const std::string& tool_name, 
                                     const Json::Value& arguments) {
    ToolResult result;
    
    if (!pImpl->connected) {
        result.success = false;
        result.message = "Not connected to server";
        return result;
    }
    
    // Placeholder - in real implementation, this would make RPC call
    result.success = true;
    result.message = "Tool called: " + tool_name;
    result.data["tool"] = tool_name;
    result.data["arguments"] = arguments;
    
    return result;
}

void ProxyMCPClient::callToolAsync(const std::string& tool_name,
                                    const Json::Value& arguments,
                                    ToolCallback callback) {
    std::thread([this, tool_name, arguments, callback]() {
        auto result = callTool(tool_name, arguments);
        if (callback) {
            callback(result);
        }
    }).detach();
}

ToolResult ProxyMCPClient::listTools() {
    ToolResult result;
    result.success = true;
    result.message = "Available tools";
    
    Json::Value tools(Json::arrayValue);
    
    Json::Value t1;
    t1["name"] = "analyze_traffic";
    t1["description"] = "Analyze network traffic for security threats";
    tools.append(t1);
    
    Json::Value t2;
    t2["name"] = "inspect_session";
    t2["description"] = "Inspect a specific network session";
    tools.append(t2);
    
    Json::Value t3;
    t3["name"] = "modify_tls_policy";
    t3["description"] = "Modify TLS/SSL policy configuration";
    tools.append(t3);
    
    Json::Value t4;
    t4["name"] = "update_proxy_rules";
    t4["description"] = "Update firewall and proxy rules";
    tools.append(t4);
    
    Json::Value t5;
    t5["name"] = "update_clearweb_database";
    t5["description"] = "Update content categorization database";
    tools.append(t5);
    
    result.data["tools"] = tools;
    return result;
}

} // namespace mcp
} // namespace kernun
'''
        save(self, os.path.join(src_dir, "kernun_mcp.cpp"), impl_content)
        
        # Create CMakeLists.txt
        cmake_content = '''cmake_minimum_required(VERSION 3.15)
project(kernun-mcp-tools VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(KERNUN_MCP_BUILD_SHARED "Build shared library" OFF)
option(KERNUN_MCP_BUILD_DEMO "Build demo application" OFF)
option(KERNUN_MCP_BUILD_TESTS "Build tests" OFF)
option(KERNUN_MCP_ENABLE_LOGGING "Enable logging support" ON)

# Find dependencies
find_package(jsoncpp REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(CURL REQUIRED)

if(KERNUN_MCP_ENABLE_LOGGING)
    find_package(spdlog REQUIRED)
endif()

# Source files
set(KERNUN_MCP_HEADERS
    include/kernun_mcp/kernun_mcp.h
)

set(KERNUN_MCP_SOURCES
    src/kernun_mcp.cpp
)

# Create library
if(KERNUN_MCP_BUILD_SHARED)
    add_library(kernun-mcp-tools SHARED ${KERNUN_MCP_SOURCES})
    target_compile_definitions(kernun-mcp-tools PUBLIC KERNUN_MCP_SHARED)
    target_compile_definitions(kernun-mcp-tools PRIVATE KERNUN_MCP_EXPORTS)
else()
    add_library(kernun-mcp-tools STATIC ${KERNUN_MCP_SOURCES})
endif()

# Include directories
target_include_directories(kernun-mcp-tools PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Link dependencies
target_link_libraries(kernun-mcp-tools PUBLIC
    JsonCpp::JsonCpp
    OpenSSL::SSL
    OpenSSL::Crypto
    CURL::libcurl
)

if(KERNUN_MCP_ENABLE_LOGGING)
    target_compile_definitions(kernun-mcp-tools PUBLIC KERNUN_MCP_ENABLE_LOGGING)
    target_link_libraries(kernun-mcp-tools PUBLIC spdlog::spdlog)
endif()

# Demo application
if(KERNUN_MCP_BUILD_DEMO)
    add_executable(kernun-mcp-demo demo/main.cpp)
    target_link_libraries(kernun-mcp-demo PRIVATE kernun-mcp-tools)
endif()

# Tests
if(KERNUN_MCP_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    
    add_executable(kernun-mcp-tests tests/test_mcp.cpp)
    target_link_libraries(kernun-mcp-tests PRIVATE 
        kernun-mcp-tools 
        GTest::gtest_main
    )
    
    include(GoogleTest)
    gtest_discover_tests(kernun-mcp-tests)
endif()

# Installation
include(GNUInstallDirs)

install(TARGETS kernun-mcp-tools
    EXPORT kernun-mcp-tools-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/kernun_mcp
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT kernun-mcp-tools-targets
    FILE kernun-mcp-tools-targets.cmake
    NAMESPACE kernun::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/kernun-mcp-tools
)

# Package config
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/kernun-mcp-tools-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/kernun-mcp-tools-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/kernun-mcp-tools
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/kernun-mcp-tools-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/kernun-mcp-tools-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/kernun-mcp-tools-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/kernun-mcp-tools
)
'''
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)
        
        # Create cmake config template
        cmake_dir = os.path.join(self.source_folder, "cmake")
        os.makedirs(cmake_dir, exist_ok=True)
        
        config_template = '''@PACKAGE_INIT@

include("${CMAKE_CURRENT_LIST_DIR}/kernun-mcp-tools-targets.cmake")

check_required_components(kernun-mcp-tools)
'''
        save(self, os.path.join(cmake_dir, "kernun-mcp-tools-config.cmake.in"), config_template)
    
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["KERNUN_MCP_BUILD_SHARED"] = self.options.shared
        tc.variables["KERNUN_MCP_BUILD_DEMO"] = self.options.with_demo
        tc.variables["KERNUN_MCP_BUILD_TESTS"] = self.options.with_tests
        tc.variables["KERNUN_MCP_ENABLE_LOGGING"] = self.options.enable_logging
        tc.generate()
        
        deps = CMakeDeps(self)
        deps.generate()
    
    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_folder)
        cmake.build()
        
        if self.options.with_tests:
            cmake.test()
    
    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        
        # Remove CMake files from lib folder
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
    
    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kernun-mcp-tools")
        self.cpp_info.set_property("cmake_target_name", "kernun::mcp-tools")
        
        # Library name
        self.cpp_info.libs = ["kernun-mcp-tools"]
        
        # Defines
        if self.options.shared:
            self.cpp_info.defines.append("KERNUN_MCP_SHARED")
        
        if self.options.enable_logging:
            self.cpp_info.defines.append("KERNUN_MCP_ENABLE_LOGGING")
        
        # System libraries
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "crypt32"]
        
        # Backward compatibility
        self.cpp_info.names["cmake_find_package"] = "kernun-mcp-tools"
        self.cpp_info.names["cmake_find_package_multi"] = "kernun-mcp-tools"
