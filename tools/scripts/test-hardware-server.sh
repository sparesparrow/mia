#!/bin/bash

# Test script for Hardware Control Server
# This script tests the GPIO control functionality

echo "Testing Hardware Control Server..."

# Start the server in background
echo "Starting hardware server..."
./src/hardware/build/hardware-server &
SERVER_PID=$!

# Wait for server to start
sleep 2

echo "Testing GPIO control commands..."

# Test commands
echo "1. Configure pin 17 as output:"
echo '{"pin":17,"direction":"output"}' | nc localhost 8081

echo "2. Set pin 17 to HIGH:"
echo '{"pin":17,"value":1}' | nc localhost 8081

echo "3. Set pin 17 to LOW:"
echo '{"pin":17,"value":0}' | nc localhost 8081

echo "4. Configure pin 18 as input:"
echo '{"pin":18,"direction":"input"}' | nc localhost 8081

echo "5. Read pin 18 value:"
echo '{"pin":18}' | nc localhost 8081

# Stop the server
echo "Stopping server..."
kill $SERVER_PID

echo "Test completed."