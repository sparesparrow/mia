#include "WebGrabServer.h"
#include <iostream>
#include <string>
#include <thread>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <port> <working_dir>" << std::endl;
        return 1;
    }

    uint16_t port = static_cast<uint16_t>(std::stoi(argv[1]));
    std::string workingDir = argv[2];

    WebGrabServer server(port, workingDir);
    if (!server.start()) {
        std::cerr << "Failed to start server" << std::endl;
        return 1;
    }

    std::cout << "Server started on port " << port << ", working dir: " << workingDir << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl;

    // Keep running
    std::cin.get();

    server.stop();
    std::cout << "Server stopped" << std::endl;

    return 0;
}