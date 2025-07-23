# Customer Portal Service

## Overview

The Customer Portal Service provides a self-service interface for MAMS customers to manage their accounts, subscriptions, support tickets, and access resources.

## Features

### Account Management
- Organization profile management
- User management and invitations
- Billing information and invoices
- Subscription management
- Usage analytics and reporting

### Support Center
- Support ticket creation and tracking
- Knowledge base access
- Community forums
- Live chat integration
- Support history

### Resource Center
- Documentation access
- API keys management
- Download center
- Training materials
- Release notes

### Subscription Management
- Plan selection and upgrades
- Add-on management
- Usage monitoring
- Billing history
- Payment methods

### Analytics Dashboard
- Usage metrics and trends
- Storage consumption
- API usage statistics
- User activity reports
- Cost analysis

## Architecture

The Customer Portal is built as a microservice with:
- FastAPI backend with async support
- PostgreSQL for customer data
- Redis for caching and sessions
- Integration with other MAMS services
- React frontend (separate repository)

## API Endpoints

### Account Management
- `GET /api/v1/account` - Get account details
- `PUT /api/v1/account` - Update account information
- `GET /api/v1/account/users` - List organization users
- `POST /api/v1/account/users/invite` - Invite new users
- `DELETE /api/v1/account/users/{id}` - Remove user

### Subscription Management
- `GET /api/v1/subscription` - Get current subscription
- `GET /api/v1/subscription/plans` - List available plans
- `POST /api/v1/subscription/upgrade` - Upgrade subscription
- `GET /api/v1/subscription/usage` - Get usage statistics
- `GET /api/v1/subscription/invoices` - List invoices

### Support
- `GET /api/v1/support/tickets` - List support tickets
- `POST /api/v1/support/tickets` - Create new ticket
- `GET /api/v1/support/tickets/{id}` - Get ticket details
- `POST /api/v1/support/tickets/{id}/comments` - Add comment
- `GET /api/v1/support/kb/search` - Search knowledge base

### Resources
- `GET /api/v1/resources/docs` - List documentation
- `GET /api/v1/resources/downloads` - List downloads
- `GET /api/v1/resources/training` - List training materials
- `GET /api/v1/resources/api-keys` - Manage API keys

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose

### Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the service:
   ```bash
   uvicorn src.main:app --reload --port 8014
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/customer_portal

# Redis
REDIS_URL=redis://localhost:6379/0

# Service URLs
AUTH_SERVICE_URL=http://user-management:8001
BILLING_SERVICE_URL=http://billing:8015
SUPPORT_SERVICE_URL=http://support:8016

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-api-key

# Features
ENABLE_LIVE_CHAT=true
ENABLE_COMMUNITY_FORUM=true
ENABLE_SELF_SERVICE_UPGRADE=true
```

## Testing

Run tests:
```bash
pytest tests/ -v --cov=src --cov-report=html
```

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8014/docs
- ReDoc: http://localhost:8014/redoc