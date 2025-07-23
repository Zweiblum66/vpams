"""
Tests for tenant configuration management.

Tests configuration CRUD, templates, versioning, and validation.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from ..src.services.config_manager import ConfigurationManager, ConfigTemplate
from ..src.models.schemas import (
    TenantConfig, TenantConfigUpdate, BrandingConfig,
    FeatureFlags, SecurityConfig, IntegrationConfig
)
from ..src.core.exceptions import (
    ConfigurationError, ValidationError, ResourceNotFoundError
)


class TestConfigurationManager:
    """Test configuration management functionality."""
    
    @pytest.fixture
    async def config_manager(self):
        """Create configuration manager instance."""
        manager = ConfigurationManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_default_config(self, config_manager):
        """Test getting default configuration for new tenant."""
        tenant_id = "tenant001"
        
        # Get config for new tenant
        config = await config_manager.get_config(tenant_id)
        
        # Verify default values
        assert config.tenant_id == tenant_id
        assert config.version == 1
        assert config.branding.primary_color == "#1976d2"
        assert config.features.ai_enabled is True
        assert config.security.mfa_required is False
        assert config.integrations.api_rate_limit == 1000
    
    @pytest.mark.asyncio
    async def test_update_config(self, config_manager):
        """Test updating tenant configuration."""
        tenant_id = "tenant001"
        
        # Get initial config
        initial_config = await config_manager.get_config(tenant_id)
        initial_version = initial_config.version
        
        # Update branding
        update = TenantConfigUpdate(
            branding=BrandingConfig(
                primary_color="#ff0000",
                secondary_color="#00ff00",
                logo_url="/custom/logo.png"
            )
        )
        
        # Apply update
        updated_config = await config_manager.update_config(tenant_id, update)
        
        # Verify updates
        assert updated_config.version == initial_version + 1
        assert updated_config.branding.primary_color == "#ff0000"
        assert updated_config.branding.secondary_color == "#00ff00"
        assert updated_config.branding.logo_url == "/custom/logo.png"
        
        # Verify other settings unchanged
        assert updated_config.features.ai_enabled == initial_config.features.ai_enabled
    
    @pytest.mark.asyncio
    async def test_config_validation(self, config_manager):
        """Test configuration validation."""
        tenant_id = "tenant001"
        
        # Invalid color format
        with pytest.raises(ValidationError) as exc_info:
            update = TenantConfigUpdate(
                branding=BrandingConfig(
                    primary_color="invalid-color"
                )
            )
            await config_manager.update_config(tenant_id, update)
        
        assert "Invalid primary color format" in str(exc_info.value)
        
        # Invalid security settings
        with pytest.raises(ValidationError) as exc_info:
            update = TenantConfigUpdate(
                security=SecurityConfig(
                    session_timeout_minutes=3  # Too low
                )
            )
            await config_manager.update_config(tenant_id, update)
        
        assert "Session timeout must be at least 5 minutes" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_apply_template(self, config_manager):
        """Test applying configuration templates."""
        tenant_id = "tenant001"
        
        # Apply professional template
        config = await config_manager.apply_template(
            tenant_id,
            "professional",
            merge=True
        )
        
        # Verify template applied
        assert config.features.ai_enabled is True
        assert config.integrations.api_rate_limit == 5000
        assert config.integrations.slack_enabled is True
        assert config.security.mfa_required is True
    
    @pytest.mark.asyncio
    async def test_config_rollback(self, config_manager):
        """Test configuration rollback."""
        tenant_id = "tenant001"
        
        # Get initial config
        initial_config = await config_manager.get_config(tenant_id)
        
        # Make multiple updates
        update1 = TenantConfigUpdate(
            branding=BrandingConfig(primary_color="#ff0000")
        )
        config_v2 = await config_manager.update_config(tenant_id, update1)
        
        update2 = TenantConfigUpdate(
            branding=BrandingConfig(primary_color="#00ff00")
        )
        config_v3 = await config_manager.update_config(tenant_id, update2)
        
        # Rollback to previous version
        rolled_back = await config_manager.rollback_config(tenant_id)
        
        # Verify rollback
        assert rolled_back.version == config_v2.version
        assert rolled_back.branding.primary_color == "#ff0000"
        
        # Rollback to specific version
        rolled_back_v1 = await config_manager.rollback_config(
            tenant_id,
            version=initial_config.version
        )
        
        assert rolled_back_v1.version == initial_config.version
        assert rolled_back_v1.branding.primary_color == initial_config.branding.primary_color
    
    @pytest.mark.asyncio
    async def test_config_diff(self, config_manager):
        """Test configuration diff calculation."""
        tenant_id = "tenant001"
        
        # Get initial config
        initial_config = await config_manager.get_config(tenant_id)
        
        # Update config
        update = TenantConfigUpdate(
            branding=BrandingConfig(
                primary_color="#ff0000",
                logo_url="/new/logo.png"
            ),
            features=FeatureFlags(
                ai_enabled=False
            )
        )
        await config_manager.update_config(tenant_id, update)
        
        # Get diff
        diff = await config_manager.get_config_diff(
            tenant_id,
            version1=initial_config.version
        )
        
        # Verify diff contains changes
        assert diff is not None
        assert "values_changed" in diff or "type_changes" in diff
    
    @pytest.mark.asyncio
    async def test_feature_flags(self, config_manager):
        """Test feature flag management."""
        tenant_id = "tenant001"
        
        # Disable features
        update = TenantConfigUpdate(
            features=FeatureFlags(
                ai_enabled=False,
                workflow_automation=False,
                mobile_app=False
            )
        )
        
        config = await config_manager.update_config(tenant_id, update)
        
        # Verify features disabled
        assert config.features.ai_enabled is False
        assert config.features.workflow_automation is False
        assert config.features.mobile_app is False
        
        # Other features should remain enabled
        assert config.features.api_access is True
        assert config.features.advanced_search is True
    
    @pytest.mark.asyncio
    async def test_integration_config(self, config_manager):
        """Test integration configuration."""
        tenant_id = "tenant001"
        
        # Configure integrations
        update = TenantConfigUpdate(
            integrations=IntegrationConfig(
                slack_enabled=True,
                teams_enabled=True,
                ldap_enabled=True,
                api_rate_limit=5000,
                allowed_domains=["example.com", "test.com"]
            )
        )
        
        config = await config_manager.update_config(tenant_id, update)
        
        # Verify integrations
        assert config.integrations.slack_enabled is True
        assert config.integrations.teams_enabled is True
        assert config.integrations.ldap_enabled is True
        assert config.integrations.api_rate_limit == 5000
        assert "example.com" in config.integrations.allowed_domains
    
    @pytest.mark.asyncio
    async def test_security_config(self, config_manager):
        """Test security configuration."""
        tenant_id = "tenant001"
        
        # Configure security
        update = TenantConfigUpdate(
            security=SecurityConfig(
                password_policy={
                    "min_length": 12,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True,
                    "history_count": 5
                },
                session_timeout_minutes=60,
                mfa_required=True,
                ip_whitelist=["192.168.1.0", "10.0.0.0"],
                max_login_attempts=3
            )
        )
        
        config = await config_manager.update_config(tenant_id, update)
        
        # Verify security settings
        assert config.security.password_policy["min_length"] == 12
        assert config.security.password_policy["history_count"] == 5
        assert config.security.session_timeout_minutes == 60
        assert config.security.mfa_required is True
        assert len(config.security.ip_whitelist) == 2
    
    @pytest.mark.asyncio
    async def test_config_subscription(self, config_manager):
        """Test configuration change subscriptions."""
        tenant_id = "tenant001"
        changes_received = []
        
        # Subscribe to changes
        async def on_config_change(config):
            changes_received.append(config)
        
        await config_manager.subscribe_to_changes(tenant_id, on_config_change)
        
        # Make config change
        update = TenantConfigUpdate(
            branding=BrandingConfig(primary_color="#ff0000")
        )
        await config_manager.update_config(tenant_id, update)
        
        # Allow async notification
        await asyncio.sleep(0.1)
        
        # Verify notification received
        assert len(changes_received) == 1
        assert changes_received[0].branding.primary_color == "#ff0000"
        
        # Unsubscribe
        await config_manager.unsubscribe_from_changes(tenant_id, on_config_change)
        
        # Make another change
        await config_manager.update_config(tenant_id, update)
        await asyncio.sleep(0.1)
        
        # Should not receive notification
        assert len(changes_received) == 1
    
    @pytest.mark.asyncio
    async def test_export_import_config(self, config_manager):
        """Test configuration export and import."""
        tenant_id_source = "tenant001"
        tenant_id_target = "tenant002"
        
        # Configure source tenant
        update = TenantConfigUpdate(
            branding=BrandingConfig(
                primary_color="#123456",
                logo_url="/custom/logo.png"
            ),
            features=FeatureFlags(
                ai_enabled=False,
                mobile_app=True
            )
        )
        await config_manager.update_config(tenant_id_source, update)
        
        # Export configuration
        exported = await config_manager.export_config(tenant_id_source)
        
        # Remove tenant-specific data
        exported.pop("tenant_id", None)
        exported.pop("version", None)
        exported.pop("created_at", None)
        exported.pop("updated_at", None)
        
        # Import to target tenant
        imported_config = await config_manager.import_config(
            tenant_id_target,
            exported
        )
        
        # Verify imported config
        assert imported_config.branding.primary_color == "#123456"
        assert imported_config.branding.logo_url == "/custom/logo.png"
        assert imported_config.features.ai_enabled is False
        assert imported_config.features.mobile_app is True
    
    @pytest.mark.asyncio
    async def test_get_templates(self, config_manager):
        """Test retrieving configuration templates."""
        # Get all templates
        templates = await config_manager.get_templates()
        assert len(templates) > 0
        
        # Get plan templates
        plan_templates = await config_manager.get_templates(category="plan")
        assert all(t.category == "plan" for t in plan_templates)
        
        # Verify template content
        starter_template = next(
            (t for t in templates if t.name == "starter"),
            None
        )
        assert starter_template is not None
        assert starter_template.is_default is True
        assert starter_template.config["features"]["ai_enabled"] is False
    
    @pytest.mark.asyncio
    async def test_config_cache(self, config_manager):
        """Test configuration caching."""
        tenant_id = "tenant001"
        
        # Get config (should cache)
        config1 = await config_manager.get_config(tenant_id)
        
        # Get again (should use cache)
        config2 = await config_manager.get_config(tenant_id)
        
        # Should be same instance due to caching
        assert tenant_id in config_manager.compiled_configs
        
        # Update config (should invalidate cache)
        update = TenantConfigUpdate(
            branding=BrandingConfig(primary_color="#ff0000")
        )
        await config_manager.update_config(tenant_id, update)
        
        # Cache should be cleared
        assert tenant_id not in config_manager.compiled_configs


class TestConfigTemplates:
    """Test configuration templates."""
    
    @pytest.mark.asyncio
    async def test_starter_template(self, config_manager):
        """Test starter plan template."""
        tenant_id = "starter_tenant"
        
        # Apply starter template
        config = await config_manager.apply_template(
            tenant_id,
            "starter",
            merge=False
        )
        
        # Verify starter limitations
        assert config.features.ai_enabled is False
        assert config.features.workflow_automation is False
        assert config.features.advanced_search is False
        assert config.features.api_access is False
        assert config.features.mobile_app is False
        assert config.integrations.api_rate_limit == 100
        assert config.security.mfa_required is False
    
    @pytest.mark.asyncio
    async def test_enterprise_template(self, config_manager):
        """Test enterprise plan template."""
        tenant_id = "enterprise_tenant"
        
        # Apply enterprise template
        config = await config_manager.apply_template(
            tenant_id,
            "enterprise",
            merge=False
        )
        
        # Verify enterprise features
        assert all([
            config.features.ai_enabled,
            config.features.workflow_automation,
            config.features.advanced_search,
            config.features.custom_metadata,
            config.features.api_access,
            config.features.mobile_app,
            config.features.collaboration,
            config.features.version_control,
            config.features.audit_logging,
            config.features.custom_reports
        ])
        
        assert config.integrations.api_rate_limit == 50000
        assert all([
            config.integrations.slack_enabled,
            config.integrations.teams_enabled,
            config.integrations.ldap_enabled,
            config.integrations.sso_enabled,
            config.integrations.webhook_enabled
        ])
        
        assert config.security.mfa_required is True
        assert config.workflows.approval_required is True