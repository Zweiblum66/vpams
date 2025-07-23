#include "MAMSContainer.h"
#include "MAMSPlugin.h"
#include "MAMSClip.h"
#include "MAMSAPIClient.h"
#include "MAMSUtils.h"
#include <AMA/IMAPropertySet.h>
#include <sstream>
#include <algorithm>

namespace MAMS {

MAMSContainer::MAMSContainer(MAMSPlugin* pPlugin)
    : m_pPlugin(pPlugin)
    , m_type(TYPE_SINGLE)
{
}

MAMSContainer::~MAMSContainer()
{
    Close();
}

HRESULT MAMSContainer::Initialize(const std::wstring& url)
{
    m_url = url;
    
    // Parse URL to determine container type
    HRESULT hr = ParseURL(url);
    if (FAILED(hr)) {
        return hr;
    }
    
    // Load content based on type
    switch (m_type) {
        case TYPE_SEARCH:
            {
                size_t pos = url.find(L"search/");
                if (pos != std::wstring::npos) {
                    std::wstring query = url.substr(pos + 7);
                    return LoadSearchResults(query);
                }
            }
            break;
            
        case TYPE_PROJECT:
            {
                size_t pos = url.find(L"project/");
                if (pos != std::wstring::npos) {
                    std::wstring projectId = url.substr(pos + 8);
                    return LoadProjectAssets(projectId);
                }
            }
            break;
            
        case TYPE_FOLDER:
            {
                size_t pos = url.find(L"folder/");
                if (pos != std::wstring::npos) {
                    std::wstring folderId = url.substr(pos + 7);
                    return LoadFolderContents(folderId);
                }
            }
            break;
            
        case TYPE_SINGLE:
            {
                size_t pos = url.find(L"asset/");
                if (pos != std::wstring::npos) {
                    std::wstring assetId = url.substr(pos + 6);
                    return LoadSingleAsset(assetId);
                }
            }
            break;
    }
    
    return E_FAIL;
}

HRESULT MAMSContainer::GetContainerInfo(MAContainerInfo* pInfo)
{
    if (!pInfo) {
        return E_POINTER;
    }
    
    wcscpy_s(pInfo->name, m_name.c_str());
    wcscpy_s(pInfo->url, m_url.c_str());
    pInfo->clipCount = static_cast<uint32_t>(m_clips.size());
    pInfo->isReadOnly = true;
    pInfo->canRefresh = true;
    
    return S_OK;
}

uint32_t MAMSContainer::GetClipCount()
{
    return static_cast<uint32_t>(m_clips.size());
}

HRESULT MAMSContainer::GetClip(uint32_t index, IMAClip** ppClip)
{
    if (!ppClip || index >= m_clips.size()) {
        return E_INVALIDARG;
    }
    
    *ppClip = m_clips[index].get();
    (*ppClip)->AddRef();
    
    return S_OK;
}

HRESULT MAMSContainer::GetClipByID(const wchar_t* pID, IMAClip** ppClip)
{
    if (!pID || !ppClip) {
        return E_POINTER;
    }
    
    std::wstring id(pID);
    
    for (const auto& clip : m_clips) {
        MAClipInfo info;
        if (SUCCEEDED(clip->GetClipInfo(&info))) {
            if (std::wstring(info.id) == id) {
                *ppClip = clip.get();
                (*ppClip)->AddRef();
                return S_OK;
            }
        }
    }
    
    return E_FAIL;
}

HRESULT MAMSContainer::AddClip(IMAClip* pClip)
{
    // Container is read-only from MAMS
    return E_NOTIMPL;
}

HRESULT MAMSContainer::RemoveClip(IMAClip* pClip)
{
    // Container is read-only from MAMS
    return E_NOTIMPL;
}

HRESULT MAMSContainer::GetMetadata(IMAPropertySet** ppMetadata)
{
    if (!ppMetadata || !m_pPlugin || !m_pPlugin->GetHost()) {
        return E_POINTER;
    }
    
    IMAPropertySet* pMetadata = nullptr;
    HRESULT hr = m_pPlugin->GetHost()->CreatePropertySet(&pMetadata);
    if (FAILED(hr) || !pMetadata) {
        return hr;
    }
    
    // Add container metadata
    pMetadata->SetString(L"ContainerType", 
        m_type == TYPE_SEARCH ? L"Search Results" :
        m_type == TYPE_PROJECT ? L"Project Assets" :
        m_type == TYPE_FOLDER ? L"Folder Contents" : L"Single Asset");
    pMetadata->SetString(L"URL", m_url.c_str());
    pMetadata->SetInt32(L"ClipCount", static_cast<int32_t>(m_clips.size()));
    
    *ppMetadata = pMetadata;
    return S_OK;
}

HRESULT MAMSContainer::SetMetadata(IMAPropertySet* pMetadata)
{
    // Container metadata is read-only
    return E_NOTIMPL;
}

HRESULT MAMSContainer::Refresh()
{
    // Clear existing clips
    m_clips.clear();
    
    // Reload based on container type
    return Initialize(m_url);
}

HRESULT MAMSContainer::Close()
{
    m_clips.clear();
    return S_OK;
}

HRESULT MAMSContainer::ParseURL(const std::wstring& url)
{
    // Parse MAMS URL format: mams://server/type/id
    if (url.find(L"mams://") != 0) {
        return E_INVALIDARG;
    }
    
    // Determine container type from URL
    if (url.find(L"/search/") != std::wstring::npos) {
        m_type = TYPE_SEARCH;
        m_name = L"MAMS Search Results";
    }
    else if (url.find(L"/project/") != std::wstring::npos) {
        m_type = TYPE_PROJECT;
        m_name = L"MAMS Project";
    }
    else if (url.find(L"/folder/") != std::wstring::npos) {
        m_type = TYPE_FOLDER;
        m_name = L"MAMS Folder";
    }
    else if (url.find(L"/asset/") != std::wstring::npos) {
        m_type = TYPE_SINGLE;
        m_name = L"MAMS Asset";
    }
    else {
        return E_INVALIDARG;
    }
    
    return S_OK;
}

HRESULT MAMSContainer::LoadSearchResults(const std::wstring& query)
{
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    // Perform search
    std::vector<std::wstring> results;
    if (!client.SearchAssets(query, results)) {
        return E_FAIL;
    }
    
    // Create clips for each result
    for (const auto& assetData : results) {
        CreateClipFromAsset(L"", assetData);
    }
    
    m_name = L"Search: " + query;
    return S_OK;
}

HRESULT MAMSContainer::LoadProjectAssets(const std::wstring& projectId)
{
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    // Get project assets
    std::vector<std::wstring> assets;
    if (!client.GetProjectAssets(projectId, assets)) {
        return E_FAIL;
    }
    
    // Create clips
    for (const auto& assetData : assets) {
        CreateClipFromAsset(L"", assetData);
    }
    
    m_name = L"Project: " + projectId;
    return S_OK;
}

HRESULT MAMSContainer::LoadFolderContents(const std::wstring& folderId)
{
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    // Get folder contents
    std::vector<std::wstring> contents;
    if (!client.GetFolderContents(folderId, contents)) {
        return E_FAIL;
    }
    
    // Create clips
    for (const auto& assetData : contents) {
        CreateClipFromAsset(L"", assetData);
    }
    
    m_name = L"Folder: " + folderId;
    return S_OK;
}

HRESULT MAMSContainer::LoadSingleAsset(const std::wstring& assetId)
{
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    // Get asset data
    std::wstring assetData;
    if (!client.GetAsset(assetId, assetData)) {
        return E_FAIL;
    }
    
    // Create single clip
    return CreateClipFromAsset(assetId, assetData);
}

HRESULT MAMSContainer::CreateClipFromAsset(const std::wstring& assetId, const std::wstring& assetData)
{
    auto clip = std::make_unique<MAMSClip>(this, m_pPlugin);
    
    HRESULT hr = clip->Initialize(assetId, assetData);
    if (FAILED(hr)) {
        return hr;
    }
    
    m_clips.push_back(std::move(clip));
    return S_OK;
}

} // namespace MAMS