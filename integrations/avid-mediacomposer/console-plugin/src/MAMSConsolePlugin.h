#ifndef MAMS_CONSOLE_PLUGIN_H
#define MAMS_CONSOLE_PLUGIN_H

#include <AvidConsoleAPI.h>
#include <string>
#include <vector>
#include <memory>

namespace MAMS {

class MAMSConsolePlugin : public IAvidConsolePlugin {
public:
    MAMSConsolePlugin();
    virtual ~MAMSConsolePlugin();
    
    // IAvidConsolePlugin interface
    virtual HRESULT Initialize(IAvidConsoleHost* pHost) override;
    virtual HRESULT Terminate() override;
    
    virtual HRESULT GetPluginInfo(AvidConsolePluginInfo* pInfo) override;
    virtual HRESULT GetCommandCount(uint32_t* pCount) override;
    virtual HRESULT GetCommandInfo(uint32_t index, AvidConsoleCommandInfo* pInfo) override;
    
    virtual HRESULT ExecuteCommand(const wchar_t* pCommand, const wchar_t* pParams, wchar_t* pResult, uint32_t resultSize) override;
    
private:
    IAvidConsoleHost* m_pHost;
    
    // Command handlers
    HRESULT HandleSearch(const std::wstring& params, std::wstring& result);
    HRESULT HandleImport(const std::wstring& params, std::wstring& result);
    HRESULT HandleSync(const std::wstring& params, std::wstring& result);
    HRESULT HandleLink(const std::wstring& params, std::wstring& result);
    HRESULT HandleExport(const std::wstring& params, std::wstring& result);
    HRESULT HandleConfig(const std::wstring& params, std::wstring& result);
    HRESULT HandleStatus(const std::wstring& params, std::wstring& result);
    HRESULT HandleHelp(const std::wstring& params, std::wstring& result);
    
    // Helper functions
    std::vector<std::wstring> ParseParameters(const std::wstring& params);
    std::wstring GetCurrentBinPath();
    std::wstring GetCurrentSequencePath();
    bool ImportAssetToBin(const std::wstring& assetId, const std::wstring& binPath);
    bool ExportSequenceToMAMS(const std::wstring& sequencePath, const std::wstring& format);
    
    // Command definitions
    struct CommandDef {
        std::wstring name;
        std::wstring description;
        std::wstring syntax;
        std::wstring example;
    };
    std::vector<CommandDef> m_commands;
    
    void InitializeCommands();
};

} // namespace MAMS

#endif // MAMS_CONSOLE_PLUGIN_H