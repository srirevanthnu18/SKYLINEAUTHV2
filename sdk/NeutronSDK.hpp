/*
 * Neutron SDK - C++ Authentication Library
 * =========================================
 * Use this SDK to authenticate users in your C++ application.
 * Requires: libcurl, nlohmann/json
 * 
 * Usage:
 *     NeutronAuth auth;
 *     auto result = auth.login("username", "password");
 *     
 *     if (result["success"].get<bool>())
 *         std::cout << "Welcome, " << result["user"]["username"] << "!" << std::endl;
 *     else
 *         std::cout << "Error: " << result["error"] << std::endl;
 */

#ifndef NEUTRON_SDK_HPP
#define NEUTRON_SDK_HPP

#include <string>
#include <curl/curl.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

class NeutronAuth {
private:
    // Pre-configured credentials for your application
    const std::string api_url = "{{API_URL}}";
    const std::string app_secret = "{{APP_SECRET}}";
    const std::string app_name = "{{APP_NAME}}";
    const std::string version = "{{VERSION}}";

    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
        userp->append((char*)contents, size * nmemb);
        return size * nmemb;
    }

    std::string getHWID() {
        #ifdef _WIN32
            char buffer[256];
            DWORD volumeSerialNumber;
            if (GetVolumeInformationA("C:\\", NULL, 0, &volumeSerialNumber, NULL, NULL, NULL, 0)) {
                sprintf(buffer, "%lu", volumeSerialNumber);
                return std::string(buffer);
            }
        #endif
        return "unknown";
    }

    json httpPost(const std::string& endpoint, const json& payload) {
        CURL* curl = curl_easy_init();
        std::string response;
        
        if (curl) {
            std::string url = api_url + endpoint;
            std::string postData = payload.dump();
            
            struct curl_slist* headers = NULL;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, postData.c_str());
            curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
            curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
            
            CURLcode res = curl_easy_perform(curl);
            
            curl_slist_free_all(headers);
            curl_easy_cleanup(curl);
            
            if (res != CURLE_OK) {
                return json{{"success", false}, {"error", curl_easy_strerror(res)}};
            }
        }
        
        try {
            return json::parse(response);
        } catch (...) {
            return json{{"success", false}, {"error", "Failed to parse response"}};
        }
    }

public:
    NeutronAuth() {
        curl_global_init(CURL_GLOBAL_DEFAULT);
    }
    
    ~NeutronAuth() {
        curl_global_cleanup();
    }

    json login(const std::string& username, const std::string& password, const std::string& hwid = "") {
        std::string hw = hwid.empty() ? getHWID() : hwid;
        
        json payload = {
            {"secret", app_secret},
            {"username", username},
            {"password", password},
            {"hwid", hw}
        };
        
        return httpPost("/login", payload);
    }

    json checkLicense(const std::string& licenseKey) {
        json payload = {
            {"secret", app_secret},
            {"license", licenseKey}
        };
        
        return httpPost("/check", payload);
    }
};

#endif // NEUTRON_SDK_HPP
