"""Configuration settings for Zero Trust Service."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = Field(default="zero-trust", env="SERVICE_NAME")
    service_port: int = Field(default=8025, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/7", env="REDIS_URL")
    
    # Zero Trust core settings
    zero_trust_enabled: bool = Field(default=True, env="ZERO_TRUST_ENABLED")
    trust_verification_interval: int = Field(default=300, env="TRUST_VERIFICATION_INTERVAL")  # seconds
    
    # Trust scoring
    min_trust_score: float = Field(default=0.7, env="MIN_TRUST_SCORE")
    max_trust_score: float = Field(default=1.0, env="MAX_TRUST_SCORE")
    trust_decay_rate: float = Field(default=0.1, env="TRUST_DECAY_RATE")  # per hour
    
    # Device authentication
    device_registration_required: bool = Field(default=True, env="DEVICE_REGISTRATION_REQUIRED")
    device_trust_duration: int = Field(default=7200, env="DEVICE_TRUST_DURATION")  # seconds
    unknown_device_action: str = Field(default="challenge", env="UNKNOWN_DEVICE_ACTION")  # allow, challenge, deny
    
    # Continuous authentication
    continuous_auth_enabled: bool = Field(default=True, env="CONTINUOUS_AUTH_ENABLED")
    session_verification_interval: int = Field(default=600, env="SESSION_VERIFICATION_INTERVAL")  # seconds
    behavioral_analysis_enabled: bool = Field(default=True, env="BEHAVIORAL_ANALYSIS_ENABLED")
    
    # Risk assessment
    risk_assessment_enabled: bool = Field(default=True, env="RISK_ASSESSMENT_ENABLED")
    high_risk_threshold: float = Field(default=0.8, env="HIGH_RISK_THRESHOLD")
    medium_risk_threshold: float = Field(default=0.5, env="MEDIUM_RISK_THRESHOLD")
    
    # Geographic restrictions
    geo_restrictions_enabled: bool = Field(default=True, env="GEO_RESTRICTIONS_ENABLED")
    allowed_countries: List[str] = Field(default=[], env="ALLOWED_COUNTRIES")
    blocked_countries: List[str] = Field(default=[], env="BLOCKED_COUNTRIES")
    geoip_database_path: str = Field(default="/app/data/GeoLite2-Country.mmdb", env="GEOIP_DATABASE_PATH")
    
    # Time-based access controls
    time_restrictions_enabled: bool = Field(default=False, env="TIME_RESTRICTIONS_ENABLED")
    allowed_hours_start: int = Field(default=8, env="ALLOWED_HOURS_START")  # 24-hour format
    allowed_hours_end: int = Field(default=18, env="ALLOWED_HOURS_END")
    
    # Network security
    network_verification_enabled: bool = Field(default=True, env="NETWORK_VERIFICATION_ENABLED")
    trusted_networks: List[str] = Field(
        default=["192.168.0.0/16", "10.0.0.0/8"],
        env="TRUSTED_NETWORKS"
    )
    untrusted_networks: List[str] = Field(
        default=["0.0.0.0/0"],
        env="UNTRUSTED_NETWORKS"
    )
    
    # Multi-factor authentication
    mfa_enforcement_enabled: bool = Field(default=True, env="MFA_ENFORCEMENT_ENABLED")
    mfa_grace_period: int = Field(default=3600, env="MFA_GRACE_PERIOD")  # seconds
    mfa_methods: List[str] = Field(
        default=["totp", "sms", "push", "hardware_key"],
        env="MFA_METHODS"
    )
    
    # Adaptive access controls
    adaptive_controls_enabled: bool = Field(default=True, env="ADAPTIVE_CONTROLS_ENABLED")
    access_patterns_learning: bool = Field(default=True, env="ACCESS_PATTERNS_LEARNING")
    anomaly_detection_sensitivity: float = Field(default=0.7, env="ANOMALY_DETECTION_SENSITIVITY")
    
    # Policy engine
    policy_engine_enabled: bool = Field(default=True, env="POLICY_ENGINE_ENABLED")
    policy_files: List[str] = Field(
        default=["/app/policies/default.yaml", "/app/policies/custom.yaml"],
        env="POLICY_FILES"
    )
    policy_evaluation_cache_ttl: int = Field(default=300, env="POLICY_EVALUATION_CACHE_TTL")
    
    # Device fingerprinting
    device_fingerprinting_enabled: bool = Field(default=True, env="DEVICE_FINGERPRINTING_ENABLED")
    fingerprint_factors: List[str] = Field(
        default=["user_agent", "screen_resolution", "timezone", "language", "plugins"],
        env="FINGERPRINT_FACTORS"
    )
    
    # Privileged access management
    pam_enabled: bool = Field(default=True, env="PAM_ENABLED")
    privileged_session_timeout: int = Field(default=1800, env="PRIVILEGED_SESSION_TIMEOUT")  # seconds
    privileged_actions_approval: bool = Field(default=True, env="PRIVILEGED_ACTIONS_APPROVAL")
    
    # Micro-segmentation
    microsegmentation_enabled: bool = Field(default=True, env="MICROSEGMENTATION_ENABLED")
    default_network_policy: str = Field(default="deny", env="DEFAULT_NETWORK_POLICY")  # allow, deny
    
    # Compliance and auditing
    audit_all_actions: bool = Field(default=True, env="AUDIT_ALL_ACTIONS")
    compliance_mode: Optional[str] = Field(default=None, env="COMPLIANCE_MODE")  # gdpr, hipaa, sox
    audit_retention_days: int = Field(default=2555, env="AUDIT_RETENTION_DAYS")  # 7 years
    
    # Threat intelligence integration
    threat_intel_enabled: bool = Field(default=True, env="THREAT_INTEL_ENABLED")
    threat_intel_sources: List[str] = Field(
        default=["internal", "commercial", "open_source"],
        env="THREAT_INTEL_SOURCES"
    )
    threat_intel_update_interval: int = Field(default=3600, env="THREAT_INTEL_UPDATE_INTERVAL")
    
    # Machine learning
    ml_models_enabled: bool = Field(default=True, env="ML_MODELS_ENABLED")
    model_training_interval: int = Field(default=86400, env="MODEL_TRAINING_INTERVAL")  # daily
    behavioral_baseline_days: int = Field(default=30, env="BEHAVIORAL_BASELINE_DAYS")
    
    # Alert configuration
    alert_enabled: bool = Field(default=True, env="ALERT_ENABLED")
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    alert_high_risk_threshold: float = Field(default=0.8, env="ALERT_HIGH_RISK_THRESHOLD")
    
    # Performance settings
    max_concurrent_evaluations: int = Field(default=100, env="MAX_CONCURRENT_EVALUATIONS")
    evaluation_timeout: int = Field(default=30, env="EVALUATION_TIMEOUT")  # seconds
    cache_size: int = Field(default=10000, env="CACHE_SIZE")
    
    # Integration settings
    user_service_url: str = Field(default="http://user-management:8000", env="USER_SERVICE_URL")
    asset_service_url: str = Field(default="http://asset-management:8000", env="ASSET_SERVICE_URL")
    waf_service_url: str = Field(default="http://waf-protection:8000", env="WAF_SERVICE_URL")
    ids_service_url: str = Field(default="http://intrusion-detection:8000", env="IDS_SERVICE_URL")
    
    # Security settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # JWT settings
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=15, env="JWT_EXPIRATION_MINUTES")
    
    # Encryption settings
    encryption_key: str = Field(env="ENCRYPTION_KEY")
    data_encryption_enabled: bool = Field(default=True, env="DATA_ENCRYPTION_ENABLED")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    requests_per_minute: int = Field(default=100, env="REQUESTS_PER_MINUTE")
    
    # Data retention
    trust_data_retention_days: int = Field(default=90, env="TRUST_DATA_RETENTION_DAYS")
    session_data_retention_days: int = Field(default=30, env="SESSION_DATA_RETENTION_DAYS")
    
    # Trust factors weights
    trust_factor_weights: Dict[str, float] = Field(
        default={
            "device_trust": 0.25,
            "location_trust": 0.20,
            "behavioral_trust": 0.25,
            "time_based_trust": 0.10,
            "network_trust": 0.20
        },
        env="TRUST_FACTOR_WEIGHTS"
    )
    
    # Risk scoring weights
    risk_factor_weights: Dict[str, float] = Field(
        default={
            "anomalous_behavior": 0.30,
            "suspicious_location": 0.25,
            "unknown_device": 0.20,
            "threat_intelligence": 0.15,
            "time_based_risk": 0.10
        },
        env="RISK_FACTOR_WEIGHTS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()