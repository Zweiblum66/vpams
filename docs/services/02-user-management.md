# User Management Service

## Overview

The User Management Service handles all user-related operations including authentication, authorization, user profiles, roles, permissions, and integration with external identity providers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Management Service                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │Authentication│  │Authorization │  │ User Repository │  │
│  │             │  │              │  │                 │  │
│  │  - Local    │  │ - RBAC       │  │ - User CRUD     │  │
│  │  - LDAP     │  │ - Permissions│  │ - Profile Mgmt  │  │
│  │  - SAML     │  │ - Policies   │  │ - Preferences   │  │
│  │  - OAuth2   │  │ - Groups     │  │ - Sessions      │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Integration Layer                    │  │
│  │      LDAP | Active Directory | SAML | OAuth2         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Database Layer                       │  │
│  │         PostgreSQL (Users, Roles, Permissions)       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. User Management
- User registration and onboarding
- Profile management
- Password policies
- Account activation/deactivation
- User preferences

### 2. Authentication
- Local authentication
- Multi-factor authentication (MFA)
- Single Sign-On (SSO)
- Session management
- Password recovery

### 3. Authorization
- Role-Based Access Control (RBAC)
- Fine-grained permissions
- Dynamic permission evaluation
- Resource-level permissions
- Permission inheritance

### 4. Identity Provider Integration
- LDAP/Active Directory
- SAML 2.0
- OAuth2/OpenID Connect
- Custom providers
- Just-In-Time (JIT) provisioning

### 5. Audit & Compliance
- Login history
- Permission changes tracking
- User activity logs
- Compliance reporting
- Data privacy controls

## API Endpoints

### User Operations

#### Register User
```http
POST /api/v1/users/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe",
  "organization": "ACME Corp",
  "role": "editor"
}
```

Response:
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "name": "John Doe",
  "organization": "ACME Corp",
  "status": "pending_activation",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Get User Profile
```http
GET /api/v1/users/{user_id}
Authorization: Bearer {token}
```

Response:
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "organization": "ACME Corp",
  "department": "Marketing",
  "title": "Senior Editor",
  "roles": ["editor", "reviewer"],
  "permissions": [
    "asset:read",
    "asset:write",
    "asset:delete",
    "project:read",
    "project:write"
  ],
  "preferences": {
    "theme": "dark",
    "language": "en",
    "timezone": "America/New_York",
    "notifications": {
      "email": true,
      "push": false
    }
  },
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-20T09:15:00Z"
}
```

#### Update User Profile
```http
PUT /api/v1/users/{user_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "John Updated",
  "department": "Creative",
  "preferences": {
    "theme": "light",
    "notifications": {
      "email": false
    }
  }
}
```

#### Change Password
```http
POST /api/v1/users/{user_id}/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "confirm_password": "NewPassword456!"
}
```

### Authentication Endpoints

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password",
  "mfa_code": "123456"  // Optional
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["editor", "reviewer"]
  }
}
```

#### SSO Login
```http
GET /api/v1/auth/sso/{provider}
```

Providers: `saml`, `oauth2`, `ldap`

#### Enable MFA
```http
POST /api/v1/users/{user_id}/mfa/enable
Authorization: Bearer {token}
```

Response:
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344"
  ]
}
```

### Role & Permission Management

#### List Roles
```http
GET /api/v1/roles
Authorization: Bearer {token}
```

Response:
```json
{
  "data": [
    {
      "id": "role-admin",
      "name": "Administrator",
      "description": "Full system access",
      "permissions": ["*"],
      "user_count": 5
    },
    {
      "id": "role-editor",
      "name": "Editor",
      "description": "Can edit and manage assets",
      "permissions": [
        "asset:read",
        "asset:write",
        "asset:delete",
        "project:read",
        "project:write"
      ],
      "user_count": 25
    }
  ]
}
```

#### Create Role
```http
POST /api/v1/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Reviewer",
  "description": "Can review and approve assets",
  "permissions": [
    "asset:read",
    "asset:review",
    "asset:approve",
    "project:read"
  ]
}
```

#### Assign Role to User
```http
POST /api/v1/users/{user_id}/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "role_id": "role-reviewer"
}
```

### Group Management

#### Create Group
```http
POST /api/v1/groups
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Marketing Team",
  "description": "Marketing department users",
  "permissions": [
    "project:marketing:*",
    "asset:read",
    "asset:write"
  ]
}
```

#### Add User to Group
```http
POST /api/v1/groups/{group_id}/members
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "user-123"
}
```

## Data Models

### User Model
```typescript
interface User {
  id: string;
  email: string;
  username?: string;
  name: string;
  avatar_url?: string;
  
  // Organization
  organization?: string;
  department?: string;
  title?: string;
  
  // Authentication
  password_hash: string;
  mfa_enabled: boolean;
  mfa_secret?: string;
  
  // Status
  status: UserStatus;
  email_verified: boolean;
  
  // Roles & Permissions
  roles: Role[];
  groups: Group[];
  direct_permissions: Permission[];
  
  // Preferences
  preferences: UserPreferences;
  
  // Audit
  created_at: Date;
  updated_at: Date;
  last_login?: Date;
  last_password_change?: Date;
  login_count: number;
}

enum UserStatus {
  ACTIVE = "active",
  INACTIVE = "inactive",
  PENDING = "pending",
  SUSPENDED = "suspended",
  DELETED = "deleted"
}
```

### Role Model
```typescript
interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  is_system: boolean;  // Cannot be modified
  priority: number;    // For permission resolution
  
  created_at: Date;
  updated_at: Date;
}
```

### Permission Model
```typescript
interface Permission {
  id: string;
  resource: string;    // e.g., "asset", "project"
  action: string;      // e.g., "read", "write", "delete"
  scope?: string;      // e.g., "own", "department", "all"
  conditions?: PermissionCondition[];
  
  created_at: Date;
}

interface PermissionCondition {
  field: string;
  operator: "eq" | "ne" | "in" | "contains";
  value: any;
}
```

## Configuration

### Environment Variables

```bash
# Service Configuration
USER_SERVICE_PORT=8001
SERVICE_NAME=user-management

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/mams_users

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Password Policy
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true
PASSWORD_HISTORY_COUNT=5

# MFA
MFA_ISSUER_NAME=MAMS
MFA_WINDOW_SIZE=1

# LDAP Configuration
LDAP_ENABLED=false
LDAP_SERVER=ldap://ldap.example.com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=password
LDAP_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_FILTER=(uid={username})

# SAML Configuration
SAML_ENABLED=false
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
SAML_SP_ENTITY_ID=https://mams.example.com
SAML_SP_ACS_URL=https://mams.example.com/api/v1/auth/saml/acs

# OAuth2 Configuration
OAUTH2_ENABLED=false
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_AUTHORIZE_URL=https://oauth.example.com/authorize
OAUTH2_TOKEN_URL=https://oauth.example.com/token
```

### Service Configuration (config.yaml)

```yaml
user_management:
  # Registration
  registration:
    enabled: true
    require_email_verification: true
    default_role: user
    allowed_domains:
      - example.com
      - company.com
    
  # Password policy
  password_policy:
    min_length: 12
    max_length: 128
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_special: true
    special_chars: "!@#$%^&*"
    prevent_common: true
    prevent_reuse: 5
    expiry_days: 90
    
  # Session management
  session:
    timeout_minutes: 60
    max_sessions_per_user: 5
    remember_me_days: 30
    
  # MFA settings
  mfa:
    enabled: true
    enforce_for_roles:
      - admin
      - manager
    methods:
      - totp
      - backup_codes
      
  # Rate limiting
  rate_limits:
    login_attempts: 5
    login_window_minutes: 15
    password_reset_per_day: 3
```

## Authentication Flows

### Local Authentication

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant UserService
    participant Database
    participant Redis
    
    Client->>API Gateway: POST /auth/login
    API Gateway->>UserService: Validate credentials
    UserService->>Database: Get user by email
    Database-->>UserService: User data
    UserService->>UserService: Verify password
    UserService->>Redis: Store session
    UserService->>UserService: Generate JWT
    UserService-->>API Gateway: Tokens & user info
    API Gateway-->>Client: Authentication response
```

### SAML SSO Flow

```mermaid
sequenceDiagram
    participant User
    participant MAMS
    participant IdP
    
    User->>MAMS: Access protected resource
    MAMS->>User: Redirect to IdP
    User->>IdP: Login at IdP
    IdP->>User: SAML Response
    User->>MAMS: POST SAML Response
    MAMS->>MAMS: Validate SAML
    MAMS->>MAMS: Create/Update user
    MAMS->>User: Set session & redirect
```

## Security Features

### 1. Password Security

```python
class PasswordValidator:
    def validate(self, password: str, user: User) -> List[str]:
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
            
        # Complexity checks
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letters")
            
        # Common password check
        if self.prevent_common and password.lower() in COMMON_PASSWORDS:
            errors.append("Password is too common")
            
        # User info check
        if any(info in password.lower() for info in [user.email, user.name]):
            errors.append("Password cannot contain personal information")
            
        # History check
        for old_hash in user.password_history:
            if verify_password(password, old_hash):
                errors.append("Password was recently used")
                
        return errors
```

### 2. Account Security

```python
class AccountSecurity:
    async def handle_failed_login(self, email: str):
        key = f"login_attempts:{email}"
        attempts = await redis.incr(key)
        await redis.expire(key, 900)  # 15 minutes
        
        if attempts >= 5:
            await self.lock_account(email)
            await self.send_security_alert(email)
            
    async def require_mfa(self, user: User) -> bool:
        # Always require for certain roles
        if any(role in MFA_REQUIRED_ROLES for role in user.roles):
            return True
            
        # Require for suspicious activity
        if await self.detect_suspicious_login(user):
            return True
            
        return user.mfa_enabled
```

### 3. Session Management

```python
class SessionManager:
    async def create_session(self, user: User, request: Request) -> Session:
        # Check concurrent sessions
        active_sessions = await self.get_active_sessions(user.id)
        if len(active_sessions) >= MAX_SESSIONS_PER_USER:
            # Revoke oldest session
            await self.revoke_session(active_sessions[0].id)
            
        session = Session(
            id=generate_session_id(),
            user_id=user.id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        await redis.setex(
            f"session:{session.id}",
            3600,
            session.json()
        )
        
        return session
```

## Permission System

### Permission Evaluation

```python
class PermissionEvaluator:
    def has_permission(
        self,
        user: User,
        resource: str,
        action: str,
        resource_data: dict = None
    ) -> bool:
        # Check direct permissions
        if self._check_direct_permissions(user, resource, action):
            return True
            
        # Check role permissions
        for role in user.roles:
            if self._check_role_permissions(role, resource, action):
                return True
                
        # Check group permissions
        for group in user.groups:
            if self._check_group_permissions(group, resource, action):
                return True
                
        # Check conditional permissions
        if resource_data:
            return self._check_conditional_permissions(
                user, resource, action, resource_data
            )
            
        return False
        
    def _check_conditional_permissions(
        self,
        user: User,
        resource: str,
        action: str,
        resource_data: dict
    ) -> bool:
        permissions = self._get_all_permissions(user)
        
        for perm in permissions:
            if perm.resource == resource and perm.action == action:
                if self._evaluate_conditions(perm.conditions, resource_data, user):
                    return True
                    
        return False
```

### Dynamic Permissions

```python
# Define custom permission rules
DYNAMIC_PERMISSIONS = {
    "asset:delete": lambda user, asset: (
        user.id == asset.created_by or
        "admin" in user.roles or
        (asset.project_id and user.has_permission(f"project:{asset.project_id}:admin"))
    ),
    
    "project:write": lambda user, project: (
        user.id in project.member_ids or
        user.department == project.department or
        "manager" in user.roles
    )
}
```

## Integration Examples

### LDAP Integration

```python
class LDAPAuthenticator:
    def __init__(self, config: LDAPConfig):
        self.server = Server(config.server, get_info=ALL)
        self.search_base = config.search_base
        self.user_filter = config.user_filter
        
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        # Bind with service account
        conn = Connection(
            self.server,
            self.bind_dn,
            self.bind_password,
            auto_bind=True
        )
        
        # Search for user
        search_filter = self.user_filter.format(username=username)
        conn.search(
            self.search_base,
            search_filter,
            attributes=['*']
        )
        
        if not conn.entries:
            return None
            
        user_dn = conn.entries[0].entry_dn
        
        # Try to bind as user
        try:
            user_conn = Connection(
                self.server,
                user_dn,
                password,
                auto_bind=True
            )
            user_conn.unbind()
            
            # Create or update local user
            return await self.sync_user(conn.entries[0])
        except:
            return None
```

### SAML Integration

```python
class SAMLAuthenticator:
    def __init__(self, config: SAMLConfig):
        self.saml_auth = OneLogin_Saml2_Auth(
            self._get_saml_settings(config)
        )
        
    async def handle_sso(self, request: Request) -> Optional[User]:
        self.saml_auth.process_response()
        
        if not self.saml_auth.is_authenticated():
            errors = self.saml_auth.get_errors()
            raise SAMLAuthError(errors)
            
        attributes = self.saml_auth.get_attributes()
        
        # Create or update user
        user_data = {
            "email": attributes.get("email")[0],
            "name": attributes.get("displayName")[0],
            "external_id": self.saml_auth.get_nameid(),
            "auth_provider": "saml"
        }
        
        return await self.create_or_update_user(user_data)
```

## Monitoring & Metrics

### Key Metrics

```python
# User metrics
user_registrations = Counter(
    'user_registrations_total',
    'Total number of user registrations',
    ['status']
)

login_attempts = Counter(
    'login_attempts_total',
    'Total number of login attempts',
    ['result', 'method']
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active user sessions'
)

mfa_usage = Counter(
    'mfa_usage_total',
    'MFA usage statistics',
    ['method', 'result']
)

# Track metrics
@track_metrics
async def login(credentials: LoginRequest):
    try:
        user = await authenticate_user(credentials)
        login_attempts.labels(result='success', method='local').inc()
        return user
    except AuthenticationError:
        login_attempts.labels(result='failure', method='local').inc()
        raise
```

## Troubleshooting

### Common Issues

1. **Account Lockouts**
   - Check failed login attempts
   - Verify account status
   - Review security logs

2. **SSO Integration Issues**
   - Validate metadata configuration
   - Check network connectivity
   - Verify certificates

3. **Permission Denials**
   - Review user roles and groups
   - Check permission inheritance
   - Verify conditional permissions

### Debug Endpoints

```http
GET /api/v1/users/{user_id}/permissions/debug
Authorization: Bearer {admin_token}

Response shows permission evaluation tree:
{
  "user_id": "user-123",
  "requested": "asset:write",
  "granted": false,
  "evaluation": {
    "direct_permissions": [],
    "role_permissions": [
      {
        "role": "viewer",
        "permissions": ["asset:read"],
        "matched": false
      }
    ],
    "group_permissions": [],
    "reason": "No matching permission found"
  }
}
```

---

For more information:
- [Authentication Configuration](../configuration/authentication.md)
- [LDAP Setup Guide](../configuration/ldap.md)
- [SAML Configuration](../configuration/saml.md)
- [Security Best Practices](../security/user-security.md)