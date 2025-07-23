#ifndef MAMS_PLUGIN_H
#define MAMS_PLUGIN_H

#include <AMA/IMAPlugin.h>
#include <AMA/IMAContainer.h>
#include <AMA/IMAHost.h>
#include <memory>
#include <string>
#include <vector>

namespace MAMS {

class MAMSPlugin : public IMAPlugin {
public:
    MAMSPlugin();
    virtual ~MAMSPlugin();

    // IMAPlugin interface
    virtual HRESULT Initialize(IMAHost* pHost) override;
    virtual HRESULT Terminate() override;
    
    virtual HRESULT GetPluginInfo(MAPluginInfo* pInfo) override;
    virtual HRESULT GetContainerInfo(uint32_t index, MAContainerInfo* pInfo) override;
    virtual uint32_t GetContainerCount() override;
    
    virtual HRESULT OpenContainer(const wchar_t* pURL, IMAContainer** ppContainer) override;
    virtual HRESULT CanOpenContainer(const wchar_t* pURL) override;
    
    virtual HRESULT GetPreferences(IMAPropertySet** ppPrefs) override;
    virtual HRESULT SetPreferences(IMAPropertySet* pPrefs) override;
    
    // Authentication and configuration
    HRESULT Authenticate(const std::wstring& serverUrl, const std::wstring& apiKey);
    HRESULT SetServerUrl(const std::wstring& url);
    std::wstring GetServerUrl() const { return m_serverUrl; }
    
    // Host access
    IMAHost* GetHost() const { return m_pHost; }

private:
    IMAHost* m_pHost;
    std::wstring m_serverUrl;
    std::wstring m_apiKey;
    bool m_authenticated;
    
    // Supported container types
    struct ContainerType {
        std::wstring extension;
        std::wstring description;
        std::wstring mimeType;
    };
    std::vector<ContainerType> m_containerTypes;
    
    void InitializeContainerTypes();
    bool IsSupportedURL(const std::wstring& url);
};

// Plugin factory function
extern "C" HRESULT CreateMAMSPlugin(IMAPlugin** ppPlugin);

} // namespace MAMS

#endif // MAMS_PLUGIN_H