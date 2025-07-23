"""
Cache utilities for CDN service
"""

import hashlib
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
import mimetypes


class CacheKeyGenerator:
    """
    Generates cache keys for CDN content
    """
    
    def __init__(self):
        self.static_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.ico', '.svg',
            '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
            '.mp4', '.webm', '.mp3', '.wav', '.m4a',
            '.pdf', '.zip', '.tar', '.gz'
        }
        
        self.ignore_query_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', '_ga', 'mc_cid', 'mc_eid'
        }
    
    def generate_cache_key(
        self,
        url: str,
        query_string_behavior: str = "none",
        query_string_keys: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        headers_behavior: str = "none",
        headers_whitelist: Optional[List[str]] = None
    ) -> str:
        """Generate a cache key based on URL and configuration"""
        parsed = urlparse(url)
        
        # Start with base path
        key_parts = [parsed.netloc, parsed.path]
        
        # Handle query strings
        if query_string_behavior != "none" and parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            if query_string_behavior == "whitelist" and query_string_keys:
                # Only include whitelisted query parameters
                filtered_params = {
                    k: v for k, v in query_params.items()
                    if k in query_string_keys
                }
            elif query_string_behavior == "all":
                # Include all query parameters except tracking ones
                filtered_params = {
                    k: v for k, v in query_params.items()
                    if k not in self.ignore_query_params
                }
            else:
                filtered_params = {}
            
            if filtered_params:
                # Sort parameters for consistent key generation
                sorted_params = sorted(filtered_params.items())
                query_string = urlencode(sorted_params, doseq=True)
                key_parts.append(query_string)
        
        # Handle headers
        if headers and headers_behavior != "none":
            header_parts = []
            
            if headers_behavior == "whitelist" and headers_whitelist:
                # Only include whitelisted headers
                for header_name in sorted(headers_whitelist):
                    if header_name in headers:
                        header_parts.append(f"{header_name}:{headers[header_name]}")
            elif headers_behavior == "all":
                # Include all headers
                for header_name, header_value in sorted(headers.items()):
                    header_parts.append(f"{header_name}:{header_value}")
            
            if header_parts:
                key_parts.extend(header_parts)
        
        # Generate hash of all parts
        cache_key = ":".join(key_parts)
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    def is_cacheable_by_extension(self, url: str) -> bool:
        """Check if URL has a cacheable file extension"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        for ext in self.static_extensions:
            if path.endswith(ext):
                return True
        
        return False
    
    def get_content_type(self, url: str) -> str:
        """Get content type from URL"""
        parsed = urlparse(url)
        content_type, _ = mimetypes.guess_type(parsed.path)
        return content_type or "application/octet-stream"
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent caching"""
        parsed = urlparse(url.lower())
        
        # Remove default ports
        netloc = parsed.netloc
        if parsed.port:
            if (parsed.scheme == 'http' and parsed.port == 80) or \
               (parsed.scheme == 'https' and parsed.port == 443):
                netloc = parsed.hostname
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/') or '/'
        
        # Rebuild URL
        normalized = f"{parsed.scheme}://{netloc}{path}"
        
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def extract_cache_tags(self, url: str, headers: Optional[Dict[str, str]] = None) -> List[str]:
        """Extract cache tags from URL and headers"""
        tags = []
        
        # Extract from URL path
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Add path-based tags
        for i, part in enumerate(path_parts):
            if part:
                # Add hierarchical tags
                tags.append(f"path:{'/'.join(path_parts[:i+1])}")
        
        # Add file type tag
        content_type = self.get_content_type(url)
        if content_type:
            tags.append(f"type:{content_type.split('/')[0]}")
            tags.append(f"mime:{content_type}")
        
        # Extract from headers
        if headers:
            # Add tenant tag if present
            if 'X-Tenant-ID' in headers:
                tags.append(f"tenant:{headers['X-Tenant-ID']}")
            
            # Add user tag if present
            if 'X-User-ID' in headers:
                tags.append(f"user:{headers['X-User-ID']}")
            
            # Add custom cache tags
            if 'Cache-Tag' in headers:
                custom_tags = headers['Cache-Tag'].split(',')
                tags.extend([tag.strip() for tag in custom_tags])
        
        return list(set(tags))  # Remove duplicates
    
    def should_bypass_cache(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Determine if request should bypass cache"""
        # Only cache GET and HEAD requests
        if method not in ['GET', 'HEAD']:
            return True
        
        # Check for no-cache headers
        if headers:
            cache_control = headers.get('Cache-Control', '').lower()
            if 'no-cache' in cache_control or 'no-store' in cache_control:
                return True
            
            if headers.get('Pragma') == 'no-cache':
                return True
        
        # Check for authentication
        if headers and 'Authorization' in headers:
            return True
        
        # Check for dynamic content patterns
        parsed = urlparse(url)
        dynamic_patterns = [
            r'/api/',
            r'/admin/',
            r'/auth/',
            r'/ws/',
            r'/realtime/'
        ]
        
        for pattern in dynamic_patterns:
            if re.search(pattern, parsed.path):
                return True
        
        return False
    
    def calculate_ttl(
        self,
        url: str,
        content_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        default_ttl: int = 3600
    ) -> int:
        """Calculate TTL for cache entry"""
        if not content_type:
            content_type = self.get_content_type(url)
        
        # Check for explicit cache control
        if headers:
            cache_control = headers.get('Cache-Control', '')
            max_age_match = re.search(r'max-age=(\d+)', cache_control)
            if max_age_match:
                return int(max_age_match.group(1))
            
            # Check for expires header
            if 'Expires' in headers:
                # In real implementation, parse expires date
                pass
        
        # Use content-type based TTLs
        ttl_by_type = {
            'image/': 86400 * 30,  # 30 days for images
            'video/': 86400 * 7,   # 7 days for videos
            'audio/': 86400 * 7,   # 7 days for audio
            'text/css': 86400 * 7, # 7 days for CSS
            'application/javascript': 86400 * 7,  # 7 days for JS
            'application/json': 300,  # 5 minutes for JSON
            'text/html': 300,  # 5 minutes for HTML
        }
        
        for prefix, ttl in ttl_by_type.items():
            if content_type.startswith(prefix):
                return ttl
        
        return default_ttl
    
    def generate_vary_key(
        self,
        base_key: str,
        vary_headers: List[str],
        request_headers: Dict[str, str]
    ) -> str:
        """Generate cache key variation based on Vary headers"""
        vary_parts = [base_key]
        
        for header in vary_headers:
            value = request_headers.get(header, '')
            vary_parts.append(f"{header}:{value}")
        
        return hashlib.md5(':'.join(vary_parts).encode()).hexdigest()
    
    def parse_cache_control(self, cache_control: str) -> Dict[str, Optional[str]]:
        """Parse Cache-Control header into directives"""
        directives = {}
        
        for directive in cache_control.split(','):
            directive = directive.strip()
            
            if '=' in directive:
                key, value = directive.split('=', 1)
                directives[key.strip()] = value.strip()
            else:
                directives[directive] = None
        
        return directives
    
    def is_stale(
        self,
        cached_time: float,
        ttl: int,
        cache_control: Optional[str] = None
    ) -> bool:
        """Check if cached content is stale"""
        import time
        
        age = time.time() - cached_time
        
        if age > ttl:
            return True
        
        if cache_control:
            directives = self.parse_cache_control(cache_control)
            
            # Check for must-revalidate
            if 'must-revalidate' in directives:
                return True
            
            # Check for stale-while-revalidate
            if 'stale-while-revalidate' in directives:
                swr_window = int(directives['stale-while-revalidate'] or 0)
                if age > ttl + swr_window:
                    return True
        
        return False