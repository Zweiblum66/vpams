# MAMS Alerting System

This directory contains the comprehensive alerting infrastructure for the MAMS (Media Asset Management System). The system provides intelligent, context-aware alerting across all infrastructure, application, and business layers.

## Overview

The MAMS alerting system is designed with multiple layers of intelligence:

1. **Smart Alert Classification**: Infrastructure, Application, Business, Security, and Compliance categories
2. **Team-Based Routing**: Alerts automatically routed to the appropriate teams
3. **Business Hours Awareness**: Different notification strategies for business vs. after hours
4. **Alert Correlation**: Suppress redundant alerts and group related incidents
5. **Rich Notifications**: Multi-channel delivery with actionable information

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Prometheus    │ -> │   Alert      │ -> │  Notification   │
│   (Metrics)     │    │   Rules      │    │   Channels      │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Application   │    │ AlertManager │    │    Teams &      │
│    Metrics      │    │  (Routing)   │    │   Runbooks      │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Alert Categories

### Infrastructure Alerts (`infrastructure-alerts.yml`)

**Critical Infrastructure:**
- Service availability (`MAMSServiceDown`)
- Database connectivity (`MAMSDatabaseConnectionFailure`)
- Storage backend failures (`MAMSStorageBackendDown`)
- OpenSearch cluster health (`MAMSOpenSearchClusterRed`)
- Message queue issues (`MAMSRabbitMQDown`)

**Resource Monitoring:**
- High CPU/Memory usage
- Disk space warnings
- Network performance issues
- Container resource limits

**Monitoring Stack Health:**
- Prometheus target monitoring
- Log ingestion issues
- Trace collection problems

### Application Alerts (`application-alerts.yml`)

**Performance Issues:**
- High error rates (`MAMSHighErrorRate`)
- Extreme latency (`MAMSExtremeLatency`)
- Queue backlogs (`MAMSQueueBacklog`)

**Business Function Failures:**
- Asset upload failures (`MAMSAssetUploadFailure`)
- Search performance degradation
- Authentication system issues
- Workflow execution failures

**Security Events:**
- High authentication error rates
- Potential attacks (`MAMSAuthenticationAttack`)
- Malicious file upload attempts
- Permission escalation attempts

**Data Integrity:**
- Asset corruption detection
- Metadata validation failures
- Database constraint violations

### Business Alerts (`business-alerts.yml`)

**Critical Business Processes:**
- Asset ingestion stopped (`MAMSAssetIngestionStopped`)
- License expiration warnings
- Storage quota critical levels
- Backup system failures

**Operational Issues:**
- Unusual user activity patterns
- Workflow bottlenecks
- Content approval delays
- Asset quality degradation

**Compliance & Legal:**
- GDPR compliance violations
- Rights usage violations
- Audit trail integrity issues

**Financial Impact:**
- Unexpected cost increases
- High subscription cancellation rates
- License optimization opportunities

## Alert Routing & Notification

### Team-Based Routing

Alerts are automatically routed to appropriate teams:

```yaml
# Infrastructure issues → Platform Team
- matchers: [team = platform]
  receiver: 'platform-team'

# Application issues → Backend Team  
- matchers: [team = backend]
  receiver: 'backend-team'

# Media processing → Media Team
- matchers: [team = media]
  receiver: 'media-team'

# Security events → Security Team
- matchers: [team = security]
  receiver: 'security-team'
```

### Severity-Based Escalation

```yaml
# Critical alerts - immediate notification
- matchers: [severity = critical]
  receiver: 'critical-alerts'
  group_wait: 10s
  repeat_interval: 1h

# Warnings - normal business hours
- matchers: [severity = warning]
  receiver: 'warning-business-hours'
  active_time_intervals: [business_hours]
```

### Business Hours Configuration

Different notification strategies for business vs. after hours:

```yaml
time_intervals:
  - name: business_hours
    time_intervals:
      - times:
        - start_time: '09:00'
          end_time: '17:00'
        weekdays: ['monday:friday']
        location: 'America/New_York'
```

## Alert Suppression & Correlation

### Intelligent Inhibition Rules

Prevent alert spam by suppressing related alerts:

```yaml
inhibit_rules:
  # Service down suppresses all other alerts for that service
  - source_matchers: [alertname = MAMSServiceDown]
    target_matchers: [severity =~ warning|info]
    equal: [service]

  # Infrastructure issues suppress application alerts
  - source_matchers: [severity = critical, category = infrastructure]
    target_matchers: [severity =~ warning|info, category = application]
    equal: [instance]
```

### Alert Grouping

Related alerts are grouped together:

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
```

## Notification Channels

### Email Notifications

Rich HTML email templates with:
- Color-coded severity levels
- Detailed alert information
- Direct links to dashboards and runbooks
- Business impact assessment

### Slack Integration

Contextual Slack notifications:
- Channel-specific routing (`#mams-critical`, `#platform-alerts`)
- Rich formatting with emoji indicators
- Interactive buttons for quick actions
- Thread-based alert updates

### PagerDuty Integration (Critical Alerts)

For critical alerts requiring immediate attention:
- Automatic incident creation
- Escalation policies
- Mobile notifications
- Integration with on-call schedules

### Webhook Integration

Custom webhook endpoints for:
- Internal monitoring systems
- Ticketing system integration
- Custom notification logic

## Alert Templates

### Email Templates (`email.tmpl`)

Professional HTML email templates for different alert types:

- **Critical Alerts**: Red theme with urgent styling
- **Infrastructure Alerts**: Orange theme with system details
- **Business Alerts**: Purple theme with business impact
- **Security Alerts**: Red theme with confidentiality notice

### Slack Templates (`slack.tmpl`)

Contextual Slack message templates:

- **Critical**: 🚨 Red alert with immediate action required
- **Business**: 📊 Business impact notifications
- **Security**: 🔒 Security incident alerts
- **Resolved**: ✅ Resolution confirmations

## Runbooks Integration

Each alert includes links to detailed runbooks:

```yaml
annotations:
  runbook_url: "https://docs.mams.local/runbooks/service-down"
  action: "Check service logs and restart if necessary"
```

Runbooks provide:
- Step-by-step troubleshooting procedures
- Common causes and solutions
- Escalation procedures
- Post-incident checklist

## Configuration Files

### Prometheus Rules
- `infrastructure-alerts.yml`: Infrastructure monitoring rules
- `application-alerts.yml`: Application performance and functionality
- `business-alerts.yml`: Business process and compliance monitoring

### AlertManager Configuration
- `alertmanager-advanced.yml`: Main AlertManager configuration
- `email.tmpl`: Email notification templates  
- `slack.tmpl`: Slack message templates

## Setup and Deployment

### 1. Deploy Prometheus Rules

```bash
# Copy rules to Prometheus configuration
cp prometheus/rules/*.yml /etc/prometheus/rules/

# Reload Prometheus configuration
curl -X POST http://prometheus:9090/-/reload
```

### 2. Configure AlertManager

```bash
# Set environment variables
export SMTP_HOST="smtp.company.com"
export SMTP_FROM_ADDRESS="alerts@company.com"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Deploy AlertManager configuration
docker-compose -f docker-compose.alerting.yml up -d
```

### 3. Verify Alert Rules

```bash
# Check rule syntax
promtool check rules prometheus/rules/*.yml

# Test alert queries
curl http://prometheus:9090/api/v1/rules
```

## Monitoring Alert System Health

### AlertManager Metrics

Monitor the alerting system itself:

```yaml
# Alert notification failures
- alert: MAMSAlertmanagerNotificationFailed
  expr: rate(alertmanager_notifications_failed_total[5m]) > 0.1

# Prometheus rule evaluation failures  
- alert: MAMSPrometheusRuleEvaluationFailed
  expr: prometheus_rule_evaluation_failures_total > 0
```

### Alert Fatigue Prevention

Strategies to prevent alert fatigue:

1. **Severity Tuning**: Regular review of alert thresholds
2. **Grouping**: Related alerts grouped together
3. **Suppression**: Automatic suppression of redundant alerts
4. **Business Hours**: Reduced urgency during off-hours
5. **Actionable Alerts**: Every alert includes clear action steps

## Customization Guide

### Adding New Alert Rules

1. **Choose Appropriate File**: Infrastructure, Application, or Business
2. **Define Alert Logic**: Prometheus query expression
3. **Set Metadata**: Labels for routing and context
4. **Add Annotations**: Description, runbook, and actions
5. **Test Alert**: Verify query and notification routing

Example new alert:

```yaml
- alert: MAMSCustomBusinessMetric
  expr: custom_business_metric > 100
  for: 5m
  labels:
    severity: warning
    category: business
    team: analytics
    impact: medium
  annotations:
    summary: "Custom business metric exceeded threshold"
    description: "Business metric value is {{ $value }}"
    runbook_url: "https://docs.mams.local/runbooks/custom-metric"
    action: "Review business process and adjust if necessary"
    business_impact: "May affect business KPI tracking"
```

### Adding New Notification Channels

1. **Define Receiver**: Add to `alertmanager-advanced.yml`
2. **Configure Routing**: Add routing rules
3. **Create Templates**: Custom message templates if needed
4. **Test Integration**: Verify message delivery

### Environment Variables

Required environment variables:

```env
# SMTP Configuration
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=alerts@company.com
SMTP_PASSWORD=smtp_password
SMTP_FROM_ADDRESS=mams-alerts@company.com

# Slack Integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_SECURITY_WEBHOOK_URL=https://hooks.slack.com/services/...

# PagerDuty Integration  
PAGERDUTY_ROUTING_KEY=your_pagerduty_key

# Webhook Authentication
WEBHOOK_TOKEN=your_webhook_token
```

## Best Practices

### Alert Design Principles

1. **Actionable**: Every alert should have a clear action
2. **Contextual**: Include relevant metadata and business impact
3. **Appropriate Urgency**: Match severity to business impact
4. **Clear Ownership**: Route to the right team automatically
5. **Documentation**: Link to runbooks and procedures

### Maintenance Tasks

1. **Weekly Alert Review**: Check for alert fatigue and false positives
2. **Monthly Threshold Tuning**: Adjust thresholds based on performance trends
3. **Quarterly Runbook Updates**: Keep troubleshooting procedures current
4. **Annual Alert Architecture Review**: Evaluate overall alerting strategy

### Testing Procedures

1. **Alert Rule Testing**: Validate Prometheus queries
2. **Notification Testing**: Test all notification channels
3. **Escalation Testing**: Verify escalation procedures work
4. **Business Continuity**: Test alerting during incident scenarios

---

For more details on specific alert configurations or troubleshooting, refer to the individual configuration files and the MAMS monitoring documentation.