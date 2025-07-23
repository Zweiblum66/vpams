# Playout Integration Service

A comprehensive service for integrating with broadcast playout systems, providing automated content delivery and scheduling for the MAMS (Media Asset Management System) project.

## Overview

The Playout Integration Service enables seamless integration with various broadcast playout systems, allowing automated content scheduling, delivery, and monitoring. It supports multiple playout vendors and provides a unified interface for content distribution.

### Key Features

- **Multi-Vendor Support**: Integration with major playout system vendors
- **Automated Content Delivery**: Push content to playout servers automatically
- **Schedule Management**: Create and manage playout schedules
- **Clip Preparation**: Format conversion and technical validation
- **Status Monitoring**: Real-time playout status and health checks
- **Failover Support**: Redundancy and disaster recovery features
- **Graphics Integration**: Support for graphics and branding elements
- **As-Run Logs**: Capture and process as-run information
- **Quality Control**: Pre-flight checks and validation

## Supported Playout Systems

### 1. Grass Valley

- **K2 Summit/Solo**: Media server integration
- **Stratus**: Workflow automation
- **Ignite**: Integrated playout platform
- **AMPP**: Cloud-based playout

### 2. Harmonic

- **Spectrum X**: Advanced playout system
- **Polaris**: Integrated channel playout
- **VOS**: Cloud-native media processing

### 3. Imagine Communications

- **Versio**: Integrated playout platform
- **ADC**: Automation and device control
- **Nexio**: Media server platform

### 4. Evertz

- **Mediator-X**: Playout automation
- **OvertureRT**: Real-time playout engine
- **BRAVO**: Studio automation

### 5. Pebble Beach Systems

- **Marina**: Automation system
- **Lighthouse**: Content management
- **Neptune**: Integrated channel playout

### 6. PlayBox Technology

- **AirBox**: Channel playout
- **TitleBox**: Graphics and CG
- **ListBox**: Playlist preparation

### 7. Aveco

- **ASTRA**: Studio automation
- **Redwood**: News production
- **MCR**: Master control automation

### 8. Generic Interfaces

- **VDCP**: Video Disk Control Protocol
- **MOS**: Media Object Server (for rundown integration)
- **BXF**: Broadcast eXchange Format
- **MRSS**: Media RSS for content syndication

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MAMS Core     │────▶│    Playout      │────▶│  Playout        │
│   Services      │     │  Integration    │     │  Systems        │
└─────────────────┘     │    Service      │     └─────────────────┘
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Asset Service   │     │ Schedule Engine │     │ Device Control  │
│ Metadata        │     │ Content Prep    │     │ Status Monitor  │
│ Workflow        │     │ Delivery Queue  │     │ As-Run Logger   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Features

### 1. Schedule Management

- Create daily/weekly playout schedules
- Import schedules from traffic systems
- Schedule validation and conflict resolution
- Secondary event management
- Live event integration

### 2. Content Preparation

- Format conversion to playout requirements
- Audio level normalization
- Aspect ratio handling
- Closed caption insertion
- Subtitles and graphics overlay

### 3. Delivery Management

- Automated file transfer to playout servers
- Transfer queue management
- Bandwidth throttling
- Priority-based delivery
- Partial file delivery support

### 4. Device Control

- Remote control of playout devices
- Clip loading and cueing
- Play/stop/pause control
- Emergency take control
- Multi-channel management

### 5. Monitoring & Reporting

- Real-time playout status
- Content verification
- As-run log collection
- Discrepancy reporting
- Performance metrics

### 6. Redundancy & Failover

- Primary/backup server support
- Automatic failover detection
- Content synchronization
- Split-brain prevention
- Disaster recovery procedures

## API Endpoints

### Schedule Management

```http
GET    /api/v1/playout/schedules
POST   /api/v1/playout/schedules
GET    /api/v1/playout/schedules/{id}
PUT    /api/v1/playout/schedules/{id}
DELETE /api/v1/playout/schedules/{id}
POST   /api/v1/playout/schedules/{id}/validate
POST   /api/v1/playout/schedules/{id}/publish
```

### Content Delivery

```http
POST   /api/v1/playout/delivery/queue
GET    /api/v1/playout/delivery/status
POST   /api/v1/playout/delivery/{content_id}/transfer
DELETE /api/v1/playout/delivery/{content_id}/cancel
GET    /api/v1/playout/delivery/{content_id}/progress
```

### Device Control

```http
GET    /api/v1/playout/devices
GET    /api/v1/playout/devices/{id}/status
POST   /api/v1/playout/devices/{id}/control
POST   /api/v1/playout/devices/{id}/load
POST   /api/v1/playout/devices/{id}/cue
```

### Monitoring

```http
GET    /api/v1/playout/status
GET    /api/v1/playout/health
GET    /api/v1/playout/as-run/{date}
GET    /api/v1/playout/discrepancies
GET    /api/v1/playout/metrics
```

### System Configuration

```http
GET    /api/v1/playout/systems
POST   /api/v1/playout/systems
GET    /api/v1/playout/systems/{id}
PUT    /api/v1/playout/systems/{id}
DELETE /api/v1/playout/systems/{id}
POST   /api/v1/playout/systems/{id}/test
```

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=playout-integration
SERVICE_PORT=8013
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/playout
REDIS_URL=redis://localhost:6379/2

# Default Playout System
DEFAULT_PLAYOUT_SYSTEM=generic
DEFAULT_PLAYOUT_PROTOCOL=vdcp

# Transfer Settings
TRANSFER_MAX_CONCURRENT=5
TRANSFER_CHUNK_SIZE=10485760  # 10MB
TRANSFER_TIMEOUT_SECONDS=3600
TRANSFER_RETRY_COUNT=3

# Schedule Settings
SCHEDULE_LOOKAHEAD_DAYS=7
SCHEDULE_VALIDATION_ENABLED=true
SCHEDULE_AUTO_GAP_FILL=true

# Monitoring
MONITOR_INTERVAL_SECONDS=30
ASRUN_RETENTION_DAYS=90
METRICS_ENABLED=true
```

### Playout System Configuration

```yaml
# config/playout_systems.yaml
systems:
  - id: main_playout
    name: "Main Channel Playout"
    vendor: grass_valley
    type: k2_summit
    host: 192.168.1.100
    port: 1234
    protocol: vdcp
    channels:
      - channel: 1
        name: "HD Main"
      - channel: 2
        name: "SD Simulcast"
    
  - id: backup_playout
    name: "Backup Playout"
    vendor: harmonic
    type: spectrum_x
    api_url: https://harmonic.local/api
    api_key: ${HARMONIC_API_KEY}
    
  - id: news_playout
    name: "News Channel"
    vendor: evertz
    type: mediator_x
    connection_string: "evertz://news.local:7000"
```

## Integration Examples

### 1. Schedule Import from Traffic System

```python
# Import schedule from BXF file
POST /api/v1/playout/schedules/import
Content-Type: application/xml

<?xml version="1.0" encoding="UTF-8"?>
<BxfMessage>
  <BxfData>
    <Schedule>
      <ScheduledEvent>
        <EventData>
          <StartDateTime>2025-01-21T18:00:00</StartDateTime>
          <Duration>00:30:00</Duration>
          <Content>
            <ContentId>ASSET-12345</ContentId>
          </Content>
        </EventData>
      </ScheduledEvent>
    </Schedule>
  </BxfData>
</BxfMessage>
```

### 2. Content Delivery to Playout

```python
# Queue content for delivery
POST /api/v1/playout/delivery/queue
{
  "content_id": "ASSET-12345",
  "playout_system_id": "main_playout",
  "channel": 1,
  "delivery_time": "2025-01-21T17:00:00Z",
  "priority": "high",
  "technical_checks": {
    "validate_duration": true,
    "validate_format": true,
    "normalize_audio": true
  }
}
```

### 3. Device Control Commands

```python
# Load and cue content
POST /api/v1/playout/devices/main_playout/control
{
  "command": "load",
  "channel": 1,
  "content_id": "ASSET-12345",
  "in_point": "00:00:00:00",
  "out_point": "00:30:00:00",
  "preroll": 5
}

# Take to air
POST /api/v1/playout/devices/main_playout/control
{
  "command": "play",
  "channel": 1
}
```

## Content Preparation

### Technical Requirements

Different playout systems have specific technical requirements:

1. **Video Formats**
   - Codec: MPEG-2, H.264, XDCAM, ProRes
   - Resolution: SD, HD, UHD
   - Frame rate: 25fps, 29.97fps, 50fps, 59.94fps
   - Bit rate: System-specific requirements

2. **Audio Formats**
   - Channels: Stereo, 5.1, discrete tracks
   - Sample rate: 48kHz
   - Bit depth: 16-bit, 24-bit
   - Loudness: EBU R128, ATSC A/85

3. **Metadata Requirements**
   - House ID
   - Duration
   - Segment markers
   - Closed captions
   - Aspect ratio flags

### Validation Checks

Pre-delivery validation includes:

- Format compatibility
- Duration accuracy
- Audio level compliance
- Closed caption presence
- Aspect ratio verification
- GOP structure validation

## Monitoring and Alerts

### Health Monitoring

- Playout server connectivity
- Storage availability
- Transfer queue status
- Device responsiveness
- Network bandwidth

### Alert Conditions

- Content delivery failure
- Schedule conflicts
- Device offline
- Storage low
- As-run discrepancies

### Metrics Collection

- Content delivery times
- Transfer success rates
- Device uptime
- Schedule adherence
- Error frequencies

## Security

### Authentication

- API key authentication
- OAuth2 for user access
- Device-specific credentials
- Encrypted configuration

### Network Security

- VPN connections to playout networks
- Firewall rules for device control
- Encrypted file transfers
- Audit logging

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
uvicorn src.main:app --reload --port 8013
```

### Testing

```bash
# Run tests
pytest

# Test coverage
pytest --cov=src --cov-report=html

# Integration tests
pytest tests/integration/
```

## Troubleshooting

### Common Issues

1. **Content Delivery Failures**
   - Check network connectivity
   - Verify storage permissions
   - Validate content format
   - Review transfer logs

2. **Device Control Issues**
   - Confirm device IP/port
   - Check protocol compatibility
   - Verify credentials
   - Test with vendor tools

3. **Schedule Conflicts**
   - Review schedule validation
   - Check content duration
   - Verify time zones
   - Analyze gap reports

## Future Enhancements

1. **Cloud Playout Support**
   - AWS MediaLive integration
   - Azure Media Services
   - Google Cloud Video

2. **Advanced Features**
   - Dynamic ad insertion
   - Live graphics overlay
   - Multi-language audio
   - Interactive content

3. **AI Integration**
   - Predictive maintenance
   - Automated QC
   - Schedule optimization
   - Anomaly detection