# MAMS Grafana Dashboards

This directory contains Grafana dashboard configurations for monitoring the MAMS platform.

## Dashboard Overview

### 1. System Overview Dashboard (`mams-system-overview`)
- **Purpose**: High-level view of the entire MAMS platform
- **Key Metrics**:
  - Service health status
  - Request distribution across services
  - Processing queue size
  - Storage usage
  - Active workflows
  - Overall error rate
  - Request rates and response times

### 2. Service Metrics Dashboard (`mams-service-metrics`)
- **Purpose**: Detailed metrics for individual services
- **Features**:
  - Service selector dropdown
  - Service health and uptime
  - CPU and memory usage
  - Request rate and error rate
  - Response time percentiles (p50, p95, p99)
  - Status code distribution
- **Use Case**: Deep dive into specific service performance

### 3. Business Metrics Dashboard (`mams-business-metrics`)
- **Purpose**: Business and usage analytics
- **Key Metrics**:
  - Total assets, users, and projects
  - Storage usage
  - Asset uploads per hour by type
  - Asset distribution by type
  - Workflow executions
  - Search query volume
  - Top storage users
- **Use Case**: Business intelligence and capacity planning

### 4. Infrastructure Dashboard (`mams-infrastructure`)
- **Purpose**: Infrastructure and resource monitoring
- **Key Metrics**:
  - Node CPU and memory usage
  - Disk usage
  - Network I/O
  - Database connections and query latency
  - Cache hit rates
  - Top resource-consuming containers
- **Use Case**: Infrastructure optimization and troubleshooting

### 5. Alerts Dashboard (`mams-alerts`)
- **Purpose**: Alert management and overview
- **Features**:
  - Active alert counts by severity
  - Alert table with details
  - Alert trend visualization
  - Integration with Prometheus Alertmanager
- **Use Case**: Incident response and alert management

## Setup Instructions

### 1. Access Grafana
- URL: http://localhost:3001
- Default credentials: admin/admin

### 2. Dashboard Import
Dashboards are automatically provisioned via the configuration files in this directory.

### 3. Data Source Configuration
The Prometheus data source is automatically configured via `provisioning/datasources/prometheus.yml`.

## Customization

### Adding New Dashboards
1. Create a new JSON file in `provisioning/dashboards/`
2. Follow the existing dashboard structure
3. Restart Grafana container to load the new dashboard

### Modifying Existing Dashboards
1. Edit dashboards in Grafana UI
2. Export the JSON
3. Replace the corresponding file in `provisioning/dashboards/`
4. Commit changes to version control

## Best Practices

### 1. Dashboard Design
- Keep dashboards focused on specific use cases
- Use consistent color schemes
- Include relevant time ranges
- Add helpful descriptions to panels

### 2. Query Optimization
- Use recording rules for complex queries
- Avoid high-cardinality labels
- Set appropriate refresh intervals
- Use query caching where possible

### 3. Alert Integration
- Link dashboards to relevant alerts
- Include runbook links in panel descriptions
- Use annotations to show alert events

## Troubleshooting

### Dashboard Not Loading
1. Check Grafana logs: `docker logs mams-grafana`
2. Verify Prometheus is accessible
3. Check dashboard JSON syntax

### No Data Showing
1. Verify Prometheus is scraping metrics
2. Check time range selection
3. Validate query syntax in Explore view

### Performance Issues
1. Reduce panel refresh rates
2. Optimize Prometheus queries
3. Consider using recording rules
4. Limit time ranges for heavy queries

## Dashboard URLs

Once running, dashboards are accessible at:
- System Overview: http://localhost:3001/d/mams-system-overview
- Service Metrics: http://localhost:3001/d/mams-service-metrics
- Business Metrics: http://localhost:3001/d/mams-business-metrics
- Infrastructure: http://localhost:3001/d/mams-infrastructure
- Alerts: http://localhost:3001/d/mams-alerts

## Maintenance

### Regular Tasks
1. Review and update alert thresholds
2. Archive old dashboard versions
3. Optimize slow queries
4. Update dashboards for new services

### Backup
Dashboard configurations are stored in version control. Additional backups can be created using Grafana's export feature.