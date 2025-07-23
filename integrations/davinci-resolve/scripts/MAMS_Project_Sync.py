#!/usr/bin/env python3
"""
MAMS Project Sync for DaVinci Resolve
Synchronize Resolve projects with MAMS
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

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

class MAMSProjectSync:
    def __init__(self):
        self.resolve = None
        self.project_manager = None
        self.current_project = None
        
        # Initialize Resolve API
        if dvr_script:
            try:
                self.resolve = dvr_script.scriptapp("Resolve")
                if self.resolve:
                    self.project_manager = self.resolve.GetProjectManager()
                    self.current_project = self.project_manager.GetCurrentProject()
            except Exception as e:
                print(f"Error initializing Resolve API: {e}")
    
    def export_project_to_mams(self) -> Optional[str]:
        """Export current Resolve project to MAMS"""
        if not self.current_project:
            print("No project open")
            return None
        
        try:
            # Gather project information
            project_data = self._gather_project_data()
            
            # Create project in MAMS
            project_id = mams_client.create_project(project_data)
            if project_id:
                print(f"Project exported to MAMS with ID: {project_id}")
                
                # Store MAMS project ID in project metadata
                self.current_project.SetMetadata("MAMS_Project_ID", project_id)
                
                return project_id
            else:
                print("Failed to create project in MAMS")
                return None
                
        except Exception as e:
            print(f"Export error: {e}")
            return None
    
    def sync_project_with_mams(self, project_id: str = None) -> bool:
        """Sync current project with existing MAMS project"""
        if not self.current_project:
            print("No project open")
            return False
        
        try:
            # Get MAMS project ID
            if not project_id:
                project_id = self.current_project.GetMetadata("MAMS_Project_ID")
            
            if not project_id:
                print("No MAMS project ID found. Use export_project_to_mams first.")
                return False
            
            # Gather current project data
            project_data = self._gather_project_data()
            project_data['id'] = project_id
            
            # Sync with MAMS
            success = mams_client.sync_project(project_data)
            if success:
                print("Project synchronized with MAMS")
                return True
            else:
                print("Failed to sync project with MAMS")
                return False
                
        except Exception as e:
            print(f"Sync error: {e}")
            return False
    
    def import_project_from_mams(self, project_id: str) -> bool:
        """Import project from MAMS to Resolve"""
        try:
            # Get project data from MAMS
            projects = mams_client.get_projects()
            project_data = None
            
            for project in projects:
                if project.get('id') == project_id:
                    project_data = project
                    break
            
            if not project_data:
                print(f"Project {project_id} not found in MAMS")
                return False
            
            # Create new Resolve project
            new_project = self.project_manager.CreateProject(project_data['name'])
            if not new_project:
                print("Failed to create Resolve project")
                return False
            
            # Set project metadata
            new_project.SetMetadata("MAMS_Project_ID", project_id)
            new_project.SetMetadata("MAMS_Imported", "true")
            new_project.SetMetadata("Import_Date", datetime.now().isoformat())
            
            # Load project into current session
            self.project_manager.LoadProject(project_data['name'])
            self.current_project = self.project_manager.GetCurrentProject()
            
            # Import project assets
            if 'assets' in project_data:
                self._import_project_assets(project_data['assets'])
            
            # Create timelines
            if 'timelines' in project_data:
                self._import_project_timelines(project_data['timelines'])
            
            print(f"Project '{project_data['name']}' imported from MAMS")
            return True
            
        except Exception as e:
            print(f"Import error: {e}")
            return False
    
    def export_timeline_to_mams(self, timeline_name: str = None) -> Optional[str]:
        """Export timeline to MAMS"""
        if not self.current_project:
            return None
        
        try:
            timeline = None
            if timeline_name:
                # Find specific timeline
                for i in range(self.current_project.GetTimelineCount()):
                    tl = self.current_project.GetTimelineByIndex(i + 1)
                    if tl and tl.GetName() == timeline_name:
                        timeline = tl
                        break
            else:
                # Use current timeline
                timeline = self.current_project.GetCurrentTimeline()
            
            if not timeline:
                print("No timeline found")
                return None
            
            # Gather timeline data
            timeline_data = self._gather_timeline_data(timeline)
            
            # Export to MAMS
            response = mams_client._request('POST', '/api/v1/timelines', json=timeline_data)
            timeline_id = response.json().get('id')
            
            if timeline_id:
                print(f"Timeline exported to MAMS with ID: {timeline_id}")
                return timeline_id
            
            return None
            
        except Exception as e:
            print(f"Timeline export error: {e}")
            return None
    
    def _gather_project_data(self) -> Dict[str, Any]:
        """Gather comprehensive project data"""
        project_data = {
            'name': self.current_project.GetName(),
            'created_at': datetime.now().isoformat(),
            'resolve_settings': {},
            'timelines': [],
            'bins': [],
            'assets': []
        }
        
        # Get project settings
        project_data['resolve_settings'] = {
            'frame_rate': self.current_project.GetSetting('timelineFrameRate'),
            'resolution_width': self.current_project.GetSetting('timelineResolutionWidth'),
            'resolution_height': self.current_project.GetSetting('timelineResolutionHeight'),
            'pixel_aspect_ratio': self.current_project.GetSetting('timelinePixelAspectRatio')
        }
        
        # Get timelines
        for i in range(self.current_project.GetTimelineCount()):
            timeline = self.current_project.GetTimelineByIndex(i + 1)
            if timeline:
                timeline_data = self._gather_timeline_data(timeline)
                project_data['timelines'].append(timeline_data)
        
        # Get media pool structure
        media_pool = self.current_project.GetMediaPool()
        if media_pool:
            root_folder = media_pool.GetRootFolder()
            project_data['bins'] = self._gather_folder_structure(root_folder)
            project_data['assets'] = self._gather_media_pool_assets(media_pool)
        
        return project_data
    
    def _gather_timeline_data(self, timeline) -> Dict[str, Any]:
        """Gather timeline data including tracks and clips"""
        timeline_data = {
            'name': timeline.GetName(),
            'frame_rate': timeline.GetSetting('timelineFrameRate'),
            'start_frame': timeline.GetStartFrame(),
            'end_frame': timeline.GetEndFrame(),
            'video_tracks': [],
            'audio_tracks': []
        }
        
        # Get video tracks
        video_track_count = timeline.GetTrackCount('video')
        for track_index in range(1, video_track_count + 1):
            clips = timeline.GetItemsInTrack('video', track_index)
            track_data = {
                'index': track_index,
                'clips': []
            }
            
            if clips:
                for clip in clips:
                    clip_data = self._gather_clip_data(clip)
                    track_data['clips'].append(clip_data)
            
            timeline_data['video_tracks'].append(track_data)
        
        # Get audio tracks
        audio_track_count = timeline.GetTrackCount('audio')
        for track_index in range(1, audio_track_count + 1):
            clips = timeline.GetItemsInTrack('audio', track_index)
            track_data = {
                'index': track_index,
                'clips': []
            }
            
            if clips:
                for clip in clips:
                    clip_data = self._gather_clip_data(clip)
                    track_data['clips'].append(clip_data)
            
            timeline_data['audio_tracks'].append(track_data)
        
        return timeline_data
    
    def _gather_clip_data(self, clip) -> Dict[str, Any]:
        """Gather individual clip data"""
        clip_data = {
            'name': clip.GetName(),
            'start_frame': clip.GetStart(),
            'end_frame': clip.GetEnd(),
            'duration': clip.GetDuration(),
            'left_offset': clip.GetLeftOffset(),
            'right_offset': clip.GetRightOffset()
        }
        
        # Get media pool item if available
        media_pool_item = clip.GetMediaPoolItem()
        if media_pool_item:
            clip_data['media_pool_item'] = {
                'name': media_pool_item.GetName(),
                'file_path': media_pool_item.GetClipProperty('File Path'),
                'duration': media_pool_item.GetClipProperty('Duration'),
                'frame_rate': media_pool_item.GetClipProperty('FPS')
            }
        
        return clip_data
    
    def _gather_folder_structure(self, folder, path="") -> List[Dict[str, Any]]:
        """Recursively gather media pool folder structure"""
        folders = []
        
        folder_data = {
            'name': folder.GetName(),
            'path': path,
            'subfolders': [],
            'clips': []
        }
        
        # Get subfolders
        subfolders = folder.GetSubFolderList()
        if subfolders:
            for subfolder in subfolders:
                subfolder_path = f"{path}/{subfolder.GetName()}" if path else subfolder.GetName()
                folder_data['subfolders'].extend(self._gather_folder_structure(subfolder, subfolder_path))
        
        # Get clips in this folder
        clips = folder.GetClipList()
        if clips:
            for clip in clips:
                clip_data = {
                    'name': clip.GetName(),
                    'file_path': clip.GetClipProperty('File Path'),
                    'duration': clip.GetClipProperty('Duration'),
                    'type': clip.GetClipProperty('Type')
                }
                folder_data['clips'].append(clip_data)
        
        folders.append(folder_data)
        return folders
    
    def _gather_media_pool_assets(self, media_pool) -> List[Dict[str, Any]]:
        """Gather all assets in media pool"""
        assets = []
        
        def process_folder(folder):
            clips = folder.GetClipList()
            if clips:
                for clip in clips:
                    asset_data = {
                        'name': clip.GetName(),
                        'file_path': clip.GetClipProperty('File Path'),
                        'duration': clip.GetClipProperty('Duration'),
                        'frame_rate': clip.GetClipProperty('FPS'),
                        'type': clip.GetClipProperty('Type'),
                        'folder_path': self._get_folder_path(folder)
                    }
                    assets.append(asset_data)
            
            # Process subfolders
            subfolders = folder.GetSubFolderList()
            if subfolders:
                for subfolder in subfolders:
                    process_folder(subfolder)
        
        root_folder = media_pool.GetRootFolder()
        process_folder(root_folder)
        
        return assets
    
    def _get_folder_path(self, folder) -> str:
        """Get full path of folder"""
        path_parts = []
        current_folder = folder
        
        while current_folder and current_folder.GetName() != "Master":
            path_parts.insert(0, current_folder.GetName())
            # Note: GetParentFolder might not be available in all Resolve versions
            # This is a simplified implementation
            break
        
        return "/".join(path_parts)
    
    def _import_project_assets(self, assets: List[Dict[str, Any]]) -> None:
        """Import assets from MAMS to current project"""
        if not self.current_project:
            return
        
        media_pool = self.current_project.GetMediaPool()
        if not media_pool:
            return
        
        for asset in assets:
            # Download asset from MAMS
            asset_id = asset.get('id')
            if asset_id:
                local_path = mams_client.download_asset(asset_id, quality='edit')
                if local_path:
                    # Import to media pool
                    media_pool.ImportMedia([{
                        "FilePath": local_path,
                        "ClipName": asset['name']
                    }])
    
    def _import_project_timelines(self, timelines: List[Dict[str, Any]]) -> None:
        """Import timeline structures"""
        if not self.current_project:
            return
        
        for timeline_data in timelines:
            # Create empty timeline
            timeline = self.current_project.CreateEmptyTimeline(timeline_data['name'])
            if timeline:
                # Set timeline properties
                timeline.SetSetting('timelineFrameRate', timeline_data.get('frame_rate', '25'))
                print(f"Created timeline: {timeline_data['name']}")

def show_project_sync():
    """Show project sync interface"""
    sync = MAMSProjectSync()
    
    if not sync.resolve:
        print("DaVinci Resolve not available")
        return
    
    if not mams_client.test_connection():
        print("Cannot connect to MAMS server. Please check settings.")
        return
    
    print("MAMS Project Sync for DaVinci Resolve")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Export current project to MAMS")
        print("2. Sync current project with MAMS")
        print("3. Import project from MAMS")
        print("4. Export timeline to MAMS")
        print("5. List MAMS projects")
        print("6. Show current project info")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            export_project_interactive(sync)
        elif choice == "2":
            sync_project_interactive(sync)
        elif choice == "3":
            import_project_interactive(sync)
        elif choice == "4":
            export_timeline_interactive(sync)
        elif choice == "5":
            list_mams_projects()
        elif choice == "6":
            show_current_project_info(sync)

def export_project_interactive(sync: MAMSProjectSync):
    """Interactive project export"""
    if not sync.current_project:
        print("No project open in Resolve")
        return
    
    project_name = sync.current_project.GetName()
    confirm = input(f"Export project '{project_name}' to MAMS? (y/n): ").strip().lower()
    
    if confirm == 'y':
        project_id = sync.export_project_to_mams()
        if project_id:
            print(f"✅ Project exported successfully. MAMS ID: {project_id}")
        else:
            print("❌ Export failed")

def sync_project_interactive(sync: MAMSProjectSync):
    """Interactive project sync"""
    if not sync.current_project:
        print("No project open in Resolve")
        return
    
    project_id = sync.current_project.GetMetadata("MAMS_Project_ID")
    if not project_id:
        print("No MAMS project ID found. Export project first.")
        return
    
    project_name = sync.current_project.GetName()
    confirm = input(f"Sync project '{project_name}' (ID: {project_id}) with MAMS? (y/n): ").strip().lower()
    
    if confirm == 'y':
        success = sync.sync_project_with_mams(project_id)
        if success:
            print("✅ Project synchronized successfully")
        else:
            print("❌ Sync failed")

def import_project_interactive(sync: MAMSProjectSync):
    """Interactive project import"""
    project_id = input("Enter MAMS project ID to import: ").strip()
    if not project_id:
        print("Project ID required")
        return
    
    success = sync.import_project_from_mams(project_id)
    if success:
        print("✅ Project imported successfully")
    else:
        print("❌ Import failed")

def export_timeline_interactive(sync: MAMSProjectSync):
    """Interactive timeline export"""
    if not sync.current_project:
        print("No project open in Resolve")
        return
    
    timeline_name = input("Enter timeline name (or press Enter for current timeline): ").strip()
    timeline_name = timeline_name if timeline_name else None
    
    timeline_id = sync.export_timeline_to_mams(timeline_name)
    if timeline_id:
        print(f"✅ Timeline exported successfully. MAMS ID: {timeline_id}")
    else:
        print("❌ Timeline export failed")

def list_mams_projects():
    """List available MAMS projects"""
    projects = mams_client.get_projects()
    
    if not projects:
        print("No projects found in MAMS")
        return
    
    print(f"\nFound {len(projects)} projects in MAMS:")
    for i, project in enumerate(projects[:10], 1):  # Show first 10
        print(f"{i:2d}. {project['name']} - ID: {project['id']}")
        if project.get('description'):
            print(f"    {project['description'][:100]}...")
    
    if len(projects) > 10:
        print(f"... and {len(projects) - 10} more")

def show_current_project_info(sync: MAMSProjectSync):
    """Show current project information"""
    if not sync.current_project:
        print("No project open")
        return
    
    project_name = sync.current_project.GetName()
    timeline_count = sync.current_project.GetTimelineCount()
    current_timeline = sync.current_project.GetCurrentTimeline()
    mams_id = sync.current_project.GetMetadata("MAMS_Project_ID")
    
    print(f"\nCurrent Project: {project_name}")
    print(f"Timelines: {timeline_count}")
    if current_timeline:
        print(f"Current Timeline: {current_timeline.GetName()}")
    if mams_id:
        print(f"MAMS Project ID: {mams_id}")
    else:
        print("Not linked to MAMS project")

# Main execution
if __name__ == "__main__":
    show_project_sync()
