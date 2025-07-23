"""
Integration tests for domain verification flows.

Tests the complete domain verification process including:
- Domain configuration
- DNS verification
- SSL provisioning
- Domain routing
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import dns.resolver

from ..src.services.domain_manager import DomainManager
from ..src.services.tenant_resolver import TenantResolver
from ..src.models.schemas import DomainInfo, DomainVerificationMethod
from ..src.core.exceptions import (
    DomainNotAvailableError, DomainVerificationError,
    ValidationError
)


class TestDomainVerification:
    """Test domain verification workflows."""
    
    @pytest.fixture
    async def domain_manager(self):
        """Create domain manager instance."""
        manager = DomainManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def tenant_resolver(self):
        """Create tenant resolver instance."""
        resolver = TenantResolver()
        await resolver.initialize()
        yield resolver
        await resolver.cleanup()
    
    @pytest.mark.asyncio
    async def test_domain_configuration(self, domain_manager):
        """Test domain configuration process."""
        tenant_id = "tenant001"
        domain = "example.com"
        
        # Configure domain
        domain_info = await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain,
            auto_verify=False,
            auto_ssl=False
        )
        
        # Verify domain info
        assert domain_info.domain == domain
        assert not domain_info.is_verified
        assert domain_info.verification_token.startswith("mams-verify-")
        assert len(domain_info.dns_records) > 0
        
        # Verify DNS records generated
        txt_record = next(
            (r for r in domain_info.dns_records if r["type"] == "TXT"),
            None
        )
        assert txt_record is not None
        assert txt_record["name"] == f"_mams-verify.{domain}"
        assert txt_record["value"] == domain_info.verification_token
    
    @pytest.mark.asyncio
    async def test_duplicate_domain_rejection(self, domain_manager):
        """Test that duplicate domains are rejected."""
        tenant1 = "tenant001"
        tenant2 = "tenant002"
        domain = "example.com"
        
        # Configure domain for tenant1
        await domain_manager.configure_domain(
            tenant_id=tenant1,
            domain=domain
        )
        
        # Try to configure same domain for tenant2
        with pytest.raises(DomainNotAvailableError) as exc_info:
            await domain_manager.configure_domain(
                tenant_id=tenant2,
                domain=domain
            )
        
        assert domain in str(exc_info.value)
        assert tenant1 in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_dns_verification_success(self, domain_manager):
        """Test successful DNS verification."""
        tenant_id = "tenant001"
        domain = "verified.com"
        
        # Configure domain
        domain_info = await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain,
            auto_verify=False
        )
        
        # Mock DNS resolver to return correct TXT record
        with patch.object(domain_manager.resolver, 'resolve') as mock_resolve:
            # Create mock DNS response
            mock_answer = Mock()
            mock_rdata = Mock()
            mock_rdata.strings = [domain_info.verification_token.encode()]
            mock_answer.__iter__ = Mock(return_value=iter([mock_rdata]))
            mock_resolve.return_value = mock_answer
            
            # Verify domain
            verified = await domain_manager.verify_domain(
                tenant_id=tenant_id,
                domain=domain,
                method=DomainVerificationMethod.DNS
            )
            
            assert verified is True
            
            # Check domain is marked as verified
            updated_info = await domain_manager.get_domain_info(domain)
            assert updated_info.is_verified
            assert updated_info.verified_at is not None
    
    @pytest.mark.asyncio
    async def test_dns_verification_failure(self, domain_manager):
        """Test DNS verification failure."""
        tenant_id = "tenant001"
        domain = "unverified.com"
        
        # Configure domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain,
            auto_verify=False
        )
        
        # Mock DNS resolver to return wrong TXT record
        with patch.object(domain_manager.resolver, 'resolve') as mock_resolve:
            mock_resolve.side_effect = dns.resolver.NXDOMAIN
            
            # Try to verify domain
            with pytest.raises(DomainVerificationError):
                await domain_manager.verify_domain(
                    tenant_id=tenant_id,
                    domain=domain,
                    method=DomainVerificationMethod.DNS
                )
    
    @pytest.mark.asyncio
    async def test_file_verification(self, domain_manager):
        """Test file-based domain verification."""
        tenant_id = "tenant001"
        domain = "filetest.com"
        
        # Configure domain
        domain_info = await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Mock HTTP request for file verification
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value=domain_info.verification_token
            )
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Verify domain
            verified = await domain_manager.verify_domain(
                tenant_id=tenant_id,
                domain=domain,
                method=DomainVerificationMethod.FILE
            )
            
            assert verified is True
    
    @pytest.mark.asyncio
    async def test_meta_tag_verification(self, domain_manager):
        """Test meta tag domain verification."""
        tenant_id = "tenant001"
        domain = "metatest.com"
        
        # Configure domain
        domain_info = await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Mock HTTP request for meta tag verification
        html_content = f'''
        <html>
        <head>
            <meta name="mams-verify" content="{domain_info.verification_token}">
        </head>
        <body>Test</body>
        </html>
        '''
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=html_content)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Verify domain
            verified = await domain_manager.verify_domain(
                tenant_id=tenant_id,
                domain=domain,
                method=DomainVerificationMethod.META
            )
            
            assert verified is True
    
    @pytest.mark.asyncio
    async def test_ssl_provisioning(self, domain_manager):
        """Test SSL certificate provisioning."""
        tenant_id = "tenant001"
        domain = "ssltest.com"
        
        # Configure and verify domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain,
            auto_ssl=False
        )
        
        # Mock DNS verification
        with patch.object(domain_manager, '_verify_dns_record', return_value=True):
            await domain_manager.verify_domain(
                tenant_id=tenant_id,
                domain=domain
            )
        
        # Wait for SSL provisioning (triggered by verification)
        await asyncio.sleep(0.1)
        
        # Check SSL certificate
        ssl_expiry = await domain_manager.check_ssl_expiry(domain)
        assert ssl_expiry is not None
        assert ssl_expiry > datetime.utcnow()
        
        # Verify certificate stored
        assert domain in domain_manager.ssl_certificates
        cert_info = domain_manager.ssl_certificates[domain]
        assert cert_info["tenant_id"] == tenant_id
        assert "certificate" in cert_info
        assert "private_key" in cert_info
    
    @pytest.mark.asyncio
    async def test_domain_removal(self, domain_manager):
        """Test domain removal process."""
        tenant_id = "tenant001"
        domain = "remove.com"
        
        # Configure domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Verify domain exists
        domain_info = await domain_manager.get_domain_info(domain)
        assert domain_info is not None
        
        # Remove domain
        await domain_manager.remove_domain(tenant_id, domain)
        
        # Verify domain removed
        domain_info = await domain_manager.get_domain_info(domain)
        assert domain_info is None
        
        # Verify tenant can't access removed domain
        with pytest.raises(ValidationError):
            await domain_manager.remove_domain(tenant_id, domain)
    
    @pytest.mark.asyncio
    async def test_tenant_domain_resolution(self, domain_manager, tenant_resolver):
        """Test domain-based tenant resolution."""
        tenant_id = "tenant001"
        domain = "resolution.com"
        
        # Configure and verify domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Add domain mapping to resolver
        await tenant_resolver.add_domain_mapping(domain, tenant_id)
        
        # Test resolution
        context = await tenant_resolver.resolve_tenant(host=domain)
        assert context is not None
        assert context.tenant_id == tenant_id
        assert context.resolved_from == "domain"
    
    @pytest.mark.asyncio
    async def test_subdomain_resolution(self, tenant_resolver):
        """Test subdomain-based tenant resolution."""
        tenant_id = "tenant001"
        subdomain = tenant_id
        host = f"{subdomain}.mams.app"
        
        # Mock subdomain lookup
        with patch.object(
            tenant_resolver,
            '_lookup_subdomain_tenant',
            return_value=tenant_id
        ):
            context = await tenant_resolver.resolve_tenant(host=host)
            assert context is not None
            assert context.tenant_id == tenant_id
            assert context.resolved_from == "subdomain"
    
    @pytest.mark.asyncio
    async def test_auto_verification_flow(self, domain_manager):
        """Test automatic domain verification flow."""
        tenant_id = "tenant001"
        domain = "autotest.com"
        
        # Mock DNS verification to succeed on second attempt
        call_count = 0
        
        async def mock_verify_dns(domain, token):
            nonlocal call_count
            call_count += 1
            return call_count >= 2  # Succeed on second attempt
        
        with patch.object(domain_manager, '_verify_dns_record', side_effect=mock_verify_dns):
            # Configure with auto-verify
            domain_info = await domain_manager.configure_domain(
                tenant_id=tenant_id,
                domain=domain,
                auto_verify=True
            )
            
            # Wait for auto-verification
            await asyncio.sleep(65)  # Wait for first retry
            
            # Check domain status
            updated_info = await domain_manager.get_domain_info(domain)
            assert updated_info.is_verified
    
    @pytest.mark.asyncio
    async def test_invalid_domain_formats(self, domain_manager):
        """Test rejection of invalid domain formats."""
        tenant_id = "tenant001"
        
        invalid_domains = [
            "not a domain",
            "http://example.com",
            "example..com",
            "-example.com",
            "example.com-",
            "example.c",
            "a" * 254,  # Too long
            "",
            "example.123"
        ]
        
        for invalid_domain in invalid_domains:
            with pytest.raises(ValidationError):
                await domain_manager.configure_domain(
                    tenant_id=tenant_id,
                    domain=invalid_domain
                )
    
    @pytest.mark.asyncio
    async def test_domain_statistics(self, domain_manager):
        """Test domain manager statistics."""
        tenant_id = "tenant001"
        
        # Configure multiple domains
        domains = ["test1.com", "test2.com", "test3.com"]
        for domain in domains:
            await domain_manager.configure_domain(
                tenant_id=tenant_id,
                domain=domain
            )
        
        # Get statistics
        stats = await domain_manager.get_statistics()
        
        assert stats["domains_registered"] == 3
        assert stats["total_domains"] == 3
        assert stats["verified_domains"] == 0
        assert stats["ssl_enabled_domains"] == 0
        
        # Verify one domain
        with patch.object(domain_manager, '_verify_dns_record', return_value=True):
            await domain_manager.verify_domain(tenant_id, domains[0])
        
        # Check updated stats
        stats = await domain_manager.get_statistics()
        assert stats["domains_verified"] == 1
        assert stats["verified_domains"] == 1


class TestDomainBackgroundTasks:
    """Test background tasks for domain management."""
    
    @pytest.mark.asyncio
    async def test_verification_check_loop(self, domain_manager):
        """Test background verification checking."""
        tenant_id = "tenant001"
        domain = "bgtest.com"
        
        # Configure domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Mock DNS to return correct record after some time
        with patch.object(domain_manager, '_verify_dns_record', return_value=True):
            # Trigger verification check
            await domain_manager._verification_check_loop()
            
            # Check domain is verified
            domain_info = await domain_manager.get_domain_info(domain)
            assert domain_info.is_verified
    
    @pytest.mark.asyncio
    async def test_ssl_renewal_check(self, domain_manager):
        """Test SSL certificate renewal checking."""
        tenant_id = "tenant001"
        domain = "renewtest.com"
        
        # Create expired certificate
        domain_manager.ssl_certificates[domain] = {
            "certificate_id": "test-cert",
            "tenant_id": tenant_id,
            "expires_at": datetime.utcnow() + timedelta(days=25),  # Near expiry
            "certificate": b"mock-cert",
            "private_key": b"mock-key"
        }
        
        # Run renewal check
        with patch.object(domain_manager, '_provision_ssl_certificate') as mock_provision:
            await domain_manager._ssl_renewal_loop()
            
            # Verify renewal was triggered
            mock_provision.assert_called_once_with(domain, tenant_id)
    
    @pytest.mark.asyncio
    async def test_dns_health_monitoring(self, domain_manager):
        """Test DNS health monitoring."""
        tenant_id = "tenant001"
        domain = "healthtest.com"
        
        # Configure and verify domain
        await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain
        )
        
        # Mark as verified
        domain_manager.tenant_domains[tenant_id][0].is_verified = True
        
        # Mock DNS resolution failure
        with patch.object(domain_manager.resolver, 'resolve') as mock_resolve:
            mock_resolve.side_effect = Exception("DNS failure")
            
            # Run health check
            await domain_manager._dns_health_check_loop()
            
            # Should log warning but not crash
            # In real implementation, would check logs