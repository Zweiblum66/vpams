#!/usr/bin/env python3
"""
MAMS DaVinci Resolve Integration Installer
Installs MAMS scripts and configuration
"""

import os
import sys
import shutil
import platform
import json
from pathlib import Path

class MAMSResolveInstaller:
    def __init__(self):
        self.system = platform.system()
        self.script_dir = Path(__file__).parent
        self.scripts_source = self.script_dir / "scripts"
        self.fusion_source = self.script_dir / "fusion-scripts"
        self.utils_source = self.script_dir / "utils"
        
        # Determine installation paths
        self.resolve_paths = self._get_resolve_paths()
        self.scripts_dest = None
        self.fusion_dest = None
        
    def _get_resolve_paths(self):
        """Get DaVinci Resolve script directories for current OS"""
        if self.system == "Windows":
            appdata = os.environ.get('APPDATA', '')
            base_path = Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support"
            return {
                'scripts': base_path / "Scripts" / "MAMS",
                'fusion': base_path / "Fusion" / "Scripts" / "MAMS"
            }
        elif self.system == "Darwin":  # macOS
            home = Path.home()
            base_path = home / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve"
            return {
                'scripts': base_path / "Scripts" / "MAMS",
                'fusion': base_path / "Fusion" / "Scripts" / "MAMS"
            }
        else:  # Linux
            home = Path.home()
            base_path = home / ".local" / "share" / "DaVinciResolve"
            return {
                'scripts': base_path / "scripts" / "MAMS",
                'fusion': base_path / "Fusion" / "Scripts" / "MAMS"
            }
    
    def check_resolve_installation(self):
        """Check if DaVinci Resolve is installed"""
        print("Checking DaVinci Resolve installation...")
        
        if self.system == "Windows":
            # Check common installation paths
            program_files = [
                "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve",
                "C:\\Program Files (x86)\\Blackmagic Design\\DaVinci Resolve"
            ]
            for path in program_files:
                if os.path.exists(path):
                    print(f"✅ Found DaVinci Resolve at: {path}")
                    return True
        elif self.system == "Darwin":
            # Check Applications folder
            app_path = "/Applications/DaVinci Resolve"
            if os.path.exists(app_path):
                print(f"✅ Found DaVinci Resolve at: {app_path}")
                return True
        else:
            # Linux - check common paths
            linux_paths = [
                "/opt/resolve",
                "/usr/local/resolve",
                os.path.expanduser("~/DaVinci Resolve")
            ]
            for path in linux_paths:
                if os.path.exists(path):
                    print(f"✅ Found DaVinci Resolve at: {path}")
                    return True
        
        print("⚠️  DaVinci Resolve installation not found")
        print("   Installation will continue, but please ensure Resolve is installed")
        return False
    
    def create_directories(self):
        """Create installation directories"""
        print("Creating installation directories...")
        
        try:
            # Create scripts directory
            self.scripts_dest = self.resolve_paths['scripts']
            self.scripts_dest.mkdir(parents=True, exist_ok=True)
            print(f"✅ Scripts directory: {self.scripts_dest}")
            
            # Create fusion scripts directory
            self.fusion_dest = self.resolve_paths['fusion']
            self.fusion_dest.mkdir(parents=True, exist_ok=True)
            print(f"✅ Fusion scripts directory: {self.fusion_dest}")
            
            return True
        except Exception as e:\n            print(f"❌ Failed to create directories: {e}\")\n            return False\n    \n    def install_scripts(self):\n        \"\"\"Install Python scripts\"\"\"\n        print(\"Installing Python scripts...\")\n        \n        try:\n            # Install main scripts\n            for script_file in self.scripts_source.glob(\"*.py\"):\n                dest_file = self.scripts_dest / script_file.name\n                shutil.copy2(script_file, dest_file)\n                print(f\"✅ Installed: {script_file.name}\")\n            \n            # Install utils\n            utils_dest = self.scripts_dest / \"utils\"\n            if utils_dest.exists():\n                shutil.rmtree(utils_dest)\n            shutil.copytree(self.utils_source, utils_dest)\n            print(f\"✅ Installed utils directory\")\n            \n            # Make scripts executable on Unix-like systems\n            if self.system in [\"Darwin\", \"Linux\"]:\n                for script_file in self.scripts_dest.glob(\"*.py\"):\n                    os.chmod(script_file, 0o755)\n            \n            return True\n        except Exception as e:\n            print(f\"❌ Failed to install scripts: {e}\")\n            return False\n    \n    def install_fusion_scripts(self):\n        \"\"\"Install Fusion Lua scripts\"\"\"\n        print(\"Installing Fusion scripts...\")\n        \n        try:\n            for script_file in self.fusion_source.glob(\"*.lua\"):\n                dest_file = self.fusion_dest / script_file.name\n                shutil.copy2(script_file, dest_file)\n                print(f\"✅ Installed: {script_file.name}\")\n            \n            return True\n        except Exception as e:\n            print(f\"❌ Failed to install Fusion scripts: {e}\")\n            return False\n    \n    def create_config_template(self):\n        \"\"\"Create configuration template\"\"\"\n        print(\"Creating configuration template...\")\n        \n        try:\n            config_dir = Path.home() / \".mams\"\n            config_dir.mkdir(exist_ok=True)\n            \n            config_file = config_dir / \"resolve_config.json\"\n            \n            if not config_file.exists():\n                config_template = {\n                    \"server_url\": \"http://localhost:8000\",\n                    \"api_key\": \"\",\n                    \"username\": \"\",\n                    \"auto_login\": False,\n                    \"download_quality\": \"proxy\",\n                    \"import_location\": \"current_bin\",\n                    \"metadata_sync\": True,\n                    \"proxy_cache_size\": \"10GB\",\n                    \"temp_directory\": \"\",\n                    \"color_management\": {\n                        \"auto_apply_luts\": False,\n                        \"default_color_space\": \"Rec.709\",\n                        \"lut_directory\": \"\"\n                    },\n                    \"timeline_settings\": {\n                        \"auto_conform\": True,\n                        \"default_frame_rate\": \"25\",\n                        \"track_naming\": \"mams_asset_name\"\n                    },\n                    \"sync_settings\": {\n                        \"auto_sync_on_save\": False,\n                        \"sync_metadata_changes\": True,\n                        \"export_proxies\": False\n                    }\n                }\n                \n                with open(config_file, 'w') as f:\n                    json.dump(config_template, f, indent=2)\n                \n                print(f\"✅ Created config template: {config_file}\")\n            else:\n                print(f\"✅ Config file already exists: {config_file}\")\n            \n            return True\n        except Exception as e:\n            print(f\"❌ Failed to create config: {e}\")\n            return False\n    \n    def install_menu_items(self):\n        \"\"\"Install menu items for easy access\"\"\"\n        print(\"Installing menu items...\")\n        \n        try:\n            # Create menu structure file\n            menu_file = self.scripts_dest / \"__menu__.py\"\n            \n            menu_content = '''\n#!/usr/bin/env python3\n\"\"\"\nMAMS Menu Structure for DaVinci Resolve\nDefines menu items for MAMS integration\n\"\"\"\n\n# Menu structure for DaVinci Resolve\nMENU_ITEMS = {\n    \"MAMS\": {\n        \"Asset Browser\": \"MAMS_Asset_Browser.py\",\n        \"Project Sync\": \"MAMS_Project_Sync.py\", \n        \"Settings\": \"MAMS_Settings.py\",\n        \"separator\": True,\n        \"Help\": \"MAMS_Help.py\"\n    }\n}\n\n# For Fusion page\nFUSION_MENU_ITEMS = {\n    \"MAMS\": {\n        \"Composition Browser\": \"MAMS_Comp_Browser.lua\",\n        \"Import Assets\": \"MAMS_Import.lua\"\n    }\n}\n'''\n            \n            with open(menu_file, 'w') as f:\n                f.write(menu_content)\n            \n            print(f\"✅ Created menu structure\")\n            return True\n        except Exception as e:\n            print(f\"❌ Failed to install menu items: {e}\")\n            return False\n    \n    def create_desktop_shortcuts(self):\n        \"\"\"Create desktop shortcuts (optional)\"\"\"\n        if input(\"Create desktop shortcuts? (y/n): \").lower() != 'y':\n            return True\n        \n        print(\"Creating desktop shortcuts...\")\n        \n        try:\n            desktop = Path.home() / \"Desktop\"\n            \n            if self.system == \"Windows\":\n                # Create .bat files for Windows\n                shortcuts = {\n                    \"MAMS Asset Browser.bat\": f'python \"{self.scripts_dest / \"MAMS_Asset_Browser.py\"}\"',\n                    \"MAMS Settings.bat\": f'python \"{self.scripts_dest / \"MAMS_Settings.py\"}\"'\n                }\n                \n                for name, command in shortcuts.items():\n                    shortcut_file = desktop / name\n                    with open(shortcut_file, 'w') as f:\n                        f.write(f\"@echo off\\n{command}\\npause\")\n                    print(f\"✅ Created: {name}\")\n            \n            elif self.system == \"Darwin\":\n                # Create .command files for macOS\n                shortcuts = {\n                    \"MAMS Asset Browser.command\": f'#!/bin/bash\\npython3 \"{self.scripts_dest / \"MAMS_Asset_Browser.py\"}\"',\n                    \"MAMS Settings.command\": f'#!/bin/bash\\npython3 \"{self.scripts_dest / \"MAMS_Settings.py\"}\"'\n                }\n                \n                for name, command in shortcuts.items():\n                    shortcut_file = desktop / name\n                    with open(shortcut_file, 'w') as f:\n                        f.write(command)\n                    os.chmod(shortcut_file, 0o755)\n                    print(f\"✅ Created: {name}\")\n            \n            else:\n                # Create .desktop files for Linux\n                shortcuts = {\n                    \"MAMS Asset Browser.desktop\": {\n                        \"Name\": \"MAMS Asset Browser\",\n                        \"Exec\": f'python3 \"{self.scripts_dest / \"MAMS_Asset_Browser.py\"}\"',\n                        \"Type\": \"Application\",\n                        \"Terminal\": \"true\"\n                    },\n                    \"MAMS Settings.desktop\": {\n                        \"Name\": \"MAMS Settings\",\n                        \"Exec\": f'python3 \"{self.scripts_dest / \"MAMS_Settings.py\"}\"',\n                        \"Type\": \"Application\",\n                        \"Terminal\": \"true\"\n                    }\n                }\n                \n                for filename, properties in shortcuts.items():\n                    shortcut_file = desktop / filename\n                    with open(shortcut_file, 'w') as f:\n                        f.write(\"[Desktop Entry]\\n\")\n                        for key, value in properties.items():\n                            f.write(f\"{key}={value}\\n\")\n                    os.chmod(shortcut_file, 0o755)\n                    print(f\"✅ Created: {filename}\")\n            \n            return True\n        except Exception as e:\n            print(f\"❌ Failed to create shortcuts: {e}\")\n            return False\n    \n    def verify_installation(self):\n        \"\"\"Verify installation was successful\"\"\"\n        print(\"Verifying installation...\")\n        \n        success = True\n        \n        # Check scripts\n        required_scripts = [\"MAMS_Asset_Browser.py\", \"MAMS_Project_Sync.py\", \"MAMS_Settings.py\"]\n        for script in required_scripts:\n            script_path = self.scripts_dest / script\n            if script_path.exists():\n                print(f\"✅ {script}\")\n            else:\n                print(f\"❌ {script} not found\")\n                success = False\n        \n        # Check utils\n        utils_path = self.scripts_dest / \"utils\" / \"mams_client.py\"\n        if utils_path.exists():\n            print(f\"✅ Utils directory\")\n        else:\n            print(f\"❌ Utils directory not found\")\n            success = False\n        \n        # Check Fusion scripts\n        fusion_script = self.fusion_dest / \"MAMS_Comp_Browser.lua\"\n        if fusion_script.exists():\n            print(f\"✅ Fusion scripts\")\n        else:\n            print(f\"❌ Fusion scripts not found\")\n            success = False\n        \n        # Check config\n        config_file = Path.home() / \".mams\" / \"resolve_config.json\"\n        if config_file.exists():\n            print(f\"✅ Configuration file\")\n        else:\n            print(f\"❌ Configuration file not found\")\n            success = False\n        \n        return success\n    \n    def show_post_install_instructions(self):\n        \"\"\"Show post-installation instructions\"\"\"\n        print(\"\\n\" + \"=\" * 60)\n        print(\"MAMS DaVinci Resolve Integration - Installation Complete\")\n        print(\"=\" * 60)\n        \n        if self.system == \"Windows\":\n            scripts_path = self.scripts_dest\n        else:\n            scripts_path = self.scripts_dest\n        \n        print(f\"\\n📁 Scripts installed to: {scripts_path}\")\n        print(f\"📁 Fusion scripts installed to: {self.fusion_dest}\")\n        print(f\"📁 Configuration: {Path.home() / '.mams' / 'resolve_config.json'}\")\n        \n        print(\"\\n🚀 Next Steps:\")\n        print(\"1. Start DaVinci Resolve\")\n        print(\"2. Go to Workspace > Scripts > MAMS > Settings\")\n        print(\"3. Configure your MAMS server connection\")\n        print(\"4. Test the connection\")\n        print(\"5. Start using MAMS > Asset Browser to import assets\")\n        \n        print(\"\\n📖 Available Scripts:\")\n        print(\"• Asset Browser - Browse and import MAMS assets\")\n        print(\"• Project Sync - Synchronize projects with MAMS\")\n        print(\"• Settings - Configure MAMS connection\")\n        \n        print(\"\\n🎨 Fusion Integration:\")\n        print(\"• Switch to Fusion page\")\n        print(\"• Access MAMS tools from Scripts menu\")\n        print(\"• Use Composition Browser for asset management\")\n        \n        print(\"\\n📚 Documentation:\")\n        print(\"• README.md - Complete usage guide\")\n        print(\"• API examples in the documentation\")\n        print(\"• Support: https://docs.mams.io/resolve\")\n        \n        print(\"\\n✨ Installation completed successfully!\")\n    \n    def run_installation(self):\n        \"\"\"Run the complete installation process\"\"\"\n        print(\"MAMS DaVinci Resolve Integration Installer\")\n        print(\"=\" * 50)\n        print(f\"Operating System: {self.system}\")\n        print(f\"Installation Source: {self.script_dir}\")\n        \n        # Check prerequisites\n        self.check_resolve_installation()\n        \n        # Confirm installation\n        print(f\"\\nInstallation paths:\")\n        print(f\"Scripts: {self.resolve_paths['scripts']}\")\n        print(f\"Fusion: {self.resolve_paths['fusion']}\")\n        \n        if input(\"\\nProceed with installation? (y/n): \").lower() != 'y':\n            print(\"Installation cancelled\")\n            return False\n        \n        # Run installation steps\n        steps = [\n            (\"Creating directories\", self.create_directories),\n            (\"Installing scripts\", self.install_scripts),\n            (\"Installing Fusion scripts\", self.install_fusion_scripts),\n            (\"Creating configuration\", self.create_config_template),\n            (\"Installing menu items\", self.install_menu_items),\n            (\"Creating shortcuts\", self.create_desktop_shortcuts),\n            (\"Verifying installation\", self.verify_installation)\n        ]\n        \n        for step_name, step_func in steps:\n            print(f\"\\n{step_name}...\")\n            if not step_func():\n                print(f\"❌ Installation failed at: {step_name}\")\n                return False\n        \n        # Show post-install instructions\n        self.show_post_install_instructions()\n        \n        return True\n\ndef main():\n    \"\"\"Main installation function\"\"\"\n    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:\n        print(\"MAMS DaVinci Resolve Integration Installer\")\n        print(\"Usage: python install.py [options]\")\n        print(\"Options:\")\n        print(\"  --help, -h    Show this help message\")\n        print(\"  --uninstall   Uninstall MAMS integration\")\n        return\n    \n    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':\n        print(\"Uninstall functionality not implemented yet\")\n        return\n    \n    installer = MAMSResolveInstaller()\n    \n    try:\n        success = installer.run_installation()\n        sys.exit(0 if success else 1)\n    except KeyboardInterrupt:\n        print(\"\\n\\nInstallation cancelled by user\")\n        sys.exit(1)\n    except Exception as e:\n        print(f\"\\n\\nInstallation failed with error: {e}\")\n        sys.exit(1)\n\nif __name__ == \"__main__\":\n    main()