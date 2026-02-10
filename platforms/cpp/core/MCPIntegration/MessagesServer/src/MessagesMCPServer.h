#pragma once

// Local includes
#include <Entity/Server.h>

// Standard library includes
#include <memory>
#include <string>

namespace MCPIntegration {

/**
 * @brief MCP Server for Messaging operations (SMS/MMS/Email)
 *
 * Provides MCP tools for sending and receiving messages across multiple channels,
 * queues outbound messages, and exposes basic status queries.
 */
class CMessagesMCPServer : public MCP::CMCPServer<CMessagesMCPServer> {
public:
    static constexpr const char* SERVER_NAME = "messages_mcp_server";
    static constexpr const char* SERVER_VERSION = "0.1.0";

    int Initialize() override;

private:
    friend class MCP::CMCPServer<CMessagesMCPServer>;
    CMessagesMCPServer() = default;
    static CMessagesMCPServer s_Instance;
};

} // namespace MCPIntegration

