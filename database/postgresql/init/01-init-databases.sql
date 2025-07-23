-- MAMS PostgreSQL Database Initialization
-- This script creates the necessary databases and users for the MAMS microservices

-- Create application user
CREATE USER mams_app WITH PASSWORD 'mams_dev_password';

-- Create read-only user for reporting
CREATE USER mams_readonly WITH PASSWORD 'mams_readonly_password';

-- Create databases for each service that needs PostgreSQL
CREATE DATABASE mams_users;
CREATE DATABASE mams_assets;
CREATE DATABASE mams_metadata;
CREATE DATABASE mams_workflow;
CREATE DATABASE mams_rights;
CREATE DATABASE mams_audit;

-- Grant privileges to application user
GRANT CONNECT ON DATABASE mams_users TO mams_app;
GRANT CONNECT ON DATABASE mams_assets TO mams_app;
GRANT CONNECT ON DATABASE mams_metadata TO mams_app;
GRANT CONNECT ON DATABASE mams_workflow TO mams_app;
GRANT CONNECT ON DATABASE mams_rights TO mams_app;
GRANT CONNECT ON DATABASE mams_audit TO mams_app;

-- Grant read-only access
GRANT CONNECT ON DATABASE mams_users TO mams_readonly;
GRANT CONNECT ON DATABASE mams_assets TO mams_readonly;
GRANT CONNECT ON DATABASE mams_metadata TO mams_readonly;
GRANT CONNECT ON DATABASE mams_workflow TO mams_readonly;
GRANT CONNECT ON DATABASE mams_rights TO mams_readonly;
GRANT CONNECT ON DATABASE mams_audit TO mams_readonly;

-- Create extensions in each database
\c mams_users
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
GRANT ALL PRIVILEGES ON DATABASE mams_users TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;

\c mams_assets
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For compound indexes
GRANT ALL PRIVILEGES ON DATABASE mams_assets TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;

\c mams_metadata
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "hstore";    -- For key-value storage
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
GRANT ALL PRIVILEGES ON DATABASE mams_metadata TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;

\c mams_workflow
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
GRANT ALL PRIVILEGES ON DATABASE mams_workflow TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;

\c mams_rights
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist"; -- For exclusion constraints
GRANT ALL PRIVILEGES ON DATABASE mams_rights TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;

\c mams_audit
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_partman"; -- For table partitioning
GRANT ALL PRIVILEGES ON DATABASE mams_audit TO mams_app;
GRANT USAGE ON SCHEMA public TO mams_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mams_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mams_readonly;