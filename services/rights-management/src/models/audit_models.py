"""
Database models for audit trails in Rights Management Service
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

from .audit_schemas import AuditAction, AuditResourceType

Base = declarative_base()


class AuditTrail(Base):
    """Audit trail database model"""
    __tablename__ = "audit_trails"
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_compliance", "compliance_relevant"),
        Index("idx_audit_security", "security_relevant"),
        Index("idx_audit_session", "session_id"),
        Index("idx_audit_timestamp_user", "timestamp", "user_id"),
        Index("idx_audit_timestamp_resource", "timestamp", "resource_type", "resource_id"),
    )
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Action and resource
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(SQLEnum(AuditResourceType), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    # User information
    user_id = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255))
    user_roles = Column(JSON, default=list)
    
    # Context information
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Change details
    old_values = Column(JSON)
    new_values = Column(JSON)
    changes_summary = Column(Text)
    
    # Additional metadata
    metadata = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    # Compliance and security
    compliance_relevant = Column(Boolean, default=False, nullable=False)
    security_relevant = Column(Boolean, default=False, nullable=False)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action.value if self.action else None,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "user_roles": self.user_roles or [],
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "changes_summary": self.changes_summary,
            "metadata": self.metadata or {},
            "tags": self.tags or [],
            "compliance_relevant": self.compliance_relevant,
            "security_relevant": self.security_relevant,
            "success": self.success,
            "error_message": self.error_message
        }
    
    def get_display_names(self) -> Dict[str, str]:
        """Get human-readable display names"""
        action_display = self.action.value.replace("_", " ").title() if self.action else "Unknown"
        resource_display = f"{self.resource_type.value.replace('_', ' ').title()} ({self.resource_id})" if self.resource_type else "Unknown"
        
        return {
            "action_display_name": action_display,
            "resource_display_name": resource_display
        }


class AuditArchive(Base):
    """Archived audit trail entries (for long-term storage)"""
    __tablename__ = "audit_archives"
    
    # Same structure as AuditTrail but for archived data
    id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Action and resource
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(SQLEnum(AuditResourceType), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    # User information
    user_id = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255))
    user_roles = Column(JSON, default=list)
    
    # Context information
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Change details
    old_values = Column(JSON)
    new_values = Column(JSON)
    changes_summary = Column(Text)
    
    # Additional metadata
    metadata = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    
    # Compliance and security
    compliance_relevant = Column(Boolean, default=False, nullable=False)
    security_relevant = Column(Boolean, default=False, nullable=False)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    
    # Archive metadata
    archived_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    archive_batch_id = Column(String(100))
    
    # Indexes for archived data (fewer indexes for storage efficiency)
    __table_args__ = (
        Index("idx_archive_timestamp", "timestamp"),
        Index("idx_archive_archived_at", "archived_at"),
        Index("idx_archive_user_id", "user_id"),
        Index("idx_archive_resource", "resource_type", "resource_id"),
    )