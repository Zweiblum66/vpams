# MAMS Database Setup

This directory contains the database schema and initialization scripts for the MAMS (Media Asset Management System) PostgreSQL databases.

## Database Structure

MAMS uses multiple PostgreSQL databases for different services:

- **mams_users**: User management, authentication, and authorization
- **mams_assets**: Core asset management, projects, and collections
- **mams_metadata**: Flexible metadata schemas and vocabularies
- **mams_workflow**: Workflow engine and automation
- **mams_rights**: Rights management, licensing, and compliance
- **mams_audit**: Audit logs, analytics, and monitoring

## Quick Start

1. **Start PostgreSQL**:
   ```bash
   cd database
   docker-compose up -d
   ```

2. **Verify Database Creation**:
   ```bash
   docker exec -it mams_postgres psql -U postgres -c "\l"
   ```

3. **Access pgAdmin**:
   - URL: http://localhost:5050
   - Email: admin@mams.local
   - Password: pgadmin_password

## Database Users

- **postgres**: Admin user (password: postgres_admin_password)
- **mams_app**: Application user (password: mams_dev_password)
- **mams_readonly**: Read-only user (password: mams_readonly_password)

## Demo Users

The seed data creates the following demo users (all passwords are 'password123'):

- **admin@mams.demo**: Full system administrator
- **editor@mams.demo**: Content editor with create/edit permissions
- **viewer@mams.demo**: Read-only access
- **producer@mams.demo**: Project manager with approval permissions

## Schema Overview

### Users Database (mams_users)
- Organizations and multi-tenancy
- Users, roles, and permissions (RBAC)
- OAuth providers and sessions
- API keys management

### Assets Database (mams_assets)
- Projects and asset collections
- Asset versions and relationships
- Proxies and thumbnails
- Comments and collaboration
- Shot items for editorial workflows

### Metadata Database (mams_metadata)
- Flexible metadata schemas
- Controlled vocabularies
- AI-generated metadata
- Metadata extraction jobs

### Workflow Database (mams_workflow)
- Workflow templates and instances
- Task management and assignments
- Approval workflows
- Automation rules

### Rights Database (mams_rights)
- License agreements
- Model and property releases
- Copyright management
- Usage tracking and compliance

### Audit Database (mams_audit)
- Audit logs (partitioned by month)
- Access logs and analytics
- Performance metrics
- Compliance reporting

## Management Scripts

### Initialize/Reset Database
```bash
# Stop and remove existing data
docker-compose down -v

# Start fresh
docker-compose up -d
```

### Backup Database
```bash
# Backup all databases
docker exec mams_postgres pg_dumpall -U postgres > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific database
docker exec mams_postgres pg_dump -U postgres mams_assets > mams_assets_backup.sql
```

### Restore Database
```bash
# Restore all databases
docker exec -i mams_postgres psql -U postgres < backup.sql

# Restore specific database
docker exec -i mams_postgres psql -U postgres mams_assets < mams_assets_backup.sql
```

### Connect to Database
```bash
# Connect to PostgreSQL
docker exec -it mams_postgres psql -U postgres

# Connect to specific database
docker exec -it mams_postgres psql -U postgres -d mams_assets
```

## Development Tips

1. **Viewing Logs**:
   ```bash
   docker-compose logs -f postgres
   ```

2. **Running Custom SQL**:
   ```bash
   docker exec -it mams_postgres psql -U postgres -d mams_assets -c "SELECT * FROM assets LIMIT 10;"
   ```

3. **Schema Updates**:
   - Add new SQL files to `postgresql/schemas/`
   - They will be executed in alphabetical order on container startup

4. **Performance Monitoring**:
   ```sql
   -- Check database sizes
   SELECT pg_database.datname, 
          pg_size_pretty(pg_database_size(pg_database.datname)) AS size
   FROM pg_database;
   
   -- Check table sizes
   SELECT schemaname AS table_schema,
          tablename AS table_name,
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

## Production Considerations

1. **Security**:
   - Change all default passwords
   - Use SSL/TLS connections
   - Implement network isolation
   - Regular security audits

2. **Performance**:
   - Configure connection pooling
   - Tune PostgreSQL parameters
   - Set up read replicas
   - Implement proper indexing

3. **Backup Strategy**:
   - Automated daily backups
   - Point-in-time recovery
   - Off-site backup storage
   - Regular restore testing

4. **Monitoring**:
   - Set up pg_stat_statements
   - Configure slow query logging
   - Monitor disk usage
   - Track connection counts

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs postgres

# Verify permissions
ls -la postgresql/init/
```

### Connection Issues
```bash
# Test connection
docker exec -it mams_postgres pg_isready -U postgres

# Check network
docker network ls
```

### Performance Issues
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
AND n_distinct > 100
AND correlation < 0.1
ORDER BY n_distinct DESC;
```