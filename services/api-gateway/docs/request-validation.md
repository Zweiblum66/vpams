# Request Validation and Sanitization

The MAMS API Gateway implements comprehensive request validation and sanitization to protect against security vulnerabilities and ensure data integrity. This guide covers the validation system's features, configuration, and usage.

## Overview

The validation system provides multiple layers of protection:
- **Input Sanitization**: Removes or escapes dangerous content
- **Content Validation**: Validates data types, formats, and constraints
- **Security Headers**: Adds security headers to prevent common attacks
- **Request Size Limits**: Prevents resource exhaustion attacks
- **Pattern Blocking**: Blocks known malicious patterns

## Key Features

### Security Protection
- **XSS Prevention**: HTML escaping and script tag blocking
- **SQL Injection Protection**: SQL pattern detection and blocking
- **Path Traversal Protection**: Directory traversal pattern blocking
- **Command Injection Protection**: Command execution pattern blocking
- **CSRF Protection**: Security headers and token validation

### Content Validation
- **Data Type Validation**: Ensures correct data types
- **Format Validation**: Validates emails, URLs, UUIDs, etc.
- **Size Limits**: Prevents oversized requests and data
- **Character Filtering**: Removes control characters and dangerous content
- **File Upload Validation**: Validates file types and sizes

### Performance Features
- **Async Processing**: Non-blocking validation
- **Efficient Patterns**: Compiled regex patterns
- **Memory Management**: Prevents memory exhaustion
- **Rate Limiting**: Validation-specific rate limiting

## Architecture

### Core Components

```python
core/
├── validation.py              # Core validation logic
├── validation_middleware.py   # FastAPI middleware
└── validation_utils.py        # Utility functions and schemas
```

### Middleware Stack

```python
# Middleware order (request processing)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(ContentSecurityMiddleware)     # Security headers
app.add_middleware(ValidationMiddleware)          # Input validation
app.add_middleware(RequestSizeMiddleware)         # Size limits
app.add_middleware(RateLimitMiddleware)
```

## Configuration

### Validation Configuration

```python
from core.validation import RequestValidationConfig

config = RequestValidationConfig(
    max_string_length=10000,
    max_text_length=100000,
    max_json_size=10 * 1024 * 1024,  # 10MB
    max_form_fields=100,
    max_query_params=50,
    max_header_size=8192,
    max_filename_length=255,
    validation_rate_limit=1000,
    log_blocked_requests=True,
    log_sanitization=False
)
```

### Allowed File Extensions

```python
allowed_extensions = [
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    # Video
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
    # Audio
    '.mp3', '.wav', '.aac', '.ogg', '.flac',
    # Documents
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    # Archives
    '.zip', '.rar', '.7z', '.tar', '.gz'
]
```

### Blocked Patterns

```python
blocked_patterns = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',                # JavaScript URLs
    r'vbscript:',                 # VBScript URLs
    r'on\w+\s*=',                # Event handlers
    r'\bUNION\b.*\bSELECT\b',   # SQL injection
    r'\.\.[\\/]',              # Directory traversal
    r'<%.*%>',                   # ASP tags
    r'\${.*}',                   # Expression language
    # ... more patterns
]
```

## Usage

### Basic Validation

```python
from fastapi import FastAPI, Request
from core.validation_middleware import ValidationMiddleware

app = FastAPI()
app.add_middleware(ValidationMiddleware)

@app.post("/api/v1/data")
async def create_data(request: Request):
    # Sanitized data is automatically available
    from core.validation_middleware import get_sanitized_json
    
    data = get_sanitized_json(request)
    return {"received": data}
```

### Accessing Sanitized Data

```python
from core.validation_middleware import (
    get_sanitized_headers,
    get_sanitized_query_params,
    get_sanitized_json,
    get_sanitized_form,
    get_sanitized_text,
    get_sanitized_multipart_form
)

@app.post("/api/v1/upload")
async def upload_data(request: Request):
    # Get sanitized data
    headers = get_sanitized_headers(request)
    query_params = get_sanitized_query_params(request)
    json_data = get_sanitized_json(request)
    form_data = get_sanitized_form(request)
    
    return {
        "headers": headers,
        "query_params": query_params,
        "json_data": json_data,
        "form_data": form_data
    }
```

### Validation Utilities

```python
from core.validation_utils import (
    validate_uuid_param,
    validate_email_param,
    validate_url_param,
    PaginationParams,
    FilterParams
)

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    # Validate UUID parameter
    validated_id = validate_uuid_param(user_id)
    return {"user_id": validated_id}

@app.get("/api/v1/users")
async def list_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    filters: FilterParams = Depends(get_filter_params)
):
    return {
        "pagination": pagination,
        "filters": filters
    }
```

### Custom Validation

```python
from core.validation import get_sanitizer, get_validator
from core.exceptions import ValidationException

@app.post("/api/v1/custom")
async def custom_validation(request: Request):
    sanitizer = get_sanitizer()
    validator = get_validator()
    
    # Custom validation logic
    raw_data = await request.json()
    
    try:
        # Manual sanitization
        sanitized_data = sanitizer.sanitize_json_value(raw_data)
        
        # Additional validation
        if 'email' in sanitized_data:
            sanitized_data['email'] = sanitizer.sanitize_email(
                sanitized_data['email']
            )
        
        return {"data": sanitized_data}
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Security Features

### XSS Prevention

```python
# Input: "<script>alert('xss')</script>"
# Output: "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

# Blocked patterns
blocked_xss_patterns = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'vbscript:',
    r'on\w+\s*=',  # Event handlers
    r'\beval\s*\(',
    r'\bexec\s*\('
]
```

### SQL Injection Prevention

```python
# Blocked SQL patterns
blocked_sql_patterns = [
    r'\bUNION\b.*\bSELECT\b',
    r'\bDROP\b.*\bTABLE\b',
    r'\bINSERT\b.*\bINTO\b',
    r'\bUPDATE\b.*\bSET\b',
    r'\bDELETE\b.*\bFROM\b',
    r'\-\-',  # SQL comments
    r'/\*.*\*/',  # SQL comments
    r'\bxp_cmdshell\b',
    r'\bsp_executesql\b'
]
```

### Path Traversal Prevention

```python
# Blocked path traversal patterns
blocked_path_patterns = [
    r'\.\.[\\/]',  # Directory traversal
    r'[\\/]etc[\\/]passwd',  # Unix passwd file
    r'[\\/]windows[\\/]system32',  # Windows system dir
]
```

### Content Security Policy

```python
security_headers = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https: wss:; "
        "frame-ancestors 'none';"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

## Validation Types

### String Validation

```python
from core.validation import InputSanitizer

sanitizer = InputSanitizer(config)

# Basic string sanitization
clean_string = sanitizer.sanitize_string("Hello <script>alert('xss')</script>")
# Result: "Hello &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

# Length validation
try:
    sanitizer.sanitize_string("a" * 10001)  # Too long
except ValidationException as e:
    print(f"Validation error: {e}")
```

### Email Validation

```python
# Valid emails
valid_emails = [
    "user@example.com",
    "test.email+123@example.com",
    "user123@test-domain.co.uk"
]

# Invalid emails (will raise ValidationException)
invalid_emails = [
    "invalid-email",
    "test@",
    "@example.com",
    "user@.com",
    "user@domain."
]

for email in valid_emails:
    clean_email = sanitizer.sanitize_email(email)
    print(f"Valid: {email} -> {clean_email}")
```

### URL Validation

```python
# Valid URLs
valid_urls = [
    "https://example.com",
    "http://test.example.com/path",
    "ftp://files.example.com/file.txt"
]

# Invalid URLs (will raise ValidationException)
invalid_urls = [
    "javascript:alert('xss')",
    "data:text/html,<script>alert('xss')</script>",
    "file:///etc/passwd"
]

for url in valid_urls:
    clean_url = sanitizer.sanitize_url(url)
    print(f"Valid: {url} -> {clean_url}")
```

### File Upload Validation

```python
# Valid file uploads
valid_files = [
    ("document.pdf", "application/pdf", 1024 * 1024),
    ("image.jpg", "image/jpeg", 500 * 1024),
    ("video.mp4", "video/mp4", 10 * 1024 * 1024)
]

# Invalid file uploads
invalid_files = [
    ("malware.exe", "application/octet-stream", 1024),  # Bad extension
    ("large.pdf", "application/pdf", 100 * 1024 * 1024),  # Too large
    ("CON.txt", "text/plain", 1024)  # Reserved name
]

for filename, content_type, size in valid_files:
    try:
        validator.validate_file_upload(filename, content_type, size)
        print(f"Valid file: {filename}")
    except ValidationException as e:
        print(f"Invalid file {filename}: {e}")
```

### JSON Validation

```python
# Complex JSON validation
complex_data = {
    "user": {
        "name": "John <script>alert('xss')</script> Doe",
        "email": "john@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    },
    "items": [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item <script>alert('xss')</script> 2"}
    ]
}

# Sanitize nested JSON
sanitized_data = sanitizer.sanitize_json_value(complex_data)
# XSS content will be HTML escaped throughout the structure
```

## Error Handling

### Validation Errors

```python
try:
    validator.validate_content_length(20 * 1024 * 1024)  # Too large
except ValidationException as e:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "timestamp": time.time()
            }
        }
    )
```

### Common Error Codes

```python
error_codes = {
    "VALIDATION_ERROR": "Input validation failed",
    "REQUEST_TOO_LARGE": "Request size exceeds limits",
    "INVALID_CONTENT_TYPE": "Unsupported content type",
    "VALIDATION_RATE_LIMIT_EXCEEDED": "Too many validation requests",
    "MALICIOUS_CONTENT_DETECTED": "Dangerous content blocked",
    "FILE_UPLOAD_ERROR": "File upload validation failed"
}
```

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input contains blocked content",
    "details": {
      "field": "description",
      "pattern": "javascript:",
      "value": "javascript:alert('xss')"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

## Performance Optimization

### Compiled Patterns

```python
# Patterns are compiled once at startup
class InputSanitizer:
    def __init__(self, config):
        self.blocked_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in config.blocked_patterns
        ]
```

### Async Processing

```python
# All validation is async
async def validate_request(self, request: Request) -> None:
    # Validate headers
    headers = await self._validate_headers(request)
    
    # Validate query params
    params = await self._validate_query_params(request)
    
    # Validate body
    if request.method in ["POST", "PUT", "PATCH"]:
        await self._validate_request_body(request)
```

### Memory Management

```python
# Limits to prevent memory exhaustion
config = RequestValidationConfig(
    max_json_size=10 * 1024 * 1024,  # 10MB
    max_form_fields=100,
    max_query_params=50,
    max_header_size=8192
)
```

### Rate Limiting

```python
# Validation-specific rate limiting
class ValidationMiddleware:
    def __init__(self, app):
        self.validation_requests = {}  # IP -> timestamps
        self.validation_window = 60  # seconds
        self.max_validation_requests = 1000
    
    def _check_validation_rate_limit(self, request: Request) -> bool:
        # Implementation details...
        pass
```

## Monitoring and Logging

### Security Logging

```python
# Log blocked requests
logger.warning(
    "Blocked malicious request",
    extra={
        "client_ip": request.client.host,
        "method": request.method,
        "path": request.url.path,
        "pattern": "javascript:",
        "value": blocked_value,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.state.request_id
    }
)
```

### Performance Metrics

```python
# Validation performance metrics
validation_duration = Histogram(
    'validation_duration_seconds',
    'Time spent validating requests'
)

validation_errors = Counter(
    'validation_errors_total',
    'Total validation errors',
    ['error_type']
)

blocked_requests = Counter(
    'blocked_requests_total',
    'Total blocked requests',
    ['pattern_type']
)
```

### Health Checks

```python
@app.get("/health/validation")
async def validation_health():
    return {
        "status": "healthy",
        "patterns_loaded": len(sanitizer.blocked_patterns),
        "validation_rate_limit": config.validation_rate_limit,
        "max_request_size": config.max_json_size
    }
```

## Testing

### Unit Tests

```python
import pytest
from core.validation import InputSanitizer, RequestValidationConfig

def test_sanitize_string_xss():
    config = RequestValidationConfig()
    sanitizer = InputSanitizer(config)
    
    result = sanitizer.sanitize_string("<script>alert('xss')</script>")
    assert "&lt;script&gt;" in result
    assert "&lt;/script&gt;" in result

def test_blocked_patterns():
    config = RequestValidationConfig()
    sanitizer = InputSanitizer(config)
    
    with pytest.raises(ValidationException):
        sanitizer.sanitize_string("javascript:alert('xss')")
```

### Integration Tests

```python
from fastapi.testclient import TestClient

def test_validation_middleware():
    app = FastAPI()
    app.add_middleware(ValidationMiddleware)
    
    @app.post("/test")
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    client = TestClient(app)
    
    # Test with malicious content
    response = client.post(
        "/test",
        json={"data": "<script>alert('xss')</script>"}
    )
    
    assert response.status_code == 200
    # Content should be sanitized
```

### Performance Tests

```python
import time

def test_validation_performance():
    sanitizer = InputSanitizer(RequestValidationConfig())
    
    # Test with large dataset
    large_data = {f"field_{i}": f"value_{i}" for i in range(1000)}
    
    start_time = time.time()
    sanitized = sanitizer.sanitize_json_value(large_data)
    end_time = time.time()
    
    # Should complete in reasonable time
    assert (end_time - start_time) < 1.0
```

## Best Practices

### 1. Always Use Middleware
```python
# Add validation middleware early in the stack
app.add_middleware(ValidationMiddleware)
app.add_middleware(ContentSecurityMiddleware)
app.add_middleware(RequestSizeMiddleware)
```

### 2. Access Sanitized Data
```python
# Always use sanitized data
from core.validation_middleware import get_sanitized_json

@app.post("/api/data")
async def handle_data(request: Request):
    # Use sanitized data instead of raw request data
    data = get_sanitized_json(request)
    return process_data(data)
```

### 3. Custom Validation
```python
# Add custom validation for specific needs
from core.validation_utils import validate_uuid_param

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    # Validate UUID format
    validated_id = validate_uuid_param(user_id)
    return get_user_by_id(validated_id)
```

### 4. Error Handling
```python
# Handle validation errors gracefully
try:
    data = validator.validate_json_body(raw_data)
except ValidationException as e:
    raise HTTPException(
        status_code=400,
        detail=f"Validation failed: {e}"
    )
```

### 5. Security Monitoring
```python
# Monitor security events
logger.warning(
    "Security event detected",
    extra={
        "event_type": "blocked_request",
        "client_ip": request.client.host,
        "pattern": pattern_matched,
        "severity": "high"
    }
)
```

## Configuration Examples

### Development Environment
```python
dev_config = RequestValidationConfig(
    max_string_length=5000,
    max_json_size=5 * 1024 * 1024,  # 5MB
    validation_rate_limit=500,
    log_blocked_requests=True,
    log_sanitization=True  # Detailed logging
)
```

### Production Environment
```python
prod_config = RequestValidationConfig(
    max_string_length=10000,
    max_json_size=10 * 1024 * 1024,  # 10MB
    validation_rate_limit=2000,
    log_blocked_requests=True,
    log_sanitization=False  # Performance optimization
)
```

### High-Security Environment
```python
secure_config = RequestValidationConfig(
    max_string_length=2000,
    max_json_size=2 * 1024 * 1024,  # 2MB
    validation_rate_limit=100,
    log_blocked_requests=True,
    log_sanitization=True,
    # Additional security patterns
    blocked_patterns=default_patterns + additional_security_patterns
)
```

## Troubleshooting

### Common Issues

1. **Validation Too Strict**
   - Adjust configuration limits
   - Review blocked patterns
   - Check allowed file extensions

2. **Performance Issues**
   - Reduce validation complexity
   - Optimize blocked patterns
   - Adjust rate limits

3. **False Positives**
   - Review and refine patterns
   - Add pattern exceptions
   - Implement whitelist validation

### Debug Mode

```python
# Enable debug logging
config = RequestValidationConfig(
    log_blocked_requests=True,
    log_sanitization=True
)

# Set logging level
logging.getLogger('core.validation').setLevel(logging.DEBUG)
```

## Future Enhancements

- Machine learning-based threat detection
- Real-time pattern updates
- Advanced file content validation
- Integration with external security services
- Performance optimizations
- Additional validation rules

## Support

For questions or issues:
- Check logs for validation errors
- Review configuration settings
- Test with validation utilities
- Contact security team for pattern updates
