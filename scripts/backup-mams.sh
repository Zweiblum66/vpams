#!/bin/bash
# MAMS Backup Script
# Backs up databases and critical data to /mnt/data/backups

set -e

# Configuration
BACKUP_DIR="/mnt/data/backups"
MAMS_DIR="/opt/mams"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_RETENTION_DAYS=30

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Create backup directory
create_backup_dir() {
    print_status "Creating backup directory..."
    mkdir -p "$BACKUP_DIR/$TIMESTAMP"
    cd "$BACKUP_DIR/$TIMESTAMP"
}

# Backup PostgreSQL
backup_postgres() {
    print_status "Backing up PostgreSQL databases..."
    
    cd $MAMS_DIR
    docker-compose -f docker-compose.production.yml exec -T postgres \
        pg_dumpall -U mams > "$BACKUP_DIR/$TIMESTAMP/postgres_backup.sql"
    
    # Compress the backup
    gzip "$BACKUP_DIR/$TIMESTAMP/postgres_backup.sql"
    
    print_status "PostgreSQL backup completed"
}

# Backup MongoDB
backup_mongodb() {
    print_status "Backing up MongoDB..."
    
    cd $MAMS_DIR
    docker-compose -f docker-compose.production.yml exec -T mongodb \
        mongodump --uri="mongodb://mams:${MONGO_ROOT_PASSWORD}@localhost:27017/?authSource=admin" \
        --archive=/tmp/mongodb_backup.gz --gzip
    
    # Copy backup from container
    docker cp mams-mongodb:/tmp/mongodb_backup.gz "$BACKUP_DIR/$TIMESTAMP/"
    
    # Clean up container
    docker-compose -f docker-compose.production.yml exec -T mongodb rm /tmp/mongodb_backup.gz
    
    print_status "MongoDB backup completed"
}

# Backup OpenSearch indices
backup_opensearch() {
    print_status "Backing up OpenSearch indices..."
    
    # Create snapshot repository if not exists
    curl -X PUT "http://localhost:9200/_snapshot/backup" \
        -H 'Content-Type: application/json' \
        -d "{
            \"type\": \"fs\",
            \"settings\": {
                \"location\": \"/backup\",
                \"compress\": true
            }
        }" 2>/dev/null || true
    
    # Create snapshot
    curl -X PUT "http://localhost:9200/_snapshot/backup/snapshot_$TIMESTAMP?wait_for_completion=true" \
        -H 'Content-Type: application/json' 2>/dev/null
    
    print_status "OpenSearch backup completed"
}

# Backup Redis
backup_redis() {
    print_status "Backing up Redis..."
    
    cd $MAMS_DIR
    docker-compose -f docker-compose.production.yml exec -T redis \
        redis-cli --rdb /tmp/redis_backup.rdb BGSAVE
    
    # Wait for backup to complete
    sleep 5
    
    # Copy backup from container
    docker cp mams-redis:/tmp/redis_backup.rdb "$BACKUP_DIR/$TIMESTAMP/"
    
    print_status "Redis backup completed"
}

# Backup configuration files
backup_configs() {
    print_status "Backing up configuration files..."
    
    # Create config backup directory
    mkdir -p "$BACKUP_DIR/$TIMESTAMP/configs"
    
    # Copy important config files
    cp $MAMS_DIR/.env "$BACKUP_DIR/$TIMESTAMP/configs/"
    cp $MAMS_DIR/docker-compose.production.yml "$BACKUP_DIR/$TIMESTAMP/configs/"
    cp -r $MAMS_DIR/nginx "$BACKUP_DIR/$TIMESTAMP/configs/"
    cp -r $MAMS_DIR/monitoring "$BACKUP_DIR/$TIMESTAMP/configs/"
    
    # Compress configs
    cd "$BACKUP_DIR/$TIMESTAMP"
    tar czf configs.tar.gz configs/
    rm -rf configs/
    
    print_status "Configuration backup completed"
}

# Clean old backups
cleanup_old_backups() {
    print_status "Cleaning up old backups..."
    
    find $BACKUP_DIR -type d -name "20*" -mtime +$BACKUP_RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
    
    print_status "Old backups cleaned"
}

# Create backup summary
create_summary() {
    print_status "Creating backup summary..."
    
    cat > "$BACKUP_DIR/$TIMESTAMP/backup_summary.txt" <<EOF
MAMS Backup Summary
==================
Timestamp: $TIMESTAMP
Date: $(date)
Server: $(hostname)

Backup Contents:
- PostgreSQL: postgres_backup.sql.gz
- MongoDB: mongodb_backup.gz
- Redis: redis_backup.rdb
- Configurations: configs.tar.gz

Backup Location: $BACKUP_DIR/$TIMESTAMP
Total Size: $(du -sh "$BACKUP_DIR/$TIMESTAMP" | cut -f1)

Retention Policy: $BACKUP_RETENTION_DAYS days
EOF
    
    # Also create a latest symlink
    cd $BACKUP_DIR
    rm -f latest
    ln -s $TIMESTAMP latest
}

# Main backup process
main() {
    print_status "=== Starting MAMS Backup ==="
    
    # Load environment variables
    if [ -f "$MAMS_DIR/.env" ]; then
        source "$MAMS_DIR/.env"
    fi
    
    create_backup_dir
    backup_postgres
    backup_mongodb
    backup_opensearch
    backup_redis
    backup_configs
    cleanup_old_backups
    create_summary
    
    print_status "=== Backup Completed Successfully ==="
    print_status "Backup location: $BACKUP_DIR/$TIMESTAMP"
    print_status "Total size: $(du -sh "$BACKUP_DIR/$TIMESTAMP" | cut -f1)"
}

# Run main function
main "$@"