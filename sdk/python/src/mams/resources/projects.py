"""
Projects resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource
from ..models import Project, ProjectCreate, ProjectUpdate, Asset


class ProjectsResource(BaseResource[Project]):
    """Projects API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "projects"
        self.model_class = Project
    
    def get_containers(
        self,
        project_id: str,
        container_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get project containers (folders, bins, etc.)
        
        Args:
            project_id: Project ID
            container_type: Optional container type filter
        
        Returns:
            List of containers
        """
        params = {}
        if container_type:
            params["type"] = container_type
        
        response = self._make_request(
            "GET",
            self._get_path(project_id, "containers"),
            params=params
        )
        
        return response.get("data", [])
    
    def create_container(
        self,
        project_id: str,
        name: str,
        type: str = "folder",
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create project container
        
        Args:
            project_id: Project ID
            name: Container name
            type: Container type (folder, bin, shotlist, sequence)
            parent_id: Optional parent container ID
            metadata: Optional metadata
        
        Returns:
            Created container
        """
        data = {
            "name": name,
            "type": type
        }
        
        if parent_id:
            data["parent_id"] = parent_id
        
        if metadata:
            data["metadata"] = metadata
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "containers"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_assets(
        self,
        project_id: str,
        container_id: Optional[str] = None,
        **filters
    ) -> List[Asset]:
        """Get project assets
        
        Args:
            project_id: Project ID
            container_id: Optional container ID filter
            **filters: Additional filters
        
        Returns:
            List of assets
        """
        params = filters.copy()
        if container_id:
            params["container_id"] = container_id
        
        response = self._make_request(
            "GET",
            self._get_path(project_id, "assets"),
            params=params
        )
        
        return [Asset(**item) for item in response.get("data", [])]
    
    def add_asset(
        self,
        project_id: str,
        asset_id: str,
        container_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add asset to project
        
        Args:
            project_id: Project ID
            asset_id: Asset ID
            container_id: Optional container ID
            metadata: Optional metadata
        
        Returns:
            Project asset relationship
        """
        data = {"asset_id": asset_id}
        
        if container_id:
            data["container_id"] = container_id
        
        if metadata:
            data["metadata"] = metadata
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "assets"),
            json=data
        )
        
        return response.get("data", {})
    
    def remove_asset(
        self,
        project_id: str,
        asset_id: str
    ) -> bool:
        """Remove asset from project
        
        Args:
            project_id: Project ID
            asset_id: Asset ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path(project_id, "assets", asset_id)
        )
        return True
    
    def get_sequences(self, project_id: str) -> List[Dict[str, Any]]:
        """Get project sequences
        
        Args:
            project_id: Project ID
        
        Returns:
            List of sequences
        """
        response = self._make_request(
            "GET",
            self._get_path(project_id, "sequences")
        )
        
        return response.get("data", [])
    
    def create_sequence(
        self,
        project_id: str,
        name: str,
        frame_rate: float = 25.0,
        resolution: str = "1920x1080",
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create sequence
        
        Args:
            project_id: Project ID
            name: Sequence name
            frame_rate: Frame rate (default: 25.0)
            resolution: Resolution (default: "1920x1080")
            duration: Optional duration in seconds
            metadata: Optional metadata
        
        Returns:
            Created sequence
        """
        data = {
            "name": name,
            "frame_rate": frame_rate,
            "resolution": resolution
        }
        
        if duration:
            data["duration"] = duration
        
        if metadata:
            data["metadata"] = metadata
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "sequences"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_timeline(
        self,
        project_id: str,
        sequence_id: str
    ) -> Dict[str, Any]:
        """Get sequence timeline
        
        Args:
            project_id: Project ID
            sequence_id: Sequence ID
        
        Returns:
            Timeline data
        """
        response = self._make_request(
            "GET",
            self._get_path(project_id, "sequences", sequence_id, "timeline")
        )
        
        return response.get("data", {})
    
    def add_clip_to_timeline(
        self,
        project_id: str,
        sequence_id: str,
        asset_id: str,
        track_type: str,
        track_index: int,
        start_time: float,
        in_point: Optional[float] = None,
        out_point: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add clip to timeline
        
        Args:
            project_id: Project ID
            sequence_id: Sequence ID
            asset_id: Asset ID
            track_type: Track type (video, audio)
            track_index: Track index
            start_time: Start time in timeline
            in_point: Optional in point of asset
            out_point: Optional out point of asset
            metadata: Optional metadata
        
        Returns:
            Created clip
        """
        data = {
            "asset_id": asset_id,
            "track_type": track_type,
            "track_index": track_index,
            "start_time": start_time
        }
        
        if in_point is not None:
            data["in_point"] = in_point
        
        if out_point is not None:
            data["out_point"] = out_point
        
        if metadata:
            data["metadata"] = metadata
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "sequences", sequence_id, "timeline"),
            json=data
        )
        
        return response.get("data", {})
    
    def export_project(
        self,
        project_id: str,
        format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Export project to NLE format
        
        Args:
            project_id: Project ID
            format: Export format (aaf, xml, edl, otio)
            options: Optional export options
        
        Returns:
            Export job information
        """
        data = {"format": format}
        
        if options:
            data["options"] = options
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "export"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_export_status(
        self,
        project_id: str,
        export_id: str
    ) -> Dict[str, Any]:
        """Get export job status
        
        Args:
            project_id: Project ID
            export_id: Export job ID
        
        Returns:
            Export status
        """
        response = self._make_request(
            "GET",
            self._get_path(project_id, "exports", export_id)
        )
        
        return response.get("data", {})
    
    def get_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Get project members
        
        Args:
            project_id: Project ID
        
        Returns:
            List of project members
        """
        response = self._make_request(
            "GET",
            self._get_path(project_id, "members")
        )
        
        return response.get("data", [])
    
    def add_member(
        self,
        project_id: str,
        user_id: str,
        role: str = "contributor"
    ) -> Dict[str, Any]:
        """Add member to project
        
        Args:
            project_id: Project ID
            user_id: User ID
            role: Member role (viewer, contributor, admin)
        
        Returns:
            Project membership
        """
        data = {
            "user_id": user_id,
            "role": role
        }
        
        response = self._make_request(
            "POST",
            self._get_path(project_id, "members"),
            json=data
        )
        
        return response.get("data", {})
    
    def remove_member(
        self,
        project_id: str,
        user_id: str
    ) -> bool:
        """Remove member from project
        
        Args:
            project_id: Project ID
            user_id: User ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path(project_id, "members", user_id)
        )
        return True