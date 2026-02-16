#include "test_orchestrator.h"
#include "../CoreOrchestrator.h"
#include <cassert>
#include <iostream>

void testOrchestrator() {
    using namespace WebGrab;
    
    // Test 1: Create orchestrator
    CoreOrchestrator orchestrator(9997);
    
    // Test 2: Register a service
    std::vector<std::string> capabilities = {"test", "capability"};
    bool registered = orchestrator.registerService("test-service", "localhost", 9996, capabilities);
    assert(registered);
    
    // Test 3: List services
    auto services = orchestrator.listServices();
    assert(services.size() == 1);
    assert(services[0].name == "test-service");
    
    // Test 4: Process a voice command
    std::string result = orchestrator.processVoiceCommand("test command", "test_interface");
    assert(!result.empty());
    
    std::cout << "  Orchestrator processed command: " << result << std::endl;
}
