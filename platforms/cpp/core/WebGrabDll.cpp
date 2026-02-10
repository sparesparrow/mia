#include "WebGrabClient.h"
#include <memory>
#include <cstring>

// C API for shared library
extern "C" {

void* wg_create_client(const char* server_host, uint16_t server_port) {
    try {
        return new WebGrabClient(server_host, server_port);
    } catch (...) {
        return nullptr;
    }
}

void wg_destroy_client(void* client_handle) {
    delete static_cast<WebGrabClient*>(client_handle);
}

bool wg_download(void* client_handle, const char* url, uint32_t* out_session_id) {
    if (!client_handle || !out_session_id) return false;
    
    auto client = static_cast<WebGrabClient*>(client_handle);
    uint32_t sessionId = 0;
    if (!client->executeDownload(url, sessionId)) {
        return false;
    }
    
    *out_session_id = sessionId;
    return true;
}

bool wg_get_status(void* client_handle, uint32_t session_id, char* out_status, size_t status_buf_size) {
    if (!client_handle || !out_status || status_buf_size == 0) return false;
    
    auto client = static_cast<WebGrabClient*>(client_handle);
    std::string status;
    if (!client->executeStatus(session_id, status)) {
        return false;
    }
    
    if (status.length() >= status_buf_size) {
        return false; // Buffer too small
    }
    
    strncpy(out_status, status.c_str(), status_buf_size - 1);
    out_status[status_buf_size - 1] = '\0';
    return true;
}

bool wg_abort(void* client_handle, uint32_t session_id) {
    auto client = static_cast<WebGrabClient*>(client_handle);
    return client->executeAbort(session_id);
}

void wg_shutdown(void* client_handle) {
    auto client = static_cast<WebGrabClient*>(client_handle);
    client->executeQuit();
}

}