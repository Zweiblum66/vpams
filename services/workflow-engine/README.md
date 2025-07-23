# MAMS Workflow Engine Service

The Workflow Engine Service provides comprehensive workflow automation and orchestration capabilities for the MAMS platform, enabling users to create, manage, and execute automated workflows for media processing, approval processes, and content distribution.

## Features

- **Workflow Definition**: Create and manage complex workflows with conditional logic, loops, and parallel execution
- **Task Types**: Support for 20+ task types including media processing, file operations, notifications, and AI/ML tasks
- **Triggers**: Multiple trigger types (manual, schedule, webhook, event, file watch, API)
- **State Management**: Distributed state management with Redis for scalability
- **Error Handling**: Comprehensive error handling with retry mechanisms
- **Monitoring**: Built-in workflow execution tracking and statistics

## Architecture

### Core Components

1. **Workflow Engine**: Core execution engine that orchestrates workflow instances
2. **Task Executor**: Executes individual tasks with proper error handling
3. **State Manager**: Manages workflow state persistence and recovery
4. **Workflow Service**: Handles CRUD operations for workflow definitions

### Task Types

#### Media Processing
- `transcode`: Transcode media files
- `generate_proxy`: Generate proxy files
- `extract_metadata`: Extract metadata from media files
- `generate_thumbnail`: Generate thumbnails

#### File Operations
- `copy_file`: Copy files between locations
- `move_file`: Move files
- `delete_file`: Delete files
- `archive_file`: Archive files to cold storage

#### Asset Operations
- `create_asset`: Create new assets
- `update_asset`: Update asset metadata
- `tag_asset`: Add tags to assets
- `publish_asset`: Publish assets to destinations

#### Notifications
- `send_email`: Send email notifications
- `send_notification`: Send in-app notifications
- `webhook_call`: Call external webhooks

#### AI/ML
- `auto_tag`: Automatic content tagging
- `transcribe`: Audio/video transcription
- `detect_objects`: Object detection in images/video
- `analyze_content`: Content analysis

## API Endpoints

### Workflow Management
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/{workflow_id}` - Get workflow details
- `PATCH /api/v1/workflows/{workflow_id}` - Update workflow
- `DELETE /api/v1/workflows/{workflow_id}` - Delete workflow

### Workflow Execution
- `POST /api/v1/workflows/{workflow_id}/execute` - Execute workflow
- `GET /api/v1/instances` - List workflow instances
- `GET /api/v1/instances/{instance_id}` - Get instance details
- `POST /api/v1/instances/{instance_id}/pause` - Pause instance
- `POST /api/v1/instances/{instance_id}/resume` - Resume instance
- `POST /api/v1/instances/{instance_id}/cancel` - Cancel instance

### Statistics
- `GET /api/v1/stats` - Get workflow statistics

## Configuration

Key environment variables:

```env
SERVICE_NAME=workflow-engine
SERVICE_PORT=8088
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
MONGODB_URL=mongodb://mongo:27017/workflow_engine
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://user:pass@rabbitmq:5672/
ASSET_SERVICE_URL=http://asset-management:8003
METADATA_SERVICE_URL=http://metadata-service:8005
PROXY_SERVICE_URL=http://proxy-generation:8007
NOTIFICATION_SERVICE_URL=http://notification-service:8010
ENABLE_METRICS=true
```

## Architecture Components

### Core Services
- **Main API Service** (Port 8088): RESTful API for workflow management
- **Task Worker**: Background worker processing tasks from RabbitMQ queue
- **RabbitMQ**: Message queue for async task processing and distribution
- **Redis**: Workflow state caching and distributed locks
- **PostgreSQL**: Workflow definitions and execution history
- **MongoDB**: Flexible workflow configuration and template storage

### Integration Points
- Notification system integration for alerts and approvals
- Integration with other MAMS services (Asset Management, Metadata, Proxy Generation)
- Webhook support for external system integration

## Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- MongoDB 7.0+
- Redis 7+
- RabbitMQ 3.12+

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run database migrations:
```bash
alembic upgrade head
```

3. Start the service:
```bash
uvicorn src.main:app --reload --port 8088
```

### Docker

Start all services with Docker Compose:
```bash
docker-compose up -d
```

### Running the Worker

Start the background task worker:
```bash
python -m src.workers.task_worker
```

## Testing

Run tests:
```bash
pytest tests/ -v --cov=src
```

## Example Workflows

### Media Processing Workflow
```json
{
  "name": "Media Processing Workflow",
  "description": "Process uploaded media files",
  "tasks": [
    {
      "task_id": "extract-metadata",
      "task_type": "extract_metadata",
      "name": "Extract Metadata",
      "parameters": {
        "asset_id": "$input.asset_id"
      }
    },
    {
      "task_id": "generate-proxy",
      "task_type": "generate_proxy",
      "name": "Generate Proxy",
      "parameters": {
        "asset_id": "$input.asset_id",
        "quality": "medium"
      }
    },
    {
      "task_id": "auto-tag",
      "task_type": "auto_tag",
      "name": "Auto Tag Content",
      "parameters": {
        "asset_id": "$input.asset_id"
      }
    }
  ]
}
```

### Approval Workflow with Notifications
```json
{
  "name": "Content Approval Workflow",
  "description": "Review and approve content before publishing",
  "tasks": [
    {
      "task_id": "request-approval",
      "task_type": "approval",
      "name": "Request Editorial Approval",
      "parameters": {
        "approvers": ["editor@company.com", "manager@company.com"],
        "timeout_hours": 24,
        "escalation_enabled": true
      }
    },
    {
      "task_id": "check-approval",
      "task_type": "conditional",
      "name": "Check Approval Status",
      "conditions": [
        {
          "field": "$output.request-approval.decision",
          "operator": "equals",
          "value": "approved"
        }
      ],
      "then_tasks": [
        {
          "task_id": "publish",
          "task_type": "publish_asset",
          "name": "Publish Asset",
          "parameters": {
            "asset_id": "$input.asset_id",
            "destination": "production"
          }
        }
      ],
      "else_tasks": [
        {
          "task_id": "notify-rejection",
          "task_type": "send_notification",
          "name": "Notify Rejection",
          "parameters": {
            "recipient": "$input.submitter_email",
            "subject": "Content Rejected",
            "message": "Your content has been rejected. Reason: $output.request-approval.comments"
          }
        }
      ]
    }
  ]
}
```

## Monitoring

### Health Endpoints
- `GET /health` - Basic health check
- `GET /metrics` - Prometheus metrics
- `GET /api/v1/queue/status` - RabbitMQ queue statistics

### Key Metrics
- `workflow_created_total` - Total workflows created
- `workflow_executed_total` - Total workflows executed
- `workflow_duration_seconds` - Workflow execution duration
- `task_executed_total` - Total tasks executed
- `task_duration_seconds` - Task execution duration
- `approval_response_time_seconds` - Approval response times
- `rabbitmq_queue_size` - Queue sizes for monitoring backlog