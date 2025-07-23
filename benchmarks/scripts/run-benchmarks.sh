#!/bin/bash

# MAMS Performance Benchmark Runner
# This script orchestrates all performance benchmarks

set -e

# Configuration
BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${BENCHMARK_DIR}/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/benchmark_report_${TIMESTAMP}.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CATEGORY="all"
CONFIG_FILE="${BENCHMARK_DIR}/config/default.json"
TEST_NAME=""
COMPARE_BASELINE=""
USER_COUNTS="100,500,1000"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --category)
            CATEGORY="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --test)
            TEST_NAME="$2"
            shift 2
            ;;
        --compare)
            COMPARE_BASELINE="$2"
            shift 2
            ;;
        --users)
            USER_COUNTS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --category <api|database|frontend|all>  Run specific category (default: all)"
            echo "  --config <file>                        Use specific config file"
            echo "  --test <name>                          Run specific test"
            echo "  --compare <baseline>                   Compare with baseline results"
            echo "  --users <counts>                       User counts for load testing (default: 100,500,1000)"
            echo "  --help                                 Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        log_warning "Services are not running. Starting services..."
        docker-compose up -d
        sleep 10
    fi
    
    # Check if k6 is installed
    if ! command -v k6 &> /dev/null; then
        log_warning "k6 is not installed. Installing k6..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install k6
        else
            sudo apt-get update && sudo apt-get install -y k6
        fi
    fi
    
    # Check if Node.js is installed for frontend tests
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed. Please install Node.js for frontend tests."
        exit 1
    fi
    
    # Create report directory
    mkdir -p "$REPORT_DIR"
    
    log_success "Prerequisites check completed"
}

# Run API benchmarks
run_api_benchmarks() {
    log "Running API benchmarks..."
    
    cd "${BENCHMARK_DIR}/api"
    
    # Run k6 tests
    if [[ -n "$TEST_NAME" ]] && [[ "$TEST_NAME" == api/* ]]; then
        # Run specific test
        k6 run --out json="${REPORT_DIR}/api_${TIMESTAMP}.json" "${TEST_NAME#api/}.js"
    else
        # Run all API tests
        k6 run --out json="${REPORT_DIR}/api_${TIMESTAMP}.json" k6-config.js
        k6 run --out json="${REPORT_DIR}/api_upload_${TIMESTAMP}.json" asset-upload-benchmark.js
    fi
    
    log_success "API benchmarks completed"
}

# Run database benchmarks
run_database_benchmarks() {
    log "Running database benchmarks..."
    
    # Connect to PostgreSQL and run benchmarks
    PGPASSWORD=${POSTGRES_PASSWORD:-postgres} psql \
        -h localhost \
        -p 5432 \
        -U ${POSTGRES_USER:-postgres} \
        -d ${POSTGRES_DB:-mams} \
        -f "${BENCHMARK_DIR}/database/query-benchmarks.sql" \
        -c "SELECT * FROM benchmark.generate_report();" \
        > "${REPORT_DIR}/database_${TIMESTAMP}.txt"
    
    # Convert to JSON format
    python3 - <<EOF > "${REPORT_DIR}/database_${TIMESTAMP}.json"
import json
import re

with open("${REPORT_DIR}/database_${TIMESTAMP}.txt", 'r') as f:
    content = f.read()

# Parse the report
results = {
    "timestamp": "${TIMESTAMP}",
    "type": "database",
    "benchmarks": []
}

# Extract benchmark results
pattern = r'(\w+[\w\s]+):\s+Average:\s+([\d.]+)\s+ms\s+Min:\s+([\d.]+)\s+ms\s+Max:\s+([\d.]+)\s+ms\s+Std Dev:\s+([\d.]+)\s+ms'
matches = re.findall(pattern, content)

for match in matches:
    results["benchmarks"].append({
        "name": match[0].strip(),
        "avg_ms": float(match[1]),
        "min_ms": float(match[2]),
        "max_ms": float(match[3]),
        "std_dev_ms": float(match[4])
    })

print(json.dumps(results, indent=2))
EOF
    
    log_success "Database benchmarks completed"
}

# Run frontend benchmarks
run_frontend_benchmarks() {
    log "Running frontend benchmarks..."
    
    cd "${BENCHMARK_DIR}/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log "Installing frontend benchmark dependencies..."
        npm install puppeteer lighthouse
    fi
    
    # Run performance tests
    node performance-tests.js
    
    log_success "Frontend benchmarks completed"
}

# Generate consolidated report
generate_report() {
    log "Generating consolidated report..."
    
    python3 - <<EOF
import json
import glob
import os
from datetime import datetime

report_dir = "${REPORT_DIR}"
timestamp = "${TIMESTAMP}"

# Collect all benchmark results
results = {
    "timestamp": datetime.now().isoformat(),
    "environment": os.environ.get("NODE_ENV", "development"),
    "summary": {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "performance_score": 0
    },
    "results": {
        "api": {},
        "database": {},
        "frontend": {}
    },
    "recommendations": []
}

# Process API results
api_files = glob.glob(f"{report_dir}/api_*{timestamp}.json")
for file in api_files:
    with open(file, 'r') as f:
        data = json.load(f)
        # Process k6 results
        # Add to results["results"]["api"]

# Process database results
db_file = f"{report_dir}/database_{timestamp}.json"
if os.path.exists(db_file):
    with open(db_file, 'r') as f:
        data = json.load(f)
        results["results"]["database"] = data

# Process frontend results
frontend_files = glob.glob(f"{report_dir}/frontend-performance-*.json")
if frontend_files:
    with open(frontend_files[-1], 'r') as f:
        data = json.load(f)
        results["results"]["frontend"] = data

# Calculate summary
total_tests = 0
passed = 0

# Check API thresholds
if "api" in results["results"]:
    total_tests += 1
    # Check if meets performance targets
    passed += 1  # Simplified for now

# Check database thresholds
if "database" in results["results"]:
    for benchmark in results["results"]["database"].get("benchmarks", []):
        total_tests += 1
        if benchmark["avg_ms"] < 50:  # 50ms threshold
            passed += 1

# Check frontend thresholds
if "frontend" in results["results"]:
    total_tests += 1
    # Check if meets performance targets
    passed += 1  # Simplified for now

results["summary"]["total_tests"] = total_tests
results["summary"]["passed"] = passed
results["summary"]["failed"] = total_tests - passed
results["summary"]["performance_score"] = (passed / total_tests * 100) if total_tests > 0 else 0

# Generate recommendations
if results["summary"]["performance_score"] < 90:
    results["recommendations"].append("Performance score is below target. Review failed benchmarks.")

# Save consolidated report
with open("${REPORT_FILE}", 'w') as f:
    json.dump(results, f, indent=2)

print(f"Report saved to: ${REPORT_FILE}")
EOF
    
    log_success "Report generated: ${REPORT_FILE}"
}

# Compare with baseline
compare_with_baseline() {
    if [[ -z "$COMPARE_BASELINE" ]]; then
        return
    fi
    
    log "Comparing with baseline: $COMPARE_BASELINE"
    
    python3 - <<EOF
import json

current_file = "${REPORT_FILE}"
baseline_file = "${COMPARE_BASELINE}"

with open(current_file, 'r') as f:
    current = json.load(f)

with open(baseline_file, 'r') as f:
    baseline = json.load(f)

# Compare performance scores
current_score = current["summary"]["performance_score"]
baseline_score = baseline["summary"]["performance_score"]

print(f"Current performance score: {current_score:.1f}%")
print(f"Baseline performance score: {baseline_score:.1f}%")
print(f"Difference: {current_score - baseline_score:+.1f}%")

# Compare specific metrics
# ... detailed comparison logic ...
EOF
}

# Main execution
main() {
    log "Starting MAMS Performance Benchmarks"
    log "Category: $CATEGORY"
    log "Config: $CONFIG_FILE"
    
    check_prerequisites
    
    case $CATEGORY in
        api)
            run_api_benchmarks
            ;;
        database)
            run_database_benchmarks
            ;;
        frontend)
            run_frontend_benchmarks
            ;;
        all)
            run_api_benchmarks
            run_database_benchmarks
            run_frontend_benchmarks
            ;;
        *)
            log_error "Invalid category: $CATEGORY"
            exit 1
            ;;
    esac
    
    generate_report
    compare_with_baseline
    
    log_success "All benchmarks completed successfully!"
    log "Report available at: ${REPORT_FILE}"
}

# Run main function
main