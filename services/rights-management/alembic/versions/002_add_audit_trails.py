"""Add audit trails tables

Revision ID: 002
Revises: 001
Create Date: 2025-07-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit action enum
    op.execute("""
        CREATE TYPE auditaction AS ENUM (
            'party_created', 'party_updated', 'party_deleted', 'party_activated', 'party_deactivated',
            'license_created', 'license_updated', 'license_approved', 'license_rejected',
            'license_activated', 'license_suspended', 'license_terminated', 'license_expired',
            'license_renewed', 'license_downloaded', 'license_viewed',
            'usage_recorded', 'usage_updated', 'usage_deleted', 'usage_exported',
            'compliance_check_performed', 'compliance_alert_created', 'compliance_alert_resolved',
            'compliance_alert_acknowledged',
            'report_generated', 'report_exported', 'report_scheduled',
            'access_granted', 'access_revoked', 'permission_changed',
            'bulk_operation_performed', 'data_exported', 'data_imported', 'settings_changed'
        );
    """)
    
    # Create audit resource type enum
    op.execute("""
        CREATE TYPE auditresourcetype AS ENUM (
            'rights_party', 'license', 'usage_record', 'compliance_alert', 'report', 'system'
        );
    """)
    
    # Create audit_trails table
    op.create_table('audit_trails',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('action', sa.Enum('party_created', 'party_updated', 'party_deleted', 'party_activated', 'party_deactivated',
                                   'license_created', 'license_updated', 'license_approved', 'license_rejected',
                                   'license_activated', 'license_suspended', 'license_terminated', 'license_expired',
                                   'license_renewed', 'license_downloaded', 'license_viewed',
                                   'usage_recorded', 'usage_updated', 'usage_deleted', 'usage_exported',
                                   'compliance_check_performed', 'compliance_alert_created', 'compliance_alert_resolved',
                                   'compliance_alert_acknowledged', 'report_generated', 'report_exported', 'report_scheduled',
                                   'access_granted', 'access_revoked', 'permission_changed',
                                   'bulk_operation_performed', 'data_exported', 'data_imported', 'settings_changed',
                                   name='auditaction', native_enum=False), nullable=False),
        sa.Column('resource_type', sa.Enum('rights_party', 'license', 'usage_record', 'compliance_alert', 'report', 'system',
                                          name='auditresourcetype', native_enum=False), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('user_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('compliance_relevant', sa.Boolean(), nullable=False, default=False),
        sa.Column('security_relevant', sa.Boolean(), nullable=False, default=False),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit_trails
    op.create_index('idx_audit_trail_timestamp', 'audit_trails', ['timestamp'])
    op.create_index('idx_audit_trail_user_id', 'audit_trails', ['user_id'])
    op.create_index('idx_audit_trail_resource', 'audit_trails', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_trail_action', 'audit_trails', ['action'])
    op.create_index('idx_audit_trail_compliance', 'audit_trails', ['compliance_relevant'])
    op.create_index('idx_audit_trail_security', 'audit_trails', ['security_relevant'])
    op.create_index('idx_audit_trail_session', 'audit_trails', ['session_id'])
    op.create_index('idx_audit_trail_timestamp_user', 'audit_trails', ['timestamp', 'user_id'])
    op.create_index('idx_audit_trail_timestamp_resource', 'audit_trails', ['timestamp', 'resource_type', 'resource_id'])
    
    # Create audit_archives table
    op.create_table('audit_archives',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('action', sa.Enum('party_created', 'party_updated', 'party_deleted', 'party_activated', 'party_deactivated',
                                   'license_created', 'license_updated', 'license_approved', 'license_rejected',
                                   'license_activated', 'license_suspended', 'license_terminated', 'license_expired',
                                   'license_renewed', 'license_downloaded', 'license_viewed',
                                   'usage_recorded', 'usage_updated', 'usage_deleted', 'usage_exported',
                                   'compliance_check_performed', 'compliance_alert_created', 'compliance_alert_resolved',
                                   'compliance_alert_acknowledged', 'report_generated', 'report_exported', 'report_scheduled',
                                   'access_granted', 'access_revoked', 'permission_changed',
                                   'bulk_operation_performed', 'data_exported', 'data_imported', 'settings_changed',
                                   name='auditaction', native_enum=False), nullable=False),
        sa.Column('resource_type', sa.Enum('rights_party', 'license', 'usage_record', 'compliance_alert', 'report', 'system',
                                          name='auditresourcetype', native_enum=False), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('user_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('compliance_relevant', sa.Boolean(), nullable=False, default=False),
        sa.Column('security_relevant', sa.Boolean(), nullable=False, default=False),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('archive_batch_id', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit_archives
    op.create_index('idx_archive_timestamp', 'audit_archives', ['timestamp'])
    op.create_index('idx_archive_archived_at', 'audit_archives', ['archived_at'])
    op.create_index('idx_archive_user_id', 'audit_archives', ['user_id'])
    op.create_index('idx_archive_resource', 'audit_archives', ['resource_type', 'resource_id'])


def downgrade():
    # Drop tables
    op.drop_table('audit_archives')
    op.drop_table('audit_trails')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS auditaction')
    op.execute('DROP TYPE IF EXISTS auditresourcetype')