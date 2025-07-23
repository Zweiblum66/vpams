#!/usr/bin/env python3
"""
MAMS Asset Browser for DaVinci Resolve
Main script for browsing and importing MAMS assets
"""

import sys
import os
import json
from typing import List, Dict, Any

# Add utils directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(os.path.dirname(script_dir), 'utils')
sys.path.insert(0, utils_dir)

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("DaVinci Resolve Script API not available")
    dvr_script = None

from mams_client import mams_client

class MAMSAssetBrowser:
    def __init__(self):
        self.resolve = None
        self.project = None
        self.media_pool = None
        self.current_folder = None
        
        # Initialize Resolve API
        if dvr_script:
            try:
                self.resolve = dvr_script.scriptapp("Resolve")
                if self.resolve:
                    project_manager = self.resolve.GetProjectManager()
                    self.project = project_manager.GetCurrentProject()
                    if self.project:
                        self.media_pool = self.project.GetMediaPool()
                        self.current_folder = self.media_pool.GetCurrentFolder()
            except Exception as e:
                print(f"Error initializing Resolve API: {e}")
    
    def search_assets(self, query: str = "", asset_type: str = "", tags: str = "") -> List[Dict]:
        """Search for assets in MAMS"""
        filters = {}
        if asset_type:
            filters['type'] = asset_type
        if tags:
            filters['tags'] = tags.split(',')
        
        return mams_client.search_assets(query, filters)
    
    def import_asset_to_media_pool(self, asset_id: str, bin_name: str = None) -> bool:
        """Import asset to Resolve Media Pool"""
        if not self.media_pool:
            print("Media Pool not available")
            return False
        
        try:
            # Get asset details
            asset = mams_client.get_asset(asset_id)
            if not asset:
                print(f"Asset {asset_id} not found")
                return False
            
            # Download asset
            print(f"Downloading asset: {asset['name']}")
            local_path = mams_client.download_asset(asset_id, quality='edit')
            if not local_path:
                print("Failed to download asset")
                return False
            
            # Create or find target bin
            target_folder = self.current_folder
            if bin_name:
                # Create new bin or find existing one
                subfolder = self.media_pool.AddSubFolder(target_folder, bin_name)
                if subfolder:
                    target_folder = subfolder
            
            # Prepare import data
            import_data = {
                "FilePath": local_path,
                "ClipName": asset['name']
            }
            
            # Add metadata if available
            metadata = mams_client.get_asset_metadata(asset_id)
            if metadata:
                import_data.update({
                    "Comments": metadata.get('description', ''),
                    "Keywords": ','.join(metadata.get('tags', [])),
                    "Shot": metadata.get('creator', ''),
                    "Scene": metadata.get('location', '')
                })
            
            # Import to Media Pool
            imported_clips = self.media_pool.ImportMedia([import_data])
            
            if imported_clips:
                print(f"Successfully imported: {asset['name']}")
                
                # Set additional properties on imported clip
                for clip in imported_clips:
                    if hasattr(clip, 'SetClipProperty'):
                        # Add MAMS metadata
                        clip.SetClipProperty("Comments", f"MAMS ID: {asset_id}")
                        if metadata.get('description'):
                            clip.SetClipProperty("Notes", metadata['description'])
                
                return True
            else:
                print("Import failed - no clips returned")
                return False
                
        except Exception as e:
            print(f"Import error: {e}")
            return False
    
    def batch_import_assets(self, asset_ids: List[str], bin_name: str = "MAMS Import") -> int:
        """Import multiple assets to Media Pool"""
        success_count = 0
        
        # Create import bin
        if bin_name and self.media_pool:
            import_folder = self.media_pool.AddSubFolder(self.current_folder, bin_name)
            if import_folder:
                self.media_pool.SetCurrentFolder(import_folder)
        
        for asset_id in asset_ids:
            if self.import_asset_to_media_pool(asset_id):
                success_count += 1
        
        print(f"Imported {success_count} of {len(asset_ids)} assets")
        return success_count
    
    def create_timeline_from_assets(self, asset_ids: List[str], timeline_name: str) -> bool:
        """Create timeline and add assets"""
        if not self.project:
            return False
        
        try:
            # Import assets first
            imported_count = self.batch_import_assets(asset_ids, "Timeline Assets")
            if imported_count == 0:
                print("No assets imported, cannot create timeline")
                return False
            
            # Create timeline
            timeline = self.project.CreateEmptyTimeline(timeline_name)
            if not timeline:
                print("Failed to create timeline")
                return False
            
            # Get imported clips from current folder
            clips = self.current_folder.GetClipList()
            
            # Add clips to timeline
            for i, clip in enumerate(clips[-imported_count:]):  # Get last imported clips
                timeline.AppendToTrack([{
                    "mediaPoolItem": clip,
                    "startTC": "01:00:00:00",
                    "endTC": "01:00:10:00"  # 10 second default
                }], 1, 0)  # Video track 1
            
            print(f"Created timeline '{timeline_name}' with {imported_count} clips")
            return True
            
        except Exception as e:
            print(f"Timeline creation error: {e}")
            return False

def show_asset_browser():
    """Show the asset browser interface"""
    browser = MAMSAssetBrowser()
    
    if not browser.resolve:
        print("DaVinci Resolve not available")
        return
    
    if not mams_client.test_connection():
        print("Cannot connect to MAMS server. Please check settings.")
        return
    
    print("MAMS Asset Browser for DaVinci Resolve")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Search assets")
        print("2. Import asset by ID")
        print("3. Batch import assets")
        print("4. Create timeline from assets")
        print("5. Show current project info")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            search_and_display_assets(browser)
        elif choice == "2":
            import_single_asset(browser)
        elif choice == "3":
            batch_import_assets_interactive(browser)
        elif choice == "4":
            create_timeline_interactive(browser)
        elif choice == "5":
            show_project_info(browser)

def search_and_display_assets(browser: MAMSAssetBrowser):
    """Interactive asset search"""
    query = input("Enter search query: ").strip()
    asset_type = input("Asset type (video/audio/image/project, or empty): ").strip()
    tags = input("Tags (comma-separated, or empty): ").strip()
    
    print("\nSearching...")
    assets = browser.search_assets(query, asset_type, tags)
    
    if not assets:
        print("No assets found")
        return
    
    print(f"\nFound {len(assets)} assets:")
    for i, asset in enumerate(assets[:10], 1):  # Show first 10
        print(f"{i:2d}. {asset['name']} ({asset['type']}) - ID: {asset['id']}")
        if asset.get('metadata', {}).get('description'):
            print(f"    {asset['metadata']['description'][:100]}...")
    
    if len(assets) > 10:
        print(f"... and {len(assets) - 10} more")
    
    # Option to import selected assets
    selection = input("\nEnter asset numbers to import (e.g., 1,3,5) or press Enter to skip: ").strip()
    if selection:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_assets = [assets[i]['id'] for i in indices if 0 <= i < len(assets)]
            
            if selected_assets:
                bin_name = input("Enter bin name (or press Enter for current bin): ").strip()
                bin_name = bin_name if bin_name else None
                
                success_count = browser.batch_import_assets(selected_assets, bin_name)
                print(f"Imported {success_count} assets")
        except (ValueError, IndexError):
            print("Invalid selection")

def import_single_asset(browser: MAMSAssetBrowser):
    """Import single asset by ID"""
    asset_id = input("Enter asset ID: ").strip()
    bin_name = input("Enter bin name (or press Enter for current bin): ").strip()
    bin_name = bin_name if bin_name else None
    
    if browser.import_asset_to_media_pool(asset_id, bin_name):
        print("Asset imported successfully")
    else:
        print("Import failed")

def batch_import_assets_interactive(browser: MAMSAssetBrowser):
    """Interactive batch import"""
    asset_ids = input("Enter asset IDs (comma-separated): ").strip().split(',')
    asset_ids = [aid.strip() for aid in asset_ids if aid.strip()]
    
    if not asset_ids:
        print("No asset IDs provided")
        return
    
    bin_name = input("Enter bin name (default: MAMS Import): ").strip()
    bin_name = bin_name if bin_name else "MAMS Import"
    
    success_count = browser.batch_import_assets(asset_ids, bin_name)
    print(f"Imported {success_count} of {len(asset_ids)} assets")

def create_timeline_interactive(browser: MAMSAssetBrowser):
    """Interactive timeline creation"""
    timeline_name = input("Enter timeline name: ").strip()
    if not timeline_name:
        print("Timeline name required")
        return
    
    asset_ids = input("Enter asset IDs (comma-separated): ").strip().split(',')
    asset_ids = [aid.strip() for aid in asset_ids if aid.strip()]
    
    if not asset_ids:
        print("No asset IDs provided")
        return
    
    if browser.create_timeline_from_assets(asset_ids, timeline_name):
        print(f"Timeline '{timeline_name}' created successfully")
    else:
        print("Timeline creation failed")

def show_project_info(browser: MAMSAssetBrowser):
    """Display current project information"""
    if not browser.project:
        print("No project open")
        return
    
    project_name = browser.project.GetName()
    timeline_count = browser.project.GetTimelineCount()
    current_timeline = browser.project.GetCurrentTimeline()
    
    print(f"\nProject: {project_name}")
    print(f"Timelines: {timeline_count}")
    if current_timeline:
        print(f"Current Timeline: {current_timeline.GetName()}")
    
    if browser.media_pool and browser.current_folder:
        clips = browser.current_folder.GetClipList()
        print(f"Clips in current bin: {len(clips) if clips else 0}")

# Main execution
if __name__ == "__main__":
    show_asset_browser()