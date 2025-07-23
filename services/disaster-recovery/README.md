# MAMS Disaster Recovery Service

A comprehensive disaster recovery and business continuity service for the Digital Media Asset Management System (MAMS) platform. This service provides automated backup management, failover orchestration, recovery testing, and business continuity planning capabilities.

## Features

### Core Capabilities
- **Disaster Recovery Planning**: Create and manage comprehensive DR plans with service tiers
- **Automated Backup Management**: Schedule and execute backups with multiple strategies
- **Failover Orchestration**: Automated and manual failover procedures
- **Recovery Testing**: Conduct drills and simulations to validate recovery procedures
- **Business Continuity Planning**: Manage critical functions and emergency procedures
- **Real-time Monitoring**: Health checks and automated failure detection
- **Recovery Runbooks**: Generate step-by-step recovery procedures
- **Compliance Tracking**: Monitor RTO/RPO compliance and generate reports

### Supported Disaster Types
- Hardware Failure
- Software Failure
- Network Outage
- Data Corruption
- Cyber Attack
- Natural Disaster
- Power Outage
- Human Error
- Provider Outage
- Complete Datacenter Loss

### Recovery Tiers
- **Critical**: RTO < 1 hour, RPO < 15 minutes
- **High**: RTO < 4 hours, RPO < 1 hour
- **Medium**: RTO < 24 hours, RPO < 4 hours
- **Low**: RTO < 72 hours, RPO < 24 hours

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and setup**:
   ```bash
   cd services/disaster-recovery
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start the service**:
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**:
   ```bash
   curl http://localhost:8014/health
   ```

4. **Access API documentation**:
   Open http://localhost:8014/docs

### Manual Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup databases**:
   ```bash
   # PostgreSQL
   createdb mams_dr
   
   # Run migrations
   alembic upgrade head
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env file
   ```

4. **Run the service**:
   ```bash
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8014
   ```

## API Endpoints

### Disaster Recovery Plans
- `POST /api/v1/disaster-recovery/plans` - Create new DR plan
- `GET /api/v1/disaster-recovery/plans` - List all DR plans
- `GET /api/v1/disaster-recovery/plans/{plan_id}` - Get plan details
- `PUT /api/v1/disaster-recovery/plans/{plan_id}` - Update plan
- `DELETE /api/v1/disaster-recovery/plans/{plan_id}` - Delete plan

### Backup Operations
- `POST /api/v1/disaster-recovery/backup/execute` - Execute backup
- `GET /api/v1/disaster-recovery/backup/status/{plan_id}` - Get backup status
- `POST /api/v1/disaster-recovery/backup/restore` - Restore from backup
- `GET /api/v1/disaster-recovery/backup/history/{plan_id}` - Get backup history

### Failover Operations
- `POST /api/v1/disaster-recovery/failover/execute` - Execute failover
- `POST /api/v1/disaster-recovery/failover/rollback/{failover_id}` - Rollback failover
- `GET /api/v1/disaster-recovery/failover/status/{service_name}` - Get failover status
- `GET /api/v1/disaster-recovery/failover/history/{plan_id}` - Get failover history

### Recovery Testing
- `POST /api/v1/disaster-recovery/tests/conduct` - Conduct recovery test
- `GET /api/v1/disaster-recovery/tests/history/{plan_id}` - Get test history
- `GET /api/v1/disaster-recovery/tests/report/{test_id}` - Get test report

### Business Continuity
- `POST /api/v1/disaster-recovery/business-continuity/plans` - Create BCP
- `GET /api/v1/disaster-recovery/business-continuity/plans/{bcp_id}` - Get BCP details
- `POST /api/v1/disaster-recovery/business-continuity/activate/{bcp_id}` - Activate BCP

### Monitoring & Dashboard
- `GET /api/v1/disaster-recovery/dashboard/{plan_id}` - Get recovery dashboard
- `GET /api/v1/disaster-recovery/health/{service_name}` - Get service health
- `GET /api/v1/disaster-recovery/metrics/{plan_id}` - Get recovery metrics

### Recovery Runbooks
- `POST /api/v1/disaster-recovery/runbooks/generate` - Generate recovery runbook
- `GET /api/v1/disaster-recovery/runbooks/{plan_id}` - List runbooks
- `GET /api/v1/disaster-recovery/runbooks/download/{runbook_id}` - Download runbook

### Disaster Events
- `POST /api/v1/disaster-recovery/events/report` - Report disaster event
- `GET /api/v1/disaster-recovery/events/active` - Get active events
- `PUT /api/v1/disaster-recovery/events/{event_id}/resolve` - Resolve event

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | Service port | 8014 |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `BACKUP_BUCKET` | S3 bucket for backups | mams-backups |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `DEFAULT_RTO_CRITICAL_MINUTES` | Critical tier RTO | 60 |
| `DEFAULT_RPO_CRITICAL_MINUTES` | Critical tier RPO | 15 |
| `BACKUP_RETENTION_DAYS_DEFAULT` | Default backup retention | 30 |
| `FAILOVER_HEALTH_CHECK_INTERVAL_SECONDS` | Health check interval | 30 |
| `MONITORING_ENABLED` | Enable monitoring | true |

### Backup Strategies

The service supports multiple backup strategies:
- **Full Backup**: Complete backup of all data
- **Incremental**: Only changes since last backup
- **Differential**: Changes since last full backup
- **Snapshot**: Point-in-time snapshots
- **Continuous**: Real-time replication

### Failover Modes

- **Automatic**: Triggered by health check failures
- **Manual**: Administrator-initiated
- **Scheduled**: Planned maintenance windows
- **Emergency**: Immediate failover for disasters

## Usage Examples

### Create a Disaster Recovery Plan

```bash
curl -X POST "http://localhost:8014/api/v1/disaster-recovery/plans" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Production DR Plan",
    "description": "Main production disaster recovery plan",
    "recovery_tiers": {
      "postgresql": "critical",
      "mongodb": "high",
      "storage": "medium",
      "redis": "low"
    },
    "backup_strategies": [
      {
        "service_name": "postgresql",
        "backup_type": "full",
        "frequency": "0 2 * * *",
        "retention_days": 30,
        "storage_locations": ["s3://mams-backups/postgresql"]
      }
    ],
    "failover_procedures": [
      {
        "service_name": "postgresql",
        "failover_mode": "automatic",
        "primary_region": "us-east-1",
        "failover_regions": ["us-west-2", "eu-west-1"],
        "health_check_url": "http://postgres:5432/health",
        "failover_steps": [
          {
            "name": "Update DNS",
            "type": "update_dns",
            "domain": "db.mams.example.com"
          }
        ]
      }
    ],
    "contact_list": [
      {
        "name": "John Doe",
        "role": "DBA",
        "phone": "+1-555-1234",
        "email": "john.doe@example.com"
      }
    ]
  }'
```

### Execute a Backup

```bash
curl -X POST "http://localhost:8014/api/v1/disaster-recovery/backup/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "plan_id": "plan_12345678",
    "service_name": "postgresql",
    "backup_type": "full"
  }'
```

### Conduct a Recovery Test

```bash
curl -X POST "http://localhost:8014/api/v1/disaster-recovery/tests/conduct" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "plan_id": "plan_12345678",
    "test_type": "backup_restore",
    "services": ["postgresql", "mongodb"],
    "scenario": {
      "disaster_type": "data_corruption",
      "affected_regions": ["us-east-1"],
      "data_loss_scenario": true
    }
  }'
```

### Generate Recovery Runbook

```bash
curl -X POST "http://localhost:8014/api/v1/disaster-recovery/runbooks/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "plan_id": "plan_12345678",
    "disaster_type": "complete_datacenter_loss",
    "affected_services": ["postgresql", "mongodb", "storage", "redis"]
  }'
```

## Recovery Testing Types

### Tabletop Exercise
- Discussion-based walkthrough of procedures
- No actual system changes
- Validates documentation and communication

### Backup/Restore Test
- Creates test backup
- Restores to isolated environment
- Validates data integrity

### Failover Test
- Tests failover procedures
- Can be done in test environment
- Validates automation and timing

### Full Simulation
- Complete disaster simulation
- Includes all aspects of recovery
- Most comprehensive test type

## Monitoring & Alerts

### Health Monitoring
- Continuous health checks for critical services
- Automatic failover triggering
- Real-time status dashboard

### Compliance Monitoring
- RTO/RPO compliance tracking
- Backup success rate monitoring
- Test completion tracking

### Alert Channels
- Email notifications
- Slack integration
- Microsoft Teams webhooks
- PagerDuty escalation

## Database Schema

The service uses PostgreSQL with the following main tables:
- `dr_plans` - Disaster recovery plans
- `backup_strategies` - Backup configurations
- `backup_jobs` - Backup execution records
- `failover_procedures` - Failover configurations
- `failover_events` - Failover execution records
- `recovery_tests` - Test/drill records
- `recovery_metrics` - RTO/RPO metrics
- `disaster_events` - Actual disaster records
- `business_continuity_plans` - BCP configurations

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
ruff src/
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

1. **High Availability**:
   - Deploy multiple instances
   - Use load balancing
   - Configure database replication

2. **Security**:
   - Secure JWT configuration
   - Encrypt backups at rest
   - Use HTTPS for all endpoints
   - Implement audit logging

3. **Performance**:
   - Optimize backup scheduling
   - Use compression for large backups
   - Implement connection pooling
   - Monitor resource usage

4. **Compliance**:
   - Regular compliance reports
   - Audit trail maintenance
   - Test documentation
   - Recovery time tracking

### Kubernetes Deployment
See `k8s/` directory for Kubernetes manifests.

## Disaster Recovery Best Practices

1. **Regular Testing**:
   - Monthly backup restore tests
   - Quarterly failover drills
   - Annual full simulations

2. **Documentation**:
   - Keep runbooks updated
   - Document all procedures
   - Maintain contact lists
   - Track configuration changes

3. **Monitoring**:
   - Set up comprehensive alerts
   - Monitor all critical services
   - Track compliance metrics
   - Review incident reports

4. **Continuous Improvement**:
   - Learn from incidents
   - Update procedures regularly
   - Implement automation
   - Reduce recovery times

## Support

For issues and questions:
- Check the API documentation at `/docs`
- Review logs for error details
- Contact the platform team

## License

Part of the MAMS platform - Internal use only.