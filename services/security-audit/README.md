# Security Audit Service

Comprehensive security auditing and compliance checking service for the MAMS platform. Provides automated security scanning, vulnerability assessment, and compliance verification across multiple standards.

## Features

### Security Scanning
- **Code Analysis**: Static code analysis using Bandit and Semgrep
- **Dependency Scanning**: Vulnerability detection in dependencies using Safety and pip-audit
- **Web Application Scanning**: OWASP ZAP integration for web vulnerability assessment
- **Network Scanning**: Network security assessment capabilities

### Compliance Checking
- **ISO 27001**: Information Security Management compliance
- **GDPR**: General Data Protection Regulation compliance
- **SOC 2 Type II**: Service Organization Control 2 compliance
- **PCI DSS**: Payment Card Industry Data Security Standard (optional)

### Key Capabilities
- ✅ **Automated Scanning**: Schedule and run comprehensive security audits
- ✅ **Multi-Standard Compliance**: Support for major security and privacy standards
- ✅ **Real-time Monitoring**: Continuous security monitoring and alerting
- ✅ **Detailed Reporting**: Comprehensive reports with actionable recommendations
- ✅ **API Integration**: RESTful API for integration with other services
- ✅ **Scalable Architecture**: Async processing with configurable concurrency

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Docker and Docker Compose

### Installation

1. **Clone and Setup**
```bash
cd services/security-audit
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
uvicorn src.main:app --host 0.0.0.0 --port 8021 --reload
```

### API Documentation
- OpenAPI docs: `http://localhost:8021/docs`
- ReDoc: `http://localhost:8021/redoc`

## Usage Examples

### Start Security Audit

```bash
curl -X POST "http://localhost:8021/api/v1/audits" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "/path/to/project",
    "scans": ["code", "dependency"],
    "compliance_standards": ["iso27001", "gdpr"]
  }'
```

### Check Audit Status

```bash
curl "http://localhost:8021/api/v1/audits/{audit_id}/status"
```

### Get Audit Results

```bash
curl "http://localhost:8021/api/v1/audits/{audit_id}"
```

### Individual Scans

```bash
# Code scan
curl -X POST "http://localhost:8021/api/v1/scans" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "/path/to/code",
    "scan_type": "code"
  }'

# Dependency scan
curl -X POST "http://localhost:8021/api/v1/scans" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "/path/to/project",
    "scan_type": "dependency"
  }'

# Web application scan
curl -X POST "http://localhost:8021/api/v1/scans" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "https://example.com",
    "scan_type": "web"
  }'
```

### Compliance Checks

```bash
curl -X POST "http://localhost:8021/api/v1/compliance/check" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "/path/to/project",
    "standards": ["iso27001", "gdpr", "soc2"]
  }'
```

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=security-audit
SERVICE_PORT=8021
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/mams_security

# Redis
REDIS_URL=redis://localhost:6379/3

# Security Scanning
SCAN_INTERVAL_MINUTES=60
MAX_CONCURRENT_SCANS=5
SCAN_TIMEOUT_SECONDS=300

# OWASP ZAP
ZAP_API_KEY=your-zap-api-key
ZAP_PROXY_HOST=localhost
ZAP_PROXY_PORT=8080

# Compliance Standards
ENABLE_ISO27001=true
ENABLE_GDPR=true
ENABLE_SOC2=true
ENABLE_PCI_DSS=false

# Vulnerability Database
NVD_API_KEY=your-nvd-api-key

# Alerting
ALERT_WEBHOOK_URL=https://hooks.slack.com/your-webhook
ALERT_EMAIL=security@yourdomain.com
CRITICAL_SEVERITY_THRESHOLD=9.0
HIGH_SEVERITY_THRESHOLD=7.0
```

### Scanner Configuration

The service supports multiple security scanners:

#### Code Scanners
- **Bandit**: Python security linting
- **Semgrep**: Multi-language static analysis
- **ESLint**: JavaScript security rules (optional)

#### Dependency Scanners
- **Safety**: Python package vulnerability database
- **pip-audit**: Python dependency auditing
- **npm audit**: Node.js dependency auditing (if detected)

#### Web Scanners
- **OWASP ZAP**: Web application security scanner
- **Custom rules**: Configurable security tests

## Architecture

### Service Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Security Audit  │────│    Database     │
│                 │    │     Service      │    │   PostgreSQL    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                       ┌────────▼────────┐
                       │  Audit Engine   │
                       │                 │
                       └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Security   │    │   Compliance     │    │    External      │
│   Scanners   │    │   Checkers       │    │   Integrations   │
│              │    │                  │    │                  │
│ • Code       │    │ • ISO 27001      │    │ • OWASP ZAP      │
│ • Dependency │    │ • GDPR           │    │ • NVD Database   │
│ • Web App    │    │ • SOC 2          │    │ • Slack/Email    │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

### Audit Workflow

1. **Audit Request**: Client submits audit request with target and options
2. **Validation**: Request validation and resource availability check
3. **Scheduling**: Audit queued and scheduled based on concurrency limits
4. **Execution**: Parallel execution of selected scans and compliance checks
5. **Aggregation**: Results collected and aggregated into comprehensive report
6. **Notification**: Alerts sent for critical findings
7. **Storage**: Results persisted to database for historical analysis

### Database Schema

```sql
-- Core audit tracking
audit_results (id, target, status, started_at, completed_at, ...)
scan_results (id, scan_type, target, status, findings_count, ...)
findings (id, scan_result_id, severity, title, description, ...)
compliance_results (id, standard, target, score, status, ...)

-- Scheduling and templates
scan_schedules (id, cron_expression, target, scan_types, ...)
scan_templates (id, name, scan_types, options, ...)

-- Metrics and reporting
security_metrics (id, metric_name, value, timestamp, ...)
```

## Security Features

### Vulnerability Types Detected

#### Code Vulnerabilities
- SQL injection patterns
- Cross-site scripting (XSS)
- Command injection
- Hardcoded secrets
- Insecure cryptography
- Authentication bypasses
- Authorization flaws

#### Dependency Vulnerabilities
- Known CVEs in dependencies
- Outdated packages with security fixes
- Malicious packages
- License compliance issues

#### Web Application Vulnerabilities
- OWASP Top 10 vulnerabilities
- SSL/TLS configuration issues
- HTTP security headers
- Authentication and session management
- Input validation flaws

### Compliance Standards

#### ISO 27001 Controls
- **A.9**: Access Control
- **A.10**: Cryptography
- **A.12**: Operations Security
- **A.13**: Communications Security
- **A.14**: System Acquisition, Development and Maintenance
- **A.15**: Supplier Relationships
- **A.16**: Information Security Incident Management
- **A.17**: Information Security Aspects of Business Continuity Management

#### GDPR Principles
- Lawfulness, fairness and transparency
- Purpose limitation
- Data minimisation
- Accuracy
- Storage limitation
- Integrity and confidentiality
- Accountability

#### SOC 2 Criteria
- Security
- Availability
- Processing Integrity
- Confidentiality
- Privacy

## API Reference

### Audit Endpoints

#### POST /api/v1/audits
Start comprehensive security audit

**Request:**
```json
{
  "target": "/path/to/project",
  "scans": ["code", "dependency", "web"],
  "compliance_standards": ["iso27001", "gdpr"],
  "options": {
    "include_patterns": ["*.py", "*.js"],
    "exclude_patterns": ["*/test/*"]
  }
}
```

**Response:**
```json
{
  "audit_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "accepted",
  "message": "Security audit started successfully"
}
```

#### GET /api/v1/audits/{audit_id}
Get complete audit results

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "target": "/path/to/project",
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:15:00Z",
  "duration_seconds": 900,
  "scan_results": [...],
  "compliance_results": [...],
  "summary": {
    "total_scans": 3,
    "successful_scans": 3,
    "failed_scans": 0,
    "total_findings": 25,
    "critical_findings": 2,
    "high_findings": 8,
    "compliance_score": 0.85
  },
  "status": "completed"
}
```

### Scan Endpoints

#### POST /api/v1/scans
Start individual security scan

#### GET /api/v1/scans/{scan_id}
Get scan results

#### GET /api/v1/scans
List scan results with pagination

### Compliance Endpoints

#### POST /api/v1/compliance/check
Start compliance check

#### GET /api/v1/compliance/{check_id}
Get compliance results

#### GET /api/v1/compliance
List compliance results

### Health Endpoint

#### GET /health
Service health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "database_connected": true,
  "redis_connected": true,
  "active_scans": 2
}
```

## Monitoring and Alerting

### Metrics Collected
- Audit execution times
- Finding counts by severity
- Compliance scores over time
- Scanner performance metrics
- Error rates and types

### Alert Conditions
- Critical vulnerabilities detected
- Compliance score below threshold
- Scan failures
- Service health issues

### Integration Points
- Slack webhooks
- Email notifications
- Prometheus metrics
- Custom webhook endpoints

## Deployment

### Docker Deployment

```yaml
version: '3.8'
services:
  security-audit:
    build: .
    ports:
      - "8021:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/mams_security
      - REDIS_URL=redis://redis:6379/3
    depends_on:
      - postgres
      - redis
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For container scanning
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: security-audit
spec:
  replicas: 2
  selector:
    matchLabels:
      app: security-audit
  template:
    metadata:
      labels:
        app: security-audit
    spec:
      containers:
      - name: security-audit
        image: mams/security-audit:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: security-audit-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_security_scanner.py -v
pytest tests/test_compliance_checker.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type checking
mypy src/
```

### Adding New Scanners

1. Implement scanner interface in `src/core/security_scanner.py`
2. Add configuration options in `src/core/config.py`
3. Register scanner in audit engine
4. Add tests in `tests/`
5. Update documentation

### Adding New Compliance Standards

1. Implement checker interface in `src/core/compliance_checker.py`
2. Add standard enum value in schemas
3. Define compliance controls and requirements
4. Add pattern matching for standard requirements
5. Add tests and documentation

## Security Considerations

### Service Security
- All external tool executions are sandboxed
- Input validation for all API endpoints
- Rate limiting and authentication
- Secure configuration management
- Regular security updates

### Data Protection
- Audit results encrypted at rest
- Secure transmission of findings
- Data retention policies
- Access logging and monitoring

### Scanner Safety
- Read-only access to scan targets
- Timeout protection
- Resource usage limits
- Error handling and recovery

## Troubleshooting

### Common Issues

#### Scanner Not Found
```bash
# Install missing scanner
pip install bandit semgrep safety

# Verify installation
bandit --version
semgrep --version
safety --version
```

#### Database Connection Issues
```bash
# Check database connectivity
psql -h localhost -U postgres -d mams_security

# Verify connection string
echo $DATABASE_URL
```

#### OWASP ZAP Connection
```bash
# Start ZAP in daemon mode
zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.key=your-api-key

# Test ZAP connection
curl http://localhost:8080/JSON/core/view/version/
```

### Performance Tuning

#### Scan Performance
- Adjust `MAX_CONCURRENT_SCANS` based on resources
- Use `SCAN_TIMEOUT_SECONDS` to prevent hanging scans
- Configure scanner-specific options for faster execution

#### Database Performance
- Monitor query performance
- Add indexes for frequent queries
- Configure connection pooling
- Regular maintenance and VACUUM

### Logs and Debugging

```bash
# View service logs
docker-compose logs -f security-audit

# Enable debug logging
export LOG_LEVEL=DEBUG

# Check scan execution
grep "scan_completed" /var/log/security-audit.log
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## License

This service is part of the MAMS platform and follows the project's licensing terms.

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs for error details
- Contact the MAMS development team
- Submit issues in the project repository