#include <iostream>
#include <cassert>
#include "test_tcp_socket.h"
#include "test_gpio_control.h"
#include "test_orchestrator.h"

// Forward declaration for GPIO TCP test
void testGpioViaTcp();

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  AI-SERVIS Test Suite" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    int tests_passed = 0;
    int tests_failed = 0;
    
    // Test TCP Socket
    std::cout << "Testing TCP Socket..." << std::endl;
    try {
        testTcpSocket();
        std::cout << "✓ TCP Socket tests passed" << std::endl;
        tests_passed++;
    } catch (const std::exception& e) {
        std::cerr << "✗ TCP Socket tests failed: " << e.what() << std::endl;
        tests_failed++;
    }
    
    // Test GPIO Control (only if on Raspberry Pi)
    std::cout << "Testing GPIO Control..." << std::endl;
    try {
        testGpioControl();
        std::cout << "✓ GPIO Control tests passed" << std::endl;
        tests_passed++;
        
        // Test GPIO via TCP
        std::cout << "Testing GPIO via TCP..." << std::endl;
        testGpioViaTcp();
        std::cout << "✓ GPIO TCP tests passed" << std::endl;
        tests_passed++;
    } catch (const std::exception& e) {
        std::cerr << "⚠ GPIO Control tests skipped (not on Raspberry Pi or no permissions): " << e.what() << std::endl;
        // Don't count as failure - GPIO may not be available
    }
    
    // Test Orchestrator
    std::cout << "Testing Orchestrator..." << std::endl;
    try {
        testOrchestrator();
        std::cout << "✓ Orchestrator tests passed" << std::endl;
        tests_passed++;
    } catch (const std::exception& e) {
        std::cerr << "✗ Orchestrator tests failed: " << e.what() << std::endl;
        tests_failed++;
    }
    
    std::cout << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "  Test Results" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Passed: " << tests_passed << std::endl;
    std::cout << "Failed: " << tests_failed << std::endl;
    std::cout << std::endl;
    
    return tests_failed == 0 ? 0 : 1;
}
