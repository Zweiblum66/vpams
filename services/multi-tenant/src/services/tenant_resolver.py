"""
Tenant Resolver - Service for resolving tenant context from various sources.

Handles tenant identification from:
- Custom domains
- Subdomains
- API keys
- JWT tokens
- Request headers
"""

import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import structlog
from urllib.parse import urlparse

from ..core.config import get_settings
from ..core.exceptions import TenantNotFoundError, ValidationError
from ..models.schemas import TenantContext, TenantInfo


logger = structlog.get_logger()


class TenantResolver:
    """
    Resolves tenant context from incoming requests.
    
    Supports multiple resolution strategies:
    - Domain-based resolution (custom domains)
    - Subdomain-based resolution
    - Header-based resolution (X-Tenant-ID)
    - Token-based resolution (JWT claims)
    - API key-based resolution
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Cache for domain -> tenant mappings
        self.domain_cache: Dict[str, str] = {}
        self.subdomain_cache: Dict[str, str] = {}
        
        # Cache TTL
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Compiled regex patterns
        self.subdomain_pattern = re.compile(r'^([a-z0-9-]+)\.' + re.escape(self.settings.base_domain))
        self.api_key_pattern = re.compile(r'^mams_[a-z0-9]{32}$')
        
        # Statistics
        self.stats = {
            "resolutions_total": 0,
            "domain_resolutions": 0,
            "subdomain_resolutions": 0,
            "header_resolutions": 0,
            "token_resolutions": 0,
            "api_key_resolutions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "resolution_failures": 0
        }
    
    async def initialize(self) -> None:
        """Initialize tenant resolver."""
        try:
            logger.info("Initializing tenant resolver")
            
            # Load initial domain mappings
            await self._load_domain_mappings()
            
            logger.info(
                "Tenant resolver initialized",
                domains_cached=len(self.domain_cache),
                subdomains_cached=len(self.subdomain_cache)
            )
            
        except Exception as e:
            logger.error("Failed to initialize tenant resolver", error=str(e))
            raise
    
    async def resolve_tenant(
        self,
        host: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        token_claims: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None
    ) -> Optional[TenantContext]:
        """
        Resolve tenant context from request information.
        
        Resolution order:
        1. Explicit header (X-Tenant-ID)
        2. API key
        3. JWT token claims
        4. Custom domain
        5. Subdomain
        
        Args:
            host: Request host header
            headers: Request headers
            token_claims: Decoded JWT claims
            api_key: API key from request
            
        Returns:
            TenantContext if resolved, None otherwise
        """
        self.stats["resolutions_total"] += 1
        
        try:
            # 1. Check explicit header
            if headers:
                tenant_id = await self._resolve_from_header(headers)
                if tenant_id:
                    self.stats["header_resolutions"] += 1
                    return await self._create_context(tenant_id, "header")
            
            # 2. Check API key
            if api_key:
                tenant_id = await self._resolve_from_api_key(api_key)
                if tenant_id:
                    self.stats["api_key_resolutions"] += 1
                    return await self._create_context(tenant_id, "api_key")
            
            # 3. Check JWT token
            if token_claims:
                tenant_id = await self._resolve_from_token(token_claims)
                if tenant_id:
                    self.stats["token_resolutions"] += 1
                    return await self._create_context(tenant_id, "token")
            
            # 4. Check custom domain
            if host:
                tenant_id = await self._resolve_from_domain(host)
                if tenant_id:
                    self.stats["domain_resolutions"] += 1
                    return await self._create_context(tenant_id, "domain")
                
                # 5. Check subdomain
                tenant_id = await self._resolve_from_subdomain(host)
                if tenant_id:
                    self.stats["subdomain_resolutions"] += 1
                    return await self._create_context(tenant_id, "subdomain")
            
            # No tenant resolved
            self.stats["resolution_failures"] += 1
            return None
            
        except Exception as e:
            logger.error("Error resolving tenant", error=str(e))
            self.stats["resolution_failures"] += 1
            return None
    
    async def _resolve_from_header(self, headers: Dict[str, str]) -> Optional[str]:
        """Resolve tenant from request headers."""
        # Check X-Tenant-ID header
        tenant_id = headers.get("x-tenant-id") or headers.get("X-Tenant-ID")
        
        if tenant_id:
            # Validate tenant ID format
            if self._validate_tenant_id(tenant_id):
                logger.debug("Resolved tenant from header", tenant_id=tenant_id)
                return tenant_id
            else:
                logger.warning("Invalid tenant ID in header", tenant_id=tenant_id)
        
        return None
    
    async def _resolve_from_api_key(self, api_key: str) -> Optional[str]:
        """Resolve tenant from API key."""
        # Validate API key format
        if not self.api_key_pattern.match(api_key):
            logger.warning("Invalid API key format", api_key=api_key[:10] + "...")
            return None
        
        # Look up tenant from API key
        # In production, this would query the database
        # For now, extract tenant ID from key structure
        if api_key.startswith("mams_"):
            # Mock extraction - would be database lookup
            tenant_id = api_key[5:13]  # Extract portion as tenant ID
            if self._validate_tenant_id(tenant_id):
                logger.debug("Resolved tenant from API key", tenant_id=tenant_id)
                return tenant_id
        
        return None
    
    async def _resolve_from_token(self, token_claims: Dict[str, Any]) -> Optional[str]:
        """Resolve tenant from JWT token claims."""
        # Check for tenant_id claim
        tenant_id = token_claims.get("tenant_id")
        
        if tenant_id and self._validate_tenant_id(tenant_id):
            logger.debug("Resolved tenant from token", tenant_id=tenant_id)
            return tenant_id
        
        # Check for custom claims
        custom_claims = token_claims.get("custom", {})
        tenant_id = custom_claims.get("tenant_id")
        
        if tenant_id and self._validate_tenant_id(tenant_id):
            logger.debug("Resolved tenant from custom token claims", tenant_id=tenant_id)
            return tenant_id
        
        return None
    
    async def _resolve_from_domain(self, host: str) -> Optional[str]:
        """Resolve tenant from custom domain."""
        # Normalize host
        domain = self._normalize_domain(host)
        
        # Check cache
        if domain in self.domain_cache:
            if self._is_cache_valid(domain):
                self.stats["cache_hits"] += 1
                return self.domain_cache[domain]
        
        self.stats["cache_misses"] += 1
        
        # Query domain manager for tenant
        # In production, this would use the domain_manager service
        tenant_id = await self._lookup_domain_tenant(domain)
        
        if tenant_id:
            # Update cache
            self.domain_cache[domain] = tenant_id
            self.cache_timestamps[domain] = datetime.utcnow()
            
            logger.debug("Resolved tenant from domain", domain=domain, tenant_id=tenant_id)
            return tenant_id
        
        return None
    
    async def _resolve_from_subdomain(self, host: str) -> Optional[str]:
        """Resolve tenant from subdomain."""
        # Extract subdomain
        match = self.subdomain_pattern.match(host.lower())
        
        if match:
            subdomain = match.group(1)
            
            # Check cache
            if subdomain in self.subdomain_cache:
                if self._is_cache_valid(subdomain):
                    self.stats["cache_hits"] += 1
                    return self.subdomain_cache[subdomain]
            
            self.stats["cache_misses"] += 1
            
            # Look up tenant by subdomain
            tenant_id = await self._lookup_subdomain_tenant(subdomain)
            
            if tenant_id:
                # Update cache
                self.subdomain_cache[subdomain] = tenant_id
                self.cache_timestamps[subdomain] = datetime.utcnow()
                
                logger.debug("Resolved tenant from subdomain", subdomain=subdomain, tenant_id=tenant_id)
                return tenant_id
        
        return None
    
    def _normalize_domain(self, host: str) -> str:
        """Normalize domain name."""
        # Remove port if present
        domain = host.split(':')[0]
        
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain.lower()
    
    def _validate_tenant_id(self, tenant_id: str) -> bool:
        """Validate tenant ID format."""
        # Tenant IDs should be 8 characters, alphanumeric
        if len(tenant_id) != 8:
            return False
        
        return tenant_id.isalnum()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self.cache_timestamps:
            return False
        
        age = (datetime.utcnow() - self.cache_timestamps[key]).total_seconds()
        return age < self.cache_ttl
    
    async def _create_context(self, tenant_id: str, source: str) -> TenantContext:
        """Create tenant context."""
        # Get tenant info
        tenant_info = await self._get_tenant_info(tenant_id)
        
        if not tenant_info:
            raise TenantNotFoundError(tenant_id)
        
        return TenantContext(
            tenant_id=tenant_id,
            name=tenant_info.name,
            subdomain=tenant_info.subdomain,
            is_active=tenant_info.is_active,
            plan=tenant_info.plan,
            resolved_from=source,
            created_at=datetime.utcnow()
        )
    
    async def _lookup_domain_tenant(self, domain: str) -> Optional[str]:
        """Look up tenant ID from custom domain."""
        # In production, this would query the domain_manager
        # Mock implementation
        mock_domains = {
            "customer1.com": "tenant001",
            "customer2.net": "tenant002"
        }
        
        return mock_domains.get(domain)
    
    async def _lookup_subdomain_tenant(self, subdomain: str) -> Optional[str]:
        """Look up tenant ID from subdomain."""
        # In production, this would query the tenant_manager
        # Mock implementation returns subdomain as tenant ID if valid
        if self._validate_tenant_id(subdomain):
            return subdomain
        
        return None
    
    async def _get_tenant_info(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant information."""
        # In production, this would query the tenant_manager
        # Mock implementation
        return TenantInfo(
            tenant_id=tenant_id,
            name=f"Tenant {tenant_id}",
            subdomain=tenant_id,
            is_active=True,
            plan="standard"
        )
    
    async def _load_domain_mappings(self) -> None:
        """Load domain mappings from storage."""
        # In production, this would load from database
        # Mock implementation
        self.domain_cache = {
            "customer1.com": "tenant001",
            "customer2.net": "tenant002"
        }
        
        self.subdomain_cache = {
            "tenant001": "tenant001",
            "tenant002": "tenant002"
        }
    
    async def invalidate_cache(self, tenant_id: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        if tenant_id:
            # Remove specific tenant from caches
            domains_to_remove = [
                domain for domain, tid in self.domain_cache.items()
                if tid == tenant_id
            ]
            
            for domain in domains_to_remove:
                del self.domain_cache[domain]
                if domain in self.cache_timestamps:
                    del self.cache_timestamps[domain]
            
            subdomains_to_remove = [
                subdomain for subdomain, tid in self.subdomain_cache.items()
                if tid == tenant_id
            ]
            
            for subdomain in subdomains_to_remove:
                del self.subdomain_cache[subdomain]
                if subdomain in self.cache_timestamps:
                    del self.cache_timestamps[subdomain]
            
            logger.info("Cache invalidated for tenant", tenant_id=tenant_id)
        
        else:
            # Clear all caches
            self.domain_cache.clear()
            self.subdomain_cache.clear()
            self.cache_timestamps.clear()
            
            logger.info("All caches cleared")
    
    async def add_domain_mapping(self, domain: str, tenant_id: str) -> None:
        """Add domain to tenant mapping."""
        domain = self._normalize_domain(domain)
        
        self.domain_cache[domain] = tenant_id
        self.cache_timestamps[domain] = datetime.utcnow()
        
        logger.info("Added domain mapping", domain=domain, tenant_id=tenant_id)
    
    async def remove_domain_mapping(self, domain: str) -> None:
        """Remove domain mapping."""
        domain = self._normalize_domain(domain)
        
        if domain in self.domain_cache:
            del self.domain_cache[domain]
        
        if domain in self.cache_timestamps:
            del self.cache_timestamps[domain]
        
        logger.info("Removed domain mapping", domain=domain)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get resolver statistics."""
        return {
            **self.stats,
            "domains_cached": len(self.domain_cache),
            "subdomains_cached": len(self.subdomain_cache),
            "cache_size": len(self.cache_timestamps)
        }
    
    async def cleanup(self) -> None:
        """Cleanup resolver resources."""
        try:
            # Clear caches
            self.domain_cache.clear()
            self.subdomain_cache.clear()
            self.cache_timestamps.clear()
            
            logger.info("Tenant resolver cleanup completed")
            
        except Exception as e:
            logger.error("Error during tenant resolver cleanup", error=str(e))