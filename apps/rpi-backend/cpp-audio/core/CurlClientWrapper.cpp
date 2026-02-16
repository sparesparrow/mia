#include "CurlClientWrapper.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

bool CurlClient::init(const char* username, const char* password, bool verbose)
{
    curl_global_init(CURL_GLOBAL_DEFAULT);
    curl = curl_easy_init();

    auto optCode = CURLcode::CURLE_OK; // debugging purposes

    if (curl != nullptr)
    {
        optCode = curl_easy_setopt(curl, CURLOPT_CAINFO, "./cacert.pem");
        optCode = curl_easy_setopt(curl, CURLOPT_NOPROGRESS, 0L);
        if (verbose)
        {
            optCode = curl_easy_setopt(curl, CURLOPT_VERBOSE, 1);
        }

        if (username != nullptr && username[0] != '\0' && password != nullptr && password[0] != '\0')
        {
            optCode = curl_easy_setopt(curl, CURLOPT_USERNAME, username);
            optCode = curl_easy_setopt(curl, CURLOPT_PASSWORD, password);
        }
        return true;
    }

    curl_global_cleanup();
    return false;

};

CURLcode CurlClient::getFile(const char* url, const char* outFilename, const std::vector<std::string>& customHeaders, bool verifySSL)
{
    std::ofstream outFile(outFilename, std::ios::out | std::ios::binary);
    auto optCode = CURLcode::CURLE_OK; // debugging purposes
    struct curl_slist* chunk = nullptr;

    for (const std::string& header : customHeaders)
    {
        chunk = curl_slist_append(chunk, header.c_str());
    }

    if (outFile.fail())
    {
        std::cout << "Unable to open path provided" << std::endl;
        return CURLcode::CURLE_ABORTED_BY_CALLBACK;
    }

    if (!verifySSL)
    {
        optCode = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    }
    optCode = curl_easy_setopt(curl, CURLOPT_HTTPHEADER, chunk);
    optCode = curl_easy_setopt(curl, CURLOPT_URL, url);
    optCode = curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeData);
    optCode = curl_easy_setopt(curl, CURLOPT_WRITEDATA, &outFile);
    res = curl_easy_perform(curl);

    if (res == CURLE_OK)
    {
        int32_t responseCode = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &responseCode);
        std::cout << "HTTP response code: " << responseCode << std::endl;
    }

    return res;
}

CURLcode CurlClient::putFile(const char* url, const char* filename, const std::vector<std::string>& customHeaders, bool verifySSL)
{
    auto optCode = CURLcode::CURLE_OK; // debugging purposes
    std::unique_ptr<uint8_t> content = nullptr;
    struct curl_slist* chunk = nullptr;
    std::ifstream file(filename, std::ios::binary | std::ios::ate);

    if (file.fail())
    {
        std::cout << "Unable to open provided path" << std::endl;
        return CURLcode::CURLE_ABORTED_BY_CALLBACK;
    }

    std::streamsize file_size = file.tellg();
    std::vector<char> buffer(file_size);
    file.seekg(0, std::ios::beg);

    if (file.read(buffer.data(), file_size))
    {
        std::string str(buffer.begin(), buffer.end());

        std::vector<uint8_t> vec(str.begin(), str.end());

        content = std::unique_ptr<uint8_t>(new uint8_t[vec.size()]);

        copy(vec.begin(), vec.end(), content.get());
    }
    else
    {
        std::cout << "Unable to read file" << std::endl;
        return CURLcode::CURLE_ABORTED_BY_CALLBACK;
    }

    for (const std::string &header : customHeaders)
    {
        chunk = curl_slist_append(chunk, header.c_str());
    }

    if (!verifySSL)
    {
        optCode = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    }
    optCode = curl_easy_setopt(curl, CURLOPT_HTTPHEADER, chunk);
    optCode = curl_easy_setopt(curl, CURLOPT_URL, url);
    optCode = curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "PUT");
    optCode = curl_easy_setopt(curl, CURLOPT_POSTFIELDS, content.get());
    optCode = curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, static_cast<uint32_t>(file_size));
    res = curl_easy_perform(curl);

    if (res == CURLE_OK)
    {
        int32_t responseCode = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &responseCode);
        std::cout << "HTTP response code: " << responseCode << std::endl;
    }

    return res;
}

CURLcode CurlClient::delFile(const char* url, const std::vector<std::string>& customHeaders, bool verifySSL)
{
    auto optCode = CURLcode::CURLE_OK;
    struct curl_slist* chunk = nullptr;

    for (const std::string& header : customHeaders)
    {
        chunk = curl_slist_append(chunk, header.c_str());
    }

    if (!verifySSL)
    {
        optCode = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    }
    optCode = curl_easy_setopt(curl, CURLOPT_HTTPHEADER, chunk);
    optCode = curl_easy_setopt(curl, CURLOPT_URL, url);
    optCode = curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");
    res = curl_easy_perform(curl);

    if (res == CURLE_OK)
    {
        int32_t responseCode = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &responseCode);
        std::cout << "HTTP response code: " << responseCode << std::endl;
    }
    return res;
}

CURLcode CurlClient::getFileList(const char* url, std::string& output, const std::vector<std::string>& customHeaders, bool verifySSL)
{
    auto optCode = CURLcode::CURLE_OK; // debugging purposes
    struct curl_slist* chunk = nullptr;

    for (const std::string& header : customHeaders)
    {
        chunk = curl_slist_append(chunk, header.c_str());
    }

    if (!verifySSL)
    {
        optCode = curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
    }
    optCode = curl_easy_setopt(curl, CURLOPT_HTTPHEADER, chunk);
    optCode = curl_easy_setopt(curl, CURLOPT_URL, url);
    optCode = curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeDataToString);
    optCode = curl_easy_setopt(curl, CURLOPT_WRITEDATA, &output);
    res = curl_easy_perform(curl);

    if (res == CURLE_OK)
    {
        int32_t responseCode = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &responseCode);
        std::cout << "HTTP response code: " << responseCode << std::endl;
    }
    return res;
}

CurlClient::~CurlClient()
{
    curl_easy_cleanup(curl);
    curl_global_cleanup();
}

size_t CurlClient::writeData(void* ptr, size_t size, size_t nmemb, void* stream)
{
    static_cast<std::ofstream*>(stream)->write(static_cast<char*>(ptr), size * nmemb);
    if (static_cast<std::ofstream*>(stream)->bad())
    {
        return 0;
    }

    return size * nmemb;

}

size_t CurlClient::writeDataToString(void* ptr, size_t size, size_t nmemb, void* buff)
{
    static_cast<std::string*>(buff)->append(static_cast<char*>(ptr), size * nmemb);
    return size * nmemb;
};
