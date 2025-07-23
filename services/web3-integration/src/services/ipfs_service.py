"""IPFS Service for decentralized storage"""

import asyncio
import logging
import json
import aiohttp
import io
from typing import Optional, Dict, Any, List, BinaryIO
from dataclasses import dataclass

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class IPFSFile:
    """IPFS file information"""
    cid: str
    name: str
    size: int
    type: str = "file"

class IPFSService:
    """Service for interacting with IPFS"""
    
    def __init__(self):
        self.api_url = settings.IPFS_API_URL.rstrip('/')
        self.gateway_url = settings.IPFS_GATEWAY_URL.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Pinata configuration (optional pinning service)
        self.pinata_api_key = settings.PINATA_API_KEY
        self.pinata_secret_key = settings.PINATA_SECRET_KEY
        self.pinata_url = "https://api.pinata.cloud"
    
    async def initialize(self):
        """Initialize IPFS client"""
        self.session = aiohttp.ClientSession()
        
        # Test connection
        if await self.check_connection():
            logger.info("Connected to IPFS")
        else:
            logger.warning("Failed to connect to IPFS")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def check_connection(self) -> bool:
        """Check if IPFS node is accessible"""
        try:
            async with self.session.get(f"{self.api_url}/api/v0/version") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"IPFS connection check failed: {e}")
            return False
    
    async def add_file(
        self, 
        file_data: BinaryIO, 
        filename: str,
        pin: bool = True,
        wrap_with_directory: bool = False
    ) -> Optional[IPFSFile]:
        """Add a file to IPFS"""
        try:
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('file',
                          file_data,
                          filename=filename,
                          content_type='application/octet-stream')
            
            # Add parameters
            params = {
                'pin': str(pin).lower(),
                'wrap-with-directory': str(wrap_with_directory).lower()
            }
            
            # Upload to IPFS
            async with self.session.post(
                f"{self.api_url}/api/v0/add",
                data=data,
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return IPFSFile(
                        cid=result['Hash'],
                        name=result['Name'],
                        size=int(result['Size'])
                    )
                else:
                    error = await response.text()
                    logger.error(f"Failed to add file to IPFS: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error adding file to IPFS: {e}")
            return None
    
    async def add_json(self, data: Dict[str, Any], pin: bool = True) -> Optional[str]:
        """Add JSON data to IPFS"""
        try:
            json_bytes = json.dumps(data).encode('utf-8')
            file_like = io.BytesIO(json_bytes)
            
            result = await self.add_file(file_like, "data.json", pin=pin)
            return result.cid if result else None
            
        except Exception as e:
            logger.error(f"Error adding JSON to IPFS: {e}")
            return None
    
    async def get_file(self, cid: str) -> Optional[bytes]:
        """Get file content from IPFS"""
        try:
            async with self.session.post(
                f"{self.api_url}/api/v0/cat",
                params={'arg': cid}
            ) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to get file from IPFS: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting file from IPFS: {e}")
            return None
    
    async def get_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from IPFS"""
        try:
            content = await self.get_file(cid)
            if content:
                return json.loads(content.decode('utf-8'))
            return None
            
        except Exception as e:
            logger.error(f"Error getting JSON from IPFS: {e}")
            return None
    
    async def pin_add(self, cid: str, recursive: bool = True) -> bool:
        """Pin a CID to prevent garbage collection"""
        try:
            params = {
                'arg': cid,
                'recursive': str(recursive).lower()
            }
            
            async with self.session.post(
                f"{self.api_url}/api/v0/pin/add",
                params=params
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error pinning CID: {e}")
            return False
    
    async def pin_rm(self, cid: str, recursive: bool = True) -> bool:
        """Unpin a CID"""
        try:
            params = {
                'arg': cid,
                'recursive': str(recursive).lower()
            }
            
            async with self.session.post(
                f"{self.api_url}/api/v0/pin/rm",
                params=params
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error unpinning CID: {e}")
            return False
    
    async def pin_ls(self, cid: Optional[str] = None) -> List[Dict[str, Any]]:
        """List pinned objects"""
        try:
            params = {}
            if cid:
                params['arg'] = cid
            
            async with self.session.post(
                f"{self.api_url}/api/v0/pin/ls",
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('Keys', {})
                return []
                
        except Exception as e:
            logger.error(f"Error listing pins: {e}")
            return []
    
    async def object_stat(self, cid: str) -> Optional[Dict[str, Any]]:
        """Get object statistics"""
        try:
            async with self.session.post(
                f"{self.api_url}/api/v0/object/stat",
                params={'arg': cid}
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
                
        except Exception as e:
            logger.error(f"Error getting object stats: {e}")
            return None
    
    async def dag_get(self, cid: str) -> Optional[Dict[str, Any]]:
        """Get DAG node"""
        try:
            async with self.session.post(
                f"{self.api_url}/api/v0/dag/get",
                params={'arg': cid}
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
                
        except Exception as e:
            logger.error(f"Error getting DAG: {e}")
            return None
    
    def get_gateway_url(self, cid: str) -> str:
        """Get public gateway URL for a CID"""
        return f"{self.gateway_url}/{cid}"
    
    # Pinata integration methods
    
    async def pin_to_pinata(
        self, 
        cid: str, 
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Pin CID to Pinata pinning service"""
        if not self.pinata_api_key or not self.pinata_secret_key:
            logger.warning("Pinata credentials not configured")
            return None
        
        try:
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret_key
            }
            
            data = {
                'hashToPin': cid,
                'pinataMetadata': {
                    'name': name or cid
                }
            }
            
            if metadata:
                data['pinataMetadata']['keyvalues'] = metadata
            
            async with self.session.post(
                f"{self.pinata_url}/pinning/pinByHash",
                json=data,
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    logger.error(f"Pinata pinning failed: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error pinning to Pinata: {e}")
            return None
    
    async def upload_to_pinata(
        self,
        file_data: BinaryIO,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Upload file directly to Pinata"""
        if not self.pinata_api_key or not self.pinata_secret_key:
            logger.warning("Pinata credentials not configured")
            return None
        
        try:
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret_key
            }
            
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('file',
                          file_data,
                          filename=filename,
                          content_type='application/octet-stream')
            
            # Add metadata
            if metadata:
                pinata_metadata = {
                    'name': filename,
                    'keyvalues': metadata
                }
                data.add_field('pinataMetadata', json.dumps(pinata_metadata))
            
            async with self.session.post(
                f"{self.pinata_url}/pinning/pinFileToIPFS",
                data=data,
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    logger.error(f"Pinata upload failed: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error uploading to Pinata: {e}")
            return None
    
    async def get_pinata_pins(
        self,
        status: str = "pinned",
        page_limit: int = 10,
        page_offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """List pins from Pinata"""
        if not self.pinata_api_key or not self.pinata_secret_key:
            return None
        
        try:
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret_key
            }
            
            params = {
                'status': status,
                'pageLimit': page_limit,
                'pageOffset': page_offset
            }
            
            async with self.session.get(
                f"{self.pinata_url}/data/pinList",
                params=params,
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
                
        except Exception as e:
            logger.error(f"Error getting Pinata pins: {e}")
            return None
    
    async def unpin_from_pinata(self, ipfs_hash: str) -> bool:
        """Unpin from Pinata"""
        if not self.pinata_api_key or not self.pinata_secret_key:
            return False
        
        try:
            headers = {
                'pinata_api_key': self.pinata_api_key,
                'pinata_secret_api_key': self.pinata_secret_key
            }
            
            async with self.session.delete(
                f"{self.pinata_url}/pinning/unpin/{ipfs_hash}",
                headers=headers
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error unpinning from Pinata: {e}")
            return False