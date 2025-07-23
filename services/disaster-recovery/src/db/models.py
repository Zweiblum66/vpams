"""
Database models for Disaster Recovery Service
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float, Boolean,
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class DisasterType(str, enum.Enum):
    """Types of disasters"""
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_FAILURE = "software_failure"
    NETWORK_OUTAGE = "network_outage"
    DATA_CORRUPTION = "data_corruption"
    CYBER_ATTACK = "cyber_attack"
    NATURAL_DISASTER = "natural_disaster"
    POWER_OUTAGE = "power_outage"
    HUMAN_ERROR = "human_error"
    PROVIDER_OUTAGE = "provider_outage"
    COMPLETE_DATACENTER_LOSS = "complete_datacenter_loss"


class BackupType(str, enum.Enum):
    """Backup types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"
    CONTINUOUS = "continuous"


class FailoverMode(str, enum.Enum):
    """Failover modes"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"


class RecoveryTier(str, enum.Enum):
    """Recovery priority tiers"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DisasterRecoveryPlan(Base):
    """Disaster recovery plan model"""
    __tablename__ = "dr_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    recovery_tiers = Column(JSON, nullable=False)  # {service_name: tier}
    contact_list = Column(JSON, nullable=False)  # Emergency contacts
    activation_criteria = Column(JSON)  # Criteria for activating DR plan
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    backup_strategies = relationship("BackupStrategy", back_populates="plan")
    failover_procedures = relationship("FailoverProcedure", back_populates="plan")
    recovery_tests = relationship("RecoveryTest", back_populates="plan")
    recovery_metrics = relationship("RecoveryMetrics", back_populates="plan")
    disaster_events = relationship("DisasterEvent", back_populates="plan")
    
    __table_args__ = (
        Index('idx_dr_plans_active', 'is_active'),
    )


class BackupStrategy(Base):
    """Backup strategy configuration"""
    __tablename__ = "backup_strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    service_name = Column(String(100), nullable=False)
    backup_type = Column(SQLEnum(BackupType), nullable=False)
    frequency = Column(String(100), nullable=False)  # Cron expression
    retention_days = Column(Integer, nullable=False)
    storage_locations = Column(JSON, nullable=False)  # List of storage locations
    encryption_enabled = Column(Boolean, default=True)
    compression_enabled = Column(Boolean, default=True)
    verification_enabled = Column(Boolean, default=True)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    plan = relationship("DisasterRecoveryPlan", back_populates="backup_strategies")
    backup_jobs = relationship("BackupJob", back_populates="strategy")
    
    __table_args__ = (
        UniqueConstraint('plan_id', 'service_name', name='uq_backup_strategy_service'),
        Index('idx_backup_strategies_plan_service', 'plan_id', 'service_name'),
    )


class BackupJob(Base):
    """Backup job execution record"""
    __tablename__ = "backup_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('backup_strategies.id'))
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    service_name = Column(String(100), nullable=False)
    backup_type = Column(SQLEnum(BackupType), nullable=False)
    status = Column(String(50), nullable=False)  # in_progress, completed, failed
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    storage_location = Column(String(500))
    size_bytes = Column(Integer)
    checksum = Column(String(255))
    error_message = Column(Text)
    metadata = Column(JSON)
    
    # Relationships
    strategy = relationship("BackupStrategy", back_populates="backup_jobs")
    
    __table_args__ = (
        Index('idx_backup_jobs_status', 'status'),
        Index('idx_backup_jobs_service_time', 'service_name', 'start_time'),
    )


class FailoverProcedure(Base):
    """Failover procedure configuration"""
    __tablename__ = "failover_procedures"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    service_name = Column(String(100), nullable=False)
    failover_mode = Column(SQLEnum(FailoverMode), nullable=False)
    primary_region = Column(String(50), nullable=False)
    failover_regions = Column(JSON, nullable=False)  # List of failover regions
    health_check_url = Column(String(500))
    failover_steps = Column(JSON, nullable=False)  # List of steps
    rollback_steps = Column(JSON)  # List of rollback steps
    validation_steps = Column(JSON)  # List of validation steps
    notification_channels = Column(JSON)  # List of notification channels
    auto_failover_threshold = Column(Integer, default=3)  # Failed health checks
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    plan = relationship("DisasterRecoveryPlan", back_populates="failover_procedures")
    failover_events = relationship("FailoverEvent", back_populates="procedure")
    
    __table_args__ = (
        UniqueConstraint('plan_id', 'service_name', name='uq_failover_procedure_service'),
        Index('idx_failover_procedures_plan_service', 'plan_id', 'service_name'),
    )


class FailoverEvent(Base):
    """Failover event record"""
    __tablename__ = "failover_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    procedure_id = Column(UUID(as_uuid=True), ForeignKey('failover_procedures.id'))
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    service_name = Column(String(100), nullable=False)
    disaster_type = Column(SQLEnum(DisasterType), nullable=False)
    failover_mode = Column(SQLEnum(FailoverMode), nullable=False)
    source_region = Column(String(50), nullable=False)
    target_region = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # in_progress, completed, failed, rolled_back
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    steps_completed = Column(JSON)  # List of completed steps
    validation_results = Column(JSON)
    error_message = Column(Text)
    metadata = Column(JSON)
    
    # Relationships
    procedure = relationship("FailoverProcedure", back_populates="failover_events")
    
    __table_args__ = (
        Index('idx_failover_events_status', 'status'),
        Index('idx_failover_events_service_time', 'service_name', 'start_time'),
    )


class RecoveryTest(Base):
    """Disaster recovery test/drill record"""
    __tablename__ = "recovery_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    test_type = Column(String(50), nullable=False)  # tabletop, backup_restore, failover, full_simulation
    services_tested = Column(JSON, nullable=False)  # List of services tested
    scenario = Column(JSON, nullable=False)  # Test scenario details
    status = Column(String(50), nullable=False)  # planned, in_progress, completed, cancelled
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    results = Column(JSON)  # Test results
    issues_found = Column(JSON)  # List of issues discovered
    recommendations = Column(JSON)  # List of recommendations
    success_rate = Column(Float)  # Percentage
    report_url = Column(String(500))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plan = relationship("DisasterRecoveryPlan", back_populates="recovery_tests")
    
    __table_args__ = (
        Index('idx_recovery_tests_plan_type', 'plan_id', 'test_type'),
        Index('idx_recovery_tests_status', 'status'),
    )


class RecoveryMetrics(Base):
    """Recovery metrics and objectives"""
    __tablename__ = "recovery_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    service_name = Column(String(100), nullable=False)
    recovery_tier = Column(SQLEnum(RecoveryTier), nullable=False)
    rto_target_minutes = Column(Integer, nullable=False)  # Recovery Time Objective
    rpo_target_minutes = Column(Integer, nullable=False)  # Recovery Point Objective
    actual_rto_minutes = Column(Integer)  # Last measured RTO
    actual_rpo_minutes = Column(Integer)  # Last measured RPO
    last_backup_time = Column(DateTime)
    last_test_time = Column(DateTime)
    last_failover_time = Column(DateTime)
    backup_success_rate = Column(Float)  # Percentage
    test_success_rate = Column(Float)  # Percentage
    compliance_status = Column(String(50))  # compliant, non_compliant, at_risk
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("DisasterRecoveryPlan", back_populates="recovery_metrics")
    
    __table_args__ = (
        UniqueConstraint('plan_id', 'service_name', name='uq_recovery_metrics_service'),
        Index('idx_recovery_metrics_compliance', 'compliance_status'),
    )


class DisasterEvent(Base):
    """Actual disaster event record"""
    __tablename__ = "disaster_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    disaster_type = Column(SQLEnum(DisasterType), nullable=False)
    severity = Column(String(50), nullable=False)  # low, medium, high, critical
    affected_services = Column(JSON, nullable=False)  # List of affected services
    impact_description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    detection_time = Column(DateTime, nullable=False)
    response_time = Column(DateTime)
    resolution_time = Column(DateTime)
    status = Column(String(50), nullable=False)  # detected, responding, resolved
    recovery_actions = Column(JSON)  # List of recovery actions taken
    lessons_learned = Column(Text)
    financial_impact = Column(Float)
    user_impact = Column(Integer)  # Number of affected users
    metadata = Column(JSON)
    
    # Relationships
    plan = relationship("DisasterRecoveryPlan", back_populates="disaster_events")
    recovery_operations = relationship("RecoveryOperation", back_populates="disaster_event")
    
    __table_args__ = (
        Index('idx_disaster_events_type_time', 'disaster_type', 'start_time'),
        Index('idx_disaster_events_status', 'status'),
    )


class RecoveryOperation(Base):
    """Individual recovery operation during a disaster event"""
    __tablename__ = "recovery_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disaster_event_id = Column(UUID(as_uuid=True), ForeignKey('disaster_events.id'), nullable=False)
    operation_type = Column(String(50), nullable=False)  # backup_restore, failover, data_sync, etc.
    service_name = Column(String(100), nullable=False)
    operator = Column(String(255))  # Person or system performing operation
    status = Column(String(50), nullable=False)  # pending, in_progress, completed, failed
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    recovery_data = Column(JSON)  # Operation-specific data
    error_message = Column(Text)
    metadata = Column(JSON)
    
    # Relationships
    disaster_event = relationship("DisasterEvent", back_populates="recovery_operations")
    
    __table_args__ = (
        Index('idx_recovery_operations_event_service', 'disaster_event_id', 'service_name'),
        Index('idx_recovery_operations_status', 'status'),
    )


class BusinessContinuityPlan(Base):
    """Business continuity plan model"""
    __tablename__ = "business_continuity_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dr_plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    critical_functions = Column(JSON, nullable=False)  # List of critical business functions
    communication_plan = Column(JSON, nullable=False)  # Communication procedures
    emergency_procedures = Column(JSON, nullable=False)  # Emergency response procedures
    resource_requirements = Column(JSON, nullable=False)  # Required resources
    activation_criteria = Column(JSON, nullable=False)  # When to activate BCP
    alternate_locations = Column(JSON)  # Alternative work locations
    vendor_contacts = Column(JSON)  # Critical vendor contact information
    training_schedule = Column(JSON)  # BCP training schedule
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_bcp_active', 'is_active'),
    )


class EmergencyContact(Base):
    """Emergency contact information"""
    __tablename__ = "emergency_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bcp_id = Column(UUID(as_uuid=True), ForeignKey('business_continuity_plans.id'))
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    phone_primary = Column(String(50), nullable=False)
    phone_secondary = Column(String(50))
    email = Column(String(255))
    notification_priority = Column(Integer, default=1)  # 1 = highest priority
    availability = Column(JSON)  # Availability schedule
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_emergency_contacts_priority', 'notification_priority'),
        Index('idx_emergency_contacts_active', 'is_active'),
    )


class RecoveryRunbook(Base):
    """Generated recovery runbooks"""
    __tablename__ = "recovery_runbooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('dr_plans.id'), nullable=False)
    disaster_type = Column(SQLEnum(DisasterType), nullable=False)
    affected_services = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)  # Ordered list of recovery steps
    estimated_recovery_time_hours = Column(Float)
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(255))
    printable_url = Column(String(500))
    metadata = Column(JSON)
    
    __table_args__ = (
        Index('idx_recovery_runbooks_type', 'disaster_type'),
        Index('idx_recovery_runbooks_generated', 'generated_at'),
    )