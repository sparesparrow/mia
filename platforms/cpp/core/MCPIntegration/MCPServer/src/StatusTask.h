#pragma once

// Local includes
#include <Task/BasicTask.h>
#include <Message/Request.h>

// Standard library includes
#include <string>

namespace MCPIntegration {

class WebGrabClientWrapper;

/**
 * @brief MCP tool for checking download status
 *
 * This tool handles status requests from MCP clients, querying
 * the WebGrab backend for current download progress.
 */
class StatusTask : public MCP::ProcessCallToolRequest {
public:
    static constexpr const char* TOOL_NAME = "download_status";
    static constexpr const char* TOOL_DESCRIPTION = "Check the status of a download session.";
    static constexpr const char* TOOL_INPUT_SCHEMA = R"({
        "type": "object",
        "properties": {
            "session_id": {
                "type": "integer",
                "description": "The session ID of the download to check"
            }
        },
        "required": ["session_id"]
    })";
    static constexpr const char* TOOL_ARGUMENT_SESSION_ID = "session_id";

    StatusTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper);

    std::shared_ptr<CMCPTask> Clone() const override;
    int Execute() override;
    int Cancel() override;

private:
    WebGrabClientWrapper* clientWrapper;
};

} // namespace MCPIntegration