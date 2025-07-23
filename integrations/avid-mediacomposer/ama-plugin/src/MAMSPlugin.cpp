#include "MAMSPlugin.h"
#include "MAMSContainer.h"
#include "MAMSAPIClient.h"
#include "MAMSUtils.h"
#include <AMA/IMAPropertySet.h>
#include <sstream>
#include <algorithm>

namespace MAMS {

// Plugin GUID - must be unique
static const GUID MAMS_PLUGIN_GUID = 
    { 0x12345678, 0x1234, 0x5678, { 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0 } };

MAMSPlugin::MAMSPlugin()
    : m_pHost(nullptr)
    , m_authenticated(false)
{
    InitializeContainerTypes();
}

MAMSPlugin::~MAMSPlugin()
{
    Terminate();
}

HRESULT MAMSPlugin::Initialize(IMAHost* pHost)
{
    if (!pHost) {
        return E_POINTER;
    }
    
    m_pHost = pHost;
    
    // Initialize API client
    MAMSAPIClient::Initialize();
    
    // Load saved preferences
    IMAPropertySet* pPrefs = nullptr;
    if (SUCCEEDED(m_pHost->LoadPreferences(&pPrefs)) && pPrefs) {
        SetPreferences(pPrefs);
        pPrefs->Release();
    }
    
    return S_OK;
}

HRESULT MAMSPlugin::Terminate()
{
    // Save preferences
    if (m_pHost) {
        IMAPropertySet* pPrefs = nullptr;
        if (SUCCEEDED(GetPreferences(&pPrefs)) && pPrefs) {
            m_pHost->SavePreferences(pPrefs);
            pPrefs->Release();
        }
    }
    
    // Cleanup
    MAMSAPIClient::Terminate();
    m_pHost = nullptr;
    
    return S_OK;
}

HRESULT MAMSPlugin::GetPluginInfo(MAPluginInfo* pInfo)
{
    if (!pInfo) {
        return E_POINTER;
    }
    
    pInfo->guid = MAMS_PLUGIN_GUID;
    wcscpy_s(pInfo->name, L"MAMS Media Access");
    wcscpy_s(pInfo->vendor, L"MAMS");
    wcscpy_s(pInfo->version, L"1.0.0");
    wcscpy_s(pInfo->description, L"Access media assets from MAMS directly in Avid Media Composer");
    
    return S_OK;
}

HRESULT MAMSPlugin::GetContainerInfo(uint32_t index, MAContainerInfo* pInfo)
{
    if (!pInfo || index >= m_containerTypes.size()) {
        return E_INVALIDARG;
    }
    
    const auto& containerType = m_containerTypes[index];
    
    wcscpy_s(pInfo->extension, containerType.extension.c_str());
    wcscpy_s(pInfo->description, containerType.description.c_str());
    wcscpy_s(pInfo->mimeType, containerType.mimeType.c_str());
    pInfo->canOpen = true;
    pInfo->canCreate = false;
    
    return S_OK;
}

uint32_t MAMSPlugin::GetContainerCount()
{
    return static_cast<uint32_t>(m_containerTypes.size());
}

HRESULT MAMSPlugin::OpenContainer(const wchar_t* pURL, IMAContainer** ppContainer)
{
    if (!pURL || !ppContainer) {
        return E_POINTER;
    }
    
    *ppContainer = nullptr;
    
    // Check if we can open this URL
    if (FAILED(CanOpenContainer(pURL))) {
        return E_FAIL;
    }
    
    // Parse URL - format: mams://server/asset/id or mams://server/search/query
    std::wstring url(pURL);
    
    // Create appropriate container
    MAMSContainer* pContainer = new MAMSContainer(this);
    if (!pContainer) {
        return E_OUTOFMEMORY;
    }
    
    HRESULT hr = pContainer->Initialize(url);
    if (FAILED(hr)) {
        delete pContainer;
        return hr;
    }
    
    *ppContainer = pContainer;
    return S_OK;
}

HRESULT MAMSPlugin::CanOpenContainer(const wchar_t* pURL)
{
    if (!pURL) {
        return E_POINTER;
    }
    
    std::wstring url(pURL);
    
    // Check if it's a MAMS URL
    if (url.find(L"mams://") == 0) {
        return S_OK;
    }
    
    // Check file extensions for local files that might be MAMS-linked
    if (IsSupportedURL(url)) {
        return S_OK;
    }
    
    return S_FALSE;
}

HRESULT MAMSPlugin::GetPreferences(IMAPropertySet** ppPrefs)
{
    if (!ppPrefs || !m_pHost) {
        return E_POINTER;
    }
    
    IMAPropertySet* pPrefs = nullptr;
    HRESULT hr = m_pHost->CreatePropertySet(&pPrefs);
    if (FAILED(hr) || !pPrefs) {
        return hr;
    }
    
    // Save current settings
    pPrefs->SetString(L"ServerURL", m_serverUrl.c_str());
    pPrefs->SetString(L"APIKey", m_apiKey.c_str());
    
    *ppPrefs = pPrefs;
    return S_OK;
}

HRESULT MAMSPlugin::SetPreferences(IMAPropertySet* pPrefs)
{
    if (!pPrefs) {
        return E_POINTER;
    }
    
    // Load settings
    wchar_t buffer[1024];
    
    if (SUCCEEDED(pPrefs->GetString(L"ServerURL", buffer, 1024))) {
        m_serverUrl = buffer;
    }
    
    if (SUCCEEDED(pPrefs->GetString(L"APIKey", buffer, 1024))) {
        m_apiKey = buffer;
        // Attempt authentication
        Authenticate(m_serverUrl, m_apiKey);
    }
    
    return S_OK;
}

HRESULT MAMSPlugin::Authenticate(const std::wstring& serverUrl, const std::wstring& apiKey)
{
    m_serverUrl = serverUrl;
    m_apiKey = apiKey;
    
    // Configure API client
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    client.SetServerUrl(serverUrl);
    client.SetAPIKey(apiKey);
    
    // Test authentication
    m_authenticated = client.TestConnection();
    
    return m_authenticated ? S_OK : E_FAIL;
}

HRESULT MAMSPlugin::SetServerUrl(const std::wstring& url)
{
    m_serverUrl = url;
    MAMSAPIClient::GetInstance().SetServerUrl(url);
    return S_OK;
}

void MAMSPlugin::InitializeContainerTypes()
{
    // MAMS virtual container
    m_containerTypes.push_back({L".mams", L"MAMS Asset Container", L"application/x-mams"});
    
    // Supported video formats
    m_containerTypes.push_back({L".mov", L"QuickTime Movie", L"video/quicktime"});
    m_containerTypes.push_back({L".mp4", L"MPEG-4 Video", L"video/mp4"});
    m_containerTypes.push_back({L".mxf", L"Material Exchange Format", L"application/mxf"});
    m_containerTypes.push_back({L".avi", L"AVI Video", L"video/x-msvideo"});
    
    // Supported audio formats
    m_containerTypes.push_back({L".wav", L"WAV Audio", L"audio/wav"});
    m_containerTypes.push_back({L".aiff", L"AIFF Audio", L"audio/aiff"});
    m_containerTypes.push_back({L".mp3", L"MP3 Audio", L"audio/mpeg"});
    
    // Supported image sequences
    m_containerTypes.push_back({L".dpx", L"DPX Image Sequence", L"image/x-dpx"});
    m_containerTypes.push_back({L".tiff", L"TIFF Image Sequence", L"image/tiff"});
    m_containerTypes.push_back({L".png", L"PNG Image Sequence", L"image/png"});
}

bool MAMSPlugin::IsSupportedURL(const std::wstring& url)
{
    // Convert to lowercase for comparison
    std::wstring lowerUrl = url;
    std::transform(lowerUrl.begin(), lowerUrl.end(), lowerUrl.begin(), ::tolower);
    
    // Check against supported extensions
    for (const auto& containerType : m_containerTypes) {
        if (lowerUrl.find(containerType.extension) != std::wstring::npos) {
            return true;
        }
    }
    
    return false;
}

// Plugin factory function
extern "C" __declspec(dllexport) HRESULT CreateMAMSPlugin(IMAPlugin** ppPlugin)
{
    if (!ppPlugin) {
        return E_POINTER;
    }
    
    *ppPlugin = new MAMSPlugin();
    if (!*ppPlugin) {
        return E_OUTOFMEMORY;
    }
    
    return S_OK;
}

} // namespace MAMS