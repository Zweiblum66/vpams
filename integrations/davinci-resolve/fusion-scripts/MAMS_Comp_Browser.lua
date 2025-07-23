-- MAMS Composition Browser for Fusion
-- Browse and import MAMS assets in Fusion page

local json = require("json")

-- MAMS Client functions
local MAMSClient = {}

function MAMSClient:new()
    local client = {}
    setmetatable(client, self)
    self.__index = self
    
    client.base_url = ""
    client.api_key = ""
    client.access_token = ""
    
    -- Load configuration
    client:loadConfig()
    
    return client
end

function MAMSClient:loadConfig()
    local config_path = os.getenv("HOME") .. "/.mams/resolve_config.json"
    local file = io.open(config_path, "r")
    
    if file then
        local content = file:read("*all")
        file:close()
        
        local config = json.decode(content)
        if config then
            self.base_url = config.server_url or ""
            self.api_key = config.api_key or ""
            self.access_token = config.access_token or ""
        end
    end
end

function MAMSClient:request(method, endpoint, data)
    -- Basic HTTP request implementation
    -- Note: Fusion's HTTP capabilities are limited
    -- This would need to be implemented using external tools or libraries
    
    local url = self.base_url .. endpoint
    local headers = {
        ["Content-Type"] = "application/json",
        ["User-Agent"] = "MAMS-Fusion/1.0"
    }
    
    if self.api_key ~= "" then
        headers["X-API-Key"] = self.api_key
    elseif self.access_token ~= "" then
        headers["Authorization"] = "Bearer " .. self.access_token
    end
    
    -- Placeholder for actual HTTP implementation
    print("Making " .. method .. " request to " .. url)
    
    return nil -- Would return actual response
end

function MAMSClient:searchAssets(query, filters)
    local params = "?q=" .. (query or "")
    
    if filters then
        for key, value in pairs(filters) do
            params = params .. "&" .. key .. "=" .. tostring(value)
        end
    end
    
    return self:request("GET", "/api/v1/assets/search" .. params)
end

function MAMSClient:getAsset(asset_id)
    return self:request("GET", "/api/v1/assets/" .. asset_id)
end

function MAMSClient:downloadAsset(asset_id, quality)
    quality = quality or "proxy"
    return self:request("GET", "/api/v1/assets/" .. asset_id .. "/download?quality=" .. quality)
end

-- UI Functions
local UI = {}

function UI:createWindow()
    local disp = fu.UIDispatcher
    local ui = disp:AddWindow({
        ID = "MAMSBrowser",
        WindowTitle = "MAMS Asset Browser",
        Geometry = {100, 100, 800, 600},
        
        ui:VGroup{
            -- Search section
            ui:HGroup{
                ui:Label{Text = "Search:", Weight = 0.1},
                ui:LineEdit{
                    ID = "SearchInput",
                    PlaceholderText = "Enter search terms...",
                    Weight = 0.7
                },
                ui:Button{
                    ID = "SearchButton",
                    Text = "Search",
                    Weight = 0.2
                }
            },
            
            -- Filters section
            ui:HGroup{
                ui:Label{Text = "Type:", Weight = 0.1},
                ui:ComboBox{
                    ID = "TypeFilter",
                    Weight = 0.2
                },
                ui:Label{Text = "Tags:", Weight = 0.1},
                ui:LineEdit{
                    ID = "TagsInput",
                    PlaceholderText = "Comma-separated tags",
                    Weight = 0.4
                },
                ui:Button{
                    ID = "ClearFilters",
                    Text = "Clear",
                    Weight = 0.2
                }
            },
            
            -- Results section
            ui:Tree{
                ID = "ResultsTree",
                SortingEnabled = true,
                RootIsDecorated = false,
                SelectionMode = "ExtendedSelection",
                HeaderHidden = false
            },
            
            -- Preview section
            ui:HGroup{
                ui:VGroup{
                    ui:Label{Text = "Preview:", Weight = 0.1},
                    ui:Label{
                        ID = "PreviewImage",
                        Text = "No preview available",
                        Alignment = {AlignHCenter = true, AlignVCenter = true},
                        Weight = 0.9
                    }
                },
                ui:VGroup{
                    ui:Label{Text = "Details:", Weight = 0.1},
                    ui:TextEdit{
                        ID = "DetailsText",
                        ReadOnly = true,
                        PlainText = "Select an asset to view details",
                        Weight = 0.9
                    }
                }
            },
            
            -- Action buttons
            ui:HGroup{
                ui:Button{
                    ID = "ImportButton",
                    Text = "Import to Composition",
                    Enabled = false
                },
                ui:Button{
                    ID = "ImportLoaderButton",
                    Text = "Import as Loader",
                    Enabled = false
                },
                ui:Button{
                    ID = "DownloadButton",
                    Text = "Download",
                    Enabled = false
                },
                ui:HSpacer{},
                ui:Button{
                    ID = "RefreshButton",
                    Text = "Refresh"
                },
                ui:Button{
                    ID = "SettingsButton",
                    Text = "Settings"
                },
                ui:Button{
                    ID = "CloseButton",
                    Text = "Close"
                }
            }
        }
    })
    
    return ui
end

function UI:setupEventHandlers(win)
    local function OnSearchButton(ev)
        self:performSearch(win)
    end
    
    local function OnResultsTreeItemClicked(ev)
        self:updatePreview(win, ev)
    end
    
    local function OnImportButton(ev)
        self:importSelectedAssets(win)
    end
    
    local function OnImportLoaderButton(ev)
        self:importAsLoader(win)
    end
    
    local function OnDownloadButton(ev)
        self:downloadSelectedAssets(win)
    end
    
    local function OnRefreshButton(ev)
        self:refreshResults(win)
    end
    
    local function OnSettingsButton(ev)
        self:showSettings(win)
    end
    
    local function OnCloseButton(ev)
        win:Hide()
    end
    
    local function OnClose(ev)
        win:Hide()
    end
    
    win.On.SearchButton.Clicked = OnSearchButton
    win.On.ResultsTree.ItemClicked = OnResultsTreeItemClicked
    win.On.ImportButton.Clicked = OnImportButton
    win.On.ImportLoaderButton.Clicked = OnImportLoaderButton
    win.On.DownloadButton.Clicked = OnDownloadButton
    win.On.RefreshButton.Clicked = OnRefreshButton
    win.On.SettingsButton.Clicked = OnSettingsButton
    win.On.CloseButton.Clicked = OnCloseButton
    win.On.MAMSBrowser.Close = OnClose
end

function UI:performSearch(win)
    local search_query = win:GetData("SearchInput.Text")
    local asset_type = win:GetData("TypeFilter.CurrentText")
    local tags = win:GetData("TagsInput.Text")
    
    print("Searching for: " .. search_query)
    
    -- Clear current results
    win:GetItems("ResultsTree"):Clear()
    
    -- Perform search (placeholder)
    local results = {
        {
            id = "asset_1",
            name = "Interview_Setup_001.mov",
            type = "video",
            duration = "00:02:30",
            resolution = "1920x1080",
            tags = {"interview", "setup", "wide"},
            description = "Wide shot of interview setup"
        },
        {
            id = "asset_2", 
            name = "Logo_Animation.mov",
            type = "video",
            duration = "00:00:05",
            resolution = "1920x1080",
            tags = {"logo", "animation", "branding"},
            description = "Company logo animation sequence"
        }
    }
    
    -- Populate results tree
    for i, asset in ipairs(results) do
        local item = win:GetItems("ResultsTree"):NewItem()
        item.Text[0] = asset.name
        item.Text[1] = asset.type
        item.Text[2] = asset.duration
        item.Text[3] = asset.resolution
        item.Text[4] = table.concat(asset.tags, ", ")
        item.Data = asset
        win:GetItems("ResultsTree"):AddTopLevelItem(item)
    end
    
    print("Found " .. #results .. " assets")
end

function UI:updatePreview(win, ev)
    local selected_items = win:GetItems("ResultsTree"):SelectedItems()
    
    if #selected_items > 0 then
        local asset = selected_items[1].Data
        
        -- Update details
        local details = string.format(
            "Name: %s\nType: %s\nDuration: %s\nResolution: %s\nTags: %s\nDescription: %s",
            asset.name,
            asset.type,
            asset.duration,
            asset.resolution,
            table.concat(asset.tags, ", "),
            asset.description
        )
        
        win:SetData("DetailsText.PlainText", details)
        
        -- Enable action buttons
        win:SetData("ImportButton.Enabled", true)
        win:SetData("ImportLoaderButton.Enabled", true)
        win:SetData("DownloadButton.Enabled", true)
    else
        win:SetData("DetailsText.PlainText", "Select an asset to view details")
        win:SetData("ImportButton.Enabled", false)
        win:SetData("ImportLoaderButton.Enabled", false)
        win:SetData("DownloadButton.Enabled", false)
    end
end

function UI:importSelectedAssets(win)
    local selected_items = win:GetItems("ResultsTree"):SelectedItems()
    
    if #selected_items == 0 then
        print("No assets selected")
        return
    end
    
    local comp = fu:GetCurrentComp()
    if not comp then
        print("No composition open")
        return
    end
    
    for i, item in ipairs(selected_items) do
        local asset = item.Data
        self:importAssetToComp(comp, asset)
    end
end

function UI:importAsLoader(win)
    local selected_items = win:GetItems("ResultsTree"):SelectedItems()
    
    if #selected_items == 0 then
        print("No asset selected")
        return
    end
    
    local comp = fu:GetCurrentComp()
    if not comp then
        print("No composition open")
        return
    end
    
    local asset = selected_items[1].Data
    self:createLoaderFromAsset(comp, asset)
end

function UI:downloadSelectedAssets(win)
    local selected_items = win:GetItems("ResultsTree"):SelectedItems()
    
    if #selected_items == 0 then
        print("No assets selected")
        return
    end
    
    for i, item in ipairs(selected_items) do
        local asset = item.Data
        self:downloadAsset(asset)
    end
end

function UI:refreshResults(win)
    self:performSearch(win)
end

function UI:showSettings(win)
    -- Placeholder for settings dialog
    print("Opening settings...")
end

function UI:importAssetToComp(comp, asset)
    print("Importing asset: " .. asset.name)
    
    -- Download asset first (placeholder)
    local local_path = "/tmp/mams_assets/" .. asset.name
    
    -- Create Loader node
    local loader = comp:AddTool("Loader", -32768, -32768)
    loader:LoadFile(local_path)
    loader:SetAttrs({TOOLS_Name = "MAMS_" .. asset.name})
    
    -- Set metadata
    loader:SetData("MAMS.AssetID", asset.id)
    loader:SetData("MAMS.AssetName", asset.name)
    loader:SetData("MAMS.Tags", table.concat(asset.tags, ","))
    
    print("Created Loader node for: " .. asset.name)
end

function UI:createLoaderFromAsset(comp, asset)
    self:importAssetToComp(comp, asset)
end

function UI:downloadAsset(asset)
    print("Downloading asset: " .. asset.name)
    -- Placeholder for download functionality
end

-- Main function
function ShowMAMSBrowser()
    local mams_client = MAMSClient:new()
    local ui_manager = UI
    
    -- Create and show window
    local win = ui_manager:createWindow()
    ui_manager:setupEventHandlers(win)
    
    -- Setup tree headers
    local tree = win:GetItems("ResultsTree")
    tree:SetHeaderLabels({"Name", "Type", "Duration", "Resolution", "Tags"})
    
    -- Setup type filter
    local type_filter = win:GetItems("TypeFilter")
    type_filter:AddItems({"All", "video", "audio", "image", "project", "sequence"})
    
    win:Show()
    win:Raise()
    
    print("MAMS Asset Browser opened")
end

-- Export main function
_G.ShowMAMSBrowser = ShowMAMSBrowser

-- Auto-run if executed directly
if arg and arg[0] and arg[0]:match("MAMS_Comp_Browser%.lua$") then
    ShowMAMSBrowser()
end