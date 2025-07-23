# Module 5: System Administration

## Duration: 6 hours

## Learning Objectives
By the end of this module, trainees will be able to:
1. Perform basic system administration tasks
2. Manage user accounts and permissions
3. Configure system settings
4. Monitor system performance
5. Perform routine maintenance
6. Handle backup and recovery operations

## 1. Administrative Access Levels

### Support Team Access
```yaml
Level 1 Support:
  - Read-only access to logs
  - View user information
  - Reset passwords
  - View system status

Level 2 Support:
  - All Level 1 permissions
  - Modify user roles
  - Adjust quotas
  - Configure integrations
  - Restart services

Level 3 Support:
  - All Level 2 permissions
  - Database modifications
  - System configuration
  - Infrastructure access
  - Full admin rights
```

### Admin Interface Access
URL: https://mams.company.com/admin
Login: Use your support credentials with MFA

Main sections:
- Dashboard: System overview
- Users: Account management
- System: Configuration
- Storage: Quota management
- Monitoring: Performance metrics
- Audit: Activity logs

## 2. User Management

### Creating User Accounts

#### Via Admin UI
1. Navigate to Users → Add User
2. Fill in required fields:
   - Email (unique)
   - Full Name
   - Organization
   - Role
   - Storage Quota
3. Set initial password or send invite
4. Configure permissions
5. Save and notify user

#### Via API
```bash
curl -X POST https://api.mams.com/v1/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@company.com",
    "name": "John Smith",
    "role": "editor",
    "quota_gb": 100,
    "send_invite": true
  }'
```

### Managing Roles and Permissions

#### Default Roles
```json
{
  "admin": {
    "description": "Full system access",
    "permissions": ["*"]
  },
  "editor": {
    "description": "Create and modify content",
    "permissions": [
      "asset.create", "asset.read", "asset.update", "asset.delete",
      "project.create", "project.read", "project.update",
      "workflow.create", "workflow.execute"
    ]
  },
  "viewer": {
    "description": "Read-only access",
    "permissions": [
      "asset.read", "project.read", "metadata.read"
    ]
  },
  "guest": {
    "description": "Limited temporary access",
    "permissions": ["asset.read:shared"]
  }
}
```

#### Creating Custom Roles
```sql
-- Create new role
INSERT INTO roles (name, description, permissions)
VALUES ('producer', 'Production team member', 
  '["asset.*", "project.*", "workflow.execute"]');

-- Assign role to user
INSERT INTO user_roles (user_id, role_id)
VALUES ('user-uuid', 'role-uuid');
```

### Account Maintenance

#### Bulk Operations
```python
# Disable inactive users
UPDATE users 
SET status = 'disabled' 
WHERE last_login < NOW() - INTERVAL '90 days';

# Reset quotas for organization
UPDATE users 
SET quota_bytes = 107374182400  -- 100GB
WHERE organization_id = 'org-uuid';

# Export user list
SELECT email, name, role, last_login, storage_used
FROM users
WHERE status = 'active'
ORDER BY organization_id, name;
```

## 3. System Configuration

### Core Settings

#### Via Environment Variables
```bash
# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRATION_MINUTES=60
MFA_REQUIRED=true
SESSION_TIMEOUT_MINUTES=30

# Storage
DEFAULT_STORAGE_TIER=hot
STORAGE_QUOTA_DEFAULT_GB=50
ENABLE_DEDUPLICATION=true

# Performance
MAX_UPLOAD_SIZE_GB=100
CONCURRENT_UPLOADS=5
WORKER_PROCESSES=4
CACHE_TTL_SECONDS=3600
```

#### Via Configuration API
```bash
# View current settings
curl https://api.mams.com/v1/admin/config \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Update setting
curl -X PUT https://api.mams.com/v1/admin/config/upload_limit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"value": "104857600000"}'  # 100GB in bytes
```

### Feature Flags
```yaml
features:
  ai_tagging:
    enabled: true
    models: ["general", "facial", "scene"]
  
  auto_transcription:
    enabled: true
    languages: ["en", "es", "fr", "de"]
  
  advanced_search:
    visual_similarity: true
    semantic_search: true
    natural_language: false  # Beta
  
  integrations:
    adobe_premiere: true
    avid: true
    davinci: false  # Coming soon
```

### Email Configuration
```yaml
email:
  smtp_host: smtp.sendgrid.net
  smtp_port: 587
  smtp_user: apikey
  smtp_password: ${SENDGRID_API_KEY}
  from_address: noreply@mams.com
  from_name: MAMS Support
  
templates:
  welcome: /templates/welcome.html
  password_reset: /templates/reset.html
  quota_warning: /templates/quota.html
```

## 4. Storage Management

### Storage Tier Configuration
```yaml
tiers:
  hot:
    type: local_ssd
    path: /mnt/ssd/hot
    capacity: 10TB
    retention: 30d
    cost_per_gb: 0.10
  
  warm:
    type: local_hdd
    path: /mnt/hdd/warm
    capacity: 100TB
    retention: 90d
    cost_per_gb: 0.03
  
  cold:
    type: s3
    bucket: mams-cold-storage
    retention: 365d
    cost_per_gb: 0.01
  
  archive:
    type: glacier
    vault: mams-archive
    retention: indefinite
    cost_per_gb: 0.004
```

### Quota Management
```sql
-- Check storage usage
SELECT 
  u.email,
  u.quota_bytes / 1073741824 as quota_gb,
  COALESCE(SUM(a.size_bytes), 0) / 1073741824 as used_gb,
  (COALESCE(SUM(a.size_bytes), 0)::float / u.quota_bytes * 100) as percent_used
FROM users u
LEFT JOIN assets a ON a.owner_id = u.id
GROUP BY u.id
HAVING percent_used > 80
ORDER BY percent_used DESC;

-- Increase quota for user
UPDATE users 
SET quota_bytes = quota_bytes + 53687091200  -- Add 50GB
WHERE email = 'user@company.com';
```

### Storage Cleanup
```bash
# Find orphaned files
./scripts/find-orphans.sh

# Remove expired proxies
DELETE FROM proxies 
WHERE created_at < NOW() - INTERVAL '30 days'
AND quality = 'low';

# Archive old assets
./scripts/archive-assets.sh --older-than 365 --tier archive

# Cleanup temp files
find /tmp/mams-upload -mtime +1 -delete
```

## 5. System Monitoring

### Key Metrics Dashboard

#### System Health
```bash
# Check all services
docker-compose ps

# Service health endpoints
for service in api-gateway user-mgmt storage asset search; do
  echo "Checking $service..."
  curl -s http://$service:8000/health | jq .
done

# Database connections
SELECT count(*) as connections, 
       state, 
       wait_event_type 
FROM pg_stat_activity 
GROUP BY state, wait_event_type;
```

#### Performance Metrics
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Storage usage
mams_storage_used_bytes / mams_storage_total_bytes
```

### Alert Configuration
```yaml
alerts:
  - name: HighErrorRate
    expr: error_rate > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      
  - name: StorageNearCapacity
    expr: storage_usage_percent > 85
    for: 15m
    labels:
      severity: critical
    annotations:
      summary: "Storage capacity critical"
      
  - name: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.service }} is down"
```

## 6. Backup and Recovery

### Backup Strategy

#### Database Backups
```bash
# PostgreSQL backup
pg_dump -h postgres -U mams_user mams_db > backup_$(date +%Y%m%d).sql

# MongoDB backup
mongodump --uri mongodb://mongo:27017/mams --out /backup/mongo_$(date +%Y%m%d)

# Redis backup
redis-cli --rdb /backup/redis_$(date +%Y%m%d).rdb

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup all databases
for db in postgres mongo redis; do
  echo "Backing up $db..."
  docker exec mams-$db backup.sh $BACKUP_DIR
done

# Upload to S3
aws s3 sync $BACKUP_DIR s3://mams-backups/$(date +%Y%m%d)/
```

#### Asset Backup
```yaml
backup_policy:
  hot_tier:
    frequency: daily
    retention: 7d
    method: incremental
    
  warm_tier:
    frequency: weekly
    retention: 30d
    method: incremental
    
  cold_tier:
    frequency: monthly
    retention: 365d
    method: full
```

### Recovery Procedures

#### Database Recovery
```bash
# Restore PostgreSQL
psql -h postgres -U mams_user mams_db < backup_20240115.sql

# Restore MongoDB
mongorestore --uri mongodb://mongo:27017/mams /backup/mongo_20240115

# Restore Redis
redis-cli --pipe < backup_20240115.rdb
```

#### Disaster Recovery Plan
1. **Assess damage scope**
2. **Activate DR site if needed**
3. **Restore databases from backup**
4. **Verify data integrity**
5. **Restore asset files**
6. **Update DNS if failover**
7. **Test all services**
8. **Notify stakeholders**

## 7. Security Administration

### Access Control
```bash
# Review admin users
SELECT u.email, r.name as role, u.last_login
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE r.name = 'admin'
ORDER BY u.last_login DESC;

# Audit permissions
SELECT 
  r.name as role,
  array_agg(p.name) as permissions
FROM roles r
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
GROUP BY r.name;
```

### Security Monitoring
```sql
-- Failed login attempts
SELECT 
  email,
  ip_address,
  COUNT(*) as attempts,
  MAX(attempted_at) as last_attempt
FROM login_attempts
WHERE successful = false
AND attempted_at > NOW() - INTERVAL '24 hours'
GROUP BY email, ip_address
HAVING COUNT(*) > 5;

-- Suspicious activity
SELECT 
  user_id,
  action,
  COUNT(*) as count
FROM audit_log
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY user_id, action
HAVING COUNT(*) > 100;
```

## 8. Routine Maintenance

### Daily Tasks
- [ ] Check system health dashboard
- [ ] Review error logs
- [ ] Monitor storage usage
- [ ] Verify backup completion
- [ ] Check service performance

### Weekly Tasks
- [ ] Review user access reports
- [ ] Clean temporary files
- [ ] Update system statistics
- [ ] Test backup restoration
- [ ] Review security alerts

### Monthly Tasks
- [ ] Audit user permissions
- [ ] Archive old logs
- [ ] Update documentation
- [ ] Performance optimization
- [ ] Security patches

### Maintenance Scripts
```bash
#!/bin/bash
# maintenance.sh - Run weekly

echo "Starting weekly maintenance..."

# 1. Clean temp files
find /tmp -name "mams-*" -mtime +7 -delete

# 2. Vacuum databases
docker exec mams-postgres vacuumdb -a -z

# 3. Rotate logs
logrotate /etc/logrotate.d/mams

# 4. Update statistics
docker exec mams-postgres analyze;

# 5. Clear old sessions
redis-cli --scan --pattern "session:*" | \
  xargs -L 1 redis-cli TTL | \
  grep -v "-1" | \
  xargs -L 1 redis-cli DEL

echo "Maintenance completed"
```

## 9. Troubleshooting Admin Issues

### Common Admin Problems

#### Problem: Cannot Access Admin Panel
```bash
# Check admin role
SELECT * FROM user_roles WHERE user_id = 'your-user-id';

# Verify MFA status
SELECT mfa_enabled FROM users WHERE id = 'your-user-id';

# Check IP whitelist
SELECT * FROM admin_ip_whitelist;
```

#### Problem: Bulk Operation Timeout
```sql
-- Use batches for large operations
DO $$
DECLARE
  batch_size INT := 1000;
  offset_val INT := 0;
BEGIN
  LOOP
    UPDATE users 
    SET status = 'active'
    WHERE id IN (
      SELECT id FROM users 
      WHERE status = 'pending'
      LIMIT batch_size
      OFFSET offset_val
    );
    
    EXIT WHEN NOT FOUND;
    offset_val := offset_val + batch_size;
    
    -- Pause between batches
    PERFORM pg_sleep(1);
  END LOOP;
END $$;
```

## Hands-On Exercises

### Exercise 1: User Management (45 min)
1. Create 5 test users with different roles
2. Modify permissions for one user
3. Disable inactive accounts
4. Generate user activity report
5. Reset passwords in bulk

### Exercise 2: System Configuration (45 min)
1. View current system settings
2. Update upload limits
3. Configure email templates
4. Enable/disable features
5. Test configuration changes

### Exercise 3: Monitoring Setup (30 min)
1. Access Grafana dashboards
2. Create custom metric query
3. Set up test alert
4. Investigate performance issue
5. Generate system report

### Exercise 4: Backup and Recovery (60 min)
1. Perform manual backup
2. Verify backup integrity
3. Simulate data loss
4. Execute recovery procedure
5. Verify recovered data

## Administrative Best Practices

### Documentation
- Document all changes
- Maintain runbooks
- Update procedures
- Track known issues
- Share knowledge

### Change Management
1. Test in staging first
2. Schedule maintenance windows
3. Notify users in advance
4. Have rollback plan
5. Monitor after changes

### Security
- Use MFA for admin access
- Audit admin actions
- Rotate credentials
- Limit admin privileges
- Monitor suspicious activity

## Summary

In this module, you learned:
- User and role management
- System configuration options
- Storage administration
- Monitoring and alerting
- Backup and recovery procedures
- Security best practices
- Routine maintenance tasks

Next Module: [Advanced Troubleshooting](./06-advanced-troubleshooting.md)