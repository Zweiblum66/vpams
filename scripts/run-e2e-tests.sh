#!/bin/bash

# MAMS E2E Test Runner Script
# This script sets up the environment and runs Cypress E2E tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_DIR="./frontend"
DOCKER_COMPOSE_FILE="docker-compose.yml"
TEST_TIMEOUT=300

# Functions
print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_error() {
    echo -e "${RED}Error: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

cleanup() {
    print_header "Cleaning up..."
    
    # Stop frontend dev server if running
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Stop Docker services
    docker-compose -f $DOCKER_COMPOSE_FILE down
    
    echo "Cleanup completed"
}

# Trap cleanup on exit
trap cleanup EXIT

# Parse command line arguments
MODE="run"
BROWSER="chrome"
HEADED="false"
SPEC=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --open)
            MODE="open"
            shift
            ;;
        --browser)
            BROWSER="$2"
            shift 2
            ;;
        --headed)
            HEADED="true"
            shift
            ;;
        --spec)
            SPEC="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --open          Open Cypress Test Runner"
            echo "  --browser       Browser to use (chrome, firefox, edge)"
            echo "  --headed        Run tests in headed mode"
            echo "  --spec          Run specific spec file"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check prerequisites
print_header "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed"
    exit 1
fi

echo "All prerequisites are installed"

# Start backend services
print_header "Starting backend services..."

# Check if services are already running
if docker-compose ps | grep -q "Up"; then
    print_warning "Some services are already running. Restarting..."
    docker-compose -f $DOCKER_COMPOSE_FILE down
fi

docker-compose -f $DOCKER_COMPOSE_FILE up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
./scripts/wait-for-services.sh

# Seed test database
print_header "Seeding test database..."

# Create test users
docker-compose exec -T postgres psql -U mams -d mams <<EOF
-- Insert test users if not exist
INSERT INTO users (id, email, password_hash, name, is_active, created_at)
VALUES 
    ('test-user-id', 'test@mams.local', '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiLXCJrD/XuC', 'Test User', true, NOW()),
    ('admin-user-id', 'admin@mams.local', '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiLXCJrD/XuC', 'Admin User', true, NOW())
ON CONFLICT (email) DO NOTHING;

-- Assign roles
INSERT INTO user_roles (user_id, role_id)
SELECT 'test-user-id', id FROM roles WHERE name = 'user'
ON CONFLICT DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT 'admin-user-id', id FROM roles WHERE name = 'admin'
ON CONFLICT DO NOTHING;
EOF

echo "Test database seeded"

# Install frontend dependencies
print_header "Installing frontend dependencies..."
cd $FRONTEND_DIR

if [ ! -d "node_modules" ]; then
    npm ci
else
    echo "Dependencies already installed"
fi

# Install Cypress if not already installed
if [ ! -d "node_modules/cypress" ]; then
    npm install cypress --save-dev
fi

# Build frontend
print_header "Building frontend..."
npm run build

# Start frontend server
print_header "Starting frontend server..."
npm run preview &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
npx wait-on http://localhost:3000 -t 30000

# Run Cypress tests
print_header "Running Cypress E2E tests..."

if [ "$MODE" = "open" ]; then
    # Open Cypress Test Runner
    npx cypress open
else
    # Run tests in CI mode
    CYPRESS_OPTS=""
    
    if [ "$HEADED" = "false" ]; then
        CYPRESS_OPTS="$CYPRESS_OPTS --headless"
    fi
    
    if [ ! -z "$SPEC" ]; then
        CYPRESS_OPTS="$CYPRESS_OPTS --spec $SPEC"
    fi
    
    npx cypress run --browser $BROWSER $CYPRESS_OPTS
fi

# Check test results
if [ $? -eq 0 ]; then
    print_header "✅ All tests passed!"
else
    print_error "❌ Some tests failed"
    exit 1
fi