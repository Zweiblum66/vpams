#!/bin/bash

# Setup local Docker registry for development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGISTRY_PORT="${REGISTRY_PORT:-5000}"
REGISTRY_NAME="mams-registry"
REGISTRY_VOLUME="mams-registry-data"
REGISTRY_AUTH_VOLUME="mams-registry-auth"
REGISTRY_DOMAIN="registry.mams.local"

echo -e "${BLUE}=== Setting up Local Docker Registry ===${NC}"

# Check if registry is already running
if docker ps -a | grep -q $REGISTRY_NAME; then
    echo -e "${YELLOW}Registry container already exists${NC}"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Stopping and removing existing registry...${NC}"
        docker stop $REGISTRY_NAME 2>/dev/null || true
        docker rm $REGISTRY_NAME 2>/dev/null || true
    else
        echo -e "${GREEN}Using existing registry${NC}"
        exit 0
    fi
fi

# Create volumes
echo -e "${YELLOW}Creating Docker volumes...${NC}"
docker volume create $REGISTRY_VOLUME
docker volume create $REGISTRY_AUTH_VOLUME

# Generate self-signed certificate
echo -e "${YELLOW}Generating self-signed certificate...${NC}"
mkdir -p certs
if [ ! -f "certs/registry.crt" ]; then
    openssl req -newkey rsa:4096 -nodes -sha256 -keyout certs/registry.key \
        -x509 -days 365 -out certs/registry.crt \
        -subj "/C=US/ST=State/L=City/O=MAMS/CN=$REGISTRY_DOMAIN" \
        -addext "subjectAltName=DNS:$REGISTRY_DOMAIN,DNS:localhost,IP:127.0.0.1"
fi

# Create htpasswd file for basic auth
echo -e "${YELLOW}Setting up authentication...${NC}"
mkdir -p auth
if [ ! -f "auth/htpasswd" ]; then
    # Default credentials: admin/admin (change in production!)
    docker run --rm --entrypoint htpasswd httpd:2 -Bbn admin admin > auth/htpasswd
    echo -e "${GREEN}Created default credentials: admin/admin${NC}"
    echo -e "${RED}WARNING: Change these credentials for production use!${NC}"
fi

# Start registry
echo -e "${YELLOW}Starting Docker registry...${NC}"
docker run -d \
    --name $REGISTRY_NAME \
    --restart=unless-stopped \
    -p $REGISTRY_PORT:5000 \
    -v $REGISTRY_VOLUME:/var/lib/registry \
    -v "$(pwd)/auth:/auth:ro" \
    -v "$(pwd)/certs:/certs:ro" \
    -e REGISTRY_AUTH=htpasswd \
    -e REGISTRY_AUTH_HTPASSWD_REALM="MAMS Registry" \
    -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
    -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/registry.crt \
    -e REGISTRY_HTTP_TLS_KEY=/certs/registry.key \
    -e REGISTRY_STORAGE_DELETE_ENABLED=true \
    registry:2

# Wait for registry to start
echo -e "${YELLOW}Waiting for registry to start...${NC}"
sleep 5

# Test registry
if curl -k -u admin:admin https://localhost:$REGISTRY_PORT/v2/_catalog >/dev/null 2>&1; then
    echo -e "${GREEN}Registry is running successfully!${NC}"
else
    echo -e "${RED}Failed to start registry${NC}"
    docker logs $REGISTRY_NAME
    exit 1
fi

# Create registry UI (optional)
read -p "Do you want to install Registry UI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting Registry UI...${NC}"
    docker run -d \
        --name mams-registry-ui \
        --restart=unless-stopped \
        -p 8080:80 \
        -e REGISTRY_URL=https://$REGISTRY_NAME:5000 \
        -e REGISTRY_NAME="MAMS Registry" \
        -e PULL_URL=$REGISTRY_DOMAIN:$REGISTRY_PORT \
        joxit/docker-registry-ui:latest
    
    echo -e "${GREEN}Registry UI available at: http://localhost:8080${NC}"
fi

# Configure Docker to trust the certificate
echo -e "${YELLOW}Configuring Docker to trust the certificate...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/registry.crt
    echo -e "${GREEN}Certificate added to macOS keychain${NC}"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sudo cp certs/registry.crt /usr/local/share/ca-certificates/mams-registry.crt
    sudo update-ca-certificates
    echo -e "${GREEN}Certificate added to Linux trust store${NC}"
fi

# Add registry to /etc/hosts
echo -e "${YELLOW}Adding registry to /etc/hosts...${NC}"
if ! grep -q "$REGISTRY_DOMAIN" /etc/hosts; then
    echo "127.0.0.1 $REGISTRY_DOMAIN" | sudo tee -a /etc/hosts
    echo -e "${GREEN}Added $REGISTRY_DOMAIN to /etc/hosts${NC}"
fi

# Create helper scripts
echo -e "${YELLOW}Creating helper scripts...${NC}"

# Login script
cat > registry-login.sh << EOF
#!/bin/bash
echo "Logging into MAMS registry..."
docker login $REGISTRY_DOMAIN:$REGISTRY_PORT
EOF
chmod +x registry-login.sh

# Push script
cat > push-to-registry.sh << EOF
#!/bin/bash
# Push all MAMS images to local registry

SERVICES=(
    "api-gateway"
    "user-management"
    "storage-abstraction"
    "asset-management"
    "metadata-service"
    "search-engine"
    "ingest-service"
    "proxy-generation"
    "workflow-engine"
    "ai-ml-service"
    "rights-management"
    "monitoring-logging"
    "integration-service"
    "frontend"
)

echo "Tagging and pushing MAMS images to local registry..."

for SERVICE in "\${SERVICES[@]}"; do
    if docker images | grep -q "mams-\$SERVICE"; then
        echo "Processing \$SERVICE..."
        docker tag mams-\$SERVICE:latest $REGISTRY_DOMAIN:$REGISTRY_PORT/mams-\$SERVICE:latest
        docker push $REGISTRY_DOMAIN:$REGISTRY_PORT/mams-\$SERVICE:latest
    fi
done

echo "Push completed!"
EOF
chmod +x push-to-registry.sh

# Print summary
echo -e "${GREEN}=== Local Registry Setup Complete ===${NC}"
echo -e "Registry URL: ${BLUE}https://$REGISTRY_DOMAIN:$REGISTRY_PORT${NC}"
echo -e "Username: ${BLUE}admin${NC}"
echo -e "Password: ${BLUE}admin${NC}"
echo ""
echo -e "To login to the registry:"
echo -e "  ${YELLOW}./registry-login.sh${NC}"
echo ""
echo -e "To push images to the registry:"
echo -e "  ${YELLOW}./push-to-registry.sh${NC}"
echo ""
echo -e "To use images from the registry:"
echo -e "  ${YELLOW}$REGISTRY_DOMAIN:$REGISTRY_PORT/mams-<service>:latest${NC}"
echo ""
echo -e "${RED}Remember to change the default credentials for production use!${NC}"