"""
MAMS Client for DaVinci Resolve Integration
Handles communication with MAMS server
"""

import json
import requests
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import tempfile
import shutil

class MAMSClient:
    def __init__(self):
        self.base_url = ""
        self.api_key = ""
        self.access_token = ""
        self.session = requests.Session()
        self._load_config()
        
    def _load_config(self):
        """Load configuration from settings file"""
        config_path = os.path.expanduser("~/.mams/resolve_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.base_url = config.get('server_url', '')
                    self.api_key = config.get('api_key', '')
                    self.access_token = config.get('access_token', '')
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save_config(self, server_url: str, api_key: str):
        """Save configuration to settings file"""
        config_dir = os.path.expanduser("~/.mams")
        os.makedirs(config_dir, exist_ok=True)
        
        config = {
            'server_url': server_url,
            'api_key': api_key,
            'access_token': self.access_token
        }
        
        config_path = os.path.join(config_dir, 'resolve_config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.base_url = server_url
        self.api_key = api_key
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to MAMS API"""
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MAMS-Resolve/1.0'
        }
        
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        elif self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    
    def test_connection(self) -> bool:
        """Test connection to MAMS server"""
        try:
            response = self._request('GET', '/api/v1/health')
            return response.status_code == 200
        except:
            return False
    
    def login(self, username: str, password: str) -> bool:
        """Login to MAMS server"""
        try:
            response = self._request('POST', '/api/v1/auth/login', 
                                   json={'username': username, 'password': password})
            data = response.json()
            self.access_token = data.get('access_token', '')
            return bool(self.access_token)
        except:
            return False
    
    def search_assets(self, query: str = "", filters: Dict[str, Any] = None) -> List[Dict]:
        """Search for assets in MAMS"""
        params = {'q': query}
        if filters:
            params.update(filters)
        
        try:
            response = self._request('GET', '/api/v1/assets/search', params=params)
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get asset details by ID"""
        try:
            response = self._request('GET', f'/api/v1/assets/{asset_id}')
            return response.json()
        except:
            return None
    
    def get_asset_metadata(self, asset_id: str) -> Dict[str, Any]:
        """Get asset metadata"""
        try:
            response = self._request('GET', f'/api/v1/assets/{asset_id}/metadata')
            return response.json()
        except:
            return {}
    
    def download_asset(self, asset_id: str, quality: str = 'proxy') -> Optional[str]:
        """Download asset to local temporary file"""
        try:
            # Get download URL
            response = self._request('GET', f'/api/v1/assets/{asset_id}/download', 
                                   params={'quality': quality})
            download_data = response.json()
            download_url = download_data.get('url')
            filename = download_data.get('filename', f'asset_{asset_id}')
            
            if not download_url:
                return None
            
            # Download file
            file_response = requests.get(download_url, stream=True)
            file_response.raise_for_status()
            
            # Save to temporary file
            temp_dir = tempfile.mkdtemp(prefix='mams_resolve_')
            local_path = os.path.join(temp_dir, filename)
            
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(file_response.raw, f)
            
            return local_path
            
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def get_proxy_url(self, asset_id: str) -> Optional[str]:
        """Get proxy URL for streaming"""
        try:
            response = self._request('GET', f'/api/v1/assets/{asset_id}/proxy')
            data = response.json()
            return data.get('url')
        except:
            return None
    
    def upload_asset(self, file_path: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Upload asset to MAMS"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'metadata': json.dumps(metadata or {})}
                
                headers = {}
                if self.api_key:
                    headers['X-API-Key'] = self.api_key
                elif self.access_token:
                    headers['Authorization'] = f'Bearer {self.access_token}'
                
                response = requests.post(
                    f"{self.base_url}/api/v1/assets/upload",
                    files=files,
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('id')
                
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def create_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """Create project in MAMS"""
        try:
            response = self._request('POST', '/api/v1/projects', json=project_data)
            data = response.json()
            return data.get('id')
        except Exception as e:
            print(f"Project creation error: {e}")
            return None
    
    def sync_project(self, project_data: Dict[str, Any]) -> bool:
        """Sync project with MAMS"""
        try:
            response = self._request('POST', '/api/v1/projects/sync', json=project_data)
            return response.status_code == 200
        except Exception as e:
            print(f"Project sync error: {e}")
            return False
    
    def get_projects(self) -> List[Dict]:
        """Get list of projects"""
        try:
            response = self._request('GET', '/api/v1/projects')
            data = response.json()
            return data.get('data', [])
        except:
            return []
    
    def get_collections(self) -> List[Dict]:
        """Get list of collections"""
        try:
            response = self._request('GET', '/api/v1/collections')
            data = response.json()
            return data.get('data', [])
        except:
            return []
    
    def download_lut(self, lut_name: str) -> Optional[str]:
        """Download LUT file for color grading"""
        try:
            response = self._request('GET', f'/api/v1/luts/{lut_name}/download')
            download_data = response.json()
            download_url = download_data.get('url')
            
            if not download_url:
                return None
            
            # Download LUT file
            lut_response = requests.get(download_url)
            lut_response.raise_for_status()
            
            # Save to temporary file
            temp_dir = tempfile.mkdtemp(prefix='mams_luts_')
            lut_path = os.path.join(temp_dir, f'{lut_name}.cube')
            
            with open(lut_path, 'wb') as f:
                f.write(lut_response.content)
            
            return lut_path
            
        except Exception as e:
            print(f"LUT download error: {e}")
            return None
    
    def update_asset_metadata(self, asset_id: str, metadata: Dict[str, Any]) -> bool:
        """Update asset metadata"""
        try:
            response = self._request('PATCH', f'/api/v1/assets/{asset_id}/metadata', 
                                   json=metadata)
            return response.status_code == 200
        except Exception as e:
            print(f"Metadata update error: {e}")
            return False

# Global instance
mams_client = MAMSClient()