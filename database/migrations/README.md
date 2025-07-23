# MAMS Database Migration Framework

This directory contains the Alembic-based database migration framework for the MAMS (Media Asset Management System) PostgreSQL databases.

## Overview

The migration framework provides:

- **Multi-database Support**: Manages migrations for all 6 PostgreSQL databases
- **Alembic Integration**: Uses Alembic for schema versioning and migrations
- **CLI Management**: Rich CLI interface for migration operations
- **Environment Management**: Supports different environments (dev, staging, prod)
- **Automated Migrations**: Can auto-generate migrations from model changes
- **Rollback Support**: Safe rollback to previous schema versions

## Database Structure

The framework manages migrations for these databases:

- **users**: User management, authentication, roles, permissions
- **assets**: Asset management, projects, collections, versions
- **metadata**: Flexible metadata schemas and validation
- **workflow**: Workflow engine, tasks, approvals, automation
- **rights**: Rights management, licensing, compliance
- **audit**: Audit logs, analytics, monitoring

## Quick Start

1. **Install Dependencies**:
   ```bash
   cd database/migrations
   make install
   # or
   pip install -r requirements.txt
   ```

2. **Initialize Migration Environment**:
   ```bash
   make init
   # or
   python scripts/migrate.py init
   ```

3. **Check Migration Status**:
   ```bash
   make status
   # or
   python scripts/migrate.py status
   ```

4. **Run Migrations**:
   ```bash
   make upgrade
   # or
   python scripts/migrate.py upgrade
   ```

## Migration CLI Usage

### Basic Commands

```bash
# Show migration status
python scripts/migrate.py status

# Show status for specific database
python scripts/migrate.py status --database users

# Upgrade all databases
python scripts/migrate.py upgrade

# Upgrade specific database
python scripts/migrate.py upgrade --database users

# Show migration history
python scripts/migrate.py history

# Show database information
python scripts/migrate.py info
```

### Creating Migrations

```bash
# Create new migration
python scripts/migrate.py revision --database users --message "Add new table"

# Auto-generate migration from model changes
python scripts/migrate.py revision --database users --message "Auto migration" --autogenerate

# Create empty migration
python scripts/migrate.py revision --database users --message "Custom migration"
```

### Migration Management

```bash
# Downgrade to specific revision
python scripts/migrate.py downgrade --database users --revision abc123

# Stamp database with revision (mark as migrated)
python scripts/migrate.py stamp --database users --revision head

# Generate SQL without executing
python scripts/migrate.py upgrade --sql
```

## Makefile Shortcuts

The included Makefile provides convenient shortcuts:

```bash
# Setup and status
make install          # Install dependencies
make init            # Initialize migration environment
make status          # Show migration status
make info            # Show database configuration

# Migration operations
make upgrade         # Upgrade all databases
make upgrade-db DB=users  # Upgrade specific database
make upgrade-sql     # Generate SQL for all databases

# Create migrations
make revision DB=users MSG="Add new table"
make auto-revision DB=users MSG="Auto migration"

# History and rollback
make history         # Show migration history
make downgrade REV=abc123  # Downgrade to revision

# Database-specific shortcuts
make users-status    # Show users database status
make users-upgrade   # Upgrade users database
make assets-status   # Show assets database status
make assets-upgrade  # Upgrade assets database
# ... (similar for other databases)
```

## Configuration

### Environment Variables

The migration framework uses these environment variables:

```bash
# Database URLs (override defaults)
export USERS_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_users"
export ASSETS_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_assets"
export METADATA_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_metadata"
export WORKFLOW_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_workflow"
export RIGHTS_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_rights"
export AUDIT_DATABASE_URL="postgresql://user:pass@localhost:5432/mams_audit"

# Target database for single-database operations
export MAMS_TARGET_DB="users"

# Run migrations for all databases
export MAMS_ALL_DATABASES="true"
```

### Configuration Files

- **alembic.ini**: Main Alembic configuration
- **alembic/env.py**: Environment configuration and multi-database support
- **alembic/script.py.mako**: Migration template
- **requirements.txt**: Python dependencies

## Migration Workflow

### Development

1. **Make Model Changes**: Update SQLAlchemy models
2. **Generate Migration**: `make auto-revision DB=users MSG="Add new field"`
3. **Review Migration**: Check generated migration file
4. **Test Migration**: `make upgrade-db DB=users`
5. **Test Rollback**: `make downgrade-db DB=users REV=previous`

### Production

1. **Test in Staging**: Run migrations in staging environment
2. **Generate SQL**: `make upgrade-sql` to review changes
3. **Backup Database**: Always backup before migrations
4. **Run Migration**: `make upgrade` or database-specific command
5. **Verify**: Check application functionality

## Migration File Structure

```
migrations/
├── alembic/
│   ├── versions/           # Migration files
│   │   └── 2024_01_15_1234_abc123_add_user_table.py
│   ├── env.py             # Environment configuration
│   ├── script.py.mako     # Migration template
│   └── models/            # SQLAlchemy models
│       ├── __init__.py
│       ├── base.py        # Base classes
│       ├── users.py       # User models
│       ├── assets.py      # Asset models
│       └── ...
├── scripts/
│   └── migrate.py         # CLI management script
├── alembic.ini           # Alembic configuration
├── requirements.txt      # Dependencies
├── Makefile             # Convenient shortcuts
└── README.md            # This file
```

## Writing Migrations

### Basic Migration

```python
"""Add user profile table

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bio', sa.Text()),
        sa.Column('avatar_url', sa.String(1024)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create index
    op.create_index('idx_user_profiles_user_id', 'user_profiles', ['user_id'])

def downgrade() -> None:
    # Drop table
    op.drop_table('user_profiles')
```

### Data Migration

```python
"""Migrate user data

Revision ID: xyz789
Revises: abc123
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xyz789'
down_revision = 'abc123'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Get connection
    connection = op.get_bind()
    
    # Migrate data
    connection.execute(
        sa.text("""
            INSERT INTO user_profiles (id, user_id, bio, created_at)
            SELECT gen_random_uuid(), id, 'Default bio', created_at
            FROM users
            WHERE id NOT IN (SELECT user_id FROM user_profiles)
        """)
    )

def downgrade() -> None:
    # Remove migrated data
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM user_profiles WHERE bio = 'Default bio'")
    )
```

## Best Practices

### Migration Safety

1. **Always Review**: Review auto-generated migrations before applying
2. **Test Rollbacks**: Ensure downgrade functions work correctly
3. **Backup First**: Always backup before running migrations
4. **Small Changes**: Keep migrations focused and atomic
5. **Data Validation**: Validate data after complex migrations

### Performance Considerations

1. **Index Management**: Add/remove indexes carefully
2. **Large Tables**: Use background operations for large tables
3. **Lock Minimization**: Minimize table locks during migrations
4. **Batch Operations**: Process large data changes in batches

### Development Workflow

1. **Feature Branches**: Create migrations in feature branches
2. **Squash Migrations**: Squash related migrations before merging
3. **Naming Convention**: Use descriptive migration names
4. **Documentation**: Document complex migrations

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check database URLs and connectivity
2. **Permission Errors**: Ensure proper database permissions
3. **Conflict Errors**: Resolve migration conflicts manually
4. **Rollback Failures**: Check downgrade functions

### Debug Commands

```bash
# Check database connections
python scripts/migrate.py info

# Show detailed migration history
python scripts/migrate.py history --verbose

# Generate SQL to review changes
python scripts/migrate.py upgrade --sql

# Check current revision
python scripts/migrate.py status --database users
```

### Recovery Procedures

```bash
# Reset to specific revision
python scripts/migrate.py downgrade --database users --revision abc123

# Stamp with revision (if migration table is corrupted)
python scripts/migrate.py stamp --database users --revision head

# Manual migration table repair
psql -d mams_users -c "DROP TABLE IF EXISTS alembic_version_users;"
python scripts/migrate.py stamp --database users --revision head
```

## Integration with CI/CD

### GitHub Actions

```yaml
# .github/workflows/migrations.yml
name: Database Migrations

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  migrations:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd database/migrations
        pip install -r requirements.txt
    
    - name: Run migrations
      run: |
        cd database/migrations
        python scripts/migrate.py upgrade
    
    - name: Check migration status
      run: |
        cd database/migrations
        python scripts/migrate.py status
```

### Docker Integration

```dockerfile
# Migration container
FROM python:3.11-slim

WORKDIR /app
COPY database/migrations/ .

RUN pip install -r requirements.txt

CMD ["python", "scripts/migrate.py", "upgrade"]
```

This migration framework provides a robust, scalable solution for managing database schema changes across all MAMS PostgreSQL databases.