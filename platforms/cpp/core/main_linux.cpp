#include "HotReloadManager.h"
#include <dlfcn.h>
#include <iostream>
#include <thread>
#include <chrono>

typedef void* (*wg_create_client_t)(const char*, uint16_t);
typedef bool (*wg_download_t)(void*, const char*, uint32_t*);

int main() {
    HotReloadManager hrm("libwebgrab.so", []() {
        std::cout << "Shared library reloaded successfully\n";
    });

    if (!hrm.loadDll()) {
        return 1;
    }

    // Load function pointers
    auto createClient = (wg_create_client_t)dlsym(hrm.getDllHandle(), "wg_create_client");
    auto download = (wg_download_t)dlsym(hrm.getDllHandle(), "wg_download");
    if (!createClient || !download) {
        std::cerr << "Failed to load functions: " << dlerror() << "\n";
        return 1;
    }

    void* client = createClient("localhost", 8080);

    std::thread reloadThread([&]() {
        while (true) {
            hrm.reloadIfChanged();
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    });

    std::string command;
    while (std::getline(std::cin, command)) {
        if (command.rfind("download ", 0) == 0) {
            std::string url = command.substr(9);
            uint32_t sessionId;
            if (download(client, url.c_str(), &sessionId)) {
                std::cout << "Download started, ID: " << sessionId << "\n";
            }
        }
        // Handle other commands...
    }

    reloadThread.detach();
    return 0;
}