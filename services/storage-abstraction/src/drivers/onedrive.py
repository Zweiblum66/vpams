"""
OneDrive Storage Driver

This module implements the OneDrive storage driver for the storage abstraction layer.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from pathlib import Path
import mimetypes
import hashlib
import json
from urllib.parse import quote

try:
    import httpx
    from httpx import AsyncClient
except ImportError:
    httpx = None
    AsyncClient = None

from ..core.interfaces import (
    StorageDriver, StorageObject, StorageTier, PresignedUrl,
    ObjectNotFoundError, StorageQuotaExceededError, StoragePermissionError,
    InvalidStorageOperationError, StorageOperationError
)


logger = logging.getLogger(__name__)


class OneDriveStorageDriver(StorageDriver):
    """OneDrive storage driver implementation using Microsoft Graph API"""
    
    # Microsoft Graph API endpoints
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    AUTH_BASE = "https://login.microsoftonline.com"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OneDrive driver"""
        if httpx is None:
            raise ImportError("httpx package is required for OneDrive storage")
        
        self.config = config
        self.tenant_id = config.get("tenant_id", "common")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.access_token = config.get("access_token")
        self.refresh_token = config.get("refresh_token")
        
        # Drive configuration
        self.drive_type = config.get("drive_type", "me")  # me, sites, groups
        self.site_id = config.get("site_id")
        self.group_id = config.get("group_id")
        
        # Path configuration
        self.path_prefix = config.get("path_prefix", "/MAMS")
        if not self.path_prefix.startswith("/"):
            self.path_prefix = "/" + self.path_prefix
        
        # Upload configuration
        self.chunk_size = config.get("chunk_size", 10 * 1024 * 1024)  # 10MB default
        self.max_file_size = config.get("max_file_size", 250 * 1024 * 1024 * 1024)  # 250GB
        
        # HTTP client
        self.client: Optional[AsyncClient] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Validate configuration
        if not self.access_token and not (self.client_id and self.client_secret):
            raise ValueError("Either access_token or client_id/client_secret required")
    
    async def initialize(self) -> None:
        """Initialize the driver"""
        self.client = AsyncClient(
            timeout=httpx.Timeout(30.0, read=300.0),
            follow_redirects=True
        )
        
        # Refresh token if needed
        if not self.access_token and self.refresh_token:
            await self._refresh_access_token()
    
    async def close(self) -> None:
        """Close the driver and cleanup resources"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def _get_drive_url(self) -> str:
        """Get the base URL for the drive"""
        if self.drive_type == "me":
            return f"{self.GRAPH_API_BASE}/me/drive"
        elif self.drive_type == "sites" and self.site_id:
            return f"{self.GRAPH_API_BASE}/sites/{self.site_id}/drive"
        elif self.drive_type == "groups" and self.group_id:
            return f"{self.GRAPH_API_BASE}/groups/{self.group_id}/drive"
        else:
            return f"{self.GRAPH_API_BASE}/me/drive"
    
    def _normalize_path(self, key: str) -> str:
        """Normalize object key to OneDrive path"""
        if not key.startswith("/"):
            key = "/" + key
        
        # Combine with prefix
        full_path = self.path_prefix + key
        
        # Normalize path
        return str(Path(full_path).as_posix())
    
    def _extract_key(self, onedrive_path: str) -> str:
        """Extract object key from OneDrive path"""
        if onedrive_path.startswith(self.path_prefix):
            key = onedrive_path[len(self.path_prefix):]
            if key.startswith("/"):
                key = key[1:]
            return key
        return onedrive_path
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        # Check if token needs refresh
        if self._token_expires_at and datetime.utcnow() >= self._token_expires_at:
            await self._refresh_access_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise StoragePermissionError("Cannot refresh token: missing credentials")
        
        token_url = f"{self.AUTH_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/.default"
        }
        
        response = await self.client.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
        else:
            raise StoragePermissionError(f"Failed to refresh token: {response.text}")
    
    def _metadata_to_storage_object(self, item: Dict[str, Any]) -> StorageObject:
        """Convert OneDrive item metadata to StorageObject"""
        # Extract path from parent reference
        parent_path = item.get("parentReference", {}).get("path", "")
        if parent_path.startswith("/drive/root:"):
            parent_path = parent_path[12:]  # Remove "/drive/root:"
        
        full_path = f"{parent_path}/{item['name']}"
        key = self._extract_key(full_path)
        
        # Parse timestamps
        created = datetime.fromisoformat(item["createdDateTime"].replace("Z", "+00:00"))
        modified = datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
        
        # Get file info
        file_info = item.get("file", {})
        folder_info = item.get("folder", {})
        
        return StorageObject(
            key=key,
            size=item.get("size", 0),
            last_modified=modified,
            etag=item.get("eTag", ""),
            content_type=file_info.get("mimeType") or mimetypes.guess_type(key)[0],
            metadata={
                "id": item["id"],
                "created": created.isoformat(),
                "web_url": item.get("webUrl"),
                "is_folder": "folder" in item,
                "child_count": folder_info.get("childCount", 0) if folder_info else 0,
                "sha1_hash": file_info.get("hashes", {}).get("sha1Hash"),
                "quick_xor_hash": file_info.get("hashes", {}).get("quickXorHash")
            },
            storage_class="standard",
            version_id=item.get("eTag")
        )
    
    async def get_object_info(self, key: str) -> StorageObject:
        """Get object metadata"""
        try:
            path = self._normalize_path(key)
            url = f"{self._get_drive_url()}/root:{path}"
            
            headers = await self._get_headers()
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                return self._metadata_to_storage_object(response.json())
            elif response.status_code == 404:
                raise ObjectNotFoundError(key)
            else:
                raise StorageOperationError(
                    f"Failed to get object info: {response.status_code} - {response.text}"
                )
        
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get object info for {key}: {e}")
            raise StorageOperationError(f"Failed to get object info: {e}")
    
    async def get_object(self, key: str) -> bytes:
        """Download object content"""
        try:
            path = self._normalize_path(key)
            url = f"{self._get_drive_url()}/root:{path}:/content"
            
            headers = await self._get_headers()
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 404:
                raise ObjectNotFoundError(key)
            else:
                raise StorageOperationError(
                    f"Failed to download object: {response.status_code} - {response.text}"
                )
        
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download object {key}: {e}")
            raise StorageOperationError(f"Failed to download object: {e}")
    
    async def get_object_stream(self, key: str, **kwargs) -> AsyncGenerator[bytes, None]:
        """Stream object content"""
        try:
            path = self._normalize_path(key)
            url = f"{self._get_drive_url()}/root:{path}:/content"
            
            headers = await self._get_headers()
            chunk_size = kwargs.get('chunk_size', self.chunk_size)
            
            # Stream the response
            async with self.client.stream("GET", url, headers=headers) as response:
                if response.status_code == 200:
                    async for chunk in response.aiter_bytes(chunk_size):
                        yield chunk
                elif response.status_code == 404:
                    raise ObjectNotFoundError(key)
                else:
                    raise StorageOperationError(
                        f"Failed to stream object: {response.status_code}"
                    )
        
        except Exception as e:
            logger.error(f"Failed to stream object {key}: {e}")
            raise StorageOperationError(f"Failed to stream object: {e}")
    
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Upload object"""
        try:
            path = self._normalize_path(key)
            
            # For small files (< 4MB), use simple upload
            if len(data) < 4 * 1024 * 1024:
                return await self._simple_upload(path, data, content_type)
            else:
                # Use upload session for larger files
                return await self._resumable_upload(path, data, content_type)
        
        except Exception as e:
            logger.error(f"Failed to upload object {key}: {e}")
            raise StorageOperationError(f"Failed to upload object: {e}")
    
    async def _simple_upload(
        self, 
        path: str, 
        data: bytes, 
        content_type: Optional[str] = None
    ) -> StorageObject:
        """Simple upload for small files"""
        url = f"{self._get_drive_url()}/root:{path}:/content"
        
        headers = await self._get_headers()
        headers["Content-Type"] = content_type or "application/octet-stream"
        
        response = await self.client.put(url, headers=headers, content=data)
        
        if response.status_code in (200, 201):
            return self._metadata_to_storage_object(response.json())
        elif response.status_code == 507:
            raise StorageQuotaExceededError("OneDrive storage quota exceeded")
        else:
            raise StorageOperationError(
                f"Upload failed: {response.status_code} - {response.text}"
            )
    
    async def _resumable_upload(
        self, 
        path: str, 
        data: bytes, 
        content_type: Optional[str] = None
    ) -> StorageObject:
        """Resumable upload for large files"""
        # Create upload session
        session_url = f"{self._get_drive_url()}/root:{path}:/createUploadSession"
        
        headers = await self._get_headers()
        session_data = {
            "item": {
                "@microsoft.graph.conflictBehavior": "replace"
            }
        }
        
        response = await self.client.post(
            session_url, 
            headers=headers, 
            json=session_data
        )
        
        if response.status_code != 200:
            raise StorageOperationError(
                f"Failed to create upload session: {response.status_code} - {response.text}"
            )
        
        session = response.json()
        upload_url = session["uploadUrl"]
        
        # Upload in chunks
        file_size = len(data)
        offset = 0
        
        while offset < file_size:
            chunk_size = min(self.chunk_size, file_size - offset)
            chunk = data[offset:offset + chunk_size]
            
            # Upload chunk
            chunk_headers = {
                "Content-Length": str(chunk_size),
                "Content-Range": f"bytes {offset}-{offset + chunk_size - 1}/{file_size}"
            }
            
            chunk_response = await self.client.put(
                upload_url,
                headers=chunk_headers,
                content=chunk
            )
            
            if chunk_response.status_code not in (200, 201, 202):
                raise StorageOperationError(
                    f"Chunk upload failed: {chunk_response.status_code} - {chunk_response.text}"
                )
            
            offset += chunk_size
            
            # Check if upload is complete
            if chunk_response.status_code in (200, 201):
                return self._metadata_to_storage_object(chunk_response.json())
        
        raise StorageOperationError("Upload completed but no response received")
    
    async def delete_object(self, key: str) -> bool:
        """Delete object"""
        try:
            path = self._normalize_path(key)
            url = f"{self._get_drive_url()}/root:{path}"
            
            headers = await self._get_headers()
            response = await self.client.delete(url, headers=headers)
            
            if response.status_code == 204:
                return True
            elif response.status_code == 404:
                return False
            else:
                raise StorageOperationError(
                    f"Delete failed: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise StorageOperationError(f"Failed to delete object: {e}")
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[StorageObject], Optional[str]]:
        """List objects"""
        try:
            # Build the path
            if prefix:
                search_path = self._normalize_path(prefix)
                url = f"{self._get_drive_url()}/root:{search_path}:/children"
            else:
                url = f"{self._get_drive_url()}/root/children"
            
            # Add query parameters
            params = {
                "$top": min(max_keys, 999),  # OneDrive max is 999
                "$select": "id,name,size,file,folder,parentReference,createdDateTime,"
                          "lastModifiedDateTime,eTag,webUrl"
            }
            
            if continuation_token:
                params["$skiptoken"] = continuation_token
            
            headers = await self._get_headers()
            response = await self.client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                objects = []
                for item in data.get("value", []):
                    # Skip folders if delimiter is not set
                    if delimiter and "folder" in item:
                        continue
                    
                    obj = self._metadata_to_storage_object(item)
                    objects.append(obj)
                
                # Extract next token from @odata.nextLink
                next_link = data.get("@odata.nextLink", "")
                next_token = None
                
                if next_link and "$skiptoken=" in next_link:
                    next_token = next_link.split("$skiptoken=")[1].split("&")[0]
                
                return objects, next_token
            
            elif response.status_code == 404:
                return [], None
            else:
                raise StorageOperationError(
                    f"List failed: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise StorageOperationError(f"Failed to list objects: {e}")
    
    async def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Copy object"""
        try:
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            # Get source item
            source_url = f"{self._get_drive_url()}/root:{source_path}"
            headers = await self._get_headers()
            
            # Create copy request
            dest_parent = str(Path(dest_path).parent)
            dest_name = Path(dest_path).name
            
            copy_data = {
                "parentReference": {
                    "path": f"/drive/root:{dest_parent}"
                },
                "name": dest_name
            }
            
            response = await self.client.post(
                f"{source_url}/copy",
                headers=headers,
                json=copy_data
            )
            
            if response.status_code == 202:
                # Copy is async, need to wait for completion
                monitor_url = response.headers.get("Location")
                if monitor_url:
                    # Poll for completion
                    for _ in range(30):  # Max 30 seconds
                        await asyncio.sleep(1)
                        status_response = await self.client.get(monitor_url)
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get("status") == "completed":
                                # Get the new item
                                return await self.get_object_info(dest_key)
                            elif status_data.get("status") == "failed":
                                raise StorageOperationError("Copy operation failed")
                
                # If we get here, assume success and get info
                return await self.get_object_info(dest_key)
            
            else:
                raise StorageOperationError(
                    f"Copy failed: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to copy object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to copy object: {e}")
    
    async def move_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> StorageObject:
        """Move object"""
        try:
            source_path = self._normalize_path(source_key)
            dest_path = self._normalize_path(dest_key)
            
            # Get source item URL
            source_url = f"{self._get_drive_url()}/root:{source_path}"
            headers = await self._get_headers()
            
            # Create move request
            dest_parent = str(Path(dest_path).parent)
            dest_name = Path(dest_path).name
            
            move_data = {
                "parentReference": {
                    "path": f"/drive/root:{dest_parent}"
                },
                "name": dest_name
            }
            
            response = await self.client.patch(
                source_url,
                headers=headers,
                json=move_data
            )
            
            if response.status_code == 200:
                return self._metadata_to_storage_object(response.json())
            elif response.status_code == 404:
                raise ObjectNotFoundError(source_key)
            else:
                raise StorageOperationError(
                    f"Move failed: {response.status_code} - {response.text}"
                )
        
        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to move object {source_key} to {dest_key}: {e}")
            raise StorageOperationError(f"Failed to move object: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if object exists"""
        try:
            await self.get_object_info(key)
            return True
        except ObjectNotFoundError:
            return False
        except Exception:
            return False
    
    async def get_presigned_url(
        self,
        key: str,
        operation: str = "get",
        expires_in: int = 3600,
        **kwargs
    ) -> PresignedUrl:
        """Generate presigned URL (sharing link)"""
        try:
            path = self._normalize_path(key)
            
            if operation == "get":
                # Create a sharing link
                url = f"{self._get_drive_url()}/root:{path}:/createLink"
                headers = await self._get_headers()
                
                link_data = {
                    "type": "view",  # or "edit" for write access
                    "scope": "anonymous",
                    "expirationDateTime": (
                        datetime.utcnow() + timedelta(seconds=expires_in)
                    ).isoformat() + "Z"
                }
                
                response = await self.client.post(url, headers=headers, json=link_data)
                
                if response.status_code == 201:
                    data = response.json()
                    return PresignedUrl(
                        url=data["link"]["webUrl"],
                        expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
                    )
                else:
                    # Fallback to direct download URL (requires auth)
                    download_url = f"{self._get_drive_url()}/root:{path}:/content"
                    return PresignedUrl(
                        url=download_url,
                        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
            else:
                raise InvalidStorageOperationError(
                    f"Presigned URLs for operation '{operation}' not supported"
                )
        
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageOperationError(f"Failed to generate presigned URL: {e}")
    
    async def create_multipart_upload(
        self,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Create multipart upload session"""
        try:
            path = self._normalize_path(key)
            session_url = f"{self._get_drive_url()}/root:{path}:/createUploadSession"
            
            headers = await self._get_headers()
            session_data = {
                "item": {
                    "@microsoft.graph.conflictBehavior": "replace"
                }
            }
            
            response = await self.client.post(
                session_url,
                headers=headers,
                json=session_data
            )
            
            if response.status_code == 200:
                session = response.json()
                # Return upload URL as upload ID
                return session["uploadUrl"]
            else:
                raise StorageOperationError(
                    f"Failed to create upload session: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to create multipart upload for {key}: {e}")
            raise StorageOperationError(f"Failed to create multipart upload: {e}")
    
    async def upload_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes,
        **kwargs
    ) -> Dict[str, Any]:
        """Upload part for multipart upload"""
        try:
            # Calculate offset based on part number and size
            # Assuming fixed chunk size except for last part
            offset = (part_number - 1) * self.chunk_size
            
            # Upload chunk
            headers = {
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {offset}-{offset + len(data) - 1}/*"
            }
            
            response = await self.client.put(
                upload_id,  # Upload URL from create_multipart_upload
                headers=headers,
                content=data
            )
            
            if response.status_code in (200, 201, 202):
                return {
                    "PartNumber": part_number,
                    "ETag": hashlib.md5(data).hexdigest(),
                    "Size": len(data)
                }
            else:
                raise StorageOperationError(
                    f"Part upload failed: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to upload part {part_number} for {key}: {e}")
            raise StorageOperationError(f"Failed to upload part: {e}")
    
    async def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]],
        **kwargs
    ) -> StorageObject:
        """Complete multipart upload"""
        # OneDrive automatically completes the upload when all bytes are received
        # The last upload_part call should have returned the completed file
        # We'll verify by getting the object info
        return await self.get_object_info(key)
    
    async def abort_multipart_upload(self, key: str, upload_id: str, **kwargs) -> None:
        """Abort multipart upload"""
        try:
            # Cancel the upload session
            await self.client.delete(upload_id)
        except Exception as e:
            logger.warning(f"Failed to abort upload session: {e}")
    
    async def change_storage_tier(self, key: str, tier: StorageTier, **kwargs) -> StorageObject:
        """Change storage tier (not supported by OneDrive)"""
        raise InvalidStorageOperationError("Storage tier changes not supported by OneDrive")
    
    async def restore_object(self, key: str, days: int = 1, tier: str = "Standard", **kwargs) -> bool:
        """Restore object (not applicable for OneDrive)"""
        raise InvalidStorageOperationError("Object restoration not applicable for OneDrive")
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage information"""
        try:
            url = f"{self._get_drive_url()}"
            headers = await self._get_headers()
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                quota = data.get("quota", {})
                
                return {
                    "used_bytes": quota.get("used", 0),
                    "total_bytes": quota.get("total", 0),
                    "remaining_bytes": quota.get("remaining", 0),
                    "deleted_bytes": quota.get("deleted", 0),
                    "state": quota.get("state", "normal"),  # normal, nearing, critical, exceeded
                    "usage_percentage": (
                        (quota.get("used", 0) / quota.get("total", 1)) * 100
                        if quota.get("total", 0) > 0 else 0
                    )
                }
            else:
                raise StorageOperationError(
                    f"Failed to get storage usage: {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            raise StorageOperationError(f"Failed to get storage usage: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Test API access by getting drive info
            url = f"{self._get_drive_url()}"
            headers = await self._get_headers()
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "OneDrive API accessible",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"API returned status {response.status_code}",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }