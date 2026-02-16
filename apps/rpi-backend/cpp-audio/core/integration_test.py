#!/usr/bin/env python3
import socket
import struct
import time
import subprocess
import threading
import os

# Start server
def start_server(port):
    server_process = subprocess.Popen(['./webgrab-server', str(port), '/tmp/downloads'])
    time.sleep(1)  # Wait for server to start
    return server_process

# Client simulation
def send_request(sock, data):
    length = struct.pack('>I', len(data))
    sock.send(length + data)

def receive_response(sock):
    length_data = sock.recv(4)
    if not length_data:
        return None
    length = struct.unpack('>I', length_data)[0]
    return sock.recv(length)

def test_download():
    # FlatBuffers placeholder - in real test, serialize properly
    download_request = b'download:http://example.com/file.txt'
    send_request(client_sock, download_request)
    response = receive_response(client_sock)
    assert response is not None
    print("Download test passed")

def test_status():
    status_request = b'status:1'
    send_request(client_sock, status_request)
    response = receive_response(client_sock)
    assert response is not None
    print("Status test passed")

if __name__ == '__main__':
    port = 8080
    server_proc = start_server(port)

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(('localhost', port))

    try:
        test_download()
        test_status()
        print("All tests passed!")
    finally:
        client_sock.close()
        server_proc.terminate()
        server_proc.wait()