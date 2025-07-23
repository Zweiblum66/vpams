#!/bin/bash
# Full deployment script for MAMS on Ubuntu server

set -e

# Configuration
SERVER_IP="192.168.178.186"
SERVER_USER="jens"
SERVER_PASS='Tr4umK3ks!!'
REMOTE_DIR="/opt/mams"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to execute remote commands
remote_exec() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $SERVER_USER@$SERVER_IP "$@"
}

# Function to copy files
remote_copy() {
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$@"
}

# Test connection
test_connection() {
    print_status "Testing connection to $SERVER_IP..."
    
    if remote_exec "echo 'Connection successful' && hostname" > /dev/null 2>&1; then
        print_status "✓ Connected successfully"
        return 0
    else
        print_error "Failed to connect to server"
        print_warning "Please ensure:"
        print_warning "1. SSH password authentication is enabled on the server"
        print_warning "2. The password is correct"
        print_warning "3. The server is accessible at $SERVER_IP"
        echo ""
        echo "To enable password authentication on the server:"
        echo "1. Connect to the server console"
        echo "2. Edit /etc/ssh/sshd_config"
        echo "3. Set: PasswordAuthentication yes"
        echo "4. Restart SSH: sudo systemctl restart sshd"
        return 1
    fi
}

# Main deployment
main() {
    print_status "=== MAMS Production Deployment ==="
    print_status "Server: $SERVER_IP"
    print_status "User: $SERVER_USER"
    echo ""
    
    # Test connection
    if ! test_connection; then
        exit 1
    fi
    
    # Create directories
    print_status "Creating remote directories..."
    remote_exec "sudo mkdir -p $REMOTE_DIR && sudo chown $SERVER_USER:$SERVER_USER $REMOTE_DIR"
    remote_exec "mkdir -p $REMOTE_DIR/{scripts,nginx,monitoring,services}"
    
    # System setup
    print_status "Running system setup..."
    remote_exec "sudo apt-get update"
    remote_exec "sudo apt-get install -y docker.io docker-compose"
    remote_exec "sudo usermod -aG docker $SERVER_USER"
    
    # Create directories
    print_status "Creating storage directories..."
    remote_exec "sudo mkdir -p /var/lib/mams/{postgres,mongodb,opensearch,redis,rabbitmq,grafana,prometheus}"
    remote_exec "sudo mkdir -p /var/log/mams/{nginx,services}"
    remote_exec "sudo mkdir -p /mnt/data/{assets,proxies,thumbnails,temp,archive,backups,minio}"
    
    # Set permissions
    remote_exec "sudo chown -R 999:999 /var/lib/mams/postgres"
    remote_exec "sudo chown -R 999:999 /var/lib/mams/mongodb"
    remote_exec "sudo chown -R 1000:1000 /var/lib/mams/opensearch"
    remote_exec "sudo chown -R 472:472 /var/lib/mams/grafana"
    remote_exec "sudo chown -R $SERVER_USER:$SERVER_USER /mnt/data"
    
    print_status "Deployment preparation complete!"
    print_status "Next steps:"
    print_status "1. Copy your application files to $REMOTE_DIR"
    print_status "2. Configure environment variables"
    print_status "3. Start services with docker-compose"
}

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    print_error "sshpass is not installed"
    print_status "Install with: brew install hudochenkov/sshpass/sshpass (macOS)"
    print_status "           : apt-get install sshpass (Ubuntu/Debian)"
    exit 1
fi

# Run deployment
main "$@"