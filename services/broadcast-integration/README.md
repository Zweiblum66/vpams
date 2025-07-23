# Broadcast Integration Service

A comprehensive service for broadcast newsroom integration, extending MOS protocol capabilities with advanced newsroom production features for the MAMS (Media Asset Management System) project.

## Overview

The Broadcast Integration Service provides advanced newsroom and broadcast production features that complement the MOS Integration Service. While MOS handles the protocol-level integration, this service focuses on production workflows, rundown management, and live broadcast capabilities.

### Key Features

- **Rundown Management**: Complete rundown creation, editing, and execution
- **Script Integration**: Teleprompter scripts with timing and cue management
- **Graphics Management**: Lower thirds, tickers, and full-screen graphics
- **Live Production**: Real-time updates and broadcast automation
- **Multi-Newsroom Support**: Integration with multiple newsroom systems
- **Template Library**: Pre-built templates for common broadcast elements
- **Approval Workflows**: Editorial approval chains for scripts and rundowns
- **Broadcast Automation**: Integration with playout and automation systems

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   News Editor   │    │  MOS Integration │    │   Playout       │
│   Interface     │◄──►│     Service      │◄──►│   Systems       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                        │
         ▼                      ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│            Broadcast Integration Service                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Rundown Manager │ Script Engine   │ Graphics Controller      │
├─────────────────┼─────────────────┼─────────────────────────┤
│ Template Engine │ Approval System │ Automation Interface     │
└─────────────────┴─────────────────┴─────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   PostgreSQL    │
                   │   Database      │
                   └─────────────────┘
```

## Features

### 1. Rundown Management

- Create and manage broadcast rundowns
- Real-time collaboration on rundown editing
- Timing calculations and management
- Story reordering and updates
- Integration with MOS running orders

### 2. Script Management

- Teleprompter script creation and editing
- Script timing and pacing
- Cue point management
- Multi-language support
- Version control for scripts

### 3. Graphics Integration

- Lower thirds management
- Ticker/crawler content
- Full-screen graphics templates
- Dynamic data binding
- Preview capabilities

### 4. Live Production Support

- Real-time rundown updates
- On-air status tracking
- Breaking news integration
- Live shot management
- Remote contribution handling

### 5. Template System

- Pre-built broadcast templates
- Custom template creation
- Template versioning
- Category-based organization
- Quick access library

### 6. Approval Workflows

- Multi-level approval chains
- Editorial review process
- Legal compliance checks
- Automated notifications
- Audit trail

### 7. Automation Integration

- Playout system control
- Camera switching
- Audio routing
- Graphics triggering
- Timing synchronization

### 8. Multi-Newsroom Support

- ENPS integration
- Avid iNEWS support
- Ross Inception compatibility
- Octopus Newsroom connection
- Generic newsroom API

## API Endpoints

### Rundown Management

```http
GET    /api/v1/broadcast/rundowns
POST   /api/v1/broadcast/rundowns
GET    /api/v1/broadcast/rundowns/{id}
PUT    /api/v1/broadcast/rundowns/{id}
DELETE /api/v1/broadcast/rundowns/{id}
POST   /api/v1/broadcast/rundowns/{id}/stories
PUT    /api/v1/broadcast/rundowns/{id}/reorder
POST   /api/v1/broadcast/rundowns/{id}/execute
```

### Script Management

```http
GET    /api/v1/broadcast/scripts
POST   /api/v1/broadcast/scripts
GET    /api/v1/broadcast/scripts/{id}
PUT    /api/v1/broadcast/scripts/{id}
POST   /api/v1/broadcast/scripts/{id}/approve
GET    /api/v1/broadcast/scripts/{id}/teleprompter
POST   /api/v1/broadcast/scripts/{id}/timing
```

### Graphics Management

```http
GET    /api/v1/broadcast/graphics
POST   /api/v1/broadcast/graphics
GET    /api/v1/broadcast/graphics/{id}
PUT    /api/v1/broadcast/graphics/{id}
POST   /api/v1/broadcast/graphics/{id}/preview
POST   /api/v1/broadcast/graphics/{id}/activate
```

### Template Management

```http
GET    /api/v1/broadcast/templates
POST   /api/v1/broadcast/templates
GET    /api/v1/broadcast/templates/{id}
PUT    /api/v1/broadcast/templates/{id}
GET    /api/v1/broadcast/templates/categories
POST   /api/v1/broadcast/templates/{id}/instantiate
```

### Live Production

```http
GET    /api/v1/broadcast/live/status
POST   /api/v1/broadcast/live/breaking-news
PUT    /api/v1/broadcast/live/on-air/{story_id}
POST   /api/v1/broadcast/live/remote-feed
GET    /api/v1/broadcast/live/countdown
```

### Automation Control

```http
POST   /api/v1/broadcast/automation/trigger
PUT    /api/v1/broadcast/automation/preset/{id}
POST   /api/v1/broadcast/automation/camera/{id}/select
POST   /api/v1/broadcast/automation/audio/route
GET    /api/v1/broadcast/automation/status
```

## Integration Points

### MOS Integration Service

- Receives MOS objects and running orders
- Synchronizes rundown changes
- Handles object updates
- Manages media references

### Asset Management Service

- Links media assets to stories
- Manages proxy access
- Handles version control
- Provides metadata

### Workflow Engine

- Approval workflows
- Editorial review process
- Publishing workflows
- Notification handling

### Rights Management

- Content usage verification
- License compliance
- Geographic restrictions
- Rights reporting

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=broadcast-integration
SERVICE_PORT=8012
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/broadcast
REDIS_URL=redis://localhost:6379/1

# MOS Integration
MOS_SERVICE_URL=http://mos-integration:8011

# Newsroom Systems
ENPS_ENABLED=true
ENPS_API_URL=http://enps.newsroom.local/api
AVID_ENABLED=false
ROSS_ENABLED=false

# Automation Systems
AUTOMATION_ENABLED=true
PLAYOUT_SYSTEM=vizrt
PLAYOUT_API_URL=http://vizrt.local/api

# Graphics
GRAPHICS_RENDERER=vizrt
GRAPHICS_PREVIEW_URL=http://graphics.local/preview

# Teleprompter
TELEPROMPTER_SPEED_WPM=180
TELEPROMPTER_FONT_SIZE=32
```

## Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn src.main:app --reload --port 8012
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/test_rundown_service.py -v
```

## Security

- Role-based access control for editorial functions
- Audit logging for all broadcast operations
- Secure communication with newsroom systems
- Encryption for sensitive script content
- IP whitelisting for automation systems

## Performance Considerations

- Real-time updates using WebSockets
- Caching for frequently accessed templates
- Optimized database queries for large rundowns
- Async processing for non-critical operations
- Connection pooling for external systems

## Monitoring

- Health checks for all integrated systems
- Performance metrics for rundown operations
- Alert thresholds for timing violations
- Audit trail for compliance
- Real-time dashboard for production status

## License

This project is part of the MAMS system and follows the project's licensing terms.