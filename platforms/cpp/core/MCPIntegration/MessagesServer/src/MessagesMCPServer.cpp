// Standard library includes
#include <signal.h>

// Local includes
#include "MessagesMCPServerImpl.cpp"

int main(int argc, char* argv[]) {
    signal(SIGINT, MCPIntegration::signal_handler);
    signal(SIGTERM, MCPIntegration::signal_handler);

    return MCPIntegration::LaunchMessagesMCPServer();
}

