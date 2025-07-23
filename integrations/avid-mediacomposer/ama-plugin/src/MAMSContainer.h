#ifndef MAMS_CONTAINER_H
#define MAMS_CONTAINER_H

#include <AMA/IMAContainer.h>
#include <AMA/IMAClip.h>
#include <vector>
#include <memory>
#include <string>

namespace MAMS {

class MAMSPlugin;
class MAMSClip;

class MAMSContainer : public IMAContainer {
public:
    MAMSContainer(MAMSPlugin* pPlugin);
    virtual ~MAMSContainer();

    // IMAContainer interface
    virtual HRESULT Initialize(const std::wstring& url);
    virtual HRESULT GetContainerInfo(MAContainerInfo* pInfo) override;
    
    virtual uint32_t GetClipCount() override;
    virtual HRESULT GetClip(uint32_t index, IMAClip** ppClip) override;
    virtual HRESULT GetClipByID(const wchar_t* pID, IMAClip** ppClip) override;
    
    virtual HRESULT AddClip(IMAClip* pClip) override;
    virtual HRESULT RemoveClip(IMAClip* pClip) override;
    
    virtual HRESULT GetMetadata(IMAPropertySet** ppMetadata) override;
    virtual HRESULT SetMetadata(IMAPropertySet* pMetadata) override;
    
    virtual HRESULT Refresh() override;
    virtual HRESULT Close() override;
    
    // Container types
    enum ContainerType {
        TYPE_SEARCH,    // Search results
        TYPE_PROJECT,   // Project assets
        TYPE_FOLDER,    // Folder/bin
        TYPE_SINGLE     // Single asset
    };
    
    ContainerType GetType() const { return m_type; }
    std::wstring GetURL() const { return m_url; }

private:
    MAMSPlugin* m_pPlugin;
    std::wstring m_url;
    std::wstring m_name;
    ContainerType m_type;
    std::vector<std::unique_ptr<MAMSClip>> m_clips;
    
    // Parse URL and determine container type
    HRESULT ParseURL(const std::wstring& url);
    
    // Load content based on container type
    HRESULT LoadSearchResults(const std::wstring& query);
    HRESULT LoadProjectAssets(const std::wstring& projectId);
    HRESULT LoadFolderContents(const std::wstring& folderId);
    HRESULT LoadSingleAsset(const std::wstring& assetId);
    
    // Helper to create clip from asset data
    HRESULT CreateClipFromAsset(const std::wstring& assetId, const std::wstring& assetData);
};

} // namespace MAMS

#endif // MAMS_CONTAINER_H