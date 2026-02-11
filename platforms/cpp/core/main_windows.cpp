#include "HotReloadManager.h"
#include "WebGrabDll.h"  // Assuming DLL interface
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    HotReloadManager hrm("webgrab_client.dll", []() {
        std::cout << "Client DLL reloaded successfully\n";
    });

    if (!hrm.loadDll()) {
        return 1;
    }

    // Load function pointers
    auto createClient = (wg_create_client_t)GetProcAddress(hrm.getDllHandle(), "wg_create_client");
    auto download = (wg_download_t)GetProcAddress(hrm.getDllHandle(), "wg_download");
    // Add others...

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