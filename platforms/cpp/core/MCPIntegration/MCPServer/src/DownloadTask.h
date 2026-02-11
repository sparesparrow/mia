#pragma once

// Local includes
#include <Task/BasicTask.h>
#include <Message/Request.h>

// Standard library includes
#include <string>

namespace MCPIntegration {

class WebGrabClientWrapper;

/**
 * @brief MCP tool for downloading files asynchronously
 *
 * This tool handles download requests from MCP clients, forwarding them
 * to the WebGrab backend and returning session IDs for progress tracking.
 */
class DownloadTask : public MCP::ProcessCallToolRequest {
public:
    static constexpr const char* TOOL_NAME = "download_file";
    static constexpr const char* TOOL_DESCRIPTION = "Download a file from a URL asynchronously. Returns a session ID for tracking progress.";
    static constexpr const char* TOOL_INPUT_SCHEMA = R"({
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the file to download"
            }
        },
        "required": ["url"]
    })";
    static constexpr const char* TOOL_ARGUMENT_URL = "url";

    DownloadTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper);

    std::shared_ptr<CMCPTask> Clone() const override;
    int Execute() override;
    int Cancel() override;

private:
    WebGrabClientWrapper* clientWrapper;
};

} // namespace MCPIntegration