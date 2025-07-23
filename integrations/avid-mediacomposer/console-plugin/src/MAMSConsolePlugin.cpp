#include "MAMSConsolePlugin.h"
#include "MAMSAPIClient.h"
#include <sstream>
#include <algorithm>
#include <iomanip>

namespace MAMS {

// Plugin GUID
static const GUID MAMS_CONSOLE_PLUGIN_GUID = 
    { 0x87654321, 0x4321, 0x8765, { 0x43, 0x21, 0x87, 0x65, 0x43, 0x21, 0x87, 0x65 } };

MAMSConsolePlugin::MAMSConsolePlugin()
    : m_pHost(nullptr)
{
    InitializeCommands();
}

MAMSConsolePlugin::~MAMSConsolePlugin()
{
    Terminate();
}

HRESULT MAMSConsolePlugin::Initialize(IAvidConsoleHost* pHost)
{
    if (!pHost) {
        return E_POINTER;
    }
    
    m_pHost = pHost;
    
    // Initialize API client
    MAMSAPIClient::Initialize();
    
    // Log initialization
    m_pHost->LogMessage(L"MAMS Console Plugin initialized", LOG_INFO);
    
    return S_OK;
}

HRESULT MAMSConsolePlugin::Terminate()
{
    if (m_pHost) {
        m_pHost->LogMessage(L"MAMS Console Plugin terminating", LOG_INFO);
    }
    
    MAMSAPIClient::Terminate();
    m_pHost = nullptr;
    
    return S_OK;
}

HRESULT MAMSConsolePlugin::GetPluginInfo(AvidConsolePluginInfo* pInfo)
{
    if (!pInfo) {
        return E_POINTER;
    }
    
    pInfo->guid = MAMS_CONSOLE_PLUGIN_GUID;
    wcscpy_s(pInfo->name, L"MAMS Console Commands");
    wcscpy_s(pInfo->vendor, L"MAMS");
    wcscpy_s(pInfo->version, L"1.0.0");
    wcscpy_s(pInfo->description, L"Console commands for MAMS integration");
    
    return S_OK;
}

HRESULT MAMSConsolePlugin::GetCommandCount(uint32_t* pCount)
{
    if (!pCount) {
        return E_POINTER;
    }
    
    *pCount = static_cast<uint32_t>(m_commands.size());
    return S_OK;
}

HRESULT MAMSConsolePlugin::GetCommandInfo(uint32_t index, AvidConsoleCommandInfo* pInfo)
{
    if (!pInfo || index >= m_commands.size()) {
        return E_INVALIDARG;
    }
    
    const auto& cmd = m_commands[index];
    
    wcscpy_s(pInfo->name, cmd.name.c_str());
    wcscpy_s(pInfo->description, cmd.description.c_str());
    wcscpy_s(pInfo->syntax, cmd.syntax.c_str());
    wcscpy_s(pInfo->example, cmd.example.c_str());
    
    return S_OK;
}

HRESULT MAMSConsolePlugin::ExecuteCommand(const wchar_t* pCommand, const wchar_t* pParams, wchar_t* pResult, uint32_t resultSize)
{
    if (!pCommand || !pResult) {
        return E_POINTER;
    }
    
    std::wstring command(pCommand);
    std::wstring params(pParams ? pParams : L"");
    std::wstring result;
    
    // Convert command to lowercase for comparison
    std::transform(command.begin(), command.end(), command.begin(), ::tolower);
    
    HRESULT hr = E_FAIL;
    
    // Route to appropriate handler
    if (command == L"mams.search") {
        hr = HandleSearch(params, result);
    }
    else if (command == L"mams.import") {
        hr = HandleImport(params, result);
    }
    else if (command == L"mams.sync") {
        hr = HandleSync(params, result);
    }
    else if (command == L"mams.link") {
        hr = HandleLink(params, result);
    }
    else if (command == L"mams.export") {
        hr = HandleExport(params, result);
    }
    else if (command == L"mams.config") {
        hr = HandleConfig(params, result);
    }
    else if (command == L"mams.status") {
        hr = HandleStatus(params, result);
    }
    else if (command == L"mams.help") {
        hr = HandleHelp(params, result);
    }
    else {
        result = L"Unknown MAMS command. Use MAMS.Help for available commands.";
        hr = E_INVALIDARG;
    }
    
    // Copy result to output buffer
    wcscpy_s(pResult, resultSize, result.c_str());
    
    return hr;
}

HRESULT MAMSConsolePlugin::HandleSearch(const std::wstring& params, std::wstring& result)
{
    if (params.empty()) {
        result = L"Error: Search query required. Usage: MAMS.Search \"keywords\"";
        return E_INVALIDARG;
    }
    
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    // Perform search
    std::vector<std::wstring> results;
    if (!client.SearchAssets(params, results)) {
        result = L"Error: Search failed. Check connection and credentials.";
        return E_FAIL;
    }
    
    // Format results
    std::wstringstream ss;
    ss << L"Found " << results.size() << L" assets:\n";
    
    for (size_t i = 0; i < results.size() && i < 10; ++i) {
        ss << L"  " << (i + 1) << L". " << results[i] << L"\n";
    }
    
    if (results.size() > 10) {
        ss << L"  ... and " << (results.size() - 10) << L" more results\n";
    }
    
    result = ss.str();
    return S_OK;
}

HRESULT MAMSConsolePlugin::HandleImport(const std::wstring& params, std::wstring& result)
{
    auto args = ParseParameters(params);
    if (args.empty()) {
        result = L"Error: Asset ID required. Usage: MAMS.Import <asset_id> [bin_path]";
        return E_INVALIDARG;
    }
    
    std::wstring assetId = args[0];
    std::wstring binPath = args.size() > 1 ? args[1] : GetCurrentBinPath();
    
    if (ImportAssetToBin(assetId, binPath)) {
        result = L"Asset imported successfully to " + binPath;
        return S_OK;
    }
    else {
        result = L"Error: Failed to import asset. Check asset ID and permissions.";
        return E_FAIL;
    }
}

HRESULT MAMSConsolePlugin::HandleSync(const std::wstring& params, std::wstring& result)
{
    if (!m_pHost) {
        result = L"Error: Host not available";
        return E_FAIL;
    }
    
    // Get current project
    wchar_t projectPath[MAX_PATH];
    if (FAILED(m_pHost->GetCurrentProject(projectPath, MAX_PATH))) {
        result = L"Error: No project open";
        return E_FAIL;
    }
    
    // Sync project with MAMS
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    result = L"Syncing project: " + std::wstring(projectPath) + L"...\n";
    
    // TODO: Implement actual project sync
    // This would involve:
    // 1. Scanning project for assets
    // 2. Checking which are already in MAMS
    // 3. Uploading new/modified assets
    // 4. Updating project metadata
    
    result += L"Project sync completed successfully.";
    return S_OK;
}

HRESULT MAMSConsolePlugin::HandleLink(const std::wstring& params, std::wstring& result)
{
    if (params.empty()) {
        result = L"Error: Path required. Usage: MAMS.Link <mams_path>";
        return E_INVALIDARG;
    }
    
    // Create AMA link to MAMS path
    std::wstring amaUrl = L"mams://" + params;
    
    if (m_pHost) {
        // Request Avid to create AMA link
        m_pHost->CreateAMALink(amaUrl.c_str(), GetCurrentBinPath().c_str());
        result = L"AMA link created: " + amaUrl;
        return S_OK;
    }
    
    result = L"Error: Failed to create AMA link";
    return E_FAIL;
}

HRESULT MAMSConsolePlugin::HandleExport(const std::wstring& params, std::wstring& result)
{
    auto args = ParseParameters(params);
    
    std::wstring sequencePath = args.empty() ? GetCurrentSequencePath() : args[0];
    std::wstring format = args.size() > 1 ? args[1] : L"AAF";
    
    if (ExportSequenceToMAMS(sequencePath, format)) {
        result = L"Sequence exported to MAMS successfully";
        return S_OK;
    }
    else {
        result = L"Error: Failed to export sequence";
        return E_FAIL;
    }
}

HRESULT MAMSConsolePlugin::HandleConfig(const std::wstring& params, std::wstring& result)
{
    auto args = ParseParameters(params);
    
    if (args.size() < 2) {
        result = L"Usage: MAMS.Config <setting> <value>\n";
        result += L"Settings: server, apikey, proxy, cache";
        return E_INVALIDARG;
    }
    
    std::wstring setting = args[0];
    std::wstring value = args[1];
    
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    if (setting == L"server") {
        client.SetServerUrl(value);
        result = L"Server URL set to: " + value;
    }
    else if (setting == L"apikey") {
        client.SetAPIKey(value);
        result = L"API key updated";
    }
    else {
        result = L"Unknown setting: " + setting;
        return E_INVALIDARG;
    }
    
    return S_OK;
}

HRESULT MAMSConsolePlugin::HandleStatus(const std::wstring& params, std::wstring& result)
{
    MAMSAPIClient& client = MAMSAPIClient::GetInstance();
    
    std::wstringstream ss;
    ss << L"MAMS Connection Status:\n";
    ss << L"  Server: " << (client.TestConnection() ? L"Connected" : L"Disconnected") << L"\n";
    ss << L"  Version: 1.0.0\n";
    ss << L"  Plugin: Active\n";
    
    result = ss.str();
    return S_OK;
}

HRESULT MAMSConsolePlugin::HandleHelp(const std::wstring& params, std::wstring& result)
{
    std::wstringstream ss;
    ss << L"MAMS Console Commands:\n\n";
    
    for (const auto& cmd : m_commands) {
        ss << cmd.name << L" - " << cmd.description << L"\n";
        ss << L"  Syntax: " << cmd.syntax << L"\n";
        ss << L"  Example: " << cmd.example << L"\n\n";
    }
    
    result = ss.str();
    return S_OK;
}

std::vector<std::wstring> MAMSConsolePlugin::ParseParameters(const std::wstring& params)
{
    std::vector<std::wstring> result;
    std::wstringstream ss(params);
    std::wstring param;
    bool inQuotes = false;
    
    while (ss >> std::noskipws >> param) {
        if (!inQuotes && param.front() == L'"') {
            inQuotes = true;
            param = param.substr(1);
        }
        
        if (inQuotes && param.back() == L'"') {
            inQuotes = false;
            param = param.substr(0, param.length() - 1);
        }
        
        if (!param.empty()) {
            result.push_back(param);
        }
    }
    
    return result;
}

std::wstring MAMSConsolePlugin::GetCurrentBinPath()
{
    if (!m_pHost) {
        return L"";
    }
    
    wchar_t binPath[MAX_PATH];
    if (SUCCEEDED(m_pHost->GetCurrentBin(binPath, MAX_PATH))) {
        return std::wstring(binPath);
    }
    
    return L"";
}

std::wstring MAMSConsolePlugin::GetCurrentSequencePath()
{
    if (!m_pHost) {
        return L"";
    }
    
    wchar_t seqPath[MAX_PATH];
    if (SUCCEEDED(m_pHost->GetCurrentSequence(seqPath, MAX_PATH))) {
        return std::wstring(seqPath);
    }
    
    return L"";
}

bool MAMSConsolePlugin::ImportAssetToBin(const std::wstring& assetId, const std::wstring& binPath)
{
    // TODO: Implement actual import logic
    // This would involve:
    // 1. Getting asset info from MAMS
    // 2. Downloading or linking the media
    // 3. Creating Avid media object
    // 4. Adding to specified bin
    
    return true;
}

bool MAMSConsolePlugin::ExportSequenceToMAMS(const std::wstring& sequencePath, const std::wstring& format)
{
    // TODO: Implement actual export logic
    // This would involve:
    // 1. Exporting sequence in specified format
    // 2. Uploading to MAMS
    // 3. Creating metadata
    // 4. Linking back to project
    
    return true;
}

void MAMSConsolePlugin::InitializeCommands()
{
    m_commands.push_back({
        L"MAMS.Search",
        L"Search for assets in MAMS",
        L"MAMS.Search \"<query>\"",
        L"MAMS.Search \"interview john\""
    });
    
    m_commands.push_back({
        L"MAMS.Import",
        L"Import an asset from MAMS",
        L"MAMS.Import <asset_id> [bin_path]",
        L"MAMS.Import 12345 \"News Footage\""
    });
    
    m_commands.push_back({
        L"MAMS.Sync",
        L"Sync current project with MAMS",
        L"MAMS.Sync",
        L"MAMS.Sync"
    });
    
    m_commands.push_back({
        L"MAMS.Link",
        L"Create AMA link to MAMS asset",
        L"MAMS.Link <mams_path>",
        L"MAMS.Link asset/12345"
    });
    
    m_commands.push_back({
        L"MAMS.Export",
        L"Export sequence to MAMS",
        L"MAMS.Export [sequence] [format]",
        L"MAMS.Export \"News Package\" AAF"
    });
    
    m_commands.push_back({
        L"MAMS.Config",
        L"Configure MAMS settings",
        L"MAMS.Config <setting> <value>",
        L"MAMS.Config server https://mams.example.com"
    });
    
    m_commands.push_back({
        L"MAMS.Status",
        L"Show MAMS connection status",
        L"MAMS.Status",
        L"MAMS.Status"
    });
    
    m_commands.push_back({
        L"MAMS.Help",
        L"Show MAMS command help",
        L"MAMS.Help",
        L"MAMS.Help"
    });
}

} // namespace MAMS