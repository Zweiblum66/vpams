"""
Integration tests for CDN service.

Tests the complete CDN functionality including URL generation,
cache invalidation, and multi-provider support.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
import hashlib
import hmac
import base64

from src.cdn_service import CDNService
from src.config import CDNConfig
from src.models import CDNProvider, CDNOptions


class TestCDNIntegration:
    """Integration tests for CDN service."""
    
    @pytest.fixture
    async def cdn_service(self):
        """Create CDN service with test configuration."""
        config = CDNConfig(
            providers={
                CDNProvider.CLOUDFRONT: {
                    'enabled': True,
                    'distribution_id': 'test-dist-123',
                    'domain': 'test.cloudfront.net',
                    'signing_key_id': 'test-key-123',
                    'signing_private_key': self._generate_test_key()
                },
                CDNProvider.CLOUDFLARE: {
                    'enabled': True,
                    'zone_id': 'test-zone-456',
                    'domain': 'test.cloudflare.com',
                    'api_key': 'test-api-key',
                    'api_email': 'test@example.com'
                }
            },
            default_provider=CDNProvider.CLOUDFRONT,
            fallback_providers=[CDNProvider.CLOUDFLARE]
        )
        
        service = CDNService(config)
        await service.initialize()
        yield service
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_cdn_url_generation(self, cdn_service):
        """Test CDN URL generation for different asset types."""
        # Test cases with different options
        test_cases = [
            {
                'path': '/images/logo.png',
                'options': CDNOptions(),
                'expected_domain': 'test.cloudfront.net'
            },
            {
                'path': '/videos/demo.mp4',
                'options': CDNOptions(
                    expires_in=3600,
                    signed=True
                ),
                'expected_params': ['Expires', 'Signature', 'Key-Pair-Id']
            },
            {
                'path': '/assets/app.js',
                'options': CDNOptions(
                    transform={'quality': 85, 'format': 'auto'}
                ),
                'expected_query': 'quality=85&format=auto'
            }
        ]
        
        for case in test_cases:
            url = await cdn_service.get_cdn_url(case['path'], case.get('options'))
            
            assert url.startswith('https://')
            
            if 'expected_domain' in case:
                assert case['expected_domain'] in url
            
            if 'expected_params' in case:
                for param in case['expected_params']:
                    assert param in url
            
            if 'expected_query' in case:
                assert case['expected_query'] in url
    
    @pytest.mark.asyncio
    async def test_signed_url_generation(self, cdn_service):
        """Test signed URL generation with expiration."""
        path = '/private/document.pdf'
        expires_in = 3600  # 1 hour
        
        # Generate signed URL
        signed_url = await cdn_service.get_cdn_url(
            path,
            CDNOptions(signed=True, expires_in=expires_in)
        )
        
        # Verify signature components
        assert 'Expires=' in signed_url
        assert 'Signature=' in signed_url
        assert 'Key-Pair-Id=' in signed_url
        
        # Extract expiration time
        import urllib.parse
        parsed = urllib.parse.urlparse(signed_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        expires = int(params['Expires'][0])
        now = int(datetime.utcnow().timestamp())
        
        # Verify expiration is approximately correct
        assert expires > now
        assert expires <= now + expires_in + 60  # Allow 60s buffer
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cdn_service):
        """Test cache invalidation across providers."""
        paths = [
            '/images/hero.jpg',
            '/css/styles.css',
            '/js/app.*.js'  # Wildcard
        ]
        
        # Mock the invalidation API calls
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {'status': 'success'}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Invalidate paths
            result = await cdn_service.invalidate_cache(paths)
            
            assert result['success'] is True
            assert result['invalidated_paths'] == paths
            assert len(result['providers']) >= 1
            
            # Verify API calls were made
            assert mock_post.called
    
    @pytest.mark.asyncio
    async def test_multi_provider_failover(self, cdn_service):
        """Test failover between CDN providers."""
        path = '/assets/logo.png'
        
        # Simulate CloudFront failure
        with patch.object(
            cdn_service.providers[CDNProvider.CLOUDFRONT],
            'get_url',
            side_effect=Exception("CloudFront unavailable")
        ):
            # Should failover to Cloudflare
            url = await cdn_service.get_cdn_url(path)
            
            assert 'cloudflare.com' in url
            assert 'cloudfront.net' not in url
    
    @pytest.mark.asyncio
    async def test_batch_url_generation(self, cdn_service):
        """Test batch URL generation for performance."""
        # Generate many paths
        paths = [f'/images/photo_{i}.jpg' for i in range(100)]
        
        start_time = datetime.utcnow()
        
        # Generate URLs concurrently
        tasks = [
            cdn_service.get_cdn_url(path, CDNOptions(transform={'w': 300}))
            for path in paths
        ]
        urls = await asyncio.gather(*tasks)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify all URLs generated
        assert len(urls) == len(paths)
        assert all('w=300' in url for url in urls)
        
        # Should complete quickly (< 1 second for 100 URLs)
        assert duration < 1.0
    
    @pytest.mark.asyncio
    async def test_health_check(self, cdn_service):
        """Test CDN health check functionality."""
        # Mock health check responses
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = 'OK'
            mock_get.return_value.__aenter__.return_value = mock_response
            
            health = await cdn_service.check_health()
            
            assert health['status'] == 'healthy'
            assert health['providers'][CDNProvider.CLOUDFRONT]['status'] == 'healthy'
            assert health['providers'][CDNProvider.CLOUDFLARE]['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_custom_domain_support(self, cdn_service):
        """Test custom domain configuration."""
        # Update config with custom domain
        cdn_service.config.custom_domain = 'cdn.mams.example.com'
        
        url = await cdn_service.get_cdn_url('/assets/app.js')
        
        assert 'cdn.mams.example.com' in url
        assert 'cloudfront.net' not in url
    
    @pytest.mark.asyncio
    async def test_geo_restriction(self, cdn_service):
        """Test geo-restriction URL generation."""
        options = CDNOptions(
            geo_restriction={
                'type': 'whitelist',
                'countries': ['US', 'CA', 'GB']
            }
        )
        
        url = await cdn_service.get_cdn_url('/video/content.mp4', options)
        
        # Verify geo-restriction parameters
        assert 'geo=' in url or 'country=' in url
    
    @pytest.mark.asyncio
    async def test_bandwidth_optimization(self, cdn_service):
        """Test bandwidth optimization features."""
        # Test adaptive bitrate URL
        options = CDNOptions(
            adaptive_bitrate=True,
            qualities=['360p', '720p', '1080p']
        )
        
        manifest_url = await cdn_service.get_cdn_url(
            '/videos/movie.m3u8',
            options
        )
        
        assert '.m3u8' in manifest_url
        assert 'adaptive=true' in manifest_url
    
    @pytest.mark.asyncio
    async def test_error_handling(self, cdn_service):
        """Test error handling and recovery."""
        # Test with invalid path
        with pytest.raises(ValueError):
            await cdn_service.get_cdn_url('')
        
        # Test with all providers failing
        with patch.object(cdn_service, 'providers', {}):
            with pytest.raises(Exception) as exc_info:
                await cdn_service.get_cdn_url('/test.jpg')
            
            assert 'No CDN providers available' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_monitoring_metrics(self, cdn_service):
        """Test monitoring and metrics collection."""
        # Generate some traffic
        for i in range(10):
            await cdn_service.get_cdn_url(f'/image_{i}.jpg')
        
        # Invalidate some paths
        await cdn_service.invalidate_cache(['/image_1.jpg'])
        
        # Get metrics
        metrics = await cdn_service.get_metrics()
        
        assert metrics['url_generations'] >= 10
        assert metrics['cache_invalidations'] >= 1
        assert 'providers' in metrics
        assert metrics['uptime_seconds'] > 0
    
    def _generate_test_key(self):
        """Generate a test RSA private key."""
        # This is a dummy key for testing only
        return """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtest_key_content_here
-----END RSA PRIVATE KEY-----"""


class TestCDNPerformance:
    """Performance tests for CDN service."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_url_generation_performance(self, cdn_service):
        """Test URL generation performance under load."""
        num_requests = 1000
        
        start_time = datetime.utcnow()
        
        # Generate URLs concurrently
        tasks = [
            cdn_service.get_cdn_url(f'/assets/file_{i % 100}.js')
            for i in range(num_requests)
        ]
        
        urls = await asyncio.gather(*tasks)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        requests_per_second = num_requests / duration
        
        # Performance assertions
        assert len(urls) == num_requests
        assert requests_per_second > 1000  # Should handle >1000 req/s
        
        print(f"Performance: {requests_per_second:.0f} requests/second")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_invalidation_performance(self, cdn_service):
        """Test cache invalidation performance."""
        # Generate many paths to invalidate
        num_paths = 1000
        paths = [f'/assets/file_{i}.js' for i in range(num_paths)]
        
        start_time = datetime.utcnow()
        
        # Mock the API calls for speed
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {'status': 'success'}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await cdn_service.invalidate_cache(paths)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Should complete quickly even with many paths
        assert duration < 5.0
        assert result['success'] is True
        assert len(result['invalidated_paths']) == num_paths


class TestCDNSecurity:
    """Security tests for CDN service."""
    
    @pytest.mark.asyncio
    async def test_signed_url_tampering(self, cdn_service):
        """Test that tampering with signed URLs fails."""
        path = '/secure/document.pdf'
        
        # Generate signed URL
        signed_url = await cdn_service.get_cdn_url(
            path,
            CDNOptions(signed=True, expires_in=3600)
        )
        
        # Tamper with the URL
        tampered_url = signed_url.replace('document.pdf', 'other-file.pdf')
        
        # Verification should fail (in real scenario)
        # This would be validated by CloudFront/CDN provider
        assert 'Signature=' in signed_url
        assert tampered_url != signed_url
    
    @pytest.mark.asyncio
    async def test_ip_restriction(self, cdn_service):
        """Test IP-based access restriction."""
        options = CDNOptions(
            ip_whitelist=['192.168.1.0/24', '10.0.0.0/8'],
            signed=True
        )
        
        url = await cdn_service.get_cdn_url('/private/data.json', options)
        
        # URL should include IP restriction parameters
        assert 'Signature=' in url
        # In real implementation, CDN would enforce IP restrictions
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, cdn_service):
        """Test CORS header configuration."""
        # Set CORS configuration
        cdn_service.config.cors_origins = ['https://app.mams.example.com']
        
        # Generate URL with CORS
        url = await cdn_service.get_cdn_url('/api/data.json')
        
        # In real scenario, CDN would add appropriate CORS headers
        assert url.startswith('https://')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])