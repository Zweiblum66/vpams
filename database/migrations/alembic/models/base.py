"""
Base SQLAlchemy models for MAMS migrations
"""
from sqlalchemy import MetaData, Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Create metadata object for each database
users_metadata = MetaData()
assets_metadata = MetaData()
metadata_metadata = MetaData()
workflow_metadata = MetaData()
rights_metadata = MetaData()
audit_metadata = MetaData()

# Base classes for each database
UsersBase = declarative_base(metadata=users_metadata)
AssetsBase = declarative_base(metadata=assets_metadata)
MetadataBase = declarative_base(metadata=metadata_metadata)
WorkflowBase = declarative_base(metadata=workflow_metadata)
RightsBase = declarative_base(metadata=rights_metadata)
AuditBase = declarative_base(metadata=audit_metadata)

class TimestampMixin:
    """Mixin for adding timestamp columns"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UUIDMixin:
    """Mixin for adding UUID primary key"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)