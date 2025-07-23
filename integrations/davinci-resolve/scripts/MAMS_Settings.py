#!/usr/bin/env python3
"""
MAMS Settings for DaVinci Resolve
Configuration interface for MAMS integration
"""

import sys
import os
import json
from typing import Dict, Any

# Add utils directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(os.path.dirname(script_dir), 'utils')
sys.path.insert(0, utils_dir)

from mams_client import mams_client

class MAMSSettings:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.mams")
        self.config_file = os.path.join(self.config_dir, "resolve_config.json")
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from config file"""
        default_settings = {
            'server_url': '',
            'api_key': '',
            'username': '',
            'auto_login': False,
            'download_quality': 'proxy',
            'import_location': 'current_bin',
            'metadata_sync': True,
            'proxy_cache_size': '10GB',
            'temp_directory': '',
            'color_management': {
                'auto_apply_luts': False,
                'default_color_space': 'Rec.709',
                'lut_directory': ''
            },
            'timeline_settings': {
                'auto_conform': True,
                'default_frame_rate': '25',
                'track_naming': 'mams_asset_name'
            },
            'sync_settings': {
                'auto_sync_on_save': False,
                'sync_metadata_changes': True,
                'export_proxies': False
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings.update(loaded_settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self) -> bool:
        """Save settings to config file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connection to MAMS server"""
        if not self.settings.get('server_url'):
            print("Server URL not configured")
            return False
        
        # Update mams_client configuration
        mams_client.save_config(
            self.settings['server_url'],
            self.settings.get('api_key', '')
        )
        
        return mams_client.test_connection()
    
    def login(self, username: str, password: str) -> bool:
        """Login to MAMS server"""
        return mams_client.login(username, password)
    
    def get_setting(self, key: str, default=None):
        """Get setting value"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_setting(self, key: str, value: Any):
        """Set setting value"""
        keys = key.split('.')
        setting_dict = self.settings
        
        for k in keys[:-1]:
            if k not in setting_dict:
                setting_dict[k] = {}
            setting_dict = setting_dict[k]
        
        setting_dict[keys[-1]] = value
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self._load_settings()
        # Clear the file to force defaults on next load
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        self.settings = self._load_settings()

def show_settings_interface():
    """Show settings configuration interface"""
    settings = MAMSSettings()
    
    print("MAMS Settings for DaVinci Resolve")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Connection Settings")
        print("2. Import Settings")
        print("3. Color Management")
        print("4. Timeline Settings")
        print("5. Sync Settings")
        print("6. Test Connection")
        print("7. Login to MAMS")
        print("8. Show Current Settings")
        print("9. Reset to Defaults")
        print("0. Save and Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            if settings.save_settings():
                print("✅ Settings saved successfully")
            else:
                print("❌ Failed to save settings")
            break
        elif choice == "1":
            configure_connection(settings)
        elif choice == "2":
            configure_import(settings)
        elif choice == "3":
            configure_color_management(settings)
        elif choice == "4":
            configure_timeline(settings)
        elif choice == "5":
            configure_sync(settings)
        elif choice == "6":
            test_connection_interactive(settings)
        elif choice == "7":
            login_interactive(settings)
        elif choice == "8":
            show_current_settings(settings)
        elif choice == "9":
            reset_settings_interactive(settings)

def configure_connection(settings: MAMSSettings):
    """Configure connection settings"""
    print("\n--- Connection Settings ---")
    
    current_url = settings.get_setting('server_url', '')
    print(f"Current server URL: {current_url}")
    new_url = input("Enter MAMS server URL (or press Enter to keep current): ").strip()
    if new_url:
        settings.set_setting('server_url', new_url)
    
    current_key = settings.get_setting('api_key', '')
    if current_key:
        print("API key is configured")
        change_key = input("Change API key? (y/n): ").strip().lower()
        if change_key == 'y':
            new_key = input("Enter new API key: ").strip()
            settings.set_setting('api_key', new_key)
    else:
        new_key = input("Enter API key (optional): ").strip()
        if new_key:
            settings.set_setting('api_key', new_key)
    
    current_username = settings.get_setting('username', '')
    print(f"Current username: {current_username}")
    new_username = input("Enter username (or press Enter to keep current): ").strip()
    if new_username:
        settings.set_setting('username', new_username)
    
    auto_login = settings.get_setting('auto_login', False)
    print(f"Auto login: {auto_login}")
    new_auto = input("Enable auto login? (y/n): ").strip().lower()
    settings.set_setting('auto_login', new_auto == 'y')

def configure_import(settings: MAMSSettings):
    """Configure import settings"""
    print("\n--- Import Settings ---")
    
    # Download quality
    current_quality = settings.get_setting('download_quality', 'proxy')
    print(f"Current download quality: {current_quality}")
    print("Available qualities: proxy, edit, full")
    new_quality = input("Enter download quality (or press Enter to keep current): ").strip()
    if new_quality and new_quality in ['proxy', 'edit', 'full']:
        settings.set_setting('download_quality', new_quality)
    
    # Import location
    current_location = settings.get_setting('import_location', 'current_bin')
    print(f"Current import location: {current_location}")
    print("Options: current_bin, new_bin, root")
    new_location = input("Enter import location (or press Enter to keep current): ").strip()
    if new_location and new_location in ['current_bin', 'new_bin', 'root']:
        settings.set_setting('import_location', new_location)
    
    # Metadata sync
    metadata_sync = settings.get_setting('metadata_sync', True)
    print(f"Sync metadata: {metadata_sync}")
    new_sync = input("Enable metadata sync? (y/n): ").strip().lower()
    settings.set_setting('metadata_sync', new_sync != 'n')
    
    # Cache size
    current_cache = settings.get_setting('proxy_cache_size', '10GB')
    print(f"Current proxy cache size: {current_cache}")
    new_cache = input("Enter cache size (e.g., 10GB, 500MB): ").strip()
    if new_cache:
        settings.set_setting('proxy_cache_size', new_cache)

def configure_color_management(settings: MAMSSettings):
    """Configure color management settings"""
    print("\n--- Color Management ---")
    
    # Auto apply LUTs
    auto_luts = settings.get_setting('color_management.auto_apply_luts', False)
    print(f"Auto apply LUTs: {auto_luts}")
    new_auto = input("Auto apply LUTs from MAMS? (y/n): ").strip().lower()
    settings.set_setting('color_management.auto_apply_luts', new_auto == 'y')
    
    # Default color space
    current_cs = settings.get_setting('color_management.default_color_space', 'Rec.709')
    print(f"Default color space: {current_cs}")
    new_cs = input("Enter default color space (or press Enter to keep current): ").strip()
    if new_cs:
        settings.set_setting('color_management.default_color_space', new_cs)
    
    # LUT directory
    current_lut_dir = settings.get_setting('color_management.lut_directory', '')
    print(f"LUT directory: {current_lut_dir}")
    new_lut_dir = input("Enter LUT directory path (or press Enter to keep current): ").strip()
    if new_lut_dir:
        settings.set_setting('color_management.lut_directory', new_lut_dir)

def configure_timeline(settings: MAMSSettings):
    """Configure timeline settings"""
    print("\n--- Timeline Settings ---")
    
    # Auto conform
    auto_conform = settings.get_setting('timeline_settings.auto_conform', True)
    print(f"Auto conform frame rates: {auto_conform}")
    new_conform = input("Enable auto conform? (y/n): ").strip().lower()
    settings.set_setting('timeline_settings.auto_conform', new_conform != 'n')
    
    # Default frame rate
    current_fps = settings.get_setting('timeline_settings.default_frame_rate', '25')
    print(f"Default frame rate: {current_fps}")
    new_fps = input("Enter default frame rate (or press Enter to keep current): ").strip()
    if new_fps:
        settings.set_setting('timeline_settings.default_frame_rate', new_fps)
    
    # Track naming
    current_naming = settings.get_setting('timeline_settings.track_naming', 'mams_asset_name')
    print(f"Track naming: {current_naming}")
    print("Options: mams_asset_name, original_filename, custom")
    new_naming = input("Enter track naming option (or press Enter to keep current): ").strip()
    if new_naming and new_naming in ['mams_asset_name', 'original_filename', 'custom']:
        settings.set_setting('timeline_settings.track_naming', new_naming)

def configure_sync(settings: MAMSSettings):
    """Configure sync settings"""
    print("\n--- Sync Settings ---")
    
    # Auto sync on save
    auto_sync = settings.get_setting('sync_settings.auto_sync_on_save', False)
    print(f"Auto sync on save: {auto_sync}")
    new_auto = input("Enable auto sync on save? (y/n): ").strip().lower()
    settings.set_setting('sync_settings.auto_sync_on_save', new_auto == 'y')
    
    # Sync metadata changes
    sync_meta = settings.get_setting('sync_settings.sync_metadata_changes', True)
    print(f"Sync metadata changes: {sync_meta}")
    new_meta = input("Sync metadata changes? (y/n): ").strip().lower()
    settings.set_setting('sync_settings.sync_metadata_changes', new_meta != 'n')
    
    # Export proxies
    export_proxies = settings.get_setting('sync_settings.export_proxies', False)
    print(f"Export proxies to MAMS: {export_proxies}")
    new_export = input("Export proxies to MAMS? (y/n): ").strip().lower()
    settings.set_setting('sync_settings.export_proxies', new_export == 'y')

def test_connection_interactive(settings: MAMSSettings):
    """Test connection interactively"""
    print("\nTesting connection to MAMS...")
    
    if settings.test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed. Check your settings.")

def login_interactive(settings: MAMSSettings):
    """Interactive login"""
    username = input("Username: ").strip()
    if not username:
        print("Username required")
        return
    
    import getpass
    password = getpass.getpass("Password: ")
    
    print("Logging in...")
    if settings.login(username, password):
        print("✅ Login successful!")
        settings.set_setting('username', username)
    else:
        print("❌ Login failed. Check credentials.")

def show_current_settings(settings: MAMSSettings):
    """Display current settings"""
    print("\n--- Current Settings ---")
    
    # Connection
    print(f"Server URL: {settings.get_setting('server_url')}")
    print(f"Username: {settings.get_setting('username')}")
    print(f"API Key: {'***configured***' if settings.get_setting('api_key') else 'not set'}")
    print(f"Auto Login: {settings.get_setting('auto_login')}")
    
    # Import
    print(f"Download Quality: {settings.get_setting('download_quality')}")
    print(f"Import Location: {settings.get_setting('import_location')}")
    print(f"Metadata Sync: {settings.get_setting('metadata_sync')}")
    print(f"Cache Size: {settings.get_setting('proxy_cache_size')}")
    
    # Color
    print(f"Auto Apply LUTs: {settings.get_setting('color_management.auto_apply_luts')}")
    print(f"Default Color Space: {settings.get_setting('color_management.default_color_space')}")
    
    # Timeline
    print(f"Auto Conform: {settings.get_setting('timeline_settings.auto_conform')}")
    print(f"Default FPS: {settings.get_setting('timeline_settings.default_frame_rate')}")
    
    # Sync
    print(f"Auto Sync on Save: {settings.get_setting('sync_settings.auto_sync_on_save')}")
    print(f"Sync Metadata: {settings.get_setting('sync_settings.sync_metadata_changes')}")

def reset_settings_interactive(settings: MAMSSettings):
    """Reset settings interactively"""
    confirm = input("Reset all settings to defaults? This cannot be undone. (y/n): ").strip().lower()
    if confirm == 'y':
        settings.reset_to_defaults()
        print("✅ Settings reset to defaults")

# Main execution
if __name__ == "__main__":
    show_settings_interface()