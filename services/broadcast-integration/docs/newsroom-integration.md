# Newsroom Integration Guide

## Overview

The Broadcast Integration Service provides comprehensive newsroom integration capabilities that extend beyond the MOS protocol. This service focuses on production workflows, editorial processes, and live broadcast management.

## Key Features

### 1. Rundown Management

The service provides complete rundown lifecycle management:

- **Creation and Planning**: Build rundowns from scratch or templates
- **Story Management**: Add, edit, reorder, and delete stories
- **Timing Calculations**: Automatic duration tracking and backtime/fronttime calculations
- **Version Control**: Track changes and maintain rundown history
- **Multi-User Collaboration**: Real-time updates for concurrent editing

### 2. Script Engine

Advanced teleprompter and script management:

- **Rich Text Editing**: Full formatting support for scripts
- **Multi-Language Support**: Handle scripts in any language
- **Reading Speed Calculations**: Estimate duration based on WPM
- **Cue Points**: Mark important moments in scripts
- **Version History**: Track all script changes

### 3. Editorial Workflows

Complete editorial approval system:

- **Multi-Level Approvals**: Editorial, legal, and technical reviews
- **Conditional Approvals**: Set conditions that must be met
- **Audit Trail**: Complete history of all approval actions
- **Notification System**: Alert relevant parties of pending approvals

### 4. Graphics Integration

Manage all broadcast graphics:

- **Lower Thirds**: Name supers and identification graphics
- **Tickers/Crawlers**: Breaking news and information crawls
- **Full-Screen Graphics**: Maps, charts, and data visualizations
- **Template System**: Reusable graphics templates
- **Preview Capability**: See graphics before going to air

### 5. Live Production Support

Real-time broadcast features:

- **On-Air Tracking**: Monitor what's currently broadcasting
- **Breaking News**: Insert urgent content into live shows
- **Countdown Timers**: Track time to next element
- **Remote Contributions**: Manage live shots and remote feeds
- **Studio Status**: Monitor readiness of all production elements

### 6. Automation Integration

Connect with broadcast automation systems:

- **Camera Control**: Trigger camera presets and movements
- **Audio Routing**: Control audio sources and mixing
- **Graphics Triggering**: Automated graphics playout
- **Timing Synchronization**: Keep all systems in sync
- **Device Control**: Interface with production equipment

## Newsroom System Support

### ENPS (Associated Press)

```python
# ENPS Configuration
ENPS_ENABLED=true
ENPS_API_URL=http://enps.newsroom.local/api
ENPS_API_KEY=your-enps-api-key
```

Features:
- Bi-directional rundown sync
- Story updates in real-time
- Wire service integration
- Assignment management

### Avid iNEWS

```python
# Avid Configuration
AVID_ENABLED=true
AVID_API_URL=http://inews.newsroom.local/api
AVID_API_KEY=your-avid-api-key
```

Features:
- iNEWS Command protocol support
- MediaCentral integration
- Shared storage access
- Collaborative editing

### Ross Inception

```python
# Ross Configuration
ROSS_ENABLED=true
ROSS_API_URL=http://inception.newsroom.local/api
ROSS_API_KEY=your-ross-api-key
```

Features:
- Inception API integration
- OverDrive automation sync
- XPression graphics control
- Video server integration

### Octopus Newsroom

```python
# Octopus Configuration
OCTOPUS_ENABLED=true
OCTOPUS_API_URL=http://octopus.newsroom.local/api
OCTOPUS_API_KEY=your-octopus-api-key
```

Features:
- NRCS8 protocol support
- Planning tool integration
- Resource management
- Mobile app sync

## Workflow Examples

### Creating a News Broadcast

1. **Create Rundown**
```http
POST /api/v1/broadcast/rundowns
{
  "title": "Evening News",
  "slug": "evening-news-2025-01-21",
  "show_date": "2025-01-21T18:00:00Z",
  "duration_seconds": 1800,
  "studio": "Studio A"
}
```

2. **Apply Template**
```http
POST /api/v1/broadcast/rundowns/{rundown_id}/apply-template
{
  "template_id": "standard-news-template"
}
```

3. **Add Stories**
```http
POST /api/v1/broadcast/rundowns/{rundown_id}/stories
{
  "slug": "lead-story",
  "title": "Breaking News Coverage",
  "duration_seconds": 180,
  "position": 0
}
```

4. **Create Script**
```http
POST /api/v1/broadcast/scripts
{
  "content": "Good evening, I'm John Doe...",
  "language": "en",
  "cue_points": [
    {"time": 10, "label": "Show graphic"},
    {"time": 45, "label": "Roll video"}
  ]
}
```

5. **Request Approval**
```http
POST /api/v1/broadcast/stories/{story_id}/approve
{
  "approval_type": "editorial",
  "comments": "Ready for review"
}
```

### Managing Live Production

1. **Get Live Status**
```http
GET /api/v1/broadcast/live/status
```

2. **Mark Story On-Air**
```http
PUT /api/v1/broadcast/live/on-air/{story_id}
```

3. **Insert Breaking News**
```http
POST /api/v1/broadcast/live/breaking-news
{
  "title": "Breaking: Major Event",
  "slug": "breaking-major-event",
  "duration_seconds": 120,
  "script_content": "We interrupt this program...",
  "interrupt_current": true
}
```

## Integration Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Newsroom      │────▶│   Broadcast     │────▶│     MAMS        │
│   Systems       │     │   Integration   │     │   Services      │
│                 │◀────│    Service      │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  MOS Protocol   │     │   WebSocket     │     │   Asset Mgmt    │
│  Communication  │     │   Real-time     │     │   Metadata      │
│                 │     │   Updates       │     │   Rights        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Best Practices

### 1. Rundown Organization

- Use consistent naming conventions
- Set accurate timing for all elements
- Tag content appropriately
- Lock rundowns when ready for air

### 2. Script Management

- Keep scripts concise and clear
- Mark all cue points accurately
- Use version control for changes
- Get approvals before broadcast

### 3. Graphics Coordination

- Preview all graphics before air
- Use templates for consistency
- Test data bindings
- Have backups ready

### 4. Live Production

- Monitor system status continuously
- Have contingency plans ready
- Communicate changes immediately
- Log all on-air events

## Performance Optimization

### Caching Strategy

- Cache rundown structures
- Store rendered graphics
- Keep script calculations
- Minimize database queries

### Real-time Updates

- Use WebSocket connections
- Batch updates when possible
- Prioritize critical changes
- Handle connection failures

### Database Optimization

- Index frequently queried fields
- Archive old rundowns regularly
- Optimize story ordering queries
- Use read replicas for reports

## Troubleshooting

### Common Issues

1. **Sync Delays**
   - Check network connectivity
   - Verify API credentials
   - Monitor message queues
   - Review error logs

2. **Missing Updates**
   - Confirm WebSocket connection
   - Check user permissions
   - Verify change notifications
   - Review audit logs

3. **Performance Issues**
   - Monitor database queries
   - Check cache hit rates
   - Review connection pools
   - Analyze response times

### Debug Tools

- Enable debug logging
- Use API monitoring
- Check system metrics
- Review audit trails

## Security Considerations

### Access Control

- Role-based permissions
- Rundown-level security
- Story approval rights
- System integration keys

### Data Protection

- Encrypt sensitive content
- Secure API communications
- Audit all changes
- Regular security reviews

## Future Enhancements

1. **AI-Powered Features**
   - Automatic script generation
   - Content suggestions
   - Timing optimization
   - Error detection

2. **Advanced Analytics**
   - Production metrics
   - Performance tracking
   - Audience engagement
   - Resource utilization

3. **Mobile Support**
   - Field reporter apps
   - Remote production tools
   - Mobile prompter
   - Approval workflows

4. **Cloud Integration**
   - Cloud-based production
   - Remote collaboration
   - Distributed workflows
   - Global syndication