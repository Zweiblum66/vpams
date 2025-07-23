#!/bin/bash
# MAMS Database Restore Script
# Restores all databases from backup

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backup}"
TIMESTAMP="${1:-}"
LOG_FILE="${BACKUP_DIR}/logs/restore_$(date +%Y%m%d_%H%M%S).log"

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

# Check if Docker container is running
check_container() {
    local container_name=$1
    if ! docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        error_exit "Container ${container_name} is not running"
    fi
}

# Show available backups
show_available_backups() {
    log "Available backups:"
    
    find "${BACKUP_DIR}" -name "backup_manifest_*.json" -type f | sort -r | head -10 | while read -r manifest; do
        timestamp=$(basename "${manifest}" .json | sed 's/backup_manifest_//')
        backup_date=$(jq -r '.backup_date' "${manifest}" 2>/dev/null || echo "Unknown")
        
        echo "  ${timestamp} (${backup_date})"
    done
}

# Validate backup
validate_backup() {
    local timestamp=$1
    local manifest_file="${BACKUP_DIR}/backup_manifest_${timestamp}.json"
    
    if [ ! -f "${manifest_file}" ]; then
        error_exit "Backup manifest not found: ${manifest_file}"
    fi
    
    # Check if backup directories exist
    for db_type in postgresql mongodb redis opensearch; do
        backup_path="${BACKUP_DIR}/${db_type}/${timestamp}"
        if [ ! -d "${backup_path}" ]; then
            error_exit "Backup directory not found: ${backup_path}"
        fi
    done
    
    # Check success marker
    if [ ! -f "${BACKUP_DIR}/backup_${timestamp}_SUCCESS" ]; then
        log "WARNING: Backup success marker not found for ${timestamp}"
        if ! confirm "Continue with potentially incomplete backup?"; then
            exit 1
        fi
    fi
    
    log "Backup validation passed for timestamp: ${timestamp}"
}

# Confirmation prompt
confirm() {
    local prompt="$1"
    read -p "${prompt} (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Stop services before restore
stop_services() {
    log "Stopping services before restore..."
    
    # This would typically stop application services
    # For development, we'll just log the action
    log "Services stopped (placeholder for production implementation)"
}

# Start services after restore
start_services() {
    log "Starting services after restore..."
    
    # This would typically start application services
    # For development, we'll just log the action
    log "Services started (placeholder for production implementation)"
}

# PostgreSQL restore
restore_postgresql() {
    local timestamp=$1
    
    log "Starting PostgreSQL restore..."
    
    check_container "${POSTGRES_CONTAINER}"
    
    # List of databases to restore
    databases=("mams_users" "mams_assets" "mams_metadata" "mams_workflow" "mams_rights" "mams_audit")
    
    for db in "${databases[@]}"; do
        backup_file="${BACKUP_DIR}/postgresql/${timestamp}/${db}_${timestamp}.sql.gz"
        
        if [ ! -f "${backup_file}" ]; then
            error_exit "PostgreSQL backup file not found: ${backup_file}"
        fi
        
        log "Restoring PostgreSQL database: ${db}"
        
        # Drop and recreate database
        docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${db};"
        docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${db};"
        
        # Restore from backup
        zcat "${backup_file}" | docker exec -i "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${db}"
        
        if [ $? -eq 0 ]; then
            log "Successfully restored PostgreSQL database: ${db}"
        else
            error_exit "Failed to restore PostgreSQL database: ${db}"
        fi
    done
    
    log "PostgreSQL restore completed"
}

# MongoDB restore
restore_mongodb() {
    local timestamp=$1
    
    log "Starting MongoDB restore..."
    
    check_container "${MONGODB_CONTAINER}"
    
    # List of databases to restore
    databases=("mams_search" "mams_metadata" "mams_assets" "mams_ai" "mams_cache")
    
    for db in "${databases[@]}"; do
        backup_dir="${BACKUP_DIR}/mongodb/${timestamp}/${db}"
        
        if [ ! -d "${backup_dir}" ]; then
            error_exit "MongoDB backup directory not found: ${backup_dir}"
        fi
        
        log "Restoring MongoDB database: ${db}"
        
        # Drop existing database
        docker exec "${MONGODB_CONTAINER}" mongosh \
            --username="${MONGO_USER}" \
            --password="${MONGO_PASSWORD}" \
            --authenticationDatabase=admin \
            --eval "db.getSiblingDB('${db}').dropDatabase()"
        
        # Copy backup to container
        docker cp "${backup_dir}" "${MONGODB_CONTAINER}:/tmp/restore_${db}"
        
        # Restore from backup
        docker exec "${MONGODB_CONTAINER}" mongorestore \
            --username="${MONGO_USER}" \
            --password="${MONGO_PASSWORD}" \
            --authenticationDatabase=admin \
            --db="${db}" \
            --gzip \
            "/tmp/restore_${db}"
        
        if [ $? -eq 0 ]; then
            # Clean up container
            docker exec "${MONGODB_CONTAINER}" rm -rf "/tmp/restore_${db}"
            log "Successfully restored MongoDB database: ${db}"
        else
            error_exit "Failed to restore MongoDB database: ${db}"
        fi
    done
    
    log "MongoDB restore completed"
}

# Redis restore
restore_redis() {
    local timestamp=$1
    
    log "Starting Redis restore..."
    
    check_container "${REDIS_CONTAINER}"
    
    # Check for RDB backup
    rdb_file="${BACKUP_DIR}/redis/${timestamp}/dump_${timestamp}.rdb.gz"
    
    if [ ! -f "${rdb_file}" ]; then
        error_exit "Redis RDB backup file not found: ${rdb_file}"
    fi
    
    log "Restoring Redis from RDB file..."
    
    # Stop Redis temporarily
    docker exec "${REDIS_CONTAINER}" redis-cli SHUTDOWN NOSAVE || true
    
    # Wait for Redis to stop
    sleep 5
    
    # Copy RDB file to container
    zcat "${rdb_file}" | docker exec -i "${REDIS_CONTAINER}" sh -c 'cat > /data/dump.rdb'
    
    # Restart Redis container
    docker restart "${REDIS_CONTAINER}"
    
    # Wait for Redis to start
    sleep 10
    
    # Verify Redis is running
    if docker exec "${REDIS_CONTAINER}" redis-cli ping > /dev/null 2>&1; then
        log "Successfully restored Redis database"
    else
        error_exit "Failed to restore Redis database"
    fi
    
    # Restore AOF if it exists
    aof_file="${BACKUP_DIR}/redis/${timestamp}/appendonly_${timestamp}.aof.gz"
    if [ -f "${aof_file}" ]; then
        log "Restoring Redis AOF file..."
        zcat "${aof_file}" | docker exec -i "${REDIS_CONTAINER}" sh -c 'cat > /data/appendonly.aof'
        log "Redis AOF file restored"
    fi
    
    log "Redis restore completed"
}

# OpenSearch restore
restore_opensearch() {
    local timestamp=$1
    
    log "Starting OpenSearch restore..."
    
    check_container "${OPENSEARCH_CONTAINER}"
    
    backup_dir="${BACKUP_DIR}/opensearch/${timestamp}/backup"
    
    if [ ! -d "${backup_dir}" ]; then
        error_exit "OpenSearch backup directory not found: ${backup_dir}"
    fi
    
    # Copy backup data to container
    docker cp "${backup_dir}" "${OPENSEARCH_CONTAINER}:/usr/share/opensearch/"
    
    # Close existing indices
    log "Closing existing OpenSearch indices..."
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X POST "localhost:9200/mams-*/_close" > /dev/null 2>&1 || true
    
    # Delete existing indices
    log "Deleting existing OpenSearch indices..."
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X DELETE "localhost:9200/mams-*" > /dev/null 2>&1 || true
    
    # Set up snapshot repository
    log "Setting up OpenSearch snapshot repository..."
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X PUT "localhost:9200/_snapshot/backup_repo" \
        -H 'Content-Type: application/json' \
        -d '{
            "type": "fs",
            "settings": {
                "location": "/usr/share/opensearch/backup",
                "compress": true
            }
        }' > /dev/null
    
    # Restore from snapshot
    snapshot_name="backup_${timestamp}"
    log "Restoring from OpenSearch snapshot: ${snapshot_name}"
    
    docker exec "${OPENSEARCH_CONTAINER}" curl -s -X POST "localhost:9200/_snapshot/backup_repo/${snapshot_name}/_restore" \
        -H 'Content-Type: application/json' \
        -d '{
            "indices": "mams-*",
            "include_global_state": false
        }' > /dev/null
    
    if [ $? -eq 0 ]; then
        # Wait for restore to complete
        log "Waiting for OpenSearch restore to complete..."
        while true; do
            status=$(docker exec "${OPENSEARCH_CONTAINER}" curl -s "localhost:9200/_cluster/health" | \
                python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
            
            if [ "$status" = "green" ] || [ "$status" = "yellow" ]; then
                log "OpenSearch restore completed successfully"
                break
            fi
            
            sleep 10
        done
    else
        error_exit "Failed to restore OpenSearch snapshot"
    fi
    
    log "OpenSearch restore completed"
}

# Verify restore
verify_restore() {
    local timestamp=$1
    
    log "Verifying restore..."
    
    # Check PostgreSQL
    for db in mams_users mams_assets mams_metadata mams_workflow mams_rights mams_audit; do
        table_count=$(docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${db}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
        log "PostgreSQL ${db}: ${table_count} tables"
    done
    
    # Check MongoDB
    for db in mams_search mams_metadata mams_assets mams_ai mams_cache; do
        collection_count=$(docker exec "${MONGODB_CONTAINER}" mongosh --username="${MONGO_USER}" --password="${MONGO_PASSWORD}" --authenticationDatabase=admin --eval "db.getSiblingDB('${db}').getCollectionNames().length" --quiet 2>/dev/null || echo "0")
        log "MongoDB ${db}: ${collection_count} collections"
    done
    
    # Check Redis
    key_count=$(docker exec "${REDIS_CONTAINER}" redis-cli DBSIZE 2>/dev/null || echo "0")
    log "Redis: ${key_count} keys"
    
    # Check OpenSearch
    index_count=$(docker exec "${OPENSEARCH_CONTAINER}" curl -s "localhost:9200/_cat/indices/mams-*?h=index" 2>/dev/null | wc -l || echo "0")
    log "OpenSearch: ${index_count} indices"
    
    log "Restore verification completed"
}

# Main restore function
main() {
    if [ -z "${TIMESTAMP}" ]; then
        log "Usage: $0 <backup_timestamp>"
        log ""
        show_available_backups
        exit 1
    fi
    
    log "Starting MAMS database restore process..."
    log "Restore timestamp: ${TIMESTAMP}"
    log "Backup directory: ${BACKUP_DIR}"
    
    # Validate backup
    validate_backup "${TIMESTAMP}"
    
    # Final confirmation
    log "WARNING: This will DESTROY all current data and restore from backup!"
    if ! confirm "Are you sure you want to continue?"; then
        log "Restore cancelled by user"
        exit 0
    fi
    
    # Start timer
    start_time=$(date +%s)
    
    # Stop services
    stop_services
    
    # Perform restore
    restore_postgresql "${TIMESTAMP}"
    restore_mongodb "${TIMESTAMP}"
    restore_redis "${TIMESTAMP}"
    restore_opensearch "${TIMESTAMP}"
    
    # Verify restore
    verify_restore "${TIMESTAMP}"
    
    # Start services
    start_services
    
    # Calculate elapsed time
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    
    log "Restore process completed successfully in ${elapsed} seconds"
    log "Restored from backup: ${TIMESTAMP}"
    
    # Create restore marker
    touch "${BACKUP_DIR}/restore_${TIMESTAMP}_$(date +%Y%m%d_%H%M%S)_SUCCESS"
}

# Handle signals
trap 'error_exit "Restore interrupted by signal"' INT TERM

# Run main function
main "$@"