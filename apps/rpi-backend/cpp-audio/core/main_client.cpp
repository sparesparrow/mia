#include "WebGrabClient.h"
#include <iostream>
#include <string>
#include <sstream>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <host> <port>" << std::endl;
        return 1;
    }

    std::string host = argv[1];
    uint16_t port = static_cast<uint16_t>(std::stoi(argv[2]));

    WebGrabClient client(host, port);
    if (!client.connect()) {
        std::cerr << "Failed to connect to server" << std::endl;
        return 1;
    }

    std::cout << "Connected. Enter commands (download <url>, status <id>, abort <id>, quit):" << std::endl;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "download") {
            std::string url;
            iss >> url;
            uint32_t sessionId;
            if (!client.executeDownload(url, sessionId)) {
                std::cerr << "Failed to send download request" << std::endl;
            } else {
                std::cout << "Download started with session ID: " << sessionId << std::endl;
            }
        } else if (cmd == "status") {
            uint32_t id;
            iss >> id;
            std::string status;
            if (!client.executeStatus(id, status)) {
                std::cerr << "Failed to send status request" << std::endl;
            } else {
                std::cout << "Status for session " << id << ": " << status << std::endl;
            }
        } else if (cmd == "abort") {
            uint32_t id;
            iss >> id;
            if (!client.executeAbort(id)) {
                std::cerr << "Failed to send abort request" << std::endl;
            }
        } else if (cmd == "quit") {
            if (!client.executeQuit()) {
                std::cerr << "Failed to send quit" << std::endl;
            }
            break;
        } else {
            std::cout << "Unknown command" << std::endl;
        }
    }

    return 0;
}