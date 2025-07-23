# Billing Service

## Overview

The Billing Service manages all financial aspects of MAMS including subscriptions, payments, invoicing, and revenue tracking. It integrates with payment processors, handles multiple currencies, and provides comprehensive financial reporting.

## Features

### Subscription Management
- Flexible subscription plans and tiers
- Usage-based billing support
- Proration and credits
- Trial period management
- Plan upgrades/downgrades
- Add-ons and feature flags

### Payment Processing
- Multiple payment methods (card, ACH, wire)
- PCI-compliant tokenization
- Automated recurring billing
- Payment retry logic
- Refunds and chargebacks
- Multi-currency support

### Invoice Generation
- Automated invoice creation
- Custom invoice templates
- Tax calculation
- PDF generation
- Email delivery
- Invoice history

### Revenue Management
- Revenue recognition
- Deferred revenue tracking
- MRR/ARR calculations
- Churn analytics
- Financial reporting
- Export to accounting systems

### Integrations
- Stripe payment processing
- PayPal support
- Tax calculation services
- Accounting software (QuickBooks, Xero)
- Dunning management
- Analytics platforms

## Architecture

The Billing Service is built as a microservice with:
- FastAPI backend for high performance
- PostgreSQL for transactional data
- Redis for caching and job queues
- Celery for background tasks
- Integration with payment gateways

## API Endpoints

### Subscriptions
- `POST /api/v1/subscriptions` - Create new subscription
- `GET /api/v1/subscriptions/{id}` - Get subscription details
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `POST /api/v1/subscriptions/{id}/cancel` - Cancel subscription
- `POST /api/v1/subscriptions/{id}/reactivate` - Reactivate subscription
- `POST /api/v1/subscriptions/{id}/change-plan` - Change subscription plan

### Payments
- `POST /api/v1/payments/methods` - Add payment method
- `GET /api/v1/payments/methods` - List payment methods
- `DELETE /api/v1/payments/methods/{id}` - Remove payment method
- `POST /api/v1/payments/charge` - One-time charge
- `GET /api/v1/payments/history` - Payment history
- `POST /api/v1/payments/refund` - Process refund

### Invoices
- `GET /api/v1/invoices` - List invoices
- `GET /api/v1/invoices/{id}` - Get invoice details
- `GET /api/v1/invoices/{id}/pdf` - Download invoice PDF
- `POST /api/v1/invoices/{id}/send` - Send invoice email
- `PUT /api/v1/invoices/{id}` - Update draft invoice
- `POST /api/v1/invoices/{id}/void` - Void invoice

### Billing Configuration
- `GET /api/v1/plans` - List available plans
- `GET /api/v1/plans/{id}` - Get plan details
- `GET /api/v1/tax-rates` - Get applicable tax rates
- `POST /api/v1/coupons/validate` - Validate coupon code
- `GET /api/v1/billing/settings` - Get billing settings

### Analytics
- `GET /api/v1/analytics/mrr` - Monthly recurring revenue
- `GET /api/v1/analytics/churn` - Churn metrics
- `GET /api/v1/analytics/revenue` - Revenue analytics
- `GET /api/v1/analytics/customers` - Customer metrics

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/billing

# Redis
REDIS_URL=redis://localhost:6379/5

# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# PayPal Configuration
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_WEBHOOK_ID=...

# Tax Services
TAXJAR_API_KEY=...
AVALARA_ACCOUNT_ID=...
AVALARA_LICENSE_KEY=...

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=...

# Features
ENABLE_USAGE_BILLING=true
ENABLE_MULTI_CURRENCY=true
ENABLE_TAX_CALCULATION=true
ENABLE_DUNNING=true

# Webhooks
WEBHOOK_RETRY_COUNT=3
WEBHOOK_TIMEOUT=30
```

## Security

- PCI DSS compliant architecture
- No storage of sensitive card data
- Tokenization through payment processors
- Encrypted communication with payment gateways
- Audit logging for all financial transactions
- Role-based access control
- Webhook signature verification

## Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
uvicorn src.main:app --reload --port 8015
```

### Testing

```bash
# Run tests
pytest tests/ -v --cov=src

# Run with test coverage
pytest tests/ -v --cov=src --cov-report=html
```

## Webhook Events

The billing service sends webhooks for:
- `subscription.created`
- `subscription.updated`
- `subscription.cancelled`
- `payment.succeeded`
- `payment.failed`
- `invoice.created`
- `invoice.paid`
- `invoice.overdue`

## Error Handling

All API endpoints return consistent error responses:
```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "Payment method declined due to insufficient funds",
    "details": {...}
  }
}
```

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8015/docs
- ReDoc: http://localhost:8015/redoc