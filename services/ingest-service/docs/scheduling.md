# Ingest Scheduling Documentation

## Overview

The MAMS Ingest Service includes a comprehensive scheduling system that allows users to automate file ingestion based on cron expressions. This enables automated workflows for regularly ingesting content from various sources.

## Features

### Core Scheduling Capabilities

- **Cron-based Scheduling**: Use standard cron expressions for flexible timing
- **Multiple Schedules**: Support for unlimited scheduled ingest configurations
- **Priority Handling**: Scheduled ingests can have different priority levels
- **Metadata Templates**: Apply consistent metadata to scheduled ingests
- **Automatic Tagging**: Add tags automatically to scheduled content
- **Error Handling**: Robust error handling with retry logic
- **Manual Triggers**: Ability to manually trigger scheduled ingests
- **Statistics**: Comprehensive statistics and monitoring

### Supported Cron Expressions

The scheduler supports standard cron expressions with optional seconds:

```bash
# Standard 5-field format (minute hour day month weekday)
0 2 * * *          # Every day at 2:00 AM
0 */6 * * *         # Every 6 hours
0 0 * * 1           # Every Monday at midnight
0 0 1 * *           # First day of every month at midnight

# Extended 6-field format (second minute hour day month weekday)
30 0 2 * * *        # Every day at 2:00:30 AM
0 */30 * * * *      # Every 30 minutes
0 0 */2 * * *       # Every 2 hours
```

## API Endpoints

### Create Scheduled Ingest

```http
POST /api/v1/scheduled-ingests
Content-Type: application/json

{
  "name": "Daily News Archive",
  "source_path": "/watch/news/archive",
  "destination_project_id": "news-project-123",
  "cron_expression": "0 2 * * *",
  "enabled": true,
  "metadata_template": {
    "category": "news",
    "retention_policy": "30_days"
  },
  "tags": ["automated", "news"],
  "priority": "normal",
  "auto_generate_proxies": true,
  "preserve_folder_structure": true
}
```

### List Scheduled Ingests

```http
GET /api/v1/scheduled-ingests
```

### Get Scheduled Ingest

```http
GET /api/v1/scheduled-ingests/{ingest_id}
```

### Update Scheduled Ingest

```http
PUT /api/v1/scheduled-ingests/{ingest_id}
Content-Type: application/json

{
  "name": "Updated Schedule",
  "cron_expression": "0 3 * * *",
  "enabled": false
}
```

### Delete Scheduled Ingest

```http
DELETE /api/v1/scheduled-ingests/{ingest_id}
```

### Manual Trigger

```http
POST /api/v1/scheduled-ingests/{ingest_id}/run
```

## Configuration Examples

### Daily Archive Ingest

```json
{
  "name": "Daily Archive Ingest",
  "source_path": "/archive/daily",
  "destination_project_id": "archive-project",
  "cron_expression": "0 1 * * *",
  "enabled": true,
  "metadata_template": {
    "source": "archive",
    "processed_date": "{{current_date}}"
  },
  "tags": ["archive", "daily"],
  "priority": "low",
  "auto_generate_proxies": false,
  "preserve_folder_structure": true
}
```

### Hourly Breaking News

```json
{
  "name": "Breaking News Monitor",
  "source_path": "/incoming/breaking",
  "destination_project_id": "news-urgent",
  "cron_expression": "0 * * * *",
  "enabled": true,
  "metadata_template": {
    "category": "breaking_news",
    "priority": "urgent"
  },
  "tags": ["breaking", "news", "urgent"],
  "priority": "urgent",
  "auto_generate_proxies": true,
  "preserve_folder_structure": false
}
```

### Weekly Backup Ingest

```json
{
  "name": "Weekly Backup",
  "source_path": "/backup/weekly",
  "destination_project_id": "backup-project",
  "cron_expression": "0 0 * * 0",
  "enabled": true,
  "metadata_template": {
    "backup_type": "weekly",
    "retention": "1_year"
  },
  "tags": ["backup", "weekly"],
  "priority": "low",
  "auto_generate_proxies": false,
  "preserve_folder_structure": true
}
```

## Monitoring and Management

### Statistics API

```http
GET /api/v1/scheduler-stats
```

Returns:
```json
{
  "is_running": true,
  "total_scheduled_ingests": 5,
  "active_scheduled_ingests": 4,
  "scheduled_jobs": 4,
  "next_run_times": [
    {
      "job_id": "scheduled_ingest_abc123",
      "job_name": "Scheduled Ingest: Daily Archive",
      "next_run_time": "2025-01-16T01:00:00Z"
    }
  ]
}
```

### Execution Tracking

Each scheduled ingest tracks:
- **Last Execution**: When it was last run
- **Next Execution**: When it will run next
- **Success/Failure**: Whether executions succeeded
- **Error Messages**: Details of any failures

### Error Handling

The scheduler includes comprehensive error handling:

1. **Cron Validation**: Invalid cron expressions are rejected
2. **Source Path Validation**: Checks if source paths exist
3. **Execution Errors**: Graceful handling of ingest failures
4. **Recovery**: Automatic retry for transient failures
5. **Logging**: Detailed logging of all scheduling activities

## Best Practices

### Cron Expression Guidelines

1. **Use Standard Formats**: Stick to standard cron expressions when possible
2. **Avoid Overlap**: Ensure scheduled jobs don't overlap in execution time
3. **Consider System Load**: Spread high-frequency jobs across different times
4. **Time Zones**: All times are in UTC - plan accordingly

### Performance Considerations

1. **Batch Processing**: Group small files into batches when possible
2. **Priority Management**: Use appropriate priorities for different content types
3. **Resource Limits**: Monitor system resources during scheduled operations
4. **Storage Capacity**: Ensure adequate storage for scheduled ingests

### Monitoring Recommendations

1. **Regular Health Checks**: Monitor scheduler service health
2. **Execution Logs**: Review execution logs for failures
3. **Performance Metrics**: Track ingest performance over time
4. **Alert Setup**: Configure alerts for failed scheduled ingests

## Troubleshooting

### Common Issues

1. **Invalid Cron Expression**
   - Error: "Invalid cron expression"
   - Solution: Validate cron syntax using online tools

2. **Source Path Not Found**
   - Error: "Source path does not exist"
   - Solution: Verify path exists and is accessible

3. **Execution Failures**
   - Error: Various ingest-related errors
   - Solution: Check ingest service logs and source file integrity

4. **Scheduler Not Running**
   - Error: "Scheduler service not initialized"
   - Solution: Check service startup logs and dependencies

### Debug Commands

```bash
# Check scheduler service status
curl http://localhost:8002/api/v1/scheduler-stats

# View scheduled ingest details
curl http://localhost:8002/api/v1/scheduled-ingests/{id}

# Check service health
curl http://localhost:8002/health

# View service logs
docker logs ingest-service
```

## Integration with Other Services

### Watch Folders vs Scheduled Ingests

- **Watch Folders**: Real-time monitoring for immediate ingestion
- **Scheduled Ingests**: Time-based processing for predictable workflows
- **Hot Folders**: Immediate processing for urgent content

### Message Queue Integration

Scheduled ingests use the same message queue system as other ingest types:
- Jobs are queued with appropriate priority
- Processing follows the same validation pipeline
- Results are tracked and reported consistently

### Storage Integration

Scheduled ingests work with all supported storage backends:
- Local file systems
- Network attached storage (NAS)
- Cloud storage (S3, Azure, GCS)
- Archive systems

## Security Considerations

### Access Control

- Scheduled ingests respect user permissions
- Only authorized users can create/modify schedules
- Source paths must be accessible by the service account

### Data Protection

- Metadata templates are validated for sensitive information
- Source paths are validated to prevent unauthorized access
- All scheduling activities are logged for audit purposes

## Future Enhancements

### Planned Features

1. **Advanced Scheduling**: Support for more complex scheduling patterns
2. **Conditional Execution**: Execute only if certain conditions are met
3. **Resource Awareness**: Schedule based on system resource availability
4. **Multi-Location**: Support for scheduling across multiple locations
5. **Integration APIs**: Enhanced integration with external scheduling systems