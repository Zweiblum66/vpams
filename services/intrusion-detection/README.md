# Intrusion Detection Service

## Overview

The Intrusion Detection Service (IDS) is a comprehensive security monitoring system for MAMS that provides real-time threat detection, network monitoring, and security incident management. It combines signature-based detection, anomaly detection, and threat intelligence to identify and respond to security threats.

## Features

### Core Capabilities

- **Network Traffic Monitoring**: Real-time packet capture and analysis
- **Intrusion Detection**: Multiple detection methods including:
  - Signature-based detection
  - Anomaly detection using machine learning
  - Behavioral analysis
  - Threat intelligence matching
- **Host-based Monitoring**: 
  - File integrity monitoring
  - Process monitoring
  - System activity tracking
- **Security Event Management**: Aggregation and correlation of security events
- **Alert Management**: Multi-channel alerting (webhook, email, Slack)
- **Threat Intelligence**: Integration with external threat feeds

### Detection Capabilities

1. **Network Attacks**
   - Port scanning
   - DDoS attacks
   - DNS tunneling
   - SYN floods
   - Suspicious traffic patterns

2. **Host-based Threats**
   - Unauthorized file modifications
   - Suspicious process execution
   - Privilege escalation attempts
   - Malware activity

3. **Application Security**
   - SQL injection attempts
   - Cross-site scripting (XSS)
   - Command injection
   - Authentication attacks

## Architecture

### Components

1. **Detection Engine**: Core detection logic with multiple analyzers
2. **Network Monitor**: Packet capture and analysis using Scapy
3. **Alert Service**: Notification system for security incidents
4. **Database Models**: Storage for events, alerts, and threat intelligence
5. **API Routes**: RESTful API for management and monitoring

### Data Flow

```
Network Traffic → Packet Capture → Analysis Engine → Detection Rules
                                                   ↓
Host Activity → File Monitor → Detection Service → Security Events
                                                   ↓
                                              Alert Generation
                                                   ↓
                                         Notification Channels
```

## API Endpoints

### Events
- `GET /api/v1/events` - List intrusion events with filtering
- `GET /api/v1/events/{event_id}` - Get specific event details

### Alerts
- `GET /api/v1/alerts` - List security alerts
- `GET /api/v1/alerts/{alert_id}` - Get alert details
- `PATCH /api/v1/alerts/{alert_id}` - Update alert status

### Threat Intelligence
- `GET /api/v1/threat-intel` - List threat indicators
- `POST /api/v1/threat-intel` - Add new threat indicator

### Monitoring
- `GET /api/v1/system/metrics` - Current system metrics
- `GET /api/v1/network/stats` - Network monitoring statistics
- `GET /api/v1/dashboard/stats` - Dashboard statistics

### Actions
- `POST /api/v1/actions/block-ip` - Manually block IP address
- `POST /api/v1/actions/trigger-scan` - Trigger security scan

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=intrusion-detection
SERVICE_PORT=8022
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/intrusion_detection

# Redis
REDIS_URL=redis://redis:6379/3

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# Network Monitoring
MONITOR_INTERFACES=["eth0"]
PACKET_CAPTURE_SIZE=65535

# Detection Settings
ANOMALY_THRESHOLD=0.85
MAX_FAILED_LOGINS=5
PORT_SCAN_THRESHOLD=10
DDOS_THRESHOLD=1000

# Alerting
ALERT_WEBHOOK_URL=https://your-webhook.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
```

## Detection Rules

### Port Scan Detection
- Threshold: 10 unique ports within 60 seconds
- Severity: High
- Response: Alert generation, optional IP blocking

### DDoS Detection
- Threshold: 1000 requests per 10 seconds
- Severity: Critical
- Response: Immediate alert, automatic mitigation

### Suspicious Process Detection
- Patterns: Common attack tools (nmap, nikto, sqlmap, etc.)
- Severity: High
- Response: Process termination, alert generation

### File Integrity Monitoring
- Critical paths: /etc/passwd, /etc/shadow, /etc/sudoers, etc.
- Severity: Critical for system files
- Response: Immediate alert, rollback capability

## Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize database:
```bash
alembic upgrade head
```

3. Run the service:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8022
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_detection_service.py
```

### Docker

```bash
# Build image
docker build -t mams-intrusion-detection .

# Run container
docker run -p 8022:8022 --cap-add=NET_ADMIN --cap-add=NET_RAW mams-intrusion-detection
```

Note: Network capabilities (NET_ADMIN, NET_RAW) are required for packet capture.

## Security Considerations

1. **Privileged Access**: The service requires elevated privileges for packet capture
2. **Data Privacy**: Captured packets may contain sensitive information
3. **False Positives**: Tune detection thresholds to minimize false alerts
4. **Performance Impact**: Monitor resource usage, especially for high-traffic networks
5. **Alert Fatigue**: Implement proper alert prioritization and grouping

## Monitoring

### Metrics
- Packets captured/analyzed per second
- Detection accuracy rate
- False positive rate
- Alert response time
- System resource usage

### Health Checks
- Service availability: `/health`
- Component status: Check network monitor, detection engine
- Database connectivity
- Redis connectivity

## Integration

### With Other MAMS Services
- **Asset Management**: Link security events to assets
- **User Management**: Track user-related security events
- **Workflow Engine**: Trigger automated responses
- **Monitoring Service**: Export metrics and logs

### External Systems
- SIEM integration via syslog or API
- Threat intelligence feed integration
- Firewall rule updates
- Incident response platforms

## Best Practices

1. **Regular Updates**: Keep threat intelligence and detection rules updated
2. **Baseline Tuning**: Adjust anomaly detection baselines for your environment
3. **Alert Tuning**: Configure alert thresholds to reduce noise
4. **Log Retention**: Set appropriate retention policies for security events
5. **Testing**: Regularly test detection capabilities with safe tools

## Troubleshooting

### Common Issues

1. **No packets captured**
   - Check network interface permissions
   - Verify interface name in configuration
   - Ensure Docker capabilities are set

2. **High false positive rate**
   - Review and adjust detection thresholds
   - Update baseline models
   - Whitelist known safe IPs/domains

3. **Performance issues**
   - Limit packet capture rate
   - Optimize detection rules
   - Scale horizontally for high-traffic environments

## License

This service is part of the MAMS project and follows the same licensing terms.