#pragma once

// Forward declarations
class WebGrabClient;

// Standard library includes
#include <memory>
#include <string>
#include <mutex>

namespace MCPIntegration {

/**
 * @brief Wrapper for WebGrabClient to provide thread-safe access
 *
 * This class provides a thread-safe interface to the WebGrabClient,
 * allowing the MCP server to communicate with the WebGrab backend.
 */
class WebGrabClientWrapper {
public:
    WebGrabClientWrapper();
    ~WebGrabClientWrapper();

    /**
     * @brief Connect to WebGrab server
     *
     * @param host Server hostname
     * @param port Server port
     * @return true if connection successful, false otherwise
     */
    bool connect(const std::string& host, uint16_t port);

    /**
     * @brief Start a download
     *
     * @param url URL to download
     * @param sessionId Output parameter for session ID
     * @return true if download started successfully
     */
    bool download(const std::string& url, uint32_t& sessionId);

    /**
     * @brief Check download status
     *
     * @param sessionId Session ID to check
     * @param status Output parameter for status string
     * @return true if status retrieved successfully
     */
    bool status(uint32_t sessionId, std::string& status);

    /**
     * @brief Abort a download
     *
     * @param sessionId Session ID to abort
     * @return true if abort request sent successfully
     */
    bool abort(uint32_t sessionId);

private:
    std::unique_ptr<WebGrabClient> client;
    std::mutex mutex_;  // For thread safety
};

} // namespace MCPIntegration