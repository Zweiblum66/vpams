#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Initializing MAMS databases...${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
until docker exec mams-postgres pg_isready -U mams; do
  sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Create PostgreSQL databases for each service
echo -e "${YELLOW}Creating PostgreSQL databases...${NC}"
docker exec mams-postgres psql -U mams -d mams_dev -c "
CREATE DATABASE IF NOT EXISTS mams_users;
CREATE DATABASE IF NOT EXISTS mams_assets;
CREATE DATABASE IF NOT EXISTS mams_workflows;
CREATE DATABASE IF NOT EXISTS mams_rights;
"
echo -e "${GREEN}PostgreSQL databases created!${NC}"

# Initialize MongoDB collections
echo -e "${YELLOW}Initializing MongoDB...${NC}"
docker exec mams-mongodb mongosh --eval "
use mams_metadata;
db.createCollection('asset_metadata');
db.createCollection('metadata_schemas');
db.createCollection('custom_fields');

use mams_workflows;
db.createCollection('workflow_definitions');
db.createCollection('workflow_instances');
db.createCollection('workflow_history');
"
echo -e "${GREEN}MongoDB collections created!${NC}"

# Create MinIO buckets
echo -e "${YELLOW}Creating MinIO buckets...${NC}"
docker exec mams-minio mc config host add minio http://localhost:9000 minioadmin minioadmin
docker exec mams-minio mc mb minio/mams-assets --ignore-existing
docker exec mams-minio mc mb minio/mams-proxies --ignore-existing
docker exec mams-minio mc mb minio/mams-temp --ignore-existing
docker exec mams-minio mc mb minio/mams-archive --ignore-existing
echo -e "${GREEN}MinIO buckets created!${NC}"

# Initialize OpenSearch indices
echo -e "${YELLOW}Creating OpenSearch indices...${NC}"
curl -X PUT "http://localhost:9200/mams-assets" -H 'Content-Type: application/json' -d '{
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "name": { "type": "text", "analyzer": "standard" },
      "description": { "type": "text", "analyzer": "standard" },
      "tags": { "type": "keyword" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" },
      "file_type": { "type": "keyword" },
      "file_size": { "type": "long" },
      "metadata": { "type": "object", "enabled": true }
    }
  }
}' 2>/dev/null || true

echo -e "${GREEN}OpenSearch indices created!${NC}"

# Create RabbitMQ exchanges and queues
echo -e "${YELLOW}Setting up RabbitMQ...${NC}"
sleep 5  # Wait for RabbitMQ management plugin
docker exec mams-rabbitmq rabbitmqctl add_vhost mams 2>/dev/null || true
docker exec mams-rabbitmq rabbitmqctl set_permissions -p mams mams ".*" ".*" ".*" 2>/dev/null || true

echo -e "${GREEN}All databases initialized successfully!${NC}"