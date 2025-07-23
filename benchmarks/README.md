# MAMS Performance Benchmarks

This directory contains performance benchmarking tools and tests for the MAMS platform.

## Overview

Our performance benchmarking framework measures:
- API endpoint response times
- Database query performance
- File upload/download throughput
- Search query performance
- Frontend loading times
- Concurrent user handling
- Resource utilization

## Benchmark Categories

### 1. API Benchmarks
- Authentication endpoints
- CRUD operations
- Search queries
- Workflow execution
- File operations

### 2. Database Benchmarks
- Query execution times
- Index performance
- Connection pooling
- Transaction throughput
- Aggregate operations

### 3. Frontend Benchmarks
- Initial page load
- Asset rendering
- Search responsiveness
- File upload progress
- UI interaction latency

### 4. System Benchmarks
- Memory usage
- CPU utilization
- Network throughput
- Disk I/O
- Container performance

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (95th percentile) | < 200ms | > 500ms |
| Database Query Time (95th percentile) | < 50ms | > 200ms |
| File Upload Speed | > 100MB/s | < 50MB/s |
| Search Response Time | < 1s | > 3s |
| Frontend Load Time | < 2s | > 5s |
| Concurrent Users | > 1000 | < 500 |
| Memory Usage per Container | < 2GB | > 4GB |
| CPU Usage (average) | < 70% | > 90% |

## Running Benchmarks

### Quick Start

Run all benchmarks:
```bash
./scripts/run-benchmarks.sh
```

Run specific category:
```bash
./scripts/run-benchmarks.sh --category api
./scripts/run-benchmarks.sh --category database
./scripts/run-benchmarks.sh --category frontend
```

### Detailed Options

```bash
# Run with specific configuration
./scripts/run-benchmarks.sh --config benchmarks/config/production.json

# Run specific test
./scripts/run-benchmarks.sh --test api/auth/login

# Generate comparison report
./scripts/run-benchmarks.sh --compare baseline.json

# Run with different load levels
./scripts/run-benchmarks.sh --users 100,500,1000,5000
```

## Benchmark Tools

- **API Testing**: k6, Apache Bench (ab), wrk
- **Database Testing**: pgbench, sysbench, custom scripts
- **Frontend Testing**: Lighthouse, WebPageTest, custom metrics
- **Load Testing**: Locust, JMeter, k6

## Report Format

Benchmark results are saved in JSON format with the following structure:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "environment": "production",
  "summary": {
    "total_tests": 50,
    "passed": 48,
    "failed": 2,
    "performance_score": 92.5
  },
  "results": {
    "api": { ... },
    "database": { ... },
    "frontend": { ... }
  },
  "recommendations": [ ... ]
}
```

## Integration

- CI/CD pipeline runs benchmarks on each release
- Performance regression detection
- Automated alerts for threshold violations
- Historical trend analysis

## Contributing

When adding new benchmarks:
1. Follow the existing structure
2. Document performance targets
3. Include both average and percentile metrics
4. Consider cold and warm scenarios
5. Test with realistic data volumes