#include "HardwareControlServer.h"
#include <csignal>
#include <iostream>
#include <atomic>
#include <thread>
#include <chrono>
#include <unistd.h>

namespace {

volatile std::sig_atomic_t g_stopSignal = 0;

void signal_handler(int signal) {
    if (g_stopSignal != 0) {
        ::_exit(128 + signal);
    }

    g_stopSignal = signal;
}

bool install_signal_handlers() {
    return std::signal(SIGINT, signal_handler) != SIG_ERR
        && std::signal(SIGTERM, signal_handler) != SIG_ERR
        && std::signal(SIGPIPE, SIG_IGN) != SIG_ERR;
}

bool stop_requested() {
    return g_stopSignal != 0;
}

} // namespace

int main(int argc, char* argv[]) {
    if (!install_signal_handlers()) {
        std::cerr << "Failed to install signal handlers" << std::endl;
        return 1;
    }

    try {
        // Create and start the hardware control server
        WebGrab::HardwareControlServer server;

        std::cout << "Hardware Control Server starting..." << std::endl;
        std::cout << "GPIO control available via TCP connections on port 8081" << std::endl;
        std::cout << "Example commands:" << std::endl;
        std::cout << "  Configure pin 17 as output: {\"pin\":17,\"direction\":\"output\"}" << std::endl;
        std::cout << "  Set pin 17 high: {\"pin\":17,\"value\":1}" << std::endl;
        std::cout << "  Configure pin 18 as input: {\"pin\":18,\"direction\":\"input\"}" << std::endl;
        std::cout << "  Read pin 18: {\"pin\":18}" << std::endl;
        std::cout << "Press Ctrl+C to stop" << std::endl;

        // Start the server (this will block until stopped)
        if (!server.Start()) {
            std::cerr << "Failed to start Hardware Control Server" << std::endl;
            return 1;
        }

        // Wait for stop signal
        while (!stop_requested()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

        std::cout << "Received shutdown signal " << g_stopSignal << ", stopping server..." << std::endl;

        // Stop the server
        server.Stop();

    } catch (const std::exception& e) {
        std::cerr << "Hardware Control Server failed: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}