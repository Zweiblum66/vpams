# API Gateway Rate Limiting Guide

## Overview

The MAMS API Gateway implements sophisticated rate limiting to ensure fair usage, prevent abuse, and maintain service stability. The system supports multiple rate limiting strategies, user tiers, and granular control over API endpoints.

## Rate Limiting Strategies

### 1. Sliding Window (Default)

The sliding window algorithm provides smooth rate limiting by tracking requests in a moving time window.

**Advantages:**
- No sudden resets
- Fair distribution of requests
- Accurate request counting

**How it works:**
```
Time: [------|------|------|------|------]
         ^                          ^
         60s ago                    now
         
Requests older than 60s are removed
New requests are added if under limit
```

### 2. Fixed Window

Fixed window divides time into discrete windows and resets counters at window boundaries.

**Advantages:**
- Simple and predictable
- Lower memory usage
- Clear reset times

**Use cases:**
- Daily/hourly quotas
- Billing period limits

### 3. Token Bucket

Token bucket allows burst traffic while maintaining long-term rate limits.

**Advantages:**
- Handles burst traffic
- Smooth traffic shaping
- Configurable refill rate

**Use cases:**
- Upload endpoints
- API calls with varying costs

## Rate Limit Rules

### Authentication Endpoints

| Endpoint | Limit | Window | Strategy |
|----------|-------|--------|----------|
| `/auth/login` | 5 | 1 minute | Sliding Window |
| `/auth/register` | 3 | 5 minutes | Fixed Window |
| `/auth/password-reset` | 3 | 1 hour | Fixed Window |

### API Endpoints

| Method | Type | Limit (Free) | Window | Strategy |
|--------|------|--------------|--------|----------|
| GET | Read | 1000 | 1 minute | Sliding Window |
| POST/PUT | Write | 100 | 1 minute | Token Bucket |
| POST | Upload | 10 | 5 minutes | Token Bucket |
| DELETE | Delete | 50 | 1 minute | Token Bucket |

### User Tiers

Different user tiers have different rate limit multipliers:

| Tier | Multiplier | Example (Read Limit) |
|------|------------|---------------------|
| Free | 1x | 1000/min |
| Basic | 2x | 2000/min |
| Premium | 5x | 5000/min |
| Enterprise | 10x | 10000/min |
| Unlimited | 1000x | 1000000/min |

## Rate Limit Headers

All API responses include rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
```

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
Retry-After: 45

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 45 seconds",
    "details": {
      "limit": 1000,
      "window": 60,
      "remaining": 0,
      "retry_after": 45
    }
  }
}
```

## Rate Limit Management API

### Check Your Rate Limits

```http
GET /api/v1/rate-limits/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "identifier": "user123",
  "limits": {
    "/api/v1/assets": {
      "endpoint": "/api/v1/assets",
      "limit": 5000,
      "window": 60,
      "remaining": 4823,
      "reset": 1640995200,
      "strategy": "sliding_window"
    }
  },
  "current_usage": {
    "rate_limit:sliding:user123": 177
  }
}
```

### Admin: Check User Rate Limits

```http
GET /api/v1/rate-limits/user/{user_id}
Authorization: Bearer <admin_token>
```

### Admin: Override Rate Limits

```http
POST /api/v1/rate-limits/override
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "identifier": "user123",
  "endpoint": "/api/v1/assets",
  "limit": 10000,
  "window": 60,
  "duration": 3600
}
```

### Admin: Reset Rate Limit Counters

```http
POST /api/v1/rate-limits/reset/{identifier}?endpoint=/api/v1/assets
Authorization: Bearer <admin_token>
```

## Implementation Details

### Redis Storage

Rate limit data is stored in Redis using different patterns:

```
# Sliding window
rate_limit:sliding:{identifier} -> Sorted Set
  - Score: timestamp
  - Member: unique request ID

# Fixed window  
rate_limit:fixed:{identifier}:{window_id} -> String (counter)

# Token bucket
rate_limit:bucket:{identifier} -> JSON
  {
    "tokens": 45.5,
    "last_update": 1640995200
  }
```

### IP-Based Limiting

For unauthenticated requests, IP addresses are used with stricter limits:

- IPs are hashed for privacy (SHA256, truncated to 16 chars)
- Default limit: 50 requests/minute
- Applies in addition to user limits

### Cost-Based Limiting

Some operations consume more than one request:

```python
# Regular API call
cost = 1

# Large file upload
cost = 10

# Batch operation
cost = items_count

result = await rate_limiter.check_rate_limit(
    identifier=user_id,
    limit=1000,
    window=60,
    cost=cost
)
```

## Best Practices

### For API Consumers

1. **Handle 429 Responses**
   ```python
   async def make_request_with_retry(url):
       response = await client.get(url)
       
       if response.status_code == 429:
           retry_after = int(response.headers.get('Retry-After', 60))
           await asyncio.sleep(retry_after)
           return await make_request_with_retry(url)
       
       return response
   ```

2. **Monitor Rate Limit Headers**
   ```python
   remaining = int(response.headers['X-RateLimit-Remaining'])
   if remaining < 100:
       # Slow down requests
       await asyncio.sleep(0.1)
   ```

3. **Use Exponential Backoff**
   ```python
   async def exponential_backoff(attempt):
       delay = min(300, (2 ** attempt) + random.uniform(0, 1))
       await asyncio.sleep(delay)
   ```

### For Administrators

1. **Monitor Rate Limit Metrics**
   - Track 429 response rates
   - Identify users hitting limits
   - Adjust limits based on usage patterns

2. **Set Appropriate Limits**
   - Start conservative, increase as needed
   - Consider peak vs average usage
   - Different limits for different operations

3. **Use Overrides Sparingly**
   - Temporary increases for migrations
   - Special events or promotions
   - Always set expiration

## Configuration

### Environment Variables

```env
# Default rate limits
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_BURST=20

# Redis configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=20
```

### Custom Rules

Edit `rate_limiter.py` to add custom rules:

```python
"custom_endpoint": {
    "limit": 50,
    "window": 300,
    "strategy": RateLimitStrategy.TOKEN_BUCKET,
    "cost_multiplier": 2
}
```

## Troubleshooting

### Common Issues

1. **"Rate limit exceeded" immediately**
   - Check if old requests are being cleaned up
   - Verify Redis connectivity
   - Check for duplicate request IDs

2. **Limits not applying correctly**
   - Verify user tier is set correctly
   - Check endpoint matching rules
   - Ensure Redis keys aren't expiring early

3. **Performance issues**
   - Use sliding window for high-traffic endpoints
   - Implement local caching for tier lookups
   - Consider Redis cluster for scale

### Debug Commands

```bash
# Check Redis keys for a user
redis-cli keys "rate_limit:*:user123*"

# Get current request count
redis-cli zcard "rate_limit:sliding:user123"

# Check token bucket state
redis-cli get "rate_limit:bucket:user123"

# Monitor rate limit operations
redis-cli monitor | grep rate_limit
```

## Advanced Features

### Distributed Rate Limiting

The system works across multiple API Gateway instances:
- Shared Redis backend
- Atomic operations
- Consistent counting

### Hierarchical Limits

Apply limits at multiple levels:
1. Global (all users)
2. User tier
3. Individual user
4. Specific endpoint
5. IP address

### Dynamic Adjustments

Rate limits can be adjusted in real-time:
- No restart required
- Immediate effect
- Temporary overrides

### Cost-Based Operations

Different operations can have different costs:
- Simple read: 1 point
- Complex search: 5 points  
- File upload: 10 points
- Batch operation: N points

## Security Considerations

1. **Prevent Bypass Attempts**
   - Validate all identifiers
   - Hash sensitive data (IPs)
   - Rate limit by multiple factors

2. **DDoS Protection**
   - IP-based limits as first defense
   - Aggressive limits for auth endpoints
   - Circuit breakers for backend protection

3. **Privacy**
   - IPs are hashed
   - Minimal data retention
   - No PII in Redis keys

## Monitoring and Alerts

Set up monitoring for:
- 429 response rate > 1%
- Individual users hitting limits frequently
- Sudden spike in requests
- Redis memory usage
- Rate limit override usage

Example Prometheus metrics:
```
rate_limit_requests_total{endpoint="/api/v1/assets",status="allowed"} 
rate_limit_requests_total{endpoint="/api/v1/assets",status="denied"}
rate_limit_remaining{user_tier="premium",endpoint="/api/v1/assets"}
```