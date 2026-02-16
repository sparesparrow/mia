// Standard library includes
#include <iostream>
#include <string>
#include <sstream>
#include <thread>
#include <chrono>
#include <atomic>
#include <signal.h>

// Third-party includes
#include <Transport/Transport.h>
#include <Session/Session.h>
#include <Message/Request.h>
#include <Public/Config.h>
#include <json/json.h>

std::atomic_bool g_bStop{ false };
void signal_handler(int signal) { g_bStop = true; }

/**
 * @brief Simple MCP client simulator for testing WebGrab MCP server
 *
 * This simulator provides a command-line interface to send MCP tool calls
 * to test the WebGrab MCP server's download functionality.
 */
class MCPClientSimulator {
public:
    MCPClientSimulator() {
        transport = std::make_unique<MCP::CStdioTransport>();
    }

    /**
     * @brief Initialize the simulator
     *
     * @return true if initialization successful, false otherwise
     */
    bool initialize() {
        // Initialize transport
        if (!transport->Initialize()) {
            std::cerr << "Failed to initialize transport" << std::endl;
            return false;
        }

        // Create session
        session = std::make_unique<MCP::CSession>(transport.get());
        if (!session->Initialize()) {
            std::cerr << "Failed to initialize session" << std::endl;
            return false;
        }

        return true;
    }

    /**
     * @brief Run the interactive simulator
     */
    void run() {
        std::cout << "=== WebGrab MCP Client Simulator ===" << std::endl;
        std::cout << "Available commands:" << std::endl;
        std::cout << "  download <url>     - Start a download" << std::endl;
        std::cout << "  status <session_id> - Check download status" << std::endl;
        std::cout << "  abort <session_id>  - Abort a download" << std::endl;
        std::cout << "  list               - List available tools" << std::endl;
        std::cout << "  quit               - Exit simulator" << std::endl;
        std::cout << std::endl;

        std::string line;
        while (!g_bStop && std::getline(std::cin, line)) {
            if (line.empty()) {
                continue;
            }

            std::istringstream iss(line);
            std::string cmd;
            iss >> cmd;

            if (cmd == "download") {
                std::string url;
                iss >> url;
                if (!url.empty()) {
                    sendDownloadRequest(url);
                } else {
                    std::cout << "Usage: download <url>" << std::endl;
                }
            } else if (cmd == "status") {
                uint32_t sessionId;
                iss >> sessionId;
                sendStatusRequest(sessionId);
            } else if (cmd == "abort") {
                uint32_t sessionId;
                iss >> sessionId;
                sendAbortRequest(sessionId);
            } else if (cmd == "list") {
                sendListToolsRequest();
            } else if (cmd == "quit") {
                break;
            } else {
                std::cout << "Unknown command: " << cmd << std::endl;
                printHelp();
            }
        }
    }

private:
    void printHelp() {
        std::cout << "Available commands:" << std::endl;
        std::cout << "  download <url>     - Start a download" << std::endl;
        std::cout << "  status <session_id> - Check download status" << std::endl;
        std::cout << "  abort <session_id>  - Abort a download" << std::endl;
        std::cout << "  list               - List available tools" << std::endl;
        std::cout << "  quit               - Exit simulator" << std::endl;
    }

    void sendDownloadRequest(const std::string& url) {
        Json::Value params;
        params["name"] = "download_file";
        params["arguments"]["url"] = url;

        sendToolCall("download_file", params);
    }

    void sendStatusRequest(uint32_t sessionId) {
        Json::Value params;
        params["name"] = "download_status";
        params["arguments"]["session_id"] = sessionId;

        sendToolCall("download_status", params);
    }

    void sendAbortRequest(uint32_t sessionId) {
        Json::Value params;
        params["name"] = "abort_download";
        params["arguments"]["session_id"] = sessionId;

        sendToolCall("abort_download", params);
    }

    void sendListToolsRequest() {
        Json::Value request;
        request["jsonrpc"] = "2.0";
        request["id"] = generateId();
        request["method"] = "tools/list";
        request["params"] = Json::Value(Json::objectValue);

        sendRequest(request);
    }

    void sendToolCall(const std::string& toolName, const Json::Value& params) {
        Json::Value request;
        request["jsonrpc"] = "2.0";
        request["id"] = generateId();
        request["method"] = "tools/call";
        request["params"] = params;

        sendRequest(request);
    }

    void sendRequest(const Json::Value& request) {
        Json::StreamWriterBuilder writer;
        std::string jsonStr = Json::writeString(writer, request);

        std::cout << jsonStr << std::endl;

        // In a real MCP client, we would send this via the transport
        // and wait for a response. For this simulator, we just print it.
    }

    std::string generateId() {
        static int counter = 1;
        return std::to_string(counter++);
    }

    std::unique_ptr<MCP::CTransport> transport;
    std::unique_ptr<MCP::CSession> session;
};

int main(int argc, char* argv[])
{
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    MCPClientSimulator simulator;

    if (!simulator.initialize())
    {
        return 1;
    }

    simulator.run();

    return 0;
}