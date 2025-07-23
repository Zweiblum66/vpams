# WAF Protection Service

Comprehensive Web Application Firewall (WAF) protection service for the MAMS platform. Provides real-time threat detection, blocking, and comprehensive security rule management to protect against web-based attacks.

## Features

### Core Protection Modules
- **SQL Injection Protection**: Advanced pattern matching with configurable sensitivity levels
- **Cross-Site Scripting (XSS) Protection**: HTML/JavaScript injection detection with encoding awareness
- **Bot Detection**: User-agent analysis, behavioral detection, and automated traffic identification
- **Rate Limiting**: Configurable request rate limits with Redis-backed tracking
- **Geographic Blocking**: Country-based IP filtering with GeoIP database integration
- **IP Filtering**: Whitelist and blacklist management with CIDR support

### Advanced Features
- **Custom Rules Engine**: Flexible rule creation with multiple condition types and operators
- **Real-time Analysis**: Sub-millisecond threat detection and decision making
- **Multiple Operation Modes**: Blocking, monitoring, and disabled modes
- **Threat Intelligence**: Scoring system with configurable thresholds
- **Suspicious Activity Tracking**: Pattern analysis and escalation detection
- **Comprehensive Logging**: Detailed audit trails and forensic capabilities

### Rule Engine Capabilities
- ✅ **Custom Rule Creation**: Define rules with multiple conditions and actions
- ✅ **Flexible Targeting**: URL, headers, body, IP, user-agent, query string, cookies
- ✅ **Rich Operators**: Regex, contains, equals, length checks, IP ranges, lists
- ✅ **Priority-based Execution**: Rules processed in configurable priority order
- ✅ **Dynamic Rule Management**: Add, update, disable rules without service restart
- ✅ **Rule Testing**: Test rules against sample requests before deployment
- ✅ **Bulk Operations**: Enable, disable, or delete multiple rules at once

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Docker and Docker Compose (optional)

### Installation

1. **Clone and Setup**
```bash
cd services/waf-protection
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run with Docker**
```bash
docker-compose up -d
```

4. **Manual Setup**
```bash
# Initialize database
python -c "from src.services.database import create_tables; import asyncio; asyncio.run(create_tables())"

# Start service
uvicorn src.main:app --host 0.0.0.0 --port 8022 --reload
```

### API Documentation
- OpenAPI docs: `http://localhost:8022/docs`
- ReDoc: `http://localhost:8022/redoc`

## Usage Examples

### Request Analysis

```bash
# Analyze a request for threats
curl -X POST "http://localhost:8022/api/v1/waf/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "method": "GET",
    "url": "/search?q=test",
    "headers": {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Host": "example.com"
    },
    "body": null
  }'
```

**Response:**
```json
{
  "allowed": true,
  "rule_triggered": null,
  "threat_level": "low",
  "block_reason": null,
  "score": 15,
  "metadata": {
    "country_code": "US",
    "is_bot": false,
    "remaining": 55
  },
  "processing_time_ms": 2.3
}
```

### Malicious Request Detection

```bash
# Test SQL injection detection
curl -X POST "http://localhost:8022/api/v1/waf/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "method": "GET",
    "url": "/search?q=' OR 1=1 --",
    "headers": {
      "User-Agent": "sqlmap/1.4.9"
    }
  }'
```

**Response:**
```json
{
  "allowed": false,
  "rule_triggered": "SQL_INJECTION_BASIC",
  "threat_level": "high",
  "block_reason": "SQL injection attempt detected",
  "score": 90,
  "metadata": {
    "sql_patterns": ["(\b(or)\b|'.*'.*=.*'.*')"],
    "is_bot": true,
    "bot_type": "known_bot"
  },
  "processing_time_ms": 1.8
}
```

### Custom Rule Management

#### Create Custom Rule

```bash
curl -X POST "http://localhost:8022/api/v1/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ADMIN_PATH_PROTECTION",
    "name": "Admin Path Protection",
    "description": "Block unauthorized access to admin paths",
    "enabled": true,
    "action": "block",
    "priority": 10,
    "threat_level": "high",
    "score": 80,
    "tags": ["admin", "access_control"],
    "conditions": [
      {
        "target": "url",
        "operator": "regex",
        "value": "/(admin|administrator|wp-admin|cpanel)",
        "case_sensitive": false
      },
      {
        "target": "header",
        "operator": "not_contains",
        "value": "AdminToken",
        "header_name": "Authorization"
      }
    ]
  }'
```

#### Test Rule

```bash
curl -X POST "http://localhost:8022/api/v1/rules/test" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "ADMIN_PATH_PROTECTION",
    "test_request": {
      "ip": "192.168.1.100",
      "method": "GET",
      "url": "/admin/users",
      "headers": {
        "User-Agent": "Mozilla/5.0"
      }
    }
  }'
```

### Configuration Management

#### Update Geographic Blocking

```bash
curl -X PUT "http://localhost:8022/api/v1/config/geo-blocking" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "blocked_countries": ["CN", "RU", "KP"],
    "allowed_countries": []
  }'
```

#### Get WAF Status

```bash
curl "http://localhost:8022/api/v1/waf/status"
```

### Statistics and Monitoring

#### Get WAF Statistics

```bash
curl "http://localhost:8022/api/v1/stats/waf"
```

**Response:**
```json
{
  "requests_processed": 15420,
  "requests_blocked": 328,
  "block_rate": 2.13,
  "sql_injection_attempts": 45,
  "xss_attempts": 23,
  "bot_requests": 156,
  "rate_limited": 89,
  "geo_blocked": 15,
  "top_blocked_ips": [
    {"ip": "192.168.1.100", "count": 12, "last_blocked": "2024-01-15T10:30:00Z"},
    {"ip": "10.0.0.50", "count": 8, "last_blocked": "2024-01-15T10:25:00Z"}
  ],
  "top_triggered_rules": [
    {"rule": "SQL_INJECTION_BASIC", "count": 45, "last_triggered": "2024-01-15T10:30:00Z"},
    {"rule": "BOT_DETECTION", "count": 32, "last_triggered": "2024-01-15T10:28:00Z"}
  ]
}
```

#### Get Blocked Requests

```bash
curl "http://localhost:8022/api/v1/stats/blocked-requests?page=1&limit=10"
```

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=waf-protection
SERVICE_PORT=8022
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/mams_waf

# Redis
REDIS_URL=redis://localhost:6379/4

# WAF Core Settings
WAF_ENABLED=true
WAF_MODE=blocking  # blocking, monitoring, off

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_RPM=60
RATE_LIMIT_BURST=10

# IP Filtering
IP_WHITELIST=["192.168.1.0/24", "10.0.0.0/8"]
IP_BLACKLIST=["192.168.100.0/24"]

# Geographic Blocking
GEO_BLOCKING_ENABLED=true
BLOCKED_COUNTRIES=["CN", "RU"]
ALLOWED_COUNTRIES=[]
GEOIP_DATABASE_PATH=/app/data/GeoLite2-Country.mmdb

# Protection Modules
SQL_INJECTION_PROTECTION=true
SQL_INJECTION_SENSITIVITY=medium  # low, medium, high
XSS_PROTECTION=true
XSS_SENSITIVITY=medium
BOT_PROTECTION_ENABLED=true
BOT_DETECTION_SENSITIVITY=medium

# Request Limits
MAX_REQUEST_SIZE=104857600  # 100MB
MAX_HEADER_SIZE=8192
MAX_URL_LENGTH=4096

# File Upload Protection
ALLOWED_FILE_EXTENSIONS=[".jpg", ".jpeg", ".png", ".mp4", ".pdf"]
BLOCKED_FILE_EXTENSIONS=[".exe", ".bat", ".js"]
MAX_FILE_SIZE=524288000  # 500MB

# DDoS Protection
DDOS_PROTECTION_ENABLED=true
DDOS_THRESHOLD_PER_MINUTE=300
DDOS_BLOCK_DURATION=300

# Alerting
ALERT_WEBHOOK_URL=https://hooks.slack.com/your-webhook
ALERT_EMAIL=security@yourdomain.com
ALERT_THRESHOLD=10

# Custom Rules
CUSTOM_RULES_ENABLED=true
CUSTOM_RULES_FILE=/app/config/custom_rules.yaml
```

### Operation Modes

#### Blocking Mode (Default)
- Actively blocks malicious requests
- Returns HTTP 403 for blocked requests
- Logs all activities

#### Monitoring Mode
- Detects and logs threats
- Allows all requests through
- Useful for testing and tuning

#### Disabled Mode
- WAF completely disabled
- All requests allowed
- Minimal processing overhead

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  WAF Protection  │────│    Database     │
│                 │    │     Service      │    │   PostgreSQL    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌────────▼────────┐
                       │   WAF Engine    │
                       │                 │
                       └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Protection  │    │   Rule Engine    │    │    External      │
│   Modules    │    │                  │    │   Integrations   │
│              │    │                  │    │                  │
│ • SQL Injection │  │ • Custom Rules   │    │ • GeoIP Database │
│ • XSS Detection │  │ • Conditions     │    │ • Redis Cache    │
│ • Bot Detection │  │ • Actions        │    │ • Alert Webhooks │
│ • Rate Limiting │  │ • Priorities     │    │ • SIEM Systems   │
│ • Geo Blocking  │  │ • Testing        │    │ • Monitoring     │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

### Request Processing Flow

1. **Request Ingestion**: Receive and parse HTTP request
2. **IP Validation**: Check whitelist/blacklist and geographic restrictions
3. **Rate Limiting**: Verify request rate limits
4. **Content Analysis**: Run protection modules (SQL injection, XSS, etc.)
5. **Custom Rules**: Evaluate against user-defined rules
6. **Decision Engine**: Calculate threat score and determine action
7. **Response**: Allow/block request and log results
8. **Analytics**: Update statistics and trigger alerts if needed

### Database Schema

```sql
-- Core rule management
custom_rules (id, name, description, enabled, action, conditions, priority, ...)
blocked_requests (id, ip, method, url, rule_triggered, threat_level, ...)
waf_metrics (id, metric_name, metric_value, ip, timestamp, ...)

-- IP management
ip_whitelist (id, ip_range, description, enabled, hit_count, ...)
ip_blacklist (id, ip_range, description, enabled, expires_at, ...)

-- Configuration and alerting
waf_config (id, config_key, config_value, description, ...)
alert_rules (id, name, condition_metric, webhook_url, ...)
suspicious_activity (id, ip, activity_type, severity, pattern_data, ...)
```

## Protection Modules

### SQL Injection Detection

**Patterns Detected:**
- Union-based injection: `UNION SELECT`
- Boolean-based: `OR 1=1`, `AND 1=1`
- Time-based: `WAITFOR DELAY`, `SLEEP()`
- Error-based: `extractvalue()`, `updatexml()`
- Stacked queries: `;DROP TABLE`

**Sensitivity Levels:**
- **Low**: Basic patterns only
- **Medium**: Additional evasion techniques
- **High**: Aggressive detection including borderline cases

### XSS Protection

**Attack Vectors:**
- Script tags: `<script>`, `<iframe>`
- Event handlers: `onload`, `onerror`, `onclick`
- JavaScript URIs: `javascript:`, `vbscript:`
- Data URIs: `data:text/html`
- CSS expressions: `expression()`

**Encoding Awareness:**
- URL encoding: `%3Cscript%3E`
- HTML entities: `&lt;script&gt;`
- Double encoding evasion

### Bot Detection

**Detection Methods:**
- User-agent analysis
- Behavioral patterns
- Request frequency
- Header fingerprinting
- JavaScript challenges (future)

**Bot Categories:**
- Search engines (allowed)
- Security scanners (blocked)
- Scrapers (rate limited)
- Unknown bots (challenged)

### Rate Limiting

**Features:**
- Per-IP rate limiting
- Burst allowance
- Sliding window
- Redis-backed storage
- Custom rate limits per rule

**Algorithms:**
- Token bucket
- Sliding window counter
- Fixed window counter

## Custom Rules

### Rule Structure

```yaml
rules:
  - id: "CUSTOM_RULE_001"
    name: "Admin Path Protection"
    description: "Protect admin areas from unauthorized access"
    enabled: true
    action: "block"
    priority: 10
    threat_level: "high"
    score: 85
    tags: ["admin", "access_control"]
    conditions:
      - target: "url"
        operator: "regex"
        value: "/(admin|wp-admin|administrator)"
        case_sensitive: false
      - target: "header"
        operator: "not_contains"
        value: "Bearer "
        header_name: "Authorization"
```

### Condition Targets
- **url**: Request URL path and query string
- **header**: HTTP headers (specify header_name)
- **body**: Request body content
- **ip**: Client IP address
- **user_agent**: User-Agent header
- **method**: HTTP method (GET, POST, etc.)
- **query_string**: URL query parameters only
- **cookie**: Cookie values (specify cookie name)

### Operators
- **eq/ne**: Equals/not equals
- **contains/not_contains**: String contains
- **starts_with/ends_with**: String prefix/suffix
- **regex**: Regular expression matching
- **length_gt/length_lt**: Length comparisons
- **in_list/not_in_list**: List membership
- **ip_in_range**: IP/CIDR range matching
- **gt/lt**: Numeric comparisons

### Actions
- **allow**: Explicitly allow request
- **block**: Block request with 403
- **log**: Log but allow request
- **rate_limit**: Apply rate limiting
- **challenge**: Present challenge (future)

## API Reference

### WAF Analysis

#### POST /api/v1/waf/analyze
Analyze a request for threats

**Request:**
```json
{
  "ip": "192.168.1.100",
  "method": "GET",
  "url": "/search?q=test",
  "headers": {
    "User-Agent": "Mozilla/5.0",
    "Host": "example.com"
  },
  "body": null,
  "user_agent": "Mozilla/5.0",
  "referer": "https://example.com"
}
```

**Response:**
```json
{
  "allowed": true,
  "rule_triggered": null,
  "threat_level": "low",
  "block_reason": null,
  "score": 15,
  "metadata": {
    "country_code": "US",
    "is_bot": false
  },
  "processing_time_ms": 2.3
}
```

### Rule Management

#### POST /api/v1/rules
Create new custom rule

#### GET /api/v1/rules/{rule_id}
Get specific rule

#### PUT /api/v1/rules/{rule_id}
Update existing rule

#### DELETE /api/v1/rules/{rule_id}
Delete rule

#### GET /api/v1/rules
List rules with pagination

### Configuration

#### GET /api/v1/config
Get WAF configuration

#### PUT /api/v1/config/geo-blocking
Update geographic blocking settings

### Statistics

#### GET /api/v1/stats/waf
Get WAF statistics

#### GET /api/v1/stats/blocked-requests
Get blocked requests log

### Health Check

#### GET /health
Service health check

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_waf_engine.py -v
pytest tests/test_rule_engine.py -v
```

### Test Categories

#### Unit Tests
- WAF engine components
- Rule engine functionality
- Protection modules
- Database operations

#### Integration Tests
- API endpoints
- Database interactions
- Redis operations
- End-to-end workflows

#### Performance Tests
- Concurrent request handling
- Large rule set evaluation
- Memory usage under load
- Response time benchmarks

## Deployment

### Docker Deployment

```yaml
version: '3.8'
services:
  waf-protection:
    build: .
    ports:
      - "8022:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/mams_waf
      - REDIS_URL=redis://redis:6379/4
      - WAF_ENABLED=true
      - WAF_MODE=blocking
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data  # For GeoIP database
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: waf-protection
spec:
  replicas: 3
  selector:
    matchLabels:
      app: waf-protection
  template:
    metadata:
      labels:
        app: waf-protection
    spec:
      containers:
      - name: waf-protection
        image: mams/waf-protection:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: waf-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Load Balancing

WAF Protection Service is stateless and can be horizontally scaled. Use a load balancer to distribute requests across multiple instances.

**Nginx Configuration:**
```nginx
upstream waf_backend {
    server waf-1:8000;
    server waf-2:8000;
    server waf-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://waf_backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring

### Metrics Collection

The service exposes Prometheus metrics:

```
# Request metrics
waf_requests_total{status="allowed|blocked"}
waf_request_duration_seconds
waf_threats_detected_total{type="sql_injection|xss|bot"}

# Rule metrics
waf_rules_total{enabled="true|false"}
waf_rule_matches_total{rule_id="..."}

# System metrics
waf_active_connections
waf_memory_usage_bytes
```

### Alerting

Configure alerts for critical security events:

```yaml
# Prometheus alert rules
groups:
  - name: waf_alerts
    rules:
      - alert: HighThreatActivity
        expr: rate(waf_threats_detected_total[5m]) > 10
        for: 2m
        annotations:
          summary: "High threat activity detected"
      
      - alert: WAFServiceDown
        expr: up{job="waf-protection"} == 0
        for: 1m
        annotations:
          summary: "WAF Protection Service is down"
```

### Logging

Structured logging with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "WARN",
  "logger": "waf.engine",
  "message": "Request blocked",
  "ip": "192.168.1.100",
  "rule": "SQL_INJECTION_BASIC",
  "threat_level": "high",
  "score": 90,
  "request_id": "req_abc123"
}
```

## Security Considerations

### Service Security
- Input validation on all API endpoints
- Rate limiting on administrative endpoints
- Authentication for configuration changes
- Secure configuration management
- Regular security updates

### Data Protection
- Hash sensitive request bodies
- Encrypt configuration at rest
- Secure transmission of logs
- Data retention policies
- Access logging and monitoring

### Performance Impact
- Minimal latency overhead (< 5ms typical)
- Efficient pattern matching algorithms
- Redis caching for performance
- Configurable processing limits
- Graceful degradation under load

## Troubleshooting

### Common Issues

#### High False Positive Rate
```bash
# Check rule sensitivity
curl "http://localhost:8022/api/v1/rules?threat_level=high"

# Adjust rule thresholds
curl -X PUT "http://localhost:8022/api/v1/rules/RULE_ID" \
  -d '{"score": 60}'  # Lower score

# Switch to monitoring mode temporarily
export WAF_MODE=monitoring
```

#### Performance Issues
```bash
# Check active connections
curl "http://localhost:8022/health"

# Monitor request processing time
curl "http://localhost:8022/api/v1/stats/waf" | jq '.processing_time_avg'

# Review enabled rules
curl "http://localhost:8022/api/v1/rules?enabled=true"
```

#### Database Connection Issues
```bash
# Verify database connectivity
psql -h localhost -U postgres -d mams_waf

# Check connection pool
docker-compose logs waf-protection | grep "database"
```

### Debugging

Enable debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

View detailed request analysis:
```bash
curl -X POST "http://localhost:8022/api/v1/waf/analyze" \
  -H "X-Debug: true" \
  -d '{"ip": "...", "method": "...", ...}'
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add comprehensive tests
4. Ensure all tests pass
5. Submit pull request

## License

This service is part of the MAMS platform and follows the project's licensing terms.