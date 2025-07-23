"""
OpenAPI Configuration

Comprehensive OpenAPI/Swagger documentation configuration for the MAMS API Gateway.
Includes security schemes, examples, and detailed API specifications.
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import json

from core.config import get_settings

settings = get_settings()


def get_openapi_tags() -> List[Dict[str, Any]]:
    """Get OpenAPI tags with descriptions"""
    return [
        {
            "name": "health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints"
        },
        {
            "name": "users",
            "description": "User management operations"
        },
        {
            "name": "assets",
            "description": "Media asset management operations"
        },
        {
            "name": "metadata",
            "description": "Asset metadata operations"
        },
        {
            "name": "search",
            "description": "Search and discovery operations"
        },
        {
            "name": "storage",
            "description": "Storage management operations"
        },
        {
            "name": "projects",
            "description": "Project and organization operations"
        },
        {
            "name": "workflows",
            "description": "Workflow and automation operations"
        },
        {
            "name": "ai",
            "description": "AI and machine learning operations"
        },
        {
            "name": "rights",
            "description": "Rights and license management"
        },
        {
            "name": "integrations",
            "description": "Third-party integrations"
        },
        {
            "name": "admin",
            "description": "Administrative operations"
        },
        {
            "name": "rate-limiting",
            "description": "Rate limiting management"
        },
        {
            "name": "logs",
            "description": "System logging and audit trails"
        },
        {
            "name": "api-keys",
            "description": "API key management"
        },
        {
            "name": "security",
            "description": "Security configuration and monitoring"
        },
        {
            "name": "ip-whitelist",
            "description": "IP whitelisting management"
        },
        {
            "name": "cors",
            "description": "CORS configuration management"
        },
        {
            "name": "versioning",
            "description": "API versioning information"
        }
    ]


def get_openapi_security_schemes() -> Dict[str, Any]:
    """Get OpenAPI security schemes"""
    return {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token authentication"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication"
        },
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "/api/v1/auth/oauth2/authorize",
                    "tokenUrl": "/api/v1/auth/oauth2/token",
                    "scopes": {
                        "read": "Read access to resources",
                        "write": "Write access to resources",
                        "admin": "Administrative access"
                    }
                }
            }
        }
    }


def get_openapi_servers() -> List[Dict[str, Any]]:
    """Get OpenAPI server configurations"""
    servers = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
    
    if settings.environment == "staging":
        servers.append({
            "url": "https://api-staging.mams.example.com",
            "description": "Staging server"
        })
    elif settings.environment == "production":
        servers.append({
            "url": "https://api.mams.example.com",
            "description": "Production server"
        })
    
    return servers


def get_openapi_info() -> Dict[str, Any]:
    """Get OpenAPI info configuration"""
    return {
        "title": "MAMS API Gateway",
        "description": """
## Digital Media Asset Management System (MAMS) API Gateway

The MAMS API Gateway serves as the central entry point for all MAMS microservices, providing:

### Core Features
- **Authentication & Authorization**: JWT and API key-based authentication with RBAC
- **Request Routing**: Intelligent routing to downstream microservices
- **Rate Limiting**: Configurable rate limiting with Redis backend
- **Security**: Comprehensive security headers, IP whitelisting, and request validation
- **Monitoring**: Request logging, metrics collection, and health checks
- **API Versioning**: Support for multiple API versions with backward compatibility

### Architecture
The API Gateway follows a microservices architecture pattern, routing requests to:
- **User Management Service**: User accounts, authentication, and authorization
- **Asset Management Service**: Media asset CRUD operations and versioning
- **Metadata Service**: Flexible metadata management and schemas
- **Search Engine**: Full-text search, filtering, and discovery
- **Storage Abstraction**: Multi-cloud storage management
- **Workflow Engine**: Automated workflows and approvals
- **AI/ML Service**: Content analysis and intelligent features
- **Rights Management**: License tracking and compliance
- **Integration Service**: Third-party system integrations

### Authentication
Most endpoints require authentication. Use one of the following methods:

#### JWT Bearer Token
```
Authorization: Bearer <jwt_token>
```

#### API Key
```
X-API-Key: <api_key>
```

### Rate Limiting
API calls are rate-limited based on:
- User tier (free, premium, enterprise)
- Endpoint sensitivity
- Request patterns

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Window reset time (Unix timestamp)

### Error Handling
All errors follow a consistent format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error details"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Response Format
Successful responses follow this structure:
```json
{
  "data": {...},
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  },
  "links": {
    "self": "...",
    "next": "...",
    "prev": "..."
  }
}
```

### Versioning
The API supports versioning through URL paths:
- `/api/v1/...` - Version 1 (current)
- `/api/v2/...` - Version 2 (future)

### Support
- **Documentation**: Complete API documentation available at `/docs`
- **Status Page**: System status at `/health`
- **Support**: support@mams.example.com
""",
        "version": "1.0.0",
        "contact": {
            "name": "MAMS Support",
            "email": "support@mams.example.com",
            "url": "https://mams.example.com/support"
        },
        "license": {
            "name": "Commercial License",
            "url": "https://mams.example.com/license"
        },
        "termsOfService": "https://mams.example.com/terms"
    }


def get_openapi_examples() -> Dict[str, Any]:
    """Get OpenAPI examples"""
    return {
        "components": {
            "examples": {
                "SuccessResponse": {
                    "summary": "Successful API response",
                    "value": {
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Example Asset",
                            "type": "video",
                            "created_at": "2024-01-15T10:30:00Z"
                        },
                        "meta": {
                            "request_id": "req_abc123",
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                },
                "ErrorResponse": {
                    "summary": "Error response",
                    "value": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "The requested resource was not found",
                            "details": {
                                "resource_id": "123e4567-e89b-12d3-a456-426614174000"
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "req_abc123"
                        }
                    }
                },
                "ValidationError": {
                    "summary": "Validation error response",
                    "value": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Request validation failed",
                            "details": {
                                "field_errors": {
                                    "email": ["Invalid email format"],
                                    "password": ["Password must be at least 8 characters"]
                                }
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "req_abc123"
                        }
                    }
                },
                "RateLimitError": {
                    "summary": "Rate limit exceeded",
                    "value": {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded. Please try again later.",
                            "details": {
                                "limit": 100,
                                "window": 3600,
                                "retry_after": 3600
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "req_abc123"
                        }
                    }
                },
                "AuthenticationError": {
                    "summary": "Authentication required",
                    "value": {
                        "error": {
                            "code": "AUTHENTICATION_REQUIRED",
                            "message": "Authentication required to access this resource",
                            "details": {
                                "supported_methods": ["Bearer", "API Key"]
                            },
                            "timestamp": "2024-01-15T10:30:00Z",
                            "request_id": "req_abc123"
                        }
                    }
                }
            }
        }
    }


def customize_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Customize OpenAPI schema with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=get_openapi_info()["title"],
        version=get_openapi_info()["version"],
        description=get_openapi_info()["description"],
        routes=app.routes,
        tags=get_openapi_tags(),
        servers=get_openapi_servers()
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = get_openapi_security_schemes()
    
    # Add examples
    examples = get_openapi_examples()
    if "examples" in examples["components"]:
        openapi_schema["components"]["examples"] = examples["components"]["examples"]
    
    # Add contact and license info
    openapi_schema["info"]["contact"] = get_openapi_info()["contact"]
    openapi_schema["info"]["license"] = get_openapi_info()["license"]
    openapi_schema["info"]["termsOfService"] = get_openapi_info()["termsOfService"]
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "MAMS Documentation",
        "url": "https://docs.mams.example.com"
    }
    
    # Add custom extensions
    openapi_schema["x-logo"] = {
        "url": "https://mams.example.com/logo.png",
        "altText": "MAMS Logo"
    }
    
    # Add API status information
    openapi_schema["x-api-status"] = {
        "version": "1.0.0",
        "status": "stable",
        "environment": settings.environment,
        "last_updated": "2024-01-15T10:30:00Z"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi_docs(app: FastAPI) -> None:
    """Setup OpenAPI documentation endpoints"""
    
    if not settings.openapi_enabled:
        return
    
    # In production, require authentication for documentation
    auth_required = settings.environment == "production"
    
    @app.get(settings.docs_url, include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with enhanced styling"""
        return get_swagger_ui_html(
            openapi_url=settings.openapi_url,
            title=f"{app.title} - Interactive API Documentation",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.3/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.3/swagger-ui.css",
            swagger_ui_parameters={
                "deepLinking": True,
                "displayRequestDuration": True,
                "docExpansion": "none",
                "operationsSorter": "alpha",
                "filter": True,
                "showExtensions": True,
                "showCommonExtensions": True,
                "defaultModelsExpandDepth": 2,
                "defaultModelExpandDepth": 2,
                "displayOperationId": True,
                "tryItOutEnabled": True,
                "persistAuthorization": True,
                "layout": "StandaloneLayout"
            }
        )
    
    @app.get(settings.redoc_url, include_in_schema=False)
    async def redoc_html():
        """ReDoc documentation with enhanced styling"""
        return get_redoc_html(
            openapi_url=settings.openapi_url,
            title=f"{app.title} - API Documentation",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
            redoc_favicon_url="https://mams.example.com/favicon.ico",
            with_google_fonts=True
        )
    
    @app.get(settings.openapi_url, include_in_schema=False)
    async def get_openapi_json():
        """Get OpenAPI JSON schema"""
        return customize_openapi_schema(app)
    
    @app.get("/api-docs", include_in_schema=False)
    async def api_docs_redirect():
        """Redirect to main documentation"""
        return HTMLResponse(f"""
        <html>
        <head>
            <title>MAMS API Documentation</title>
            <meta http-equiv="refresh" content="0; url={settings.docs_url}">
        </head>
        <body>
            <h1>MAMS API Documentation</h1>
            <p>Redirecting to <a href="{settings.docs_url}">API Documentation</a>...</p>
        </body>
        </html>
        """)
    
    @app.get("/api-info", include_in_schema=False)
    async def api_info():
        """Get API information"""
        return {
            "title": app.title,
            "version": app.version,
            "description": "MAMS API Gateway - Central entry point for all MAMS services",
            "environment": settings.environment,
            "documentation": {
                "swagger": settings.docs_url if settings.openapi_enabled else None,
                "redoc": settings.redoc_url if settings.openapi_enabled else None,
                "openapi": settings.openapi_url if settings.openapi_enabled else None
            },
            "endpoints": {
                "health": "/health",
                "status": "/api/status",
                "metrics": "/metrics" if settings.enable_metrics else None
            },
            "support": {
                "email": "support@mams.example.com",
                "documentation": "https://docs.mams.example.com",
                "status_page": "https://status.mams.example.com"
            }
        }


def configure_openapi_security(app: FastAPI) -> None:
    """Configure OpenAPI security requirements"""
    
    # Override the openapi method to add security to all endpoints
    original_openapi = app.openapi
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = customize_openapi_schema(app)
        
        # Add global security requirement
        openapi_schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []}
        ]
        
        # Add security to individual paths
        for path, path_item in openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict) and "security" not in operation:
                    # Skip security for public endpoints
                    if path in ["/health", "/", "/docs", "/redoc", "/openapi.json", "/api-info"]:
                        continue
                    
                    operation["security"] = [
                        {"BearerAuth": []},
                        {"ApiKeyAuth": []}
                    ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


def add_response_examples(app: FastAPI) -> None:
    """Add response examples to OpenAPI schema"""
    
    def add_examples_to_responses():
        if not app.openapi_schema:
            return
        
        # Common response examples
        common_responses = {
            "400": {
                "description": "Bad Request",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "BAD_REQUEST",
                                "message": "Invalid request parameters",
                                "details": {},
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            },
            "401": {
                "description": "Unauthorized",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "AUTHENTICATION_REQUIRED",
                                "message": "Authentication required",
                                "details": {},
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            },
            "403": {
                "description": "Forbidden",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "INSUFFICIENT_PERMISSIONS",
                                "message": "Insufficient permissions",
                                "details": {},
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            },
            "404": {
                "description": "Not Found",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "RESOURCE_NOT_FOUND",
                                "message": "Resource not found",
                                "details": {},
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            },
            "429": {
                "description": "Too Many Requests",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "RATE_LIMIT_EXCEEDED",
                                "message": "Rate limit exceeded",
                                "details": {
                                    "limit": 100,
                                    "retry_after": 3600
                                },
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            },
            "500": {
                "description": "Internal Server Error",
                "content": {
                    "application/json": {
                        "example": {
                            "error": {
                                "code": "INTERNAL_SERVER_ERROR",
                                "message": "An unexpected error occurred",
                                "details": {},
                                "timestamp": "2024-01-15T10:30:00Z",
                                "request_id": "req_abc123"
                            }
                        }
                    }
                }
            }
        }
        
        # Add common responses to all paths
        for path, path_item in app.openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict) and "responses" in operation:
                    for status_code, response_spec in common_responses.items():
                        if status_code not in operation["responses"]:
                            operation["responses"][status_code] = response_spec
    
    # Add examples after schema is generated
    original_openapi = app.openapi
    
    def enhanced_openapi():
        schema = original_openapi()
        add_examples_to_responses()
        return schema
    
    app.openapi = enhanced_openapi


def setup_openapi_configuration(app: FastAPI) -> None:
    """Setup complete OpenAPI configuration"""
    
    # Update app configuration
    app.title = get_openapi_info()["title"]
    app.description = get_openapi_info()["description"]
    app.version = get_openapi_info()["version"]
    app.contact = get_openapi_info()["contact"]
    app.license_info = get_openapi_info()["license"]
    app.terms_of_service = get_openapi_info()["termsOfService"]
    
    # Configure OpenAPI schema
    configure_openapi_security(app)
    add_response_examples(app)
    
    # Setup documentation endpoints
    setup_openapi_docs(app)
    
    # Override the openapi method to use our custom schema
    app.openapi = lambda: customize_openapi_schema(app)