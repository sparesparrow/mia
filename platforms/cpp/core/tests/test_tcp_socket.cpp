#include "test_tcp_socket.h"
#include "../TcpSocket.h"
#include "../TcpListener.h"
#include <thread>
#include <chrono>
#include <cassert>
#include <cstring>

void testTcpSocket() {
    // Test 1: Create TCP listener
    TcpListener listener(9999);
    assert(listener.start());
    
    // Test 2: Create TCP socket and connect (in a separate thread)
    std::thread serverThread([&listener]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        auto clientSocket = listener.accept();
        assert(clientSocket != nullptr);
        assert(clientSocket->isConnected());
    });
    
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    
    TcpSocket client("localhost", 9999);
    assert(client.connect());
    assert(client.isConnected());
    
    // Test 3: Send and receive data
    const char* testData = "Hello, Server!";
    assert(client.send(testData, strlen(testData)));
    
    // Test 4: Disconnect
    client.disconnect();
    assert(!client.isConnected());
    
    serverThread.join();
}
