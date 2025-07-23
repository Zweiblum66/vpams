#!/bin/bash
# Setup monitoring dashboards and alerts for MAMS

set -e

# Configuration
MAMS_DIR="/opt/mams"
GRAFANA_URL="http://localhost:3001"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-mams_grafana_2024}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Wait for Grafana to be ready
wait_for_grafana() {
    print_status "Waiting for Grafana to be ready..."
    
    until curl -s "$GRAFANA_URL/api/health" > /dev/null; do
        sleep 5
    done
    
    print_status "Grafana is ready"
}

# Create API key
create_api_key() {
    print_status "Creating Grafana API key..."
    
    API_KEY=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"name":"mams-setup","role":"Admin"}' \
        "http://$GRAFANA_USER:$GRAFANA_PASSWORD@localhost:3001/api/auth/keys" | \
        jq -r '.key')
    
    export GRAFANA_API_KEY=$API_KEY
}

# Import dashboards
import_dashboards() {
    print_status "Importing monitoring dashboards..."
    
    # System Overview Dashboard
    cat > /tmp/system-overview.json <<'EOF'
{
  "dashboard": {
    "title": "MAMS System Overview",
    "panels": [
      {
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "type": "graph",
        "title": "CPU Usage",
        "targets": [
          {
            "expr": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU Usage %"
          }
        ]
      },
      {
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "type": "graph",
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "Memory Usage %"
          }
        ]
      },
      {
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
        "type": "graph",
        "title": "Disk Usage",
        "targets": [
          {
            "expr": "100 - (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"} * 100)",
            "legendFormat": "System Disk %"
          },
          {
            "expr": "100 - (node_filesystem_avail_bytes{mountpoint=\"/mnt/data\"} / node_filesystem_size_bytes{mountpoint=\"/mnt/data\"} * 100)",
            "legendFormat": "Data Disk %"
          }
        ]
      }
    ]
  },
  "overwrite": true
}
EOF

    # Service Health Dashboard
    cat > /tmp/service-health.json <<'EOF'
{
  "dashboard": {
    "title": "MAMS Service Health",
    "panels": [
      {
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
        "type": "table",
        "title": "Service Status",
        "targets": [
          {
            "expr": "up{job=\"mams-services\"}",
            "format": "table",
            "instant": true
          }
        ]
      },
      {
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "type": "graph",
        "title": "API Response Times",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "type": "graph",
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (service)",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  },
  "overwrite": true
}
EOF

    # Import dashboards
    for dashboard in system-overview service-health; do
        curl -s -X POST \
            -H "Authorization: Bearer $GRAFANA_API_KEY" \
            -H "Content-Type: application/json" \
            -d @/tmp/${dashboard}.json \
            "$GRAFANA_URL/api/dashboards/db"
        
        print_status "Imported $dashboard dashboard"
    done
}

# Create alert rules
create_alerts() {
    print_status "Creating alert rules..."
    
    # High CPU Alert
    cat > /tmp/cpu-alert.json <<EOF
{
  "uid": "cpu-alert",
  "title": "High CPU Usage",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "model": {
        "expr": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80",
        "refId": "A"
      }
    }
  ],
  "noDataState": "NoData",
  "execErrState": "Alerting",
  "for": "5m",
  "annotations": {
    "summary": "High CPU usage detected",
    "description": "CPU usage is above 80% for more than 5 minutes"
  }
}
EOF

    # High Memory Alert
    cat > /tmp/memory-alert.json <<EOF
{
  "uid": "memory-alert",
  "title": "High Memory Usage",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "model": {
        "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85",
        "refId": "A"
      }
    }
  ],
  "noDataState": "NoData",
  "execErrState": "Alerting",
  "for": "5m",
  "annotations": {
    "summary": "High memory usage detected",
    "description": "Memory usage is above 85% for more than 5 minutes"
  }
}
EOF

    # Service Down Alert
    cat > /tmp/service-down-alert.json <<EOF
{
  "uid": "service-down-alert",
  "title": "Service Down",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "model": {
        "expr": "up{job=\"mams-services\"} == 0",
        "refId": "A"
      }
    }
  ],
  "noDataState": "NoData",
  "execErrState": "Alerting",
  "for": "2m",
  "annotations": {
    "summary": "MAMS service is down",
    "description": "{{ \$labels.service }} is not responding"
  }
}
EOF

    print_status "Alert rules created"
}

# Main function
main() {
    print_status "=== Setting up MAMS Monitoring ==="
    
    wait_for_grafana
    create_api_key
    import_dashboards
    create_alerts
    
    print_status "=== Monitoring Setup Complete ==="
    print_status "Access Grafana at: $GRAFANA_URL"
    print_status "Default login: admin / $GRAFANA_PASSWORD"
}

# Run main function
main "$@"