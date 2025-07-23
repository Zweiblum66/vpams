# CDN Service

Global Content Delivery Network (CDN) management service for MAMS platform.

## Overview

The CDN service provides comprehensive content delivery management with multi-provider support, intelligent caching, and global distribution capabilities.

## Features

### Multi-Provider Support
- **AWS CloudFront**: Full integration with CloudFront distributions
- **Cloudflare**: Page rules and caching configuration
- **Akamai**: Enterprise CDN capabilities
- **Fastly**: Real-time CDN configuration
- **Azure CDN**: Microsoft Azure integration

### Core Capabilities
- **Distribution Management**: Create, update, and delete CDN distributions
- **Cache Control**: Intelligent cache key generation and TTL management
- **Content Purging**: Selective cache invalidation by path or tag
- **Content Prefetching**: Warm edge caches proactively
- **Real-time Metrics**: Performance and usage analytics
- **Security**: WAF, geo-restriction, and signed URLs

### Content Optimization
- **Image Optimization**: Auto WebP/AVIF conversion, responsive sizing
- **Video Optimization**: Adaptive bitrate, transcoding
- **Compression**: Gzip/Brotli compression
- **Minification**: CSS/JS minification

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Gateway   │────▶│   CDN Service   │────▶│ CDN Providers   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ├── CloudFront
                               ├── Cloudflare
                               ├── Akamai
                               ├── Fastly
                               └── Azure CDN
```

## API Endpoints

### Provider Management
- `GET /api/v1/cdn/providers` - List available CDN providers
- `GET /api/v1/cdn/providers/{provider_id}` - Get provider details

### Distribution Management
- `GET /api/v1/cdn/distributions` - List distributions
- `POST /api/v1/cdn/distributions` - Create distribution
- `GET /api/v1/cdn/distributions/{id}` - Get distribution
- `PUT /api/v1/cdn/distributions/{id}` - Update distribution
- `DELETE /api/v1/cdn/distributions/{id}` - Delete distribution

### Cache Operations
- `POST /api/v1/cdn/distributions/{id}/purge` - Purge cache
- `POST /api/v1/cdn/distributions/{id}/prefetch` - Prefetch content

### Metrics & Analytics
- `GET /api/v1/cdn/distributions/{id}/metrics` - Get metrics
- `GET /api/v1/cdn/distributions/{id}/bandwidth` - Get bandwidth usage
- `GET /api/v1/cdn/distributions/{id}/cache-status` - Get cache status
- `GET /api/v1/cdn/distributions/{id}/cost-estimate` - Get cost estimate

### Optimization
- `POST /api/v1/cdn/distributions/{id}/optimize` - Configure optimization
- `POST /api/v1/cdn/optimize/image-settings` - Image optimization settings
- `POST /api/v1/cdn/optimize/video-settings` - Video optimization settings

### Configuration
- `POST /api/v1/cdn/distributions/{id}/headers` - Configure headers
- `POST /api/v1/cdn/distributions/{id}/logs/realtime` - Enable real-time logs

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=cdn
SERVICE_PORT=8016
ENVIRONMENT=development

# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mams_cdn

# AWS CloudFront
ENABLE_CLOUDFRONT=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
CLOUDFRONT_DISTRIBUTION_ID=E123456789
ACM_CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789:certificate/abc

# Cloudflare
ENABLE_CLOUDFLARE=false
CLOUDFLARE_ZONE_ID=your-zone-id
CLOUDFLARE_API_TOKEN=your-api-token

# Cache Settings
DEFAULT_CACHE_TTL=86400
CACHE_STATIC_CONTENT=true
CACHE_DYNAMIC_CONTENT=false

# Optimization
ENABLE_IMAGE_OPTIMIZATION=true
ENABLE_VIDEO_OPTIMIZATION=true
IMAGE_QUALITY=85
VIDEO_ADAPTIVE_BITRATE=true

# Security
ENABLE_WAF=true
ENABLE_DDOS_PROTECTION=true
ENABLE_HOTLINK_PROTECTION=true
```

## Usage Examples

### Create a Distribution

```python
import httpx

# Create CloudFront distribution
response = httpx.post(
    "http://localhost:8016/api/v1/cdn/distributions",
    json={
        "name": "media-distribution",
        "provider_id": "cloudfront",
        "origins": [{
            "origin_id": "s3-origin",
            "domain_name": "media.s3.amazonaws.com",
            "origin_path": "/production"
        }],
        "cache_rules": [{
            "path_pattern": "*.mp4",
            "cache_enabled": True,
            "default_ttl": 86400,
            "compress": True
        }],
        "custom_domain": "cdn.example.com"
    },
    headers={"Authorization": "Bearer token"}
)
```

### Purge Cache

```python
# Purge specific paths
response = httpx.post(
    "http://localhost:8016/api/v1/cdn/distributions/dist-123/purge",
    json={
        "paths": ["/videos/*", "/images/logos/*"],
        "tags": ["homepage", "featured"]
    },
    headers={"Authorization": "Bearer token"}
)
```

### Configure Image Optimization

```python
# Enable image optimization
response = httpx.post(
    "http://localhost:8016/api/v1/cdn/distributions/dist-123/optimize",
    json={
        "optimization_type": "image_optimization",
        "settings": {
            "auto_webp": True,
            "quality": 85,
            "responsive_sizes": [320, 640, 1024, 1920],
            "lazy_loading": True
        }
    },
    headers={"Authorization": "Bearer token"}
)
```

## Cache Key Generation

The service uses intelligent cache key generation:

```python
from src.utils.cache import CacheKeyGenerator

generator = CacheKeyGenerator()

# Basic cache key
key = generator.generate_cache_key("https://cdn.example.com/video.mp4")

# With query parameters
key = generator.generate_cache_key(
    "https://cdn.example.com/api/data?id=123&format=json",
    query_string_behavior="whitelist",
    query_string_keys=["id", "format"]
)

# With headers
key = generator.generate_cache_key(
    "https://cdn.example.com/api/data",
    headers={"Accept": "application/json"},
    headers_behavior="whitelist",
    headers_whitelist=["Accept"]
)
```

## Security Features

### Signed URLs
Generate time-limited, IP-restricted URLs:

```python
from src.core.security import generate_signed_url

signed_url = generate_signed_url(
    base_url="https://cdn.example.com",
    path="/premium/video.mp4",
    expires_in=3600,  # 1 hour
    allowed_ips=["192.168.1.0/24"]
)
```

### Geo-Restriction
Configure geographic access control:

```json
{
    "security_policy": {
        "geo_restriction": {
            "restriction_type": "whitelist",
            "locations": ["US", "CA", "GB", "DE"]
        }
    }
}
```

## Performance Monitoring

### Real-time Metrics
- Request count and cache hit rate
- Bandwidth usage by content type
- Error rates and response times
- Geographic distribution of requests

### Cost Tracking
- Data transfer costs by region
- Request costs by distribution
- Invalidation request tracking
- Optimization savings

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
python -m src.main
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_cdn_manager.py -v
```

### Docker

```bash
# Build image
docker build -t mams-cdn-service .

# Run container
docker run -p 8016:8016 --env-file .env mams-cdn-service
```

## Integration

### With Storage Service
The CDN service integrates with the storage service for origin configuration:

```python
# Configure S3 origin
origin = CDNOrigin(
    origin_id="s3-media",
    domain_name="mams-media.s3.amazonaws.com",
    origin_path="/production",
    custom_headers={"x-origin-verify": "secret"}
)
```

### With Asset Management
Automatic CDN URL generation for assets:

```python
# Asset with CDN URL
asset.cdn_url = f"https://{distribution.domain_name}/assets/{asset.id}/file.mp4"
```

## Troubleshooting

### Common Issues

1. **Distribution stuck in "deploying"**
   - Check provider credentials
   - Verify origin accessibility
   - Review CloudFormation events (for CloudFront)

2. **High origin load**
   - Increase cache TTLs
   - Enable origin shield
   - Implement cache warming

3. **Purge not working**
   - Verify purge permissions
   - Check path format (must start with /)
   - Monitor purge request status

## Best Practices

1. **Cache Strategy**
   - Use appropriate TTLs for content types
   - Implement cache tags for granular purging
   - Monitor cache hit rates

2. **Security**
   - Enable WAF for public distributions
   - Use signed URLs for premium content
   - Implement geo-restrictions where needed

3. **Performance**
   - Enable compression for text content
   - Use image optimization for photos
   - Implement prefetching for predicted content

4. **Cost Optimization**
   - Monitor bandwidth usage
   - Use appropriate price classes
   - Implement smart caching strategies