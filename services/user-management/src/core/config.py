"""
Configuration management for User Management Service

This module provides centralized configuration management using Pydantic settings.
Environment variables override defaults for production deployment.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """User Management Service settings"""
    
    # Application settings
    app_name: str = "MAMS User Management Service"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    
    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://mams_app:mams_dev_password@localhost:5432/mams_users",
        env="DATABASE_URL"
    )
    
    # Redis settings (for caching and sessions)
    redis_url: str = Field(default="redis://localhost:6379/1", env="REDIS_URL")
    redis_pool_size: int = Field(default=20, env="REDIS_POOL_SIZE")
    
    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    refresh_token_expiration_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRATION_DAYS")
    
    # Password policy
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(default=True, env="PASSWORD_REQUIRE_LOWERCASE")
    password_require_numbers: bool = Field(default=True, env="PASSWORD_REQUIRE_NUMBERS")
    password_require_symbols: bool = Field(default=True, env="PASSWORD_REQUIRE_SYMBOLS")
    password_history_count: int = Field(default=5, env="PASSWORD_HISTORY_COUNT")
    
    # Account lockout settings
    max_failed_login_attempts: int = Field(default=5, env="MAX_FAILED_LOGIN_ATTEMPTS")
    account_lockout_duration_minutes: int = Field(default=30, env="ACCOUNT_LOCKOUT_DURATION_MINUTES")
    
    # Email settings
    email_verification_required: bool = Field(default=True, env="EMAIL_VERIFICATION_REQUIRED")
    email_verification_expires_hours: int = Field(default=24, env="EMAIL_VERIFICATION_EXPIRES_HOURS")
    password_reset_expires_hours: int = Field(default=1, env="PASSWORD_RESET_EXPIRES_HOURS")
    
    # Email service configuration
    smtp_server: str = Field(default="localhost", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    email_from: str = Field(default="noreply@mams.example.com", env="EMAIL_FROM")
    
    # MFA settings
    mfa_issuer: str = Field(default="MAMS", env="MFA_ISSUER")
    mfa_backup_codes_count: int = Field(default=10, env="MFA_BACKUP_CODES_COUNT")
    
    # Session settings
    session_expiration_minutes: int = Field(default=480, env="SESSION_EXPIRATION_MINUTES")  # 8 hours
    max_concurrent_sessions: int = Field(default=5, env="MAX_CONCURRENT_SESSIONS")
    
    # External authentication providers
    enable_ldap: bool = Field(default=False, env="ENABLE_LDAP")
    ldap_server: str = Field(default="", env="LDAP_SERVER")
    ldap_port: int = Field(default=389, env="LDAP_PORT")
    ldap_use_ssl: bool = Field(default=False, env="LDAP_USE_SSL")
    ldap_use_tls: bool = Field(default=False, env="LDAP_USE_TLS")
    ldap_base_dn: str = Field(default="", env="LDAP_BASE_DN")
    ldap_bind_dn: str = Field(default="", env="LDAP_BIND_DN")
    ldap_bind_password: str = Field(default="", env="LDAP_BIND_PASSWORD")
    ldap_user_search_base: str = Field(default="", env="LDAP_USER_SEARCH_BASE")
    ldap_user_search_filter: str = Field(default="(uid={username})", env="LDAP_USER_SEARCH_FILTER")
    ldap_user_object_class: str = Field(default="inetOrgPerson", env="LDAP_USER_OBJECT_CLASS")
    ldap_username_attr: str = Field(default="uid", env="LDAP_USERNAME_ATTR")
    ldap_email_attr: str = Field(default="mail", env="LDAP_EMAIL_ATTR")
    ldap_first_name_attr: str = Field(default="givenName", env="LDAP_FIRST_NAME_ATTR")
    ldap_last_name_attr: str = Field(default="sn", env="LDAP_LAST_NAME_ATTR")
    ldap_display_name_attr: str = Field(default="displayName", env="LDAP_DISPLAY_NAME_ATTR")
    ldap_phone_attr: str = Field(default="telephoneNumber", env="LDAP_PHONE_ATTR")
    ldap_department_attr: str = Field(default="department", env="LDAP_DEPARTMENT_ATTR")
    ldap_organization_attr: str = Field(default="organization", env="LDAP_ORGANIZATION_ATTR")
    ldap_groups_attr: str = Field(default="memberOf", env="LDAP_GROUPS_ATTR")
    ldap_auto_create_user: bool = Field(default=True, env="LDAP_AUTO_CREATE_USER")
    ldap_auto_update_user: bool = Field(default=True, env="LDAP_AUTO_UPDATE_USER")
    ldap_connection_timeout: int = Field(default=30, env="LDAP_CONNECTION_TIMEOUT")
    ldap_search_timeout: int = Field(default=30, env="LDAP_SEARCH_TIMEOUT")
    ldap_pool_size: int = Field(default=5, env="LDAP_POOL_SIZE")
    ldap_group_search_base: str = Field(default="", env="LDAP_GROUP_SEARCH_BASE")
    ldap_group_search_filter: str = Field(default="(cn={groupname})", env="LDAP_GROUP_SEARCH_FILTER")
    ldap_group_object_class: str = Field(default="groupOfNames", env="LDAP_GROUP_OBJECT_CLASS")
    ldap_group_name_attr: str = Field(default="cn", env="LDAP_GROUP_NAME_ATTR")
    ldap_group_member_attr: str = Field(default="member", env="LDAP_GROUP_MEMBER_ATTR")
    ldap_default_role: str = Field(default="user", env="LDAP_DEFAULT_ROLE")
    ldap_admin_groups: List[str] = Field(default_factory=list, env="LDAP_ADMIN_GROUPS")
    ldap_editor_groups: List[str] = Field(default_factory=list, env="LDAP_EDITOR_GROUPS")
    ldap_viewer_groups: List[str] = Field(default_factory=list, env="LDAP_VIEWER_GROUPS")
    
    # OAuth2 settings
    enable_oauth2: bool = Field(default=False, env="ENABLE_OAUTH2")
    oauth2_providers: Dict[str, Any] = Field(default_factory=dict, env="OAUTH2_PROVIDERS")
    
    # Google OAuth2
    google_oauth2_enabled: bool = Field(default=False, env="GOOGLE_OAUTH2_ENABLED")
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="", env="GOOGLE_REDIRECT_URI")
    google_scopes: List[str] = Field(default_factory=lambda: ["openid", "email", "profile"], env="GOOGLE_SCOPES")
    
    # Microsoft OAuth2
    microsoft_oauth2_enabled: bool = Field(default=False, env="MICROSOFT_OAUTH2_ENABLED")
    microsoft_client_id: str = Field(default="", env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str = Field(default="", env="MICROSOFT_CLIENT_SECRET")
    microsoft_redirect_uri: str = Field(default="", env="MICROSOFT_REDIRECT_URI")
    microsoft_tenant_id: str = Field(default="common", env="MICROSOFT_TENANT_ID")
    microsoft_scopes: List[str] = Field(default_factory=lambda: ["openid", "email", "profile"], env="MICROSOFT_SCOPES")
    
    # OAuth2 behavior settings
    oauth2_auto_create_user: bool = Field(default=True, env="OAUTH2_AUTO_CREATE_USER")
    oauth2_auto_update_user: bool = Field(default=True, env="OAUTH2_AUTO_UPDATE_USER")
    oauth2_default_role: str = Field(default="user", env="OAUTH2_DEFAULT_ROLE")
    oauth2_session_timeout: int = Field(default=3600, env="OAUTH2_SESSION_TIMEOUT")  # 1 hour
    
    # SAML settings
    enable_saml: bool = Field(default=False, env="ENABLE_SAML")
    saml_settings: Dict[str, Any] = Field(default_factory=dict, env="SAML_SETTINGS")
    
    # SAML Service Provider (SP) settings
    saml_sp_entity_id: str = Field(default="", env="SAML_SP_ENTITY_ID")
    saml_sp_acs_url: str = Field(default="", env="SAML_SP_ACS_URL")
    saml_sp_sls_url: str = Field(default="", env="SAML_SP_SLS_URL")
    saml_sp_x509_cert: str = Field(default="", env="SAML_SP_X509_CERT")
    saml_sp_private_key: str = Field(default="", env="SAML_SP_PRIVATE_KEY")
    
    # SAML Identity Provider (IdP) settings
    saml_idp_entity_id: str = Field(default="", env="SAML_IDP_ENTITY_ID")
    saml_idp_sso_url: str = Field(default="", env="SAML_IDP_SSO_URL")
    saml_idp_sls_url: str = Field(default="", env="SAML_IDP_SLS_URL")
    saml_idp_x509_cert: str = Field(default="", env="SAML_IDP_X509_CERT")
    
    # SAML behavior settings
    saml_auto_create_user: bool = Field(default=True, env="SAML_AUTO_CREATE_USER")
    saml_auto_update_user: bool = Field(default=True, env="SAML_AUTO_UPDATE_USER")
    saml_default_role: str = Field(default="user", env="SAML_DEFAULT_ROLE")
    saml_attribute_mapping: Dict[str, str] = Field(default_factory=dict, env="SAML_ATTRIBUTE_MAPPING")
    saml_signature_algorithm: str = Field(default="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256", env="SAML_SIGNATURE_ALGORITHM")
    saml_digest_algorithm: str = Field(default="http://www.w3.org/2001/04/xmlenc#sha256", env="SAML_DIGEST_ALGORITHM")
    saml_name_id_format: str = Field(default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", env="SAML_NAME_ID_FORMAT")
    saml_authn_requests_signed: bool = Field(default=True, env="SAML_AUTHN_REQUESTS_SIGNED")
    saml_logout_requests_signed: bool = Field(default=True, env="SAML_LOGOUT_REQUESTS_SIGNED")
    saml_want_assertions_signed: bool = Field(default=True, env="SAML_WANT_ASSERTIONS_SIGNED")
    saml_want_assertions_encrypted: bool = Field(default=False, env="SAML_WANT_ASSERTIONS_ENCRYPTED")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring and observability
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9091, env="METRICS_PORT")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    
    # API Gateway settings
    api_gateway_url: str = Field(default="http://localhost:8000", env="API_GATEWAY_URL")
    
    # Service discovery
    service_discovery_url: str = Field(
        default="http://localhost:8500", 
        env="SERVICE_DISCOVERY_URL"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Default roles and permissions
    default_user_role: str = Field(default="user", env="DEFAULT_USER_ROLE")
    admin_role: str = Field(default="admin", env="ADMIN_ROLE")
    
    # Audit settings
    enable_audit_log: bool = Field(default=True, env="ENABLE_AUDIT_LOG")
    audit_log_retention_days: int = Field(default=90, env="AUDIT_LOG_RETENTION_DAYS")
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Validate secret key is not empty"""
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    @validator("oauth2_providers", pre=True)
    def parse_oauth2_providers(cls, v):
        """Parse OAuth2 providers from JSON string or dict"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for OAuth2 providers config, using defaults")
                return {}
        return v
    
    @validator("saml_settings", pre=True)
    def parse_saml_settings(cls, v):
        """Parse SAML settings from JSON string or dict"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for SAML settings config, using defaults")
                return {}
        return v
    
    @validator("ldap_admin_groups", "ldap_editor_groups", "ldap_viewer_groups", pre=True)
    def parse_ldap_groups(cls, v):
        """Parse LDAP groups from comma-separated string or list"""
        if isinstance(v, str):
            if v.strip():
                return [group.strip() for group in v.split(",")]
            else:
                return []
        elif isinstance(v, list):
            return [str(group).strip() for group in v]
        return v or []
    
    @validator("ldap_port")
    def validate_ldap_port(cls, v):
        """Validate LDAP port is in valid range"""
        if v < 1 or v > 65535:
            raise ValueError("LDAP port must be between 1 and 65535")
        return v
    
    @validator("ldap_server")
    def validate_ldap_server(cls, v, values):
        """Validate LDAP server configuration"""
        if values.get("enable_ldap") and not v:
            raise ValueError("LDAP server is required when LDAP is enabled")
        return v
    
    @validator("ldap_base_dn")
    def validate_ldap_base_dn(cls, v, values):
        """Validate LDAP base DN configuration"""
        if values.get("enable_ldap") and not v:
            raise ValueError("LDAP base DN is required when LDAP is enabled")
        return v
    
    @validator("google_scopes", "microsoft_scopes", pre=True)
    def parse_oauth2_scopes(cls, v):
        """Parse OAuth2 scopes from comma-separated string or list"""
        if isinstance(v, str):
            if v.strip():
                return [scope.strip() for scope in v.split(",")]
            else:
                return ["openid", "email", "profile"]
        elif isinstance(v, list):
            return [str(scope).strip() for scope in v]
        return v or ["openid", "email", "profile"]
    
    @validator("google_client_id")
    def validate_google_client_id(cls, v, values):
        """Validate Google OAuth2 client ID when enabled"""
        if values.get("google_oauth2_enabled") and not v:
            raise ValueError("Google client ID is required when Google OAuth2 is enabled")
        return v
    
    @validator("google_client_secret")
    def validate_google_client_secret(cls, v, values):
        """Validate Google OAuth2 client secret when enabled"""
        if values.get("google_oauth2_enabled") and not v:
            raise ValueError("Google client secret is required when Google OAuth2 is enabled")
        return v
    
    @validator("microsoft_client_id")
    def validate_microsoft_client_id(cls, v, values):
        """Validate Microsoft OAuth2 client ID when enabled"""
        if values.get("microsoft_oauth2_enabled") and not v:
            raise ValueError("Microsoft client ID is required when Microsoft OAuth2 is enabled")
        return v
    
    @validator("microsoft_client_secret")
    def validate_microsoft_client_secret(cls, v, values):
        """Validate Microsoft OAuth2 client secret when enabled"""
        if values.get("microsoft_oauth2_enabled") and not v:
            raise ValueError("Microsoft client secret is required when Microsoft OAuth2 is enabled")
        return v
    
    @validator("saml_attribute_mapping", pre=True)
    def parse_saml_attribute_mapping(cls, v):
        """Parse SAML attribute mapping from JSON string or dict"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for SAML attribute mapping, using defaults")
                return {
                    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                    "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                    "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                    "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
                }
        return v or {}
    
    @validator("saml_sp_entity_id")
    def validate_saml_sp_entity_id(cls, v, values):
        """Validate SAML SP entity ID when enabled"""
        if values.get("enable_saml") and not v:
            raise ValueError("SAML SP entity ID is required when SAML is enabled")
        return v
    
    @validator("saml_idp_entity_id")
    def validate_saml_idp_entity_id(cls, v, values):
        """Validate SAML IdP entity ID when enabled"""
        if values.get("enable_saml") and not v:
            raise ValueError("SAML IdP entity ID is required when SAML is enabled")
        return v
    
    @validator("saml_idp_sso_url")
    def validate_saml_idp_sso_url(cls, v, values):
        """Validate SAML IdP SSO URL when enabled"""
        if values.get("enable_saml") and not v:
            raise ValueError("SAML IdP SSO URL is required when SAML is enabled")
        return v
    
    @validator("saml_idp_x509_cert")
    def validate_saml_idp_cert(cls, v, values):
        """Validate SAML IdP certificate when enabled"""
        if values.get("enable_saml") and not v:
            raise ValueError("SAML IdP X.509 certificate is required when SAML is enabled")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


# Development settings
class DevelopmentSettings(Settings):
    """Development environment settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    email_verification_required: bool = False
    
    class Config:
        env_prefix = "DEV_"


# Staging settings
class StagingSettings(Settings):
    """Staging environment settings"""
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "STAGING_"


# Production settings
class ProductionSettings(Settings):
    """Production environment settings"""
    debug: bool = False
    log_level: str = "WARNING"
    
    class Config:
        env_prefix = "PROD_"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "development":
        return DevelopmentSettings()
    elif environment == "staging":
        return StagingSettings()
    elif environment == "production":
        return ProductionSettings()
    else:
        return Settings()


# Export commonly used settings
settings = get_settings()