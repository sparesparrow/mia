#include "HotReloadManager.h"
#include <iostream>

HotReloadManager::HotReloadManager(const std::string& dllPath, ReloadCallback callback)
    : dllPath_(dllPath), dllHandle_(nullptr), callback_(callback) {
    lastStat_ = {};
}

HotReloadManager::~HotReloadManager() {
    unloadDll();
}

bool HotReloadManager::loadDll() {
    dllHandle_ = dlopen(dllPath_.c_str(), RTLD_LAZY);
    if (!dllHandle_) {
        std::cerr << "Failed to load shared library: " << dllPath_ << " - " << dlerror() << "\n";
        return false;
    }
    getFileStat(dllPath_, lastStat_);
    return true;
}

void HotReloadManager::unloadDll() {
    if (dllHandle_) {
        dlclose(dllHandle_);
        dllHandle_ = nullptr;
    }
}

bool HotReloadManager::reloadIfChanged() {
    if (hasFileChanged()) {
        std::cout << "Shared library changed, reloading...\n";
        unloadDll();
        if (loadDll()) {
            callback_();  // Notify about reload
            return true;
        } else {
            std::cerr << "Failed to reload shared library\n";
            return false;
        }
    }
    return false;
}

bool HotReloadManager::getFileStat(const std::string& path, struct stat& st) {
    return stat(path.c_str(), &st) == 0;
}

bool HotReloadManager::hasFileChanged() {
    struct stat currentStat;
    if (!getFileStat(dllPath_, currentStat)) return false;

    return currentStat.st_mtime != lastStat_.st_mtime;
}