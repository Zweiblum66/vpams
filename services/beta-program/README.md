# Beta Program Service

The Beta Program Service manages the MAMS platform beta testing program, including beta user registration, feature flags, feedback collection, and beta analytics.

## Features

- Beta user registration and invitation system
- Feature flag management for beta features
- Feedback collection and management
- Beta analytics and reporting
- A/B testing framework
- Beta user communication
- Release candidate management
- Beta program phases

## API Endpoints

### Beta Users
- `POST /api/v1/beta/register` - Register for beta program
- `POST /api/v1/beta/invite` - Send beta invitation
- `GET /api/v1/beta/users` - List beta users
- `GET /api/v1/beta/users/{user_id}` - Get beta user details
- `PUT /api/v1/beta/users/{user_id}` - Update beta user
- `DELETE /api/v1/beta/users/{user_id}` - Remove from beta

### Feature Flags
- `GET /api/v1/beta/features` - List beta features
- `GET /api/v1/beta/features/{feature_id}` - Get feature details
- `POST /api/v1/beta/features` - Create beta feature
- `PUT /api/v1/beta/features/{feature_id}` - Update feature
- `GET /api/v1/beta/features/user/{user_id}` - Get user's features

### Feedback
- `POST /api/v1/beta/feedback` - Submit feedback
- `GET /api/v1/beta/feedback` - List feedback
- `GET /api/v1/beta/feedback/{feedback_id}` - Get feedback details
- `PUT /api/v1/beta/feedback/{feedback_id}` - Update feedback

### Analytics
- `GET /api/v1/beta/analytics` - Get beta analytics
- `GET /api/v1/beta/analytics/usage` - Feature usage stats
- `GET /api/v1/beta/analytics/feedback` - Feedback analytics
- `GET /api/v1/beta/analytics/export` - Export analytics

## Environment Variables

```env
SERVICE_NAME=beta-program
SERVICE_PORT=8019
DATABASE_URL=postgresql://user:pass@postgres:5432/beta_program
REDIS_URL=redis://redis:6379/0
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=your-api-key
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run service
uvicorn src.main:app --reload --port 8019
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```