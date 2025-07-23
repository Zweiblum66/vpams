# Performance Monitoring Guide for MAMS

## Overview

This guide provides comprehensive instructions for setting up, configuring, and using the performance monitoring system in MAMS. The monitoring solution includes system metrics, application performance, user experience tracking, and real-time alerting.

## Architecture

### Monitoring Stack
```
┌─────────────────────────────────────────────────────────┐
│                   Dashboards                            │
├─────────────────────────────────────────────────────────┤
│  Grafana │ Web Vitals UI │ Custom Dashboards          │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 Metrics Storage                         │
├─────────────────────────────────────────────────────────┤
│  Prometheus │ Redis │ TimescaleDB                      │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│               Metrics Collection                        │
├─────────────────────────────────────────────────────────┤
│  Performance Monitor │ Web Vitals Tracker │ Exporters  │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                  Applications                           │
├─────────────────────────────────────────────────────────┤
│  Services │ Frontend │ Infrastructure                   │
└─────────────────────────────────────────────────────────┘
```

### Components

#### Core Monitoring Services
1. **Performance Monitor**: System and application metrics collection
2. **Web Vitals Tracker**: Frontend performance and user experience
3. **Grafana Dashboards**: Visualization and alerting
4. **Alert Manager**: Real-time notifications and escalation

#### Metrics Categories
- **System Metrics**: CPU, memory, disk, network
- **Application Metrics**: Response times, throughput, errors
- **Business Metrics**: User activity, content metrics
- **Infrastructure Metrics**: Database, cache, queues
- **User Experience**: Core Web Vitals, page performance

## Setup and Installation

### 1. Deploy Monitoring Infrastructure

#### Using Docker Compose
```yaml
# monitoring/docker-compose.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  timescaledb:
    image: timescale/timescaledb:latest-pg14
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=mams_metrics
      - POSTGRES_USER=metrics
      - POSTGRES_PASSWORD=metrics123
    volumes:
      - timescale_data:/var/lib/postgresql/data

volumes:
  prometheus_data:
  grafana_data:
  redis_data:
  timescale_data:
```

#### Deploy Monitoring Stack
```bash
cd monitoring
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Configure Prometheus

#### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # MAMS Services
  - job_name: 'mams-api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'mams-asset-management'
    static_configs:
      - targets: ['asset-management:8001']
    metrics_path: '/metrics'

  - job_name: 'mams-user-management'
    static_configs:
      - targets: ['user-management:8002']
    metrics_path: '/metrics'

  - job_name: 'mams-monitoring'
    static_configs:
      - targets: ['monitoring:8010']
    metrics_path: '/metrics'

  # System metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # Database metrics
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis metrics
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
```

#### Alert Rules
```yaml
# monitoring/alert_rules.yml
groups:
  - name: mams.rules
    rules:
      # High response time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(mams_request_duration_seconds_bucket[5m])) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      # High error rate
      - alert: HighErrorRate
        expr: rate(mams_requests_total{status=~"5.."}[5m]) / rate(mams_requests_total[5m]) > 0.1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High CPU usage
      - alert: HighCPUUsage
        expr: mams_cpu_usage_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (mams_memory_usage_bytes{type="used"} / mams_memory_usage_bytes{type="total"}) * 100 > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}%"

      # Queue size too large
      - alert: LargeQueueSize
        expr: mams_processing_queue_size > 1000
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Processing queue is large"
          description: "Queue {{ $labels.queue_type }} has {{ $value }} items"
```

### 3. Deploy Performance Monitor Service

#### Service Configuration
```yaml
# services/monitoring/docker-compose.yml
version: '3.8'
services:
  performance-monitor:
    build: .
    ports:
      - "8010:8010"
    environment:
      - REDIS_URL=redis://redis:6379
      - ALERT_WEBHOOK_URL=https://hooks.slack.com/your-webhook
      - CHECK_INTERVAL=30
    depends_on:
      - redis
    volumes:
      - ./config:/app/config
```

#### Environment Configuration
```bash
# services/monitoring/.env
REDIS_URL=redis://localhost:6379
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
CHECK_INTERVAL=30
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-grafana-api-key
```

### 4. Set Up Grafana Dashboards

#### Automatic Dashboard Setup
```bash
# Create Grafana dashboards
cd services/monitoring
python src/grafana_dashboards.py \
  --grafana-url http://localhost:3000 \
  --api-key your-grafana-api-key \
  --action create
```

#### Manual Dashboard Import
1. Access Grafana at http://localhost:3000 (admin/admin123)
2. Go to Dashboards → Import
3. Upload dashboard JSON files from `monitoring/dashboards/`

### 5. Configure Frontend Web Vitals

#### Add Web Vitals Tracking to Frontend
```typescript
// frontend/src/utils/webVitals.ts
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

interface VitalMetric {
  name: string;
  value: number;
  delta: number;
  id: string;
}

class WebVitalsReporter {
  private endpoint = '/api/monitoring/web-vitals';
  
  constructor() {
    this.setupWebVitals();
  }
  
  private setupWebVitals() {
    // Core Web Vitals
    getCLS(this.sendMetric.bind(this));
    getFID(this.sendMetric.bind(this));
    getLCP(this.sendMetric.bind(this));
    
    // Other metrics
    getFCP(this.sendMetric.bind(this));
    getTTFB(this.sendMetric.bind(this));
  }
  
  private async sendMetric(metric: VitalMetric) {
    try {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metric: metric.name,
          value: metric.value,
          page_url: window.location.href,
          user_agent: navigator.userAgent,
          connection_type: this.getConnectionType(),
          device_type: this.getDeviceType(),
          user_id: this.getCurrentUserId(),
          session_id: this.getSessionId()
        })
      });
    } catch (error) {
      console.error('Failed to send web vital:', error);
    }
  }
  
  private getConnectionType(): string {
    const connection = (navigator as any).connection;
    return connection ? connection.effectiveType : 'unknown';
  }
  
  private getDeviceType(): string {
    if (window.innerWidth < 768) return 'mobile';
    if (window.innerWidth < 1024) return 'tablet';
    return 'desktop';
  }
  
  private getCurrentUserId(): string | null {
    // Get from auth context or localStorage
    return localStorage.getItem('userId');
  }
  
  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = Math.random().toString(36).substring(2);
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }
}

// Initialize in app
export const webVitalsReporter = new WebVitalsReporter();
```

#### Add to App Root
```typescript
// frontend/src/App.tsx
import { webVitalsReporter } from './utils/webVitals';
import { performanceTracker } from './utils/performanceTracker';

function App() {
  useEffect(() => {
    // Initialize performance tracking
    performanceTracker.start();
    
    // Track page navigation
    const handleRouteChange = () => {
      performanceTracker.trackPageView(window.location.pathname);
    };
    
    window.addEventListener('popstate', handleRouteChange);
    return () => window.removeEventListener('popstate', handleRouteChange);
  }, []);
  
  // ... rest of app
}
```

## Dashboard Usage

### 1. System Overview Dashboard

**URL**: http://localhost:3000/d/system-overview

**Key Metrics**:
- CPU usage by service
- Memory consumption
- Request rates and response times
- Error rates
- Active users and queue sizes

**Alerts**:
- CPU > 90% for 5 minutes
- Memory > 90% for 5 minutes
- Error rate > 10% for 1 minute

### 2. Application Performance Dashboard

**URL**: http://localhost:3000/d/app-performance

**Key Metrics**:
- Response time percentiles (p50, p90, p95, p99)
- Database query performance
- Cache hit rates
- Throughput by endpoint

**Use Cases**:
- Identify slow endpoints
- Monitor database performance
- Track cache effectiveness
- Analyze traffic patterns

### 3. Core Web Vitals Dashboard

**URL**: http://localhost:3000/d/web-vitals

**Key Metrics**:
- Largest Contentful Paint (LCP)
- First Input Delay (FID)
- Cumulative Layout Shift (CLS)
- Performance score distribution
- Page-specific performance

**Optimization Targets**:
- LCP < 2.5s (good), < 4s (acceptable)
- FID < 100ms (good), < 300ms (acceptable)
- CLS < 0.1 (good), < 0.25 (acceptable)

### 4. Business Metrics Dashboard

**URL**: http://localhost:3000/d/business-metrics

**Key Metrics**:
- Assets uploaded per day
- Storage growth
- User activity
- Feature usage

## Alerting and Notifications

### 1. Configure Slack Notifications

#### Slack Webhook Setup
```bash
# Get Slack webhook URL from Slack app settings
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Update monitoring service configuration
echo "ALERT_WEBHOOK_URL=${SLACK_WEBHOOK_URL}" >> services/monitoring/.env
```

#### Custom Alert Template
```json
{
  "text": "MAMS Alert",
  "attachments": [
    {
      "color": "danger",
      "title": "{{ .alert.title }}",
      "text": "{{ .alert.description }}",
      "fields": [
        {
          "title": "Severity",
          "value": "{{ .alert.severity }}",
          "short": true
        },
        {
          "title": "Service",
          "value": "{{ .alert.service }}",
          "short": true
        },
        {
          "title": "Current Value",
          "value": "{{ .alert.current_value }}",
          "short": true
        },
        {
          "title": "Threshold",
          "value": "{{ .alert.threshold }}",
          "short": true
        }
      ],
      "footer": "MAMS Monitoring",
      "ts": {{ .alert.timestamp }}
    }
  ]
}
```

### 2. Email Alerts

#### SMTP Configuration
```yaml
# alertmanager/config.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@mams.example.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'ops-team@example.com'
        subject: 'MAMS Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Labels: {{ range .Labels.SortedPairs }}{{ .Name }}={{ .Value }} {{ end }}
          {{ end }}
```

### 3. PagerDuty Integration

#### PagerDuty Configuration
```yaml
# alertmanager/config.yml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: 'MAMS Alert: {{ .GroupLabels.alertname }}'
        details:
          summary: '{{ .Annotations.summary }}'
          description: '{{ .Annotations.description }}'
          severity: '{{ .CommonLabels.severity }}'
```

## Performance Optimization

### 1. Query Optimization

#### Identify Slow Queries
```promql
# Queries taking longer than 1 second
histogram_quantile(0.95, rate(mams_db_query_duration_seconds_bucket[5m])) > 1

# Most frequent slow queries
topk(10, rate(mams_db_query_duration_seconds_count[5m]))
```

#### Database Performance Monitoring
```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_statement_stats = on;
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s

-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_assets_created_at ON assets(created_at);
CREATE INDEX CONCURRENTLY idx_assets_user_id ON assets(user_id);
```

### 2. Cache Optimization

#### Monitor Cache Performance
```promql
# Cache hit rate by service
rate(mams_cache_hits_total[5m]) / (rate(mams_cache_hits_total[5m]) + rate(mams_cache_misses_total[5m]))

# Cache miss rate trend
rate(mams_cache_misses_total[5m])
```

#### Cache Strategy Tuning
```python
# Adjust cache TTL based on performance data
cache_performance = {
    'user_sessions': {'hit_rate': 0.95, 'ttl': 3600},  # Good
    'asset_metadata': {'hit_rate': 0.60, 'ttl': 300},  # Needs improvement
    'search_results': {'hit_rate': 0.45, 'ttl': 60}    # Poor
}

# Increase TTL for low hit rate items
for cache_type, perf in cache_performance.items():
    if perf['hit_rate'] < 0.8:
        new_ttl = min(perf['ttl'] * 2, 3600)  # Double TTL, max 1 hour
        print(f"Recommend increasing {cache_type} TTL to {new_ttl}s")
```

### 3. Frontend Optimization

#### Monitor Core Web Vitals
```javascript
// Set performance budgets
const PERFORMANCE_BUDGETS = {
  LCP: 2500,  // 2.5s
  FID: 100,   // 100ms
  CLS: 0.1    // 0.1
};

// Alert when budgets are exceeded
function checkPerformanceBudgets(metrics) {
  for (const [metric, value] of Object.entries(metrics)) {
    if (value > PERFORMANCE_BUDGETS[metric]) {
      console.warn(`Performance budget exceeded: ${metric} = ${value}`);
      // Send alert to monitoring
      fetch('/api/monitoring/performance-budget-alert', {
        method: 'POST',
        body: JSON.stringify({ metric, value, budget: PERFORMANCE_BUDGETS[metric] })
      });
    }
  }
}
```

#### Bundle Size Monitoring
```javascript
// Track bundle loading performance
const bundleObserver = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.name.includes('.js') || entry.name.includes('.css')) {
      // Send bundle loading metrics
      fetch('/api/monitoring/bundle-performance', {
        method: 'POST',
        body: JSON.stringify({
          name: entry.name,
          size: entry.transferSize,
          duration: entry.duration,
          timestamp: Date.now()
        })
      });
    }
  }
});

bundleObserver.observe({ entryTypes: ['resource'] });
```

## Troubleshooting

### Common Issues

#### 1. High Memory Usage
```bash
# Check memory usage by service
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Identify memory leaks
curl http://localhost:8001/debug/pprof/heap > heap.pprof
go tool pprof heap.pprof
```

#### 2. Database Connection Pool Exhaustion
```sql
-- Check active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Check connection pool configuration
SHOW max_connections;
SHOW shared_buffers;
```

#### 3. Cache Performance Issues
```bash
# Redis memory usage
redis-cli INFO memory

# Cache hit ratio
redis-cli INFO stats | grep keyspace_hits
```

#### 4. High Response Times
```promql
# Identify slowest endpoints
topk(10, histogram_quantile(0.95, rate(mams_request_duration_seconds_bucket[5m])))

# Check for database bottlenecks
histogram_quantile(0.95, rate(mams_db_query_duration_seconds_bucket[5m])) by (service, query_type)
```

### Performance Testing

#### Load Testing Setup
```bash
# Install Artillery for load testing
npm install -g artillery

# Run load test
artillery run load-test-config.yml
```

```yaml
# load-test-config.yml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
      rampTo: 100
  variables:
    endpoint:
      - "/api/v1/assets"
      - "/api/v1/search"
      - "/api/v1/projects"

scenarios:
  - name: "API Load Test"
    flow:
      - get:
          url: "{{ endpoint }}"
          headers:
            Authorization: "Bearer {{ token }}"
      - think: 5
```

#### Continuous Performance Testing
```yaml
# .github/workflows/performance-test.yml
name: Performance Test

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  
jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run performance tests
        run: |
          docker-compose -f docker-compose.test.yml up -d
          sleep 30  # Wait for services to start
          artillery run performance-tests/load-test.yml
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: performance-results.json
```

## Best Practices

### 1. Monitoring Strategy
- **Start with the basics**: System metrics, error rates, response times
- **Add business metrics**: User activity, feature usage, revenue impact
- **Monitor user experience**: Core Web Vitals, user journeys
- **Set up alerting**: Proactive notifications before users notice issues

### 2. Dashboard Design
- **Keep it simple**: Focus on key metrics that matter
- **Use appropriate visualizations**: Time series for trends, gauges for current state
- **Group related metrics**: System, application, business dashboards
- **Include context**: Annotations for deployments, incidents

### 3. Alert Management
- **Avoid alert fatigue**: Only alert on actionable issues
- **Use escalation**: Start with warnings, escalate to critical
- **Include runbooks**: Link alerts to troubleshooting guides
- **Regular review**: Tune thresholds based on actual incidents

### 4. Performance Culture
- **Share metrics**: Make performance visible to all teams
- **Set SLOs**: Define service level objectives
- **Regular reviews**: Weekly performance reviews
- **Continuous improvement**: Act on monitoring insights

This comprehensive monitoring setup ensures that MAMS performance is continuously tracked, issues are detected early, and the system maintains optimal performance for users.