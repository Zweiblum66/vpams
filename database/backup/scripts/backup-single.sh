#!/bin/bash
# MAMS Single Database Backup Script
# Backs up a single database type

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backup}"
DATABASE_TYPE="${1:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/logs/backup_${DATABASE_TYPE}_${TIMESTAMP}.log"

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

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Usage
usage() {
    echo "Usage: $0 <database_type>"
    echo "  database_type: postgresql, mongodb, redis, opensearch"
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
    
    mkdir -p "${BACKUP_DIR}/postgresql/${TIMESTAMP}"
    
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
    
    log "PostgreSQL backup completed"
}

# MongoDB backup
backup_mongodb() {
    log "Starting MongoDB backup..."
    
    check_container "${MONGODB_CONTAINER}"
    
    mkdir -p "${BACKUP_DIR}/mongodb/${TIMESTAMP}"
    
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
            
            log "Successfully backed up MongoDB database: ${db}"
        else
            error_exit "Failed to backup MongoDB database: ${db}"
        fi
    done
    
    # Clean up container
    docker exec "${MONGODB_CONTAINER}" rm -rf "/tmp/backup_${TIMESTAMP}"
    
    log "MongoDB backup completed"
}

# Redis backup
backup_redis() {
    log "Starting Redis backup..."
    
    check_container "${REDIS_CONTAINER}"
    
    mkdir -p "${BACKUP_DIR}/redis/${TIMESTAMP}"
    
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
        log "Successfully backed up Redis RDB file"
    else
        error_exit "Failed to backup Redis RDB file"
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
    
    log "Redis backup completed"
}

# OpenSearch backup
backup_opensearch() {
    log "Starting OpenSearch backup..."
    
    check_container "${OPENSEARCH_CONTAINER}"
    
    mkdir -p "${BACKUP_DIR}/opensearch/${TIMESTAMP}"
    
    # Create snapshot repository if it doesn't exist
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
            "include_global_state": false
        }' > /dev/null
    
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
    
    log "OpenSearch backup completed"
}

# Main function
main() {
    if [ -z "${DATABASE_TYPE}" ]; then
        usage
    fi
    
    case "${DATABASE_TYPE}" in
        postgresql)
            backup_postgresql
            ;;
        mongodb)
            backup_mongodb
            ;;
        redis)
            backup_redis
            ;;
        opensearch)
            backup_opensearch
            ;;
        *)
            error_exit "Invalid database type: ${DATABASE_TYPE}"
            ;;
    esac
    
    # Calculate backup size
    backup_size=$(du -sh "${BACKUP_DIR}/${DATABASE_TYPE}/${TIMESTAMP}" 2>/dev/null | cut -f1)
    log "${DATABASE_TYPE} backup completed successfully"
    log "Backup size: ${backup_size:-0}"
    log "Backup location: ${BACKUP_DIR}/${DATABASE_TYPE}/${TIMESTAMP}"
    
    # Create success marker
    touch "${BACKUP_DIR}/${DATABASE_TYPE}_backup_${TIMESTAMP}_SUCCESS"
}

# Handle signals
trap 'error_exit "Backup interrupted by signal"' INT TERM

# Create log directory
mkdir -p "${BACKUP_DIR}/logs"

# Run main function
main "$@"