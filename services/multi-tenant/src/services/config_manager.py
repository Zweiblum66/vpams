"""
Configuration Manager - Service for managing tenant-specific configurations.

Handles:
- Branding and theming
- Feature flags
- Integration settings
- Security policies
- Workflow configurations
- Notification preferences
"""

import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog
from deepdiff import DeepDiff
import asyncio

from ..core.config import get_settings
from ..core.exceptions import (
    ConfigurationError, ValidationError, ResourceNotFoundError
)
from ..models.schemas import (
    TenantConfig, TenantConfigUpdate, BrandingConfig,
    FeatureFlags, IntegrationConfig, SecurityConfig,
    NotificationConfig, WorkflowConfig
)


logger = structlog.get_logger()


@dataclass
class ConfigTemplate:
    """Configuration template for easy tenant setup."""
    name: str
    description: str
    config: Dict[str, Any]
    category: str
    is_default: bool = False
    tags: List[str] = field(default_factory=list)


class ConfigurationManager:
    """
    Manages tenant-specific configurations with versioning and inheritance.
    
    Features:
    - Hierarchical configuration with defaults and overrides
    - Configuration versioning and rollback
    - Template-based configuration
    - Real-time configuration updates
    - Configuration validation
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Configuration storage (in production, would be database)
        self.tenant_configs: Dict[str, TenantConfig] = {}
        self.config_history: Dict[str, List[TenantConfig]] = {}
        
        # Configuration templates
        self.templates: Dict[str, ConfigTemplate] = {}
        
        # Real-time update subscribers
        self.config_subscribers: Dict[str, Set[callable]] = {}
        
        # Cache for compiled configurations
        self.compiled_configs: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Default configuration
        self.default_config = self._create_default_config()
        
        # Configuration validators
        self.validators: Dict[str, callable] = {
            "branding": self._validate_branding,
            "features": self._validate_features,
            "integrations": self._validate_integrations,
            "security": self._validate_security,
            "notifications": self._validate_notifications,
            "workflows": self._validate_workflows
        }
        
        # Statistics
        self.stats = {
            "configs_created": 0,
            "configs_updated": 0,
            "rollbacks_performed": 0,
            "templates_applied": 0,
            "validation_errors": 0
        }
    
    async def initialize(self) -> None:
        """Initialize configuration manager."""
        try:
            logger.info("Initializing configuration manager")
            
            # Load default templates
            await self._load_default_templates()
            
            # Load existing configurations
            await self._load_configurations()
            
            logger.info(
                "Configuration manager initialized",
                templates_loaded=len(self.templates),
                configs_loaded=len(self.tenant_configs)
            )
            
        except Exception as e:
            logger.error("Failed to initialize configuration manager", error=str(e))
            raise ConfigurationError(f"Configuration manager initialization failed: {str(e)}")
    
    async def get_config(self, tenant_id: str) -> TenantConfig:
        """
        Get tenant configuration.
        
        Returns compiled configuration with defaults and overrides applied.
        """
        # Check if tenant has custom config
        if tenant_id not in self.tenant_configs:
            # Return default config for new tenants
            config = self._create_tenant_default_config(tenant_id)
            self.tenant_configs[tenant_id] = config
            self.stats["configs_created"] += 1
        
        # Get compiled configuration
        compiled = await self._compile_config(tenant_id)
        
        return self.tenant_configs[tenant_id]
    
    async def update_config(
        self,
        tenant_id: str,
        update: TenantConfigUpdate
    ) -> TenantConfig:
        """
        Update tenant configuration.
        
        Creates a new version and maintains history.
        """
        try:
            # Get current config
            current_config = await self.get_config(tenant_id)
            
            # Create config copy for history
            if tenant_id not in self.config_history:
                self.config_history[tenant_id] = []
            self.config_history[tenant_id].append(current_config.copy(deep=True))
            
            # Apply updates
            updated_config = await self._apply_updates(current_config, update)
            
            # Validate updated configuration
            await self._validate_config(updated_config)
            
            # Increment version
            updated_config.version += 1
            updated_config.updated_at = datetime.utcnow()
            
            # Store updated config
            self.tenant_configs[tenant_id] = updated_config
            
            # Invalidate cache
            if tenant_id in self.compiled_configs:
                del self.compiled_configs[tenant_id]
            
            # Notify subscribers
            await self._notify_config_change(tenant_id, updated_config)
            
            self.stats["configs_updated"] += 1
            
            logger.info(
                "Configuration updated",
                tenant_id=tenant_id,
                version=updated_config.version
            )
            
            return updated_config
            
        except Exception as e:
            logger.error("Failed to update configuration", 
                       tenant_id=tenant_id, 
                       error=str(e))
            raise
    
    async def apply_template(
        self,
        tenant_id: str,
        template_name: str,
        merge: bool = True
    ) -> TenantConfig:
        """
        Apply configuration template to tenant.
        
        Args:
            tenant_id: Tenant identifier
            template_name: Template to apply
            merge: If True, merge with existing config. If False, replace.
        """
        if template_name not in self.templates:
            raise ResourceNotFoundError("template", template_name)
        
        template = self.templates[template_name]
        
        if merge:
            # Get current config
            current_config = await self.get_config(tenant_id)
            
            # Merge template with current config
            update = TenantConfigUpdate(**template.config)
            updated_config = await self.update_config(tenant_id, update)
        else:
            # Replace with template config
            new_config = self._create_tenant_default_config(tenant_id)
            
            # Apply template values
            for key, value in template.config.items():
                setattr(new_config, key, value)
            
            # Store new config
            self.tenant_configs[tenant_id] = new_config
            updated_config = new_config
        
        self.stats["templates_applied"] += 1
        
        logger.info(
            "Template applied",
            tenant_id=tenant_id,
            template=template_name,
            merge=merge
        )
        
        return updated_config
    
    async def rollback_config(
        self,
        tenant_id: str,
        version: Optional[int] = None
    ) -> TenantConfig:
        """
        Rollback configuration to previous version.
        
        Args:
            tenant_id: Tenant identifier
            version: Specific version to rollback to. If None, rollback to previous.
        """
        if tenant_id not in self.config_history or not self.config_history[tenant_id]:
            raise ValidationError("No configuration history available for rollback")
        
        history = self.config_history[tenant_id]
        
        if version is None:
            # Rollback to previous version
            previous_config = history.pop()
        else:
            # Find specific version
            previous_config = None
            for i, config in enumerate(history):
                if config.version == version:
                    previous_config = history.pop(i)
                    break
            
            if previous_config is None:
                raise ResourceNotFoundError("configuration version", str(version))
        
        # Store current as history
        current = self.tenant_configs[tenant_id]
        history.append(current)
        
        # Restore previous config
        self.tenant_configs[tenant_id] = previous_config
        
        # Invalidate cache
        if tenant_id in self.compiled_configs:
            del self.compiled_configs[tenant_id]
        
        # Notify subscribers
        await self._notify_config_change(tenant_id, previous_config)
        
        self.stats["rollbacks_performed"] += 1
        
        logger.info(
            "Configuration rolled back",
            tenant_id=tenant_id,
            from_version=current.version,
            to_version=previous_config.version
        )
        
        return previous_config
    
    async def get_config_diff(
        self,
        tenant_id: str,
        version1: Optional[int] = None,
        version2: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get differences between configuration versions."""
        configs = []
        
        # Get first config
        if version1 is None:
            configs.append(self.tenant_configs.get(tenant_id))
        else:
            for config in self.config_history.get(tenant_id, []):
                if config.version == version1:
                    configs.append(config)
                    break
        
        # Get second config
        if version2 is None:
            configs.append(self.default_config)
        else:
            for config in self.config_history.get(tenant_id, []):
                if config.version == version2:
                    configs.append(config)
                    break
        
        if len(configs) != 2 or None in configs:
            raise ValidationError("Could not find specified configuration versions")
        
        # Calculate diff
        diff = DeepDiff(
            configs[0].dict(),
            configs[1].dict(),
            ignore_order=True,
            verbose_level=2
        )
        
        return diff.to_dict()
    
    async def validate_config(
        self,
        tenant_id: str,
        config: Optional[TenantConfig] = None
    ) -> List[str]:
        """
        Validate tenant configuration.
        
        Returns list of validation errors, empty if valid.
        """
        if config is None:
            config = await self.get_config(tenant_id)
        
        errors = []
        
        try:
            await self._validate_config(config)
        except ValidationError as e:
            errors.append(str(e))
        
        return errors
    
    async def subscribe_to_changes(
        self,
        tenant_id: str,
        callback: callable
    ) -> None:
        """Subscribe to configuration changes for a tenant."""
        if tenant_id not in self.config_subscribers:
            self.config_subscribers[tenant_id] = set()
        
        self.config_subscribers[tenant_id].add(callback)
        
        logger.debug("Subscribed to config changes", tenant_id=tenant_id)
    
    async def unsubscribe_from_changes(
        self,
        tenant_id: str,
        callback: callable
    ) -> None:
        """Unsubscribe from configuration changes."""
        if tenant_id in self.config_subscribers:
            self.config_subscribers[tenant_id].discard(callback)
    
    def _create_default_config(self) -> TenantConfig:
        """Create system-wide default configuration."""
        return TenantConfig(
            tenant_id="default",
            branding=BrandingConfig(
                logo_url="/assets/logo.png",
                favicon_url="/assets/favicon.ico",
                primary_color="#1976d2",
                secondary_color="#dc004e",
                font_family="Roboto, sans-serif",
                custom_css=""
            ),
            features=FeatureFlags(
                ai_enabled=True,
                workflow_automation=True,
                advanced_search=True,
                custom_metadata=True,
                api_access=True,
                mobile_app=True,
                collaboration=True,
                version_control=True,
                audit_logging=True,
                custom_reports=True
            ),
            integrations=IntegrationConfig(
                slack_enabled=False,
                teams_enabled=False,
                ldap_enabled=False,
                sso_enabled=False,
                webhook_enabled=True,
                api_rate_limit=1000,
                allowed_domains=[]
            ),
            security=SecurityConfig(
                password_policy={
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True
                },
                session_timeout_minutes=30,
                mfa_required=False,
                ip_whitelist=[],
                allowed_countries=[],
                max_login_attempts=5
            ),
            notifications=NotificationConfig(
                email_enabled=True,
                slack_enabled=False,
                teams_enabled=False,
                webhook_enabled=False,
                notification_preferences={
                    "asset_uploaded": ["email"],
                    "workflow_completed": ["email"],
                    "approval_required": ["email"],
                    "system_alerts": ["email"]
                }
            ),
            workflows=WorkflowConfig(
                auto_tagging=True,
                auto_transcription=True,
                approval_required=False,
                default_workflow="standard",
                custom_workflows={}
            ),
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _create_tenant_default_config(self, tenant_id: str) -> TenantConfig:
        """Create default configuration for new tenant."""
        config = self._create_default_config()
        config.tenant_id = tenant_id
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        return config
    
    async def _compile_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Compile configuration with inheritance and overrides.
        
        Applies:
        1. System defaults
        2. Tenant plan defaults
        3. Tenant-specific overrides
        """
        # Check cache
        if tenant_id in self.compiled_configs:
            return self.compiled_configs[tenant_id]
        
        # Start with defaults
        compiled = self.default_config.dict()
        
        # Apply tenant config
        tenant_config = self.tenant_configs.get(tenant_id)
        if tenant_config:
            tenant_dict = tenant_config.dict()
            
            # Deep merge configurations
            compiled = self._deep_merge(compiled, tenant_dict)
        
        # Cache compiled config
        self.compiled_configs[tenant_id] = compiled
        
        # Schedule cache expiration
        asyncio.create_task(self._expire_cache(tenant_id))
        
        return compiled
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _apply_updates(
        self,
        config: TenantConfig,
        update: TenantConfigUpdate
    ) -> TenantConfig:
        """Apply configuration updates."""
        # Update each provided field
        update_dict = update.dict(exclude_unset=True)
        
        for key, value in update_dict.items():
            if value is not None:
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    async def _validate_config(self, config: TenantConfig) -> None:
        """Validate configuration values."""
        errors = []
        
        # Validate each section
        for section, validator in self.validators.items():
            section_value = getattr(config, section, None)
            if section_value:
                try:
                    validator(section_value)
                except ValidationError as e:
                    errors.append(f"{section}: {str(e)}")
        
        if errors:
            self.stats["validation_errors"] += 1
            raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def _validate_branding(self, branding: BrandingConfig) -> None:
        """Validate branding configuration."""
        # Validate color formats
        import re
        color_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        if not color_pattern.match(branding.primary_color):
            raise ValidationError("Invalid primary color format")
        
        if not color_pattern.match(branding.secondary_color):
            raise ValidationError("Invalid secondary color format")
        
        # Validate URLs
        if branding.logo_url and not branding.logo_url.startswith(('/', 'http://', 'https://')):
            raise ValidationError("Invalid logo URL")
    
    def _validate_features(self, features: FeatureFlags) -> None:
        """Validate feature flags."""
        # All feature flags are boolean, validation handled by Pydantic
        pass
    
    def _validate_integrations(self, integrations: IntegrationConfig) -> None:
        """Validate integration configuration."""
        # Validate rate limit
        if integrations.api_rate_limit < 0:
            raise ValidationError("API rate limit must be non-negative")
        
        # Validate domains
        for domain in integrations.allowed_domains:
            if not self._is_valid_domain(domain):
                raise ValidationError(f"Invalid domain: {domain}")
    
    def _validate_security(self, security: SecurityConfig) -> None:
        """Validate security configuration."""
        # Validate password policy
        policy = security.password_policy
        if policy.get("min_length", 0) < 6:
            raise ValidationError("Password minimum length must be at least 6")
        
        # Validate session timeout
        if security.session_timeout_minutes < 5:
            raise ValidationError("Session timeout must be at least 5 minutes")
        
        # Validate IP whitelist
        for ip in security.ip_whitelist:
            if not self._is_valid_ip(ip):
                raise ValidationError(f"Invalid IP address: {ip}")
    
    def _validate_notifications(self, notifications: NotificationConfig) -> None:
        """Validate notification configuration."""
        # Validate notification preferences
        valid_channels = ["email", "slack", "teams", "webhook"]
        
        for event, channels in notifications.notification_preferences.items():
            for channel in channels:
                if channel not in valid_channels:
                    raise ValidationError(f"Invalid notification channel: {channel}")
    
    def _validate_workflows(self, workflows: WorkflowConfig) -> None:
        """Validate workflow configuration."""
        # Validate default workflow exists
        if workflows.default_workflow not in ["standard", "minimal", "advanced", *workflows.custom_workflows.keys()]:
            raise ValidationError("Default workflow not found")
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if domain is valid."""
        import re
        pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
        return bool(re.match(pattern, domain.lower()))
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP address is valid."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    async def _notify_config_change(
        self,
        tenant_id: str,
        config: TenantConfig
    ) -> None:
        """Notify subscribers of configuration changes."""
        if tenant_id in self.config_subscribers:
            for callback in self.config_subscribers[tenant_id]:
                try:
                    await callback(config)
                except Exception as e:
                    logger.error(
                        "Error notifying config subscriber",
                        tenant_id=tenant_id,
                        error=str(e)
                    )
    
    async def _expire_cache(self, tenant_id: str) -> None:
        """Expire cached configuration after TTL."""
        await asyncio.sleep(self.cache_ttl)
        
        if tenant_id in self.compiled_configs:
            del self.compiled_configs[tenant_id]
    
    async def _load_default_templates(self) -> None:
        """Load default configuration templates."""
        # Starter template
        self.templates["starter"] = ConfigTemplate(
            name="starter",
            description="Basic configuration for small teams",
            category="plan",
            is_default=True,
            config={
                "features": {
                    "ai_enabled": False,
                    "workflow_automation": False,
                    "advanced_search": False,
                    "api_access": False,
                    "mobile_app": False
                },
                "integrations": {
                    "api_rate_limit": 100
                },
                "security": {
                    "mfa_required": False
                }
            }
        )
        
        # Professional template
        self.templates["professional"] = ConfigTemplate(
            name="professional",
            description="Full-featured configuration for professional teams",
            category="plan",
            config={
                "features": {
                    "ai_enabled": True,
                    "workflow_automation": True,
                    "advanced_search": True,
                    "api_access": True,
                    "mobile_app": True
                },
                "integrations": {
                    "api_rate_limit": 5000,
                    "slack_enabled": True,
                    "teams_enabled": True
                },
                "security": {
                    "mfa_required": True,
                    "session_timeout_minutes": 60
                }
            }
        )
        
        # Enterprise template
        self.templates["enterprise"] = ConfigTemplate(
            name="enterprise",
            description="Enterprise-grade configuration with all features",
            category="plan",
            config={
                "features": {
                    "ai_enabled": True,
                    "workflow_automation": True,
                    "advanced_search": True,
                    "custom_metadata": True,
                    "api_access": True,
                    "mobile_app": True,
                    "collaboration": True,
                    "version_control": True,
                    "audit_logging": True,
                    "custom_reports": True
                },
                "integrations": {
                    "api_rate_limit": 50000,
                    "slack_enabled": True,
                    "teams_enabled": True,
                    "ldap_enabled": True,
                    "sso_enabled": True,
                    "webhook_enabled": True
                },
                "security": {
                    "mfa_required": True,
                    "session_timeout_minutes": 120,
                    "max_login_attempts": 3
                },
                "workflows": {
                    "approval_required": True
                }
            }
        )
        
        # Media company template
        self.templates["media_company"] = ConfigTemplate(
            name="media_company",
            description="Optimized for media production companies",
            category="industry",
            tags=["media", "production", "broadcast"],
            config={
                "features": {
                    "ai_enabled": True,
                    "workflow_automation": True,
                    "advanced_search": True,
                    "version_control": True
                },
                "workflows": {
                    "auto_transcription": True,
                    "default_workflow": "media_production"
                }
            }
        )
        
        logger.info(f"Loaded {len(self.templates)} configuration templates")
    
    async def _load_configurations(self) -> None:
        """Load existing tenant configurations from storage."""
        # In production, this would load from database
        logger.info("Loading tenant configurations")
    
    async def get_templates(self, category: Optional[str] = None) -> List[ConfigTemplate]:
        """Get available configuration templates."""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        return templates
    
    async def export_config(self, tenant_id: str) -> Dict[str, Any]:
        """Export tenant configuration as JSON."""
        config = await self.get_config(tenant_id)
        return config.dict()
    
    async def import_config(
        self,
        tenant_id: str,
        config_data: Dict[str, Any]
    ) -> TenantConfig:
        """Import configuration from JSON."""
        try:
            # Create config update from data
            update = TenantConfigUpdate(**config_data)
            
            # Apply update
            return await self.update_config(tenant_id, update)
            
        except Exception as e:
            logger.error("Failed to import configuration", error=str(e))
            raise ValidationError(f"Invalid configuration data: {str(e)}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get configuration manager statistics."""
        return {
            **self.stats,
            "total_configs": len(self.tenant_configs),
            "total_templates": len(self.templates),
            "cached_configs": len(self.compiled_configs),
            "active_subscribers": sum(
                len(subs) for subs in self.config_subscribers.values()
            )
        }
    
    async def cleanup(self) -> None:
        """Cleanup configuration manager resources."""
        try:
            # Clear caches
            self.compiled_configs.clear()
            
            # Clear subscribers
            self.config_subscribers.clear()
            
            logger.info("Configuration manager cleanup completed")
            
        except Exception as e:
            logger.error("Error during configuration manager cleanup", error=str(e))