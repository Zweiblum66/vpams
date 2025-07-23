# MOS Integration Service

A comprehensive Media Object Server (MOS) protocol implementation for the MAMS (Media Asset Management System) project. This service enables seamless integration with newsroom computer systems (NRCS) for broadcast workflow automation.

## Overview

The MOS Integration Service implements the MOS Protocol 2.8.5 specification, providing a bridge between MAMS and newsroom systems like ENPS, Ross OpenMOS, Avid iNEWS, and other MOS-compatible systems.

### Key Features

- **Full MOS Protocol Support**: Complete implementation of MOS 2.8.5 specification
- **Multi-Connection Management**: Handle multiple NRCS connections simultaneously
- **Real-time Communication**: TCP-based server for live newsroom integration
- **Message Processing**: Parse, validate, and respond to all MOS message types
- **Database Integration**: Store and manage MOS objects, running orders, and messages
- **RESTful API**: Modern API for integration and monitoring
- **Health Monitoring**: Comprehensive monitoring and alerting capabilities

## MOS Protocol Features

### Supported Message Types

#### Object Messages
- `mosObj` - Media object creation and updates
- `mosObjCreate` - Explicit object creation
- `mosListAll` - Batch object transmission
- `mosReqObj` - Request specific object
- `mosReqAll` - Request all objects

#### Running Order Messages
- `roCreate` - Create new running order
- `roReplace` - Replace entire running order
- `roDelete` - Delete running order
- `roListAll` - List all running orders
- `roReqAll` - Request all running orders
- `roStoryAppend` - Add story to running order
- `roStoryInsert` - Insert story in running order
- `roStoryReplace` - Replace story content
- `roStoryDelete` - Remove story from running order
- `roReadyToAir` - Mark running order ready for broadcast

#### System Messages
- `heartbeat` - Connection health monitoring
- `mosAck` - Acknowledgment responses
- `mosMachineInfo` - System information exchange

### MOS Profiles Supported

- **Profile 0**: Basic MOS functionality
- **Profile 1**: Object management with metadata
- **Profile 2**: Running order management
- **Profile 3**: Item management within stories
- **Profile 4**: Advanced object operations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NRCS Client   │◄──►│  MOS TCP Server │◄──►│   MOS Service   │
│   (ENPS, etc)   │    │   (Port 10540)  │    │   (Core Logic)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   FastAPI Web   │    │   PostgreSQL    │
                       │   Server        │    │   Database      │
                       │   (Port 8011)   │    │                 │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   REST API      │    │     Redis       │
                       │   Management    │    │   (Caching)     │
                       └─────────────────┘    └─────────────────┘
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Development Setup

1. **Clone the repository**
   ```bash
   cd services/mos-integration
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start infrastructure services**
   ```bash
   docker-compose up postgres redis -d
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the service**
   ```bash
   python -m src.main
   ```

### Docker Setup

1. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

2. **Check service health**
   ```bash
   curl http://localhost:8011/health
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `MOS_SERVER_ID` | `mos01.mams.local` | MOS server identifier |
| `MOS_LISTEN_PORT` | `10540` | TCP port for MOS connections |
| `MOS_UPPER_PORT` | `10541` | Upper port for MOS protocol |
| `MOS_QUERY_PORT` | `10542` | Query port for MOS protocol |
| `MOS_HEARTBEAT_INTERVAL` | `30` | Heartbeat interval in seconds |
| `MOS_TIMEOUT` | `60` | Connection timeout in seconds |
| `LOG_LEVEL` | `INFO` | Logging level |

### Sample Configuration

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mams
REDIS_URL=redis://localhost:6379/0

# MOS Configuration
MOS_SERVER_ID=mams.broadcast.local
MOS_LISTEN_PORT=10540
MOS_HEARTBEAT_INTERVAL=30
MOS_TIMEOUT=60

# Security
MOS_AUTH_ENABLED=true
MOS_SHARED_SECRET=your-secure-secret-here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## API Documentation

### Health & Status Endpoints

```http
GET /health
GET /api/v1/mos/health
GET /api/v1/mos/stats
GET /server-info
```

### Connection Management

```http
GET /api/v1/mos/connections
GET /api/v1/mos/connections/{connection_id}
```

### Object Management

```http
GET /api/v1/mos/objects
GET /api/v1/mos/objects/{obj_id}
POST /api/v1/mos/objects
```

### Running Order Management

```http
GET /api/v1/mos/running-orders
GET /api/v1/mos/running-orders/{ro_id}
```

### Message Management

```http
GET /api/v1/mos/messages
POST /api/v1/mos/send-message
POST /api/v1/mos/broadcast
```

## NRCS Integration

### Connecting ENPS

1. Configure ENPS MOS settings:
   - MOS Server: `your-mams-server`
   - Port: `10540`
   - Server ID: `mams.broadcast.local`

2. Enable MOS profiles 0-4 in ENPS configuration

3. Test connection with heartbeat messages

### Connecting Other NRCS Systems

The service supports any MOS 2.8.5 compatible NRCS:

- **Ross Video OpenMOS**
- **Avid iNEWS**
- **Octopus Newsroom**
- **Custom MOS implementations**

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_xml_parser.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New MOS Message Types

1. Add message type to `models/schemas.py`
2. Create parser logic in `utils/xml_parser.py`
3. Add handler method to `services/mos_service.py`
4. Update message handler mapping
5. Add tests for new functionality

## Monitoring & Logging

### Structured Logging

The service uses structured logging with configurable formats:

```python
logger.info(
    "mos_message_processed",
    connection_id=connection_id,
    message_type=message_type,
    processing_time_ms=elapsed_time,
    status="success"
)
```

### Metrics

Prometheus metrics are available at `/metrics`:

- `mos_connections_total` - Total number of connections
- `mos_messages_processed_total` - Total messages processed
- `mos_objects_total` - Total MOS objects
- `mos_running_orders_total` - Total running orders

### Health Checks

- **Liveness**: `/health`
- **Readiness**: `/api/v1/mos/health`
- **Database**: Connection and query tests
- **Redis**: Connection and operation tests
- **MOS Server**: TCP server status

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check firewall settings for port 10540
   - Verify MOS server is running
   - Check network connectivity

2. **XML Parsing Errors**
   - Validate XML format
   - Check character encoding
   - Review MOS protocol compliance

3. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check connection string format
   - Ensure database exists

4. **Authentication Failures**
   - Check MOS shared secret configuration
   - Verify NRCS authentication settings
   - Review security logs

### Debug Mode

Enable debug logging for detailed troubleshooting:

```env
LOG_LEVEL=DEBUG
DEBUG=true
```

### Log Analysis

Important log events to monitor:

- Connection establishment/termination
- Message parsing errors
- Database transaction failures
- Heartbeat timeouts
- Authentication failures

## Security Considerations

### Authentication

- Shared secret authentication between NRCS and MOS server
- IP-based access control
- Connection validation

### Data Protection

- TLS encryption for API endpoints
- Secure storage of credentials
- Audit logging for all operations

### Network Security

- Firewall configuration for MOS ports
- VPN/private network deployment
- Rate limiting and connection limits

## Performance Tuning

### Database Optimization

- Connection pooling configuration
- Index optimization for queries
- Partition tables for message logs

### Message Processing

- Concurrent message handling
- Message queue for high throughput
- Async processing for non-blocking operations

### Memory Management

- Connection pooling limits
- Message size restrictions
- Garbage collection tuning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Ensure code quality checks pass
5. Submit a pull request

### Development Guidelines

- Follow existing code style
- Write comprehensive tests
- Update documentation
- Use conventional commit messages

## License

This project is part of the MAMS system and follows the project's licensing terms.

## Support

For support and questions:

- Check the troubleshooting section
- Review log files
- Contact the development team
- Submit issues via the project repository