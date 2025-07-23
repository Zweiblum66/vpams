# GDPR Compliance Service

This service manages GDPR compliance for the MAMS platform, including user consent, data requests, privacy policies, and audit logging.

## Features

- **Consent Management**: Track and manage user consents for different data processing activities
- **Data Requests**: Handle GDPR data subject requests (access, portability, deletion, etc.)
- **Data Export**: Export user data in multiple formats (JSON, CSV, Excel, XML, PDF)
- **Right to be Forgotten**: Automated data deletion and anonymization
- **Privacy Policy Management**: Version control and acceptance tracking for privacy policies
- **Data Retention Policies**: Automated enforcement of data retention rules
- **Audit Logging**: Comprehensive audit trail for all GDPR-related activities
- **Compliance Reporting**: Generate detailed compliance reports with insights and recommendations
- **Audit Reporting**: Advanced analytics and reporting capabilities including:
  - Compliance scorecards with grade assessment
  - Risk identification and mitigation recommendations
  - Trend analysis over time
  - User activity patterns
  - Export in multiple formats (JSON, CSV, PDF, Excel)
  - Scheduled report generation
- **Data Classification**: Comprehensive data classification system including:
  - Data category management with privacy levels and retention rules
  - Field-level mapping of database columns to categories
  - Automatic PII detection and classification
  - Encryption requirement identification
  - Anonymization method suggestions
  - Data inventory and flow analysis
  - Compliance gap detection
- **Compliance Dashboards**: Real-time visualization and monitoring:
  - Overall compliance score with letter grades (A+ to F)
  - Interactive dashboard widgets for key metrics
  - Real-time risk assessment and mitigation recommendations
  - Consent management analytics with withdrawal trends
  - Data request compliance tracking
  - Retention policy execution monitoring
  - Audit activity visualization
  - Export dashboard data to PDF, Excel, or JSON
  - Customizable time ranges and widget configurations

## Architecture

The service follows the MAMS microservice architecture pattern:

```
src/
├── api/              # FastAPI routes and endpoints
├── core/             # Core configuration and security
├── db/               # Database models and configuration
├── models/           # Pydantic schemas
├── services/         # Business logic services
└── utils/            # Utility functions
```

## API Endpoints

### Consent Management
- `POST /api/v1/consent/` - Give consent
- `PATCH /api/v1/consent/{consent_id}` - Withdraw consent
- `GET /api/v1/consent/user/{user_id}` - Get user consents
- `GET /api/v1/consent/types` - List consent types

### Data Requests
- `POST /api/v1/data-requests/` - Create data request
- `POST /api/v1/data-requests/{request_id}/verify` - Verify request
- `GET /api/v1/data-requests/{request_id}` - Get request status
- `POST /api/v1/data-requests/{request_id}/cancel` - Cancel request
- `GET /api/v1/data-requests/user/{user_id}` - List user requests

### Privacy Policy
- `POST /api/v1/privacy-policy/` - Create policy (admin)
- `GET /api/v1/privacy-policy/current` - Get current policy
- `GET /api/v1/privacy-policy/version/{version}` - Get specific version
- `POST /api/v1/privacy-policy/accept` - Accept policy

### Audit Logs
- `GET /api/v1/audit/` - Query audit logs
- `GET /api/v1/audit/user/{user_id}/activity` - User activity report
- `GET /api/v1/audit/stats` - Audit statistics (admin)

### Admin
- `POST /api/v1/admin/categories` - Create data category
- `POST /api/v1/admin/mappings` - Create data mapping
- `GET /api/v1/admin/compliance/report` - Generate compliance report
- `GET /api/v1/admin/compliance/metrics` - Real-time metrics

### Data Retention
- `POST /api/v1/retention/rules` - Create retention rule
- `GET /api/v1/retention/rules` - List retention rules
- `GET /api/v1/retention/rules/{rule_id}` - Get specific rule
- `PATCH /api/v1/retention/rules/{rule_id}` - Update retention rule
- `DELETE /api/v1/retention/rules/{rule_id}` - Delete retention rule
- `POST /api/v1/retention/rules/{rule_id}/execute` - Execute specific rule
- `POST /api/v1/retention/execute-all` - Execute all due rules
- `POST /api/v1/retention/templates` - Create default templates
- `GET /api/v1/retention/statistics` - Get retention statistics

### Audit Reporting
- `POST /api/v1/reports/generate` - Generate comprehensive audit report
- `GET /api/v1/reports/compliance-score` - Get current compliance score
- `GET /api/v1/reports/trends` - Get compliance trends over time
- `GET /api/v1/reports/risks` - Get identified compliance risks
- `GET /api/v1/reports/quick-stats` - Get quick statistics for dashboard
- `GET /api/v1/reports/export/{report_type}` - Export report in various formats
- `POST /api/v1/reports/schedule` - Schedule automated reports
- `GET /api/v1/reports/schedules` - List scheduled reports
- `DELETE /api/v1/reports/schedule/{schedule_id}` - Delete scheduled report

### Data Classification
- `POST /api/v1/classification/categories` - Create data category
- `GET /api/v1/classification/categories` - List data categories
- `GET /api/v1/classification/categories/{category_id}` - Get specific category
- `PATCH /api/v1/classification/categories/{category_id}` - Update category
- `POST /api/v1/classification/mappings` - Create data mapping
- `GET /api/v1/classification/mappings` - List data mappings
- `GET /api/v1/classification/mappings/{mapping_id}` - Get specific mapping
- `GET /api/v1/classification/report` - Generate classification report
- `GET /api/v1/classification/inventory` - Get data inventory
- `POST /api/v1/classification/discover` - Discover and classify data
- `POST /api/v1/classification/categories/bulk` - Bulk create categories
- `POST /api/v1/classification/mappings/bulk` - Bulk create mappings
- `GET /api/v1/classification/templates/categories` - Get category templates
- `GET /api/v1/classification/templates/mappings/{table_name}` - Get mapping suggestions

### Compliance Dashboards
- `GET /api/v1/dashboard/overview` - Get comprehensive compliance dashboard
- `GET /api/v1/dashboard/classification` - Get data classification summary
- `GET /api/v1/dashboard/consent` - Get consent management metrics
- `GET /api/v1/dashboard/requests` - Get data request handling metrics
- `GET /api/v1/dashboard/retention` - Get retention policy metrics
- `GET /api/v1/dashboard/audit` - Get audit logging metrics
- `GET /api/v1/dashboard/widgets` - Get specific dashboard widgets
- `POST /api/v1/dashboard/export` - Export dashboard data
- `GET /api/v1/dashboard/quick-stats` - Get quick statistics
- `POST /api/v1/dashboard/refresh-cache` - Force refresh dashboard cache

## Configuration

Environment variables:

```env
# Service
SERVICE_NAME=gdpr-compliance
SERVICE_PORT=8012
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/gdpr
MONGODB_URL=mongodb://mongo:27017/mams
REDIS_URL=redis://redis:6379/0

# Security
JWT_SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# GDPR Settings
GDPR_DATA_RETENTION_DAYS=2555
GDPR_DELETION_GRACE_PERIOD_DAYS=30
GDPR_EXPORT_TIMEOUT_MINUTES=60
RETENTION_SCHEDULER_INTERVAL_MINUTES=60

# Email
EMAIL_ENABLED=true
SMTP_HOST=mailhog
SMTP_PORT=1025
```

## Data Models

### UserConsent
Tracks user consent for different types of data processing.

### DataRequest
Manages GDPR data subject requests (access, deletion, etc.).

### DataCategory
Classifies types of personal data collected with:
- Privacy levels (public, internal, confidential, restricted, top_secret)
- Retention periods and deletion methods
- Sensitivity flags and consent requirements
- Legal basis and purpose documentation
- Third-party sharing tracking

### DataMapping
Maps database fields to data categories for:
- PII identification and tracking
- Encryption requirement flags
- Anonymization method configuration
- Export/import control
- Automated classification support

### PrivacyPolicy
Version-controlled privacy policies.

### GDPRAuditLog
Comprehensive audit trail for compliance.

## Running the Service

### Development
```bash
docker-compose up gdpr-compliance
```

### Testing
```bash
docker-compose run gdpr-compliance pytest
```

### Database Migrations
```bash
docker-compose run gdpr-compliance alembic upgrade head
```

## Security Considerations

- All data exports are encrypted by default
- Verification required for sensitive operations (deletion, export)
- Rate limiting on all endpoints
- Comprehensive audit logging
- Role-based access control

## Compliance Features

- **Data Minimization**: Only collect necessary data
- **Purpose Limitation**: Track purpose for each data category
- **Storage Limitation**: Automated retention policies
- **Integrity & Confidentiality**: Encryption and access controls
- **Accountability**: Complete audit trail

## Audit Report Types

The service provides several types of compliance reports:

### 1. Compliance Overview
Comprehensive GDPR compliance status including:
- Overall compliance score and grade (A+ to F)
- Event statistics and success rates
- Data request handling metrics
- Consent management analysis
- Risk indicators and recommendations

### 2. User Activity Report
Analysis of user interactions with the system:
- Most active users and their event counts
- Hourly activity patterns
- Common actions performed
- Peak activity times

### 3. Data Requests Report
Detailed metrics on GDPR data subject requests:
- Request types and volumes
- Average completion times
- Compliance with 30-day deadline
- Request status breakdown

### 4. Consent Analysis
In-depth analysis of consent management:
- Active consents by type
- Withdrawal rates and trends
- Explicit vs implicit consent ratios
- Consent lifecycle tracking

### 5. Risk Assessment
Identification and assessment of compliance risks:
- Critical and high-priority risks
- Impact and likelihood analysis
- Mitigation recommendations
- Risk categories and trends

### 6. Incident Log
Security and compliance incident tracking:
- Failed operations
- Unauthorized access attempts
- Data breach incidents
- System errors affecting compliance

## Data Classification

The data classification system helps ensure GDPR compliance by:

### Key Features
1. **Data Categories**: Define types of data with privacy levels and retention rules
2. **Field Mapping**: Map database columns to categories for tracking
3. **Automatic Classification**: AI-powered detection of PII and sensitive data
4. **Compliance Analysis**: Identify gaps and generate recommendations
5. **Data Inventory**: Complete overview of all classified data

### Privacy Levels
- **Public**: Data that can be freely shared
- **Internal**: Data for internal use only
- **Confidential**: Restricted access required
- **Restricted**: High-security data with limited access
- **Top Secret**: Maximum security level

### Initialization
Run the initialization script to set up default categories and mappings:
```bash
docker-compose run gdpr-compliance python scripts/init_data_classification.py
```

This creates default categories for:
- User Identification
- Contact Information
- Personal Details
- Authentication Data
- Financial Information
- Usage Analytics
- Media Content
- System Logs
- Marketing Preferences
- Location Data

## Compliance Dashboard

The GDPR compliance dashboard provides comprehensive monitoring and visualization:

### Dashboard Components

1. **Compliance Score**
   - Overall compliance score (0-100) with letter grade (A+ to F)
   - Component scores for different compliance areas
   - Real-time calculation based on multiple factors

2. **Key Metrics**
   - Active consents count with trends
   - Pending data requests with overdue alerts
   - Request compliance rate (% completed within 30 days)
   - Data categories and classification coverage

3. **Risk Indicators**
   - Automatic detection of compliance risks
   - Severity levels (low, medium, high)
   - Mitigation recommendations
   - Affected items count

4. **Interactive Widgets**
   - Gauge charts for compliance scores
   - Pie charts for data distribution
   - Bar charts for categorical analysis
   - Line charts for trend visualization
   - Heatmaps for activity patterns

5. **Time-based Analysis**
   - Configurable time ranges (1-365 days)
   - Historical trend analysis
   - Comparative period metrics

### Dashboard Views

- **Overview**: Complete compliance status at a glance
- **Classification**: Data inventory and privacy levels
- **Consent**: User consent analytics
- **Requests**: Data request handling performance
- **Retention**: Data lifecycle management
- **Audit**: System activity and security events

### Export Options

- **PDF**: Professional compliance reports
- **Excel**: Detailed data for further analysis
- **JSON**: Raw data for system integration

## Integration

The service integrates with:
- User Management Service for authentication
- Storage Service for export files
- All other services for data collection/deletion