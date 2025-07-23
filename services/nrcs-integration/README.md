# NRCS Integration Service

A comprehensive Newsroom Computer System (NRCS) integration service that provides direct connectivity and workflow automation with major newsroom systems including ENPS, Avid iNEWS, Ross Inception, and Octopus Newsroom.

## Overview

The NRCS Integration Service acts as a unified bridge between MAMS and various newsroom systems, providing standardized APIs and workflows while handling the unique protocols and requirements of each NRCS vendor. This service complements the MOS Integration Service by providing vendor-specific optimizations and advanced workflow features.

### Key Features

- **Multi-Vendor NRCS Support**: Direct integration with ENPS, Avid iNEWS, Ross Inception, and Octopus
- **Unified API**: Consistent interface regardless of underlying NRCS system  
- **Real-time Synchronization**: Bidirectional sync of stories, rundowns, and media
- **Workflow Automation**: Automated content ingestion and publishing workflows
- **Advanced Search**: Cross-NRCS search and content discovery
- **User Management**: Synchronized user accounts and permissions across systems
- **Assignment Management**: Story assignments, beats, and reporter scheduling
- **Multi-Language Support**: International newsroom operations
- **Archive Integration**: Long-term story and content archival
- **Analytics & Reporting**: Cross-platform newsroom analytics

## Supported NRCS Systems

### 1. ENPS (Electronic News Production System)
- **Version Support**: ENPS v7.0+
- **Protocol**: TCP/IP with proprietary messaging
- **Features**: Story creation, rundown management, user sync, archive access
- **Authentication**: LDAP/Active Directory integration

### 2. Avid iNEWS
- **Version Support**: iNEWS v4.0+
- **Protocol**: FTP/SFTP and Avid API
- **Features**: Wire service integration, story templates, approval workflows
- **Authentication**: Avid User Management System

### 3. Ross Inception
- **Version Support**: Inception v6.0+
- **Protocol**: REST API and WebSocket
- **Features**: Live production integration, graphics automation
- **Authentication**: OAuth2 and API keys

### 4. Octopus Newsroom
- **Version Support**: Octopus v8.0+
- **Protocol**: REST API and SOAP
- **Features**: Multi-platform publishing, social media integration
- **Authentication**: JWT tokens and session management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      ENPS       │    │   Avid iNEWS    │    │  Ross Inception │
│   (TCP/Props)   │    │   (FTP/API)     │    │   (REST/WS)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └─────────────────┬─────────────────────────────┘
                           │
                           ▼
           ┌─────────────────────────────────────────┐
           │         NRCS Integration Service        │
           ├─────────────────┬───────────────────────┤
           │ Protocol        │  Workflow             │
           │ Adapters        │  Engine               │
           ├─────────────────┼───────────────────────┤
           │ Content         │  User Management      │
           │ Synchronizer    │  & Authentication     │
           └─────────────────┴───────────────────────┘
                           │
                           ▼
           ┌─────────────────────────────────────────┐
           │             MAMS Core                   │
           ├─────────────────┬───────────────────────┤
           │ Asset           │  MOS Integration      │
           │ Management      │  Service              │
           ├─────────────────┼───────────────────────┤
           │ Broadcast       │  Storage              │
           │ Integration     │  Abstraction          │
           └─────────────────┴───────────────────────┘
```

## Features by NRCS

### ENPS Integration
- **Story Synchronization**: Bidirectional sync of stories and metadata
- **Rundown Management**: Real-time rundown updates and timing
- **Wire Service Integration**: Automated wire story ingestion
- **User Management**: LDAP-based user synchronization
- **Assignment Desk**: Reporter assignments and beat management
- **Archive Access**: Historical story retrieval and search
- **Multi-Language Support**: International bureau operations

### Avid iNEWS Integration
- **Template Management**: Story templates and formatting
- **Approval Workflows**: Editorial review and approval chains
- **Media Tracking**: Asset references and proxy management
- **Search Integration**: Advanced story and archive search
- **Publishing Control**: Multi-platform publishing automation
- **Rights Integration**: Usage rights and licensing tracking
- **Version Control**: Story versioning and conflict resolution

### Ross Inception Integration
- **Live Production**: Real-time production control and automation
- **Graphics Integration**: Lower thirds and graphics automation
- **Teleprompter Control**: Script delivery and timing
- **Device Control**: Camera and switcher integration
- **Playlist Management**: Show rundowns and segment timing
- **Alert System**: Breaking news and emergency broadcasts
- **Social Media**: Automated social media publishing

### Octopus Integration
- **Multi-Platform Publishing**: Web, mobile, and social publishing
- **Content Planning**: Editorial calendar and planning tools
- **Analytics Integration**: Audience metrics and performance
- **SEO Optimization**: Automated SEO and metadata enhancement
- **Mobile Journalism**: Field reporting and mobile workflows
- **Video Management**: Video content and streaming integration
- **Subscription Management**: Paid content and subscriptions

## API Endpoints

### NRCS Management
```http
GET    /api/v1/nrcs/systems
POST   /api/v1/nrcs/systems
GET    /api/v1/nrcs/systems/{system_id}
PUT    /api/v1/nrcs/systems/{system_id}
DELETE /api/v1/nrcs/systems/{system_id}
POST   /api/v1/nrcs/systems/{system_id}/connect
POST   /api/v1/nrcs/systems/{system_id}/disconnect
GET    /api/v1/nrcs/systems/{system_id}/status
```

### Story Management
```http
GET    /api/v1/nrcs/stories
POST   /api/v1/nrcs/stories
GET    /api/v1/nrcs/stories/{story_id}
PUT    /api/v1/nrcs/stories/{story_id}
DELETE /api/v1/nrcs/stories/{story_id}
POST   /api/v1/nrcs/stories/{story_id}/sync
GET    /api/v1/nrcs/stories/{story_id}/versions
POST   /api/v1/nrcs/stories/{story_id}/publish
```

### Rundown Synchronization
```http
GET    /api/v1/nrcs/rundowns
POST   /api/v1/nrcs/rundowns/sync
GET    /api/v1/nrcs/rundowns/{rundown_id}
PUT    /api/v1/nrcs/rundowns/{rundown_id}
POST   /api/v1/nrcs/rundowns/{rundown_id}/execute
GET    /api/v1/nrcs/rundowns/{rundown_id}/timing
POST   /api/v1/nrcs/rundowns/{rundown_id}/reorder
```

### User & Assignment Management
```http
GET    /api/v1/nrcs/users
POST   /api/v1/nrcs/users/sync
GET    /api/v1/nrcs/users/{user_id}
GET    /api/v1/nrcs/assignments
POST   /api/v1/nrcs/assignments
PUT    /api/v1/nrcs/assignments/{assignment_id}
GET    /api/v1/nrcs/beats
POST   /api/v1/nrcs/beats
```

### Search & Archive
```http
GET    /api/v1/nrcs/search
POST   /api/v1/nrcs/search/advanced
GET    /api/v1/nrcs/archive/stories
GET    /api/v1/nrcs/archive/media
POST   /api/v1/nrcs/archive/export
GET    /api/v1/nrcs/wires
POST   /api/v1/nrcs/wires/ingest
```

### Analytics & Reporting
```http
GET    /api/v1/nrcs/analytics/usage
GET    /api/v1/nrcs/analytics/performance
GET    /api/v1/nrcs/reports/productivity
GET    /api/v1/nrcs/reports/compliance
POST   /api/v1/nrcs/reports/custom
```

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=nrcs-integration
SERVICE_PORT=8014
LOG_LEVEL=INFO
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mams_nrcs
REDIS_URL=redis://redis:6379/3

# Authentication
JWT_SECRET_KEY=nrcs-secret-key
JWT_ALGORITHM=HS256

# ENPS Configuration
ENPS_ENABLED=true
ENPS_SERVER=enps.newsroom.local
ENPS_PORT=9000
ENPS_DATABASE=ENPS_DB
ENPS_USER=mams_integration
ENPS_PASSWORD=secure_password
ENPS_LDAP_SERVER=ldap.newsroom.local

# Avid iNEWS Configuration
AVID_ENABLED=true
AVID_SERVER=inews.newsroom.local
AVID_PORT=21
AVID_FTP_USER=mams_avid
AVID_FTP_PASSWORD=avid_password
AVID_API_URL=http://inews-api.newsroom.local
AVID_API_KEY=avid_api_key

# Ross Inception Configuration
ROSS_ENABLED=true
ROSS_API_URL=https://inception.newsroom.local/api
ROSS_API_KEY=ross_api_key
ROSS_WEBSOCKET_URL=wss://inception.newsroom.local/ws
ROSS_USERNAME=mams_ross
ROSS_PASSWORD=ross_password

# Octopus Configuration
OCTOPUS_ENABLED=false
OCTOPUS_API_URL=https://octopus.newsroom.local/api
OCTOPUS_USERNAME=mams_octopus
OCTOPUS_PASSWORD=octopus_password
OCTOPUS_TENANT=newsroom_tenant

# Integration Settings
SYNC_INTERVAL_SECONDS=30
MAX_CONCURRENT_CONNECTIONS=10
RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
ARCHIVE_RETENTION_DAYS=365

# Feature Flags
ENABLE_REAL_TIME_SYNC=true
ENABLE_ARCHIVE_INTEGRATION=true
ENABLE_USER_SYNC=true
ENABLE_ASSIGNMENT_SYNC=true
ENABLE_WIRE_INGESTION=true
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)
- Network access to NRCS systems

### Development Setup

```bash
# Clone and navigate
cd services/nrcs-integration

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your NRCS system details

# Start infrastructure
docker-compose up postgres redis -d

# Run migrations
alembic upgrade head

# Start the service
python -m src.main
```

### Docker Setup

```bash
# Build and start
docker-compose up --build

# Check health
curl http://localhost:8014/api/v1/health
```

## NRCS System Configuration

### ENPS Setup

1. **Configure ENPS Database Connection**
   ```sql
   -- Create integration user
   CREATE USER mams_integration WITH PASSWORD 'secure_password';
   GRANT SELECT, INSERT, UPDATE ON ALL TABLES TO mams_integration;
   ```

2. **Enable ENPS API Access**
   - Configure TCP/IP connections
   - Set up message queue monitoring
   - Enable story notification events

3. **LDAP Integration**
   ```ldap
   # Configure LDAP bind user
   binddn: cn=mams,ou=services,dc=newsroom,dc=local
   bindpw: ldap_password
   base: ou=users,dc=newsroom,dc=local
   ```

### Avid iNEWS Setup

1. **FTP Access Configuration**
   ```ini
   [FTP]
   server = inews.newsroom.local
   port = 21
   passive = true
   timeout = 30
   ```

2. **API Key Generation**
   - Log into Avid Management Console
   - Generate API key for integration
   - Set appropriate permissions

3. **Directory Structure**
   ```
   /NEWSROOM/
   ├── STORIES/
   ├── TEMPLATES/
   ├── RUNDOWNS/
   └── ARCHIVE/
   ```

### Ross Inception Setup

1. **API Access**
   ```json
   {
     "client_id": "mams_integration",
     "client_secret": "ross_client_secret",
     "scopes": ["story_read", "story_write", "rundown_manage"]
   }
   ```

2. **WebSocket Configuration**
   - Enable real-time event notifications
   - Configure message filtering
   - Set up connection heartbeat

### Octopus Setup

1. **Tenant Configuration**
   ```json
   {
     "tenant_id": "newsroom_tenant",
     "api_version": "v2",
     "features": ["content_management", "publishing", "analytics"]
   }
   ```

2. **Publishing Channels**
   - Configure web publishing endpoints
   - Set up social media accounts
   - Enable mobile app integration

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific NRCS tests
pytest tests/test_enps_integration.py
pytest tests/test_avid_integration.py
pytest tests/test_ross_integration.py

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest --cov=src --cov-report=html
```

### Adding New NRCS System

1. **Create Adapter Class**
   ```python
   from src.adapters.base import NRCSAdapter
   
   class CustomNRCSAdapter(NRCSAdapter):
       async def connect(self):
           # Implementation
           pass
   ```

2. **Register Adapter**
   ```python
   # src/core/adapter_registry.py
   ADAPTERS = {
       'enps': ENPSAdapter,
       'avid': AvidAdapter,
       'ross': RossAdapter,
       'custom': CustomNRCSAdapter,
   }
   ```

3. **Add Configuration**
   ```python
   # src/core/config.py
   custom_enabled: bool = Field(False, env="CUSTOM_ENABLED")
   custom_api_url: str = Field("", env="CUSTOM_API_URL")
   ```

4. **Create Tests**
   ```python
   # tests/test_custom_integration.py
   class TestCustomIntegration:
       async def test_connection(self):
           # Test implementation
           pass
   ```

## Security

- **Authentication**: Multi-factor authentication for NRCS systems
- **Authorization**: Role-based access control for newsroom functions  
- **Encryption**: TLS/SSL for all external communications
- **Audit Logging**: Complete audit trail for all operations
- **IP Whitelisting**: Restrict access to authorized networks
- **Credential Management**: Secure storage of NRCS credentials

## Performance

- **Connection Pooling**: Efficient connection management for each NRCS
- **Async Processing**: Non-blocking operations for real-time sync
- **Caching Strategy**: Redis caching for frequently accessed data  
- **Batch Operations**: Bulk processing for large data sets
- **Load Balancing**: Distribute connections across multiple instances
- **Monitoring**: Real-time performance metrics and alerting

## Monitoring & Alerting

- **Health Checks**: Continuous monitoring of NRCS connections
- **Performance Metrics**: Response times and throughput tracking
- **Error Tracking**: Automated error detection and notification
- **Sync Status**: Real-time sync status for all connected systems
- **Usage Analytics**: NRCS usage patterns and optimization insights
- **Alert Thresholds**: Configurable alerts for system issues

This service provides comprehensive NRCS integration capabilities, enabling seamless workflow automation and content management across multiple newsroom systems while maintaining the flexibility to adapt to different newsroom requirements and protocols.