# MAMS Security Certification Service

A comprehensive security certification and compliance service for the Digital Media Asset Management System (MAMS) platform. This service provides automated security audits, vulnerability assessments, compliance checking, and certification reporting.

## Features

### Core Security Capabilities
- **Comprehensive Security Audits**: Full system security assessments
- **Vulnerability Scanning**: Network, web application, and infrastructure scanning
- **Compliance Checking**: Multi-standard compliance verification
- **Risk Assessment**: Automated risk scoring and analysis
- **Security Metrics**: KPI tracking and trend analysis

### Supported Compliance Standards
- ISO 27001 (Information Security Management)
- SOC 2 Type II (Service Organization Control)
- GDPR (General Data Protection Regulation)
- PCI DSS (Payment Card Industry Data Security Standard)
- NIST Cybersecurity Framework
- HIPAA (Healthcare compliance)
- SOX (Sarbanes-Oxley)
- FedRAMP (Federal Risk Authorization Management Program)

### Security Assessment Types
- **Network Security**: Port scanning, service enumeration, firewall testing
- **Web Application Security**: OWASP Top 10 vulnerability assessment
- **Infrastructure Security**: System configuration, patch management
- **SSL/TLS Analysis**: Certificate validation, cipher strength assessment
- **DNS Security**: Domain and subdomain security analysis

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and setup**:
   ```bash
   cd services/security-certification
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start the service**:
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   curl http://localhost:8010/health
   ```

4. **Access API documentation**:
   Open http://localhost:8010/docs

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # PostgreSQL setup
   createdb mams_security
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env file
   ```

4. **Run the service**:
   ```bash
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8010
   ```

## API Endpoints

### Security Audits
- `POST /api/v1/security/audit/start` - Start comprehensive security audit
- `GET /api/v1/security/audit/{audit_id}/status` - Get audit status
- `GET /api/v1/security/audit/{audit_id}/results` - Get audit results

### Compliance Checking
- `POST /api/v1/security/compliance/check` - Perform compliance check
- `GET /api/v1/security/standards` - List supported standards

### Reporting
- `POST /api/v1/security/certification/report` - Generate certification report
- `GET /api/v1/security/findings` - Get security findings
- `GET /api/v1/security/metrics` - Get security metrics

### Health & Monitoring
- `GET /health` - Service health check
- `GET /metrics` - Service metrics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | Service port | 8010 |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `MAX_SCAN_TARGETS` | Maximum scan targets | 50 |
| `SCAN_TIMEOUT_MINUTES` | Scan timeout | 120 |
| `ENABLE_AUTOMATED_SCANNING` | Enable auto scanning | true |

### Security Tools Integration

The service integrates with external security tools:
- **Nmap**: Network discovery and security auditing
- **OpenVAS**: Vulnerability scanning (optional)
- **SSLyze**: SSL/TLS configuration analysis

## Usage Examples

### Start a Security Audit

```bash
curl -X POST "http://localhost:8010/api/v1/security/audit/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "target_systems": ["https://api.example.com", "https://app.example.com"],
    "compliance_standards": ["iso27001", "soc2_type2"],
    "audit_type": "comprehensive",
    "priority": "high"
  }'
```

### Check Compliance

```bash
curl -X POST "http://localhost:8010/api/v1/security/compliance/check" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "standards": ["gdpr", "iso27001"],
    "scope": ["data_processing", "access_control"]
  }'
```

### Generate Certification Report

```bash
curl -X POST "http://localhost:8010/api/v1/security/certification/report" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "audit_id": "audit_20240115_123456_abc123",
    "report_format": "pdf",
    "include_executive_summary": true,
    "include_detailed_findings": true
  }'
```

## Security Features

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- API key management
- Rate limiting and throttling

### Data Protection
- Encryption at rest and in transit
- Secure credential storage
- Input validation and sanitization
- SQL injection prevention

### Audit Trail
- Comprehensive logging
- Activity tracking
- Change monitoring
- Compliance audit support

## Database Schema

The service uses PostgreSQL with the following main tables:
- `security_audits` - Audit records and metadata
- `security_findings` - Vulnerability findings
- `compliance_checks` - Compliance verification results
- `security_certifications` - Certification records
- `security_metrics` - Performance metrics and KPIs

## Monitoring & Logging

### Structured Logging
- JSON-formatted logs
- Correlation IDs
- Performance metrics
- Error tracking

### Health Checks
- Database connectivity
- Redis connectivity
- External service status
- Resource utilization

### Metrics
- Audit completion rates
- Finding severity distribution
- Compliance scores
- Performance indicators

## Development

### Running Tests
```bash
pytest tests/ -v --cov=src
```

### Code Quality
```bash
# Formatting
black src/
isort src/

# Linting
flake8 src/
mypy src/
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Deployment

### Production Considerations
1. **Security**:
   - Use strong JWT secrets
   - Enable HTTPS only
   - Configure proper CORS
   - Set up WAF rules

2. **Scalability**:
   - Use connection pooling
   - Configure Redis clustering
   - Set up load balancing
   - Monitor resource usage

3. **Reliability**:
   - Database backups
   - Health monitoring
   - Graceful shutdowns
   - Error recovery

### Kubernetes Deployment
See `k8s/` directory for Kubernetes manifests.

## Support

For issues and questions:
- Check the API documentation at `/docs`
- Review the health endpoint at `/health`
- Check application logs
- Contact the security team

## License

Part of the MAMS platform - Internal use only.