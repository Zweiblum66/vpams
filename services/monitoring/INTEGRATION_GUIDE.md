# Prometheus Metrics Integration Guide

This guide explains how to integrate Prometheus metrics into MAMS microservices.

## Quick Start

### 1. Add Prometheus Client Dependency

Add to your service's `requirements.txt`:
```
prometheus-client==0.19.0
```

### 2. Add Metrics Endpoint

In your service's `main.py`, add the metrics endpoint:

```python
from prometheus_client import generate_latest, REGISTRY
from fastapi import Response

@app.get("/metrics", response_class=Response)
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

### 3. Use the Metrics Middleware

Import and add the metrics middleware to automatically track HTTP requests:

```python
from monitoring.middleware import PrometheusMetricsMiddleware

app.add_middleware(
    PrometheusMetricsMiddleware,
    service_name="your-service-name",
    version="1.0.0",
    environment="production"
)
```

### 4. Track Custom Metrics

Use the MetricsCollector for service-specific metrics:

```python
from monitoring.core.metrics import MetricsCollector

# Initialize collector
metrics = MetricsCollector(
    service_name="asset-management",
    version="1.0.0"
)

# Track asset upload
metrics.track_asset_upload(
    asset_type="video",
    status="success",
    duration=12.5
)

# Track processing task
metrics.track_processing_task(
    task_type="transcoding",
    status="completed",
    duration=300.5
)

# Track errors
metrics.track_error(
    error_type="ValidationError",
    severity="warning"
)
```

## Complete Example

Here's a complete example for the Asset Management Service:

```python
from fastapi import FastAPI, UploadFile, HTTPException
from monitoring.middleware import PrometheusMetricsMiddleware
from monitoring.core.metrics import MetricsCollector
from prometheus_client import generate_latest, REGISTRY
import time

app = FastAPI(title="Asset Management Service")

# Add metrics middleware
app.add_middleware(
    PrometheusMetricsMiddleware,
    service_name="asset-management",
    version="1.0.0"
)

# Initialize metrics collector
metrics = MetricsCollector(
    service_name="asset-management",
    version="1.0.0"
)

# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

# Example API endpoint with metrics
@app.post("/api/v1/assets/upload")
async def upload_asset(file: UploadFile):
    start_time = time.time()
    
    try:
        # Process upload...
        result = await process_upload(file)
        
        # Track successful upload
        metrics.track_asset_upload(
            asset_type=result.asset_type,
            status="success",
            duration=time.time() - start_time
        )
        
        return result
    except Exception as e:
        # Track error
        metrics.track_error(
            error_type=type(e).__name__,
            severity="error"
        )
        # Track failed upload
        metrics.track_asset_upload(
            asset_type="unknown",
            status="failed",
            duration=time.time() - start_time
        )
        raise HTTPException(status_code=500, detail=str(e))
```

## Available Metrics

The following metrics are automatically collected:

### HTTP Metrics
- `mams_http_requests_total` - Total HTTP requests (by service, method, endpoint, status)
- `mams_http_request_duration_seconds` - Request duration histogram
- `mams_http_request_size_bytes` - Request size summary
- `mams_http_response_size_bytes` - Response size summary

### Service Metrics
- `mams_service_health` - Service health status (1=healthy, 0=unhealthy)
- `mams_service_uptime_seconds` - Service uptime

### Custom Metrics (via MetricsCollector)
- `mams_asset_uploads_total` - Asset upload counter
- `mams_asset_upload_duration_seconds` - Upload duration histogram
- `mams_processing_tasks_total` - Processing task counter
- `mams_processing_duration_seconds` - Processing duration histogram
- `mams_errors_total` - Error counter by type and severity

## Best Practices

1. **Use Consistent Labels**: Always include service name in metrics
2. **Avoid High Cardinality**: Don't use user IDs or unique values as labels
3. **Track Business Metrics**: Not just technical metrics
4. **Set Appropriate Buckets**: For histograms, choose buckets that match your SLAs
5. **Document Metrics**: Include descriptions and units

## Troubleshooting

### Metrics Not Appearing
1. Check that the `/metrics` endpoint is accessible
2. Verify Prometheus is scraping your service
3. Check service logs for errors

### High Memory Usage
1. Reduce label cardinality
2. Use summaries instead of histograms where appropriate
3. Check for metric leaks (creating new metrics dynamically)

### Performance Impact
The metrics middleware adds minimal overhead (<1ms per request). If you notice performance issues:
1. Check custom metric collection code
2. Reduce the frequency of expensive metric calculations
3. Use sampling for high-volume endpoints