// Standard library includes
#include <signal.h>

// Local includes
#include "WebGrabMCPServerImpl.cpp"

int main(int argc, char* argv[]) {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    return LaunchWebGrabMCPServer();
}