"""
Assets resource implementation
"""

from typing import Optional, Dict, Any, List, BinaryIO
import os
from pathlib import Path
from ..resources.base import BaseResource
from ..models import Asset, AssetCreate, AssetUpdate


class AssetsResource(BaseResource[Asset]):
    """Assets API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "assets"
        self.model_class = Asset
    
    def upload(
        self,
        file: BinaryIO,
        name: str,
        type: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Asset:
        """Upload a new asset
        
        Args:
            file: File-like object to upload
            name: Asset name
            type: Asset type (video, audio, image, document)
            project_id: Optional project ID
            metadata: Optional metadata dict
            **kwargs: Additional asset properties
        
        Returns:
            Created Asset object
        """
        # Prepare form data
        files = {"file": (name, file, self._get_content_type(name, type))}
        
        data = {
            "name": name,
            "type": type,
            **kwargs
        }
        
        if project_id:
            data["project_id"] = project_id
        
        if metadata:
            data["metadata"] = metadata
        
        # Upload file
        response = self._make_request(
            "POST",
            self._get_path("upload"),
            files=files,
            data=data
        )
        
        return self._parse_response(response)
    
    def upload_from_path(
        self,
        file_path: str,
        name: Optional[str] = None,
        type: Optional[str] = None,
        **kwargs
    ) -> Asset:
        """Upload asset from file path
        
        Args:
            file_path: Path to file
            name: Optional asset name (defaults to filename)
            type: Optional asset type (auto-detected if not provided)
            **kwargs: Additional parameters for upload()
        
        Returns:
            Created Asset object
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not name:
            name = path.name
        
        if not type:
            type = self._detect_asset_type(path.suffix)
        
        with open(file_path, "rb") as f:
            return self.upload(f, name, type, **kwargs)
    
    def download(
        self,
        asset_id: str,
        output_path: Optional[str] = None,
        chunk_size: Optional[int] = None
    ) -> str:
        """Download asset file
        
        Args:
            asset_id: Asset ID
            output_path: Optional output path (defaults to asset name)
            chunk_size: Optional chunk size for download
        
        Returns:
            Path to downloaded file
        """
        # Get download URL
        response = self._make_request(
            "GET",
            self._get_path(asset_id, "download"),
            stream=True
        )
        
        # Determine output path
        if not output_path:
            # Extract filename from headers or use asset ID
            content_disposition = response.headers.get("Content-Disposition", "")
            if "filename=" in content_disposition:
                output_path = content_disposition.split("filename=")[1].strip('"')
            else:
                output_path = f"{asset_id}.bin"
        
        # Download file
        chunk_size = chunk_size or self.client.config.chunk_size
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size):
                f.write(chunk)
        
        return output_path
    
    def get_metadata(self, asset_id: str) -> Dict[str, Any]:
        """Get asset metadata
        
        Args:
            asset_id: Asset ID
        
        Returns:
            Metadata dictionary
        """
        response = self._make_request(
            "GET",
            self._get_path(asset_id, "metadata")
        )
        
        return response.get("data", {})
    
    def update_metadata(
        self,
        asset_id: str,
        metadata: Dict[str, Any],
        merge: bool = True
    ) -> Dict[str, Any]:
        """Update asset metadata
        
        Args:
            asset_id: Asset ID
            metadata: Metadata to update
            merge: Whether to merge with existing metadata (default: True)
        
        Returns:
            Updated metadata
        """
        response = self._make_request(
            "PATCH" if merge else "PUT",
            self._get_path(asset_id, "metadata"),
            json={"metadata": metadata}
        )
        
        return response.get("data", {})
    
    def get_versions(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get asset versions
        
        Args:
            asset_id: Asset ID
        
        Returns:
            List of version objects
        """
        response = self._make_request(
            "GET",
            self._get_path(asset_id, "versions")
        )
        
        return response.get("data", [])
    
    def create_version(
        self,
        asset_id: str,
        file: BinaryIO,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new asset version
        
        Args:
            asset_id: Asset ID
            file: New version file
            comment: Optional version comment
        
        Returns:
            Version object
        """
        asset = self.get(asset_id)
        
        files = {"file": (asset.name, file, self._get_content_type(asset.name, asset.type))}
        data = {}
        
        if comment:
            data["comment"] = comment
        
        response = self._make_request(
            "POST",
            self._get_path(asset_id, "versions"),
            files=files,
            data=data
        )
        
        return response.get("data", {})
    
    def get_proxy(
        self,
        asset_id: str,
        quality: str = "medium"
    ) -> str:
        """Get proxy URL for asset
        
        Args:
            asset_id: Asset ID
            quality: Proxy quality (low, medium, high)
        
        Returns:
            Proxy URL
        """
        response = self._make_request(
            "GET",
            self._get_path(asset_id, "proxy"),
            params={"quality": quality}
        )
        
        return response.get("url", "")
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Asset]:
        """Search assets
        
        Args:
            query: Search query
            filters: Optional filters
            limit: Results limit
            offset: Results offset
        
        Returns:
            List of matching assets
        """
        params = {
            "q": query,
            "limit": limit,
            "offset": offset
        }
        
        if filters:
            params.update(filters)
        
        response = self._make_request(
            "GET",
            self._get_path("search"),
            params=params
        )
        
        return self._parse_list_response(response)
    
    def _get_content_type(self, filename: str, asset_type: str) -> str:
        """Get content type for file"""
        # Map extensions to content types
        ext_map = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        
        ext = Path(filename).suffix.lower()
        return ext_map.get(ext, "application/octet-stream")
    
    def _detect_asset_type(self, extension: str) -> str:
        """Detect asset type from file extension"""
        ext = extension.lower()
        
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
        audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"}
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        
        if ext in video_exts:
            return "video"
        elif ext in audio_exts:
            return "audio"
        elif ext in image_exts:
            return "image"
        else:
            return "document"