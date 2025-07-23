# MAMS SLA Management Service

A comprehensive Service Level Agreement (SLA) management and monitoring service for the Digital Media Asset Management System (MAMS) platform. This service provides automated SLA compliance monitoring, penalty calculation, and notification management.

## Features

### Core SLA Capabilities
- **Multi-Tier SLA Agreements**: Basic, Professional, Enterprise, and Premium tiers
- **Real-Time Compliance Monitoring**: Continuous tracking of SLA metrics
- **Automated Penalty Calculation**: Service credit calculations for SLA breaches
- **Comprehensive Notification System**: Multi-channel alerting and escalation
- **Compliance History Tracking**: Historical compliance data and trend analysis
- **Custom SLA Templates**: Configurable metrics, penalties, and notifications

### Supported SLA Tiers

#### Basic Tier (99.0% Uptime)
- Business hours support (9 AM - 5 PM)
- Email support
- Standard backups (30 days)
- Community forum access
- API response time: ≤2000ms
- Support response: ≤24 hours

#### Professional Tier (99.5% Uptime)
- Extended hours support (6 AM - 10 PM)
- Phone and email support
- Extended backups (90 days)
- Priority support queue
- Dedicated account manager
- API response time: ≤1000ms
- Support response: ≤8 hours

#### Enterprise Tier (99.9% Uptime)
- 24/7 support coverage
- Multi-channel support
- Long-term backups (1 year)
- Dedicated technical account manager
- On-site support available
- API response time: ≤500ms
- Support response: ≤2 hours
- Compliance reporting

#### Premium Tier (99.99% Uptime)
- 24/7/365 premium support
- Dedicated support team
- Unlimited backups
- Named technical contacts
- Emergency hotline
- API response time: ≤250ms
- Support response: ≤1 hour
- Custom development
- Strategic consulting

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and setup**:
   ```bash
   cd services/sla-management
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start the service**:
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   curl http://localhost:8011/health
   ```

4. **Access API documentation**:
   Open http://localhost:8011/docs

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # PostgreSQL setup
   createdb mams_sla
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env file
   ```

4. **Run the service**:
   ```bash
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8011
   ```

## API Endpoints

### Customer Management
- `POST /api/v1/sla/customers` - Create new customer
- `GET /api/v1/sla/customers/{customer_id}` - Get customer details

### SLA Agreement Management
- `POST /api/v1/sla/agreements` - Create SLA agreement
- `GET /api/v1/sla/agreements` - List SLA agreements
- `GET /api/v1/sla/agreements/{agreement_id}` - Get agreement details
- `POST /api/v1/sla/agreements/{agreement_id}/activate` - Activate agreement

### SLA Templates
- `GET /api/v1/sla/tiers` - Get available SLA tiers
- `GET /api/v1/sla/templates/{tier}` - Get SLA template for tier

### Compliance Monitoring
- `POST /api/v1/sla/compliance/calculate` - Calculate compliance for period
- `GET /api/v1/sla/compliance/{agreement_id}/history` - Get compliance history

### System Information
- `GET /health` - Service health check
- `GET /metrics` - Service metrics
- `GET /summary` - SLA system summary

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | Service port | 8011 |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `MONITORING_INTERVAL_MINUTES` | Monitoring frequency | 5 |
| `PENALTY_CALCULATION_ENABLED` | Enable penalty calculation | true |
| `PENALTY_AUTO_APPLY` | Auto-apply penalties | false |
| `EMAIL_SMTP_HOST` | SMTP server for notifications | None |

### SLA Configuration

The service supports extensive SLA customization:
- **Custom Metrics**: Define application-specific metrics
- **Custom Penalties**: Configure penalty structures
- **Custom Notifications**: Set up multi-channel notifications
- **Escalation Rules**: Define escalation workflows

## Usage Examples

### Create a Customer

```bash
curl -X POST "http://localhost:8011/api/v1/sla/customers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "customer_id": "acme_corp",
    "company_name": "ACME Corporation",
    "contact_email": "admin@acme.com",
    "contact_name": "John Smith"
  }'
```

### Create an SLA Agreement

```bash
curl -X POST "http://localhost:8011/api/v1/sla/agreements" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "customer_id": "acme_corp",
    "tier": "enterprise",
    "effective_date": "2025-01-01T00:00:00Z",
    "expiration_date": "2025-12-31T23:59:59Z"
  }'
```

### Calculate Compliance

```bash
curl -X POST "http://localhost:8011/api/v1/sla/compliance/calculate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "agreement_id": "sla_acme_corp_12345678",
    "period_start": "2025-07-01T00:00:00Z",
    "period_end": "2025-07-31T23:59:59Z"
  }'
```

### Get Compliance History

```bash
curl "http://localhost:8011/api/v1/sla/compliance/sla_acme_corp_12345678/history?period_type=monthly&limit=12" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## SLA Metrics

### Standard Metrics
- **System Uptime**: Percentage availability
- **API Response Time**: Average response latency
- **Support Response Time**: Time to first support response
- **Data Backup Success Rate**: Backup reliability
- **Security Compliance Score**: Security posture rating

### Custom Metrics
Support for custom business metrics:
- Media processing time
- Transcoding success rate
- Storage performance
- Search response time
- User satisfaction scores

## Penalty System

### Penalty Types
- **Service Credits**: Percentage-based credits
- **Fixed Amount**: Dollar amount penalties
- **Termination Rights**: Customer termination options

### Penalty Calculation
- Automatic calculation based on SLA breaches
- Configurable penalty amounts and caps
- Approval workflows for penalty application
- Dispute resolution tracking

## Notification System

### Notification Channels
- **Email**: SMTP-based email notifications
- **Webhook**: HTTP webhook calls
- **SMS**: Twilio-based SMS alerts
- **Slack**: Slack channel notifications
- **Microsoft Teams**: Teams channel alerts

### Escalation Rules
- Time-based escalation
- Multi-level escalation chains
- Rate limiting and cooldown periods
- Acknowledgment tracking

## Monitoring & Reporting

### Real-Time Monitoring
- Continuous compliance monitoring
- Real-time alerting
- Dashboard integration
- Performance metrics

### Reporting Features
- Compliance scorecards
- Trend analysis
- Executive summaries
- Detailed breach reports
- Historical comparisons

### Integration with Monitoring Tools
- Prometheus metrics export
- Grafana dashboard templates
- Custom monitoring integrations

## Database Schema

The service uses PostgreSQL with comprehensive SLA tracking:
- `sla_agreements` - SLA agreement records
- `sla_metrics` - Metric definitions
- `sla_penalties` - Penalty configurations
- `sla_notifications` - Notification settings
- `sla_metric_measurements` - Metric measurements
- `sla_compliance_records` - Compliance tracking
- `sla_penalty_applications` - Applied penalties
- `sla_notification_logs` - Notification history

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
   - Secure JWT configuration
   - HTTPS-only communication
   - Database encryption
   - Audit logging

2. **Scalability**:
   - Database connection pooling
   - Redis clustering
   - Load balancing
   - Horizontal scaling

3. **Reliability**:
   - Database backups
   - Monitoring and alerting
   - Disaster recovery
   - High availability setup

### Kubernetes Deployment
See `k8s/` directory for Kubernetes manifests.

## Legal Compliance

### SLA Terms and Conditions
Each SLA tier includes comprehensive legal terms covering:
- Service availability commitments
- Performance standards
- Support coverage details
- Penalty structures
- Termination clauses
- Liability limitations

### Audit Trail
Complete audit trail for:
- SLA agreement changes
- Compliance calculations
- Penalty applications
- Notification delivery
- Customer interactions

## Support

For issues and questions:
- Check the API documentation at `/docs`
- Review the health endpoint at `/health`
- Check application logs
- Contact the SLA management team

## License

Part of the MAMS platform - Internal use only.