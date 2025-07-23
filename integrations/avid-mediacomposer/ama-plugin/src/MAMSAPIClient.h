#ifndef MAMS_API_CLIENT_H
#define MAMS_API_CLIENT_H

#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <map>

namespace MAMS {

struct AssetInfo {
    std::wstring id;
    std::wstring name;
    std::wstring type;
    std::wstring path;
    std::wstring proxyPath;
    int64_t size;
    double duration;
    int width;
    int height;
    double frameRate;
    std::wstring format;
    std::wstring codec;
    std::map<std::wstring, std::wstring> metadata;
};

class MAMSAPIClient {
public:
    static MAMSAPIClient& GetInstance();
    static void Initialize();
    static void Terminate();
    
    // Configuration
    void SetServerUrl(const std::wstring& url);
    void SetAPIKey(const std::wstring& key);
    void SetAccessToken(const std::wstring& token);
    
    // Authentication
    bool Login(const std::wstring& username, const std::wstring& password);
    bool TestConnection();
    
    // Asset operations
    bool SearchAssets(const std::wstring& query, std::vector<std::wstring>& results);
    bool GetAsset(const std::wstring& assetId, std::wstring& assetData);
    bool GetAssetInfo(const std::wstring& assetId, AssetInfo& info);
    bool GetAssetMetadata(const std::wstring& assetId, std::map<std::wstring, std::wstring>& metadata);
    
    // Project operations
    bool GetProjectAssets(const std::wstring& projectId, std::vector<std::wstring>& assets);
    bool GetFolderContents(const std::wstring& folderId, std::vector<std::wstring>& contents);
    
    // Media operations
    bool GetProxyUrl(const std::wstring& assetId, std::wstring& proxyUrl);
    bool GetHighResUrl(const std::wstring& assetId, std::wstring& url);
    bool DownloadFile(const std::wstring& url, const std::wstring& localPath);
    
    // Metadata operations
    bool UpdateAssetMetadata(const std::wstring& assetId, const std::map<std::wstring, std::wstring>& metadata);
    
private:
    MAMSAPIClient();
    ~MAMSAPIClient();
    
    // HTTP operations
    bool HttpGet(const std::wstring& endpoint, std::wstring& response);
    bool HttpPost(const std::wstring& endpoint, const std::wstring& data, std::wstring& response);
    bool HttpPut(const std::wstring& endpoint, const std::wstring& data, std::wstring& response);
    bool HttpDelete(const std::wstring& endpoint, std::wstring& response);
    
    // Helpers
    std::wstring BuildUrl(const std::wstring& endpoint);
    std::string WStringToUTF8(const std::wstring& wstr);
    std::wstring UTF8ToWString(const std::string& str);
    
    // JSON parsing helpers
    bool ParseAssetInfo(const std::wstring& json, AssetInfo& info);
    bool ParseSearchResults(const std::wstring& json, std::vector<std::wstring>& results);
    
private:
    static std::unique_ptr<MAMSAPIClient> s_instance;
    static std::mutex s_mutex;
    
    std::wstring m_serverUrl;
    std::wstring m_apiKey;
    std::wstring m_accessToken;
    
    // HTTP client handle (platform-specific)
    void* m_httpClient;
};

} // namespace MAMS

#endif // MAMS_API_CLIENT_H