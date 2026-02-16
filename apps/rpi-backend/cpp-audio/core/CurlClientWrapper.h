#pragma once
#include "curl/curl.h"
#include <string>
#include <vector>

class CurlClient
{
public:
    CurlClient() = default;
    bool init(const char* username, const char* password, bool verbose = true);
    CURLcode putFile(const char* url, const char* filename, const std::vector<std::string>& customHeaders, bool verifySSL);
    CURLcode getFile(const char* url, const char* outFilename, const std::vector<std::string>& customHeaders, bool verifySSL);
    CURLcode delFile(const char* url, const std::vector<std::string>& customHeaders, bool verifySSL);
    CURLcode getFileList(const char* url, std::string& output, const std::vector<std::string>& customHeaders, bool verifySSL);
    ~CurlClient();

private:
    CURL* curl = nullptr;
    CURLcode res = CURLcode::CURLE_OK;
    static size_t writeData(void* ptr, size_t size, size_t nmemb, void* stream);
    static size_t writeDataToString(void* ptr, size_t size, size_t nmemb, void* buff);
};
