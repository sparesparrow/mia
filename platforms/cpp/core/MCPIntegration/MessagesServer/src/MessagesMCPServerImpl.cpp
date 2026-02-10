#include "MessagesMCPServer.h"

// Third-party includes
#include <Public/Config.h>

// Standard library includes
#include <iostream>

namespace MCPIntegration {

static std::atomic_bool g_bStop{ false };
static void signal_handler(int) { g_bStop = true; }

int LaunchMessagesMCPServer();

int CMessagesMCPServer::Initialize() {
    MCP::Implementation serverInfo;
    serverInfo.strName = SERVER_NAME;
    serverInfo.strVersion = SERVER_VERSION;
    SetServerInfo(serverInfo);

    // Capabilities (tools will be added incrementally per channel)
    MCP::Tools tools; tools.bListChanged = true; // dynamic tool list
    RegisterServerToolsCapabilities(tools);

    MCP::Resources resources; resources.bListChanged = false; resources.bSubscribe = false;
    RegisterServerResourcesCapabilities(resources);

    // No tools registered yet in the base scaffold
    std::vector<MCP::Tool> vecTools;
    RegisterServerTools(vecTools, false);

    return MCP::ERRNO_OK;
}

static int run_server_loop() {
    auto& server = CMessagesMCPServer::GetInstance();
    int err = server.Initialize();
    if (MCP::ERRNO_OK != err) {
        std::cout << "Failed to initialize Messages MCP Server" << std::endl;
        return err;
    }
    err = server.Start();
    if (MCP::ERRNO_OK != err) {
        std::cout << "Failed to start Messages MCP Server" << std::endl;
        return err;
    }
    std::cout << "Messages MCP Server started successfully" << std::endl;
    while (!g_bStop) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    server.Stop();
    std::cout << "Messages MCP Server stopped" << std::endl;
    return MCP::ERRNO_OK;
}

int LaunchMessagesMCPServer() {
    auto& config = MCP::Config::GetInstance();
    int configErr = config.LoadFromFile("config.ini");
    if (MCP::ERRNO_OK != configErr) {
        std::cout << "Warning: Could not load config.ini, using defaults" << std::endl;
    }
    return run_server_loop();
}

} // namespace MCPIntegration

