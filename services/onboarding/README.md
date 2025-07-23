# Onboarding Service

## Overview

The Onboarding Service provides a comprehensive guided experience for new users and organizations joining MAMS. It handles initial setup, configuration, and training to ensure users can effectively use the platform from day one.

## Features

### Onboarding Flows
- New organization setup wizard
- User role-based onboarding paths
- Progressive disclosure of features
- Interactive tutorials and guides
- Completion tracking and analytics

### Organization Setup
- Company profile configuration
- Initial user invitations
- Department/team structure
- Storage configuration
- Integration setup

### User Onboarding
- Profile completion
- Role-specific training
- Feature walkthroughs
- Best practices guidance
- Certification paths

### Interactive Elements
- Step-by-step wizards
- Interactive tooltips
- Video tutorials
- Practice environments
- Knowledge checks

### Progress Tracking
- Onboarding completion metrics
- User engagement tracking
- Feature adoption analytics
- Success milestone monitoring
- Customizable goals

## Architecture

The Onboarding Service consists of:
- FastAPI backend for flow management
- PostgreSQL for progress tracking
- Redis for session management
- React components for UI
- Analytics integration

## API Endpoints

### Onboarding Flows
- `GET /api/v1/onboarding/flows` - List available flows
- `GET /api/v1/onboarding/flows/{flow_id}` - Get flow details
- `POST /api/v1/onboarding/flows/{flow_id}/start` - Start onboarding flow
- `PUT /api/v1/onboarding/flows/{flow_id}/progress` - Update progress
- `POST /api/v1/onboarding/flows/{flow_id}/complete` - Complete flow

### Steps Management
- `GET /api/v1/onboarding/steps` - List all steps
- `GET /api/v1/onboarding/steps/{step_id}` - Get step details
- `POST /api/v1/onboarding/steps/{step_id}/complete` - Mark step complete
- `POST /api/v1/onboarding/steps/{step_id}/skip` - Skip step

### Progress Tracking
- `GET /api/v1/onboarding/progress` - Get user progress
- `GET /api/v1/onboarding/analytics` - Get analytics data
- `GET /api/v1/onboarding/achievements` - Get achievements

### Tutorials
- `GET /api/v1/onboarding/tutorials` - List tutorials
- `GET /api/v1/onboarding/tutorials/{tutorial_id}` - Get tutorial
- `POST /api/v1/onboarding/tutorials/{tutorial_id}/complete` - Complete tutorial

## Onboarding Flows

### 1. Organization Admin Flow
- Welcome and platform overview
- Organization profile setup
- User management basics
- Storage configuration
- Security settings
- Integration setup
- Billing configuration

### 2. Content Creator Flow
- Platform introduction
- Asset upload training
- Metadata best practices
- Search and discovery
- Collaboration features
- Workflow basics

### 3. Editor Flow
- Interface overview
- Project management
- Timeline and editing
- Review and approval
- Export options
- Keyboard shortcuts

### 4. Viewer Flow
- Navigation basics
- Search functionality
- Preview options
- Download permissions
- Sharing features

## Configuration

### Environment Variables

```env
# Service Configuration
SERVICE_NAME=onboarding-service
SERVICE_PORT=8019
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/onboarding

# Redis
REDIS_URL=redis://localhost:6379/9

# Analytics
ANALYTICS_ENABLED=true
SEGMENT_WRITE_KEY=your_segment_key

# Features
ENABLE_VIDEO_TUTORIALS=true
ENABLE_INTERACTIVE_GUIDES=true
ENABLE_PRACTICE_MODE=true
ENABLE_CERTIFICATIONS=true

# External Services
USER_SERVICE_URL=http://user-management:8001
ASSET_SERVICE_URL=http://asset-management:8004
```

## Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for frontend)

### Setup

```bash
# Backend setup
cd services/onboarding
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload

# Frontend setup
cd frontend/onboarding
npm install
npm run dev
```

### Testing

```bash
# Run backend tests
pytest tests/ -v --cov=src

# Run frontend tests
npm test
npm run test:e2e
```

## Onboarding Best Practices

1. **Progressive Disclosure**: Don't overwhelm users with all features at once
2. **Role-Based Paths**: Customize onboarding based on user roles
3. **Interactive Learning**: Use hands-on exercises and practice data
4. **Clear Progress**: Show users how far they've come and what's next
5. **Quick Wins**: Help users achieve something meaningful quickly
6. **Contextual Help**: Provide help where and when users need it
7. **Measure Success**: Track completion rates and user feedback

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8019/docs
- ReDoc: http://localhost:8019/redoc