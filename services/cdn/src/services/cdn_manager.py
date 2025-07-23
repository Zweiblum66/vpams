"""
CDN Manager for MAMS
Handles global content delivery network integration and management
"""

import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import mimetypes
from urllib.parse import urlparse, urljoin

import aioboto3
import aiohttp
import aioredis
from fastapi import HTTPException
import structlog

from ..core.config import settings
from ..models.schemas import (
    CDNProvider,
    CDNDistribution,
    CDNOrigin,
    CacheRule,
    EdgeLocation,
    PurgeRequest,
    PrefetchRequest,
    CDNMetrics,
    BandwidthUsage,
    CacheStatus,
    ContentOptimization,
    SecurityPolicy
)
from ..utils.cache import CacheKeyGenerator
from ..utils.metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class CDNProviderType(str, Enum):
    CLOUDFRONT = "cloudfront"
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    FASTLY = "fastly"
    AZURE_CDN = "azure_cdn"
    CUSTOM = "custom"


class CacheStrategy(str, Enum):
    CACHE_EVERYTHING = "cache_everything"
    CACHE_STATIC = "cache_static"
    CACHE_DYNAMIC = "cache_dynamic"
    BYPASS_CACHE = "bypass_cache"
    CUSTOM_RULES = "custom_rules"


class OptimizationType(str, Enum):
    IMAGE_OPTIMIZATION = "image_optimization"
    VIDEO_TRANSCODING = "video_transcoding"
    COMPRESSION = "compression"
    MINIFICATION = "minification"
    WEBP_CONVERSION = "webp_conversion"


class GlobalCDNManager:
    """
    Manages global CDN integration for MAMS
    """
    
    def __init__(self):
        self.providers: Dict[str, CDNProvider] = {}
        self.distributions: Dict[str, CDNDistribution] = {}
        self.edge_locations: Dict[str, List[EdgeLocation]] = {}
        self.metrics = MetricsCollector()
        self.cache_key_generator = CacheKeyGenerator()
        
        # Provider clients
        self.cloudfront_client: Optional[Any] = None
        self.cloudflare_client: Optional[Any] = None
        self.akamai_client: Optional[Any] = None
        self.fastly_client: Optional[Any] = None
        
        # Cache for CDN configurations
        self.redis_client: Optional[aioredis.Redis] = None
        
        # HTTP session for API calls
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        self._initialized = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize CDN manager"""
        if self._initialized:
            return
        
        logger.info("Initializing CDN manager")
        
        # Initialize Redis connection
        self.redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Initialize HTTP session
        self.http_session = aiohttp.ClientSession()
        
        # Initialize CDN providers
        await self._initialize_providers()
        
        # Load existing distributions
        await self._load_distributions()
        
        # Start monitoring
        self._monitor_task = asyncio.create_task(self._monitor_cdn_health())
        
        self._initialized = True
        logger.info("CDN manager initialized")
    
    async def _initialize_providers(self):
        """Initialize CDN provider connections"""
        # CloudFront
        if settings.ENABLE_CLOUDFRONT:
            session = aioboto3.Session()
            self.cloudfront_client = await session.client(
                "cloudfront",
                region_name=settings.AWS_REGION
            ).__aenter__()
            
            provider = CDNProvider(
                provider_id="cloudfront",
                provider_type=CDNProviderType.CLOUDFRONT,
                name="AWS CloudFront",
                enabled=True,
                configuration={
                    "distribution_id": settings.CLOUDFRONT_DISTRIBUTION_ID,
                    "origin_access_identity": settings.CLOUDFRONT_OAI
                }
            )
            self.providers["cloudfront"] = provider
        
        # Cloudflare
        if settings.ENABLE_CLOUDFLARE:
            provider = CDNProvider(
                provider_id="cloudflare",
                provider_type=CDNProviderType.CLOUDFLARE,
                name="Cloudflare",
                enabled=True,
                configuration={
                    "zone_id": settings.CLOUDFLARE_ZONE_ID,
                    "api_token": settings.CLOUDFLARE_API_TOKEN
                }
            )
            self.providers["cloudflare"] = provider
        
        # Akamai
        if settings.ENABLE_AKAMAI:
            provider = CDNProvider(
                provider_id="akamai",
                provider_type=CDNProviderType.AKAMAI,
                name="Akamai",
                enabled=True,
                configuration={
                    "host": settings.AKAMAI_HOST,
                    "client_token": settings.AKAMAI_CLIENT_TOKEN,
                    "client_secret": settings.AKAMAI_CLIENT_SECRET,
                    "access_token": settings.AKAMAI_ACCESS_TOKEN
                }
            )
            self.providers["akamai"] = provider
    
    async def create_distribution(
        self,
        name: str,
        origins: List[CDNOrigin],
        cache_rules: List[CacheRule],
        provider_id: str = "cloudfront",
        custom_domain: Optional[str] = None,
        security_policy: Optional[SecurityPolicy] = None
    ) -> CDNDistribution:
        """Create a new CDN distribution"""
        provider = self.providers.get(provider_id)
        if not provider:
            raise ValueError(f"CDN provider {provider_id} not found")
        
        distribution_id = f"dist-{hashlib.md5(name.encode()).hexdigest()[:8]}"
        
        # Create distribution based on provider
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            cdn_config = await self._create_cloudfront_distribution(
                name, origins, cache_rules, custom_domain, security_policy
            )
        elif provider.provider_type == CDNProviderType.CLOUDFLARE:
            cdn_config = await self._create_cloudflare_distribution(
                name, origins, cache_rules, custom_domain, security_policy
            )
        else:
            raise NotImplementedError(f"Provider {provider.provider_type} not implemented")
        
        # Create distribution object
        distribution = CDNDistribution(
            distribution_id=distribution_id,
            provider_id=provider_id,
            name=name,
            status="deploying",
            domain_name=cdn_config.get("domain_name"),
            custom_domain=custom_domain,
            origins=origins,
            cache_rules=cache_rules,
            security_policy=security_policy or SecurityPolicy(),
            created_at=datetime.utcnow()
        )
        
        # Store distribution
        self.distributions[distribution_id] = distribution
        await self._save_distribution(distribution)
        
        # Log creation
        logger.info(
            "CDN distribution created",
            distribution_id=distribution_id,
            provider=provider_id,
            domain=distribution.domain_name
        )
        
        return distribution
    
    async def _create_cloudfront_distribution(
        self,
        name: str,
        origins: List[CDNOrigin],
        cache_rules: List[CacheRule],
        custom_domain: Optional[str],
        security_policy: Optional[SecurityPolicy]
    ) -> Dict[str, Any]:
        """Create CloudFront distribution"""
        # Build origin configuration
        origin_items = []
        for i, origin in enumerate(origins):
            origin_config = {
                "Id": f"origin-{i}",
                "DomainName": origin.domain_name,
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "https-only",
                    "OriginSSLProtocols": {
                        "Quantity": 1,
                        "Items": ["TLSv1.2"]
                    }
                }
            }
            
            if origin.origin_path:
                origin_config["OriginPath"] = origin.origin_path
            
            if origin.custom_headers:
                origin_config["CustomHeaders"] = {
                    "Quantity": len(origin.custom_headers),
                    "Items": [
                        {"HeaderName": k, "HeaderValue": v}
                        for k, v in origin.custom_headers.items()
                    ]
                }
            
            origin_items.append(origin_config)
        
        # Build cache behaviors
        cache_behaviors = []
        for rule in cache_rules:
            behavior = {
                "PathPattern": rule.path_pattern,
                "TargetOriginId": f"origin-{rule.origin_index}",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": len(rule.allowed_methods),
                    "Items": rule.allowed_methods,
                    "CachedMethods": {
                        "Quantity": len(rule.cached_methods),
                        "Items": rule.cached_methods
                    }
                },
                "Compress": rule.compress,
                "DefaultTTL": rule.default_ttl,
                "MaxTTL": rule.max_ttl,
                "MinTTL": rule.min_ttl
            }
            cache_behaviors.append(behavior)
        
        # Create distribution configuration
        config = {
            "CallerReference": f"{name}-{datetime.utcnow().timestamp()}",
            "Comment": f"MAMS CDN Distribution: {name}",
            "Enabled": True,
            "Origins": {
                "Quantity": len(origin_items),
                "Items": origin_items
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "origin-0",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 7,
                    "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"]
                    }
                },
                "Compress": True,
                "DefaultTTL": 86400,
                "MaxTTL": 31536000,
                "MinTTL": 0
            },
            "CacheBehaviors": {
                "Quantity": len(cache_behaviors),
                "Items": cache_behaviors
            } if cache_behaviors else {"Quantity": 0},
            "HttpVersion": "http2and3",
            "PriceClass": "PriceClass_All"
        }
        
        # Add custom domain if provided
        if custom_domain:
            config["Aliases"] = {
                "Quantity": 1,
                "Items": [custom_domain]
            }
            config["ViewerCertificate"] = {
                "ACMCertificateArn": settings.ACM_CERTIFICATE_ARN,
                "SSLSupportMethod": "sni-only",
                "MinimumProtocolVersion": "TLSv1.2_2021"
            }
        else:
            config["ViewerCertificate"] = {
                "CloudFrontDefaultCertificate": True
            }
        
        # Add security policy
        if security_policy:
            if security_policy.waf_enabled:
                config["WebACLId"] = settings.WAF_WEB_ACL_ID
            
            if security_policy.geo_restriction:
                config["Restrictions"] = {
                    "GeoRestriction": {
                        "RestrictionType": security_policy.geo_restriction.restriction_type,
                        "Quantity": len(security_policy.geo_restriction.locations),
                        "Items": security_policy.geo_restriction.locations
                    }
                }
        
        # Create distribution
        response = await self.cloudfront_client.create_distribution(
            DistributionConfig=config
        )
        
        return {
            "distribution_id": response["Distribution"]["Id"],
            "domain_name": response["Distribution"]["DomainName"],
            "status": response["Distribution"]["Status"],
            "arn": response["Distribution"]["ARN"]
        }
    
    async def _create_cloudflare_distribution(
        self,
        name: str,
        origins: List[CDNOrigin],
        cache_rules: List[CacheRule],
        custom_domain: Optional[str],
        security_policy: Optional[SecurityPolicy]
    ) -> Dict[str, Any]:
        """Create Cloudflare distribution"""
        zone_id = self.providers["cloudflare"].configuration["zone_id"]
        api_token = self.providers["cloudflare"].configuration["api_token"]
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Create page rules for caching
        for rule in cache_rules:
            rule_data = {
                "targets": [
                    {
                        "target": "url",
                        "constraint": {
                            "operator": "matches",
                            "value": f"*{custom_domain or 'example.com'}{rule.path_pattern}"
                        }
                    }
                ],
                "actions": [
                    {
                        "id": "cache_level",
                        "value": "cache_everything" if rule.cache_enabled else "bypass"
                    },
                    {
                        "id": "edge_cache_ttl",
                        "value": rule.default_ttl
                    }
                ],
                "priority": 1,
                "status": "active"
            }
            
            async with self.http_session.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/pagerules",
                json=rule_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to create Cloudflare page rule: {await response.text()}")
        
        return {
            "distribution_id": zone_id,
            "domain_name": custom_domain or f"{name}.cdn.mams.io",
            "status": "active"
        }
    
    async def update_distribution(
        self,
        distribution_id: str,
        cache_rules: Optional[List[CacheRule]] = None,
        security_policy: Optional[SecurityPolicy] = None,
        enabled: Optional[bool] = None
    ) -> CDNDistribution:
        """Update CDN distribution configuration"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        provider = self.providers.get(distribution.provider_id)
        if not provider:
            raise ValueError(f"Provider {distribution.provider_id} not found")
        
        # Update configuration based on provider
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            await self._update_cloudfront_distribution(
                distribution, cache_rules, security_policy, enabled
            )
        elif provider.provider_type == CDNProviderType.CLOUDFLARE:
            await self._update_cloudflare_distribution(
                distribution, cache_rules, security_policy, enabled
            )
        
        # Update local configuration
        if cache_rules is not None:
            distribution.cache_rules = cache_rules
        if security_policy is not None:
            distribution.security_policy = security_policy
        if enabled is not None:
            distribution.enabled = enabled
        
        distribution.updated_at = datetime.utcnow()
        
        # Save updated distribution
        await self._save_distribution(distribution)
        
        logger.info(
            "CDN distribution updated",
            distribution_id=distribution_id,
            provider=distribution.provider_id
        )
        
        return distribution
    
    async def purge_cache(
        self,
        distribution_id: str,
        paths: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        purge_all: bool = False
    ) -> PurgeRequest:
        """Purge CDN cache"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        provider = self.providers.get(distribution.provider_id)
        if not provider:
            raise ValueError(f"Provider {distribution.provider_id} not found")
        
        purge_request = PurgeRequest(
            request_id=f"purge-{datetime.utcnow().timestamp()}",
            distribution_id=distribution_id,
            paths=paths or [],
            tags=tags or [],
            purge_all=purge_all,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Execute purge based on provider
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            await self._purge_cloudfront_cache(distribution, purge_request)
        elif provider.provider_type == CDNProviderType.CLOUDFLARE:
            await self._purge_cloudflare_cache(distribution, purge_request)
        
        # Track purge request
        await self._track_purge_request(purge_request)
        
        # Update metrics
        self.metrics.increment("cdn.cache.purge.requests")
        self.metrics.increment(f"cdn.cache.purge.requests.{provider.provider_type}")
        
        logger.info(
            "Cache purge initiated",
            distribution_id=distribution_id,
            paths_count=len(paths or []),
            tags_count=len(tags or []),
            purge_all=purge_all
        )
        
        return purge_request
    
    async def _purge_cloudfront_cache(
        self,
        distribution: CDNDistribution,
        purge_request: PurgeRequest
    ):
        """Purge CloudFront cache"""
        paths_to_invalidate = purge_request.paths if not purge_request.purge_all else ["/*"]
        
        invalidation_batch = {
            "Paths": {
                "Quantity": len(paths_to_invalidate),
                "Items": paths_to_invalidate
            },
            "CallerReference": purge_request.request_id
        }
        
        response = await self.cloudfront_client.create_invalidation(
            DistributionId=distribution.provider_distribution_id,
            InvalidationBatch=invalidation_batch
        )
        
        purge_request.provider_request_id = response["Invalidation"]["Id"]
        purge_request.status = "in_progress"
    
    async def _purge_cloudflare_cache(
        self,
        distribution: CDNDistribution,
        purge_request: PurgeRequest
    ):
        """Purge Cloudflare cache"""
        zone_id = self.providers["cloudflare"].configuration["zone_id"]
        api_token = self.providers["cloudflare"].configuration["api_token"]
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        if purge_request.purge_all:
            data = {"purge_everything": True}
        elif purge_request.tags:
            data = {"tags": purge_request.tags}
        else:
            data = {"files": [
                f"https://{distribution.custom_domain or distribution.domain_name}{path}"
                for path in purge_request.paths
            ]}
        
        async with self.http_session.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
            json=data,
            headers=headers
        ) as response:
            result = await response.json()
            if result.get("success"):
                purge_request.status = "completed"
            else:
                purge_request.status = "failed"
                purge_request.error_message = str(result.get("errors", []))
    
    async def prefetch_content(
        self,
        distribution_id: str,
        urls: List[str],
        priority: str = "normal"
    ) -> PrefetchRequest:
        """Prefetch content to edge locations"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        prefetch_request = PrefetchRequest(
            request_id=f"prefetch-{datetime.utcnow().timestamp()}",
            distribution_id=distribution_id,
            urls=urls,
            priority=priority,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Execute prefetch based on provider
        provider = self.providers.get(distribution.provider_id)
        if provider and provider.provider_type == CDNProviderType.CLOUDFRONT:
            # CloudFront doesn't have direct prefetch, but we can warm the cache
            await self._warm_cloudfront_cache(distribution, urls)
        
        # Track prefetch request
        await self._track_prefetch_request(prefetch_request)
        
        logger.info(
            "Content prefetch initiated",
            distribution_id=distribution_id,
            urls_count=len(urls),
            priority=priority
        )
        
        return prefetch_request
    
    async def _warm_cloudfront_cache(
        self,
        distribution: CDNDistribution,
        urls: List[str]
    ):
        """Warm CloudFront cache by making requests"""
        tasks = []
        for url in urls:
            full_url = f"https://{distribution.domain_name}{url}"
            task = self._make_cache_warming_request(full_url)
            tasks.append(task)
        
        # Limit concurrent requests
        semaphore = asyncio.Semaphore(10)
        
        async def limited_request(url):
            async with semaphore:
                return await self._make_cache_warming_request(url)
        
        await asyncio.gather(*[limited_request(url) for url in urls])
    
    async def _make_cache_warming_request(self, url: str):
        """Make a request to warm the cache"""
        try:
            async with self.http_session.head(url) as response:
                logger.debug(f"Cache warming request: {url} - Status: {response.status}")
        except Exception as e:
            logger.error(f"Cache warming failed for {url}: {e}")
    
    async def get_metrics(
        self,
        distribution_id: str,
        start_time: datetime,
        end_time: datetime,
        metric_type: str = "all"
    ) -> CDNMetrics:
        """Get CDN metrics for a distribution"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        provider = self.providers.get(distribution.provider_id)
        if not provider:
            raise ValueError(f"Provider {distribution.provider_id} not found")
        
        # Get metrics based on provider
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            metrics_data = await self._get_cloudfront_metrics(
                distribution, start_time, end_time, metric_type
            )
        elif provider.provider_type == CDNProviderType.CLOUDFLARE:
            metrics_data = await self._get_cloudflare_metrics(
                distribution, start_time, end_time, metric_type
            )
        else:
            metrics_data = {}
        
        # Create metrics object
        metrics = CDNMetrics(
            distribution_id=distribution_id,
            period_start=start_time,
            period_end=end_time,
            requests_total=metrics_data.get("requests", 0),
            requests_cached=metrics_data.get("cached_requests", 0),
            cache_hit_rate=metrics_data.get("hit_rate", 0.0),
            bandwidth_bytes=metrics_data.get("bandwidth", 0),
            unique_visitors=metrics_data.get("unique_visitors", 0),
            error_rate=metrics_data.get("error_rate", 0.0),
            avg_response_time_ms=metrics_data.get("avg_response_time", 0.0)
        )
        
        return metrics
    
    async def _get_cloudfront_metrics(
        self,
        distribution: CDNDistribution,
        start_time: datetime,
        end_time: datetime,
        metric_type: str
    ) -> Dict[str, Any]:
        """Get CloudFront metrics using CloudWatch"""
        # This would use CloudWatch API to get metrics
        # Simplified for demonstration
        return {
            "requests": 1000000,
            "cached_requests": 950000,
            "hit_rate": 0.95,
            "bandwidth": 1024 * 1024 * 1024 * 100,  # 100GB
            "unique_visitors": 50000,
            "error_rate": 0.001,
            "avg_response_time": 50.0
        }
    
    async def optimize_content(
        self,
        distribution_id: str,
        optimization_type: OptimizationType,
        settings: Dict[str, Any]
    ) -> ContentOptimization:
        """Configure content optimization settings"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        optimization = ContentOptimization(
            optimization_id=f"opt-{datetime.utcnow().timestamp()}",
            distribution_id=distribution_id,
            optimization_type=optimization_type,
            settings=settings,
            enabled=True,
            created_at=datetime.utcnow()
        )
        
        # Apply optimization based on type
        if optimization_type == OptimizationType.IMAGE_OPTIMIZATION:
            await self._configure_image_optimization(distribution, settings)
        elif optimization_type == OptimizationType.VIDEO_TRANSCODING:
            await self._configure_video_transcoding(distribution, settings)
        elif optimization_type == OptimizationType.COMPRESSION:
            await self._configure_compression(distribution, settings)
        
        # Track optimization
        await self._save_optimization(optimization)
        
        logger.info(
            "Content optimization configured",
            distribution_id=distribution_id,
            optimization_type=optimization_type
        )
        
        return optimization
    
    async def _configure_image_optimization(
        self,
        distribution: CDNDistribution,
        settings: Dict[str, Any]
    ):
        """Configure image optimization"""
        # This would configure image optimization on the CDN
        # Settings might include:
        # - Auto WebP conversion
        # - Responsive image sizing
        # - Quality settings
        # - Format conversion
        pass
    
    async def get_edge_locations(
        self,
        distribution_id: Optional[str] = None
    ) -> List[EdgeLocation]:
        """Get edge locations for a distribution or provider"""
        if distribution_id:
            distribution = self.distributions.get(distribution_id)
            if not distribution:
                raise ValueError(f"Distribution {distribution_id} not found")
            
            provider_id = distribution.provider_id
        else:
            # Return all edge locations
            all_locations = []
            for provider_id, locations in self.edge_locations.items():
                all_locations.extend(locations)
            return all_locations
        
        # Get edge locations for specific provider
        if provider_id not in self.edge_locations:
            await self._load_edge_locations(provider_id)
        
        return self.edge_locations.get(provider_id, [])
    
    async def _load_edge_locations(self, provider_id: str):
        """Load edge locations for a provider"""
        provider = self.providers.get(provider_id)
        if not provider:
            return
        
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            # CloudFront edge locations
            locations = [
                EdgeLocation(
                    location_id="edge-us-east-1",
                    name="US East (N. Virginia)",
                    region="us-east-1",
                    country="US",
                    latitude=38.7489,
                    longitude=-77.4761,
                    status="active"
                ),
                EdgeLocation(
                    location_id="edge-eu-west-1",
                    name="EU (Ireland)",
                    region="eu-west-1",
                    country="IE",
                    latitude=53.4129,
                    longitude=-8.2439,
                    status="active"
                ),
                EdgeLocation(
                    location_id="edge-ap-southeast-1",
                    name="Asia Pacific (Singapore)",
                    region="ap-southeast-1",
                    country="SG",
                    latitude=1.2897,
                    longitude=103.8501,
                    status="active"
                ),
                # Add more edge locations as needed
            ]
            self.edge_locations[provider_id] = locations
    
    async def get_bandwidth_usage(
        self,
        distribution_id: str,
        start_time: datetime,
        end_time: datetime,
        group_by: str = "hour"
    ) -> List[BandwidthUsage]:
        """Get bandwidth usage data"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        # This would fetch actual bandwidth data from the CDN provider
        # For now, return sample data
        usage_data = []
        current_time = start_time
        
        while current_time < end_time:
            usage = BandwidthUsage(
                timestamp=current_time,
                bytes_in=1024 * 1024 * 100,  # 100MB
                bytes_out=1024 * 1024 * 500,  # 500MB
                requests=10000,
                unique_ips=1000
            )
            usage_data.append(usage)
            
            if group_by == "hour":
                current_time += timedelta(hours=1)
            elif group_by == "day":
                current_time += timedelta(days=1)
            else:
                break
        
        return usage_data
    
    async def configure_custom_headers(
        self,
        distribution_id: str,
        headers: Dict[str, str]
    ):
        """Configure custom headers for a distribution"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        provider = self.providers.get(distribution.provider_id)
        if not provider:
            raise ValueError(f"Provider {distribution.provider_id} not found")
        
        # Update headers based on provider
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            await self._update_cloudfront_headers(distribution, headers)
        elif provider.provider_type == CDNProviderType.CLOUDFLARE:
            await self._update_cloudflare_headers(distribution, headers)
        
        logger.info(
            "Custom headers configured",
            distribution_id=distribution_id,
            headers_count=len(headers)
        )
    
    async def enable_real_time_logs(
        self,
        distribution_id: str,
        log_destination: str
    ):
        """Enable real-time logging for a distribution"""
        distribution = self.distributions.get(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")
        
        provider = self.providers.get(distribution.provider_id)
        if not provider:
            raise ValueError(f"Provider {distribution.provider_id} not found")
        
        if provider.provider_type == CDNProviderType.CLOUDFRONT:
            # Configure CloudFront real-time logs
            config = {
                "EndPoints": [
                    {
                        "StreamType": "Kinesis",
                        "KinesisStreamConfig": {
                            "RoleARN": settings.KINESIS_ROLE_ARN,
                            "StreamARN": log_destination
                        }
                    }
                ],
                "Fields": [
                    "timestamp", "c-ip", "sc-status", "sc-bytes",
                    "cs-method", "cs-uri-stem", "time-taken"
                ],
                "Name": f"{distribution.name}-realtime-logs",
                "SamplingRate": 100
            }
            
            response = await self.cloudfront_client.create_realtime_log_config(
                RealtimeLogConfig=config
            )
            
            distribution.realtime_logs_enabled = True
            distribution.realtime_logs_config = response["RealtimeLogConfig"]["ARN"]
        
        await self._save_distribution(distribution)
        
        logger.info(
            "Real-time logs enabled",
            distribution_id=distribution_id,
            destination=log_destination
        )
    
    async def _monitor_cdn_health(self):
        """Monitor CDN health and performance"""
        while True:
            try:
                for distribution_id, distribution in self.distributions.items():
                    if not distribution.enabled:
                        continue
                    
                    # Check distribution status
                    provider = self.providers.get(distribution.provider_id)
                    if provider and provider.provider_type == CDNProviderType.CLOUDFRONT:
                        response = await self.cloudfront_client.get_distribution(
                            Id=distribution.provider_distribution_id
                        )
                        distribution.status = response["Distribution"]["Status"].lower()
                    
                    # Update metrics
                    self.metrics.gauge(
                        f"cdn.distribution.{distribution_id}.status",
                        1 if distribution.status == "deployed" else 0
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"CDN health monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _save_distribution(self, distribution: CDNDistribution):
        """Save distribution configuration to Redis"""
        key = f"cdn:distribution:{distribution.distribution_id}"
        await self.redis_client.set(
            key,
            distribution.json(),
            ex=86400  # 24 hour expiry
        )
    
    async def _load_distributions(self):
        """Load distributions from Redis"""
        pattern = "cdn:distribution:*"
        cursor = 0
        
        while True:
            cursor, keys = await self.redis_client.scan(
                cursor, match=pattern, count=100
            )
            
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    distribution = CDNDistribution.parse_raw(data)
                    self.distributions[distribution.distribution_id] = distribution
            
            if cursor == 0:
                break
    
    async def _track_purge_request(self, purge_request: PurgeRequest):
        """Track purge request in Redis"""
        key = f"cdn:purge:{purge_request.request_id}"
        await self.redis_client.set(
            key,
            purge_request.json(),
            ex=3600  # 1 hour expiry
        )
    
    async def _track_prefetch_request(self, prefetch_request: PrefetchRequest):
        """Track prefetch request in Redis"""
        key = f"cdn:prefetch:{prefetch_request.request_id}"
        await self.redis_client.set(
            key,
            prefetch_request.json(),
            ex=3600  # 1 hour expiry
        )
    
    async def _save_optimization(self, optimization: ContentOptimization):
        """Save optimization configuration"""
        key = f"cdn:optimization:{optimization.optimization_id}"
        await self.redis_client.set(
            key,
            optimization.json(),
            ex=86400  # 24 hour expiry
        )
    
    async def shutdown(self):
        """Shutdown CDN manager"""
        logger.info("Shutting down CDN manager")
        
        if self._monitor_task:
            self._monitor_task.cancel()
        
        if self.http_session:
            await self.http_session.close()
        
        if self.cloudfront_client:
            await self.cloudfront_client.__aexit__(None, None, None)
        
        if self.redis_client:
            await self.redis_client.close()
        
        self._initialized = False