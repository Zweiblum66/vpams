"""
IPFS service for decentralized content storage.
"""
import asyncio
import json
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime, timezone
from pathlib import Path
import uuid

import ipfshttpclient
import aiofiles
import structlog

from ..core.config import settings
from ..db.models import IPFSHash

logger = structlog.get_logger()


class IPFSError(Exception):
    """Base exception for IPFS operations."""
    pass


class IPFSConnectionError(IPFSError):
    """Raised when IPFS node is not available."""
    pass


class IPFSUploadError(IPFSError):
    """Raised when upload to IPFS fails."""
    pass


class IPFSService:
    """Service for IPFS operations and content management."""
    
    def __init__(self):
        self.client = None
        self.gateway_url = settings.ipfs_gateway_url
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize IPFS HTTP client."""
        try:
            # Parse IPFS node URL
            node_url = settings.ipfs_node_url
            if node_url.startswith('http://'):
                host = node_url.replace('http://', '').split(':')[0]
                port = int(node_url.split(':')[2]) if ':' in node_url.split('//')[1] else 5001
            else:
                host = 'localhost'
                port = 5001
            
            self.client = ipfshttpclient.connect(f'/ip4/{host}/tcp/{port}/http')
            
            # Test connection
            self.client.version()
            logger.info(f"Connected to IPFS node at {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to IPFS node: {e}")
            raise IPFSConnectionError(f"IPFS connection failed: {e}")
    
    async def upload_file(
        self,
        file_path: str,
        asset_id: Optional[uuid.UUID] = None,
        content_type: str = "file",
        pin: bool = True
    ) -> Dict[str, Any]:
        """Upload file to IPFS."""
        try:
            # Read file
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Get file info
            file_name = Path(file_path).name
            file_size = len(content)
            mime_type = mimetypes.guess_type(file_path)[0]
            
            # Calculate checksum
            checksum = hashlib.sha256(content).hexdigest()
            
            # Upload to IPFS
            result = self.client.add_bytes(content)
            ipfs_hash = result['Hash']
            
            # Pin if requested
            if pin:
                self.client.pin.add(ipfs_hash)
            
            # Create gateway URL
            gateway_url = f"{self.gateway_url}/ipfs/{ipfs_hash}"
            
            upload_result = {
                "ipfs_hash": ipfs_hash,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "checksum": checksum,
                "gateway_url": gateway_url,
                "pinned": pin,
                "content_type": content_type,
                "asset_id": str(asset_id) if asset_id else None,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Uploaded file to IPFS: {upload_result}")
            return upload_result
            
        except Exception as e:
            logger.error(f"Failed to upload file to IPFS: {e}")
            raise IPFSUploadError(f"File upload failed: {e}")
    
    async def upload_json(
        self,
        data: Dict[str, Any],
        asset_id: Optional[uuid.UUID] = None,
        content_type: str = "metadata",
        pin: bool = True
    ) -> Dict[str, Any]:
        """Upload JSON data to IPFS."""
        try:
            # Convert to JSON
            json_content = json.dumps(data, indent=2, sort_keys=True)
            json_bytes = json_content.encode('utf-8')
            
            # Calculate checksum
            checksum = hashlib.sha256(json_bytes).hexdigest()
            
            # Upload to IPFS
            result = self.client.add_bytes(json_bytes)
            ipfs_hash = result['Hash']
            
            # Pin if requested
            if pin:
                self.client.pin.add(ipfs_hash)
            
            # Create gateway URL
            gateway_url = f"{self.gateway_url}/ipfs/{ipfs_hash}"
            
            upload_result = {
                "ipfs_hash": ipfs_hash,
                "file_name": f"{content_type}.json",
                "file_size": len(json_bytes),
                "mime_type": "application/json",
                "checksum": checksum,
                "gateway_url": gateway_url,
                "pinned": pin,
                "content_type": content_type,
                "asset_id": str(asset_id) if asset_id else None,
                "data": data,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Uploaded JSON to IPFS: {upload_result}")
            return upload_result
            
        except Exception as e:
            logger.error(f"Failed to upload JSON to IPFS: {e}")
            raise IPFSUploadError(f"JSON upload failed: {e}")
    
    async def download_file(
        self,
        ipfs_hash: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download file from IPFS."""
        try:
            # Get content from IPFS
            content = self.client.cat(ipfs_hash)
            
            # Save to file if path provided
            if output_path:
                async with aiofiles.open(output_path, 'wb') as f:
                    await f.write(content)
            
            # Calculate checksum
            checksum = hashlib.sha256(content).hexdigest()
            
            result = {
                "ipfs_hash": ipfs_hash,
                "content_size": len(content),
                "checksum": checksum,
                "output_path": output_path,
                "downloaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            if not output_path:
                result["content"] = content
            
            logger.info(f"Downloaded file from IPFS: {ipfs_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to download file from IPFS: {e}")
            raise IPFSError(f"File download failed: {e}")
    
    async def download_json(self, ipfs_hash: str) -> Dict[str, Any]:
        """Download and parse JSON from IPFS."""
        try:
            # Get content from IPFS
            content = self.client.cat(ipfs_hash)
            
            # Parse JSON
            data = json.loads(content.decode('utf-8'))
            
            result = {
                "ipfs_hash": ipfs_hash,
                "data": data,
                "content_size": len(content),
                "downloaded_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Downloaded JSON from IPFS: {ipfs_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to download JSON from IPFS: {e}")
            raise IPFSError(f"JSON download failed: {e}")
    
    async def get_file_info(self, ipfs_hash: str) -> Dict[str, Any]:
        """Get information about a file on IPFS."""
        try:
            # Get object stats
            stats = self.client.object.stat(ipfs_hash)
            
            # Check if pinned
            pinned = self._is_pinned(ipfs_hash)
            
            # Get content to calculate checksum
            content = self.client.cat(ipfs_hash)
            checksum = hashlib.sha256(content).hexdigest()
            
            info = {
                "ipfs_hash": ipfs_hash,
                "hash": stats.get('Hash'),
                "size": stats.get('DataSize', len(content)),
                "cumulative_size": stats.get('CumulativeSize'),
                "links": stats.get('NumLinks', 0),
                "checksum": checksum,
                "pinned": pinned,
                "gateway_url": f"{self.gateway_url}/ipfs/{ipfs_hash}",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            raise IPFSError(f"File info retrieval failed: {e}")
    
    async def pin_hash(self, ipfs_hash: str) -> Dict[str, Any]:
        """Pin a hash to prevent garbage collection."""
        try:
            self.client.pin.add(ipfs_hash)
            
            result = {
                "ipfs_hash": ipfs_hash,
                "pinned": True,
                "pinned_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Pinned hash: {ipfs_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to pin hash: {e}")
            raise IPFSError(f"Pin operation failed: {e}")
    
    async def unpin_hash(self, ipfs_hash: str) -> Dict[str, Any]:
        """Unpin a hash to allow garbage collection."""
        try:
            self.client.pin.rm(ipfs_hash)
            
            result = {
                "ipfs_hash": ipfs_hash,
                "pinned": False,
                "unpinned_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Unpinned hash: {ipfs_hash}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to unpin hash: {e}")
            raise IPFSError(f"Unpin operation failed: {e}")
    
    async def list_pinned_hashes(self) -> List[Dict[str, Any]]:
        """List all pinned hashes."""
        try:
            pins = self.client.pin.ls()
            
            pinned_list = []
            for pin_info in pins:
                pinned_list.append({
                    "ipfs_hash": pin_info['Hash'],
                    "type": pin_info.get('Type', 'unknown')
                })
            
            return pinned_list
            
        except Exception as e:
            logger.error(f"Failed to list pinned hashes: {e}")
            raise IPFSError(f"Pin list operation failed: {e}")
    
    async def create_metadata_json(
        self,
        asset_data: Dict[str, Any],
        rights_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive metadata JSON for blockchain assets."""
        metadata = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "asset": {
                "id": asset_data.get("id"),
                "title": asset_data.get("title"),
                "description": asset_data.get("description"),
                "creator": asset_data.get("creator"),
                "created_date": asset_data.get("created_date"),
                "file_type": asset_data.get("file_type"),
                "file_size": asset_data.get("file_size"),
                "duration": asset_data.get("duration"),
                "resolution": asset_data.get("resolution"),
                "checksum": asset_data.get("checksum")
            },
            "rights": {
                "type": rights_data.get("type"),
                "owner": rights_data.get("owner"),
                "license_terms": rights_data.get("license_terms", {}),
                "territories": rights_data.get("territories", []),
                "languages": rights_data.get("languages", []),
                "valid_from": rights_data.get("valid_from"),
                "valid_until": rights_data.get("valid_until"),
                "royalty_percentage": rights_data.get("royalty_percentage", 0),
                "commercial_use": rights_data.get("commercial_use", False),
                "derivative_works": rights_data.get("derivative_works", False)
            },
            "blockchain": {
                "network": rights_data.get("network", settings.default_network),
                "contract_version": "1.0",
                "schema_version": "1.0"
            }
        }
        
        return metadata
    
    async def upload_asset_metadata(
        self,
        asset_data: Dict[str, Any],
        rights_data: Dict[str, Any],
        asset_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Upload complete asset metadata to IPFS."""
        try:
            # Create metadata JSON
            metadata = await self.create_metadata_json(asset_data, rights_data)
            
            # Upload to IPFS
            result = await self.upload_json(
                metadata,
                asset_id=asset_id,
                content_type="asset_metadata",
                pin=True
            )
            
            logger.info(f"Uploaded asset metadata: {result['ipfs_hash']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload asset metadata: {e}")
            raise IPFSUploadError(f"Metadata upload failed: {e}")
    
    def _is_pinned(self, ipfs_hash: str) -> bool:
        """Check if a hash is pinned."""
        try:
            pins = self.client.pin.ls()
            for pin_info in pins:
                if pin_info['Hash'] == ipfs_hash:
                    return True
            return False
        except Exception:
            return False
    
    async def get_node_info(self) -> Dict[str, Any]:
        """Get IPFS node information."""
        try:
            version = self.client.version()
            id_info = self.client.id()
            
            info = {
                "version": version.get("Version"),
                "commit": version.get("Commit"),
                "repo": version.get("Repo"),
                "system": version.get("System"),
                "golang": version.get("Golang"),
                "node_id": id_info.get("ID"),
                "public_key": id_info.get("PublicKey"),
                "addresses": id_info.get("Addresses", []),
                "agent_version": id_info.get("AgentVersion"),
                "protocol_version": id_info.get("ProtocolVersion"),
                "gateway_url": self.gateway_url,
                "connected": True,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get node info: {e}")
            return {
                "connected": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def garbage_collect(self) -> Dict[str, Any]:
        """Run garbage collection on IPFS node."""
        try:
            # Get stats before GC
            repo_stats_before = self.client.repo.stat()
            
            # Run garbage collection
            gc_result = self.client.repo.gc()
            
            # Get stats after GC
            repo_stats_after = self.client.repo.stat()
            
            # Calculate freed space
            freed_bytes = repo_stats_before.get('RepoSize', 0) - repo_stats_after.get('RepoSize', 0)
            
            result = {
                "garbage_collected": True,
                "freed_bytes": freed_bytes,
                "freed_mb": freed_bytes / (1024 * 1024),
                "repo_size_before": repo_stats_before.get('RepoSize', 0),
                "repo_size_after": repo_stats_after.get('RepoSize', 0),
                "objects_before": repo_stats_before.get('NumObjects', 0),
                "objects_after": repo_stats_after.get('NumObjects', 0),
                "gc_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"IPFS garbage collection completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run garbage collection: {e}")
            raise IPFSError(f"Garbage collection failed: {e}")
    
    async def batch_upload_files(
        self,
        file_paths: List[str],
        asset_id: Optional[uuid.UUID] = None,
        content_type: str = "file",
        pin: bool = True
    ) -> List[Dict[str, Any]]:
        """Upload multiple files to IPFS concurrently."""
        tasks = []
        
        for file_path in file_paths:
            task = self.upload_file(file_path, asset_id, content_type, pin)
            tasks.append(task)
        
        # Process uploads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file_path": file_paths[i],
                    "error": str(result),
                    "uploaded": False
                })
            else:
                processed_results.append(result)
        
        return processed_results