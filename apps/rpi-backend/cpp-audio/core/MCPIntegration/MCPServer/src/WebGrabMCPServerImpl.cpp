#include "WebGrabMCPServer.h"

// Local includes
#include "WebGrabClientWrapper.h"
#include "DownloadTask.h"
#include "StatusTask.h"
#include "AbortTask.h"
#include "GPIOTask.h"

// Third-party includes
#include <Public/Config.h>

// Standard library includes
#include <iostream>
#include <chrono>
#include <thread>
#include <atomic>
#include <signal.h>

namespace MCPIntegration {

std::atomic_bool g_bStop{ false };
void signal_handler(int signal) { g_bStop = true; }

int LaunchWebGrabMCPServer() {
    // 0. Load configuration
    auto& config = MCP::Config::GetInstance();
    int configErr = config.LoadFromFile("config.ini");
    if (MCP::ERRNO_OK != configErr) {
        std::cout << "Warning: Could not load config.ini, using defaults" << std::endl;
    }

    // 1. Configure the Server.
    auto& server = CWebGrabMCPServer::GetInstance();
    int iErrCode = server.Initialize();
    if (MCP::ERRNO_OK == iErrCode) {
        // 2. Start the Server.
        iErrCode = server.Start();
        if (MCP::ERRNO_OK == iErrCode) {
            std::cout << "WebGrab MCP Server started successfully" << std::endl;
            std::cout << "Press Ctrl+C to stop" << std::endl;

            // 3. Keep running until signal
            while (!g_bStop) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }

            // 4. Stop the Server.
            server.Stop();
            std::cout << "WebGrab MCP Server stopped" << std::endl;
        } else {
            std::cout << "Failed to start WebGrab MCP Server" << std::endl;
        }
    } else {
        std::cout << "Failed to initialize WebGrab MCP Server" << std::endl;
    }

    return iErrCode;
}

int CWebGrabMCPServer::Initialize() {
    // 1. Set the basic information of the Server.
    MCP::Implementation serverInfo;
    serverInfo.strName = SERVER_NAME;
    serverInfo.strVersion = SERVER_VERSION;
    SetServerInfo(serverInfo);

    // 2. Initialize WebGrab client wrapper
    webgrabClient = std::make_unique<WebGrabClientWrapper>();

    // Load configuration
    auto& config = MCP::Config::GetInstance();
    std::string host = config.GetValue("webgrab", "host", "localhost");
    uint16_t port = static_cast<uint16_t>(std::stoi(config.GetValue("webgrab", "port", "8080")));

    if (!webgrabClient->connect(host, port)) {
        return MCP::ERRNO_INTERNAL_ERROR;
    }

    // 3. Register the Server's capability declaration.
    MCP::Tools tools;
    tools.bListChanged = true;  // Tools can be added/removed dynamically
    RegisterServerToolsCapabilities(tools);

    // Register resource capabilities (not used for now)
    MCP::Resources resources;
    resources.bListChanged = false;
    resources.bSubscribe = false;
    RegisterServerResourcesCapabilities(resources);

    // 4. Register the descriptions of the Server's actual capabilities and their calling methods.
    std::vector<MCP::Tool> vecTools;

    // Download tool
    {
        MCP::Tool tool;
        tool.strName = DownloadTask::TOOL_NAME;
        tool.strDescription = DownloadTask::TOOL_DESCRIPTION;
        std::string strInputSchema = DownloadTask::TOOL_INPUT_SCHEMA;
        Json::Reader reader;
        Json::Value jInputSchema(Json::objectValue);
        if (!reader.parse(strInputSchema, jInputSchema) || !jInputSchema.isObject()) {
            return MCP::ERRNO_PARSE_ERROR;
        }
        tool.jInputSchema = jInputSchema;
        vecTools.push_back(tool);
    }

    // Status tool
    {
        MCP::Tool tool;
        tool.strName = StatusTask::TOOL_NAME;
        tool.strDescription = StatusTask::TOOL_DESCRIPTION;
        std::string strInputSchema = StatusTask::TOOL_INPUT_SCHEMA;
        Json::Reader reader;
        Json::Value jInputSchema(Json::objectValue);
        if (!reader.parse(strInputSchema, jInputSchema) || !jInputSchema.isObject()) {
            return MCP::ERRNO_PARSE_ERROR;
        }
        tool.jInputSchema = jInputSchema;
        vecTools.push_back(tool);
    }

    // Abort tool
    {
        MCP::Tool tool;
        tool.strName = AbortTask::TOOL_NAME;
        tool.strDescription = AbortTask::TOOL_DESCRIPTION;
        std::string strInputSchema = AbortTask::TOOL_INPUT_SCHEMA;
        Json::Reader reader;
        Json::Value jInputSchema(Json::objectValue);
        if (!reader.parse(strInputSchema, jInputSchema) || !jInputSchema.isObject()) {
            return MCP::ERRNO_PARSE_ERROR;
        }
        tool.jInputSchema = jInputSchema;
        vecTools.push_back(tool);
    }

    // GPIO control tool
    {
        MCP::Tool tool;
        tool.strName = GPIOTask::TOOL_NAME;
        tool.strDescription = GPIOTask::TOOL_DESCRIPTION;
        std::string strInputSchema = GPIOTask::TOOL_INPUT_SCHEMA;
        Json::Reader reader;
        Json::Value jInputSchema(Json::objectValue);
        if (!reader.parse(strInputSchema, jInputSchema) || !jInputSchema.isObject()) {
            return MCP::ERRNO_PARSE_ERROR;
        }
        tool.jInputSchema = jInputSchema;
        vecTools.push_back(tool);
    }

    RegisterServerTools(vecTools, false);

    // 5. Register the tasks for implementing the actual capabilities.
    auto spDownloadTask = std::make_shared<DownloadTask>(nullptr, webgrabClient.get());
    if (!spDownloadTask) {
        return MCP::ERRNO_INTERNAL_ERROR;
    }
    RegisterToolsTasks(DownloadTask::TOOL_NAME, spDownloadTask);

    auto spStatusTask = std::make_shared<StatusTask>(nullptr, webgrabClient.get());
    if (!spStatusTask) {
        return MCP::ERRNO_INTERNAL_ERROR;
    }
    RegisterToolsTasks(StatusTask::TOOL_NAME, spStatusTask);

    auto spAbortTask = std::make_shared<AbortTask>(nullptr, webgrabClient.get());
    if (!spAbortTask) {
        return MCP::ERRNO_INTERNAL_ERROR;
    }
    RegisterToolsTasks(AbortTask::TOOL_NAME, spAbortTask);

    auto spGPIOTask = std::make_shared<GPIOTask>(nullptr);
    if (!spGPIOTask) {
        return MCP::ERRNO_INTERNAL_ERROR;
    }
    RegisterToolsTasks(GPIOTask::TOOL_NAME, spGPIOTask);

    return MCP::ERRNO_OK;
}

} // namespace MCPIntegration