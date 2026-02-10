#pragma once

// Local includes
#include <Entity/Server.h>

// Standard library includes
#include <memory>
#include <string>

namespace MCPIntegration {

/**
 * @brief MCP Server for WebGrab operations
 *
 * This server provides MCP tools for asynchronous file downloading,
 * status checking, and download abortion using the WebGrab backend.
 */
class CWebGrabMCPServer : public MCP::CMCPServer<CWebGrabMCPServer> {
public:
    static constexpr const char* SERVER_NAME = "webgrab_mcp_server";
    static constexpr const char* SERVER_VERSION = "1.0.0";

    /**
     * @brief Initialize the MCP server
     *
     * Sets up server information, registers capabilities and tools,
     * and initializes the WebGrab client connection.
     *
     * @return MCP error code (0 for success)
     */
    int Initialize() override;

private:
    friend class MCP::CMCPServer<CWebGrabMCPServer>;
    CWebGrabMCPServer() = default;
    static CWebGrabMCPServer s_Instance;

    // WebGrab client wrapper for communicating with WebGrab server
    class WebGrabClientWrapper;
    std::unique_ptr<WebGrabClientWrapper> webgrabClient;
};

} // namespace MCPIntegration