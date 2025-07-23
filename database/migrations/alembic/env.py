"""
Alembic Environment Configuration for MAMS
Supports multiple databases for different services
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Database configurations
DATABASES = {
    'users': {
        'url': os.getenv('USERS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_users'),
        'schema_file': '../../postgresql/schemas/02-users-schema.sql'
    },
    'assets': {
        'url': os.getenv('ASSETS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_assets'),
        'schema_file': '../../postgresql/schemas/03-assets-schema.sql'
    },
    'metadata': {
        'url': os.getenv('METADATA_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_metadata'),
        'schema_file': '../../postgresql/schemas/04-metadata-schema.sql'
    },
    'workflow': {
        'url': os.getenv('WORKFLOW_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_workflow'),
        'schema_file': '../../postgresql/schemas/05-workflow-schema.sql'
    },
    'rights': {
        'url': os.getenv('RIGHTS_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_rights'),
        'schema_file': '../../postgresql/schemas/06-rights-schema.sql'
    },
    'audit': {
        'url': os.getenv('AUDIT_DATABASE_URL', 'postgresql://mams_app:mams_dev_password@localhost:5432/mams_audit'),
        'schema_file': '../../postgresql/schemas/07-audit-schema.sql'
    }
}

# Get the target database from environment or command line
target_db = os.getenv('MAMS_TARGET_DB', 'users')

# Validate target database
if target_db not in DATABASES:
    raise ValueError(f"Invalid target database: {target_db}. Available: {list(DATABASES.keys())}")

# Set the database URL for the target
config.set_main_option('sqlalchemy.url', DATABASES[target_db]['url'])

# Import models based on target database
target_metadata = None

def get_metadata_for_database(db_name):
    """Get SQLAlchemy metadata for a specific database"""
    if db_name == 'users':
        from models.users import metadata
        return metadata
    elif db_name == 'assets':
        from models.assets import metadata
        return metadata
    elif db_name == 'metadata':
        from models.metadata import metadata
        return metadata
    elif db_name == 'workflow':
        from models.workflow import metadata
        return metadata
    elif db_name == 'rights':
        from models.rights import metadata
        return metadata
    elif db_name == 'audit':
        from models.audit import metadata
        return metadata
    else:
        return None

# Try to get metadata for the target database
try:
    target_metadata = get_metadata_for_database(target_db)
except ImportError:
    # If models are not available, metadata will be None
    # This is fine for initial setup or when running without models
    target_metadata = None

def get_url():
    """Get database URL for current target"""
    return DATABASES[target_db]['url']

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=f"alembic_version_{target_db}",
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=f"alembic_version_{target_db}",
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

def run_migrations_for_all_databases():
    """Run migrations for all databases"""
    original_target = target_db
    
    for db_name in DATABASES.keys():
        print(f"\n--- Running migrations for {db_name} database ---")
        os.environ['MAMS_TARGET_DB'] = db_name
        
        # Update global target_db
        globals()['target_db'] = db_name
        
        # Update metadata
        globals()['target_metadata'] = get_metadata_for_database(db_name)
        
        # Update config
        config.set_main_option('sqlalchemy.url', DATABASES[db_name]['url'])
        
        # Run migrations
        if context.is_offline_mode():
            run_migrations_offline()
        else:
            run_migrations_online()
    
    # Restore original target
    os.environ['MAMS_TARGET_DB'] = original_target

# Check if we should run for all databases
if os.getenv('MAMS_ALL_DATABASES', '').lower() == 'true':
    run_migrations_for_all_databases()
else:
    # Run for single database
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()