# MAMS Database Backup System

This directory contains the comprehensive backup and restore system for all MAMS databases.

## Overview

The backup system provides:

- **Automated Backups**: Scheduled backups for all databases
- **Individual Database Backups**: Backup specific databases on demand
- **Complete Restore**: Full system restore from backups
- **Monitoring**: Backup health monitoring and alerting
- **Retention Management**: Automatic cleanup of old backups
- **Disaster Recovery**: Complete disaster recovery procedures

## Supported Databases

- **PostgreSQL**: All 6 MAMS databases with schema and data
- **MongoDB**: All 5 collections with indexes and validation
- **Redis**: Memory snapshots (RDB) and append-only files (AOF)
- **OpenSearch**: Index snapshots with mappings and data

## Quick Start

### 1. Create Backup Directory
```bash
sudo mkdir -p /opt/mams/backup
sudo chown -R $(id -u):$(id -g) /opt/mams/backup
```

### 2. Set Environment Variables
```bash
export BACKUP_DIR="/opt/mams/backup"
export RETENTION_DAYS="7"
```

### 3. Run Full Backup
```bash
cd database/backup
./scripts/backup-all.sh
```

### 4. List Available Backups
```bash
ls -la /opt/mams/backup/
```

### 5. Restore from Backup
```bash
./scripts/restore-all.sh 20241216_143000
```

## Backup Scripts

### Full System Backup
```bash
# Backup all databases
./scripts/backup-all.sh

# With custom settings
BACKUP_DIR=/custom/path RETENTION_DAYS=30 ./scripts/backup-all.sh
```

### Individual Database Backup
```bash
# Backup PostgreSQL only
./scripts/backup-single.sh postgresql

# Backup MongoDB only
./scripts/backup-single.sh mongodb

# Backup Redis only
./scripts/backup-single.sh redis

# Backup OpenSearch only
./scripts/backup-single.sh opensearch
```

### Restore Operations
```bash
# Restore all databases
./scripts/restore-all.sh 20241216_143000

# List available backups
./scripts/restore-all.sh
```

## Backup Directory Structure

```
/opt/mams/backup/
├── postgresql/
│   ├── 20241216_143000/
│   │   ├── mams_users_20241216_143000.sql.gz
│   │   ├── mams_assets_20241216_143000.sql.gz
│   │   └── cluster_dump_20241216_143000.sql.gz
│   └── 20241216_150000/
├── mongodb/
│   ├── 20241216_143000/
│   │   ├── mams_search/
│   │   ├── mams_metadata/
│   │   └── full_backup/
│   └── 20241216_150000/
├── redis/
│   ├── 20241216_143000/
│   │   ├── dump_20241216_143000.rdb.gz
│   │   └── appendonly_20241216_143000.aof.gz
│   └── 20241216_150000/
├── opensearch/
│   ├── 20241216_143000/
│   │   └── backup/
│   └── 20241216_150000/
├── logs/
│   ├── backup_20241216_143000.log
│   └── restore_20241216_143000.log
├── backup_manifest_20241216_143000.json
└── backup_20241216_143000_SUCCESS
```

## Automated Scheduling

### Cron Setup
```bash
# Edit crontab
crontab -e

# Add backup schedules
# Daily full backup at 2 AM
0 2 * * * /path/to/mams/database/backup/scripts/backup-all.sh

# Hourly PostgreSQL backup
0 * * * * /path/to/mams/database/backup/scripts/backup-single.sh postgresql

# Every 4 hours Redis backup
0 */4 * * * /path/to/mams/database/backup/scripts/backup-single.sh redis
```

### Docker Compose Scheduler
```bash
# Start backup scheduler
cd database/backup/docker
docker-compose -f docker-compose.backup.yml up -d

# View scheduler logs
docker-compose -f docker-compose.backup.yml logs -f backup-scheduler
```

## Configuration

### Environment Variables
```bash
# Backup directory
export BACKUP_DIR="/opt/mams/backup"

# Retention period
export RETENTION_DAYS="7"

# Database containers
export POSTGRES_CONTAINER="mams-postgres"
export MONGODB_CONTAINER="mams-mongodb"
export REDIS_CONTAINER="mams-redis"
export OPENSEARCH_CONTAINER="mams-opensearch"

# Database credentials
export POSTGRES_USER="mams_app"
export POSTGRES_PASSWORD="mams_dev_password"
export MONGO_USER="admin"
export MONGO_PASSWORD="admin_password"
```

### Backup Schedule Configuration
Edit `config/backup-schedule.yml` to customize:
- Backup frequencies
- Retention periods
- Notification settings
- Environment-specific settings

## Monitoring and Alerting

### Health Checks
```bash
# Check backup health
curl http://localhost:9091/health

# Check backup metrics
curl http://localhost:9091/metrics

# View backup status
curl http://localhost:9091/status
```

### Web Interface
Access the backup web interface at: http://localhost:8080

Features:
- View backup history
- Monitor backup status
- Download backups
- Schedule manual backups
- View logs and metrics

## Disaster Recovery

### Recovery Time Objective (RTO)
- **Target**: 30 minutes
- **Components**: Database restore, application startup, validation

### Recovery Point Objective (RPO)
- **Target**: 1 hour
- **Method**: Continuous backup with 1-hour intervals

### Recovery Procedures

1. **Assess Damage**
   ```bash
   # Check database status
   docker ps
   docker logs mams-postgres
   docker logs mams-mongodb
   ```

2. **Stop Services**
   ```bash
   docker-compose down
   ```

3. **Restore Databases**
   ```bash
   # Find latest backup
   ls -la /opt/mams/backup/backup_manifest_*.json | tail -1
   
   # Restore from backup
   ./scripts/restore-all.sh 20241216_143000
   ```

4. **Verify Restoration**
   ```bash
   # Check data integrity
   docker exec mams-postgres psql -U mams_app -d mams_users -c "SELECT COUNT(*) FROM users;"
   docker exec mams-mongodb mongosh --eval "db.getMongo().getDBNames()"
   ```

5. **Restart Services**
   ```bash
   docker-compose up -d
   ```

## Backup Verification

### Automatic Verification
The backup system includes automatic verification:
- File integrity checks
- Database connection tests
- Sample data validation
- Backup size verification

### Manual Verification
```bash
# Test PostgreSQL backup
zcat /opt/mams/backup/postgresql/20241216_143000/mams_users_20241216_143000.sql.gz | head -20

# Test MongoDB backup
ls -la /opt/mams/backup/mongodb/20241216_143000/

# Test Redis backup
file /opt/mams/backup/redis/20241216_143000/dump_20241216_143000.rdb.gz

# Test OpenSearch backup
ls -la /opt/mams/backup/opensearch/20241216_143000/backup/
```

## Security Considerations

### Backup Encryption
```bash
# Enable GPG encryption
export BACKUP_ENCRYPTION=true
export GPG_KEY_ID="backup@mams.com"

# Generate GPG key
gpg --full-generate-key
```

### Access Control
```bash
# Restrict backup directory access
chmod 700 /opt/mams/backup
chown -R mams:mams /opt/mams/backup
```

### Network Security
- Use VPN for remote backup access
- Implement firewall rules
- Use secure protocols (HTTPS, SSH)

## Troubleshooting

### Common Issues

1. **Backup Fails**
   ```bash
   # Check container status
   docker ps
   
   # Check logs
   tail -f /opt/mams/backup/logs/backup_*.log
   
   # Check disk space
   df -h /opt/mams/backup
   ```

2. **Restore Fails**
   ```bash
   # Check backup integrity
   ls -la /opt/mams/backup/backup_*_SUCCESS
   
   # Verify backup files
   file /opt/mams/backup/postgresql/*/mams_users_*.sql.gz
   ```

3. **Permission Errors**
   ```bash
   # Fix permissions
   sudo chown -R $(id -u):$(id -g) /opt/mams/backup
   chmod +x scripts/*.sh
   ```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true

# Run with verbose output
./scripts/backup-all.sh 2>&1 | tee backup-debug.log
```

## Performance Optimization

### Backup Performance
- Use compression to reduce backup size
- Schedule backups during low-traffic hours
- Use incremental backups for large databases
- Implement parallel backup processes

### Storage Optimization
- Use LVM snapshots for consistent backups
- Implement tiered storage (hot/warm/cold)
- Use deduplication for repeated data
- Compress old backups

## Compliance and Auditing

### Audit Trail
- All backup operations are logged
- Backup manifests include metadata
- Restore operations are tracked
- Access to backups is monitored

### Compliance Features
- GDPR-compliant data handling
- Configurable retention policies
- Secure deletion of expired backups
- Audit log retention

## Migration and Upgrades

### Database Migration
```bash
# Backup before migration
./scripts/backup-all.sh

# Run migration
cd ../migrations
python scripts/migrate.py upgrade

# Verify migration
python scripts/migrate.py status
```

### System Upgrades
```bash
# Pre-upgrade backup
./scripts/backup-all.sh

# Post-upgrade verification
./scripts/verify-backup.sh
```

This comprehensive backup system ensures data protection, disaster recovery capabilities, and operational continuity for the MAMS platform.