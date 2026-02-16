#pragma once

// Local includes
#include <Task/BasicTask.h>
#include <Message/Request.h>

// Standard library includes
#include <string>

namespace MCPIntegration {

class WebGrabClientWrapper;

/**
 * @brief MCP tool for aborting downloads
 *
 * This tool handles abort requests from MCP clients,
 * allowing cancellation of running download sessions.
 */
class AbortTask : public MCP::ProcessCallToolRequest {
public:
    static constexpr const char* TOOL_NAME = "abort_download";
    static constexpr const char* TOOL_DESCRIPTION = "Abort a running download session.";
    static constexpr const char* TOOL_INPUT_SCHEMA = R"({
        "type": "object",
        "properties": {
            "session_id": {
                "type": "integer",
                "description": "The session ID of the download to abort"
            }
        },
        "required": ["session_id"]
    })";
    static constexpr const char* TOOL_ARGUMENT_SESSION_ID = "session_id";

    AbortTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper);

    std::shared_ptr<CMCPTask> Clone() const override;
    int Execute() override;
    int Cancel() override;

private:
    WebGrabClientWrapper* clientWrapper;
};

} // namespace MCPIntegration