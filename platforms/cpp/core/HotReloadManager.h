#pragma once
#include <string>
#include <functional>
#include <memory>
#include <dlfcn.h>
#include <sys/stat.h>
#include <unistd.h>

class HotReloadManager {
public:
    using ReloadCallback = std::function<void()>;

    HotReloadManager(const std::string& dllPath, ReloadCallback callback);
    ~HotReloadManager();

    bool loadDll();
    void unloadDll();
    bool reloadIfChanged();
    void* getDllHandle() const { return dllHandle_; }

private:
    std::string dllPath_;
    void* dllHandle_;
    struct stat lastStat_;
    ReloadCallback callback_;

    bool getFileStat(const std::string& path, struct stat& st);
    bool hasFileChanged();
};