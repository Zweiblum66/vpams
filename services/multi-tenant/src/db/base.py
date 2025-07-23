"""
Database base configuration for Multi-Tenant Service.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create base class for SQLAlchemy models
Base = declarative_base()

# Import all models to ensure they are registered
from .models import (
    Tenant, TenantDomain, TenantConfig, TenantUsage,
    TenantApiKey, TenantAuditLog
)