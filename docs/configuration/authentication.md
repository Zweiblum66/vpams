# Authentication Configuration Guide

## Overview

This guide covers configuring authentication for MAMS, including local authentication, Single Sign-On (SSO), Multi-Factor Authentication (MFA), and integration with external identity providers.

## Authentication Methods

MAMS supports multiple authentication methods:

1. **Local Authentication** - Username/password stored in MAMS
2. **LDAP/Active Directory** - Enterprise directory integration
3. **SAML 2.0** - Enterprise SSO
4. **OAuth2/OpenID Connect** - Modern SSO protocols
5. **API Keys** - For programmatic access

## Local Authentication

### Basic Configuration

```yaml
# config/authentication.yaml
authentication:
  local:
    enabled: true
    
    # Password requirements
    password_policy:
      min_length: 12
      max_length: 128
      require_uppercase: true
      require_lowercase: true
      require_numbers: true
      require_special: true
      special_characters: "!@#$%^&*()_+-=[]{}|;:,.<>?"
      
    # Password expiration
    password_expiration:
      enabled: true
      days: 90
      warning_days: 14
      
    # Password history
    password_history:
      enabled: true
      count: 5  # Remember last 5 passwords
      
    # Account lockout
    lockout_policy:
      enabled: true
      attempts: 5
      duration_minutes: 30
      reset_after_minutes: 60
```

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-very-long-random-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Session Configuration
SESSION_TIMEOUT_MINUTES=60
SESSION_EXTEND_ON_ACTIVITY=true
MAX_SESSIONS_PER_USER=5

# Security
BCRYPT_ROUNDS=12
SECURE_COOKIES=true
SAME_SITE_COOKIES=strict
```

## LDAP/Active Directory

### LDAP Configuration

```yaml
# config/ldap.yaml
ldap:
  enabled: true
  
  # Connection settings
  servers:
    - host: ldap.company.com
      port: 389
      use_ssl: false
      use_tls: true
      timeout: 30
      
  # Bind credentials
  bind_dn: "cn=service-account,ou=services,dc=company,dc=com"
  bind_password: "${LDAP_BIND_PASSWORD}"
  
  # User search
  user_search:
    base_dn: "ou=users,dc=company,dc=com"
    filter: "(&(objectClass=user)(sAMAccountName={username}))"
    attributes:
      - sAMAccountName
      - mail
      - displayName
      - department
      - title
      - memberOf
      
  # Group search
  group_search:
    base_dn: "ou=groups,dc=company,dc=com"
    filter: "(member={user_dn})"
    name_attribute: cn
    
  # Attribute mapping
  attribute_mapping:
    username: sAMAccountName
    email: mail
    full_name: displayName
    department: department
    title: title
    
  # Role mapping
  group_role_mapping:
    "CN=MAMS-Admins,OU=Groups,DC=company,DC=com": admin
    "CN=MAMS-Editors,OU=Groups,DC=company,DC=com": editor
    "CN=MAMS-Viewers,OU=Groups,DC=company,DC=com": viewer
```

### Active Directory Specific Settings

```yaml
active_directory:
  enabled: true
  domain: COMPANY.COM
  
  # Domain controllers
  controllers:
    - dc1.company.com
    - dc2.company.com
    
  # Nested group support
  nested_groups: true
  
  # User principal name
  use_upn_username: true
  
  # Additional settings
  page_size: 1000
  referrals: false
```

### LDAP SSL/TLS Configuration

```yaml
ldap_ssl:
  # Certificate validation
  verify_certificates: true
  ca_certificate_file: /etc/ssl/certs/company-ca.crt
  
  # Client certificates (optional)
  client_certificate_file: /etc/ssl/certs/mams-client.crt
  client_key_file: /etc/ssl/private/mams-client.key
  
  # TLS version
  tls_version: TLSv1.2
  
  # Cipher suites
  cipher_suites:
    - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
```

## SAML 2.0 Configuration

### Basic SAML Setup

```yaml
# config/saml.yaml
saml:
  enabled: true
  
  # Service Provider (SP) settings
  sp:
    entity_id: "https://mams.company.com"
    assertion_consumer_service:
      url: "https://mams.company.com/api/v1/auth/saml/acs"
      binding: "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      
    # SP certificate and key
    x509_cert: |
      -----BEGIN CERTIFICATE-----
      MIIDXTCCAkWgAwIBAgIJALmVVuDWu4NYMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
      ...
      -----END CERTIFICATE-----
    private_key: |
      -----BEGIN PRIVATE KEY-----
      MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC0Z2QX2b
      ...
      -----END PRIVATE KEY-----
      
  # Identity Provider (IdP) settings
  idp:
    entity_id: "https://idp.company.com"
    single_sign_on_service:
      url: "https://idp.company.com/sso"
      binding: "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    single_logout_service:
      url: "https://idp.company.com/slo"
      binding: "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
      
    # IdP certificate
    x509_cert: |
      -----BEGIN CERTIFICATE-----
      MIIDXTCCAkWgAwIBAgIJALmVVuDWu4NYMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
      ...
      -----END CERTIFICATE-----
      
  # Attribute mapping
  attribute_mapping:
    email: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    name: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    groups: "http://schemas.xmlsoap.org/claims/Group"
    
  # Security settings
  security:
    name_id_encrypted: false
    authn_requests_signed: true
    logout_requests_signed: true
    logout_responses_signed: true
    want_assertions_signed: true
    want_assertions_encrypted: false
    want_name_id: true
    want_name_id_encrypted: false
    want_attribute_statement: true
    signature_algorithm: "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    digest_algorithm: "http://www.w3.org/2001/04/xmlenc#sha256"
```

### Advanced SAML Settings

```yaml
saml_advanced:
  # Session settings
  session:
    not_on_or_after: 3600  # seconds
    
  # Relay state
  relay_state:
    enabled: true
    parameter_name: "RelayState"
    
  # Force authentication
  force_authn: false
  
  # Authentication context
  requested_authn_context:
    enabled: true
    comparison: "exact"
    authn_context_class_ref:
      - "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
      
  # Just-In-Time provisioning
  jit_provisioning:
    enabled: true
    update_attributes: true
    default_role: viewer
    default_groups:
      - mams-users
```

## OAuth2/OpenID Connect

### OAuth2 Provider Configuration

```yaml
# config/oauth2.yaml
oauth2:
  providers:
    # Google OAuth2
    google:
      enabled: true
      client_id: "${GOOGLE_CLIENT_ID}"
      client_secret: "${GOOGLE_CLIENT_SECRET}"
      authorize_url: "https://accounts.google.com/o/oauth2/v2/auth"
      token_url: "https://oauth2.googleapis.com/token"
      userinfo_url: "https://openidconnect.googleapis.com/v1/userinfo"
      scopes:
        - openid
        - email
        - profile
      attribute_mapping:
        email: email
        name: name
        picture: picture
        
    # Microsoft Azure AD
    azure:
      enabled: true
      tenant_id: "${AZURE_TENANT_ID}"
      client_id: "${AZURE_CLIENT_ID}"
      client_secret: "${AZURE_CLIENT_SECRET}"
      authorize_url: "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
      token_url: "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
      userinfo_url: "https://graph.microsoft.com/v1.0/me"
      scopes:
        - openid
        - email
        - profile
        - User.Read
      attribute_mapping:
        email: mail
        name: displayName
        department: department
        
    # Generic OIDC
    custom:
      enabled: false
      issuer: "https://identity.company.com"
      client_id: "${OIDC_CLIENT_ID}"
      client_secret: "${OIDC_CLIENT_SECRET}"
      discovery_url: "https://identity.company.com/.well-known/openid-configuration"
      scopes:
        - openid
        - email
        - profile
        - groups
```

### OAuth2 Security Settings

```yaml
oauth2_security:
  # State parameter
  use_state: true
  state_timeout: 600  # seconds
  
  # PKCE (Proof Key for Code Exchange)
  use_pkce: true
  
  # Token validation
  validate_issuer: true
  validate_audience: true
  clock_skew_seconds: 30
  
  # Token storage
  store_tokens: true
  encrypt_tokens: true
```

## Multi-Factor Authentication (MFA)

### MFA Configuration

```yaml
# config/mfa.yaml
mfa:
  enabled: true
  
  # MFA methods
  methods:
    # Time-based One-Time Password (TOTP)
    totp:
      enabled: true
      issuer: "MAMS Platform"
      digits: 6
      period: 30
      algorithm: SHA1
      qr_code:
        size: 200
        error_correction: "M"
        
    # SMS-based OTP
    sms:
      enabled: true
      provider: twilio
      template: "Your MAMS verification code is: {code}"
      code_length: 6
      validity_minutes: 5
      
    # Email-based OTP
    email:
      enabled: true
      template: "mfa_code"
      subject: "MAMS Security Code"
      code_length: 6
      validity_minutes: 10
      
    # Backup codes
    backup_codes:
      enabled: true
      count: 10
      length: 8
      
  # MFA policies
  policies:
    # Enforce MFA for roles
    enforce_for_roles:
      - admin
      - manager
      
    # Enforce MFA for operations
    enforce_for_operations:
      - delete_assets
      - modify_permissions
      - export_data
      
    # Remember device
    remember_device:
      enabled: true
      duration_days: 30
      
    # Grace period for new users
    grace_period:
      enabled: true
      days: 7
```

### MFA Implementation

```python
# Example MFA verification
class MFAService:
    async def verify_totp(self, user_id: str, code: str) -> bool:
        user = await self.get_user(user_id)
        if not user.mfa_secret:
            return False
            
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(code, valid_window=1)
        
    async def send_sms_code(self, user_id: str) -> str:
        user = await self.get_user(user_id)
        code = self.generate_code()
        
        await self.sms_provider.send(
            to=user.phone_number,
            body=f"Your MAMS code is: {code}"
        )
        
        await self.cache.set(
            f"mfa:sms:{user_id}",
            code,
            expire=300  # 5 minutes
        )
        
        return code
```

## API Key Authentication

### API Key Configuration

```yaml
# config/api_keys.yaml
api_keys:
  enabled: true
  
  # Key generation
  generation:
    prefix: "mams_"
    length: 32
    algorithm: "secrets.token_urlsafe"
    
  # Key policies
  policies:
    max_keys_per_user: 5
    
    # Expiration
    expiration:
      enabled: true
      default_days: 365
      max_days: 730
      
    # Rate limiting
    rate_limits:
      default: "1000/hour"
      by_tier:
        basic: "100/hour"
        standard: "1000/hour"
        premium: "10000/hour"
        
  # Key scopes
  scopes:
    - read:assets
    - write:assets
    - delete:assets
    - read:projects
    - write:projects
    - admin:users
    - admin:system
    
  # Security
  security:
    hash_algorithm: "sha256"
    store_plaintext: false
    require_ip_whitelist: false
    require_user_agent: false
```

### API Key Usage

```bash
# Using API key in header
curl -H "X-API-Key: mams_AbCdEfGhIjKlMnOpQrStUvWxYz123456" \
  https://api.mams.com/v1/assets

# Using API key in query parameter (not recommended)
curl https://api.mams.com/v1/assets?api_key=mams_AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

## Session Management

### Session Configuration

```yaml
# config/sessions.yaml
sessions:
  # Storage backend
  storage:
    type: redis  # redis, database, memory
    redis:
      host: localhost
      port: 6379
      db: 0
      key_prefix: "session:"
      
  # Session settings
  settings:
    cookie_name: "mams_session"
    cookie_domain: ".mams.com"
    cookie_path: "/"
    cookie_secure: true  # HTTPS only
    cookie_httponly: true
    cookie_samesite: "Lax"
    
  # Timeouts
  timeouts:
    idle_timeout_minutes: 60
    absolute_timeout_hours: 12
    warning_minutes: 5
    
  # Concurrent sessions
  concurrent_sessions:
    enabled: true
    max_per_user: 5
    action_on_exceed: "revoke_oldest"  # revoke_oldest, prevent_new, allow_all
    
  # Session tracking
  tracking:
    track_ip: true
    track_user_agent: true
    track_location: true
    
  # Session security
  security:
    regenerate_id: true
    regenerate_interval_minutes: 30
    validate_ip: false  # Strict IP validation
    validate_user_agent: true
```

## Security Headers

### Header Configuration

```yaml
# config/security_headers.yaml
security_headers:
  # Strict-Transport-Security
  hsts:
    enabled: true
    max_age: 31536000  # 1 year
    include_subdomains: true
    preload: true
    
  # Content-Security-Policy
  csp:
    enabled: true
    directives:
      default-src: ["'self'"]
      script-src: ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"]
      style-src: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
      img-src: ["'self'", "data:", "https:"]
      font-src: ["'self'", "https://fonts.gstatic.com"]
      connect-src: ["'self'", "wss://mams.com"]
      frame-ancestors: ["'none'"]
      
  # Other headers
  headers:
    X-Frame-Options: "DENY"
    X-Content-Type-Options: "nosniff"
    X-XSS-Protection: "1; mode=block"
    Referrer-Policy: "strict-origin-when-cross-origin"
    Permissions-Policy: "geolocation=(), microphone=(), camera=()"
```

## Authentication Flow Examples

### 1. Local Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API Gateway
    participant Auth Service
    participant Database
    
    User->>Frontend: Enter credentials
    Frontend->>API Gateway: POST /auth/login
    API Gateway->>Auth Service: Validate credentials
    Auth Service->>Database: Get user by email
    Database-->>Auth Service: User data
    Auth Service->>Auth Service: Verify password
    Auth Service->>Auth Service: Check MFA requirement
    Auth Service-->>API Gateway: MFA required
    API Gateway-->>Frontend: Request MFA code
    Frontend-->>User: Show MFA prompt
    User->>Frontend: Enter MFA code
    Frontend->>API Gateway: POST /auth/verify-mfa
    API Gateway->>Auth Service: Verify MFA
    Auth Service->>Auth Service: Generate tokens
    Auth Service-->>API Gateway: Tokens
    API Gateway-->>Frontend: Auth success + tokens
```

### 2. SAML SSO Flow

```mermaid
sequenceDiagram
    participant User
    participant MAMS
    participant IdP
    
    User->>MAMS: Access protected resource
    MAMS->>MAMS: Check authentication
    MAMS->>User: Redirect to IdP
    User->>IdP: Login at IdP
    IdP->>IdP: Authenticate user
    IdP->>User: SAML Response
    User->>MAMS: POST SAML Response
    MAMS->>MAMS: Validate SAML
    MAMS->>MAMS: Create/Update user
    MAMS->>User: Set session & redirect
```

## Troubleshooting

### Common Issues

1. **LDAP Connection Failures**
   ```bash
   # Test LDAP connection
   ldapsearch -x -H ldap://ldap.company.com \
     -D "cn=service-account,ou=services,dc=company,dc=com" \
     -w password \
     -b "ou=users,dc=company,dc=com" \
     "(sAMAccountName=testuser)"
   ```

2. **SAML Assertion Errors**
   - Check IdP and SP certificates
   - Verify entity IDs match
   - Check clock synchronization
   - Review SAML response in browser dev tools

3. **OAuth2 Redirect Issues**
   - Verify redirect URIs are registered
   - Check CORS configuration
   - Ensure state parameter matches

4. **MFA Token Issues**
   - Verify server time is synchronized
   - Check TOTP window settings
   - Test with multiple time windows

### Debug Logging

```yaml
# Enable authentication debug logging
logging:
  loggers:
    mams.auth: DEBUG
    mams.auth.ldap: DEBUG
    mams.auth.saml: DEBUG
    mams.auth.oauth2: DEBUG
    mams.auth.mfa: DEBUG
```

---

For more information:
- [LDAP Setup Guide](./ldap.md)
- [SAML Integration Guide](./saml.md)
- [OAuth2 Setup Guide](./oauth2.md)
- [Security Best Practices](../security/authentication-security.md)