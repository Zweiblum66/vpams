"""
Domain Manager - Service for managing custom domains for tenants.

Handles domain registration, verification, SSL provisioning, and DNS management.
"""

import asyncio
import uuid
import hashlib
import dns.resolver
import ssl
import socket
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from ..core.config import get_settings
from ..core.exceptions import (
    DomainNotAvailableError, DomainVerificationError,
    ConfigurationError, ValidationError
)
from ..models.schemas import DomainInfo, DomainVerificationMethod


logger = structlog.get_logger()


class DomainManager:
    """
    Manages custom domains for tenants including:
    - Domain registration and validation
    - DNS verification
    - SSL certificate provisioning
    - Domain routing configuration
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Domain registry
        self.domain_registry: Dict[str, str] = {}  # domain -> tenant_id
        self.tenant_domains: Dict[str, List[DomainInfo]] = {}  # tenant_id -> domains
        
        # Verification tokens
        self.verification_tokens: Dict[str, Dict[str, Any]] = {}
        
        # SSL certificates cache
        self.ssl_certificates: Dict[str, Dict[str, Any]] = {}
        
        # DNS resolver
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5.0
        self.resolver.lifetime = 10.0
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # Statistics
        self.stats = {
            "domains_registered": 0,
            "domains_verified": 0,
            "ssl_certificates_issued": 0,
            "verification_failures": 0,
            "last_verification": None
        }
    
    async def initialize(self) -> None:
        """Initialize domain manager."""
        try:
            logger.info("Initializing domain manager")
            
            # Load existing domain mappings
            await self._load_domain_registry()
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Domain manager initialized",
                total_domains=len(self.domain_registry),
                custom_domains_enabled=self.settings.custom_domains_enabled
            )
            
        except Exception as e:
            logger.error("Failed to initialize domain manager", error=str(e))
            raise ConfigurationError(f"Domain manager initialization failed: {str(e)}")
    
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        # Domain verification check
        if self.settings.domain_verification_enabled:
            task = asyncio.create_task(self._verification_check_loop())
            self._tasks.append(task)
        
        # SSL certificate renewal
        if self.settings.domain_ssl_auto_provision:
            task = asyncio.create_task(self._ssl_renewal_loop())
            self._tasks.append(task)
        
        # DNS health check
        task = asyncio.create_task(self._dns_health_check_loop())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def configure_domain(
        self,
        tenant_id: str,
        domain: str,
        auto_verify: bool = True,
        auto_ssl: bool = True
    ) -> DomainInfo:
        """
        Configure a custom domain for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            domain: Domain name (e.g., example.com)
            auto_verify: Automatically start verification
            auto_ssl: Automatically provision SSL certificate
            
        Returns:
            Domain configuration information
        """
        try:
            # Normalize domain
            domain = domain.lower().strip()
            
            # Validate domain format
            if not self._validate_domain_format(domain):
                raise ValidationError(f"Invalid domain format: {domain}")
            
            # Check if domain is available
            if domain in self.domain_registry:
                existing_tenant = self.domain_registry[domain]
                if existing_tenant != tenant_id:
                    raise DomainNotAvailableError(
                        domain,
                        f"Already registered to tenant {existing_tenant}"
                    )
            
            # Create domain info
            domain_info = DomainInfo(
                domain=domain,
                subdomain=None,
                is_verified=False,
                verification_token=self._generate_verification_token(tenant_id, domain),
                ssl_enabled=False,
                ssl_certificate_id=None,
                created_at=datetime.utcnow(),
                verified_at=None,
                dns_records=[]
            )
            
            # Register domain
            self.domain_registry[domain] = tenant_id
            
            if tenant_id not in self.tenant_domains:
                self.tenant_domains[tenant_id] = []
            self.tenant_domains[tenant_id].append(domain_info)
            
            # Generate DNS records for verification
            domain_info.dns_records = await self._generate_dns_records(
                domain,
                tenant_id,
                domain_info.verification_token
            )
            
            # Store verification token
            self.verification_tokens[domain] = {
                "tenant_id": tenant_id,
                "token": domain_info.verification_token,
                "created_at": datetime.utcnow(),
                "method": "dns"
            }
            
            self.stats["domains_registered"] += 1
            
            logger.info(
                "Domain configured",
                tenant_id=tenant_id,
                domain=domain,
                verification_token=domain_info.verification_token
            )
            
            # Start verification if requested
            if auto_verify:
                asyncio.create_task(self._auto_verify_domain(domain, tenant_id))
            
            return domain_info
            
        except Exception as e:
            logger.error("Failed to configure domain", 
                       tenant_id=tenant_id, 
                       domain=domain, 
                       error=str(e))
            raise
    
    async def verify_domain(
        self,
        tenant_id: str,
        domain: str,
        method: DomainVerificationMethod = DomainVerificationMethod.DNS
    ) -> bool:
        """
        Verify domain ownership.
        
        Args:
            tenant_id: Tenant identifier
            domain: Domain to verify
            method: Verification method
            
        Returns:
            True if verification successful
        """
        try:
            # Check domain ownership
            if self.domain_registry.get(domain) != tenant_id:
                raise ValidationError("Domain not registered to tenant")
            
            # Get verification token
            token_info = self.verification_tokens.get(domain)
            if not token_info:
                raise ValidationError("No verification token found")
            
            verification_successful = False
            
            if method == DomainVerificationMethod.DNS:
                verification_successful = await self._verify_dns_record(
                    domain,
                    token_info["token"]
                )
            
            elif method == DomainVerificationMethod.FILE:
                verification_successful = await self._verify_file_upload(
                    domain,
                    token_info["token"]
                )
            
            elif method == DomainVerificationMethod.META:
                verification_successful = await self._verify_meta_tag(
                    domain,
                    token_info["token"]
                )
            
            if verification_successful:
                # Update domain info
                await self._mark_domain_verified(tenant_id, domain)
                
                self.stats["domains_verified"] += 1
                self.stats["last_verification"] = datetime.utcnow()
                
                logger.info(
                    "Domain verified successfully",
                    tenant_id=tenant_id,
                    domain=domain,
                    method=method.value
                )
                
                # Provision SSL if enabled
                if self.settings.domain_ssl_auto_provision:
                    asyncio.create_task(self._provision_ssl_certificate(domain, tenant_id))
                
                return True
            
            else:
                self.stats["verification_failures"] += 1
                raise DomainVerificationError(
                    domain,
                    f"Verification failed using method: {method.value}"
                )
                
        except Exception as e:
            logger.error("Domain verification failed", 
                       tenant_id=tenant_id, 
                       domain=domain, 
                       error=str(e))
            raise
    
    async def remove_domain(self, tenant_id: str, domain: str) -> None:
        """Remove a custom domain from tenant."""
        try:
            # Verify ownership
            if self.domain_registry.get(domain) != tenant_id:
                raise ValidationError("Domain not owned by tenant")
            
            # Remove from registry
            del self.domain_registry[domain]
            
            # Remove from tenant domains
            if tenant_id in self.tenant_domains:
                self.tenant_domains[tenant_id] = [
                    d for d in self.tenant_domains[tenant_id] 
                    if d.domain != domain
                ]
            
            # Cleanup verification tokens
            if domain in self.verification_tokens:
                del self.verification_tokens[domain]
            
            # Cleanup SSL certificates
            if domain in self.ssl_certificates:
                await self._revoke_ssl_certificate(domain)
                del self.ssl_certificates[domain]
            
            logger.info(
                "Domain removed",
                tenant_id=tenant_id,
                domain=domain
            )
            
        except Exception as e:
            logger.error("Failed to remove domain", 
                       tenant_id=tenant_id, 
                       domain=domain, 
                       error=str(e))
            raise
    
    async def get_tenant_domains(self, tenant_id: str) -> List[DomainInfo]:
        """Get all domains for a tenant."""
        return self.tenant_domains.get(tenant_id, [])
    
    async def get_domain_info(self, domain: str) -> Optional[DomainInfo]:
        """Get domain information."""
        tenant_id = self.domain_registry.get(domain)
        if not tenant_id:
            return None
        
        tenant_domains = self.tenant_domains.get(tenant_id, [])
        for domain_info in tenant_domains:
            if domain_info.domain == domain:
                return domain_info
        
        return None
    
    def _validate_domain_format(self, domain: str) -> bool:
        """Validate domain format."""
        # Basic validation
        if not domain or len(domain) > 253:
            return False
        
        # Check for valid characters
        import re
        pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
        return bool(re.match(pattern, domain))
    
    def _generate_verification_token(self, tenant_id: str, domain: str) -> str:
        """Generate verification token for domain."""
        # Create unique token
        data = f"{tenant_id}:{domain}:{datetime.utcnow().isoformat()}"
        token = hashlib.sha256(data.encode()).hexdigest()[:32]
        return f"mams-verify-{token}"
    
    async def _generate_dns_records(
        self,
        domain: str,
        tenant_id: str,
        verification_token: str
    ) -> List[Dict[str, Any]]:
        """Generate DNS records for domain configuration."""
        records = []
        
        # TXT record for verification
        records.append({
            "type": "TXT",
            "name": f"_mams-verify.{domain}",
            "value": verification_token,
            "ttl": 300,
            "purpose": "domain_verification"
        })
        
        # CNAME record for app access
        records.append({
            "type": "CNAME",
            "name": domain,
            "value": f"{tenant_id}.mams.app",
            "ttl": 3600,
            "purpose": "app_routing"
        })
        
        # Additional records for subdomain
        records.append({
            "type": "CNAME",
            "name": f"www.{domain}",
            "value": f"{tenant_id}.mams.app",
            "ttl": 3600,
            "purpose": "www_redirect"
        })
        
        return records
    
    async def _verify_dns_record(self, domain: str, expected_token: str) -> bool:
        """Verify domain via DNS TXT record."""
        try:
            # Query TXT records
            txt_name = f"_mams-verify.{domain}"
            
            answers = self.resolver.resolve(txt_name, 'TXT')
            
            for rdata in answers:
                for txt_string in rdata.strings:
                    txt_value = txt_string.decode('utf-8')
                    if txt_value == expected_token:
                        return True
            
            return False
            
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, Exception) as e:
            logger.debug("DNS verification failed", domain=domain, error=str(e))
            return False
    
    async def _verify_file_upload(self, domain: str, expected_token: str) -> bool:
        """Verify domain via file upload."""
        try:
            # Check for verification file at well-known location
            import aiohttp
            
            url = f"https://{domain}/.well-known/mams-verify.txt"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content.strip() == expected_token
            
            return False
            
        except Exception as e:
            logger.debug("File verification failed", domain=domain, error=str(e))
            return False
    
    async def _verify_meta_tag(self, domain: str, expected_token: str) -> bool:
        """Verify domain via HTML meta tag."""
        try:
            # Check for meta tag on homepage
            import aiohttp
            from bs4 import BeautifulSoup
            
            url = f"https://{domain}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Look for verification meta tag
                        meta_tag = soup.find('meta', {'name': 'mams-verify'})
                        if meta_tag and meta_tag.get('content') == expected_token:
                            return True
            
            return False
            
        except Exception as e:
            logger.debug("Meta tag verification failed", domain=domain, error=str(e))
            return False
    
    async def _mark_domain_verified(self, tenant_id: str, domain: str) -> None:
        """Mark domain as verified."""
        if tenant_id in self.tenant_domains:
            for domain_info in self.tenant_domains[tenant_id]:
                if domain_info.domain == domain:
                    domain_info.is_verified = True
                    domain_info.verified_at = datetime.utcnow()
                    break
    
    async def _auto_verify_domain(self, domain: str, tenant_id: str) -> None:
        """Automatically attempt domain verification."""
        # Wait a bit for DNS propagation
        await asyncio.sleep(60)
        
        # Try verification up to 5 times
        for attempt in range(5):
            try:
                if await self.verify_domain(tenant_id, domain):
                    logger.info("Auto-verification successful", domain=domain)
                    return
            except Exception:
                pass
            
            # Wait before retry
            await asyncio.sleep(300)  # 5 minutes
        
        logger.warning("Auto-verification failed after 5 attempts", domain=domain)
    
    async def _provision_ssl_certificate(self, domain: str, tenant_id: str) -> None:
        """Provision SSL certificate for domain."""
        try:
            logger.info("Provisioning SSL certificate", domain=domain)
            
            # In production, this would use Let's Encrypt or similar
            # For now, generate self-signed certificate
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MAMS"),
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(domain),
                    x509.DNSName(f"www.{domain}"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Store certificate
            cert_id = str(uuid.uuid4())
            self.ssl_certificates[domain] = {
                "certificate_id": cert_id,
                "certificate": cert.public_bytes(serialization.Encoding.PEM),
                "private_key": private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ),
                "issued_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=365),
                "tenant_id": tenant_id
            }
            
            # Update domain info
            if tenant_id in self.tenant_domains:
                for domain_info in self.tenant_domains[tenant_id]:
                    if domain_info.domain == domain:
                        domain_info.ssl_enabled = True
                        domain_info.ssl_certificate_id = cert_id
                        break
            
            self.stats["ssl_certificates_issued"] += 1
            
            logger.info(
                "SSL certificate provisioned",
                domain=domain,
                certificate_id=cert_id
            )
            
        except Exception as e:
            logger.error("Failed to provision SSL certificate", 
                       domain=domain, 
                       error=str(e))
    
    async def _revoke_ssl_certificate(self, domain: str) -> None:
        """Revoke SSL certificate for domain."""
        # In production, this would revoke with CA
        logger.info("SSL certificate revoked", domain=domain)
    
    async def check_ssl_expiry(self, domain: str) -> Optional[datetime]:
        """Check SSL certificate expiry date."""
        cert_info = self.ssl_certificates.get(domain)
        if cert_info:
            return cert_info["expires_at"]
        return None
    
    async def _verification_check_loop(self) -> None:
        """Background task to check domain verifications."""
        while self._running:
            try:
                # Check unverified domains
                for domain, token_info in self.verification_tokens.items():
                    tenant_id = token_info["tenant_id"]
                    
                    # Skip if already verified
                    domain_info = await self.get_domain_info(domain)
                    if domain_info and domain_info.is_verified:
                        continue
                    
                    # Check age
                    age = (datetime.utcnow() - token_info["created_at"]).total_seconds()
                    if age > 86400:  # 24 hours
                        logger.warning(
                            "Domain verification expired",
                            domain=domain,
                            tenant_id=tenant_id
                        )
                        continue
                    
                    # Try verification
                    try:
                        if await self._verify_dns_record(domain, token_info["token"]):
                            await self._mark_domain_verified(tenant_id, domain)
                            logger.info("Domain verified via background check", domain=domain)
                    except Exception:
                        pass
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error("Error in verification check loop", error=str(e))
                await asyncio.sleep(3600)
    
    async def _ssl_renewal_loop(self) -> None:
        """Background task to renew SSL certificates."""
        while self._running:
            try:
                # Check SSL certificates for renewal
                for domain, cert_info in self.ssl_certificates.items():
                    expires_at = cert_info["expires_at"]
                    days_until_expiry = (expires_at - datetime.utcnow()).days
                    
                    if days_until_expiry <= 30:  # Renew 30 days before expiry
                        tenant_id = cert_info["tenant_id"]
                        logger.info(
                            "SSL certificate renewal needed",
                            domain=domain,
                            days_until_expiry=days_until_expiry
                        )
                        
                        await self._provision_ssl_certificate(domain, tenant_id)
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error("Error in SSL renewal loop", error=str(e))
                await asyncio.sleep(86400)
    
    async def _dns_health_check_loop(self) -> None:
        """Background task to check DNS health."""
        while self._running:
            try:
                # Check DNS resolution for verified domains
                for domain, tenant_id in self.domain_registry.items():
                    domain_info = await self.get_domain_info(domain)
                    
                    if domain_info and domain_info.is_verified:
                        # Check CNAME record
                        try:
                            answers = self.resolver.resolve(domain, 'CNAME')
                            resolved = False
                            
                            for rdata in answers:
                                if f"{tenant_id}.mams.app" in str(rdata.target):
                                    resolved = True
                                    break
                            
                            if not resolved:
                                logger.warning(
                                    "DNS resolution issue detected",
                                    domain=domain,
                                    tenant_id=tenant_id
                                )
                        except Exception:
                            pass
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error("Error in DNS health check loop", error=str(e))
                await asyncio.sleep(3600)
    
    async def _load_domain_registry(self) -> None:
        """Load existing domain mappings from storage."""
        # In production, this would load from database
        logger.info("Loading domain registry")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get domain manager statistics."""
        return {
            **self.stats,
            "total_domains": len(self.domain_registry),
            "verified_domains": sum(
                1 for domains in self.tenant_domains.values()
                for d in domains if d.is_verified
            ),
            "ssl_enabled_domains": sum(
                1 for domains in self.tenant_domains.values()
                for d in domains if d.ssl_enabled
            ),
            "pending_verifications": len(self.verification_tokens)
        }
    
    async def cleanup(self) -> None:
        """Cleanup domain manager resources."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info("Domain manager cleanup completed")
            
        except Exception as e:
            logger.error("Error during domain manager cleanup", error=str(e))