# Broadcast Automation Service

A comprehensive broadcast automation service that provides integration with studio automation systems, production switchers, robotic cameras, graphics systems, and audio consoles for the MAMS (Media Asset Management System) project.

## Overview

The Broadcast Automation Service enables seamless control and automation of broadcast production equipment, allowing for sophisticated studio automation workflows, remote production capabilities, and integration with newsroom and playout systems.

### Key Features

- **Multi-Vendor Support**: Integration with major automation systems (Ross Overdrive, Grass Valley Ignite, Vizrt Mosart, Sony ELC)
- **Device Control**: Direct control of cameras, switchers, audio mixers, lighting, and graphics
- **Macro Automation**: Create and execute complex production sequences
- **Event Scheduling**: Time-based and trigger-based automation
- **Remote Production**: Control studio equipment from remote locations
- **Rundown Integration**: Sync with newsroom rundowns for automated production
- **Real-time Monitoring**: Equipment status and health monitoring
- **Failover Management**: Automatic failover and redundancy handling
- **Shot Recall**: Camera preset and shot management
- **Virtual Sets**: Integration with virtual studio systems

## Supported Equipment

### Production Switchers
- **Ross Video**: Carbonite, Acuity, Ultrix
- **Grass Valley**: K-Frame, Karrera, Kula
- **Sony**: MVS series, XVS series
- **Blackmagic**: ATEM series
- **NewTek**: TriCaster series

### Robotic Camera Systems
- **Ross Video**: Furio, CamBot, PT-CP
- **Vinten**: FH-145, Quattro, Vantage
- **Panasonic**: AW series PTZ cameras
- **Sony**: BRC series, FR7 PTZ
- **Mo-Sys**: StarTracker, VP Pro

### Audio Consoles
- **Calrec**: Apollo, Artemis, Summa
- **Studer**: Vista series
- **SSL**: System T, C series
- **Lawo**: mc² series
- **Yamaha**: CL/QL series, Rivage PM

### Graphics Systems
- **Vizrt**: Viz Engine, Viz Mosart
- **Ross Video**: XPression, Inception
- **ChyronHego**: Prime, Lyric
- **Avid**: Maestro Graphics
- **NewBlue**: Titler Live

### Lighting Control
- **ETC**: Eos family, Paradigm
- **MA Lighting**: grandMA3
- **Strand**: NEO Console
- **Avolites**: Titan series

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Newsroom      │    │    Playout      │    │   Production    │
│   Systems       │    │    Systems      │    │   Control       │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                       │
         └──────────────────────┴───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  Automation Service   │
                    ├───────────────────────┤
                    │  • Device Registry    │
                    │  • Protocol Adapters  │
                    │  • Macro Engine       │
                    │  • Event Scheduler    │
                    │  • Status Monitor     │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────────▼─────────┐
│   Switchers    │  │    Cameras      │  │   Audio/Graphics     │
├────────────────┤  ├─────────────────┤  ├──────────────────────┤
│ • Ross         │  │ • PTZ Control   │  │ • Audio Mixers       │
│ • Grass Valley │  │ • Robotic Arms  │  │ • Graphics Engines   │
│ • Sony         │  │ • Shot Recall   │  │ • Lighting Control   │
└────────────────┘  └─────────────────┘  └──────────────────────┘
```

## Features

### 1. Device Management
- Auto-discovery of compatible devices
- Device registration and configuration
- Connection pooling and management
- Protocol translation layer
- Real-time device status monitoring

### 2. Macro System
```yaml
# Example macro definition
macro:
  name: "News Open Sequence"
  triggers:
    - type: "time"
      value: "17:59:30"
    - type: "gpi"
      input: 1
  actions:
    - device: "switcher"
      command: "take"
      input: "cam1"
    - device: "audio"
      command: "fade_up"
      channel: 1
      level: 0
      duration: 2000
    - device: "graphics"
      command: "play"
      template: "news_open"
    - device: "lights"
      command: "recall_scene"
      scene: "news_set"
```

### 3. Camera Control
- PTZ (Pan/Tilt/Zoom) control
- Focus, iris, and color control
- Shot preset storage and recall
- Motion path programming
- Multi-camera synchronized moves
- Virtual camera integration

### 4. Switcher Integration
- Source selection and routing
- Transition control (cuts, dissolves, wipes)
- Key and DVE control
- Multi-layer composition
- Macro recording and playback
- Tally management

### 5. Audio Automation
- Fader control and automation
- Input routing and patching
- EQ and dynamics control
- Monitor mix management
- Microphone control (on/off/mute)
- Audio-follow-video

### 6. Graphics Control
- Template triggering
- Data binding for dynamic graphics
- Playlist management
- Animation control
- Multi-layer graphics composition
- Real-time data updates

### 7. Show Control
- Cue list management
- Time-based automation
- Event-driven triggers
- Manual override capability
- Rehearsal mode
- Emergency stop functionality

### 8. Remote Production
- Low-latency device control
- Bandwidth-optimized protocols
- Multi-site coordination
- Remote camera shading
- Centralized production control

## API Endpoints

### Device Management
```http
GET    /api/v1/automation/devices
POST   /api/v1/automation/devices
GET    /api/v1/automation/devices/{device_id}
PUT    /api/v1/automation/devices/{device_id}
DELETE /api/v1/automation/devices/{device_id}
POST   /api/v1/automation/devices/{device_id}/connect
POST   /api/v1/automation/devices/{device_id}/disconnect
GET    /api/v1/automation/devices/{device_id}/status
POST   /api/v1/automation/devices/discover
```

### Camera Control
```http
GET    /api/v1/automation/cameras
GET    /api/v1/automation/cameras/{camera_id}
POST   /api/v1/automation/cameras/{camera_id}/ptz
POST   /api/v1/automation/cameras/{camera_id}/focus
POST   /api/v1/automation/cameras/{camera_id}/iris
GET    /api/v1/automation/cameras/{camera_id}/presets
POST   /api/v1/automation/cameras/{camera_id}/presets
POST   /api/v1/automation/cameras/{camera_id}/recall/{preset_id}
POST   /api/v1/automation/cameras/{camera_id}/path
```

### Switcher Control
```http
GET    /api/v1/automation/switchers
GET    /api/v1/automation/switchers/{switcher_id}
POST   /api/v1/automation/switchers/{switcher_id}/take
POST   /api/v1/automation/switchers/{switcher_id}/auto
POST   /api/v1/automation/switchers/{switcher_id}/cut
GET    /api/v1/automation/switchers/{switcher_id}/sources
POST   /api/v1/automation/switchers/{switcher_id}/preview
POST   /api/v1/automation/switchers/{switcher_id}/key
POST   /api/v1/automation/switchers/{switcher_id}/dve
```

### Audio Control
```http
GET    /api/v1/automation/audio/mixers
GET    /api/v1/automation/audio/mixers/{mixer_id}
POST   /api/v1/automation/audio/mixers/{mixer_id}/fader
POST   /api/v1/automation/audio/mixers/{mixer_id}/mute
POST   /api/v1/automation/audio/mixers/{mixer_id}/route
GET    /api/v1/automation/audio/mixers/{mixer_id}/channels
POST   /api/v1/automation/audio/mixers/{mixer_id}/eq
POST   /api/v1/automation/audio/mixers/{mixer_id}/dynamics
```

### Macro Management
```http
GET    /api/v1/automation/macros
POST   /api/v1/automation/macros
GET    /api/v1/automation/macros/{macro_id}
PUT    /api/v1/automation/macros/{macro_id}
DELETE /api/v1/automation/macros/{macro_id}
POST   /api/v1/automation/macros/{macro_id}/execute
POST   /api/v1/automation/macros/{macro_id}/schedule
GET    /api/v1/automation/macros/{macro_id}/history
```

### Show Control
```http
GET    /api/v1/automation/shows
POST   /api/v1/automation/shows
GET    /api/v1/automation/shows/{show_id}
PUT    /api/v1/automation/shows/{show_id}
GET    /api/v1/automation/shows/{show_id}/cues
POST   /api/v1/automation/shows/{show_id}/cues
POST   /api/v1/automation/shows/{show_id}/go
POST   /api/v1/automation/shows/{show_id}/stop
POST   /api/v1/automation/shows/{show_id}/rehearse
```

### Real-time Control (WebSocket)
```javascript
// WebSocket endpoint for real-time control
ws://automation-service:8015/ws/control

// Message format
{
  "type": "control",
  "device": "camera_1",
  "command": "ptz",
  "params": {
    "pan": 45.0,
    "tilt": 10.0,
    "zoom": 2.5,
    "speed": 0.5
  }
}
```

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=automation-service
SERVICE_PORT=8015
LOG_LEVEL=INFO
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/mams_automation
REDIS_URL=redis://redis:6379/4

# Authentication
JWT_SECRET_KEY=automation-secret-key
JWT_ALGORITHM=HS256

# Device Discovery
ENABLE_AUTO_DISCOVERY=true
DISCOVERY_INTERVAL=300
DISCOVERY_TIMEOUT=30

# Protocol Settings
DEFAULT_CONTROL_PROTOCOL=tcp
CONTROL_TIMEOUT=5
COMMAND_RETRY_COUNT=3
HEARTBEAT_INTERVAL=10

# Switcher Configuration
SWITCHER_ENABLED=true
DEFAULT_SWITCHER_TYPE=ross
SWITCHER_CONNECTION_POOL_SIZE=5

# Camera Configuration
CAMERA_ENABLED=true
DEFAULT_CAMERA_PROTOCOL=visca
PTZ_SPEED_SCALE=1.0
PRESET_RECALL_TIMEOUT=10

# Audio Configuration
AUDIO_ENABLED=true
DEFAULT_AUDIO_PROTOCOL=ember
AUDIO_FADE_CURVE=linear
DEFAULT_CROSSFADE_TIME=1000

# Graphics Configuration
GRAPHICS_ENABLED=true
DEFAULT_GRAPHICS_PROTOCOL=viz
TEMPLATE_CACHE_SIZE=100

# Show Control
SHOW_CONTROL_ENABLED=true
CUE_PRELOAD_COUNT=5
EMERGENCY_STOP_GPI=16

# Remote Production
REMOTE_CONTROL_ENABLED=true
CONTROL_LATENCY_COMPENSATION=true
MAX_CONTROL_LATENCY_MS=200

# Monitoring
ENABLE_DEVICE_MONITORING=true
MONITORING_INTERVAL=5
ALERT_ON_DEVICE_FAILURE=true
```

## Device Protocol Support

### Camera Protocols
- **VISCA**: Sony and compatible PTZ cameras
- **Pelco-D/P**: Standard PTZ protocol
- **NDI**: Network Device Interface control
- **FreeD**: Camera tracking data
- **Ross PIX**: Ross robotic protocol
- **Vinten**: Vinten robotic systems

### Switcher Protocols
- **Ross Talk**: Ross Video switchers
- **GVG Native**: Grass Valley protocol
- **Sony BVS**: Sony switcher protocol
- **ATEM**: Blackmagic ATEM protocol
- **NDI**: NewTek TriCaster

### Audio Protocols
- **Ember+**: Lawo and compatible
- **CSCP**: Calrec Serial Control
- **Pro64**: Yamaha protocol
- **OSC**: Open Sound Control
- **MIDI**: Musical Instrument Digital Interface

### Graphics Protocols
- **Viz Control**: Vizrt graphics
- **MOS**: Media Object Server
- **Ross Talk**: XPression control
- **CII**: ChyronHego protocol

## Macro Examples

### News Show Automation
```yaml
name: "Evening News Automation"
description: "Full automation for evening news broadcast"
triggers:
  - type: "schedule"
    time: "18:00:00"
    days: ["mon", "tue", "wed", "thu", "fri"]

sequences:
  - name: "pre_show"
    start_offset: "-00:05:00"
    actions:
      - {device: "lights", command: "scene", scene: "news_warmup"}
      - {device: "cameras", command: "home_all"}
      - {device: "graphics", command: "load_show", show: "evening_news"}
      
  - name: "show_open"
    start_offset: "00:00:00"
    actions:
      - {device: "switcher", command: "take", source: "black"}
      - {device: "audio", command: "mute_all"}
      - {device: "graphics", command: "play", template: "countdown"}
      - {wait: 10}
      - {device: "switcher", command: "take", source: "cam1"}
      - {device: "audio", command: "unmute", channel: "host_mic"}
      - {device: "graphics", command: "play", template: "news_open"}
      - {device: "lights", command: "scene", scene: "news_live"}
```

### Virtual Production
```yaml
name: "Virtual Studio Setup"
description: "Configure virtual production environment"
actions:
  - device: "tracking"
    command: "calibrate"
    cameras: ["cam1", "cam2", "cam3"]
    
  - device: "render_engine"
    command: "load_set"
    set: "news_virtual_set_01"
    
  - device: "keyer"
    command: "configure"
    mode: "ultimatte"
    cameras: ["cam1", "cam2", "cam3"]
    
  - device: "lights"
    command: "match_virtual"
    reference: "virtual_set_lighting"
```

## Integration with MAMS

### Rundown Integration
- Sync with broadcast integration service
- Automatic macro generation from rundowns
- Story-based automation triggers
- Graphics data binding from stories

### Asset Management
- Link media assets to automation events
- Automatic proxy switching for previews
- Version control for graphics templates
- Shot sheet management

### User Management
- Role-based access control
- Operator permissions and restrictions
- Activity logging and audit trails
- Multi-level authorization

## Security

- **Device Authentication**: Secure device pairing and authentication
- **Command Authorization**: Role-based command execution
- **Encrypted Control**: TLS encryption for all control protocols
- **Network Isolation**: VLAN separation for production networks
- **Audit Logging**: Complete audit trail of all commands
- **Emergency Override**: Authenticated manual override capability

## Performance

- **Low Latency**: <50ms command execution time
- **High Throughput**: 1000+ commands per second
- **Scalability**: Horizontal scaling for large installations
- **Reliability**: 99.99% uptime with redundancy
- **Real-time**: Frame-accurate switching and control
- **Buffering**: Command queuing for network resilience

## Monitoring & Alerts

- **Device Health**: Real-time device status monitoring
- **Performance Metrics**: Command latency and throughput
- **Error Tracking**: Failed command logging and analysis
- **Alert System**: Multi-channel alerting (email, SMS, webhook)
- **Dashboard**: Real-time system overview
- **Predictive Maintenance**: Equipment failure prediction

This service provides comprehensive broadcast automation capabilities, enabling sophisticated production workflows while maintaining the flexibility and reliability required for live broadcast environments.