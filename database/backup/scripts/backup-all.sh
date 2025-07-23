#!/bin/bash
# MAMS Database Backup Script
# Backs up all databases (PostgreSQL, MongoDB, Redis, OpenSearch)

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backup}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/logs/backup_${TIMESTAMP}.log"

# Docker container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-mams-postgres}"
MONGODB_CONTAINER="${MONGODB_CONTAINER:-mams-mongodb}"
REDIS_CONTAINER="${REDIS_CONTAINER:-mams-redis}"
OPENSEARCH_CONTAINER="${OPENSEARCH_CONTAINER:-mams-opensearch}"

# Database credentials
POSTGRES_USER="${POSTGRES_USER:-mams_app}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-mams_dev_password}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASSWORD="${MONGO_PASSWORD:-admin_password}"

# Create backup directories
mkdir -p "${BACKUP_DIR}/postgresql/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}/mongodb/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}/redis/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}/opensearch/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if Docker container is running
check_container() {
    local container_name=$1
    if ! docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        error_exit "Container ${container_name} is not running"
    fi
}

# PostgreSQL backup
backup_postgresql() {
    log "Starting PostgreSQL backup..."
    
    check_container "${POSTGRES_CONTAINER}"
    
    # List of databases to backup
    databases=("mams_users" "mams_assets" "mams_metadata" "mams_workflow" "mams_rights" "mams_audit")
    
    for db in "${databases[@]}"; do
        log "Backing up PostgreSQL database: ${db}"
        
        # Create compressed backup
        docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${db}" --clean --create --if-exists | \
            gzip > "${BACKUP_DIR}/postgresql/${TIMESTAMP}/${db}_${TIMESTAMP}.sql.gz"
        
        if [ $? -eq 0 ]; then
            log "Successfully backed up PostgreSQL database: ${db}"
        else
            error_exit "Failed to backup PostgreSQL database: ${db}"
        fi
    done
    
    # Create full cluster dump
    log "Creating PostgreSQL cluster dump..."
    docker exec "${POSTGRES_CONTAINER}" pg_dumpall -U "${POSTGRES_USER}" --clean | \
        gzip > "${BACKUP_DIR}/postgresql/${TIMESTAMP}/cluster_dump_${TIMESTAMP}.sql.gz"
    
    if [ $? -eq 0 ]; then
        log "Successfully created PostgreSQL cluster dump"
    else
        error_exit "Failed to create PostgreSQL cluster dump"
    fi
}

# MongoDB backup
backup_mongodb() {
    log "Starting MongoDB backup..."
    
    check_container "${MONGODB_CONTAINER}"
    
    # List of databases to backup
    databases=("mams_search" "mams_metadata" "mams_assets" "mams_ai" "mams_cache")
    
    for db in "${databases[@]}"; do
        log "Backing up MongoDB database: ${db}"
        
        # Create MongoDB dump
        docker exec "${MONGODB_CONTAINER}" mongodump \
            --username="${MONGO_USER}" \
            --password="${MONGO_PASSWORD}" \
            --authenticationDatabase=admin \
            --db="${db}" \
            --out="/tmp/backup_${TIMESTAMP}" \
            --gzip
        
        if [ $? -eq 0 ]; then
            # Copy from container to host
            docker cp "${MONGODB_CONTAINER}:/tmp/backup_${TIMESTAMP}/${db}" \
                "${BACKUP_DIR}/mongodb/${TIMESTAMP}/"
            
            # Clean up container
            docker exec "${MONGODB_CONTAINER}" rm -rf "/tmp/backup_${TIMESTAMP}"
            
            log "Successfully backed up MongoDB database: ${db}"
        else
            error_exit "Failed to backup MongoDB database: ${db}"
        fi
    done
    
    # Create full MongoDB dump
    log "Creating MongoDB full dump..."
    docker exec "${MONGODB_CONTAINER}" mongodump \
        --username="${MONGO_USER}" \
        --password="${MONGO_PASSWORD}" \
        --authenticationDatabase=admin \
        --out="/tmp/full_backup_${TIMESTAMP}" \
        --gzip
    
    if [ $? -eq 0 ]; then
        # Copy from container to host
        docker cp "${MONGODB_CONTAINER}:/tmp/full_backup_${TIMESTAMP}" \
            "${BACKUP_DIR}/mongodb/${TIMESTAMP}/full_backup"
        
        # Clean up container
        docker exec "${MONGODB_CONTAINER}" rm -rf "/tmp/full_backup_${TIMESTAMP}"
        
        log "Successfully created MongoDB full dump"
    else
        error_exit "Failed to create MongoDB full dump"
    fi
}

# Redis backup
backup_redis() {
    log "Starting Redis backup..."
    
    check_container "${REDIS_CONTAINER}"
    
    # Force Redis to save current dataset
    docker exec "${REDIS_CONTAINER}" redis-cli BGSAVE
    
    # Wait for background save to complete
    log "Waiting for Redis background save to complete..."
    while [ "$(docker exec "${REDIS_CONTAINER}" redis-cli LASTSAVE)" = "$(docker exec "${REDIS_CONTAINER}" redis-cli LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy RDB file
    docker cp "${REDIS_CONTAINER}:/data/dump.rdb" \
        "${BACKUP_DIR}/redis/${TIMESTAMP}/dump_${TIMESTAMP}.rdb"
    
    if [ $? -eq 0 ]; then
        # Compress the RDB file
        gzip "${BACKUP_DIR}/redis/${TIMESTAMP}/dump_${TIMESTAMP}.rdb"
        log "Successfully backed up Redis database"
    else
        error_exit "Failed to backup Redis database"
    fi
    
    # Also backup AOF if it exists
    if docker exec "${REDIS_CONTAINER}" test -f /data/appendonly.aof; then
        log "Backing up Redis AOF file..."
        docker cp "${REDIS_CONTAINER}:/data/appendonly.aof" \
            "${BACKUP_DIR}/redis/${TIMESTAMP}/appendonly_${TIMESTAMP}.aof"
        
        if [ $? -eq 0 ]; then
            gzip "${BACKUP_DIR}/redis/${TIMESTAMP}/appendonly_${TIMESTAMP}.aof"
            log "Successfully backed up Redis AOF file"
        else
            log "Warning: Failed to backup Redis AOF file"
        fi
    fi
}

# OpenSearch backup
backup_opensearch() {
    log "Starting OpenSearch backup..."
    
    check_container "${OPENSEARCH_CONTAINER}"
    
    # Create snapshot repository if it doesn't exist
    log "Setting up OpenSearch snapshot repository..."
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X PUT "localhost:9200/_snapshot/backup_repo" \
        -H 'Content-Type: application/json' \
        -d '{
            "type": "fs",
            "settings": {
                "location": "/usr/share/opensearch/backup",
                "compress": true
            }
        }' > /dev/null 2>&1
    
    # Create snapshot
    snapshot_name="backup_${TIMESTAMP}"
    log "Creating OpenSearch snapshot: ${snapshot_name}"
    
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X PUT "localhost:9200/_snapshot/backup_repo/${snapshot_name}" \
        -H 'Content-Type: application/json' \
        -d '{
            "indices": "mams-*",
            "include_global_state": false,
            "metadata": {
                "taken_by": "backup_script",
                "taken_because": "scheduled_backup"
            }
        }' > /dev/null
    
    if [ $? -eq 0 ]; then
        # Wait for snapshot to complete
        log "Waiting for OpenSearch snapshot to complete..."
        while true; do
            status=$(docker exec "${OPENSEARCH_CONTAINER}" curl -s "localhost:9200/_snapshot/backup_repo/${snapshot_name}" | \
                python3 -c "import sys, json; print(json.load(sys.stdin)['snapshots'][0]['state'])" 2>/dev/null)
            
            if [ "$status" = "SUCCESS" ]; then
                log "OpenSearch snapshot completed successfully"
                break
            elif [ "$status" = "FAILED" ]; then
                error_exit "OpenSearch snapshot failed"
            fi
            
            sleep 5
        done
        
        # Copy snapshot data from container
        docker cp "${OPENSEARCH_CONTAINER}:/usr/share/opensearch/backup" \
            "${BACKUP_DIR}/opensearch/${TIMESTAMP}/"
        
        if [ $? -eq 0 ]; then
            log "Successfully backed up OpenSearch data"
        else
            error_exit "Failed to copy OpenSearch backup data"
        fi
    else
        error_exit "Failed to create OpenSearch snapshot"
    fi
}

# Create backup manifest
create_manifest() {
    local manifest_file="${BACKUP_DIR}/backup_manifest_${TIMESTAMP}.json"
    
    log "Creating backup manifest..."
    
    cat > "${manifest_file}" << EOF
{
    "backup_timestamp": "${TIMESTAMP}",
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "1.0",
    "databases": {
        "postgresql": {
            "backup_path": "postgresql/${TIMESTAMP}",
            "databases": ["mams_users", "mams_assets", "mams_metadata", "mams_workflow", "mams_rights", "mams_audit"],
            "cluster_dump": "cluster_dump_${TIMESTAMP}.sql.gz"
        },
        "mongodb": {
            "backup_path": "mongodb/${TIMESTAMP}",
            "databases": ["mams_search", "mams_metadata", "mams_assets", "mams_ai", "mams_cache"],
            "full_dump": "full_backup"
        },
        "redis": {
            "backup_path": "redis/${TIMESTAMP}",
            "rdb_file": "dump_${TIMESTAMP}.rdb.gz",
            "aof_file": "appendonly_${TIMESTAMP}.aof.gz"
        },
        "opensearch": {
            "backup_path": "opensearch/${TIMESTAMP}",
            "snapshot_name": "backup_${TIMESTAMP}",
            "indices": ["mams-assets", "mams-metadata", "mams-audit-logs", "mams-search-analytics"]
        }
    },
    "system_info": {
        "hostname": "$(hostname)",
        "backup_script_version": "1.0",
        "docker_version": "$(docker --version)",
        "disk_usage": "$(df -h ${BACKUP_DIR} | tail -1 | awk '{print $5}')"
    }
}
EOF
    
    log "Backup manifest created: ${manifest_file}"
}

# Calculate backup sizes
calculate_sizes() {
    log "Calculating backup sizes..."
    
    for db_type in postgresql mongodb redis opensearch; do
        size=$(du -sh "${BACKUP_DIR}/${db_type}/${TIMESTAMP}" 2>/dev/null | cut -f1)
        log "${db_type} backup size: ${size:-0}"
    done
    
    total_size=$(du -sh "${BACKUP_DIR}/postgresql/${TIMESTAMP}" "${BACKUP_DIR}/mongodb/${TIMESTAMP}" \
        "${BACKUP_DIR}/redis/${TIMESTAMP}" "${BACKUP_DIR}/opensearch/${TIMESTAMP}" 2>/dev/null | \
        awk '{total += $1} END {print total}')
    
    log "Total backup size: ${total_size:-0}"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # Find and remove old backup directories
    find "${BACKUP_DIR}/postgresql" -maxdepth 1 -type d -name "*_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
    find "${BACKUP_DIR}/mongodb" -maxdepth 1 -type d -name "*_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
    find "${BACKUP_DIR}/redis" -maxdepth 1 -type d -name "*_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
    find "${BACKUP_DIR}/opensearch" -maxdepth 1 -type d -name "*_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
    
    # Remove old manifest files
    find "${BACKUP_DIR}" -name "backup_manifest_*.json" -mtime +${RETENTION_DAYS} -delete
    
    # Remove old log files
    find "${BACKUP_DIR}/logs" -name "backup_*.log" -mtime +${RETENTION_DAYS} -delete
    
    log "Cleanup completed"
}

# Main backup function
main() {
    log "Starting MAMS database backup process..."
    log "Backup directory: ${BACKUP_DIR}"
    log "Retention period: ${RETENTION_DAYS} days"
    
    # Create backup directory if it doesn't exist
    mkdir -p "${BACKUP_DIR}"
    
    # Check disk space
    available_space=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $4}')
    if [ "${available_space}" -lt 1048576 ]; then  # Less than 1GB
        error_exit "Insufficient disk space for backup (less than 1GB available)"
    fi
    
    # Start timer
    start_time=$(date +%s)
    
    # Perform backups
    backup_postgresql
    backup_mongodb
    backup_redis
    backup_opensearch
    
    # Create manifest and calculate sizes
    create_manifest
    calculate_sizes
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Calculate elapsed time
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    
    log "Backup process completed successfully in ${elapsed} seconds"
    log "Backup location: ${BACKUP_DIR}"
    log "Backup timestamp: ${TIMESTAMP}"
    
    # Create success marker
    touch "${BACKUP_DIR}/backup_${TIMESTAMP}_SUCCESS"
}

# Handle signals
trap 'error_exit "Backup interrupted by signal"' INT TERM

# Run main function
main "$@"