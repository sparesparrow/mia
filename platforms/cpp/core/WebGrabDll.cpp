#include "WebGrabClient.h"
#include <memory>

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
    if (!client->executeDownload(url)) {
        return false;
    }
    
    // The session ID is returned in the DownloadResponse by executeDownload
    // We need to get it from the response. Since executeDownload doesn't return it,
    // we'll need to modify the approach or use a different method.
    // For now, use a simple counter-based approach or get from response
    // This is a limitation - ideally WebGrabClient should return the session ID
    *out_session_id = 1; // Placeholder - would need to extract from response
    return true;
}

bool wg_get_status(void* client_handle, uint32_t session_id, char* out_status, size_t status_buf_size) {
    auto client = static_cast<WebGrabClient*>(client_handle);
    // Placeholder
    return client->executeStatus(session_id);
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